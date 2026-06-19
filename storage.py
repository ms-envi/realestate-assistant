"""SQLite-backed storage for tracking already-seen listings."""
import logging
import sqlite3
from datetime import datetime
from typing import Optional

from config import DB_PATH
from scrapers.base import Listing

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS seen_listings (
    id          TEXT PRIMARY KEY,
    source      TEXT NOT NULL,
    url         TEXT NOT NULL,
    title       TEXT,
    price       REAL,
    first_seen_at TEXT NOT NULL
)
"""

_ADD_PRICE_COLUMN = "ALTER TABLE seen_listings ADD COLUMN price REAL"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the database schema if it does not already exist.

    Also migrates existing databases by adding the ``price`` column when absent.
    """
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)
        try:
            conn.execute(_ADD_PRICE_COLUMN)
        except sqlite3.OperationalError:
            pass  # column already exists
    logger.debug("Storage initialised at %s", DB_PATH)


def get_seen_prices() -> dict[str, Optional[float]]:
    """Return a mapping of listing ID to the last known price for all seen listings.

    Returns:
        Dict mapping ID string to price (``None`` if price was unknown when saved).
    """
    with _connect() as conn:
        rows = conn.execute("SELECT id, price FROM seen_listings").fetchall()
    return {row["id"]: row["price"] for row in rows}


def save_listings(listings: list[Listing]) -> None:
    """Persist new listings so they are not reported again on the next run.

    Listings whose ID is already in the database are silently ignored
    (INSERT OR IGNORE).

    Args:
        listings: New listings to persist.
    """
    if not listings:
        return
    rows = [
        (
            listing.id,
            listing.source,
            listing.url,
            listing.title,
            listing.price,
            listing.seen_at.isoformat(),
        )
        for listing in listings
    ]
    with _connect() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO seen_listings (id, source, url, title, price, first_seen_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
    logger.info("Saved %d new listing(s) to storage", len(listings))


def update_listing_price(listing_id: str, price: Optional[float]) -> None:
    """Update the stored price for a listing whose price has dropped.

    Args:
        listing_id: The listing ID to update.
        price: The new (lower) price.
    """
    with _connect() as conn:
        conn.execute(
            "UPDATE seen_listings SET price = ? WHERE id = ?",
            (price, listing_id),
        )
    logger.info("Price updated for %s → %s zł", listing_id, price)
