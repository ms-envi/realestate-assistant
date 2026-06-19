"""Tests for the OLX scraper parser."""
import pathlib
import pytest
from scrapers.olx import OlxScraper, _parse_price, _parse_area

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "olx.html"


@pytest.fixture()
def scraper():
    return OlxScraper()


@pytest.fixture()
def listings(scraper):
    return scraper._parse(FIXTURE.read_text(encoding="utf-8"))


# --- _parse_price ---

def test_parse_price_with_spaces():
    assert _parse_price("150 000 zł") == 150000.0

def test_parse_price_no_match():
    assert _parse_price("brak ceny") is None

def test_parse_price_negotiable_suffix():
    assert _parse_price("44 999 złdo negocjacji") == 44999.0


# --- _parse_area ---

def test_parse_area_basic():
    assert _parse_area("2 500 m²") == 2500.0

def test_parse_area_with_suffix():
    assert _parse_area("2 500 m² - 60 zł/m²") == 2500.0

def test_parse_area_no_match():
    assert _parse_area("brak") is None


# --- _parse ---

def test_parse_returns_three_valid_listings(listings):
    # 3 valid cards (with id + anchor): 123456, 654321, 999999
    assert len(listings) == 3

def test_parse_ids_prefixed(listings):
    ids = {l.id for l in listings}
    assert "olx_123456" in ids
    assert "olx_654321" in ids
    assert "olx_999999" in ids

def test_parse_url_absolute(listings):
    for listing in listings:
        assert listing.url.startswith("https://")

def test_parse_relative_href_gets_domain_prepended(listings):
    listing = next(l for l in listings if l.id == "olx_123456")
    assert listing.url == "https://www.olx.pl/oferta/dzialka-budowlana-liszki-123456.html"

def test_parse_absolute_href_unchanged(listings):
    listing = next(l for l in listings if l.id == "olx_654321")
    assert listing.url == "https://www.olx.pl/oferta/inna-dzialka-654321.html"

def test_parse_price_parsed(listings):
    listing = next(l for l in listings if l.id == "olx_123456")
    assert listing.price == 150000.0

def test_parse_area_parsed(listings):
    listing = next(l for l in listings if l.id == "olx_123456")
    assert listing.area_m2 == 2500.0

def test_parse_location_stripped(listings):
    listing = next(l for l in listings if l.id == "olx_123456")
    assert listing.location == "Liszki"

def test_parse_missing_price_and_area_is_none(listings):
    listing = next(l for l in listings if l.id == "olx_999999")
    assert listing.price is None
    assert listing.area_m2 is None

def test_parse_source(listings):
    for listing in listings:
        assert listing.source == "olx.pl"


# --- fetch_listings pagination ---

_EMPTY = "<html></html>"

def test_fetch_listings_paginates_until_empty(mocker):
    scraper = OlxScraper()
    mocker.patch("scrapers.olx.MUNICIPALITIES", ["Liszki"])
    mock_get = mocker.patch.object(
        scraper, "_get",
        side_effect=[mocker.Mock(text=FIXTURE.read_text()), mocker.Mock(text=_EMPTY)],
    )
    listings = scraper.fetch_listings()
    assert len(listings) == 3
    assert mock_get.call_count == 2

def test_fetch_listings_page2_uses_query_param(mocker):
    scraper = OlxScraper()
    mocker.patch("scrapers.olx.MUNICIPALITIES", ["Liszki"])
    mock_get = mocker.patch.object(
        scraper, "_get",
        side_effect=[mocker.Mock(text=FIXTURE.read_text()), mocker.Mock(text=_EMPTY)],
    )
    scraper.fetch_listings()
    assert "page=2" in mock_get.call_args_list[1][0][0]

def test_fetch_listings_respects_max_pages(mocker):
    scraper = OlxScraper()
    mocker.patch("scrapers.olx.MUNICIPALITIES", ["Liszki"])
    mock_get = mocker.patch.object(scraper, "_get", return_value=mocker.Mock(text=FIXTURE.read_text()))
    scraper.fetch_listings()
    assert mock_get.call_count == 20
