# Cascadia State Legislature · Bill Tracker

A small static bill tracker for the 2026 Regular Session of the Cascadia State Legislature. Cascadia is a fictional US state, and every bill, legislator, and agency on the site is invented. Pages serves the site as-is from the repository root, so every link in the HTML is relative.

## Published URLs

- Tracker home: https://quinndarling21.github.io/cascadia-bill-tracker-demo/
- SB 214 full text: https://quinndarling21.github.io/cascadia-bill-tracker-demo/bills/sb-214.html
- RSS feed: https://quinndarling21.github.io/cascadia-bill-tracker-demo/bills/feed.rss
- JSON feed: https://quinndarling21.github.io/cascadia-bill-tracker-demo/bills/feed.json
- All bill data, including full text: https://quinndarling21.github.io/cascadia-bill-tracker-demo/bills/index.json

## How it works

`data/bills.json` is the source of truth: the session plus eight bills with status, history, and full text. `build.py` regenerates every published file from it:

| File | Contents |
| --- | --- |
| `index.html` | Tracker home: all bills with sponsor, status, status date, and effective date |
| `bills/<slug>.html` | One full-text page per bill |
| `bills/feed.rss` | RSS 2.0 feed, one item per bill, newest status change first |
| `bills/feed.json` | The same feed items as JSON |
| `bills/index.json` | All bill data, including sections |
| `.nojekyll` | Tells Pages to serve the files as-is |

`assets/site.css` is the only hand-written published file. Generated files are committed because Pages serves them directly.

Each feed item's guid is `<slug>-<status-slug>-<status_date>-<status-change timestamp>`, so feed readers see a new item every time a bill's status changes.

Requires Python 3.9 or newer, standard library only.

## Rebuild

```sh
python3 build.py
```

Run this after editing `data/bills.json`. The reset script below rebuilds on its own.

## Before each demo run

```sh
python3 scripts/reset_sb214.py --push
```

Then wait about a minute for Pages to publish, and check that the tracker home shows SB 214 as "Signed by Governor".

This sets SB 214 to "Signed by Governor" with today's date (Pacific time) and replaces any earlier "Passed Senate", "Passed House", and "Signed by Governor" history entries with fresh ones dated today. It also stamps a new status-change time, so the feed item gets a new guid and pubDate. Finally it rebuilds the site and runs `git add -A && git commit -m "Update SB 214 status" && git push`.

Other options:

| Command | Effect |
| --- | --- |
| `python3 scripts/reset_sb214.py` | Same as above, without committing or pushing |
| `python3 scripts/reset_sb214.py --date 2026-10-05` | Signs SB 214 on a specific date instead of today |
| `python3 scripts/reset_sb214.py --state committee --push` | Puts SB 214 back to "In committee" (the initial state) and publishes it |

Going back to committee restores the original feed item, including its guid, so feed readers don't treat it as new.

Pages can serve cached copies for a few minutes after a publish. If a page still shows the old status, hard-refresh it.
