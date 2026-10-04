# Sentosa Paddle Conditions

A pre-paddle quick reference for crews launching from **Siloso Beach, Sentosa**, built for Austcham Paddle Club Singapore. Plain HTML/CSS/JS in a single file, with no build step and no dependencies. It is hosted on GitHub Pages.

**Live site:** https://mybluecoffeecup-ops.github.io/sentosa-paddle-conditions/

On a phone, use **Add to Home Screen** to get an app-style icon that opens full screen.

## What it shows

A **Right now** view plus forecasts for the next club sessions (Tue 6am and Thu 6am for the 10 km route; Sat 8am and Sun 4pm for the islands loop):

- **Go / Hold verdict on the club rules.** No paddling during a CAT 1 lightning alert, or when the southern 24-hr PSI is above 120. CAT 1 is modelled on the myENV lightning alert: cloud-to-ground lightning, or a thundery / heavy-rain 2-hr forecast, within 6 km of Siloso.
- **Lightning & rain.** Strikes in the last 30 min with distance from Siloso and the earliest all-clear time, plus NEA 2-hr forecasts for nearby areas, the nearest rain gauge, and an animated NEA rain radar showing the 6 km CAT 1 ring, the White Marker and recent strikes.
- **Haze.** 24-hr PSI and 1-hr PM2.5 for the southern region.
- **Tide, current & route plan.** Rising/falling, height, next turn, and a 3-day tide curve with night shading and session markers. Route advice follows the club rule of pushing into the current first and riding it home (falling tide, E→W current → push East):
  - **10 km White Marker** (out and back East, ~1h15): whether each leg has the current with or against it, flagged ✓ Ideal or ✗ Hard finish.
  - **Around the islands** (up to 2.5 hrs): which way round to go so you finish with the current.
  - The advice uses the net current over each half of the paddle, so a tide turning mid-paddle is accounted for.
- **Wind** (info only; there's no club wind limit). Open-Meteo forecast for Siloso, the nearest NEA station observation, and an on-demand Windy map.
- **Session cards.** Tide and current at the start, the route plan, a mini tide chart of the paddle window, forecast wind and rain chance, and the NEA 4-day outlook. CAT 1 and haze are only called on the day.

Rules, routes, durations, session times and the current-direction convention all live in the `CONFIG` object at the top of the `<script>` in `index.html`.

## Data sources

| Data | Source | How |
|---|---|---|
| Tide turns | [tide-forecast.com — Victoria Dock](https://www.tide-forecast.com/tide/Singapore-Victoria-Dock/tide-times) | Scraped by `scripts/fetch_tides.py` during each deploy into `data/tides.json` |
| Tide fallback | [Open-Meteo Marine](https://open-meteo.com/en/docs/marine-weather-api) sea level | In the browser, when `tides.json` is missing, stale, or doesn't reach far enough ahead |
| Lightning, 2-hr & 4-day forecasts, rainfall, wind obs, PSI | NEA via [data.gov.sg](https://data.gov.sg/) real-time APIs | In the browser, refreshed every 5 min |
| Rain radar | [NEA rain areas](https://www.nea.gov.sg/weather/rain-areas) | 5-minute radar images |
| Wind forecast | [Open-Meteo](https://open-meteo.com/) | In the browser |

## Running locally

```bash
git clone https://github.com/mybluecoffeecup-ops/sentosa-paddle-conditions.git
cd sentosa-paddle-conditions
python3 -m http.server 8000   # then open http://localhost:8000
```

Locally there's no `data/tides.json`, so tides use the modelled fallback (the page labels this). To try the scraper:

```bash
python3 scripts/fetch_tides.py data/tides.json
```

## Deployment

[.github/workflows/deploy.yml](.github/workflows/deploy.yml) deploys to GitHub Pages:

- **Triggers:** every push to `main`, every 3 hours (so tide data stays fresh), and manually from the Actions tab.
- **Tide scrape:** the workflow scrapes tides first. That step is allowed to fail without blocking the deploy.
- **One-time setup:** in the repo's **Settings → Pages**, set **Source** to **GitHub Actions**.

GitHub pauses scheduled workflows after 60 days without repo activity. If tides start showing as "modelled", re-enable the workflow in the Actions tab.
