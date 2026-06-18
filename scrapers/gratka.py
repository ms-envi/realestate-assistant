"""Scraper for gratka.pl building plot listings."""
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from config import MUNICIPALITIES
from .base import BaseScraper, Listing

_BASE_URL = "https://gratka.pl/nieruchomosci/sprzedaz/dzialki-budowlane"


def _build_url(municipality: str) -> str:
    params = urlencode({"lokalizacja_miejscowosc_core": municipality})
    return f"{_BASE_URL}?{params}"


def _parse_price(text: str) -> float | None:
    """Extract a numeric price from a string like '250 000 zł'."""
    digits = re.sub(r"[^\d]", "", text)
    return float(digits) if digits else None


def _parse_area(text: str) -> float | None:
    """Extract area in m² from a string like '1 200 m²'."""
    match = re.search(r"[\d\s]+", text)
    if match:
        digits = re.sub(r"\s", "", match.group())
        return float(digits) if digits else None
    return None


class GratkaScraper(BaseScraper):
    """Scraper for gratka.pl.

    Fetches building plot listings by querying the site's search with the
    municipality name and parsing the returned HTML.
    """

    def fetch_listings(self) -> list[Listing]:
        """Fetch listings from gratka.pl for all configured municipalities."""
        results: list[Listing] = []
        for municipality in MUNICIPALITIES:
            url = _build_url(municipality)
            try:
                response = self._get(url)
                listings = self._parse(response.text)
                self.logger.info(
                    "gratka.pl: %d listings in %s", len(listings), municipality
                )
                results.extend(listings)
            except Exception as exc:
                self.logger.error(
                    "gratka.pl: failed to fetch %s: %s", municipality, exc
                )
        return results

    def _parse(self, html: str) -> list[Listing]:
        """Parse listing cards from the search results page.

        Args:
            html: Raw HTML of the search results page.

        Returns:
            List of parsed :class:`Listing` objects.
        """
        soup = BeautifulSoup(html, "lxml")
        articles = soup.select("article.offer-item, article.listing__item")
        listings: list[Listing] = []
        for article in articles:
            try:
                listing = self._parse_article(article)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                self.logger.debug("gratka.pl: skipping article: %s", exc)
        return listings

    def _parse_article(self, article) -> Listing | None:
        """Convert a BeautifulSoup article tag to a :class:`Listing`.

        Args:
            article: A ``<article>`` tag from the search results.

        Returns:
            A :class:`Listing`, or ``None`` if required fields are missing.
        """
        title_tag = article.select_one("h2 a, .offer-item__title a, .listing__title a")
        if not title_tag:
            return None

        url = title_tag.get("href", "")
        if not url.startswith("https://"):
            url = f"https://gratka.pl{url}" if url.startswith("/") else ""
        if not url.startswith("https://"):
            return None

        listing_id = article.get("data-id") or article.get("id") or url.rstrip("/").split("/")[-1]

        price_tag = article.select_one(".offer-item__price, .listing__price")
        price = _parse_price(price_tag.get_text()) if price_tag else None

        area_tag = article.select_one("[data-testid='area'], .offer-item__area, .listing__area")
        area = _parse_area(area_tag.get_text()) if area_tag else None

        location_tag = article.select_one(".offer-item__location, .listing__location, address")
        location = location_tag.get_text(strip=True) if location_tag else ""

        return Listing(
            id=f"gratka_{listing_id}",
            title=title_tag.get_text(strip=True),
            price=price,
            area_m2=area,
            location=location,
            url=url,
            source="gratka.pl",
        )
