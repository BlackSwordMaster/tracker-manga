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

Each title chooses a parser. `mgeko_updates` watches Mgeko's shared update feed and filters it by `match_title`; `mgeko_series` is tailored to individual Mgeko series pages. `css` is the generic, future-proof option: its `chapter_selector` is a normal CSS selector that selects each chapter element, ideally an `<a>` tag. When a site stores a chapter name in an attribute rather than visible text, set `chapter_title_attribute`, for example `"title"`.

```json
{
  "poll_interval_minutes": 60,
  "request_delay_seconds": 2,
  "manga": [
    {
      "title": "My Manga on Mgeko",
      "site": "mgeko",
      "parser": "mgeko_updates",
      "url": "https://www.mgeko.cc/jumbo/manga/",
      "match_title": "My Manga on Mgeko",
      "enabled": true
    },
    {
      "title": "My Manga on another site",
      "site": "publisher-name",
      "parser": "css",
      "url": "https://site.example/series/my-manga",
      "chapter_selector": ".chapters a",
      "enabled": true
    }
  ]
}
```

`site` is an identifier used to keep histories separate when two sources have the same title. To support a new site's unusual markup, add a small parser function to `manga_tracker.py` and register it in `PARSERS`; existing configurations will continue using their named parser. The tracker waits two seconds between websites by default, identifies itself with a clear user agent, uses timeouts, and keeps state unchanged if a parser unexpectedly matches nothing. Do not lower the interval below a site's published limits or use this with sources that prohibit automated access.

## State and troubleshooting

Seen chapters are stored in `~/.manga-chapter-tracker/state.json`. Deleting that file resets the initial baseline (the next check will not notify for currently listed chapters). Logs in Terminal explain failed requests and selector mismatches; failures do not erase previously saved history.

To tailor the parser, share the target site's chapter-list URL (and confirmation that you may check it). Some pages load chapter links with JavaScript or use an anti-bot service; those need a site-specific approach.

## Bookmarkable GitHub Pages dashboard

This project includes a small dashboard in `docs/`. It shows unread chapters first; selecting **Mark read** (or **Mark all read**) remembers that choice in the browser you use to read it. A chapter update later added by the tracker appears as unread. This is intentionally a reading list, not a notification service.

To host it on GitHub Pages:

1. Copy `config.example.json` to `config.json`, add your real titles, and commit it. URLs and titles in that file are visible to anyone who can view the repository, so use a private repository if that matters to you.
2. On GitHub, open **Settings → Pages** and set the source to **Deploy from a branch**, then select your default branch and the `/docs` folder.
3. Open the **Actions** tab and run **Refresh manga tracker** once. It downloads the current lists into `docs/data/chapters.json`; the first run can take a few minutes to appear on Pages.
4. Bookmark the Pages address. GitHub Actions refreshes the chapter data about once per hour. Scheduled GitHub jobs are best-effort and can run late, so this is a convenient tracker rather than a real-time service.

Your read/unread status is stored only in that browser. Clearing browser storage, using another browser/device, or changing the dashboard's domain starts a separate reading list. Shared cross-device read state would require a sign-in-backed database.
