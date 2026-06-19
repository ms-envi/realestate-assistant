"""Entry point: orchestrates scraping, deduplication, and email notification."""
import logging
import sys

import notifier
import storage
from config import ALLOWED_LOCATIONS, FILTER_EXEMPT_LOCATIONS, MAX_PRICE, MIN_AREA_M2
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


def passes_filter(listing: Listing) -> bool:
    """Return True if the listing should be included after applying all filters.

    Listings in exempt locations (Rączna, Ściejowice) bypass price/area checks.
    All other listings must have a location matching one of the known villages in
    gmina Liszki or gmina Czernichów, and must satisfy price/area thresholds.
    Listings with unknown price or area pass those thresholds — we don't penalise
    missing data.
    """
    location = listing.location.lower()

    if any(exempt.lower() in location for exempt in FILTER_EXEMPT_LOCATIONS):
        return True

    if not any(allowed.lower() in location for allowed in ALLOWED_LOCATIONS):
        return False

    if listing.price is not None and listing.price > MAX_PRICE:
        return False

    if listing.area_m2 is not None and listing.area_m2 < MIN_AREA_M2:
        return False

    return True


def is_price_drop(listing: Listing, seen_prices: dict) -> bool:
    """Return True if the listing was seen before and its price has dropped.

    Args:
        listing: Current listing data from the scraper.
        seen_prices: Mapping of listing ID to last known price from storage.
    """
    last_price = seen_prices.get(listing.id)
    return (
        listing.id in seen_prices
        and listing.price is not None
        and last_price is not None
        and listing.price < last_price
    )


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
    seen_prices = storage.get_seen_prices()
    logger.debug("Known listings in storage: %d", len(seen_prices))

    all_listings = run_scrapers()
    logger.info("Total listings found across all scrapers: %d", len(all_listings))

    filtered_listings = [l for l in all_listings if passes_filter(l)]
    logger.info("After filters: %d listings", len(filtered_listings))

    if not all_listings:
        logger.warning("No listings returned by any scraper — sending warning email")
        try:
            notifier.send_warning_email(
                "Żaden scraper nie zwrócił wyników. Sprawdź logi i strukturę stron."
            )
        except Exception as exc:
            logger.error("Failed to send warning email: %s", exc)
        sys.exit(0)

    new_listings = [l for l in filtered_listings if l.id not in seen_prices]
    cheaper_listings = [l for l in filtered_listings if is_price_drop(l, seen_prices)]
    logger.info("New listings: %d, price drops: %d", len(new_listings), len(cheaper_listings))

    to_report = new_listings + cheaper_listings
    if to_report:
        try:
            notifier.send_new_listings_email(
                to_report,
                price_drop_ids=frozenset(l.id for l in cheaper_listings),
            )
        except Exception as exc:
            logger.error("Failed to send notification email: %s", exc)
            sys.exit(1)
        storage.save_listings(new_listings)
        for listing in cheaper_listings:
            storage.update_listing_price(listing.id, listing.price)
    else:
        logger.info("No new listings or price drops — nothing to send")

    logger.info("Run complete")


if __name__ == "__main__":
    main()
