#!/usr/bin/env python3
"""Scrape high/low tide predictions for Singapore (Victoria Dock) from
tide-forecast.com and write them as JSON for the Sentosa conditions page.

Runs in GitHub Actions before each Pages deploy (see
.github/workflows/deploy.yml). Standard library only.

Usage: python3 fetch_tides.py <output.json>

Exits non-zero (and leaves any existing output file untouched) if fewer than
four tide turns are parsed, so a layout change on the source site never
overwrites good data with an empty file. The page falls back to the
Open-Meteo modelled sea level when this file is missing or stale.
"""
import datetime as dt
import html
import json
import re
import sys
import urllib.request

SOURCE_URL = "https://www.tide-forecast.com/tide/Singapore-Victoria-Dock/tide-times"
SGT = dt.timezone(dt.timedelta(hours=8))
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}

# Matches rows such as:
#   "High Tide 12:34 AM (Sat 04 October) 2.91 m (9.55 ft)"
#   "Low Tide 05:17 (Sat 4 October) 0.71m"
TIDE_RE = re.compile(
    r"(?P<type>High|Low)\s+Tide\s*:?\s*"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>[AaPp][Mm])?\s*"
    r"\(\s*(?:[A-Za-z]+\s+)?(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>[A-Za-z]+)\s*\)\s*"
    r"(?P<height>-?\d+(?:\.\d+)?)\s*m\b"
)


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "SentosaPaddleConditions/1.0 (+https://mybluecoffeecup-ops.github.io/sentosa-paddle-conditions/)",
        "Accept-Language": "en",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def page_text(raw_html):
    raw_html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw_html)
    text = re.sub(r"<[^>]+>", " ", raw_html)
    return re.sub(r"\s+", " ", html.unescape(text))


def parse(raw_html, today=None):
    today = today or dt.datetime.now(SGT).date()
    seen = {}
    for m in TIDE_RE.finditer(page_text(raw_html)):
        month = MONTHS.get(m["month"].lower())
        if not month:
            continue
        hour, minute = int(m["hour"]), int(m["minute"])
        if m["ampm"]:
            hour = hour % 12 + (12 if m["ampm"].lower() == "pm" else 0)
        # The page shows day + month only; pick the year closest to today
        # so a table spanning New Year lands in the right year.
        year = min((today.year - 1, today.year, today.year + 1),
                   key=lambda y: abs((dt.date(y, month, 1) - today).days))
        when = dt.datetime(year, month, int(m["day"]), hour, minute, tzinfo=SGT)
        # The same turn can appear in several tables on the page; dedupe by time.
        seen[when] = {"t": when.isoformat(), "h": float(m["height"]), "type": m["type"].lower()}
    return [seen[k] for k in sorted(seen)]


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: fetch_tides.py <output.json>")
    extremes = parse(fetch(SOURCE_URL))
    if len(extremes) < 4:
        sys.exit(f"only parsed {len(extremes)} tide turns from {SOURCE_URL}; page layout may have changed")
    out = {
        "source": SOURCE_URL,
        "station": "Singapore (Victoria Dock)",
        "datum": "chart datum",
        "units": "m",
        "fetched_at": dt.datetime.now(SGT).isoformat(timespec="seconds"),
        "extremes": extremes,
    }
    with open(sys.argv[1], "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {len(extremes)} tide turns, {extremes[0]['t']} → {extremes[-1]['t']}")


if __name__ == "__main__":
    main()
