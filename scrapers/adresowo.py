"""Scraper for adresowo.pl building plot listings."""
import re

from bs4 import BeautifulSoup

from config import MUNICIPALITIES
from .base import BaseScraper, Listing

_MUNICIPALITY_SLUGS: dict[str, str] = {
    "Liszki": "liszki-gmina",
    "Czernichów": "czernichow-gmina",
}

_BASE_URL = "https://adresowo.pl/nieruchomosci/dzialki/{municipality}/"


def _parse_price(text: str) -> float | None:
    digits = re.sub(r"[^\d]", "", text)
    return float(digits) if digits else None


def _parse_area(text: str) -> float | None:
    match = re.search(r"([\d\s]+)\s*m", text)
    if match:
        raw = re.sub(r"\s", "", match.group(1))
        try:
            return float(raw)
        except ValueError:
            pass
    return None


class AdresowoScraper(BaseScraper):
    """Scraper for adresowo.pl.

    Fetches building plot listings for each configured municipality by parsing
    the HTML listing cards.
    """

    def fetch_listings(self) -> list[Listing]:
        """Fetch listings from adresowo.pl for all configured municipalities."""
        results: list[Listing] = []
        for municipality in MUNICIPALITIES:
            slug = _MUNICIPALITY_SLUGS.get(municipality, municipality.lower())
            url = _BASE_URL.format(municipality=slug)
            try:
                response = self._get(url)
                listings = self._parse(response.text)
                self.logger.info(
                    "adresowo.pl: %d listings in %s", len(listings), municipality
                )
                results.extend(listings)
            except Exception as exc:
                self.logger.error(
                    "adresowo.pl: failed to fetch %s: %s", municipality, exc
                )
        return results

    def _parse(self, html: str) -> list[Listing]:
        """Parse listing cards from the adresowo.pl search page.

        Args:
            html: Raw HTML of the search results page.

        Returns:
            List of parsed :class:`Listing` objects.
        """
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(".property-card, .listing-item, article.offer")
        listings: list[Listing] = []
        for card in cards:
            try:
                listing = self._parse_card(card)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                self.logger.debug("adresowo.pl: skipping card: %s", exc)
        return listings

    def _parse_card(self, card) -> Listing | None:
        """Convert a BeautifulSoup card tag to a :class:`Listing`.

        Args:
            card: A listing card tag from the search results.

        Returns:
            A :class:`Listing`, or ``None`` if required fields are missing.
        """
        anchor = card.select_one("a.property-title, h2 a, h3 a, .title a")
        if not anchor:
            return None

        url = anchor.get("href", "")
        if not url.startswith("https://"):
            url = f"https://adresowo.pl{url}" if url.startswith("/") else ""
        if not url.startswith("https://"):
            return None

        listing_id = url.rstrip("/").split("/")[-1]

        title = anchor.get_text(strip=True)

        price_tag = card.select_one(".price, [class*='price']")
        price = _parse_price(price_tag.get_text()) if price_tag else None

        area_tag = card.select_one(".area, [class*='area'], [class*='surface']")
        area = _parse_area(area_tag.get_text()) if area_tag else None

        location_tag = card.select_one(".location, .address, [class*='location']")
        location = location_tag.get_text(strip=True) if location_tag else ""

        return Listing(
            id=f"adresowo_{listing_id}",
            title=title,
            price=price,
            area_m2=area,
            location=location,
            url=url,
            source="adresowo.pl",
        )
