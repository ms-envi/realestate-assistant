# 🏠 Real Estate Assistant

[![Tests](https://github.com/ms-envi/realestate-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/ms-envi/realestate-assistant/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ms-envi/realestate-assistant/graph/badge.svg)](https://codecov.io/gh/ms-envi/realestate-assistant)

A personal agent that monitors building plot listings in the **Liszki** and **Czernichów** municipalities near Kraków. Runs daily, finds new listings, and sends a summary email — no duplicates, no noise.

## What it does

- Scrapes five portals: **otodom.pl**, **gratka.pl**, **olx.pl**, **nieruchomosci-online.pl**, **adresowo.pl**
- Filters by location (only villages in the two target gminas), price (≤ 500 000 zł), and area (≥ 1 500 m²)
- Tracks seen listings in SQLite — only new ones appear in the email
- Re-reports any listing whose **price has dropped**, highlighted in red in the email
- Sends a single daily HTML email via [Resend](https://resend.com)

## Setup

```bash
pip install -r requirements.txt

export RESEND_API_KEY=...
export RESEND_FROM=alerts@yourdomain.com
export NOTIFY_EMAIL=you@example.com

python main.py
```

Intended to run via cron once a day:

```
0 5 * * * cd /path/to/realestate-assistant && python main.py
```

## Project structure

```
scrapers/        one module per portal, all inherit BaseScraper
notifier.py      builds and sends the HTML email
storage.py       SQLite deduplication + price tracking
main.py          orchestrates scrape → filter → notify
config.py        municipalities, thresholds, allowed villages
```

## Running tests

```bash
pytest
```

Coverage report is generated in `htmlcov/` and uploaded to Codecov on every push.
