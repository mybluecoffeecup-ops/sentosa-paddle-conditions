# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A pre-paddle conditions quick reference for Austcham Paddle Club crews launching from Siloso Beach, Sentosa. It is a single static page, [index.html](index.html), deployed to GitHub Pages. There is no build step, no package manager and no framework. It also ships a web app manifest ([manifest.webmanifest](manifest.webmanifest), [icon.svg](icon.svg)) so the page can be added to a phone's home screen.

## Architecture

`index.html` is organised in three layers: HTML in `<body>`, one `<style>` block in `<head>`, and one `<script>` block at the end of `<body>`. Keep new code in that structure.

- **`CONFIG`** (top of the script) holds the club rules (CAT 1 radius, haze limit as 1-hour PM2.5), routes and durations, session times, the White Marker location and the current-direction convention. Change behaviour there first.
- **Data is fetched in the browser** from data.gov.sg (NEA lightning, 2-hr and 4-day forecasts, rainfall, wind, PM2.5, PSI), Open-Meteo (wind forecast; marine sea-level as the tide fallback) and NEA radar images. Leaflet (cdnjs) draws the radar map.
- **Tides** come from `data/tides.json`. It is generated in CI by [scripts/fetch_tides.py](scripts/fetch_tides.py), which scrapes tide-forecast.com, and is gitignored. `loadTides()` falls back to Open-Meteo modelled sea level when the file is missing, stale or too short; `pick(from, to)` chooses the source that covers each window.
- **Verdict:** only CAT 1 and haze affect Go/Hold. Wind and tide are info only.
- **Route plans** (`routePlan` / `routeHtml`) use the net current over each half of the paddle. The rule is to push into the current first and ride it home.

## Design

The look is borrowed from an Admiralty nautical chart, and the tokens at the top of the `<style>` block define it:

- **Palette:** sea-white paper, shoal blue and chart buff for fills, sounding blue for the tide curve, and chart magenta for markings ("now", the CAT 1 ring, the turnaround, focus). Dark mode is a dimmed night-chart palette.
- **Type:** Spectral italic for headings, following the chart convention of italic names for water features. Atkinson Hyperlegible Next is the body face, for reading on a phone in sun. Atkinson Hyperlegible Mono is used for numbers.
- **Status:** shown as square stamped tags where the word carries the meaning (OK, Watch, Hold, CAT 1). There are no coloured dots or pills.
- **Copy:** write UI text plainly, the way a crew captain would say it: short sentences, no em-dashes, no emoji.

## Verifying changes

There is no test suite. Serve the folder (`python3 -m http.server`) and check the following in a browser at ~375px and desktop widths, in light and dark mode:

- the verdict and each card fill in, or show a labelled "Unavailable";
- the radar animates;
- the tide chart hover works;
- session cards show route plans and mini charts;
- there is no horizontal page scroll.

Run `python3 scripts/fetch_tides.py /tmp/t.json` to check the scraper still parses tide-forecast.com.
