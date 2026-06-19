"""Scraper for otodom.pl building plot listings."""
from __future__ import annotations

import json

from bs4 import BeautifulSoup

from config import MUNICIPALITIES
from .base import BaseScraper, Listing

# otodom uses ASCII slugs in URLs; diacritics are stripped
_MUNICIPALITY_SLUGS: dict[str, str] = {
    "Liszki": "liszki",
    "Czernichów": "czernichow",
}

_BASE_URL = (
    "https://www.otodom.pl/pl/oferty/sprzedaz/dzialka"
    "/malopolskie/powiat-krakowski/{municipality}"
)
_LISTING_URL = "https://www.otodom.pl/pl/oferta/{slug}"


class OtodomScraper(BaseScraper):
    """Scraper for otodom.pl.

    Fetches building plot listings for each configured municipality.
    The page embeds all listing data as JSON inside a ``<script id="__NEXT_DATA__">``
    tag — no separate API call is needed.
    """

    def fetch_listings(self) -> list[Listing]:
        """Fetch listings from otodom.pl for all configured municipalities, across all pages."""
        results: list[Listing] = []
        for municipality in MUNICIPALITIES:
            slug = _MUNICIPALITY_SLUGS.get(municipality, municipality.lower())
            base_url = _BASE_URL.format(municipality=slug)
            page = 1
            while True:
                url = base_url if page == 1 else f"{base_url}?page={page}"
                try:
                    response = self._get(url)
                    listings = self._parse(response.text)
                    total = self._parse_total_pages(response.text)
                    self.logger.info(
                        "otodom.pl: %d listings on page %d/%d in %s",
                        len(listings), page, total, municipality,
                    )
                    results.extend(listings)
                    if page >= total:
                        break
                    page += 1
                except Exception as exc:
                    self.logger.error(
                        "otodom.pl: failed to fetch %s page %d: %s", municipality, page, exc
                    )
                    break
        return results

    def _parse_next_data(self, html: str) -> dict:
        """Parse the ``__NEXT_DATA__`` JSON embedded in the page.

        Args:
            html: Raw HTML of the search results page.

        Returns:
            Parsed JSON dict, or ``{}`` on any failure.
        """
        soup = BeautifulSoup(html, "lxml")
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag:
            self.logger.warning("otodom.pl: __NEXT_DATA__ not found in page")
            return {}
        try:
            return json.loads(tag.string or "")
        except (json.JSONDecodeError, AttributeError) as exc:
            self.logger.error("otodom.pl: JSON parse error: %s", exc)
            return {}

    def _parse(self, html: str) -> list[Listing]:
        """Parse listings from the Next.js page payload.

        Args:
            html: Raw HTML of the search results page.

        Returns:
            List of parsed :class:`Listing` objects.
        """
        data = self._parse_next_data(html)
        items: list[dict] = (
            data.get("props", {})
                .get("pageProps", {})
                .get("data", {})
                .get("searchAds", {})
                .get("items", [])
        )

        listings: list[Listing] = []
        for item in items:
            try:
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                self.logger.debug("otodom.pl: skipping item %s: %s", item.get("id"), exc)
        return listings

    def _parse_total_pages(self, html: str) -> int:
        """Extract the total number of result pages from the page payload.

        Args:
            html: Raw HTML of the search results page.

        Returns:
            Total page count, or 1 when the field is absent or unparseable.
        """
        data = self._parse_next_data(html)
        pagination = (
            data.get("props", {})
                .get("pageProps", {})
                .get("data", {})
                .get("searchAds", {})
                .get("pagination", {})
        )
        return int(pagination.get("totalPages", 1))

    def _parse_item(self, item: dict) -> Listing | None:
        """Convert a raw JSON item to a :class:`Listing`.

        Args:
            item: Dict from the ``searchAds.items`` array.

        Returns:
            A :class:`Listing`, or ``None`` if the item is unusable.
        """
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            return None

        slug = item.get("slug", "")
        url = _LISTING_URL.format(slug=slug) if slug else ""
        if not url.startswith("https://"):
            return None

        price_raw = (item.get("totalPrice") or {}).get("value")
        price = float(price_raw) if price_raw is not None else None

        location_data = item.get("location", {}).get("address", {})
        location = (
            (location_data.get("city") or {}).get("name")
            or (location_data.get("county") or {}).get("name")
            or ""
        )

        return Listing(
            id=f"otodom_{item_id}",
            title=item.get("title", ""),
            price=price,
            area_m2=item.get("areaInSquareMeters"),
            location=location,
            url=url,
            source="otodom.pl",
        )
