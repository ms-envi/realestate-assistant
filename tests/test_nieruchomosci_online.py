"""Tests for the NieruchomosciOnline scraper parser."""
import pathlib
import pytest
from scrapers.nieruchomosci_online import NieruchomosciOnlineScraper, _parse_price, _parse_area

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "nieruchomosci_online.html"


@pytest.fixture()
def scraper():
    return NieruchomosciOnlineScraper()


@pytest.fixture()
def listings(scraper):
    return scraper._parse(FIXTURE.read_text(encoding="utf-8"))


# --- _parse_price ---

def test_parse_price_strips_non_digits():
    assert _parse_price("8 200 000 zł") == 8200000.0

def test_parse_price_empty_returns_none():
    assert _parse_price("") is None


# --- _parse_area ---

def test_parse_area_basic():
    assert _parse_area("2 500 m²") == 2500.0

def test_parse_area_decimal():
    assert _parse_area("1 234,5 m²") == 1234.5

def test_parse_area_empty_returns_none():
    assert _parse_area("") is None


# --- _parse ---

def test_parse_excludes_investment_tiles(listings):
    # The .tile-investment card (id="000") must be excluded
    ids = {l.id for l in listings}
    assert "nieruchomosci_online_000" not in ids

def test_parse_skips_relative_url(listings):
    ids = {l.id for l in listings}
    assert "nieruchomosci_online_000bad" not in ids

def test_parse_skips_tile_with_no_anchor(listings):
    ids = {l.id for l in listings}
    assert "nieruchomosci_online_noanchor" not in ids

def test_parse_returns_two_valid_listings(listings):
    assert len(listings) == 2

def test_parse_ids(listings):
    ids = {l.id for l in listings}
    assert "nieruchomosci_online_789" in ids
    assert "nieruchomosci_online_321" in ids

def test_parse_url_absolute(listings):
    for listing in listings:
        assert listing.url.startswith("https://")

def test_parse_price(listings):
    listing = next(l for l in listings if l.id == "nieruchomosci_online_789")
    assert listing.price == 150000.0

def test_parse_area(listings):
    listing = next(l for l in listings if l.id == "nieruchomosci_online_789")
    assert listing.area_m2 == 2500.0

def test_parse_missing_price_and_area_is_none(listings):
    listing = next(l for l in listings if l.id == "nieruchomosci_online_321")
    assert listing.price is None
    assert listing.area_m2 is None

def test_parse_location_trailing_comma_stripped(listings):
    listing = next(l for l in listings if l.id == "nieruchomosci_online_789")
    assert listing.location == "Liszki"

def test_parse_source(listings):
    for listing in listings:
        assert listing.source == "nieruchomosci-online.pl"
