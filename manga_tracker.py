#!/usr/bin/env python3
"""A polite, local manga chapter tracker.

The site-specific part is intentionally configuration-driven: chapter_selector
must select the links (or other elements) that represent individual chapters.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
import schedule
from bs4 import BeautifulSoup

APP_DIR = Path.home() / ".manga-chapter-tracker"
STATE_PATH = APP_DIR / "state.json"
CONFIG_PATH = Path("config.json")
DEFAULT_DASHBOARD_PATH = Path("docs/data/chapters.json")
USER_AGENT = "MangaChapterTracker/1.0 (personal update checker)"
LOG = logging.getLogger("manga_tracker")


@dataclass(frozen=True)
class Chapter:
    key: str
    name: str
    url: str


def load_json(path: Path, description: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"{description} not found: {path}. Run: cp config.example.json config.json")
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid {description} ({path}): {error}")


def load_state() -> dict[str, list[str]]:
    if not STATE_PATH.exists():
        return {}
    try:
        data = load_json(STATE_PATH, "state file")
        return data if isinstance(data, dict) else {}
    except SystemExit:
        LOG.warning("State file is invalid; starting with an empty state.")
        return {}


def save_state(state: dict[str, list[str]]) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(STATE_PATH)


def chapters_from_css(item: dict[str, Any], soup: BeautifulSoup) -> list[Chapter]:
    """Extract chapters using the CSS selector supplied by a site configuration."""
    url = item["url"]
    selector = item["chapter_selector"]
    attribute = item.get("chapter_title_attribute")
    chapters: list[Chapter] = []
    for element in soup.select(selector):
        name = str(element.get(attribute, "")).strip() if attribute else element.get_text(" ", strip=True)
        href = element.get("href", "")
        chapter_url = urljoin(url, href) if href else url
        if not name:
            continue
        key = hashlib.sha256(f"{name}\0{chapter_url}".encode()).hexdigest()
        chapters.append(Chapter(key=key, name=name, url=chapter_url))
    # Many pages repeat links (desktop/mobile layouts); preserve page order.
    return list(dict.fromkeys(chapters))


def chapters_from_mgeko_series(item: dict[str, Any], soup: BeautifulSoup) -> list[Chapter]:
    """Extract Mgeko chapters from a series page, excluding page-navigation links."""
    url = item["url"]
    chapters: list[Chapter] = []
    for link in soup.select(".chapter-list .chapter-list-item a[href*='/reader/']"):
        number = link.select_one(".chapter-number")
        # ``get_text`` also contains the relative publication time. The first
        # direct text node is the stable chapter label, such as "33-eng-li".
        name = next((str(part).strip() for part in number.contents if str(part).strip()), "") if number else ""
        href = link.get("href", "")
        if not name or not href:
            continue
        chapter_url = urljoin(url, href)
        key = hashlib.sha256(f"{name}\0{chapter_url}".encode()).hexdigest()
        chapters.append(Chapter(key=key, name=name, url=chapter_url))
    return list(dict.fromkeys(chapters))


def chapters_from_mgeko_updates(item: dict[str, Any], soup: BeautifulSoup) -> list[Chapter]:
    """Find one title in Mgeko's shared recently-updated feed."""
    wanted = item.get("match_title", item["title"]).casefold().strip()
    chapters: list[Chapter] = []
    for card in soup.select("li.novel-item"):
        series = card.select_one("h4.novel-title")
        chapter = card.select_one("h5.chapter-title")
        link = card.select_one("a.list-body[href]")
        if not series or not chapter or not link or series.get_text(" ", strip=True).casefold() != wanted:
            continue
        name = chapter.get_text(" ", strip=True)
        chapter_url = urljoin(item["url"], link["href"])
        key = hashlib.sha256(f"{name}\0{chapter_url}".encode()).hexdigest()
        chapters.append(Chapter(key=key, name=name, url=chapter_url))
    return list(dict.fromkeys(chapters))


PARSERS = {
    "css": chapters_from_css,
    "mgeko_series": chapters_from_mgeko_series,
    "mgeko_updates": chapters_from_mgeko_updates,
}


def fetch_chapters(item: dict[str, Any], session: requests.Session) -> list[Chapter]:
    response = session.get(item["url"], timeout=(10, 30))
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    parser_name = item.get("parser", "css")
    parser = PARSERS.get(parser_name)
    if parser is None:
        raise ValueError(f"unknown parser {parser_name!r}; available: {', '.join(PARSERS)}")
    return parser(item, soup)


def notify(title: str, message: str) -> None:
    LOG.info("%s: %s", title, message)
    if platform.system() == "Darwin":
        # Arguments keep notification text out of shell parsing.
        script = 'on run argv\n display notification (item 2 of argv) with title (item 1 of argv)\nend run'
        try:
            subprocess.run(["osascript", "-e", script, title, message], check=False, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as error:
            LOG.warning("Could not show notification: %s", error)


def check(config: dict[str, Any], announce_first_check: bool = False) -> int:
    state = load_state()
    delay = max(float(config.get("request_delay_seconds", 2)), 0)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    for item in config.get("manga", []):
        if not item.get("enabled", True):
            continue
        required = ("title", "url")
        if item.get("parser", "css") == "css":
            required += ("chapter_selector",)
        for field in required:
            if not item.get(field):
                LOG.error("Skipping malformed entry: missing %s", field)
                break
        else:
            title = item["title"]
            # Sites can contain identically named series. A source identifier
            # avoids their histories being accidentally shared.
            state_id = f"{item.get('site', item.get('parser', 'css'))}:{title}"
            try:
                chapters = fetch_chapters(item, session)
                if not chapters:
                    LOG.warning("%s: selector matched no chapters; state unchanged.", title)
                    continue
                known = set(state.get(state_id, []))
                if not known:
                    state[state_id] = [chapter.key for chapter in chapters]
                    LOG.info("%s: recorded %d existing chapter(s); no alert on first check.", title, len(chapters))
                    if announce_first_check:
                        notify("Manga tracker ready", f"{title}: recorded {len(chapters)} existing chapters")
                else:
                    new = [chapter for chapter in chapters if chapter.key not in known]
                    if new:
                        # Keep a bounded history to avoid indefinite state growth.
                        state[state_id] = list(dict.fromkeys([chapter.key for chapter in chapters] + state[state_id]))[:500]
                        message = "; ".join(chapter.name for chapter in new[:5])
                        if len(new) > 5:
                            message += f" (+{len(new) - 5} more)"
                        notify(f"New chapter — {title}", message)
                    else:
                        LOG.info("%s: no new chapters.", title)
            except (requests.RequestException, ValueError, KeyError) as error:
                LOG.error("%s: check failed (%s); will retry on the next run.", title, error)
            finally:
                if delay:
                    time.sleep(delay)
    save_state(state)
    return 0


def export_dashboard(config: dict[str, Any], output_path: Path) -> int:
    """Write current chapter data for the static GitHub Pages dashboard."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    entries: list[dict[str, Any]] = []
    for item in config.get("manga", []):
        if not item.get("enabled", True):
            continue
        try:
            chapters = fetch_chapters(item, session)
            entries.append({
                "id": f"{item.get('site', item.get('parser', 'css'))}:{item['title']}",
                "title": item["title"],
                "site": item.get("site", "Unknown source"),
                "chapters": [{"id": c.key, "name": c.name, "url": c.url} for c in chapters],
            })
        except (requests.RequestException, ValueError, KeyError) as error:
            LOG.error("%s: could not export (%s)", item.get("title", "Unknown title"), error)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"manga": entries}, indent=2) + "\n", encoding="utf-8")
    LOG.info("Dashboard data written to %s", output_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check configured manga chapter pages.")
    parser.add_argument("command", choices=("check", "run", "export"), nargs="?", default="check")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_DASHBOARD_PATH,
                        help="Output file for the export command")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_json(args.config, "configuration")
    if args.command == "check":
        return check(config, announce_first_check=True)
    if args.command == "export":
        return export_dashboard(config, args.output)
    minutes = max(int(config.get("poll_interval_minutes", 60)), 1)
    LOG.info("Running every %d minute(s). Press Ctrl-C to stop.", minutes)
    check(config, announce_first_check=True)
    schedule.every(minutes).minutes.do(check, config)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
