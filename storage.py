"""SQLite-backed storage for tracking already-seen listings."""
import logging
import sqlite3
from datetime import datetime

from config import DB_PATH
from scrapers.base import Listing

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS seen_listings (
    id          TEXT PRIMARY KEY,
    source      TEXT NOT NULL,
    url         TEXT NOT NULL,
    title       TEXT,
    first_seen_at TEXT NOT NULL
)
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the database schema if it does not already exist."""
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)
    logger.debug("Storage initialised at %s", DB_PATH)


def get_seen_ids() -> set[str]:
    """Return the set of listing IDs that have been seen in previous runs.

    Returns:
        Set of ID strings (e.g. ``"otodom_12345"``).
    """
    with _connect() as conn:
        rows = conn.execute("SELECT id FROM seen_listings").fetchall()
    return {row["id"] for row in rows}


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
            listing.seen_at.isoformat(),
        )
        for listing in listings
    ]
    with _connect() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO seen_listings (id, source, url, title, first_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
    logger.info("Saved %d new listing(s) to storage", len(listings))
