"""Email notifications via smtplib."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import NOTIFY_EMAIL, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
from scrapers.base import Listing

logger = logging.getLogger(__name__)


def _build_listing_row(listing: Listing) -> str:
    price_str = f"{listing.price:,.0f} zł".replace(",", " ") if listing.price else "–"
    area_str = f"{listing.area_m2:,.0f} m²".replace(",", " ") if listing.area_m2 else "–"
    return (
        f"<tr>"
        f"<td><a href='{listing.url}'>{listing.title}</a></td>"
        f"<td>{listing.location}</td>"
        f"<td>{price_str}</td>"
        f"<td>{area_str}</td>"
        f"<td>{listing.source}</td>"
        f"</tr>"
    )


def _build_html(listings: list[Listing]) -> str:
    rows = "\n".join(_build_listing_row(l) for l in listings)
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
    """Send a single email.

    Args:
        subject: Email subject line.
        html_body: HTML body of the email.

    Raises:
        ValueError: If SMTP credentials are not configured.
        smtplib.SMTPException: On send failure.
    """
    if not SMTP_USER or not SMTP_PASSWORD or not NOTIFY_EMAIL:
        raise ValueError(
            "SMTP_USER, SMTP_PASSWORD, and NOTIFY_EMAIL environment variables must be set"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, NOTIFY_EMAIL, msg.as_string())

    logger.info("Email sent to %s: %s", NOTIFY_EMAIL, subject)


def send_new_listings_email(listings: list[Listing]) -> None:
    """Send an email summarising newly found listings.

    Args:
        listings: New listings to include in the email.
    """
    subject = f"Nowe działki ({len(listings)}) — Liszki / Czernichów"
    html = _build_html(listings)
    _send(subject, html)


def send_warning_email(message: str) -> None:
    """Send a plain warning email when no listings were found at all.

    Args:
        message: Warning text to include in the body.
    """
    html = f"<html><body><p><strong>Uwaga:</strong> {message}</p></body></html>"
    _send("realestate-assistant: ostrzeżenie", html)
