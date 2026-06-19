"""Tests for storage.py using an in-memory SQLite database."""
import pytest
from unittest.mock import patch
from scrapers.base import Listing
import storage


def make_listing(id_suffix="1", **kwargs) -> Listing:
    defaults = dict(
        id=f"test_{id_suffix}",
        title="Działka testowa",
        url=f"https://example.com/{id_suffix}",
        source="test",
        location="Liszki",
    )
    defaults.update(kwargs)
    return Listing(**defaults)


@pytest.fixture(autouse=True)
def in_memory_db(monkeypatch):
    """Redirect every _connect() call to a single shared in-memory connection."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    monkeypatch.setattr(storage, "_connect", lambda: conn)
    storage.init_db()
    yield conn
    conn.close()


# --- init_db ---

def test_init_db_creates_table(in_memory_db):
    tables = in_memory_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='seen_listings'"
    ).fetchall()
    assert len(tables) == 1


# --- get_seen_ids ---

def test_get_seen_ids_empty_on_fresh_db():
    assert storage.get_seen_ids() == set()


# --- save_listings ---

def test_save_listings_persists_ids():
    listing = make_listing("42")
    storage.save_listings([listing])
    assert "test_42" in storage.get_seen_ids()

def test_save_listings_multiple():
    listings = [make_listing(str(i)) for i in range(3)]
    storage.save_listings(listings)
    seen = storage.get_seen_ids()
    assert seen == {"test_0", "test_1", "test_2"}

def test_save_listings_empty_list_is_noop():
    storage.save_listings([])
    assert storage.get_seen_ids() == set()

def test_save_listings_duplicate_is_ignored():
    listing = make_listing("dup")
    storage.save_listings([listing])
    storage.save_listings([listing])  # second call must not raise
    assert storage.get_seen_ids() == {"test_dup"}

def test_save_listings_stores_correct_fields(in_memory_db):
    listing = make_listing("detail", title="Moja działka", url="https://example.com/detail")
    storage.save_listings([listing])
    row = in_memory_db.execute(
        "SELECT * FROM seen_listings WHERE id = 'test_detail'"
    ).fetchone()
    assert row["source"] == "test"
    assert row["url"] == "https://example.com/detail"
    assert row["title"] == "Moja działka"
