#!/usr/bin/env python3
"""Regenerate every published file of the bill tracker from data/bills.json."""

import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

BASE_URL = "https://quinndarling21.github.io/cascadia-bill-tracker-demo/"
FEED_TITLE = "Cascadia Legislature · Bill Tracker"
PACIFIC = ZoneInfo("America/Los_Angeles")
ATOM_NS = "http://www.w3.org/2005/Atom"

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "bills.json"
BILLS_DIR = ROOT / "bills"

SEAL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" aria-hidden="true">'
    '<circle cx="32" cy="32" r="31" fill="#c9a227"/>'
    '<circle cx="32" cy="32" r="28" fill="#13294b"/>'
    '<polygon points="32,9 33.57,13.84 38.66,13.84 34.54,16.83 36.11,21.66 32,18.67 '
    '27.89,21.66 29.46,16.83 25.34,13.84 30.43,13.84" fill="#c9a227"/>'
    '<path d="M11 46 24 28l6 8 8-11 15 21z" fill="#fff"/>'
    '<path d="M16 51q4-2.5 8 0t8 0 8 0 8 0" fill="none" stroke="#fff" stroke-width="2"/>'
    "</svg>"
)
RSS_ICON_SVG = (
    '<svg viewBox="0 0 16 16" aria-hidden="true">'
    '<rect width="16" height="16" rx="3" fill="#e8772e"/>'
    '<circle cx="4.5" cy="11.5" r="1.6" fill="#fff"/>'
    '<path d="M4.5 7a4.5 4.5 0 0 1 4.5 4.5M4.5 3a8.5 8.5 0 0 1 8.5 8.5" '
    'fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/>'
    "</svg>"
)

esc = html.escape


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def fmt_date(value):
    """'2027-04-01' -> 'April 1, 2027'; text such as 'Upon enactment' passes through."""
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return value
    return f"{value:%B} {value.day}, {value.year}"


def fmt_timestamp(dt):
    local = dt.astimezone(PACIFIC)
    return f"{fmt_date(local.date())} at {local.hour % 12 or 12}:{local:%M %p %Z}"


def changed_at(bill):
    return datetime.fromisoformat(bill["status_changed_at"])


def bill_path(bill):
    return f"bills/{bill['slug']}.html"


def pill(status):
    return f'<span class="pill pill-{slugify(status)}">{esc(status)}</span>'


def page(session, title, body, root=""):
    legislature = esc(session["legislature"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="icon" href="data:image/svg+xml,{quote(SEAL_SVG)}">
<link rel="stylesheet" href="{root}assets/site.css">
<link rel="alternate" type="application/rss+xml" title="{esc(FEED_TITLE)}" href="{root}bills/feed.rss">
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="{root}index.html">
      <span class="seal">{SEAL_SVG}</span>
      <span>
        <span class="brand-name">{legislature}</span>
        <span class="brand-sub">Bill Tracker · {esc(session['name'])}</span>
      </span>
    </a>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p>{legislature} · <a href="{root}bills/feed.rss">RSS feed</a> · <a href="{root}bills/feed.json">JSON feed</a> · <a href="{root}bills/index.json">Bill data (JSON)</a></p>
  </div>
</footer>
</body>
</html>
"""


def render_index(session, bills, built_at):
    rows = "\n".join(
        f"""      <tr>
        <td class="bill-id"><a href="{bill_path(bill)}">{esc(bill['id'])}</a></td>
        <td>{esc(bill['title'])}</td>
        <td class="nowrap">{esc(bill['sponsor'])}</td>
        <td>{pill(bill['status'])}</td>
        <td class="nowrap">{fmt_date(bill['status_date'])}</td>
        <td class="nowrap">{esc(fmt_date(bill['effective_date']))}</td>
      </tr>"""
        for bill in bills
    )
    body = f"""<div class="toolbar">
  <div>
    <h1>Bills</h1>
    <p class="updated">{len(bills)} bills · Last updated <time datetime="{built_at.isoformat()}">{fmt_timestamp(built_at)}</time></p>
  </div>
  <a class="feed-link" href="bills/feed.rss">{RSS_ICON_SVG}RSS feed</a>
</div>
<div class="table-wrap">
  <table>
    <thead>
      <tr><th scope="col">Bill</th><th scope="col">Title</th><th scope="col">Sponsor</th><th scope="col">Status</th><th scope="col">Status date</th><th scope="col">Effective date</th></tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</div>"""
    return page(session, f"Bill Tracker · {session['name']} · {session['legislature']}", body)


def render_bill(session, bill):
    history = "\n".join(
        f'      <tr><td class="nowrap">{fmt_date(h["date"])}</td><td>{esc(h["action"])}</td></tr>'
        for h in bill["history"]
    )
    sections = "\n".join(
        f'  <p id="sec-{s["number"]}"><strong>Sec. {s["number"]}. {esc(s["heading"])}.</strong> {esc(s["text"])}</p>'
        for s in bill["sections"]
    )
    topics = "".join(f"<li>{esc(topic)}</li>" for topic in bill["topics"])
    body = f"""<p class="crumbs"><a href="../index.html">← All bills</a></p>
<h1 class="bill-title"><span class="eyebrow">{esc(bill['id'])}</span> {esc(bill['title'])}</h1>
<p class="status-line">{pill(bill['status'])}</p>
<dl class="meta">
  <div><dt>Sponsor</dt><dd>{esc(bill['sponsor'])}</dd></div>
  <div><dt>Committee</dt><dd>{esc(bill['committee'])}</dd></div>
  <div><dt>Status date</dt><dd>{fmt_date(bill['status_date'])}</dd></div>
  <div><dt>Effective date</dt><dd>{esc(fmt_date(bill['effective_date']))}</dd></div>
  <div class="topics"><dt>Topics</dt><dd><ul class="tags">{topics}</ul></dd></div>
</dl>
<h2>Summary</h2>
<p class="summary">{esc(bill['summary'])}</p>
<h2>History</h2>
<div class="table-wrap history">
  <table>
    <thead><tr><th scope="col">Date</th><th scope="col">Action</th></tr></thead>
    <tbody>
{history}
    </tbody>
  </table>
</div>
<h2>Full text</h2>
<div class="full-text">
{sections}
</div>"""
    return page(session, f"{bill['id']} · {bill['title']} · {session['legislature']}", body, root="../")


def feed_items(bills):
    items = []
    for bill in sorted(bills, key=changed_at, reverse=True):
        changed = changed_at(bill)
        stamp = changed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        items.append({
            "title": f"{bill['id']} · {bill['title']} · {bill['status']}",
            "link": BASE_URL + bill_path(bill),
            "guid": f"{bill['slug']}-{slugify(bill['status'])}-{bill['status_date']}-{stamp}",
            "pub_date": changed,
            "description": (
                f"Status: {bill['status']} ({fmt_date(bill['status_date'])}). "
                f"Effective date: {fmt_date(bill['effective_date'])}. {bill['summary']}"
            ),
            "categories": bill["topics"],
        })
    return items


def render_rss(description, items, built_at):
    ET.register_namespace("atom", ATOM_NS)
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = FEED_TITLE
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(built_at)
    ET.SubElement(
        channel, f"{{{ATOM_NS}}}link", href=BASE_URL + "bills/feed.rss", rel="self", type="application/rss+xml"
    )
    for item in items:
        node = ET.SubElement(channel, "item")
        ET.SubElement(node, "title").text = item["title"]
        ET.SubElement(node, "link").text = item["link"]
        ET.SubElement(node, "guid", isPermaLink="false").text = item["guid"]
        ET.SubElement(node, "pubDate").text = format_datetime(item["pub_date"])
        ET.SubElement(node, "description").text = item["description"]
        for topic in item["categories"]:
            ET.SubElement(node, "category").text = topic
    ET.indent(rss)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode") + "\n"


def to_json(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def build_site():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    session, bills = data["session"], data["bills"]
    built_at = datetime.now(PACIFIC).replace(microsecond=0)
    description = f"Status changes for bills in the {session['name']} of the {session['legislature']}."
    items = feed_items(bills)

    outputs = {
        ROOT / "index.html": render_index(session, bills, built_at),
        BILLS_DIR / "feed.rss": render_rss(description, items, built_at),
        BILLS_DIR / "feed.json": to_json({
            "title": FEED_TITLE,
            "link": BASE_URL,
            "description": description,
            "last_build_date": built_at.isoformat(),
            "items": [dict(item, pub_date=item["pub_date"].isoformat()) for item in items],
        }),
        BILLS_DIR / "index.json": to_json({
            "session": session,
            "generated_at": built_at.isoformat(),
            "bills": [dict(bill, url=BASE_URL + bill_path(bill)) for bill in bills],
        }),
        ROOT / ".nojekyll": "",
    }
    for bill in bills:
        outputs[ROOT / bill_path(bill)] = render_bill(session, bill)

    BILLS_DIR.mkdir(exist_ok=True)
    for path, text in outputs.items():
        path.write_text(text, encoding="utf-8")
    return len(outputs), built_at


if __name__ == "__main__":
    count, built_at = build_site()
    print(f"Wrote {count} files ({fmt_timestamp(built_at)}).")
