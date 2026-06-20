"""Tests for run_scrapers() scraper isolation in main.py."""
import pytest
from unittest.mock import MagicMock, patch
from scrapers.base import Listing
import main


def make_listing(id_="test_1") -> Listing:
    return Listing(
        id=id_,
        title="Działka",
        url="https://example.com/1",
        source="test",
        location="Liszki",
    )


def _mock_scraper_cls(listings=None, raises=None, name="MockScraper"):
    """Return a mock scraper class whose instance returns listings or raises."""
    instance = MagicMock()
    if raises:
        instance.fetch_listings.side_effect = raises
    else:
        instance.fetch_listings.return_value = listings or []
    cls = MagicMock(return_value=instance)
    cls.__name__ = name
    return cls


# --- Isolation ---

def test_failing_scraper_does_not_prevent_others(monkeypatch):
    good_listing = make_listing("good_1")
    good_cls = _mock_scraper_cls(listings=[good_listing])
    bad_cls = _mock_scraper_cls(raises=RuntimeError("site down"))

    monkeypatch.setattr(main, "_SCRAPERS", [bad_cls, good_cls])
    results = main.run_scrapers()

    assert len(results) == 1
    assert results[0].id == "good_1"


def test_all_scrapers_fail_returns_empty_list(monkeypatch):
    bad1 = _mock_scraper_cls(raises=RuntimeError("down"))
    bad2 = _mock_scraper_cls(raises=ConnectionError("timeout"))

    monkeypatch.setattr(main, "_SCRAPERS", [bad1, bad2])
    results = main.run_scrapers()

    assert results == []


def test_all_scrapers_combine_results(monkeypatch):
    listing_a = make_listing("a")
    listing_b = make_listing("b")
    cls_a = _mock_scraper_cls(listings=[listing_a])
    cls_b = _mock_scraper_cls(listings=[listing_b])

    monkeypatch.setattr(main, "_SCRAPERS", [cls_a, cls_b])
    results = main.run_scrapers()

    assert {l.id for l in results} == {"a", "b"}


def test_failing_scraper_error_is_logged(monkeypatch, caplog):
    import logging
    bad_cls = _mock_scraper_cls(raises=RuntimeError("boom"))

    monkeypatch.setattr(main, "_SCRAPERS", [bad_cls])
    with caplog.at_level(logging.ERROR, logger="__main__"):
        main.run_scrapers()

    assert any("boom" in record.message or "failed" in record.message.lower()
               for record in caplog.records)


# --- _dedup ---

def test_dedup_removes_duplicate_ids():
    l1 = make_listing("dup")
    l2 = make_listing("dup")  # same id, second occurrence
    l3 = make_listing("unique")
    assert [l.id for l in main._dedup([l1, l2, l3])] == ["dup", "unique"]

def test_dedup_preserves_first_occurrence():
    first = make_listing("x")
    second = Listing(
        id="x", title="Other", url="https://example.com/other", source="test", location="Liszki"
    )
    result = main._dedup([first, second])
    assert len(result) == 1
    assert result[0].title == "Działka"  # first occurrence kept

def test_dedup_empty_list():
    assert main._dedup([]) == []

def test_dedup_no_duplicates_unchanged():
    listings = [make_listing("a"), make_listing("b"), make_listing("c")]
    assert [l.id for l in main._dedup(listings)] == ["a", "b", "c"]


# --- sort ---

def test_sort_by_location_then_price_desc():
    listings = [
        Listing(id="1", title="T", url="u", source="s", location="Liszki", price=100_000),
        Listing(id="2", title="T", url="u", source="s", location="Czernichów", price=200_000),
        Listing(id="3", title="T", url="u", source="s", location="Liszki", price=300_000),
        Listing(id="4", title="T", url="u", source="s", location="Czernichów", price=None),
    ]
    listings.sort(key=lambda l: (l.location.lower(), -(l.price or 0)))
    assert [l.id for l in listings] == ["2", "4", "3", "1"]

def test_sort_none_price_treated_as_cheapest():
    listings = [
        Listing(id="a", title="T", url="u", source="s", location="Liszki", price=500_000),
        Listing(id="b", title="T", url="u", source="s", location="Liszki", price=None),
    ]
    listings.sort(key=lambda l: (l.location.lower(), -(l.price or 0)))
    assert listings[0].id == "a"
    assert listings[1].id == "b"
