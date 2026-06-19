"""Tests for the Otodom scraper parser."""
import json
import pathlib
import pytest
from scrapers.otodom import OtodomScraper

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "otodom.html"
FIXTURE_P2 = pathlib.Path(__file__).parent / "fixtures" / "otodom_page2.html"


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


# --- _parse_total_pages ---

def test_parse_total_pages_from_fixture(scraper):
    assert scraper._parse_total_pages(FIXTURE.read_text(encoding="utf-8")) == 2

def test_parse_total_pages_missing_returns_1(scraper):
    assert scraper._parse_total_pages("<html><body></body></html>") == 1

def test_parse_total_pages_no_pagination_key_returns_1(scraper):
    html = '<script id="__NEXT_DATA__">{"props":{"pageProps":{"data":{"searchAds":{"items":[]}}}}}</script>'
    assert scraper._parse_total_pages(html) == 1

def test_parse_total_pages_invalid_json_returns_1(scraper):
    html = '<script id="__NEXT_DATA__">{invalid}</script>'
    assert scraper._parse_total_pages(html) == 1


# --- fetch_listings pagination ---

def test_fetch_listings_fetches_all_pages(mocker):
    scraper = OtodomScraper()
    mocker.patch("scrapers.otodom.MUNICIPALITIES", ["Liszki"])
    page1 = mocker.Mock(text=FIXTURE.read_text(encoding="utf-8"))
    page2 = mocker.Mock(text=FIXTURE_P2.read_text(encoding="utf-8"))
    mocker.patch.object(scraper, "_get", side_effect=[page1, page2])
    listings = scraper.fetch_listings()
    assert len(listings) == 4  # 2 from page1 + 2 from page2

def test_fetch_listings_single_page_makes_one_request(mocker):
    scraper = OtodomScraper()
    mocker.patch("scrapers.otodom.MUNICIPALITIES", ["Liszki"])
    html_p1 = FIXTURE.read_text(encoding="utf-8").replace('"totalPages": 2', '"totalPages": 1')
    mock_get = mocker.patch.object(scraper, "_get", return_value=mocker.Mock(text=html_p1))
    scraper.fetch_listings()
    assert mock_get.call_count == 1

def test_fetch_listings_page2_url_has_query_param(mocker):
    scraper = OtodomScraper()
    mocker.patch("scrapers.otodom.MUNICIPALITIES", ["Liszki"])
    page1 = mocker.Mock(text=FIXTURE.read_text(encoding="utf-8"))
    page2 = mocker.Mock(text=FIXTURE_P2.read_text(encoding="utf-8"))
    mock_get = mocker.patch.object(scraper, "_get", side_effect=[page1, page2])
    scraper.fetch_listings()
    _, call_page2 = mock_get.call_args_list
    assert "?page=2" in call_page2[0][0]

def test_fetch_listings_network_error_on_page2_returns_page1_results(mocker):
    scraper = OtodomScraper()
    mocker.patch("scrapers.otodom.MUNICIPALITIES", ["Liszki"])
    page1 = mocker.Mock(text=FIXTURE.read_text(encoding="utf-8"))
    mocker.patch.object(scraper, "_get", side_effect=[page1, Exception("timeout")])
    listings = scraper.fetch_listings()
    assert len(listings) == 2  # page1 results preserved despite page2 failure
