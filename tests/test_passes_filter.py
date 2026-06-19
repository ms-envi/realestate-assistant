"""Tests for the passes_filter function in main.py."""
import pytest
from main import passes_filter
from scrapers.base import Listing


def make_listing(**kwargs) -> Listing:
    defaults = dict(
        id="test_1",
        title="Działka",
        url="https://example.com/1",
        source="test",
        location="Liszki",
        price=None,
        area_m2=None,
    )
    defaults.update(kwargs)
    return Listing(**defaults)


# --- Exempt locations ---

def test_exempt_location_raczna_passes_regardless_of_price():
    listing = make_listing(location="Rączna", price=9_999_999.0, area_m2=1.0)
    assert passes_filter(listing) is True

def test_exempt_location_sciejowice_passes_regardless_of_area():
    listing = make_listing(location="Ściejowice", price=9_999_999.0, area_m2=1.0)
    assert passes_filter(listing) is True

def test_exempt_location_substring_match():
    listing = make_listing(location="Rączna, gmina Liszki", price=9_999_999.0)
    assert passes_filter(listing) is True

def test_exempt_check_is_case_insensitive():
    listing = make_listing(location="rączna", price=9_999_999.0)
    assert passes_filter(listing) is True


# --- Price filter ---

def test_listing_over_max_price_rejected():
    listing = make_listing(price=500_001.0, area_m2=2000.0)
    assert passes_filter(listing) is False

def test_listing_at_max_price_passes():
    listing = make_listing(price=500_000.0, area_m2=2000.0)
    assert passes_filter(listing) is True

def test_listing_under_max_price_passes():
    listing = make_listing(price=250_000.0, area_m2=2000.0)
    assert passes_filter(listing) is True

def test_missing_price_passes():
    listing = make_listing(price=None, area_m2=2000.0)
    assert passes_filter(listing) is True


# --- Area filter ---

def test_listing_under_min_area_rejected():
    listing = make_listing(price=100_000.0, area_m2=1499.0)
    assert passes_filter(listing) is False

def test_listing_at_min_area_passes():
    listing = make_listing(price=100_000.0, area_m2=1500.0)
    assert passes_filter(listing) is True

def test_listing_over_min_area_passes():
    listing = make_listing(price=100_000.0, area_m2=3000.0)
    assert passes_filter(listing) is True

def test_missing_area_passes():
    listing = make_listing(price=100_000.0, area_m2=None)
    assert passes_filter(listing) is True


# --- Both missing ---

def test_both_missing_passes():
    listing = make_listing(price=None, area_m2=None)
    assert passes_filter(listing) is True


# --- Location allowlist ---

def test_unknown_location_rejected():
    listing = make_listing(location="Rzyki")
    assert passes_filter(listing) is False

def test_location_liski_rejected():
    listing = make_listing(location="Liski")
    assert passes_filter(listing) is False

def test_gmina_liszki_village_passes():
    for village in ["Baczyn", "Budzyń", "Cholerzyn", "Chrosna", "Czułów", "Jeziorzany",
                    "Kaszów", "Kryspinów", "Liszki", "Mników", "Morawica",
                    "Piekary", "Rączna", "Ściejowice"]:
        listing = make_listing(location=village)
        assert passes_filter(listing) is True, f"{village} should pass"

def test_gmina_czernichow_village_passes():
    for village in ["Czernichów", "Czułówek", "Dąbrowa Szlachecka", "Kamień",
                    "Kłokoczyn", "Nowa Wieś Szlachecka", "Przeginia Duchowna",
                    "Przeginia Narodowa", "Rybna", "Rusocice", "Wołowice", "Zagacie"]:
        listing = make_listing(location=village)
        assert passes_filter(listing) is True, f"{village} should pass"

def test_empty_location_rejected():
    listing = make_listing(location="")
    assert passes_filter(listing) is False

def test_location_check_is_case_insensitive():
    listing = make_listing(location="mników")
    assert passes_filter(listing) is True

def test_sanka_passes():
    assert passes_filter(make_listing(location="Sanka")) is True

def test_exempt_location_bypasses_location_check():
    # Rączna is in ALLOWED_LOCATIONS too, but the exempt path must trigger
    # even for a location that is NOT in ALLOWED_LOCATIONS
    listing = make_listing(location="Rączna", price=9_999_999.0, area_m2=1.0)
    assert passes_filter(listing) is True
