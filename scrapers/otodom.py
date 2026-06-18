"""Scraper for otodom.pl building plot listings."""
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
        """Fetch listings from otodom.pl for all configured municipalities."""
        results: list[Listing] = []
        for municipality in MUNICIPALITIES:
            slug = _MUNICIPALITY_SLUGS.get(municipality, municipality.lower())
            url = _BASE_URL.format(municipality=slug)
            try:
                response = self._get(url)
                listings = self._parse(response.text)
                self.logger.info(
                    "otodom.pl: %d listings in %s", len(listings), municipality
                )
                results.extend(listings)
            except Exception as exc:
                self.logger.error(
                    "otodom.pl: failed to fetch %s: %s", municipality, exc
                )
        return results

    def _parse(self, html: str) -> list[Listing]:
        """Parse listings from the Next.js page payload.

        Args:
            html: Raw HTML of the search results page.

        Returns:
            List of parsed :class:`Listing` objects.
        """
        soup = BeautifulSoup(html, "lxml")
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag:
            self.logger.warning("otodom.pl: __NEXT_DATA__ not found in page")
            return []

        try:
            data = json.loads(tag.string or "")
            items: list[dict] = (
                data.get("props", {})
                    .get("pageProps", {})
                    .get("data", {})
                    .get("searchAds", {})
                    .get("items", [])
            )
        except (json.JSONDecodeError, AttributeError) as exc:
            self.logger.error("otodom.pl: JSON parse error: %s", exc)
            return []

        listings: list[Listing] = []
        for item in items:
            try:
                listing = self._parse_item(item)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                self.logger.debug("otodom.pl: skipping item %s: %s", item.get("id"), exc)
        return listings

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
            location_data.get("city", {}).get("name")
            or location_data.get("county", {}).get("name")
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
