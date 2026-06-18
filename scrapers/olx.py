"""Scraper for olx.pl building plot listings."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from config import MUNICIPALITIES
from .base import BaseScraper, Listing

_MUNICIPALITY_SLUGS: dict[str, str] = {
    "Liszki": "liszki",
    "Czernichów": "czernichow",
}

_BASE_URL = "https://www.olx.pl/nieruchomosci/dzialki/q-{municipality}/"


def _parse_price(text: str) -> float | None:
    m = re.search(r"([\d\s]+)\s*zł", text)
    if not m:
        return None
    digits = re.sub(r"\s", "", m.group(1))
    return float(digits) if digits else None


def _parse_area(text: str) -> float | None:
    m = re.search(r"([\d\s]+)\s*m²", text)
    if not m:
        return None
    digits = re.sub(r"\s", "", m.group(1))
    return float(digits) if digits else None


class OlxScraper(BaseScraper):
    """Scraper for olx.pl building plot listings.

    Uses the keyword-search URL ``/nieruchomosci/dzialki/q-{municipality}/``
    which returns server-rendered HTML cards (``data-cy='l-card'``).
    """

    def fetch_listings(self) -> list[Listing]:
        """Fetch listings from olx.pl for all configured municipalities."""
        results: list[Listing] = []
        for municipality in MUNICIPALITIES:
            slug = _MUNICIPALITY_SLUGS.get(municipality, municipality.lower())
            url = _BASE_URL.format(municipality=slug)
            try:
                response = self._get(url)
                listings = self._parse(response.text)
                self.logger.info(
                    "olx.pl: %d listings in %s", len(listings), municipality
                )
                results.extend(listings)
            except Exception as exc:
                self.logger.error(
                    "olx.pl: failed to fetch %s: %s", municipality, exc
                )
        return results

    def _parse(self, html: str) -> list[Listing]:
        """Parse listing cards from the OLX search results page.

        Args:
            html: Raw HTML of the search results page.

        Returns:
            List of parsed :class:`Listing` objects.
        """
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("[data-cy='l-card']")
        listings: list[Listing] = []
        for card in cards:
            try:
                listing = self._parse_card(card)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                self.logger.debug("olx.pl: skipping card: %s", exc)
        return listings

    def _parse_card(self, card) -> Listing | None:
        """Convert a card tag to a :class:`Listing`.

        Card structure (confirmed against live site):
          div[data-cy='l-card'][id='<numeric id>']
            [data-testid='ad-card-title'] a[href]  — relative URL + h4 title
            [data-testid='ad-price']                — "44 999 złdo negocjacji"
            [data-testid='location-date']           — "Liszki - Odświeżono dzisiaj..."
            span containing 'm²'                    — "14 000 m² - 3.21 zł/m²"

        Args:
            card: A ``[data-cy='l-card']`` div from the search results page.

        Returns:
            A :class:`Listing`, or ``None`` if required fields are missing.
        """
        listing_id = card.get("id", "").strip()
        if not listing_id:
            return None

        title_div = card.select_one("[data-testid='ad-card-title']")
        anchor = title_div.select_one("a[href]") if title_div else None
        if not anchor:
            return None

        href = anchor.get("href", "")
        url = f"https://www.olx.pl{href}" if href.startswith("/") else href
        if not url.startswith("https://"):
            return None

        h4 = card.select_one("h4")
        title = h4.get_text(strip=True) if h4 else ""

        price_tag = card.select_one("[data-testid='ad-price']")
        price = _parse_price(price_tag.get_text() if price_tag else "")

        area_span = next(
            (s for s in card.find_all("span") if "m²" in s.get_text()),
            None,
        )
        area = _parse_area(area_span.get_text() if area_span else "")

        loc_tag = card.select_one("[data-testid='location-date']")
        location = loc_tag.get_text(strip=True).split(" - ")[0] if loc_tag else ""

        return Listing(
            id=f"olx_{listing_id}",
            title=title,
            price=price,
            area_m2=area,
            location=location,
            url=url,
            source="olx.pl",
        )
