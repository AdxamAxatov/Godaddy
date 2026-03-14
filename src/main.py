"""
╔══════════════════════════════════════════════════════╗
║        GoDaddy Domain + Website + Email Automation    ║
║  Telegram Bot → Purchase → Deploy → Create Email     ║
╚══════════════════════════════════════════════════════╝

Install dependencies:
    pip install requests playwright
    playwright install chromium

Run:
    python main.py
"""

import requests
import json
import logging
import os
import sys
import re
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOAD .env FILE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

_load_env()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION (loaded from .env)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── GoDaddy ──────────────────────────────────────────
GODADDY_API_KEY    = os.environ.get("GODADDY_API_KEY", "")
GODADDY_API_SECRET = os.environ.get("GODADDY_API_SECRET", "")
GODADDY_ENV        = os.environ.get("GODADDY_ENV", "ote")

# ── GoDaddy Registrant Contact ───────────────────────
REGISTRANT = {
    "nameFirst": os.environ.get("REGISTRANT_FIRST_NAME", ""),
    "nameLast":  os.environ.get("REGISTRANT_LAST_NAME", ""),
    "email":     os.environ.get("REGISTRANT_EMAIL", ""),
    "phone":     os.environ.get("REGISTRANT_PHONE", ""),
    "addressMailing": {
        "address1":   os.environ.get("REGISTRANT_ADDRESS", ""),
        "city":       os.environ.get("REGISTRANT_CITY", ""),
        "state":      os.environ.get("REGISTRANT_STATE", ""),
        "postalCode": os.environ.get("REGISTRANT_POSTAL_CODE", ""),
        "country":    os.environ.get("REGISTRANT_COUNTRY", "US"),
    },
}

# ── Telegram ─────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── cPanel accounts ────────────────────────────────
CPANEL_ACCOUNTS = []
for _i in range(1, 10):
    _url = os.environ.get(f"CPANEL_URL_{_i}", "")
    _user = os.environ.get(f"CPANEL_USERNAME_{_i}", "")
    _pass = os.environ.get(f"CPANEL_PASSWORD_{_i}", "")
    if _url and _user and _pass:
        CPANEL_ACCOUNTS.append({
            "url": _url, "username": _user, "password": _pass,
            "label": os.environ.get(f"CPANEL_LABEL_{_i}", f"Account {_i}"),
        })
    else:
        break

# ── GoDaddy Login accounts (for browser automation) ────
GODADDY_ACCOUNTS = []
for _i in range(1, 10):
    _email = os.environ.get(f"GODADDY_EMAIL_{_i}", "")
    _password = os.environ.get(f"GODADDY_PASSWORD_{_i}", "")
    if _email and _password:
        GODADDY_ACCOUNTS.append({"email": _email, "password": _password})
    else:
        break

# ── Logging ───────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent
LOG_FILE = str(_PROJECT_ROOT / "logs" / "automation.log")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOGGING SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def setup_logging():
    logger = logging.getLogger("automation")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

log = setup_logging()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TELEGRAM BOT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TG_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def tg_send(chat_id, text, reply_markup=None):
    """Send a message to a Telegram chat."""
    payload = {
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    resp = requests.post(f"{TG_BASE}/sendMessage", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def tg_answer_callback(callback_query_id):
    """Acknowledge a callback query (removes the loading spinner on the button)."""
    requests.post(f"{TG_BASE}/answerCallbackQuery",
                  json={"callback_query_id": callback_query_id}, timeout=10)


def tg_edit_message(chat_id, message_id, text):
    """Edit an existing message (used to update after button press)."""
    payload = {
        "chat_id":    chat_id,
        "message_id": message_id,
        "text":       text,
        "parse_mode": "Markdown",
    }
    requests.post(f"{TG_BASE}/editMessageText", json=payload, timeout=10)


def tg_send_photo(chat_id, photo_path, caption=None):
    """Send a photo to a Telegram chat."""
    with open(photo_path, "rb") as f:
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "Markdown"
        resp = requests.post(f"{TG_BASE}/sendPhoto", data=data,
                             files={"photo": f}, timeout=30)
    resp.raise_for_status()


def tg_send_document(chat_id, file_path, caption=None):
    """Send a document/file to a Telegram chat."""
    with open(file_path, "rb") as f:
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "Markdown"
        resp = requests.post(f"{TG_BASE}/sendDocument", data=data,
                             files={"document": f}, timeout=60)
    resp.raise_for_status()


def tg_delete_message(chat_id, message_id):
    """Delete a message (used to remove password messages for security)."""
    requests.post(f"{TG_BASE}/deleteMessage",
                  json={"chat_id": chat_id, "message_id": message_id}, timeout=10)


def tg_get_updates(offset=None):
    """Long-poll for new updates from Telegram."""
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    resp = requests.get(f"{TG_BASE}/getUpdates", params=params, timeout=35)
    resp.raise_for_status()
    return resp.json().get("result", [])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GODADDY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GODADDY_BASE = (
    "https://api.godaddy.com"
    if GODADDY_ENV == "production"
    else "https://api.ote-godaddy.com"
)

def _gd_headers():
    return {
        "Authorization": f"sso-key {GODADDY_API_KEY}:{GODADDY_API_SECRET}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def check_domain_availability(domain: str) -> tuple[bool, float]:
    """
    Check if a domain is available.
    Returns (available: bool, price_usd: float).
    """
    url  = f"{GODADDY_BASE}/v1/domains/available"
    resp = requests.get(url, headers=_gd_headers(), params={"domain": domain}, timeout=15)
    resp.raise_for_status()
    data      = resp.json()
    available = data.get("available", False)
    price     = data.get("price", 0) / 1_000_000  # GoDaddy returns micros
    return available, price


def purchase_domain(domain: str, years: int = 1) -> dict:
    """Purchase a domain on GoDaddy using the saved payment method on the account."""
    url = f"{GODADDY_BASE}/v1/domains/purchase"
    payload = {
        "domain":    domain,
        "period":    years,
        "renewAuto": True,
        "privacy":   False,
        "consent": {
            "agreedAt":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agreedBy":      REGISTRANT["email"],
            "agreementKeys": ["DNRA"],
        },
        "contactAdmin":      REGISTRANT,
        "contactBilling":    REGISTRANT,
        "contactRegistrant": REGISTRANT,
        "contactTech":       REGISTRANT,
    }
    resp = requests.post(url, headers=_gd_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CPANEL API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _cpanel_headers(account: dict):
    """Auth headers for cPanel API calls using API token."""
    return {
        "Authorization": f"cpanel {account['username']}:{account['password']}",
    }


def cpanel_get_main_domain(account: dict) -> str:
    """Get the primary/main domain from cPanel."""
    url = f"{account['url']}/execute/DomainInfo/list_domains"
    resp = requests.get(url, headers=_cpanel_headers(account), timeout=15, verify=True)
    resp.raise_for_status()
    result = resp.json()
    main_domain = result.get("data", {}).get("main_domain", "")
    log.debug(f"cPanel main domain: {main_domain}")
    return main_domain


def cpanel_create_domain(domain: str, account: dict) -> dict:
    """Add a domain to cPanel hosting (creates the folder in public_html)."""
    main_domain = cpanel_get_main_domain(account)

    url = f"{account['url']}/json-api/cpanel"
    params = {
        "cpanel_jsonapi_user": account["username"],
        "cpanel_jsonapi_apiversion": "2",
        "cpanel_jsonapi_module": "AddonDomain",
        "cpanel_jsonapi_func": "addaddondomain",
        "dir": f"public_html/{domain}",
        "newdomain": domain,
        "subdomain": domain.replace(".", ""),
        "rootdomain": main_domain,
    }
    resp = requests.get(url, params=params, headers=_cpanel_headers(account), timeout=30, verify=True)
    log.debug(f"cPanel addon domain response: {resp.status_code} {resp.text[:500]}")
    resp.raise_for_status()
    result = resp.json()

    cpdata = result.get("cpanelresult", {}).get("data", [{}])
    if cpdata and isinstance(cpdata, list) and len(cpdata) > 0:
        item = cpdata[0]
        if item.get("result") == 0:
            reason = item.get("reason", "Unknown error")
            result["errors"] = [reason]
        else:
            result["errors"] = None
    return result


def cpanel_upload_file(file_path: str, dest_dir: str, account: dict) -> dict:
    """Upload a file to cPanel via Fileman UAPI."""
    url = f"{account['url']}/execute/Fileman/upload_files"
    filename = Path(file_path).name
    with open(file_path, "rb") as f:
        files = {"file-1": (filename, f)}
        data = {"dir": dest_dir, "overwrite": "1"}
        resp = requests.post(url, data=data, files=files, headers=_cpanel_headers(account),
                             timeout=120, verify=True)
    resp.raise_for_status()
    result = resp.json()
    log.debug(f"cPanel upload response: {result}")
    return result


def cpanel_extract_file(archive_path: str, dest_dir: str, account: dict) -> dict:
    """Extract a zip/archive in cPanel via API2 Fileman::fileop."""
    url = f"{account['url']}/json-api/cpanel"
    params = {
        "cpanel_jsonapi_user": account["username"],
        "cpanel_jsonapi_apiversion": "2",
        "cpanel_jsonapi_module": "Fileman",
        "cpanel_jsonapi_func": "fileop",
        "op": "extract",
        "sourcefiles": archive_path,
        "destfiles": dest_dir,
    }
    resp = requests.get(url, params=params, headers=_cpanel_headers(account), timeout=120, verify=True)
    resp.raise_for_status()
    result = resp.json()
    log.debug(f"cPanel extract response: {result}")

    cpdata = result.get("cpanelresult", {}).get("data", [{}])
    if cpdata and isinstance(cpdata, list) and len(cpdata) > 0:
        item = cpdata[0]
        if item.get("result") == 0:
            reason = item.get("reason", "Unknown error")
            raise RuntimeError(f"cPanel extract error: {reason}")

    if result.get("cpanelresult", {}).get("error"):
        raise RuntimeError(f"cPanel extract error: {result['cpanelresult']['error']}")

    return result


def cpanel_delete_file(file_path: str, account: dict) -> dict:
    """Permanently delete a file on cPanel via API2 Fileman::fileop (skips trash)."""
    url = f"{account['url']}/json-api/cpanel"
    params = {
        "cpanel_jsonapi_user": account["username"],
        "cpanel_jsonapi_apiversion": "2",
        "cpanel_jsonapi_module": "Fileman",
        "cpanel_jsonapi_func": "fileop",
        "op": "unlink",
        "sourcefiles": file_path,
    }
    resp = requests.get(url, params=params, headers=_cpanel_headers(account), timeout=30, verify=True)
    resp.raise_for_status()
    result = resp.json()
    log.debug(f"cPanel delete response: {result}")
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TELEGRAM FILE DOWNLOAD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def tg_download_file(file_id: str, dest_path: str) -> str:
    """Download a file from Telegram by file_id, save to dest_path."""
    # Get file path from Telegram
    resp = requests.get(f"{TG_BASE}/getFile", params={"file_id": file_id}, timeout=10)
    resp.raise_for_status()
    file_path = resp.json()["result"]["file_path"]

    # Download the actual file
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    resp = requests.get(download_url, timeout=60)
    resp.raise_for_status()

    with open(dest_path, "wb") as f:
        f.write(resp.content)
    return dest_path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DOMAIN VALIDATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}$"
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BOT STATE — tracks what the bot is waiting for
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# When waiting for a zip upload, store the domain here
pending_website_domain = {}  # chat_id -> domain

# Email creation flow state
pending_email = {}  # chat_id -> {step, domain, username, first_name, ...}

# Domain purchase flow state
pending_buy = {}  # chat_id -> {"step": "awaiting_domain"}

# Active browser sessions (kept open after email creation)
active_browser = {}  # chat_id -> GoDaddyEmailBot instance

# Website generation flow state
pending_generate = {}  # chat_id -> {step, ...collected info}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BOT HANDLERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def handle_message(chat_id, text, message_id=None):
    """Handle an incoming text message."""
    raw_text = text.strip()
    text = raw_text.lower()

    if text == "/start":
        tg_send(chat_id,
                "👋 *GoDaddy Domain Bot*\n\n"
                "What I can do:\n"
                "• `/buy` → check availability & purchase a domain\n"
                "• `/setup` → add domain to hosting & deploy website\n"
                "• `/email` → create M365 email account\n"
                "• `/generate` → generate website + job description\n\n"
                "Example: `/buy` then `mysite.com`")
        return

    # Command: /cancel — cancel any active flow
    if text == "/cancel":
        cancelled = False
        if chat_id in pending_email:
            old = pending_email.pop(chat_id)
            if old.get("browser_bot"):
                old["browser_bot"].close()
            cancelled = True
        if chat_id in pending_website_domain:
            del pending_website_domain[chat_id]
            cancelled = True
        if chat_id in pending_buy:
            del pending_buy[chat_id]
            cancelled = True
        if chat_id in active_browser:
            active_browser.pop(chat_id).close()
            cancelled = True
        if chat_id in pending_generate:
            del pending_generate[chat_id]
            cancelled = True
        tg_send(chat_id, "🚫 Cancelled." if cancelled else "Nothing to cancel.")
        return

    # Command: /close — close the browser
    if text == "/close":
        bot = active_browser.pop(chat_id, None)
        if bot:
            bot.close()
            tg_send(chat_id, "🔒 Browser closed.")
            log.info("Browser closed via /close command")
        else:
            tg_send(chat_id, "No browser is open.")
        return

    # Command: /email — create email account
    if text == "/email" or text.startswith("/email "):
        domain = text.split(" ", 1)[1].strip() if " " in text else ""
        if domain:
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            _start_email_flow(chat_id, domain)
        else:
            pending_email[chat_id] = {"step": "awaiting_domain"}
            tg_send(chat_id, "📧 *Email Setup*\n\nWhat domain? Example: `mysite.com`")
        return

    # Route to email flow if user is in one
    if chat_id in pending_email:
        step = pending_email[chat_id].get("step", "")
        if step == "awaiting_domain":
            domain = text.strip()
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            pending_email.pop(chat_id)
            _start_email_flow(chat_id, domain)
            return
        if step in ("awaiting_username", "awaiting_name", "awaiting_password", "awaiting_notify_email"):
            _handle_email_input(chat_id, raw_text, message_id)
            return

    # Command: /setup — set up website on existing domain
    if text == "/setup" or text.startswith("/setup "):
        domain = text.split(" ", 1)[1].strip() if " " in text else ""
        if domain:
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            _start_website_setup(chat_id, domain)
        else:
            pending_website_domain[chat_id] = {"step": "awaiting_domain"}
            tg_send(chat_id, "🌐 *Website Setup*\n\nWhat domain? Example: `mysite.com`")
        return

    # Route to website flow if user is in one (awaiting domain)
    if chat_id in pending_website_domain:
        pending = pending_website_domain[chat_id]
        if isinstance(pending, dict) and pending.get("step") == "awaiting_domain":
            domain = text.strip()
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            del pending_website_domain[chat_id]
            _start_website_setup(chat_id, domain)
            return

    # Command: /buy — purchase a domain
    if text == "/buy" or text.startswith("/buy "):
        domain = text.split(" ", 1)[1].strip() if " " in text else ""
        if domain:
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            _check_and_buy_domain(chat_id, domain)
        else:
            pending_buy[chat_id] = {"step": "awaiting_domain"}
            tg_send(chat_id, "💰 *Domain Purchase*\n\nWhat domain? Example: `mysite.com`")
        return

    # Route to buy flow if user is in one (awaiting domain)
    if chat_id in pending_buy:
        if pending_buy[chat_id].get("step") == "awaiting_domain":
            domain = text.strip()
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            del pending_buy[chat_id]
            _check_and_buy_domain(chat_id, domain)
            return

    # Command: /generate — generate website + job description
    if text == "/generate":
        pending_generate[chat_id] = {"step": "awaiting_company_name"}
        tg_send(chat_id, "🏗️ *Website Generator*\n\nWhat's the company name?\nExample: `2-3 Logistics Corp`")
        return

    # Route to generate flow if user is in one
    if chat_id in pending_generate:
        _handle_generate_input(chat_id, raw_text)
        return

    tg_send(chat_id, "⚠️ Unknown command. Use `/buy`, `/setup`, `/email`, `/generate`, or `/start`.")


def _check_and_buy_domain(chat_id, domain):
    """Check domain availability and show Buy/Cancel buttons."""
    log.info(f"Domain requested: {domain}")

    tg_send(chat_id, f"🔍 Checking availability of `{domain}`...")
    try:
        available, price = check_domain_availability(domain)
    except requests.HTTPError as e:
        msg = f"GoDaddy API error: {e}"
        log.error(msg)
        tg_send(chat_id, f"🔴 {msg}")
        return

    if not available:
        tg_send(chat_id, f"❌ `{domain}` is not available for purchase.")
        return

    # Show price and Buy/Cancel buttons
    tg_send(
        chat_id,
        f"✅ `{domain}` is available — *${price:.2f}/year*\n\n"
        f"Purchase this domain?",
        reply_markup={
            "inline_keyboard": [[
                {"text": "💰 Buy", "callback_data": f"buy:{domain}"},
                {"text": "❌ Cancel", "callback_data": "cancel"},
            ]]
        },
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WEBSITE GENERATION FLOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GENERATE_STEPS = [
    ("awaiting_company_name", "company_name", "What's the short name for the logo?\nExample: `2-3 Logistics`"),
    ("awaiting_company_short", "company_short", "What's the domain?\nExample: `2-3logisticscorp.com`"),
    ("awaiting_domain", "domain", "Contact email?\nExample: `info@2-3logisticscorp.com`"),
    ("awaiting_email", "email", "Street address?\nExample: `508 Linden Dr`"),
    ("awaiting_address", "address", "City, State, Zip?\nExample: `Round Lake, IL 60073`"),
    ("awaiting_city_state", "city_state", "Job title?\nExample: `OTR Company Driver — CDL-A`"),
    ("awaiting_job_title", "job_title", "Pay range?\nExample: `$1,300 – $1,600 / week`"),
    ("awaiting_pay_range", "pay_range", "Home time?\nExample: `Home every 2 weeks for 2 days`"),
    ("awaiting_home_time", "home_time", "Home time short (for card)?\nExample: `2 Weeks Out`"),
    ("awaiting_home_time_short", "home_time_short", "Home time detail (card subtitle)?\nExample: `Home 2 Days`"),
    ("awaiting_home_time_detail", "home_time_detail", "Minimum experience?\nExample: `6 months`"),
    ("awaiting_min_exp", "min_experience", "Now list the perks/benefits, one per line.\nWhen done, send `done`.\n\nExample:\n`Weekly direct deposit\nHealth insurance\n401(k) with match`"),
]


def _handle_generate_input(chat_id, raw_text):
    """Process text input during website generation flow."""
    state = pending_generate[chat_id]
    step = state["step"]

    # Handle perks collection
    if step == "awaiting_perks":
        if raw_text.strip().lower() == "done":
            _finish_generate(chat_id)
            return
        # Add perks (support multiple lines in one message)
        perks = state.get("perks", [])
        for line in raw_text.strip().splitlines():
            line = line.strip()
            if line:
                perks.append(line)
        state["perks"] = perks
        tg_send(chat_id, f"Added {len(perks)} perk(s) so far. Send more or send `done` to finish.")
        return

    # Walk through the steps
    for i, (step_name, field, next_prompt) in enumerate(GENERATE_STEPS):
        if step == step_name:
            state[field] = raw_text.strip()
            # Move to next step
            if i + 1 < len(GENERATE_STEPS):
                next_step = GENERATE_STEPS[i + 1][0]
                state["step"] = next_step
                tg_send(chat_id, next_prompt)
            else:
                # Last step done — move to perks
                state["step"] = "awaiting_perks"
                state["perks"] = []
                tg_send(chat_id, "Now list the perks/benefits, one per line.\nWhen done, send `done`.\n\nExample:\n`Weekly direct deposit\nHealth insurance\n401(k) with match`")
            return


def _finish_generate(chat_id):
    """Generate the website and job description, send to user."""
    state = pending_generate.pop(chat_id)
    tg_send(chat_id, "⏳ Generating website and job description...")

    try:
        from website_generator import generate_website, generate_job_description

        info = {
            "company_name": state["company_name"],
            "company_short": state["company_short"],
            "domain": state["domain"],
            "email": state["email"],
            "address": state["address"],
            "city_state": state["city_state"],
            "job_title": state["job_title"],
            "pay_range": state["pay_range"],
            "home_time": state["home_time"],
            "home_time_short": state["home_time_short"],
            "home_time_detail": state["home_time_detail"],
            "min_experience": state.get("min_experience", "6 months"),
            "fourth_card_value": state.get("min_experience", "6 Mo. Exp"),
            "fourth_card_label": "Min. Required",
            "routes": "48 States",
            "routes_type": "OTR Routes",
            "perks": state.get("perks", []),
        }

        # Generate website zip
        zip_path = generate_website(info)
        log.info(f"Website generated: {zip_path}")

        # Generate job description
        job_desc = generate_job_description(info)

        # Send zip file
        tg_send_document(chat_id, zip_path, caption=f"🌐 *Website for* `{state['domain']}`")

        # Send job description as text
        # Split if too long for Telegram (4096 char limit)
        if len(job_desc) <= 4000:
            tg_send(chat_id, f"📋 *Indeed Job Description:*\n\n{job_desc}")
        else:
            # Send in chunks
            tg_send(chat_id, "📋 *Indeed Job Description:*")
            for i in range(0, len(job_desc), 4000):
                tg_send(chat_id, job_desc[i:i+4000])

        # Clean up
        try:
            os.remove(zip_path)
        except OSError:
            pass

        log.info(f"Website + job desc sent for {state['domain']}")

    except Exception as e:
        log.error(f"Website generation failed: {e}")
        tg_send(chat_id, f"🔴 Generation failed:\n`{e}`")


def _start_website_setup(chat_id, domain, account_idx=None):
    """Start the website setup flow — pick account if needed, then create domain."""
    log.info(f"Website setup started for: {domain}")

    if len(CPANEL_ACCOUNTS) == 0:
        tg_send(chat_id, "🔴 No cPanel accounts configured in `.env`")
        return

    if account_idx is None and len(CPANEL_ACCOUNTS) > 1:
        # Show account picker
        pending_website_domain[chat_id] = {"domain": domain, "step": "awaiting_account"}
        buttons = []
        for i, acc in enumerate(CPANEL_ACCOUNTS):
            buttons.append([{"text": acc["label"], "callback_data": f"cpanel_acc:{i}:{domain}"}])
        tg_send(chat_id,
                f"🌐 *Website Setup for* `{domain}`\n\nWhich hosting account?",
                reply_markup={"inline_keyboard": buttons})
        return

    # Single account or account already chosen
    if account_idx is None:
        account_idx = 0
    account = CPANEL_ACCOUNTS[account_idx]

    tg_send(chat_id, f"🌐 Adding `{domain}` to hosting ({account['label']})...")

    try:
        result = cpanel_create_domain(domain, account)
        errors = result.get("errors")
        if errors:
            error_msg = str(errors)
            if "already" in error_msg.lower() or "exists" in error_msg.lower():
                log.info(f"Domain {domain} already exists in cPanel, continuing...")
                tg_send(chat_id, f"ℹ️ `{domain}` already exists in hosting. Continuing...")
            else:
                log.error(f"cPanel domain creation failed: {error_msg}")
                tg_send(chat_id, f"🔴 Failed to add domain to hosting:\n`{error_msg}`")
                return
        else:
            tg_send(chat_id, f"✅ `{domain}` added to hosting!")
    except Exception as e:
        log.error(f"cPanel create domain error: {e}")
        tg_send(chat_id, f"🔴 Failed to add domain to hosting:\n`{e}`")
        return

    # Ask for the zip file — store domain + account index
    pending_website_domain[chat_id] = {"domain": domain, "account_idx": account_idx}
    tg_send(chat_id,
            f"📦 Now send me the `.zip` file with your website files "
            f"(HTML, CSS, images).\n\n"
            f"The contents will be deployed to `{domain}`.")


def handle_document(chat_id, document, message):
    """Handle a file/document upload (zip file for website deployment)."""
    pending = pending_website_domain.get(chat_id)

    if not pending or not isinstance(pending, dict) or "domain" not in pending:
        tg_send(chat_id,
                "📁 Got a file, but I'm not expecting one right now.\n\n"
                "To deploy a website, first use `/setup domain.com`")
        return

    domain = pending["domain"]
    account = CPANEL_ACCOUNTS[pending.get("account_idx", 0)]

    file_name = document.get("file_name", "")
    if not file_name.lower().endswith(".zip"):
        tg_send(chat_id, "⚠️ Please send a `.zip` file.")
        return

    file_id = document["file_id"]
    log.info(f"Received zip file '{file_name}' for domain '{domain}'")
    tg_send(chat_id, f"📥 Downloading `{file_name}`...")

    # Download from Telegram
    tmp_dir = tempfile.mkdtemp()
    local_zip = os.path.join(tmp_dir, file_name)
    try:
        tg_download_file(file_id, local_zip)
    except Exception as e:
        log.error(f"Failed to download file from Telegram: {e}")
        tg_send(chat_id, f"🔴 Failed to download file: `{e}`")
        return

    # Upload to cPanel
    dest_dir = f"/public_html/{domain}"
    tg_send(chat_id, f"📤 Uploading to `{dest_dir}`...")
    try:
        cpanel_upload_file(local_zip, dest_dir, account)
        log.info(f"Uploaded {file_name} to {dest_dir}")
    except Exception as e:
        log.error(f"cPanel upload failed: {e}")
        tg_send(chat_id, f"🔴 Upload failed:\n`{e}`")
        return
    finally:
        try:
            os.remove(local_zip)
            os.rmdir(tmp_dir)
        except OSError:
            pass

    # Extract the zip on cPanel
    archive_path = f"{dest_dir}/{file_name}"
    tg_send(chat_id, f"📂 Extracting `{file_name}`...")
    try:
        cpanel_extract_file(archive_path, dest_dir, account)
        log.info(f"Extracted {file_name} in {dest_dir}")
    except Exception as e:
        log.error(f"cPanel extract failed: {e}")
        tg_send(chat_id, f"🔴 Extraction failed:\n`{e}`")
        return

    # Delete the zip from cPanel (permanently, skip trash)
    try:
        cpanel_delete_file(archive_path, account)
        log.info(f"Deleted {archive_path} from cPanel")
    except Exception as e:
        log.warning(f"Failed to delete zip from cPanel: {e}")

    # Done!
    del pending_website_domain[chat_id]
    log.info(f"Website deployed for {domain}")
    tg_send(chat_id,
            f"✅ *Website deployed!*\n\n"
            f"Domain: `{domain}`\n"
            f"Files extracted to: `{dest_dir}`\n\n"
            f"Your site should be live at: http://{domain}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EMAIL CREATION FLOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _start_email_flow(chat_id, domain):
    """Start the email account creation flow."""
    # Clean up any existing email flow
    old = pending_email.pop(chat_id, None)
    if old and old.get("browser_bot"):
        old["browser_bot"].close()

    pending_email[chat_id] = {"step": "awaiting_account", "domain": domain}
    log.info(f"Email setup started for: {domain}")

    if len(GODADDY_ACCOUNTS) == 1:
        # Only one account — skip selection
        pending_email[chat_id]["account_idx"] = 0
        pending_email[chat_id]["step"] = "awaiting_username"
        tg_send(chat_id,
                f"📧 *Email Setup for* `{domain}`\n\n"
                f"What username do you want?\n"
                f"Example: type `info` for `info@{domain}`")
    elif len(GODADDY_ACCOUNTS) > 1:
        # Show account picker
        buttons = []
        for i, acc in enumerate(GODADDY_ACCOUNTS):
            buttons.append([{"text": f"Account {i+1}: {acc['email']}", "callback_data": f"email_acc:{i}"}])
        tg_send(chat_id,
                f"📧 *Email Setup for* `{domain}`\n\n"
                f"Which GoDaddy account?",
                reply_markup={"inline_keyboard": buttons})
    else:
        tg_send(chat_id, "🔴 No GoDaddy accounts configured in `.env`")
        pending_email.pop(chat_id, None)


def _handle_email_input(chat_id, raw_text, message_id=None):
    """Process text input during email creation flow."""
    state = pending_email[chat_id]
    step = state["step"]

    if step == "awaiting_username":
        username = raw_text.strip().lower().replace(" ", "")
        state["username"] = username
        state["step"] = "awaiting_name"
        tg_send(chat_id,
                f"Email: `{username}@{state['domain']}`\n\n"
                f"👤 First and last name?\n"
                f"Example: `John Doe`")

    elif step == "awaiting_name":
        parts = raw_text.strip().split(None, 1)
        if len(parts) < 2:
            tg_send(chat_id, "⚠️ Need both first and last name. Example: `John Doe`")
            return
        state["first_name"] = parts[0]
        state["last_name"] = parts[1]
        state["step"] = "awaiting_admin"
        tg_send(chat_id,
                "🔐 *Administrator permissions?*",
                reply_markup={
                    "inline_keyboard": [[
                        {"text": "Yes", "callback_data": "email_admin:yes"},
                        {"text": "No", "callback_data": "email_admin:no"},
                    ]]
                })

    elif step == "awaiting_password":
        state["password"] = raw_text.strip()
        state["step"] = "awaiting_notify_email"
        # Delete the password message for security
        if message_id:
            try:
                tg_delete_message(chat_id, message_id)
            except Exception:
                pass
        default_email = REGISTRANT.get("email", "")
        tg_send(chat_id,
                f"📬 Send account info to which email?\n\n"
                f"Default: `{default_email}`",
                reply_markup={
                    "inline_keyboard": [[
                        {"text": f"Use {default_email}", "callback_data": "email_notify:default"},
                    ]]
                })

    elif step == "awaiting_notify_email":
        state["notify_email"] = raw_text.strip()
        _launch_email_browser(chat_id)


def _launch_email_browser(chat_id):
    """Open browser, login, navigate to form, scrape expiration dates."""
    state = pending_email[chat_id]
    domain = state["domain"]

    account = GODADDY_ACCOUNTS[state.get("account_idx", 0)]
    tg_send(chat_id, f"⏳ Opening browser and navigating to GoDaddy ({account['email']})...")

    try:
        from email_automation import GoDaddyEmailBot
        bot = GoDaddyEmailBot(
            email=account["email"],
            password=account["password"],
            account_idx=state.get("account_idx", 0),
            headless=False,
        )
        bot.open()
        bot.go_to_create_email(domain)

        dates = bot.get_expiration_dates()
        state["browser_bot"] = bot
        state["expiration_dates"] = dates
        state["step"] = "awaiting_expiration"

        # Show dates as buttons
        buttons = []
        for i, date in enumerate(dates):
            buttons.append([{"text": date, "callback_data": f"email_exp:{i}"}])

        tg_send(chat_id,
                "📅 Choose an expiration/renewal date:",
                reply_markup={"inline_keyboard": buttons})

    except Exception as e:
        log.error(f"Email browser automation failed: {e}")
        tg_send(chat_id, f"🔴 Browser automation failed:\n`{e}`")
        cleanup = pending_email.pop(chat_id, {})
        if cleanup.get("browser_bot"):
            cleanup["browser_bot"].close()


def _fill_and_confirm(chat_id, message_id):
    """Fill the email form and show confirmation with screenshot."""
    state = pending_email[chat_id]
    bot = state["browser_bot"]

    tg_edit_message(chat_id, message_id, f"📅 Expiration: {state['expiration_text']}")
    tg_send(chat_id, "⏳ Filling in the form...")

    try:
        bot.fill_form(
            username=state["username"],
            first_name=state["first_name"],
            last_name=state["last_name"],
            admin=state["admin"],
            expiration_idx=state["expiration_idx"],
            password=state["password"],
            notify_email=state["notify_email"],
        )

        # Take screenshot
        screenshot_path = os.path.join(tempfile.gettempdir(), f"email_form_{chat_id}.png")
        bot.screenshot(screenshot_path)

        # Send summary + screenshot
        summary = (
            f"📋 *Email Account Summary*\n\n"
            f"Email: `{state['username']}@{state['domain']}`\n"
            f"Name: {state['first_name']} {state['last_name']}\n"
            f"Admin: {'Yes' if state['admin'] else 'No'}\n"
            f"Expiration: {state['expiration_text']}\n"
            f"Notify: {state['notify_email']}\n\n"
            f"Ready to create?"
        )

        tg_send_photo(chat_id, screenshot_path, caption=summary)
        tg_send(chat_id, "Confirm creation?",
                reply_markup={
                    "inline_keyboard": [[
                        {"text": "✅ Create", "callback_data": "email_confirm"},
                        {"text": "❌ Cancel", "callback_data": "email_cancel"},
                    ]]
                })

        state["step"] = "awaiting_confirmation"

        # Clean up screenshot file
        try:
            os.remove(screenshot_path)
        except OSError:
            pass

    except Exception as e:
        log.error(f"Form fill failed: {e}")
        tg_send(chat_id, f"🔴 Failed to fill form:\n`{e}`")
        bot.close()
        pending_email.pop(chat_id, None)


def _submit_email(chat_id):
    """Submit the email creation form."""
    state = pending_email.get(chat_id, {})
    bot = state.get("browser_bot")

    if not bot:
        tg_send(chat_id, "🔴 Browser session expired. Start over with `/email domain.com`")
        pending_email.pop(chat_id, None)
        return

    tg_send(chat_id, "⏳ Creating email account...")

    try:
        bot.submit()

        # Take final screenshot
        screenshot_path = os.path.join(tempfile.gettempdir(), f"email_result_{chat_id}.png")
        bot.screenshot(screenshot_path)

        tg_send_photo(chat_id, screenshot_path,
                      caption=(f"✅ *Email account created!*\n\n"
                               f"Email: `{state['username']}@{state['domain']}`\n"
                               f"Name: {state['first_name']} {state['last_name']}"))

        try:
            os.remove(screenshot_path)
        except OSError:
            pass

        log.info(f"Email created: {state['username']}@{state['domain']}")

        # Keep browser open — let user decide
        active_browser[chat_id] = bot
        pending_email.pop(chat_id, None)
        tg_send(chat_id, "Keep the browser open?",
                reply_markup={
                    "inline_keyboard": [[
                        {"text": "🔒 Close Browser", "callback_data": "browser_close"},
                        {"text": "👀 Keep Open", "callback_data": "browser_keep"},
                    ]]
                })

    except Exception as e:
        log.error(f"Email creation submit failed: {e}")
        tg_send(chat_id, f"🔴 Email creation failed:\n`{e}`")
        bot.close()
        pending_email.pop(chat_id, None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CALLBACK HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def handle_callback(callback_query_id, chat_id, message_id, data):
    """Handle an inline button press."""
    tg_answer_callback(callback_query_id)

    if data == "cancel":
        tg_edit_message(chat_id, message_id, "🚫 Purchase cancelled.")
        log.info("User cancelled purchase.")
        return

    if data.startswith("buy:"):
        domain = data.split(":", 1)[1]
        tg_edit_message(chat_id, message_id, f"⏳ Purchasing `{domain}`...")

        try:
            order = purchase_domain(domain)
            order_id = order.get("orderId", "N/A")
            log.info(f"Domain purchased: {domain} | Order ID: {order_id}")
            tg_send(chat_id,
                    f"✅ *Domain purchased!*\n\n"
                    f"Domain: `{domain}`\n"
                    f"Order ID: `{order_id}`\n\n"
                    f"Set up website now?",
                    reply_markup={
                        "inline_keyboard": [[
                            {"text": "🌐 Setup Website", "callback_data": f"setup:{domain}"},
                            {"text": "⏭ Skip", "callback_data": "cancel"},
                        ]]
                    })
        except requests.HTTPError as e:
            body = e.response.text if e.response else str(e)
            log.error(f"Purchase failed for '{domain}': {body}")
            tg_send(chat_id, f"🔴 Purchase failed for `{domain}`\n\n`{body}`")
        return

    if data.startswith("setup:"):
        domain = data.split(":", 1)[1]
        tg_edit_message(chat_id, message_id, f"✅ Domain purchased! Setting up website for `{domain}`...")
        _start_website_setup(chat_id, domain)
        return

    if data.startswith("cpanel_acc:"):
        parts = data.split(":", 2)
        idx = int(parts[1])
        domain = parts[2]
        acc = CPANEL_ACCOUNTS[idx]
        tg_edit_message(chat_id, message_id, f"Hosting: {acc['label']}")
        _start_website_setup(chat_id, domain, account_idx=idx)
        return

    # ── Email flow callbacks ──────────────────────────
    if data.startswith("email_acc:"):
        state = pending_email.get(chat_id)
        if not state:
            return
        idx = int(data.split(":")[1])
        state["account_idx"] = idx
        state["step"] = "awaiting_username"
        acc = GODADDY_ACCOUNTS[idx]
        tg_edit_message(chat_id, message_id, f"Account: {acc['email']}")
        tg_send(chat_id,
                f"What username do you want?\n"
                f"Example: type `info` for `info@{state['domain']}`")
        return

    if data.startswith("email_admin:"):
        choice = data.split(":")[1]
        state = pending_email.get(chat_id)
        if not state:
            return
        state["admin"] = (choice == "yes")
        state["step"] = "awaiting_password"
        tg_edit_message(chat_id, message_id, f"Admin: {'Yes' if state['admin'] else 'No'}")
        tg_send(chat_id, "🔑 Create a password for this email account:")
        return

    if data.startswith("email_notify:"):
        state = pending_email.get(chat_id)
        if not state:
            return
        if data == "email_notify:default":
            state["notify_email"] = REGISTRANT.get("email", "")
        tg_edit_message(chat_id, message_id, f"Notify: {state['notify_email']}")
        _launch_email_browser(chat_id)
        return

    if data.startswith("email_exp:"):
        state = pending_email.get(chat_id)
        if not state:
            return
        idx = int(data.split(":")[1])
        state["expiration_idx"] = idx
        state["expiration_text"] = state.get("expiration_dates", [])[idx]
        _fill_and_confirm(chat_id, message_id)
        return

    if data == "email_confirm":
        _submit_email(chat_id)
        return

    if data == "email_cancel":
        state = pending_email.pop(chat_id, {})
        bot = state.get("browser_bot")
        if bot:
            bot.close()
        tg_edit_message(chat_id, message_id, "🚫 Email creation cancelled.")
        return

    # ── Browser close/keep callbacks ─────────────────
    if data == "browser_close":
        bot = active_browser.pop(chat_id, None)
        if bot:
            bot.close()
        tg_edit_message(chat_id, message_id, "🔒 Browser closed.")
        log.info("Browser closed via button")
        return

    if data == "browser_keep":
        tg_edit_message(chat_id, message_id, "👀 Browser kept open. Use `/close` to close it later.")
        return

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN LOOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def tg_set_commands():
    """Register bot commands so they appear in Telegram's menu."""
    commands = [
        {"command": "start", "description": "Show welcome message"},
        {"command": "buy", "description": "Purchase a domain"},
        {"command": "email", "description": "Create M365 email account"},
        {"command": "setup", "description": "Deploy website to hosting"},
        {"command": "generate", "description": "Generate website + job description"},
        {"command": "close", "description": "Close the browser"},
        {"command": "cancel", "description": "Cancel current operation"},
    ]
    try:
        requests.post(f"{TG_BASE}/setMyCommands",
                      json={"commands": commands}, timeout=10)
        log.info("Bot commands registered with Telegram")
    except Exception as e:
        log.warning(f"Failed to register commands: {e}")


def run():
    log.info("Bot started. Listening for messages...")
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║   GoDaddy Domain Bot (Telegram)                  ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print(f"  Logs        → {LOG_FILE}")
    print(f"  Environment → {GODADDY_ENV} ({'SANDBOX - no real charges' if GODADDY_ENV == 'ote' else 'PRODUCTION - real money!'})")
    print(f"  Chat ID     → {TELEGRAM_CHAT_ID}")
    print()
    print("  Bot is running! Open your Telegram bot and send a domain name.")
    print("  Example: mysite.com")
    print()
    print("  Press Ctrl+C to stop.\n")

    # Register commands so they show in Telegram's menu
    tg_set_commands()

    # Flush old updates that arrived while bot was offline
    try:
        stale = tg_get_updates(offset=None)
        if stale:
            offset = stale[-1]["update_id"] + 1
            log.info(f"Skipped {len(stale)} stale update(s) from while bot was offline.")
        else:
            offset = None
    except Exception:
        offset = None

    # Send a startup message to Telegram so user knows the bot is ready
    try:
        tg_send(TELEGRAM_CHAT_ID,
                "🤖 *Bot is online!*\n\n"
                "`/buy` — purchase a domain\n"
                "`/setup` — deploy a website\n"
                "`/email` — create an email account\n"
                "`/generate` — generate website + job description")
        log.info("Startup message sent to Telegram")
    except Exception as e:
        log.error(f"Failed to send startup message: {e}")

    while True:
        try:
            updates = tg_get_updates(offset)
        except Exception as e:
            log.warning(f"Polling error: {e}")
            time.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1

            # Only respond to the authorized chat
            if "message" in update:
                msg = update["message"]
                chat_id = msg["chat"]["id"]
                if str(chat_id) != str(TELEGRAM_CHAT_ID):
                    continue

                # Handle file uploads (zip for website deployment)
                if "document" in msg:
                    handle_document(chat_id, msg["document"], msg)
                    continue

                text = msg.get("text", "")
                if text:
                    handle_message(chat_id, text, msg.get("message_id"))

            elif "callback_query" in update:
                cb = update["callback_query"]
                chat_id = cb["message"]["chat"]["id"]
                if str(chat_id) != str(TELEGRAM_CHAT_ID):
                    continue
                handle_callback(
                    cb["id"],
                    chat_id,
                    cb["message"]["message_id"],
                    cb.get("data", ""),
                )


if __name__ == "__main__":
    run()
