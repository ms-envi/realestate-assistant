"""Tests for the Otodom scraper parser."""
import json
import pathlib
import pytest
from scrapers.otodom import OtodomScraper

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "otodom.html"


@pytest.fixture()
def scraper():
    return OtodomScraper()


@pytest.fixture()
def listings(scraper):
    return scraper._parse(FIXTURE.read_text(encoding="utf-8"))


# --- _parse ---

def test_parse_returns_two_valid_listings(listings):
    # item with id=0 and empty slug is skipped; 2 remain
    assert len(listings) == 2

def test_parse_ids_prefixed(listings):
    ids = {l.id for l in listings}
    assert "otodom_987654" in ids
    assert "otodom_111222" in ids

def test_parse_url_absolute(listings):
    for listing in listings:
        assert listing.url.startswith("https://")

def test_parse_url_uses_slug(listings):
    listing = next(l for l in listings if l.id == "otodom_987654")
    assert "dzialka-budowlana-liszki-ID987654" in listing.url

def test_parse_price(listings):
    listing = next(l for l in listings if l.id == "otodom_987654")
    assert listing.price == 320000.0

def test_parse_null_price_is_none(listings):
    listing = next(l for l in listings if l.id == "otodom_111222")
    assert listing.price is None

def test_parse_area(listings):
    listing = next(l for l in listings if l.id == "otodom_987654")
    assert listing.area_m2 == 1800.0

def test_parse_null_area_is_none(listings):
    listing = next(l for l in listings if l.id == "otodom_111222")
    assert listing.area_m2 is None

def test_parse_location_prefers_city(listings):
    listing = next(l for l in listings if l.id == "otodom_987654")
    assert listing.location == "Liszki"

def test_parse_location_falls_back_to_county(listings):
    listing = next(l for l in listings if l.id == "otodom_111222")
    assert listing.location == "powiat krakowski"

def test_parse_source(listings):
    for listing in listings:
        assert listing.source == "otodom.pl"

def test_parse_missing_next_data_returns_empty(scraper):
    assert scraper._parse("<html><body></body></html>") == []

def test_parse_invalid_json_returns_empty(scraper):
    html = '<script id="__NEXT_DATA__">{invalid json}</script>'
    assert scraper._parse(html) == []
