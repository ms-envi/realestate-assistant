"""Entry point: orchestrates scraping, deduplication, and email notification."""
import logging
import sys

import notifier
import storage
from scrapers import (
    AdresowoScraper,
    GratkaScraper,
    NieruchomosciOnlineScraper,
    OlxScraper,
    OtodomScraper,
)
from scrapers.base import Listing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_SCRAPERS = [
    OtodomScraper,
    GratkaScraper,
    OlxScraper,
    NieruchomosciOnlineScraper,
    AdresowoScraper,
]


def run_scrapers() -> list[Listing]:
    """Run all scrapers, collecting results and tolerating individual failures.

    Returns:
        Combined list of listings from all scrapers that succeeded.
    """
    all_listings: list[Listing] = []
    for scraper_cls in _SCRAPERS:
        scraper = scraper_cls()
        try:
            listings = scraper.fetch_listings()
            all_listings.extend(listings)
        except Exception as exc:
            logger.error("%s failed: %s", scraper_cls.__name__, exc)
    return all_listings


def main() -> None:
    """Main entry point: scrape → deduplicate → notify."""
    logger.info("Starting realestate-assistant run")

    storage.init_db()
    seen_ids = storage.get_seen_ids()
    logger.debug("Known listings in storage: %d", len(seen_ids))

    all_listings = run_scrapers()
    logger.info("Total listings found across all scrapers: %d", len(all_listings))

    if not all_listings:
        logger.warning("No listings returned by any scraper — sending warning email")
        try:
            notifier.send_warning_email(
                "Żaden scraper nie zwrócił wyników. Sprawdź logi i strukturę stron."
            )
        except Exception as exc:
            logger.error("Failed to send warning email: %s", exc)
        sys.exit(0)

    new_listings = [l for l in all_listings if l.id not in seen_ids]
    logger.info("New listings (not seen before): %d", len(new_listings))

    if new_listings:
        try:
            notifier.send_new_listings_email(new_listings)
        except Exception as exc:
            logger.error("Failed to send notification email: %s", exc)
            sys.exit(1)
        storage.save_listings(new_listings)
    else:
        logger.info("No new listings — nothing to send")

    logger.info("Run complete")


if __name__ == "__main__":
    main()
