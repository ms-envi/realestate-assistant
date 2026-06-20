"""Tests for storage.py using an in-memory SQLite database."""
import pytest
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

def test_init_db_adds_price_column(in_memory_db):
    cols = {row[1] for row in in_memory_db.execute("PRAGMA table_info(seen_listings)")}
    assert "price" in cols

def test_init_db_is_idempotent():
    storage.init_db()  # second call must not raise


# --- get_seen_prices ---

def test_get_seen_prices_empty_on_fresh_db():
    assert storage.get_seen_prices() == {}

def test_get_seen_prices_returns_id_to_price():
    storage.save_listings([make_listing("1", price=100_000.0)])
    assert storage.get_seen_prices() == {"test_1": 100_000.0}

def test_get_seen_prices_none_when_price_unknown():
    storage.save_listings([make_listing("np", price=None)])
    assert storage.get_seen_prices() == {"test_np": None}


# --- save_listings ---

def test_save_listings_persists_ids():
    listing = make_listing("42")
    storage.save_listings([listing])
    assert "test_42" in storage.get_seen_prices()

def test_save_listings_multiple():
    listings = [make_listing(str(i)) for i in range(3)]
    storage.save_listings(listings)
    assert set(storage.get_seen_prices().keys()) == {"test_0", "test_1", "test_2"}

def test_save_listings_empty_list_is_noop():
    storage.save_listings([])
    assert storage.get_seen_prices() == {}

def test_save_listings_duplicate_is_ignored():
    listing = make_listing("dup", price=200_000.0)
    storage.save_listings([listing])
    storage.save_listings([listing])
    assert list(storage.get_seen_prices().keys()) == ["test_dup"]

def test_save_listings_stores_price(in_memory_db):
    storage.save_listings([make_listing("p", price=150_000.0)])
    row = in_memory_db.execute("SELECT price FROM seen_listings WHERE id='test_p'").fetchone()
    assert row["price"] == 150_000.0

def test_save_listings_stores_correct_fields(in_memory_db):
    listing = make_listing("detail", title="Moja działka", url="https://example.com/detail")
    storage.save_listings([listing])
    row = in_memory_db.execute(
        "SELECT * FROM seen_listings WHERE id = 'test_detail'"
    ).fetchone()
    assert row["source"] == "test"
    assert row["url"] == "https://example.com/detail"
    assert row["title"] == "Moja działka"


# --- update_listing_price ---

def test_update_listing_price_changes_stored_price(in_memory_db):
    storage.save_listings([make_listing("u", price=300_000.0)])
    storage.update_listing_price("test_u", 250_000.0)
    assert storage.get_seen_prices()["test_u"] == 250_000.0

def test_update_listing_price_to_none(in_memory_db):
    storage.save_listings([make_listing("u2", price=300_000.0)])
    storage.update_listing_price("test_u2", None)
    assert storage.get_seen_prices()["test_u2"] is None


# --- get_last_email_date / save_last_email_date ---

def test_get_last_email_date_returns_none_on_fresh_db():
    assert storage.get_last_email_date() is None

def test_save_and_get_last_email_date():
    storage.save_last_email_date()
    from datetime import datetime
    expected = datetime.utcnow().date().isoformat()
    assert storage.get_last_email_date() == expected

def test_save_last_email_date_is_idempotent():
    storage.save_last_email_date()
    storage.save_last_email_date()
    from datetime import datetime
    expected = datetime.utcnow().date().isoformat()
    assert storage.get_last_email_date() == expected

def test_init_db_creates_meta_table(in_memory_db):
    tables = {
        row[0] for row in in_memory_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "meta" in tables
