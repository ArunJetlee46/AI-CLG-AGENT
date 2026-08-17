"""Lightweight email sender using stdlib smtplib.

Falls back to logging when SMTP is not configured.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    s = get_settings()
    return s.email_enabled and bool(s.email_user and s.email_password)


def send_email(to: str, subject: str, html_body: str, plain_body: str = "") -> bool:
    """Send an HTML email. Returns True if sent, False if skipped."""
    s = get_settings()
    if not _smtp_configured():
        logger.info("Email skipped (SMTP not configured): to=%s subject=%s", to, subject)
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = s.email_from
    msg["To"] = to
    msg["Subject"] = subject
    if plain_body:
        msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(s.email_host, s.email_port) as server:
            server.starttls()
            server.login(s.email_user, s.email_password)
            server.sendmail(s.email_from, [to], msg.as_string())
        logger.info("Email sent: to=%s subject=%s", to, subject)
        return True
    except Exception:
        logger.exception("Email send failed: to=%s subject=%s", to, subject)
        return False


def drive_announcement(to: str, drive_title: str, company: str, drive_date: str, mode: str, location: str) -> bool:
    subject = f"New Placement Drive: {company} — {drive_title}"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:#16a34a;">New Placement Drive</h2>
      <p>You have been invited to participate in a new placement drive.</p>
      <table style="border-collapse:collapse;width:100%;">
        <tr><td style="padding:6px 12px;font-weight:600;">Company</td><td style="padding:6px 12px;">{company}</td></tr>
        <tr><td style="padding:6px 12px;font-weight:600;">Role</td><td style="padding:6px 12px;">{drive_title}</td></tr>
        <tr><td style="padding:6px 12px;font-weight:600;">Date</td><td style="padding:6px 12px;">{drive_date}</td></tr>
        <tr><td style="padding:6px 12px;font-weight:600;">Mode</td><td style="padding:6px 12px;">{mode}</td></tr>
        <tr><td style="padding:6px 12px;font-weight:600;">Location</td><td style="padding:6px 12px;">{location}</td></tr>
      </table>
      <p style="margin-top:16px;">Log in to the campus portal to view details and prepare.</p>
    </div>"""
    plain = f"New Placement Drive: {company} — {drive_title}\nDate: {drive_date}\nMode: {mode}\nLocation: {location}"
    return send_email(to, subject, html, plain)


def offer_email(to: str, company: str, drive_title: str, ctc: float, status: str) -> bool:
    subject = f"Placement Offer {'Update' if status == 'offered' else status.title()}: {company}"
    color = "#16a34a" if status == "offered" else "#dc2626"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:{color};">Placement Offer — {status.title()}</h2>
      <p>You have received a placement offer from <strong>{company}</strong>.</p>
      <table style="border-collapse:collapse;width:100%;">
        <tr><td style="padding:6px 12px;font-weight:600;">Company</td><td style="padding:6px 12px;">{company}</td></tr>
        <tr><td style="padding:6px 12px;font-weight:600;">Role</td><td style="padding:6px 12px;">{drive_title}</td></tr>
        <tr><td style="padding:6px 12px;font-weight:600;">CTC</td><td style="padding:6px 12px;">{ctc} LPA</td></tr>
      </table>
      <p style="margin-top:16px;">Log in to accept or decline this offer.</p>
    </div>"""
    plain = f"Placement Offer: {company}\nRole: {drive_title}\nCTC: {ctc} LPA\nStatus: {status}"
    return send_email(to, subject, html, plain)


def application_status_email(to: str, drive_title: str, company: str, new_status: str) -> bool:
    subject = f"Application Update: {company} — {new_status.title()}"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;">
      <h2 style="color:#2563eb;">Application Update</h2>
      <p>Your application for <strong>{drive_title}</strong> at <strong>{company}</strong> has been updated.</p>
      <p style="font-size:16px;margin-top:12px;">Status: <strong>{new_status.upper()}</strong></p>
    </div>"""
    plain = f"Application Update: {company} — {drive_title}\nStatus: {new_status}"
    return send_email(to, subject, html, plain)
