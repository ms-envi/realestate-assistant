"""Scraper for adresowo.pl building plot listings."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from config import MUNICIPALITIES
from .base import BaseScraper, Listing

_MUNICIPALITY_SLUGS: dict[str, str] = {
    "Liszki": "gmina-liszki",
    "Czernichów": "gmina-czernichow",
}

_BASE_URL = "https://adresowo.pl/dzialki/{municipality}/"
_MAX_PAGES = 20


class AdresowoScraper(BaseScraper):
    """Scraper for adresowo.pl.

    The site uses Tailwind utility classes so there are no stable semantic
    selectors. Instead we locate listing anchors (href starting with /o/) and
    walk up the DOM to the card container.
    """

    def fetch_listings(self) -> list[Listing]:
        """Fetch listings from adresowo.pl for all configured municipalities, across all pages."""
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
                        "adresowo.pl: %d listings on page %d in %s", len(listings), page, municipality
                    )
                    if not listings:
                        break
                    results.extend(listings)
                    page += 1
                except Exception as exc:
                    self.logger.error(
                        "adresowo.pl: failed to fetch %s page %d: %s", municipality, page, exc
                    )
                    break
        return results

    def _parse(self, html: str) -> list[Listing]:
        """Parse listings by finding /o/ anchors and walking up to their cards.

        Args:
            html: Raw HTML of the search results page.

        Returns:
            List of parsed :class:`Listing` objects.
        """
        soup = BeautifulSoup(html, "lxml")
        anchors = [a for a in soup.find_all("a", href=True) if a["href"].startswith("/o/")]
        listings: list[Listing] = []
        for anchor in anchors:
            try:
                listing = self._parse_anchor(anchor)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                self.logger.debug("adresowo.pl: skipping anchor %s: %s", anchor.get("href"), exc)
        return listings

    def _parse_anchor(self, anchor) -> Listing | None:
        """Convert a listing anchor and its card context to a :class:`Listing`.

        Card DOM structure (confirmed against live site):
        a → h2 → div.flex → div.isolate (price/area text) → div.relative (card root)

        Args:
            anchor: An ``<a>`` tag whose href starts with ``/o/``.

        Returns:
            A :class:`Listing`, or ``None`` if required fields are missing.
        """
        href = anchor["href"]
        url = f"https://adresowo.pl{href}"
        listing_id = href.rstrip("/").split("/")[-1]

        # Walk up 4 levels to the card root
        card = anchor.parent.parent.parent.parent
        card_text = card.get_text(separator="|", strip=True)

        # Price: last run of digits before "zł"
        price_match = re.search(r"([\d][\d\s]*)\|?\s*zł", card_text)
        price = float(re.sub(r"\s", "", price_match.group(1))) if price_match else None

        # Area: last run of digits before "m²"
        area_match = re.search(r"([\d][\d\s]*)\|?\s*m²", card_text)
        area = float(re.sub(r"\s", "", area_match.group(1))) if area_match else None

        # Title and location from h2 (contains the anchor)
        h2 = anchor.find_parent("h2")
        h2_text = h2.get_text(separator="|", strip=True) if h2 else anchor.get_text(strip=True)
        parts = [p.strip() for p in h2_text.split("|") if p.strip()]
        location = parts[0] if parts else ""
        title = " — ".join(parts[:2]) if len(parts) >= 2 else h2_text

        return Listing(
            id=f"adresowo_{listing_id}",
            title=title,
            price=price,
            area_m2=area,
            location=location,
            url=url,
            source="adresowo.pl",
        )
