"""Tests for the Gratka scraper parser."""
import pathlib
import pytest
from scrapers.gratka import GratkaScraper, _parse_price, _parse_area

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "gratka.html"


@pytest.fixture()
def scraper():
    return GratkaScraper()


@pytest.fixture()
def listings(scraper):
    return scraper._parse(FIXTURE.read_text(encoding="utf-8"))


# --- _parse_price ---

def test_parse_price_strips_non_digits():
    assert _parse_price("150 000 zł") == 150000.0

def test_parse_price_empty_returns_none():
    assert _parse_price("") is None


# --- _parse_area ---

def test_parse_area_basic():
    assert _parse_area("2 500 m²") == 2500.0

def test_parse_area_empty_returns_none():
    assert _parse_area("") is None


# --- _parse ---

def test_parse_skips_non_plot_listings(listings):
    # dom card must be excluded; only dzialka cards are kept
    ids = {l.id for l in listings}
    assert not any("dom" in id_ for id_ in ids)

def test_parse_returns_two_plot_listings(listings):
    # liszki-abc123 and czernichow-yyy456 are plots; dom is skipped
    assert len(listings) == 2

def test_parse_url_absolute(listings):
    for listing in listings:
        assert listing.url.startswith("https://")

def test_parse_price_extracted(listings):
    listing = next(l for l in listings if "abc123" in l.id)
    assert listing.price == 150000.0

def test_parse_area_extracted(listings):
    listing = next(l for l in listings if "abc123" in l.id)
    assert listing.area_m2 == 2500.0

def test_parse_no_price_span_is_none(listings):
    listing = next(l for l in listings if "yyy456" in l.id)
    assert listing.price is None

def test_parse_source(listings):
    for listing in listings:
        assert listing.source == "gratka.pl"

def test_parse_id_derived_from_href(listings):
    ids = {l.id for l in listings}
    assert "gratka_liszki-abc123.html" in ids or any("abc123" in id_ for id_ in ids)


# --- fetch_listings pagination ---

_EMPTY = "<html></html>"

def test_fetch_listings_paginates_until_empty(mocker):
    scraper = GratkaScraper()
    mocker.patch("scrapers.gratka.MUNICIPALITIES", ["Liszki"])
    mock_get = mocker.patch.object(
        scraper, "_get",
        side_effect=[mocker.Mock(text=FIXTURE.read_text()), mocker.Mock(text=_EMPTY)],
    )
    listings = scraper.fetch_listings()
    assert len(listings) == 2
    assert mock_get.call_count == 2

def test_fetch_listings_page2_uses_query_param(mocker):
    scraper = GratkaScraper()
    mocker.patch("scrapers.gratka.MUNICIPALITIES", ["Liszki"])
    mock_get = mocker.patch.object(
        scraper, "_get",
        side_effect=[mocker.Mock(text=FIXTURE.read_text()), mocker.Mock(text=_EMPTY)],
    )
    scraper.fetch_listings()
    assert "page=2" in mock_get.call_args_list[1][0][0]

def test_fetch_listings_respects_max_pages(mocker):
    scraper = GratkaScraper()
    mocker.patch("scrapers.gratka.MUNICIPALITIES", ["Liszki"])
    mock_get = mocker.patch.object(scraper, "_get", return_value=mocker.Mock(text=FIXTURE.read_text()))
    scraper.fetch_listings()
    assert mock_get.call_count == 20
