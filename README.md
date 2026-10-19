# Manga Chapter Tracker

A small, local macOS-friendly tracker that checks chapter-list pages, remembers what it has already seen, and displays a desktop notification only when a new chapter appears. It runs entirely on your machine.

## Setup (macOS)

1. In Terminal, open this project folder and create an isolated Python environment:

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp config.example.json config.json
   ```

2. Edit `config.json`. For each manga, provide a page URL and a parser. The Mgeko template uses the supplied shared updates page: replace both `title` and `match_title` with the series name exactly as Mgeko displays it, then set `enabled` to `true`. For the most reliable tracking, use that manga's individual Mgeko series page with `mgeko_series` instead.

3. Test it once:

   ```sh
   python manga_tracker.py check
   ```

   The first successful check records current chapters without alerting you about old releases. Later checks notify you only about new ones.

4. Keep it running every hour:

   ```sh
   python manga_tracker.py run
   ```

   Leave that Terminal window open. Press `Ctrl-C` to stop it. macOS may ask permission for Terminal to send notifications; allow it.

## Configuration

For the public dashboard, the included `feeds` configuration downloads Mgeko's latest-update page. Visitors choose titles in the site itself; no manga names are hard-coded in the configuration.

The optional `manga` section is for the local command-line tracker. `mgeko_updates` watches Mgeko's shared update feed and filters it by `match_title`; `mgeko_series` is tailored to individual Mgeko series pages. `css` is the generic, future-proof option: its `chapter_selector` is a normal CSS selector that selects each chapter element, ideally an `<a>` tag.

```json
{
  "poll_interval_minutes": 60,
  "request_delay_seconds": 2,
  "manga": [],
  "feeds": [{
    "id": "mgeko",
    "name": "Mgeko",
    "parser": "mgeko_updates_feed",
    "url": "https://www.mgeko.cc/jumbo/manga/"
  }]
}
```

`site` is an identifier used to keep histories separate when two sources have the same title. To support a new site's unusual markup, add a small parser function to `manga_tracker.py` and register it in `PARSERS`; existing configurations will continue using their named parser. The tracker waits two seconds between websites by default, identifies itself with a clear user agent, uses timeouts, and keeps state unchanged if a parser unexpectedly matches nothing. Do not lower the interval below a site's published limits or use this with sources that prohibit automated access.

## State and troubleshooting

Seen chapters are stored in `~/.manga-chapter-tracker/state.json`. Deleting that file resets the initial baseline (the next check will not notify for currently listed chapters). Logs in Terminal explain failed requests and selector mismatches; failures do not erase previously saved history.

To tailor the parser, share the target site's chapter-list URL (and confirmation that you may check it). Some pages load chapter links with JavaScript or use an anti-bot service; those need a site-specific approach.

## Bookmarkable GitHub Pages dashboard

This project includes a public, no-account dashboard in `docs/`. Type a title and choose it from the Mgeko suggestions, then select **Add to my tracker**. Current results are treated as already read, and later chapters appear as unread. **Mark read** and **Mark all read** update the local reading list in that browser. This is intentionally a reading list, not a notification service.

To host it on GitHub Pages:

1. Copy `config.example.json` to `config.json` and commit it. It contains only the public Mgeko source—not visitors' chosen titles.
2. On GitHub, open **Settings → Pages** and set the source to **Deploy from a branch**, then select your default branch and the `/docs` folder.
3. Open the **Actions** tab and run **Refresh manga tracker** once. It downloads the current lists into `docs/data/chapters.json`; the first run can take a few minutes to appear on Pages.
4. Bookmark the Pages address. GitHub Actions refreshes the chapter data about once per hour. Scheduled GitHub jobs are best-effort and can run late, so this is a convenient tracker rather than a real-time service.

Each visitor's title list and read/unread status are stored only in their browser. Clearing browser storage, using another browser/device, or changing the dashboard's domain starts a separate reading list. The shared feed contains only recent Mgeko updates, so a title must appear in that feed before it can be added.
