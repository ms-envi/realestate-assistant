"""Email notifications via Resend API."""
import logging
from typing import FrozenSet

import resend

from config import NOTIFY_EMAIL, RESEND_API_KEY, RESEND_FROM
from scrapers.base import Listing

logger = logging.getLogger(__name__)


def _build_listing_row(listing: Listing, price_drop: bool = False) -> str:
    price_str = f"{listing.price:,.0f} zł".replace(",", "\xa0") if listing.price else "–"
    area_str = f"{listing.area_m2:,.0f} m²".replace(",", "\xa0") if listing.area_m2 else "–"
    if price_drop:
        price_str = f"<span style='color:red;font-weight:bold'>{price_str} ↓</span>"
    return (
        f"<tr>"
        f"<td><a href='{listing.url}'>{listing.title}</a></td>"
        f"<td>{listing.location}</td>"
        f"<td>{price_str}</td>"
        f"<td>{area_str}</td>"
        f"<td>{listing.source}</td>"
        f"</tr>"
    )


def _build_html(listings: list[Listing], price_drop_ids: FrozenSet[str] = frozenset()) -> str:
    rows = "\n".join(
        _build_listing_row(l, price_drop=l.id in price_drop_ids) for l in listings
    )
    return f"""
<html><body>
<h2>Nowe działki budowlane — Liszki / Czernichów</h2>
<p>Znaleziono <strong>{len(listings)}</strong> nowych ogłoszeń:</p>
<table border="1" cellpadding="6" cellspacing="0"
       style="border-collapse:collapse;font-family:sans-serif;font-size:14px">
  <thead style="background:#f0f0f0">
    <tr>
      <th>Tytuł</th><th>Lokalizacja</th><th>Cena</th><th>Powierzchnia</th><th>Serwis</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
</body></html>
"""


def _send(subject: str, html_body: str) -> None:
    """Send a single email via Resend.

    Args:
        subject: Email subject line.
        html_body: HTML body of the email.

    Raises:
        ValueError: If required env vars are not configured.
        Exception: On Resend API failure.
    """
    if not RESEND_API_KEY or not RESEND_FROM or not NOTIFY_EMAIL:
        raise ValueError(
            "RESEND_API_KEY, RESEND_FROM, and NOTIFY_EMAIL environment variables must be set"
        )

    resend.api_key = RESEND_API_KEY

    resend.Emails.send({
        "from": RESEND_FROM,
        "to": [NOTIFY_EMAIL],
        "subject": subject,
        "html": html_body,
    })

    logger.info("Email sent to %s: %s", NOTIFY_EMAIL, subject)


def send_new_listings_email(
    listings: list[Listing],
    price_drop_ids: FrozenSet[str] = frozenset(),
) -> None:
    """Send an email summarising newly found listings.

    Args:
        listings: All listings to include (new and price-dropped).
        price_drop_ids: IDs of listings whose price dropped — shown in red.
    """
    subject = f"Nowe działki ({len(listings)}) — Liszki / Czernichów"
    _send(subject, _build_html(listings, price_drop_ids))


def send_warning_email(message: str) -> None:
    """Send a plain warning email when no listings were found at all.

    Args:
        message: Warning text to include in the body.
    """
    html = f"<html><body><p><strong>Uwaga:</strong> {message}</p></body></html>"
    _send("realestate-assistant: ostrzeżenie", html)
