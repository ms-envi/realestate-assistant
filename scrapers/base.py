"""Base scraper class and Listing dataclass shared by all scrapers."""
from __future__ import annotations

import abc
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import requests

from config import MAX_RETRIES, REQUEST_TIMEOUT, RETRY_BACKOFF, USER_AGENT


@dataclass
class Listing:
    """A single real estate listing."""

    id: str
    title: str
    url: str
    source: str
    location: str
    price: Optional[float] = None
    area_m2: Optional[float] = None
    seen_at: datetime = field(default_factory=datetime.now)


class BaseScraper(abc.ABC):
    """Base class for all real estate scrapers.

    Provides a shared requests Session with a realistic User-Agent and a
    ``_get`` helper that retries with exponential backoff on network errors.
    Subclasses must implement :meth:`fetch_listings`.
    """

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.logger = logging.getLogger(self.__class__.__name__)

    @abc.abstractmethod
    def fetch_listings(self) -> list[Listing]:
        """Return all current listings for the configured municipalities."""

    def _get(self, url: str, **kwargs) -> requests.Response:
        """GET with automatic retry and exponential backoff.

        Args:
            url: Target URL.
            **kwargs: Forwarded to ``requests.Session.get``.

        Returns:
            A successful :class:`requests.Response`.

        Raises:
            requests.RequestException: After all retry attempts are exhausted.
        """
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_exc = exc
                if attempt == MAX_RETRIES:
                    break
                wait = RETRY_BACKOFF ** attempt
                self.logger.warning(
                    "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                    attempt, MAX_RETRIES, url, exc, wait,
                )
                time.sleep(wait)
        raise last_exc
