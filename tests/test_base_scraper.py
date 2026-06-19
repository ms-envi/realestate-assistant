"""Tests for BaseScraper._get retry logic."""
import pytest
import requests
from unittest.mock import MagicMock, patch, call
from scrapers.base import BaseScraper


class _ConcreteScraper(BaseScraper):
    def fetch_listings(self):
        return []


@pytest.fixture()
def scraper():
    return _ConcreteScraper()


def _make_response(status_code=200):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    return resp


def _http_error():
    exc = requests.HTTPError("500 Server Error")
    return exc


# --- Success on first attempt ---

def test_get_returns_response_on_success(scraper):
    resp = _make_response()
    with patch.object(scraper.session, "get", return_value=resp) as mock_get:
        result = scraper._get("https://example.com/")
    assert result is resp
    mock_get.assert_called_once()


def test_get_sets_default_timeout(scraper):
    resp = _make_response()
    with patch.object(scraper.session, "get", return_value=resp) as mock_get:
        scraper._get("https://example.com/")
    _, kwargs = mock_get.call_args
    assert kwargs.get("timeout") == 15


def test_get_respects_explicit_timeout(scraper):
    resp = _make_response()
    with patch.object(scraper.session, "get", return_value=resp) as mock_get:
        scraper._get("https://example.com/", timeout=5)
    _, kwargs = mock_get.call_args
    assert kwargs.get("timeout") == 5


# --- Retry on failure ---

def test_get_retries_on_failure_then_succeeds(scraper):
    good = _make_response()
    side_effects = [requests.ConnectionError("down"), good]
    with patch.object(scraper.session, "get", side_effect=side_effects) as mock_get, \
         patch("scrapers.base.time.sleep") as mock_sleep:
        result = scraper._get("https://example.com/")
    assert result is good
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once()


def test_get_uses_exponential_backoff(scraper):
    good = _make_response()
    # Fail twice, succeed on third (MAX_RETRIES=3)
    side_effects = [
        requests.ConnectionError("fail 1"),
        requests.ConnectionError("fail 2"),
        good,
    ]
    with patch.object(scraper.session, "get", side_effect=side_effects), \
         patch("scrapers.base.time.sleep") as mock_sleep:
        scraper._get("https://example.com/")
    sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
    # backoff = 2.0 ** attempt: attempt 1 → 2.0, attempt 2 → 4.0
    assert sleep_calls == [2.0, 4.0]


# --- Exhausted retries ---

def test_get_raises_after_max_retries_exhausted(scraper):
    exc = requests.ConnectionError("always down")
    with patch.object(scraper.session, "get", side_effect=exc), \
         patch("scrapers.base.time.sleep"):
        with pytest.raises(requests.ConnectionError):
            scraper._get("https://example.com/")


def test_get_makes_exactly_max_retries_attempts(scraper):
    exc = requests.ConnectionError("always down")
    with patch.object(scraper.session, "get", side_effect=exc) as mock_get, \
         patch("scrapers.base.time.sleep"):
        with pytest.raises(requests.ConnectionError):
            scraper._get("https://example.com/")
    assert mock_get.call_count == 3  # MAX_RETRIES = 3


def test_get_does_not_sleep_after_last_attempt(scraper):
    exc = requests.ConnectionError("always down")
    with patch.object(scraper.session, "get", side_effect=exc), \
         patch("scrapers.base.time.sleep") as mock_sleep:
        with pytest.raises(requests.ConnectionError):
            scraper._get("https://example.com/")
    # 3 attempts → sleep only between attempt 1→2 and 2→3
    assert mock_sleep.call_count == 2
