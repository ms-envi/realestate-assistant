"""Tests for the notifier HTML builder functions."""
import pytest
from scrapers.base import Listing
from notifier import _build_listing_row, _build_html


def make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="test_1",
        title="Działka w Liszkach",
        url="https://example.com/1",
        source="otodom.pl",
        location="Liszki",
        price=None,
        area_m2=None,
    )
    defaults.update(kwargs)
    return Listing(**defaults)


# --- _build_listing_row ---

def test_row_contains_url():
    listing = make_listing(url="https://example.com/listing/1")
    row = _build_listing_row(listing)
    assert "https://example.com/listing/1" in row

def test_row_contains_title():
    listing = make_listing(title="Piękna działka")
    row = _build_listing_row(listing)
    assert "Piękna działka" in row

def test_row_price_formatted_with_space_separator():
    # notifier uses \xa0 (non-breaking space) as the thousands separator
    listing = make_listing(price=150000.0)
    row = _build_listing_row(listing)
    assert "150\xa0000 zł" in row

def test_row_price_none_shows_dash():
    listing = make_listing(price=None)
    row = _build_listing_row(listing)
    assert "–" in row

def test_row_area_formatted():
    listing = make_listing(area_m2=2500.0)
    row = _build_listing_row(listing)
    assert "2\xa0500 m²" in row

def test_row_area_none_shows_dash():
    listing = make_listing(area_m2=None)
    row = _build_listing_row(listing)
    assert "–" in row

def test_row_contains_location():
    listing = make_listing(location="Czernichów")
    row = _build_listing_row(listing)
    assert "Czernichów" in row

def test_row_contains_source():
    listing = make_listing(source="olx.pl")
    row = _build_listing_row(listing)
    assert "olx.pl" in row


# --- _build_html ---

def test_html_contains_listing_count():
    listings = [make_listing(id=f"test_{i}") for i in range(3)]
    html = _build_html(listings)
    assert "<strong>3</strong>" in html

def test_html_contains_all_listing_urls():
    listings = [make_listing(id=f"test_{i}", url=f"https://example.com/{i}") for i in range(2)]
    html = _build_html(listings)
    assert "https://example.com/0" in html
    assert "https://example.com/1" in html

def test_html_has_table_structure():
    html = _build_html([make_listing()])
    assert "<table" in html
    assert "<thead" in html
    assert "<tbody" in html

def test_html_empty_listings_still_renders():
    html = _build_html([])
    assert "<strong>0</strong>" in html
