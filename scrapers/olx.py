"""Scraper for olx.pl building plot listings."""
from __future__ import annotations

import json
import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from config import MUNICIPALITIES
from .base import BaseScraper, Listing

# Category path for real estate → building plots
_BASE_URL = "https://www.olx.pl/nieruchomosci/dzialki/malopolskie/"

_MUNICIPALITY_SLUGS: dict[str, str] = {
    "Liszki": "liszki",
    "Czernichów": "czernichow",
}


def _build_url(municipality: str) -> str:
    slug = _MUNICIPALITY_SLUGS.get(municipality, municipality.lower())
    params = urlencode({"search[filter_enum_type][0]": "budowlana"})
    return f"{_BASE_URL}{slug}/?{params}"


def _parse_price(raw: str | None) -> float | None:
    if not raw:
        return None
    digits = re.sub(r"[^\d]", "", raw)
    return float(digits) if digits else None


class OlxScraper(BaseScraper):
    """Scraper for olx.pl.

    OLX embeds listing data as JSON in a ``<script id="__NEXT_DATA__">`` tag.
    Falls back to HTML parsing if the JSON structure is not found.
    """

    def fetch_listings(self) -> list[Listing]:
        """Fetch listings from olx.pl for all configured municipalities."""
        results: list[Listing] = []
        for municipality in MUNICIPALITIES:
            url = _build_url(municipality)
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
        """Parse listings from the OLX page, preferring the JSON payload.

        Args:
            html: Raw HTML of the search results page.

        Returns:
            List of parsed :class:`Listing` objects.
        """
        soup = BeautifulSoup(html, "lxml")
        tag = soup.find("script", id="__NEXT_DATA__")
        if tag:
            try:
                data = json.loads(tag.string or "")
                offers = (
                    data.get("props", {})
                        .get("pageProps", {})
                        .get("offers", [])
                )
                if offers:
                    return self._parse_json_offers(offers)
            except (json.JSONDecodeError, AttributeError) as exc:
                self.logger.debug("olx.pl: JSON parse failed, falling back to HTML: %s", exc)

        return self._parse_html(soup)

    def _parse_json_offers(self, offers: list[dict]) -> list[Listing]:
        """Parse OLX listings from the ``offers`` JSON array.

        Args:
            offers: List of offer dicts from ``pageProps.offers``.

        Returns:
            List of :class:`Listing` objects.
        """
        listings: list[Listing] = []
        for offer in offers:
            try:
                listing = self._parse_json_offer(offer)
                if listing:
                    listings.append(listing)
            except Exception as exc:
                self.logger.debug("olx.pl: skipping offer %s: %s", offer.get("id"), exc)
        return listings

    def _parse_json_offer(self, offer: dict) -> Listing | None:
        """Convert a raw JSON offer dict to a :class:`Listing`.

        Args:
            offer: A single offer dict.

        Returns:
            A :class:`Listing`, or ``None`` if required fields are missing.
        """
        offer_id = str(offer.get("id", "")).strip()
        url = offer.get("url", "")
        if not url.startswith("https://"):
            return None

        price_raw = (
            offer.get("price", {})
                 .get("regularPrice", {})
                 .get("value")
        )
        price = float(price_raw) if price_raw is not None else None

        area_m2: float | None = None
        for param in offer.get("params", []):
            if param.get("key") == "surface":
                try:
                    area_m2 = float(re.sub(r"[^\d.]", "", str(param.get("value", {}).get("label", ""))))
                except (ValueError, TypeError):
                    pass
                break

        location = offer.get("location", {}).get("cityName", "")

        return Listing(
            id=f"olx_{offer_id}",
            title=offer.get("title", ""),
            price=price,
            area_m2=area_m2,
            location=location,
            url=url,
            source="olx.pl",
        )

    def _parse_html(self, soup: BeautifulSoup) -> list[Listing]:
        """Fallback HTML parser for olx.pl listing cards.

        Args:
            soup: Parsed page.

        Returns:
            List of :class:`Listing` objects.
        """
        cards = soup.select("[data-cy='l-card'], .css-1sw7q4x")
        listings: list[Listing] = []
        for card in cards:
            try:
                anchor = card.select_one("a[href]")
                if not anchor:
                    continue
                url = anchor["href"]
                if not url.startswith("https://"):
                    url = f"https://www.olx.pl{url}" if url.startswith("/") else ""
                if not url.startswith("https://"):
                    continue

                listing_id = url.rstrip("/").split("-")[-1].rstrip(".html")
                title_tag = card.select_one("h6, h3, [data-testid='listing-ad-title']")
                title = title_tag.get_text(strip=True) if title_tag else ""

                price_tag = card.select_one("[data-testid='ad-price'], .price")
                price = _parse_price(price_tag.get_text() if price_tag else None)

                location_tag = card.select_one("[data-testid='location-date'], .location")
                location = location_tag.get_text(strip=True).split(" - ")[0] if location_tag else ""

                listings.append(Listing(
                    id=f"olx_{listing_id}",
                    title=title,
                    price=price,
                    area_m2=None,
                    location=location,
                    url=url,
                    source="olx.pl",
                ))
            except Exception as exc:
                self.logger.debug("olx.pl HTML: skipping card: %s", exc)
        return listings
