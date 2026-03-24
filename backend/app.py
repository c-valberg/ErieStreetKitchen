"""Flask backend for Erie Street Kitchen.

Serves static frontend files and exposes two API endpoints:
  GET  /api/specials  — proxies Google Sheets CSV, returns JSON
  POST /api/catering  — accepts catering form submission, sends email notification
"""

import csv
import io
import json
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# load_dotenv()
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent

app = Flask(__name__, static_folder=str(BASE_DIR))
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SHEET_CSV_URL = os.getenv(
    "SHEET_CSV_URL",
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTPi0s2uJDoUE-5hvQa9AEBd8jZykMXsbPqzDbVakRQIBoWIVeArjpamnz1doc0as09t9cKR7ExSDRh"
    "/pub?gid=0&single=true&output=csv",
)

SUBMISSIONS_FILE = BASE_DIR / "backend" / "submissions.json"


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(str(BASE_DIR), filename)


# ---------------------------------------------------------------------------
# API — Specials
# ---------------------------------------------------------------------------

@app.route("/api/specials")
def get_specials():
    """Fetch the published Google Sheet CSV and return rows as JSON.

    Returns:
        JSON array of row objects keyed by the sheet's header row.
    """
    try:
        resp = requests.get(SHEET_CSV_URL, timeout=10)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = [
            {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            for row in reader
        ]
        if not rows:
            return jsonify({"error": "Sheet is empty"}), 404
        return jsonify(rows)
    except requests.RequestException as exc:
        logger.error("Failed to fetch Google Sheet: %s", exc)
        return jsonify({"error": "Could not load specials"}), 502


# ---------------------------------------------------------------------------
# API — Catering form submission
# ---------------------------------------------------------------------------

@app.route("/api/catering", methods=["POST"])
def submit_catering():
    """Accept a catering inquiry and send an email notification.

    Expects a JSON body with keys: firstName, lastName, email, phone,
    eventDate, eventTime, guestCount, eventType, location, notes, menuItems.

    Returns:
        JSON with {success: true} on success, or {error: str} on failure.
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    required = ["firstName", "lastName", "email", "phone", "eventDate", "location"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 422

    _save_submission(data)

    email_sent = _send_notification_email(data)
    if not email_sent:
        logger.warning("Email notification not sent — check SMTP config in .env")

    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_submission(data: dict) -> None:
    """Append the submission to a local JSON log file as a fallback record."""
    submissions = []
    if SUBMISSIONS_FILE.exists():
        try:
            submissions = json.loads(SUBMISSIONS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            submissions = []

    submissions.append({**data, "submittedAt": datetime.utcnow().isoformat() + "Z"})
    SUBMISSIONS_FILE.write_text(
        json.dumps(submissions, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Catering submission saved to %s", SUBMISSIONS_FILE)


def _send_notification_email(data: dict) -> bool:
    """Send an email notification for a new catering request.

    Reads SMTP config from environment variables. Returns True if sent.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    notify_email = os.getenv("NOTIFY_EMAIL")

    if not all([smtp_host, smtp_user, smtp_pass, notify_email]):
        return False

    menu_items = ", ".join(data.get("menuItems", [])) or "None selected"

    subject = (
        f"New Catering Request — {data.get('firstName')} {data.get('lastName')} "
        f"on {data.get('eventDate')}"
    )

    body = f"""\
New catering request received via the website.

--- Contact ---
Name:   {data.get('firstName')} {data.get('lastName')}
Email:  {data.get('email')}
Phone:  {data.get('phone')}

--- Event ---
Date:         {data.get('eventDate')}
Time:         {data.get('eventTime', 'N/A')}
Guests:       {data.get('guestCount', 'N/A')}
Type:         {data.get('eventType', 'N/A')}
Location:     {data.get('location')}

--- Menu Selections ---
{menu_items}

--- Notes ---
{data.get('notes') or 'None'}

---
Submitted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = notify_email
    msg["Subject"] = subject
    msg["Reply-To"] = data.get("email", smtp_user)
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, notify_email, msg.as_string())
        logger.info("Notification email sent to %s", notify_email)
        return True
    except smtplib.SMTPException as exc:
        logger.error("SMTP error: %s", exc)
        return False


if __name__ == "__main__":
    app.run(debug=True, port=5000)
