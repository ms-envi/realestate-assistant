"""Scraper for gratka.pl building plot listings."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from config import MUNICIPALITIES
from .base import BaseScraper, Listing

_MUNICIPALITY_SLUGS: dict[str, str] = {
    "Liszki": "gmina-liszki",
    "Czernichów": "gmina-czernichow",
}

_BASE_URL = "https://gratka.pl/nieruchomosci/{municipality}"
_MAX_PAGES = 20


def _parse_price(text: str) -> float | None:
    digits = re.sub(r"[^\d]", "", text)
    return float(digits) if digits else None


def _parse_area(text: str) -> float | None:
    digits = re.sub(r"[^\d]", "", text.split("m")[0])
    return float(digits) if digits else None


class GratkaScraper(BaseScraper):
    """Scraper for gratka.pl.

    Fetches all listings for the municipality page and filters to plots
    (działka) by checking the listing URL slug.
    """

    def fetch_listings(self) -> list[Listing]:
        """Fetch plot listings from gratka.pl for all configured municipalities, across all pages."""
        results: list[Listing] = []
        for municipality in MUNICIPALITIES:
            slug = _MUNICIPALITY_SLUGS.get(municipality, municipality.lower())
            base_url = _BASE_URL.format(municipality=slug)
            page = 1
            while page <= _MAX_PAGES:
                url = base_url if page == 1 else f"{base_url}?page={page}"
                try:
                    response = self._get(url)
                    listings = self._parse(response.text)
                    self.logger.info(
                        "gratka.pl: %d listings on page %d in %s", len(listings), page, municipality
                    )
                    if not listings:
                        break
                    results.extend(listings)
                    page += 1
                except Exception as exc:
                    self.logger.error(
                        "gratka.pl: failed to fetch %s page %d: %s", municipality, page, exc
                    )
                    break
        return results

    def _parse(self, html: str) -> list[Listing]:
        """Parse plot cards from the municipality listing page.

        Args:
            html: Raw HTML of the municipality listings page.

        Returns:
            List of parsed :class:`Listing` objects (plots only).
        """
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(".card")
        listings: list[Listing] = []
        for card in cards:
            try:
                listing = self._parse_card(card)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                self.logger.debug("gratka.pl: skipping card: %s", exc)
        return listings

    def _parse_card(self, card) -> Listing | None:
        """Convert a card tag to a :class:`Listing`, or ``None`` if not a plot.

        Confirmed card structure (live site):
          a[data-cy='propertyUrl']            — relative href (contains 'dzialka' for plots)
          a.property-card__link               — accessible title text (includes area, price, location)
          span.property-card__price--main     — price "2 499 000 zł"
          span (no class) containing m²       — area "17 000 m²"

        Args:
            card: A ``.card`` div from the search results page.

        Returns:
            A :class:`Listing`, or ``None`` if the card is not a plot or is unusable.
        """
        url_tag = card.select_one("a[data-cy='propertyUrl']")
        if not url_tag:
            return None

        href = url_tag.get("href", "")
        # Only process plot listings
        if "dzialka" not in href:
            return None

        url = f"https://gratka.pl{href}" if href.startswith("/") else href
        if not url.startswith("https://"):
            return None

        listing_id = href.rstrip("/").split("/")[-1]

        # Accessible link text: "Title N m² PRICE Location"
        title_tag = card.select_one("a.property-card__link")
        full_text = title_tag.get_text(strip=True) if title_tag else ""

        # Extract price from dedicated span
        price_tag = card.select_one("span.property-card__price--main")
        price = _parse_price(price_tag.get_text()) if price_tag else None

        # Area: span with no class whose text ends with m²
        area_tag = next(
            (s for s in card.find_all("span") if not s.get("class") and "m²" in s.get_text()),
            None,
        )
        area = _parse_area(area_tag.get_text()) if area_tag else None

        # Location: last comma-separated segments of the accessible text
        # Format: "...title... N m² PRICE city, gmina, powiat, województwo"
        location_match = re.search(r"\d[\d\s]*zł\s+(.+)$", full_text)
        location = location_match.group(1).strip() if location_match else ""

        # Title: everything before the area part
        title_match = re.match(r"^(.+?)\s+\d[\d\s]*m²", full_text)
        title = title_match.group(1).strip() if title_match else full_text[:80]

        return Listing(
            id=f"gratka_{listing_id}",
            title=title,
            price=price,
            area_m2=area,
            location=location,
            url=url,
            source="gratka.pl",
        )
