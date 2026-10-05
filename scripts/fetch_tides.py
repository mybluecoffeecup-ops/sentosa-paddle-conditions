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

# Fallback text parser. Matches table rows such as:
#   "High Tide 7:59 AM (Mon 05 October) 6.5 ft (1.98 m)"
#   "Low Tide 05:17 (Sat 4 October) 0.71m"
TIDE_RE = re.compile(
    r"(?P<type>High|Low)\s+Tide\s*:?\s*"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2})\s*(?P<ampm>[AaPp][Mm])?\s*"
    r"\(\s*(?:[A-Za-z]+\s+)?(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>[A-Za-z]+)\s*\)\s*"
    r"(?:-?\d+(?:\.\d+)?\s*ft\s*\(\s*)?(?P<height>-?\d+(?:\.\d+)?)\s*m\b"
)
DATUM_RE = re.compile(r"Tide Datum:\s*([A-Za-z ]+?)(?:\s+High\b|\s*$|\s{2})")


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


def tide_days(raw_html):
    """The page embeds its chart data as JSON: "tideDays": [{date, sunrise, sunset, tides: [...]}],
    with a height every 10 minutes (unix timestamps, metres) and type set on the turns."""
    i = raw_html.find('"tideDays"')
    if i < 0:
        return None
    try:
        days, _ = json.JSONDecoder().raw_decode(raw_html, raw_html.index("[", i))
        return days
    except ValueError:
        return None


def parse_json(raw_html):
    days = tide_days(raw_html)
    if not days:
        return []
    series = {}
    for day in days:
        for p in day.get("tides") or []:
            if isinstance(p.get("timestamp"), (int, float)) and isinstance(p.get("height"), (int, float)):
                series[int(p["timestamp"])] = p
    pts = [series[k] for k in sorted(series)]
    typed = [p for p in pts if p.get("type")]
    if not typed:
        # No labelled turns: find local maxima/minima in the 10-minute series.
        for a, b, c in zip(pts, pts[1:], pts[2:]):
            if b["height"] > a["height"] and b["height"] >= c["height"]:
                typed.append({**b, "type": "high"})
            elif b["height"] < a["height"] and b["height"] <= c["height"]:
                typed.append({**b, "type": "low"})
    out = []
    for p in typed:
        kind = "high" if "high" in str(p["type"]).lower() else "low" if "low" in str(p["type"]).lower() else None
        if kind:
            when = dt.datetime.fromtimestamp(p["timestamp"], SGT)
            out.append({"t": when.isoformat(), "h": round(float(p["height"]), 3), "type": kind})
    return out


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


def diagnose(raw_html):
    """Print a short excerpt of the page so a layout change can be fixed from the Actions log."""
    text = page_text(raw_html)
    title = re.search(r"(?is)<title>(.*?)</title>", raw_html)
    print(f"page: {len(raw_html)} bytes, title: {title.group(1).strip() if title else '-'}")
    for i, m in enumerate(re.finditer(r"(?i)(high|low)\s*tide", text)):
        if i >= 6:
            break
        print("text:", text[max(0, m.start() - 80):m.end() + 160])
    for i, m in enumerate(re.finditer(r"(?i)(high|low)\s*tide", raw_html)):
        if i >= 4:
            break
        print("html:", raw_html[max(0, m.start() - 300):m.end() + 500].replace("\n", " "))
    for m in re.finditer(r"(?i)\"(tides?|tideDays|extremes|heights?)\"\s*:", raw_html):
        print("json key:", raw_html[m.start():m.start() + 300].replace("\n", " "))
        break


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: fetch_tides.py <output.json>")
    raw = fetch(SOURCE_URL)
    extremes = parse_json(raw)
    source = "embedded chart data"
    if len(extremes) < 4:
        extremes, source = parse(raw), "tide table text"
    if len(extremes) < 4:
        diagnose(raw)
        sys.exit(f"only parsed {len(extremes)} tide turns from {SOURCE_URL}; page layout may have changed")
    # The source starts at midnight today, so before the first turn there is no previous one to
    # interpolate from. Add an estimated turn one tide-interval earlier (same height as the next
    # turn of that type) so early-morning checks still work off this data.
    if len(extremes) >= 3:
        first, second = extremes[0], extremes[1]
        gap = dt.datetime.fromisoformat(second["t"]) - dt.datetime.fromisoformat(first["t"])
        extremes.insert(0, {"t": (dt.datetime.fromisoformat(first["t"]) - gap).isoformat(),
                            "h": second["h"], "type": second["type"], "estimated": True})
    datum = DATUM_RE.search(page_text(raw))
    out = {
        "source": SOURCE_URL,
        "station": "Singapore (Victoria Dock)",
        "datum": datum.group(1).strip() if datum else "Mean Lower Low Water",
        "units": "m",
        "fetched_at": dt.datetime.now(SGT).isoformat(timespec="seconds"),
        "extremes": extremes,
    }
    with open(sys.argv[1], "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {len(extremes)} tide turns from {source}, {extremes[0]['t']} → {extremes[-1]['t']}")


if __name__ == "__main__":
    main()
