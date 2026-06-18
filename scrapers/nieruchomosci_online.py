"""Scraper for nieruchomosci-online.pl building plot listings."""
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from config import MUNICIPALITIES
from .base import BaseScraper, Listing

_BASE_URL = "https://www.nieruchomosci-online.pl/wyniki,dzialki-budowlane,sprzedaz"

_MUNICIPALITY_PARAMS: dict[str, str] = {
    "Liszki": "liszki",
    "Czernichów": "czernichow",
}


def _build_url(municipality: str) -> str:
    slug = _MUNICIPALITY_PARAMS.get(municipality, municipality.lower())
    return f"{_BASE_URL}/{slug}.html"


def _parse_price(text: str) -> float | None:
    digits = re.sub(r"[^\d]", "", text)
    return float(digits) if digits else None


def _parse_area(text: str) -> float | None:
    match = re.search(r"([\d\s,]+)\s*m", text)
    if match:
        raw = re.sub(r"[\s,]", "", match.group(1))
        try:
            return float(raw)
        except ValueError:
            pass
    return None


class NieruchomosciOnlineScraper(BaseScraper):
    """Scraper for nieruchomosci-online.pl.

    Parses HTML listing cards from the search results page.
    """

    def fetch_listings(self) -> list[Listing]:
        """Fetch listings from nieruchomosci-online.pl for all configured municipalities."""
        results: list[Listing] = []
        for municipality in MUNICIPALITIES:
            url = _build_url(municipality)
            try:
                response = self._get(url)
                listings = self._parse(response.text)
                self.logger.info(
                    "nieruchomosci-online.pl: %d listings in %s", len(listings), municipality
                )
                results.extend(listings)
            except Exception as exc:
                self.logger.error(
                    "nieruchomosci-online.pl: failed to fetch %s: %s", municipality, exc
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
        cards = soup.select(".single-offer, .offer-card, article.listing")
        listings: list[Listing] = []
        for card in cards:
            try:
                listing = self._parse_card(card)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                self.logger.debug("nieruchomosci-online.pl: skipping card: %s", exc)
        return listings

    def _parse_card(self, card) -> Listing | None:
        """Convert a BeautifulSoup card tag to a :class:`Listing`.

        Args:
            card: A listing card tag from the search results.

        Returns:
            A :class:`Listing`, or ``None`` if required fields are missing.
        """
        anchor = card.select_one("a.offer-title, h2 a, h3 a, .title a")
        if not anchor:
            return None

        url = anchor.get("href", "")
        if not url.startswith("https://"):
            url = f"https://www.nieruchomosci-online.pl{url}" if url.startswith("/") else ""
        if not url.startswith("https://"):
            return None

        listing_id = url.rstrip("/").split("/")[-1].split(",")[-1]

        title = anchor.get_text(strip=True)

        price_tag = card.select_one(".price, .offer-price, [class*='price']")
        price = _parse_price(price_tag.get_text()) if price_tag else None

        area_tag = card.select_one(".area, .offer-area, [class*='area'], [class*='surface']")
        area = _parse_area(area_tag.get_text()) if area_tag else None

        location_tag = card.select_one(".location, .address, [class*='location']")
        location = location_tag.get_text(strip=True) if location_tag else ""

        return Listing(
            id=f"nieruchomosci_online_{listing_id}",
            title=title,
            price=price,
            area_m2=area,
            location=location,
            url=url,
            source="nieruchomosci-online.pl",
        )
