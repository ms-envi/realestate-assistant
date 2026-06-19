"""Tests for is_price_drop() in main.py."""
from scrapers.base import Listing
from main import is_price_drop


def make_listing(price=None) -> Listing:
    return Listing(
        id="test_1",
        title="Działka",
        url="https://example.com/1",
        source="test",
        location="Liszki",
        price=price,
    )


def test_new_listing_is_not_price_drop():
    listing = make_listing(price=100_000.0)
    assert is_price_drop(listing, {}) is False

def test_same_price_is_not_price_drop():
    listing = make_listing(price=100_000.0)
    assert is_price_drop(listing, {"test_1": 100_000.0}) is False

def test_higher_price_is_not_price_drop():
    listing = make_listing(price=120_000.0)
    assert is_price_drop(listing, {"test_1": 100_000.0}) is False

def test_lower_price_is_price_drop():
    listing = make_listing(price=90_000.0)
    assert is_price_drop(listing, {"test_1": 100_000.0}) is True

def test_current_price_none_is_not_price_drop():
    listing = make_listing(price=None)
    assert is_price_drop(listing, {"test_1": 100_000.0}) is False

def test_stored_price_none_is_not_price_drop():
    listing = make_listing(price=90_000.0)
    assert is_price_drop(listing, {"test_1": None}) is False

def test_both_prices_none_is_not_price_drop():
    listing = make_listing(price=None)
    assert is_price_drop(listing, {"test_1": None}) is False
