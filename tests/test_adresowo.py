"""Tests for the Adresowo scraper parser."""
import pathlib
import pytest
from scrapers.adresowo import AdresowoScraper

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "adresowo.html"


@pytest.fixture()
def scraper():
    return AdresowoScraper()


@pytest.fixture()
def listings(scraper):
    return scraper._parse(FIXTURE.read_text(encoding="utf-8"))


# --- _parse ---

def test_parse_ignores_non_o_anchors(listings):
    # The /search/ anchor must not produce a listing
    ids = {l.id for l in listings}
    assert not any("search" in id_ for id_ in ids)

def test_parse_returns_two_listings(listings):
    assert len(listings) == 2

def test_parse_ids_derived_from_href(listings):
    ids = {l.id for l in listings}
    assert "adresowo_abc123" in ids
    assert "adresowo_xyz789" in ids

def test_parse_url_absolute(listings):
    for listing in listings:
        assert listing.url.startswith("https://adresowo.pl/o/")

def test_parse_price(listings):
    listing = next(l for l in listings if l.id == "adresowo_abc123")
    assert listing.price == 150000.0

def test_parse_area(listings):
    listing = next(l for l in listings if l.id == "adresowo_abc123")
    assert listing.area_m2 == 2500.0

def test_parse_missing_price_and_area_is_none(listings):
    listing = next(l for l in listings if l.id == "adresowo_xyz789")
    assert listing.price is None
    assert listing.area_m2 is None

def test_parse_location_is_first_h2_part(listings):
    listing = next(l for l in listings if l.id == "adresowo_abc123")
    assert listing.location == "Liszki"

def test_parse_title_joins_two_h2_parts(listings):
    listing = next(l for l in listings if l.id == "adresowo_abc123")
    assert listing.title == "Liszki — gmina Liszki"

def test_parse_source(listings):
    for listing in listings:
        assert listing.source == "adresowo.pl"
