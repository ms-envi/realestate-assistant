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

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", "")  # must be a verified Resend sender address
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "")

DB_PATH = os.environ.get("DB_PATH", "listings.db")

def _env_float(name: str, default=None):
    val = os.environ.get(name)
    return float(val) if val is not None else default


# Listing filters — applied after scraping, before email/storage
# Override via environment variables; unset = use default
MAX_PRICE   = _env_float("MAX_PRICE",   500_000)   # zł; set to empty to disable
MIN_AREA_M2 = _env_float("MIN_AREA_M2", 1_500)     # m²; set to empty to disable
# Locations (substring match) that are exempt from price/area filters
FILTER_EXEMPT_LOCATIONS = ["Rączna", "Ściejowice"]
# All villages in gmina Liszki and gmina Czernichów (powiat krakowski).
# A listing whose location matches none of these is filtered out.
ALLOWED_LOCATIONS = [
    # gmina Liszki
    "Baczyn", "Budzyń", "Cholerzyn", "Chrosna", "Czułów", "Jeziorzany",
    "Kaszów", "Kryspinów", "Liszki", "Mników", "Morawica",
    "Piekary", "Rączna", "Ściejowice",
    # gmina Czernichów
    "Czernichów", "Czułówek", "Dąbrowa Szlachecka", "Kamień",
    "Kłokoczyn", "Nowa Wieś Szlachecka", "Przeginia Duchowna",
    "Przeginia Narodowa", "Rybna", "Rusocice", "Wołowice", "Zagacie",
    # inne miejscowości w okolicy
    "Sanka",
]
