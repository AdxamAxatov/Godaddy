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

# ── GoDaddy API accounts ──────────────────────────────
GODADDY_ENV = os.environ.get("GODADDY_ENV", "ote")

GODADDY_API_ACCOUNTS = []
for _i in range(1, 10):
    _key = os.environ.get(f"GODADDY_API_KEY_{_i}", "")
    _secret = os.environ.get(f"GODADDY_API_SECRET_{_i}", "")
    if _key and _secret:
        GODADDY_API_ACCOUNTS.append({
            "api_key": _key,
            "api_secret": _secret,
            "label": os.environ.get(f"GODADDY_API_LABEL_{_i}", f"Account {_i}"),
            "registrant": {
                "nameFirst": os.environ.get(f"REGISTRANT_FIRST_NAME_{_i}", ""),
                "nameLast":  os.environ.get(f"REGISTRANT_LAST_NAME_{_i}", ""),
                "email":     os.environ.get(f"REGISTRANT_EMAIL_{_i}", ""),
                "phone":     os.environ.get(f"REGISTRANT_PHONE_{_i}", ""),
                "addressMailing": {
                    "address1":   os.environ.get(f"REGISTRANT_ADDRESS_{_i}", ""),
                    "city":       os.environ.get(f"REGISTRANT_CITY_{_i}", ""),
                    "state":      os.environ.get(f"REGISTRANT_STATE_{_i}", ""),
                    "postalCode": os.environ.get(f"REGISTRANT_POSTAL_CODE_{_i}", ""),
                    "country":    os.environ.get(f"REGISTRANT_COUNTRY_{_i}", "US"),
                },
            },
        })
    else:
        break

# Fallback: load old-style single account config if no numbered accounts found
if not GODADDY_API_ACCOUNTS:
    _key = os.environ.get("GODADDY_API_KEY", "")
    _secret = os.environ.get("GODADDY_API_SECRET", "")
    if _key and _secret:
        GODADDY_API_ACCOUNTS.append({
            "api_key": _key,
            "api_secret": _secret,
            "label": "Default",
            "registrant": {
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
            },
        })

# ── Telegram ─────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")  # Admin chat ID
ADMIN_CHAT_ID      = str(TELEGRAM_CHAT_ID)

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

# ── Browser settings ──────────────────────────────────
EMAIL_HEADLESS  = os.environ.get("EMAIL_HEADLESS",  "false").lower() == "true"
INDEED_HEADLESS = os.environ.get("INDEED_HEADLESS", "false").lower() == "true"

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

# ── User approval system ─────────────────────────────
_APPROVED_USERS_FILE = str(_PROJECT_ROOT / "approved_users.json")
_pending_approvals = {}  # chat_id str -> {name, username} — awaiting admin decision

def _load_approved_users() -> dict:
    """Load approved users from JSON file. Returns {id_str: {name, username}}."""
    try:
        with open(_APPROVED_USERS_FILE, "r") as f:
            data = json.load(f)
            users = data.get("approved", {})
            # Handle old format (list of IDs) gracefully
            if isinstance(users, list):
                return {str(uid): {"name": "Unknown", "username": ""} for uid in users}
            return {str(k): v for k, v in users.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_approved_users(users: dict):
    """Save approved users to JSON file."""
    with open(_APPROVED_USERS_FILE, "w") as f:
        json.dump({"approved": users}, f, indent=2)

APPROVED_USERS = _load_approved_users()
APPROVED_USERS[ADMIN_CHAT_ID] = {"name": "Admin", "username": ""}  # Admin always approved

def is_authorized(chat_id) -> bool:
    """Check if a user is approved."""
    return str(chat_id) in APPROVED_USERS

def _get_user_display(msg) -> str:
    """Get a display name from a Telegram message's 'from' field."""
    user = msg.get("from", {})
    first = user.get("first_name", "")
    last = user.get("last_name", "")
    username = user.get("username", "")
    name = f"{first} {last}".strip() or "Unknown"
    return f"{name} (@{username})" if username else name

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
    params = {"timeout": 5}
    if offset:
        params["offset"] = offset
    resp = requests.get(f"{TG_BASE}/getUpdates", params=params, timeout=10)
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

def _gd_headers(account: dict):
    return {
        "Authorization": f"sso-key {account['api_key']}:{account['api_secret']}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def check_indeed_company(company_name: str) -> str | None:
    """
    Google '{company_name} Indeed', screenshot the results page.
    Returns the screenshot file path, or None on failure.
    """
    from playwright.sync_api import sync_playwright
    screenshot_path = str(_PROJECT_ROOT / "logs" / f"indeed_{int(time.time())}.png")
    profile_dir = str(_PROJECT_ROOT / "browser_data" / "indeed")
    try:
        pw = sync_playwright().start()
        context = pw.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=INDEED_HEADLESS,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()
        query = f"{company_name} Indeed"
        page.goto(f"https://www.google.com/search?q={quote(query)}", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        # If CAPTCHA appears, wait for user to solve it
        if "unusual traffic" in (page.content() or ""):
            log.info("Google CAPTCHA detected — waiting for user to solve it...")
            page.wait_for_url("**/search?q=*", timeout=60000)
            page.wait_for_timeout(2000)
        page.screenshot(path=screenshot_path, full_page=False)
        context.close()
        pw.stop()
        return screenshot_path
    except Exception as e:
        log.error(f"Indeed check failed: {e}")
        return None


def check_domain_availability(domain: str, account: dict) -> tuple[bool, float]:
    """
    Check if a domain is available.
    Returns (available: bool, price_usd: float).
    """
    url  = f"{GODADDY_BASE}/v1/domains/available"
    resp = requests.get(url, headers=_gd_headers(account), params={"domain": domain}, timeout=15)
    resp.raise_for_status()
    data      = resp.json()
    available = data.get("available", False)
    price     = data.get("price", 0) / 1_000_000  # GoDaddy returns micros
    return available, price


def purchase_domain(domain: str, account: dict, years: int = 1) -> dict:
    """Purchase a domain on GoDaddy using the saved payment method on the account."""
    url = f"{GODADDY_BASE}/v1/domains/purchase"
    registrant = account["registrant"]
    payload = {
        "domain":    domain,
        "period":    years,
        "renewAuto": True,
        "privacy":   False,
        "consent": {
            "agreedAt":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agreedBy":      registrant["email"],
            "agreementKeys": ["DNRA"],
        },
        "contactAdmin":      registrant,
        "contactBilling":    registrant,
        "contactRegistrant": registrant,
        "contactTech":       registrant,
    }
    resp = requests.post(url, headers=_gd_headers(account), json=payload, timeout=30)
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


def cpanel_remove_domain(domain: str, account: dict) -> dict:
    """Remove an addon domain from cPanel via API2 AddonDomain::deladdondomain."""
    # First, look up the actual subdomain cPanel assigned to this addon domain
    lookup_url = f"{account['url']}/json-api/cpanel"
    lookup_params = {
        "cpanel_jsonapi_user": account["username"],
        "cpanel_jsonapi_apiversion": "2",
        "cpanel_jsonapi_module": "AddonDomain",
        "cpanel_jsonapi_func": "listaddondomains",
    }
    lookup_resp = requests.get(lookup_url, params=lookup_params, headers=_cpanel_headers(account), timeout=15, verify=True)
    lookup_resp.raise_for_status()
    lookup_data = lookup_resp.json().get("cpanelresult", {}).get("data", [])

    subdomain = None
    for entry in lookup_data:
        log.debug(f"cPanel addon domain entry: {entry}")
        if entry.get("domain") == domain:
            subdomain = entry.get("fullsubdomain", "") or domain.replace(".", "")
            break

    if subdomain is None:
        return {"errors": [f"Domain '{domain}' not found as an addon domain"]}

    log.debug(f"cPanel addon domain '{domain}' has subdomain: {subdomain}")

    url = f"{account['url']}/json-api/cpanel"
    params = {
        "cpanel_jsonapi_user": account["username"],
        "cpanel_jsonapi_apiversion": "2",
        "cpanel_jsonapi_module": "AddonDomain",
        "cpanel_jsonapi_func": "deladdondomain",
        "domain": domain,
        "subdomain": subdomain,
    }
    resp = requests.get(url, params=params, headers=_cpanel_headers(account), timeout=30, verify=True)
    log.debug(f"cPanel remove domain response: {resp.status_code} {resp.text[:500]}")
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


def cpanel_run_autossl(account: dict):
    """Trigger AutoSSL check via cPanel UAPI."""
    url = f"{account['url']}/execute/SSL/start_autossl_check"
    resp = requests.get(url, headers=_cpanel_headers(account), timeout=60, verify=True)
    resp.raise_for_status()
    result = resp.json()
    log.debug(f"cPanel AutoSSL response: {result}")
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
pending_buy = {}  # chat_id -> {"step": "awaiting_company" | "awaiting_domain", ...}

# Active browser sessions (kept open after email creation)
active_browser = {}  # chat_id -> GoDaddyEmailBot instance

# Website generation flow state
pending_generate = {}  # chat_id -> {step, ...collected info}

# Generated zips awaiting optional deploy
_pending_deploys = {}  # chat_id -> {zip_path, domain}

# AutoSSL flow state
pending_autossl = {}  # chat_id -> {step, domain}

# Remove domain flow state
pending_remove_domain = {}  # chat_id -> {step, domain}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BOT HANDLERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def handle_message(chat_id, text, message_id=None):
    """Handle an incoming text message."""
    log.info(f"[{chat_id}] Message: {text.strip()}")
    raw_text = text.strip()
    text = raw_text.lower()

    if text == "/start":
        tg_send(chat_id,
                "👋 *GoDaddy Domain Bot*\n\n"
                "What I can do:\n"
                "• /buy — purchase a domain\n"
                "• /setup — deploy a website\n"
                "• /email — create an email account\n"
                "• /generate — generate website + job description\n"
                "• /run\\_autossl — run AutoSSL for a domain\n"
                "• /remove\\_domain — remove a domain from hosting")
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
            old_buy = pending_buy.pop(chat_id)
            if isinstance(old_buy, dict) and old_buy.get("browser_bot"):
                old_buy["browser_bot"].close()
            cancelled = True
        if chat_id in active_browser:
            active_browser.pop(chat_id).close()
            cancelled = True
        if chat_id in pending_generate:
            del pending_generate[chat_id]
            cancelled = True
        if chat_id in pending_autossl:
            del pending_autossl[chat_id]
            cancelled = True
        if chat_id in pending_remove_domain:
            del pending_remove_domain[chat_id]
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

    # Command: /users — list approved users (admin only)
    if text == "/users":
        if str(chat_id) != ADMIN_CHAT_ID:
            tg_send(chat_id, "⚠️ Admin only.")
            return
        if not APPROVED_USERS:
            tg_send(chat_id, "No approved users.")
        else:
            lines = ["👥 *Approved Users*\n"]
            for uid in sorted(APPROVED_USERS):
                info = APPROVED_USERS[uid]
                name = info.get("name", "Unknown")
                username = info.get("username", "")
                role = "👑 Admin" if uid == ADMIN_CHAT_ID else "👤 User"
                display = f"@{username}" if username else name
                lines.append(f"{role}: {display} (`{uid}`)")
            tg_send(chat_id, "\n".join(lines))
        return

    # Command: /revoke — remove a user (admin only)
    if text.startswith("/revoke"):
        if str(chat_id) != ADMIN_CHAT_ID:
            tg_send(chat_id, "⚠️ Admin only.")
            return
        parts = text.split()
        if len(parts) < 2:
            tg_send(chat_id, "Usage: `/revoke <user_id>`")
            return
        target_id = parts[1].strip()
        if target_id == ADMIN_CHAT_ID:
            tg_send(chat_id, "⚠️ Cannot revoke admin.")
            return
        if target_id in APPROVED_USERS:
            del APPROVED_USERS[target_id]
            _save_approved_users(APPROVED_USERS)
            tg_send(chat_id, f"✅ User `{target_id}` has been revoked.")
            tg_send(int(target_id), "🔒 Your access has been revoked by the admin.")
            log.info(f"User {target_id} revoked by admin")
        else:
            tg_send(chat_id, f"User `{target_id}` is not in the approved list.")
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
        pending_buy[chat_id] = {"step": "awaiting_company"}
        tg_send(chat_id, "💰 *Domain Purchase*\n\nWhat is the company name?\nExample: `Werner Enterprises`",
                reply_markup={"inline_keyboard": [[
                    {"text": "⏭ Skip Indeed Check", "callback_data": "indeed_skip"},
                ]]})
        return

    # Route to buy flow if user is in one
    if chat_id in pending_buy:
        step = pending_buy[chat_id].get("step")

        if step == "awaiting_company":
            company = text.strip()
            if not company:
                tg_send(chat_id, "⚠️ Please enter a company name.")
                return
            tg_send(chat_id, f"🔍 Searching Indeed for *{company}*...")
            screenshot = check_indeed_company(company)
            if screenshot:
                pending_buy[chat_id] = {"step": "awaiting_indeed_decision", "company": company}
                tg_send_photo(chat_id, screenshot,
                              caption=f"Indeed results for *{company}*\n\nDoes this company already exist on Indeed?")
                tg_send(chat_id, "Does the company exist on Indeed?",
                        reply_markup={"inline_keyboard": [[
                            {"text": "✅ Yes, exists", "callback_data": "indeed_yes"},
                            {"text": "❌ No, doesn't exist", "callback_data": "indeed_no"},
                        ]]})
            else:
                tg_send(chat_id, "⚠️ Could not check Indeed. Proceeding to domain input.")
                pending_buy[chat_id] = {"step": "awaiting_domain", "company": company}
                tg_send(chat_id, "What domain? Example: `mysite.com`")
            return

        if step == "awaiting_domain":
            domain = text.strip()
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            pending_buy[chat_id]["domain"] = domain
            _start_domain_purchase(chat_id, domain)
            return

    # Command: /generate — generate website + job description
    if text == "/generate":
        pending_generate[chat_id] = {"step": "awaiting_info"}
        tg_send(chat_id,
                "🏗️ *Website Generator*\n\n"
                "Send all info in one message using this format:\n\n"
                "`Company: 2-3 Logistics Corp\n"
                "Logo: 2-3 Logistics\n"
                "Domain: 2-3logisticscorp.com\n"
                "Email: info@2-3logisticscorp.com\n"
                "Address: 508 Linden Dr\n"
                "City: Round Lake, IL 60073\n"
                "Job: OTR Company Driver — CDL-A\n"
                "Pay: $1,300 – $1,600 / week\n"
                "Home: Home every 2 weeks for 2 days\n"
                "Home Short: 2 Weeks Out\n"
                "Home Detail: Home 2 Days\n"
                "Experience: 6 months\n"
                "Perks: Weekly direct deposit, Health insurance, 401(k) with match`")
        return

    # Route to generate flow if user is in one
    if chat_id in pending_generate:
        _handle_generate_input(chat_id, raw_text)
        return

    # Command: /run_autossl — trigger AutoSSL for a domain
    if text == "/run_autossl" or text.startswith("/run_autossl "):
        domain = text.split(" ", 1)[1].strip() if " " in text else ""
        if domain:
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            _start_autossl(chat_id, domain)
        else:
            pending_autossl[chat_id] = {"step": "awaiting_domain"}
            tg_send(chat_id, "🔒 *Run AutoSSL*\n\nWhat domain? Example: `mysite.com`")
        return

    # Route to autossl flow if user is in one (awaiting domain)
    if chat_id in pending_autossl:
        pending = pending_autossl[chat_id]
        if pending.get("step") == "awaiting_domain":
            domain = text.strip()
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            del pending_autossl[chat_id]
            _start_autossl(chat_id, domain)
            return

    # Command: /remove_domain — remove a domain from cPanel hosting
    if text == "/remove_domain" or text.startswith("/remove_domain "):
        domain = text.split(" ", 1)[1].strip() if " " in text else ""
        if domain:
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            _start_remove_domain(chat_id, domain)
        else:
            pending_remove_domain[chat_id] = {"step": "awaiting_domain"}
            tg_send(chat_id, "🗑 *Remove Domain*\n\nWhat domain to remove? Example: `mysite.com`")
        return

    # Route to remove domain flow if user is in one (awaiting domain)
    if chat_id in pending_remove_domain:
        pending = pending_remove_domain[chat_id]
        if pending.get("step") == "awaiting_domain":
            domain = text.strip()
            if not DOMAIN_RE.match(domain):
                tg_send(chat_id, "⚠️ Invalid domain format. Example: `mysite.com`")
                return
            del pending_remove_domain[chat_id]
            _start_remove_domain(chat_id, domain)
            return

    tg_send(chat_id, "⚠️ Unknown command. Use `/buy`, `/setup`, `/email`, `/generate`, `/run_autossl`, `/remove_domain`, or `/start`.")


def _start_domain_purchase(chat_id, domain, account_idx=None):
    """Start browser-based domain purchase flow."""
    log.info(f"Domain purchase requested: {domain}")

    if len(GODADDY_ACCOUNTS) == 0:
        tg_send(chat_id, "🔴 No GoDaddy accounts configured in `.env`")
        pending_buy.pop(chat_id, None)
        return

    # If multiple accounts and none selected yet, show picker
    if account_idx is None and len(GODADDY_ACCOUNTS) > 1:
        pending_buy[chat_id] = pending_buy.get(chat_id, {})
        pending_buy[chat_id]["step"] = "awaiting_buy_account"
        pending_buy[chat_id]["domain"] = domain
        buttons = []
        for i, acc in enumerate(GODADDY_ACCOUNTS):
            buttons.append([{"text": acc["email"], "callback_data": f"buy_acc:{i}:{domain}"}])
        tg_send(chat_id,
                f"💰 *Purchase* `{domain}`\n\nWhich GoDaddy account?",
                reply_markup={"inline_keyboard": buttons})
        return

    if account_idx is None:
        account_idx = 0
    account = GODADDY_ACCOUNTS[account_idx]

    tg_send(chat_id, f"🌐 Launching browser to search for `{domain}`...")

    try:
        from domain_automation import GoDaddyDomainBot

        bot = GoDaddyDomainBot(
            email=account["email"],
            password=account["password"],
            account_idx=account_idx,
            headless=False,
        )
        bot.open()

        tg_send(chat_id, f"🔍 Searching for `{domain}`...")
        result = bot.search_domain(domain)

        if not result["available"]:
            tg_send(chat_id, f"❌ `{domain}` is not available for purchase. Browser left open — use `/close` when done.")
            active_browser[chat_id] = bot
            pending_buy.pop(chat_id, None)
            return

        price = result["price"] or "unknown"
        pending_buy[chat_id] = {
            "step": "awaiting_buy_confirm",
            "domain": domain,
            "account_idx": account_idx,
            "browser_bot": bot,
            "price": price,
        }

        # Screenshot the search results
        screenshot_path = os.path.join(tempfile.gettempdir(), f"domain_search_{chat_id}.png")
        bot.screenshot(screenshot_path)
        tg_send_photo(chat_id, screenshot_path,
                      caption=f"✅ `{domain}` is available — *{price}/yr* (1 Year)")
        try:
            os.remove(screenshot_path)
        except Exception:
            pass

        tg_send(chat_id,
                f"Proceed with purchase?",
                reply_markup={"inline_keyboard": [[
                    {"text": "💰 Proceed to Buy", "callback_data": "buy_proceed"},
                    {"text": "❌ Cancel", "callback_data": "buy_cancel"},
                ]]})

    except Exception as e:
        log.error(f"Domain search error: {e}")
        tg_send(chat_id, f"🔴 Error searching for domain:\n`{e}`\n\nBrowser left open — use `/close` when done.")
        if bot:
            active_browser[chat_id] = bot
        pending_buy.pop(chat_id, None)


def _proceed_buy_to_checkout(chat_id):
    """Drive the browser from search results through cart to checkout page."""
    state = pending_buy.get(chat_id, {})
    bot = state.get("browser_bot")
    domain = state.get("domain", "unknown")

    if not bot:
        tg_send(chat_id, "🔴 Browser session expired. Start over with `/buy`.")
        pending_buy.pop(chat_id, None)
        return

    try:
        tg_send(chat_id, "🛒 Adding to cart...")
        bot.select_term_and_add()
        bot.go_to_cart()

        tg_send(chat_id, "⏭ Skipping extras...")
        bot.skip_extras()

        tg_send(chat_id, "📋 Reviewing cart...")
        bot.prepare_checkout()

        # Screenshot the checkout page
        screenshot_path = os.path.join(tempfile.gettempdir(), f"domain_checkout_{chat_id}.png")
        bot.screenshot(screenshot_path)
        tg_send_photo(chat_id, screenshot_path,
                      caption=f"🔒 Reached checkout for `{domain}`")
        try:
            os.remove(screenshot_path)
        except Exception:
            pass

        tg_send(chat_id,
                f"✅ *Checkout ready for* `{domain}`\n\n"
                f"Browser is at the checkout page. Use `/close` when done.")

        # Keep browser open at checkout — move to active_browser
        active_browser[chat_id] = bot
        state.pop("browser_bot", None)
        pending_buy.pop(chat_id, None)

    except Exception as e:
        log.error(f"Domain purchase flow error: {e}")
        # Take debug screenshot
        try:
            bot.screenshot(f"{os.path.dirname(os.path.abspath(__file__))}/../logs/debug_domain_purchase.png")
        except Exception:
            pass
        tg_send(chat_id, f"🔴 Error during purchase flow:\n`{e}`\n\nBrowser left open — use `/close` when done.")
        active_browser[chat_id] = bot
        state.pop("browser_bot", None)
        pending_buy.pop(chat_id, None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WEBSITE GENERATION FLOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Field mapping: label in user message → internal field name
_GENERATE_FIELDS = {
    "company": "company_name",
    "logo": "company_short",
    "domain": "domain",
    "email": "email",
    "address": "address",
    "city": "city_state",
    "job": "job_title",
    "pay": "pay_range",
    "home": "home_time",
    "home short": "home_time_short",
    "home detail": "home_time_detail",
    "experience": "min_experience",
    "perks": "perks",
}

_GENERATE_REQUIRED = ["company_name", "domain", "email", "city_state", "job_title", "pay_range"]


def _handle_generate_input(chat_id, raw_text):
    """Parse the single-message info block and generate."""
    state = pending_generate[chat_id]

    # Parse "Label: Value" lines
    parsed = {}
    for line in raw_text.strip().splitlines():
        if ":" not in line:
            continue
        label, _, value = line.partition(":")
        label = label.strip().lower()
        value = value.strip()
        if not value:
            continue
        # Match label to field
        if label in _GENERATE_FIELDS:
            field = _GENERATE_FIELDS[label]
            if field == "perks":
                parsed[field] = [p.strip() for p in value.split(",") if p.strip()]
            else:
                parsed[field] = value

    if not parsed:
        tg_send(chat_id, "⚠️ Couldn't parse that. Use the `Label: Value` format, one per line.")
        return

    # Check required fields
    missing = [label for label, field in [
        ("Company", "company_name"), ("Domain", "domain"), ("Email", "email"),
        ("City", "city_state"), ("Job", "job_title"), ("Pay", "pay_range"),
    ] if field not in parsed]

    if missing:
        tg_send(chat_id, f"⚠️ Missing required fields: {', '.join(missing)}\n\nPlease resend with all fields.")
        return

    # Merge parsed into state and generate
    state.update(parsed)
    _finish_generate(chat_id)


def _finish_generate(chat_id):
    """Generate the website and job description, send to user."""
    state = pending_generate.pop(chat_id)
    tg_send(chat_id, "⏳ Generating website and job description...")

    try:
        from website_generator import generate_website_from_blocks, generate_job_description

        # Build info with defaults for optional fields
        company = state["company_name"]
        info = {
            "company_name": company,
            "company_short": state.get("company_short", company.split()[0]),
            "domain": state["domain"],
            "email": state["email"],
            "address": state.get("address", ""),
            "city_state": state["city_state"],
            "job_title": state["job_title"],
            "pay_range": state["pay_range"],
            "home_time": state.get("home_time", ""),
            "home_time_short": state.get("home_time_short", ""),
            "home_time_detail": state.get("home_time_detail", ""),
            "min_experience": state.get("min_experience", "6 months"),
            "fourth_card_value": state.get("min_experience", "6 Mo. Exp"),
            "fourth_card_label": "Min. Required",
            "routes": "48 States",
            "routes_type": "OTR Routes",
            "perks": state.get("perks", []),
        }

        # Generate website zip
        zip_path = generate_website_from_blocks(info)
        log.info(f"Website generated: {zip_path}")

        # Generate job description
        job_desc = generate_job_description(info)

        # Send zip file
        tg_send_document(chat_id, zip_path, caption=f"🌐 *Website for* `{state['domain']}`")

        # Send job description as HTML file — paste directly into Indeed's editor
        jd_path = os.path.join(tempfile.gettempdir(), f"{state['domain'].replace('.', '_')}_indeed.html")
        with open(jd_path, "w", encoding="utf-8") as f:
            f.write(job_desc)
        tg_send_document(chat_id, jd_path, caption="📋 *Indeed Job Description* — open, select all, paste into Indeed")
        try:
            os.remove(jd_path)
        except OSError:
            pass

        # Store zip path for optional deploy — don't delete yet
        pending_deploy = {
            "zip_path": zip_path,
            "domain": state["domain"],
        }
        # Store in a dict so the callback can find it
        _pending_deploys[chat_id] = pending_deploy

        tg_send(chat_id, "Deploy this website now?",
                reply_markup={
                    "inline_keyboard": [[
                        {"text": "🚀 Deploy to Hosting", "callback_data": "gen_deploy"},
                        {"text": "✅ Done", "callback_data": "gen_done"},
                    ]]
                })

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


def _start_autossl(chat_id, domain, account_idx=None):
    """Run AutoSSL for a domain on the selected cPanel account."""
    log.info(f"AutoSSL requested for: {domain}")

    if len(CPANEL_ACCOUNTS) == 0:
        tg_send(chat_id, "🔴 No cPanel accounts configured in `.env`")
        return

    if account_idx is None and len(CPANEL_ACCOUNTS) > 1:
        # Show account picker
        pending_autossl[chat_id] = {"domain": domain, "step": "awaiting_account"}
        buttons = []
        for i, acc in enumerate(CPANEL_ACCOUNTS):
            buttons.append([{"text": acc["label"], "callback_data": f"autossl_acc:{i}:{domain}"}])
        tg_send(chat_id,
                f"🔒 *AutoSSL for* `{domain}`\n\nWhich hosting account?",
                reply_markup={"inline_keyboard": buttons})
        return

    # Single account or account already chosen
    if account_idx is None:
        account_idx = 0
    account = CPANEL_ACCOUNTS[account_idx]

    tg_send(chat_id, f"🔒 Running AutoSSL for `{domain}` ({account['label']})...")

    try:
        result = cpanel_run_autossl(account)
        errors = result.get("errors")
        if errors:
            log.error(f"AutoSSL failed: {errors}")
            tg_send(chat_id, f"🔴 AutoSSL failed:\n`{errors}`")
        else:
            tg_send(chat_id,
                    f"✅ AutoSSL started for `{domain}` ({account['label']})\n\n"
                    f"SSL certificate will be issued shortly. It may take a few minutes to propagate.")
            log.info(f"AutoSSL triggered for {domain} on {account['label']}")
    except Exception as e:
        log.error(f"AutoSSL error: {e}")
        tg_send(chat_id, f"🔴 AutoSSL error:\n`{e}`")


def _start_remove_domain(chat_id, domain, account_idx=None):
    """Remove a domain from cPanel hosting — pick account, confirm, then delete."""
    log.info(f"Domain removal requested: {domain}")

    if len(CPANEL_ACCOUNTS) == 0:
        tg_send(chat_id, "🔴 No cPanel accounts configured in `.env`")
        return

    if account_idx is None and len(CPANEL_ACCOUNTS) > 1:
        # Show account picker
        pending_remove_domain[chat_id] = {"domain": domain, "step": "awaiting_account"}
        buttons = []
        for i, acc in enumerate(CPANEL_ACCOUNTS):
            buttons.append([{"text": acc["label"], "callback_data": f"remove_acc:{i}:{domain}"}])
        tg_send(chat_id,
                f"🗑 *Remove* `{domain}`\n\nWhich hosting account?",
                reply_markup={"inline_keyboard": buttons})
        return

    if account_idx is None:
        account_idx = 0
    account = CPANEL_ACCOUNTS[account_idx]

    # Check if domain exists in cPanel first
    try:
        url = f"{account['url']}/execute/DomainInfo/list_domains"
        resp = requests.get(url, headers=_cpanel_headers(account), timeout=15, verify=True)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        addon_domains = data.get("addon_domains", [])
        all_domains = addon_domains + data.get("parked_domains", []) + [data.get("main_domain", "")]
        if domain not in all_domains:
            tg_send(chat_id, f"❌ `{domain}` was not found on hosting ({account['label']}).")
            pending_remove_domain.pop(chat_id, None)
            return
    except Exception as e:
        log.error(f"Failed to check domains: {e}")
        tg_send(chat_id, f"🔴 Could not verify domain exists:\n`{e}`")
        pending_remove_domain.pop(chat_id, None)
        return

    # Ask for confirmation before removing
    tg_send(chat_id,
            f"⚠️ *Are you sure you want to remove* `{domain}` *from hosting* ({account['label']})?\n\n"
            f"This will permanently delete the domain from cPanel. The website files will remain in the document root.",
            reply_markup={"inline_keyboard": [[
                {"text": "✅ Yes, Remove", "callback_data": f"confirm_remove:{account_idx}:{domain}"},
                {"text": "❌ Cancel", "callback_data": "cancel_remove"},
            ]]})


def handle_document(chat_id, document, message):
    """Handle a file/document upload (zip file for website deployment)."""
    log.info(f"[{chat_id}] Document: {document.get('file_name', 'unknown')}")
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
        tg_send(chat_id,
                "📬 Send account info to which email?",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "smfleet02@gmail.com", "callback_data": "email_notify:smfleet02@gmail.com"}],
                        [{"text": "phillhr57@gmail.com", "callback_data": "email_notify:phillhr57@gmail.com"}],
                    ]
                })

    elif step == "awaiting_notify_email":
        state["notify_email"] = raw_text.strip()
        _launch_email_browser(chat_id)


def _launch_email_browser(chat_id):
    """Open browser, login, navigate to form, scrape expiration dates."""
    state = pending_email[chat_id]
    domain = state["domain"]
    account_idx = state.get("account_idx", 0)

    account = GODADDY_ACCOUNTS[account_idx]

    try:
        from email_automation import GoDaddyEmailBot

        # Reuse existing browser if it's open for the same account
        existing = active_browser.get(chat_id)
        if existing and getattr(existing, 'account_idx', None) == account_idx and existing._page:
            bot = existing
            active_browser.pop(chat_id)
            tg_send(chat_id, f"⏳ Reusing open browser, navigating to email form...")
            log.info(f"Reusing existing browser for account {account_idx}")
        else:
            # Close old browser if it's a different account or stale
            if existing:
                try:
                    existing.close()
                except Exception:
                    pass
                active_browser.pop(chat_id, None)
                log.info("Closed previous browser (different account or stale)")

            tg_send(chat_id, f"⏳ Opening browser and navigating to GoDaddy ({account['email']})...")
            bot = GoDaddyEmailBot(
                email=account["email"],
                password=account["password"],
                account_idx=account_idx,
                headless=EMAIL_HEADLESS,
            )
            bot.open()

        bot.go_to_create_email(domain)

        dates = bot.get_expiration_dates()
        state["browser_bot"] = bot
        state["expiration_dates"] = dates

        if len(dates) == 1:
            # Only one option — auto-select it, skip asking user
            state["expiration_idx"] = 0
            state["expiration_text"] = dates[0]
            log.info(f"Auto-selected single expiration date: {dates[0]}")
            _fill_and_confirm(chat_id, None)
        else:
            # Multiple options — show picker
            state["step"] = "awaiting_expiration"
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

    if message_id:
        tg_edit_message(chat_id, message_id, f"📅 Expiration: {state['expiration_text']}")
    else:
        tg_send(chat_id, f"📅 Expiration: {state['expiration_text']} (auto-selected)")
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
    log.info(f"[{chat_id}] Callback: {data}")
    tg_answer_callback(callback_query_id)

    # Admin: approve/deny user access
    if data.startswith("approve:"):
        target_id = data.split(":", 1)[1]
        user_info = _pending_approvals.pop(target_id, {"name": "Unknown", "username": ""})
        APPROVED_USERS[target_id] = user_info
        _save_approved_users(APPROVED_USERS)
        tg_edit_message(chat_id, message_id, f"✅ User `{target_id}` approved.")
        tg_send(int(target_id), "✅ Your access has been approved! Send /start to begin.")
        log.info(f"User {target_id} approved by admin")
        return

    if data.startswith("deny:"):
        target_id = data.split(":", 1)[1]
        _pending_approvals.pop(target_id, None)
        tg_edit_message(chat_id, message_id, f"❌ User `{target_id}` denied.")
        tg_send(int(target_id), "❌ Your access request has been denied.")
        log.info(f"User {target_id} denied by admin")
        return

    if data == "cancel":
        tg_edit_message(chat_id, message_id, "🚫 Purchase cancelled.")
        log.info("User cancelled purchase.")
        return

    if data == "indeed_yes":
        company = pending_buy.get(chat_id, {}).get("company", "Company")
        tg_edit_message(chat_id, message_id, f"✅ *{company}* exists on Indeed.")
        tg_send(chat_id,
                f"⚠️ *{company}* already exists on Indeed.\n\n"
                f"Want to try a different company?",
                reply_markup={"inline_keyboard": [[
                    {"text": "🔄 Try another", "callback_data": "indeed_retry"},
                    {"text": "❌ Cancel", "callback_data": "indeed_cancel"},
                ]]})
        return

    if data == "indeed_retry":
        tg_edit_message(chat_id, message_id, "🔄 Trying another company.")
        pending_buy[chat_id] = {"step": "awaiting_company"}
        tg_send(chat_id, "What is the company name?")
        return

    if data == "indeed_cancel":
        tg_edit_message(chat_id, message_id, "🚫 Purchase cancelled.")
        pending_buy.pop(chat_id, None)
        return

    if data == "indeed_no":
        company = pending_buy.get(chat_id, {}).get("company", "Company")
        tg_edit_message(chat_id, message_id, f"❌ *{company}* not found on Indeed.")
        pending_buy[chat_id] = {"step": "awaiting_domain", "company": company}
        tg_send(chat_id, "What domain? Example: `mysite.com`")
        return

    if data == "indeed_skip":
        tg_edit_message(chat_id, message_id, "⏭ Indeed check skipped.")
        pending_buy[chat_id] = {"step": "awaiting_domain"}
        tg_send(chat_id, "What domain? Example: `mysite.com`")
        return

    if data.startswith("buy_acc:"):
        # Account picker callback: buy_acc:IDX:domain
        parts = data.split(":", 2)
        idx = int(parts[1])
        domain = parts[2]
        tg_edit_message(chat_id, message_id, f"Account: {GODADDY_ACCOUNTS[idx]['email']}")
        _start_domain_purchase(chat_id, domain, account_idx=idx)
        return

    if data == "buy_proceed":
        tg_edit_message(chat_id, message_id, "⏳ Proceeding to checkout...")
        _proceed_buy_to_checkout(chat_id)
        return

    if data == "buy_cancel":
        state = pending_buy.pop(chat_id, {})
        bot = state.get("browser_bot")
        if bot:
            bot.close()
        tg_edit_message(chat_id, message_id, "🚫 Purchase cancelled.")
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

    if data.startswith("autossl_acc:"):
        parts = data.split(":", 2)
        idx = int(parts[1])
        domain = parts[2]
        acc = CPANEL_ACCOUNTS[idx]
        tg_edit_message(chat_id, message_id, f"Hosting: {acc['label']}")
        pending_autossl.pop(chat_id, None)
        _start_autossl(chat_id, domain, account_idx=idx)
        return

    # ── Remove domain callbacks ──────────────────────
    if data.startswith("remove_acc:"):
        parts = data.split(":", 2)
        idx = int(parts[1])
        domain = parts[2]
        acc = CPANEL_ACCOUNTS[idx]
        tg_edit_message(chat_id, message_id, f"Hosting: {acc['label']}")
        pending_remove_domain.pop(chat_id, None)
        _start_remove_domain(chat_id, domain, account_idx=idx)
        return

    if data.startswith("confirm_remove:"):
        parts = data.split(":", 2)
        acc_idx = int(parts[1])
        domain = parts[2]
        account = CPANEL_ACCOUNTS[acc_idx]
        tg_edit_message(chat_id, message_id, f"⏳ Removing `{domain}`...")

        try:
            result = cpanel_remove_domain(domain, account)
            errors = result.get("errors")
            if errors:
                log.error(f"Domain removal failed: {errors}")
                tg_send(chat_id, f"🔴 Failed to remove `{domain}`:\n`{errors}`")
            else:
                log.info(f"Domain removed: {domain} from {account['label']}")
                tg_send(chat_id, f"✅ `{domain}` has been removed from hosting ({account['label']}).")
        except Exception as e:
            log.error(f"Domain removal error: {e}")
            tg_send(chat_id, f"🔴 Error removing domain:\n`{e}`")
        pending_remove_domain.pop(chat_id, None)
        return

    if data == "cancel_remove":
        tg_edit_message(chat_id, message_id, "🚫 Domain removal cancelled.")
        pending_remove_domain.pop(chat_id, None)
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
        state["notify_email"] = data.split(":", 1)[1]
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

    # ── Generate deploy callbacks ────────────────────
    if data == "gen_done":
        deploy = _pending_deploys.pop(chat_id, None)
        if deploy:
            try:
                os.remove(deploy["zip_path"])
            except OSError:
                pass
        tg_edit_message(chat_id, message_id, "✅ Done!")
        return

    if data == "gen_deploy":
        deploy = _pending_deploys.get(chat_id)
        if not deploy:
            tg_edit_message(chat_id, message_id, "🔴 Zip expired. Generate again with `/generate`.")
            return
        tg_edit_message(chat_id, message_id, "🚀 Deploying...")
        if len(CPANEL_ACCOUNTS) == 0:
            tg_send(chat_id, "🔴 No cPanel accounts configured in `.env`")
            return
        if len(CPANEL_ACCOUNTS) == 1:
            # Single account — deploy directly using callback handler
            deploy["account_idx"] = 0
            _pending_deploys[chat_id] = deploy
            handle_callback(callback_query_id, chat_id, message_id, "gen_deploy_acc:0")
        else:
            # Show account picker
            buttons = []
            for i, acc in enumerate(CPANEL_ACCOUNTS):
                buttons.append([{"text": acc["label"], "callback_data": f"gen_deploy_acc:{i}"}])
            tg_send(chat_id, "Which hosting account?",
                    reply_markup={"inline_keyboard": buttons})
        return

    if data.startswith("gen_deploy_acc:"):
        deploy = _pending_deploys.pop(chat_id, None)
        if not deploy:
            return
        idx = int(data.split(":")[1])
        domain = deploy["domain"]
        zip_path = deploy["zip_path"]
        account = CPANEL_ACCOUNTS[idx]

        # Create domain on cPanel
        tg_send(chat_id, f"🌐 Adding `{domain}` to hosting ({account['label']})...")
        try:
            result = cpanel_create_domain(domain, account)
            errors = result.get("errors")
            if errors:
                error_msg = str(errors)
                if "already" in error_msg.lower() or "exists" in error_msg.lower():
                    tg_send(chat_id, f"ℹ️ `{domain}` already exists in hosting. Continuing...")
                else:
                    tg_send(chat_id, f"🔴 Failed to add domain:\n`{error_msg}`")
                    return
            else:
                tg_send(chat_id, f"✅ `{domain}` added to hosting!")
        except Exception as e:
            tg_send(chat_id, f"🔴 Failed to add domain:\n`{e}`")
            return

        # Upload zip to cPanel
        dest_dir = f"/public_html/{domain}"
        file_name = Path(zip_path).name
        tg_send(chat_id, f"📤 Uploading to `{dest_dir}`...")
        try:
            cpanel_upload_file(zip_path, dest_dir, account)
            log.info(f"Uploaded {file_name} to {dest_dir}")
        except Exception as e:
            tg_send(chat_id, f"🔴 Upload failed:\n`{e}`")
            return
        finally:
            try:
                os.remove(zip_path)
            except OSError:
                pass

        # Extract
        archive_path = f"{dest_dir}/{file_name}"
        tg_send(chat_id, f"📂 Extracting `{file_name}`...")
        try:
            cpanel_extract_file(archive_path, dest_dir, account)
            log.info(f"Extracted {file_name} in {dest_dir}")
        except Exception as e:
            tg_send(chat_id, f"🔴 Extraction failed:\n`{e}`")
            return

        # Delete zip from server
        try:
            cpanel_delete_file(archive_path, account)
        except Exception:
            pass

        tg_send(chat_id,
                f"✅ *Website deployed!*\n\n"
                f"Domain: `{domain}`\n"
                f"Your site should be live at: http://{domain}")
        log.info(f"Generated website deployed for {domain}")
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
        {"command": "run_autossl", "description": "Run AutoSSL for a domain"},
        {"command": "remove_domain", "description": "Remove a domain from hosting"},
        {"command": "close", "description": "Close the browser"},
        {"command": "cancel", "description": "Cancel current operation"},
        {"command": "users", "description": "List approved users (admin)"},
        {"command": "revoke", "description": "Revoke user access (admin)"},
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

    # Register commands so they show in Telegram's menu
    tg_set_commands()

    while True:
        try:
            updates = tg_get_updates(offset)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            log.warning(f"Polling error: {e}")
            time.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1

            if "message" in update:
                msg = update["message"]
                chat_id = msg["chat"]["id"]

                # Unapproved user — send access request to admin
                if not is_authorized(chat_id):
                    str_id = str(chat_id)
                    if str_id not in _pending_approvals:
                        user = msg.get("from", {})
                        _pending_approvals[str_id] = {
                            "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Unknown",
                            "username": user.get("username", ""),
                        }
                        display = _get_user_display(msg)
                        tg_send(chat_id, "🔒 You don't have access to this bot.\nA request has been sent to the admin.")
                        tg_send(int(ADMIN_CHAT_ID),
                                f"🔔 *Access Request*\n\n"
                                f"User: {display}\n"
                                f"ID: `{chat_id}`",
                                reply_markup={"inline_keyboard": [[
                                    {"text": "✅ Approve", "callback_data": f"approve:{chat_id}"},
                                    {"text": "❌ Deny", "callback_data": f"deny:{chat_id}"},
                                ]]})
                        log.info(f"[{chat_id}] Access requested by {display}")
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
                data = cb.get("data", "")

                # Admin approval/deny callbacks — always allow for admin
                if data.startswith("approve:") or data.startswith("deny:"):
                    if str(chat_id) == ADMIN_CHAT_ID:
                        handle_callback(cb["id"], chat_id, cb["message"]["message_id"], data)
                    continue

                if not is_authorized(chat_id):
                    continue
                handle_callback(
                    cb["id"],
                    chat_id,
                    cb["message"]["message_id"],
                    data,
                )


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
        print("\n  Bot stopped.")
