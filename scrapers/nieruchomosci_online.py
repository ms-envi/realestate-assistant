"""Scraper for nieruchomosci-online.pl building plot listings."""
from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup

from config import ALLOWED_LOCATIONS
from .base import BaseScraper, Listing

# nieruchomosci-online.pl uses a per-village subdomain (e.g. raczna.nieruchomosci-online.pl),
# NOT a per-municipality one. We search every village in ALLOWED_LOCATIONS.
_BASE_URL = "https://{subdomain}.nieruchomosci-online.pl/dzialki/"
_MAX_PAGES = 20


def _to_slug(name: str) -> str:
    """Convert a Polish place name to the nieruchomosci-online.pl subdomain format.

    E.g. 'Rączna' → 'raczna', 'Dąbrowa Szlachecka' → 'dabrowa-szlachecka'.
    """
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_ = nfkd.encode("ascii", "ignore").decode()
    return re.sub(r"\s+", "-", ascii_.strip().lower())


def _parse_price(text: str) -> float | None:
    digits = re.sub(r"[^\d]", "", text)
    return float(digits) if digits else None


def _parse_area(text: str) -> float | None:
    digits = re.sub(r"[^\d,.]", "", text.replace(",", ".").split("m")[0])
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


class NieruchomosciOnlineScraper(BaseScraper):
    """Scraper for nieruchomosci-online.pl.

    Searches each village in ALLOWED_LOCATIONS on its own subdomain.
    Stops paginating when a page returns the same listing IDs as the previous
    page (the site silently mirrors page 1 for all ?page=N requests).
    """

    def fetch_listings(self) -> list[Listing]:
        """Fetch listings from nieruchomosci-online.pl for all configured villages."""
        results: list[Listing] = []
        for village in ALLOWED_LOCATIONS:
            subdomain = _to_slug(village)
            base_url = _BASE_URL.format(subdomain=subdomain)
            page = 1
            prev_ids: frozenset[str] = frozenset()
            while page <= _MAX_PAGES:
                url = base_url if page == 1 else f"{base_url}?page={page}"
                try:
                    response = self._get(url)
                    listings = self._parse(response.text)
                    curr_ids = frozenset(l.id for l in listings)
                    self.logger.info(
                        "nieruchomosci-online.pl: %d listings on page %d in %s",
                        len(listings), page, village,
                    )
                    if not listings or curr_ids == prev_ids:
                        break
                    results.extend(listings)
                    prev_ids = curr_ids
                    page += 1
                except Exception as exc:
                    self.logger.error(
                        "nieruchomosci-online.pl: failed to fetch %s page %d: %s",
                        village, page, exc,
                    )
                    break
        return results

    def _parse(self, html: str) -> list[Listing]:
        """Parse listing tiles from the village subdomain page.

        Args:
            html: Raw HTML of the plots listing page.

        Returns:
            List of parsed :class:`Listing` objects.
        """
        soup = BeautifulSoup(html, "lxml")
        # Exclude promoted investment tiles
        tiles = soup.select(".tile:not(.tile-investment)")
        listings: list[Listing] = []
        for tile in tiles:
            try:
                listing = self._parse_tile(tile)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                self.logger.debug(
                    "nieruchomosci-online.pl: skipping tile %s: %s",
                    tile.get("data-id"), exc,
                )
        return listings

    def _parse_tile(self, tile) -> Listing | None:
        """Convert a tile tag to a :class:`Listing`.

        Tile structure (confirmed against live site):
          h2.name > a[href]          — title + URL
          p.title-a > span:first     — price (e.g. "8 200 000 zł")
          span.area                  — area  (e.g. "8 200 m²")
          p.province > span          — city name

        Args:
            tile: A ``.tile`` div from the search results page.

        Returns:
            A :class:`Listing`, or ``None`` if required fields are missing.
        """
        listing_id = tile.get("data-id", "").strip()

        anchor = tile.select_one("h2.name a[href]")
        if not anchor:
            return None
        url = anchor.get("href", "")
        if not url.startswith("https://"):
            return None

        title = anchor.get_text(strip=True)

        # Price: first <span> inside .title-a (second span is price-per-m²)
        price_tag = tile.select_one("p.title-a span")
        price = _parse_price(price_tag.get_text()) if price_tag else None

        area_tag = tile.select_one("span.area")
        area = _parse_area(area_tag.get_text()) if area_tag else None

        location_tag = tile.select_one("p.province span")
        location = location_tag.get_text(strip=True).rstrip(",") if location_tag else ""

        return Listing(
            id=f"nieruchomosci_online_{listing_id}",
            title=title,
            price=price,
            area_m2=area,
            location=location,
            url=url,
            source="nieruchomosci-online.pl",
        )
