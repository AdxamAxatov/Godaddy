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
    env_path = Path(__file__).parent / ".env"
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

# ── cPanel ─────────────────────────────────────────
CPANEL_URL      = os.environ.get("CPANEL_URL", "")
CPANEL_USERNAME = os.environ.get("CPANEL_USERNAME", "")
CPANEL_PASSWORD = os.environ.get("CPANEL_PASSWORD", "")

# ── GoDaddy Login (for browser automation) ────────────
GODADDY_EMAIL    = os.environ.get("GODADDY_EMAIL", "")
GODADDY_PASSWORD = os.environ.get("GODADDY_PASSWORD", "")

# ── Logging ───────────────────────────────────────────
LOG_FILE = "automation.log"

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

def _cpanel_headers():
    """Auth headers for cPanel API calls using API token."""
    return {
        "Authorization": f"cpanel {CPANEL_USERNAME}:{CPANEL_PASSWORD}",
    }


def cpanel_get_main_domain() -> str:
    """Get the primary/main domain from cPanel."""
    url = f"{CPANEL_URL}/execute/DomainInfo/list_domains"
    resp = requests.get(url, headers=_cpanel_headers(), timeout=15, verify=True)
    resp.raise_for_status()
    result = resp.json()
    main_domain = result.get("data", {}).get("main_domain", "")
    log.debug(f"cPanel main domain: {main_domain}")
    return main_domain


def cpanel_create_domain(domain: str) -> dict:
    """Add a domain to cPanel hosting (creates the folder in public_html)."""
    # Get the primary domain for the subdomain field
    main_domain = cpanel_get_main_domain()

    # Use API2 AddonDomain — matches what the cPanel UI "Create a New Domain" does
    url = f"{CPANEL_URL}/json-api/cpanel"
    params = {
        "cpanel_jsonapi_user": CPANEL_USERNAME,
        "cpanel_jsonapi_apiversion": "2",
        "cpanel_jsonapi_module": "AddonDomain",
        "cpanel_jsonapi_func": "addaddondomain",
        "dir": f"public_html/{domain}",
        "newdomain": domain,
        "subdomain": domain.replace(".", ""),  # e.g. 1guy1girl1truckllccom
        "rootdomain": main_domain,             # e.g. crjlogisticsinc.com
    }
    resp = requests.get(url, params=params, headers=_cpanel_headers(), timeout=30, verify=True)
    log.debug(f"cPanel addon domain response: {resp.status_code} {resp.text[:500]}")
    resp.raise_for_status()
    result = resp.json()

    # Check API2 response for errors
    cpdata = result.get("cpanelresult", {}).get("data", [{}])
    if cpdata and isinstance(cpdata, list) and len(cpdata) > 0:
        item = cpdata[0]
        if item.get("result") == 0:
            reason = item.get("reason", "Unknown error")
            result["errors"] = [reason]
        else:
            result["errors"] = None
    return result


def cpanel_upload_file(file_path: str, dest_dir: str) -> dict:
    """Upload a file to cPanel via Fileman UAPI."""
    url = f"{CPANEL_URL}/execute/Fileman/upload_files"
    filename = Path(file_path).name
    with open(file_path, "rb") as f:
        files = {"file-1": (filename, f)}
        data = {"dir": dest_dir, "overwrite": "1"}
        resp = requests.post(url, data=data, files=files, headers=_cpanel_headers(),
                             timeout=120, verify=True)
    resp.raise_for_status()
    result = resp.json()
    log.debug(f"cPanel upload response: {result}")
    return result


def cpanel_extract_file(archive_path: str, dest_dir: str) -> dict:
    """Extract a zip/archive in cPanel via API2 Fileman::fileop."""
    url = f"{CPANEL_URL}/json-api/cpanel"
    params = {
        "cpanel_jsonapi_user": CPANEL_USERNAME,
        "cpanel_jsonapi_apiversion": "2",
        "cpanel_jsonapi_module": "Fileman",
        "cpanel_jsonapi_func": "fileop",
        "op": "extract",
        "sourcefiles": archive_path,
        "destfiles": dest_dir,
    }
    resp = requests.get(url, params=params, headers=_cpanel_headers(), timeout=120, verify=True)
    resp.raise_for_status()
    result = resp.json()
    log.debug(f"cPanel extract response: {result}")

    # Check API2 response for errors
    cpdata = result.get("cpanelresult", {}).get("data", [{}])
    if cpdata and isinstance(cpdata, list) and len(cpdata) > 0:
        item = cpdata[0]
        if item.get("result") == 0:
            reason = item.get("reason", "Unknown error")
            raise RuntimeError(f"cPanel extract error: {reason}")

    # Also check top-level errors
    if result.get("cpanelresult", {}).get("error"):
        raise RuntimeError(f"cPanel extract error: {result['cpanelresult']['error']}")

    return result


def cpanel_delete_file(file_path: str) -> dict:
    """Permanently delete a file on cPanel via API2 Fileman::fileop (skips trash)."""
    url = f"{CPANEL_URL}/json-api/cpanel"
    params = {
        "cpanel_jsonapi_user": CPANEL_USERNAME,
        "cpanel_jsonapi_apiversion": "2",
        "cpanel_jsonapi_module": "Fileman",
        "cpanel_jsonapi_func": "fileop",
        "op": "unlink",
        "sourcefiles": file_path,
    }
    resp = requests.get(url, params=params, headers=_cpanel_headers(), timeout=30, verify=True)
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
                "• Send a domain name → check availability & purchase\n"
                "• `/setup domain.com` → add domain to hosting & deploy website\n"
                "• `/email domain.com` → create M365 email account\n\n"
                "Example: `mysite.com`")
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
        tg_send(chat_id, "🚫 Cancelled." if cancelled else "Nothing to cancel.")
        return

    # Command: /email domain.com — create email account
    if text.startswith("/email "):
        domain = text.split(" ", 1)[1].strip()
        if not DOMAIN_RE.match(domain):
            tg_send(chat_id, "⚠️ Invalid domain format. Example: `/email mysite.com`")
            return
        _start_email_flow(chat_id, domain)
        return

    # Route to email flow if user is in one
    if chat_id in pending_email:
        step = pending_email[chat_id].get("step", "")
        if step in ("awaiting_username", "awaiting_name", "awaiting_password", "awaiting_notify_email"):
            _handle_email_input(chat_id, raw_text, message_id)
            return

    # Command: /setup domain.com — set up website on existing domain
    if text.startswith("/setup "):
        domain = text.split(" ", 1)[1].strip()
        if not DOMAIN_RE.match(domain):
            tg_send(chat_id, "⚠️ Invalid domain format. Example: `/setup mysite.com`")
            return
        _start_website_setup(chat_id, domain)
        return

    # Validate domain format
    if not DOMAIN_RE.match(text):
        tg_send(chat_id, "⚠️ Invalid domain format. Send something like `mysite.com`")
        return

    domain = text
    log.info(f"Domain requested: {domain}")

    # Check availability
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


def _start_website_setup(chat_id, domain):
    """Start the website setup flow — create domain in cPanel and wait for zip."""
    log.info(f"Website setup started for: {domain}")
    tg_send(chat_id, f"🌐 Adding `{domain}` to hosting...")

    try:
        result = cpanel_create_domain(domain)
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

    # Ask for the zip file
    pending_website_domain[chat_id] = domain
    tg_send(chat_id,
            f"📦 Now send me the `.zip` file with your website files "
            f"(HTML, CSS, images).\n\n"
            f"The contents will be deployed to `{domain}`.")


def handle_document(chat_id, document, message):
    """Handle a file/document upload (zip file for website deployment)."""
    domain = pending_website_domain.get(chat_id)

    if not domain:
        tg_send(chat_id,
                "📁 Got a file, but I'm not expecting one right now.\n\n"
                "To deploy a website, first use `/setup domain.com`")
        return

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
        cpanel_upload_file(local_zip, dest_dir)
        log.info(f"Uploaded {file_name} to {dest_dir}")
    except Exception as e:
        log.error(f"cPanel upload failed: {e}")
        tg_send(chat_id, f"🔴 Upload failed:\n`{e}`")
        return
    finally:
        # Clean up temp file
        try:
            os.remove(local_zip)
            os.rmdir(tmp_dir)
        except OSError:
            pass

    # Extract the zip on cPanel
    archive_path = f"{dest_dir}/{file_name}"
    tg_send(chat_id, f"📂 Extracting `{file_name}`...")
    try:
        cpanel_extract_file(archive_path, dest_dir)
        log.info(f"Extracted {file_name} in {dest_dir}")
    except Exception as e:
        log.error(f"cPanel extract failed: {e}")
        tg_send(chat_id, f"🔴 Extraction failed:\n`{e}`")
        return

    # Delete the zip from cPanel (permanently, skip trash)
    try:
        cpanel_delete_file(archive_path)
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

    pending_email[chat_id] = {"step": "awaiting_username", "domain": domain}
    log.info(f"Email setup started for: {domain}")
    tg_send(chat_id,
            f"📧 *Email Setup for* `{domain}`\n\n"
            f"What username do you want?\n"
            f"Example: type `info` for `info@{domain}`")


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

    tg_send(chat_id, "⏳ Opening browser and logging in to GoDaddy...")

    try:
        from email_automation import GoDaddyEmailBot
        bot = GoDaddyEmailBot(
            email=GODADDY_EMAIL,
            password=GODADDY_PASSWORD,
            headless=False,
        )
        bot.open()
        bot.login()
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

    except Exception as e:
        log.error(f"Email creation submit failed: {e}")
        tg_send(chat_id, f"🔴 Email creation failed:\n`{e}`")
    finally:
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

    # ── Email flow callbacks ──────────────────────────
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN LOOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
    tg_send(TELEGRAM_CHAT_ID,
            "🤖 *Bot is online!*\n\n"
            "Send a domain name to check availability & purchase.\n"
            "Use `/setup domain.com` to deploy a website.\n"
            "Use `/email domain.com` to create an email account.\n\n"
            "Example: `mysite.com`")

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
