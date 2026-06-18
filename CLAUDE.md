# realestate-assistant

Agent that monitors building plot listings in the Kraków area. Scrapes several services daily and sends an email with new listings.

## Project goal

Track new building plot listings in the municipalities: Liszki, Czernichów. The agent runs once a day (e.g. via cron), compares results with the previous run, and sends an email only with new listings.

## Stack

- Python 3.11
- `requests` + `BeautifulSoup` — scraping
- `smtplib` — sending emails
- `sqlite3` (stdlib) or JSON file — state storage (already seen listings)

## Services to scrape

| Service | URL |
|---------|-----|
| otodom.pl | plots, filters: municipality/location |
| gratka.pl | building plots |
| olx.pl | real estate → plots |
| nieruchomosci-online.pl | plots |
| adresowo.pl | building plots |

Each service has a separate scraper module in `scrapers/`.

## Project structure

```
realestate-assistant/
├── scrapers/
│   ├── __init__.py
│   ├── base.py          # BaseScraper — shared logic (retry, timeout, User-Agent)
│   ├── otodom.py
│   ├── gratka.py
│   ├── olx.py
│   ├── nieruchomosci_online.py
│   └── adresowo.py
├── notifier.py          # sending email via smtplib
├── storage.py           # tracking already seen listings
├── main.py              # entry point, orchestrates scraping + notify
├── config.py            # constants: municipalities, keywords, SMTP config (from env)
├── requirements.txt
└── CLAUDE.md
```

## Code conventions

- **snake_case** for variable, function, and module names
- **Docstrings** on every class and public function (Google style)
- **Logging via `logging`** — do not use `print()` in production code; levels: DEBUG for scraping details, INFO for flow, WARNING/ERROR for problems
- Sensitive config (SMTP password, email address) via environment variables only, never hardcoded
- Every scraper inherits from `BaseScraper` and implements the method `fetch_listings() -> list[Listing]`
- `Listing` is a dataclass with fields: `id`, `title`, `price`, `area_m2`, `location`, `url`, `source`, `seen_at`

## Error handling

- A failure in one scraper must not stop the others — catch exceptions per-scraper, log, and continue
- Retry with backoff for network errors (default 3 attempts)
- If no scraper returns results, send a warning email instead of an empty message
- Timeout on every HTTP request: 15s

## Running

```bash
# environment variables
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=...
export SMTP_PASSWORD=...
export NOTIFY_EMAIL=...

python main.py
```

Intended to run via `cron` once a day, e.g. at 7:00.

## Testing scrapers

When developing a new scraper:
1. Run it in isolation and save the raw HTML to a fixture file
2. Write tests against the fixture, not live requests — live scraping is fragile
3. Verify that `Listing.url` is absolute (starts with `https://`)
