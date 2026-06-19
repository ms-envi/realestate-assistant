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
