"""Configuration constants and environment variable bindings."""
import os

MUNICIPALITIES = ["Liszki", "Czernichów"]

REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "")

DB_PATH = os.environ.get("DB_PATH", "listings.db")
