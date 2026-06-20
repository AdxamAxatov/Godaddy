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
import random
import threading
import queue
import company_lookup
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
_auth_lock = threading.Lock()  # guards APPROVED_USERS and _pending_approvals (cross-thread)

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
    with _auth_lock:
        return str(chat_id) in APPROVED_USERS


# ── Browser flows (/buy, /email, /close) are shelved. Set True to re-enable. ──
# NOTE: re-enabling requires revisiting active_browser locking + single-owner
# browser lifecycle (see docs/superpowers/specs/2026-06-19-...-design.md),
# because GoDaddyEmailBot's sync-Playwright objects are thread-affine.
BROWSER_FLOWS_ENABLED = False

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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RESILIENT HTTP (retry + backoff on transient failures)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_HTTP_MAX_RETRIES = 3      # 4 total attempts
_HTTP_BACKOFF_BASE = 1.0   # seconds -> waits 1, 2, 4 between attempts

# Transient request-level errors worth retrying. "Connection aborted" is a
# ConnectionError; slow servers raise Timeout; truncated bodies raise
# ChunkedEncodingError. None of these mean the request is logically invalid.
_TRANSIENT_HTTP_EXC = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


def _http(method, url, **kwargs):
    """Perform an HTTP request, retrying transient failures with backoff.

    Retries on connection drops ("Connection aborted"), timeouts, truncated
    responses, and HTTP 5xx — up to _HTTP_MAX_RETRIES times with exponential
    backoff. Returns the final `requests.Response` (callers still call
    .raise_for_status()/.json() as before). Re-raises the last transient
    exception only after all attempts are exhausted.
    """
    last_exc = None
    for attempt in range(_HTTP_MAX_RETRIES + 1):
        try:
            resp = requests.request(method, url, **kwargs)
        except _TRANSIENT_HTTP_EXC as e:
            last_exc = e
            if attempt < _HTTP_MAX_RETRIES:
                wait = _HTTP_BACKOFF_BASE * (2 ** attempt)
                log.warning(
                    f"Transient HTTP error on {method} {url} "
                    f"(attempt {attempt + 1}/{_HTTP_MAX_RETRIES + 1}): {e}; "
                    f"retrying in {wait}s"
                )
                time.sleep(wait)
                continue
            raise
        # Retry transient server errors; return the response on the last attempt
        # so the caller's raise_for_status() surfaces it normally.
        if resp.status_code >= 500 and attempt < _HTTP_MAX_RETRIES:
            wait = _HTTP_BACKOFF_BASE * (2 ** attempt)
            log.warning(
                f"HTTP {resp.status_code} on {method} {url} "
                f"(attempt {attempt + 1}/{_HTTP_MAX_RETRIES + 1}); retrying in {wait}s"
            )
            time.sleep(wait)
            continue
        return resp
    raise last_exc  # defensive; loop above returns or raises first


def tg_send(chat_id, text, reply_markup=None):
    """Send a message to a Telegram chat."""
    payload = {
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    resp = _http("POST", f"{TG_BASE}/sendMessage", json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def tg_answer_callback(callback_query_id):
    """Acknowledge a callback query (removes the loading spinner on the button)."""
    _http("POST", f"{TG_BASE}/answerCallbackQuery",
                  json={"callback_query_id": callback_query_id}, timeout=10)


def tg_edit_message(chat_id, message_id, text):
    """Edit an existing message (used to update after button press)."""
    payload = {
        "chat_id":    chat_id,
        "message_id": message_id,
        "text":       text,
        "parse_mode": "Markdown",
    }
    _http("POST", f"{TG_BASE}/editMessageText", json=payload, timeout=10)


def tg_send_photo(chat_id, photo_path, caption=None):
    """Send a photo to a Telegram chat."""
    with open(photo_path, "rb") as f:
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "Markdown"
        resp = _http("POST", f"{TG_BASE}/sendPhoto", data=data,
                             files={"photo": f}, timeout=30)
    resp.raise_for_status()


def tg_send_document(chat_id, file_path, caption=None):
    """Send a document/file to a Telegram chat."""
    with open(file_path, "rb") as f:
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "Markdown"
        resp = _http("POST", f"{TG_BASE}/sendDocument", data=data,
                             files={"document": f}, timeout=60)
    resp.raise_for_status()


def tg_delete_message(chat_id, message_id):
    """Delete a message (used to remove password messages for security)."""
    _http("POST", f"{TG_BASE}/deleteMessage",
                  json={"chat_id": chat_id, "message_id": message_id}, timeout=10)


def tg_get_updates(offset=None):
    """Long-poll for new updates from Telegram."""
    params = {"timeout": 5}
    if offset:
        params["offset"] = offset
    resp = _http("GET", f"{TG_BASE}/getUpdates", params=params, timeout=10)
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
    resp = _http("GET", url, headers=_gd_headers(account), params={"domain": domain}, timeout=15)
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
    resp = _http("POST", url, headers=_gd_headers(account), json=payload, timeout=30)
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
    resp = _http("GET", url, headers=_cpanel_headers(account), timeout=15, verify=True)
    resp.raise_for_status()
    result = resp.json()
    main_domain = result.get("data", {}).get("main_domain", "")
    log.debug(f"cPanel main domain: {main_domain}")
    return main_domain


def _is_addon_limit_error(error_msg: str) -> bool:
    """True when a cPanel failure is the addon-domain cap (a hard limit)."""
    low = (error_msg or "").lower()
    return "addon" in low and ("maximum" in low or "limit" in low
                               or "reached" in low or "exceed" in low)


def _friendly_cpanel_error(error_msg: str) -> str:
    """Turn a raw cPanel failure string into a clear, actionable user message.

    The addon-domain cap is a hard account limit (not transient), so retrying
    won't help — tell the user the concrete next steps instead.
    """
    if _is_addon_limit_error(error_msg):
        return ("🔴 This hosting account is full — the 50 addon-domain limit has "
                "been reached.\nFree a slot with `/remove_domain`, or deploy to "
                "another hosting account.")
    return f"🔴 Failed to add domain to hosting:\n`{error_msg}`"


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
    resp = _http("GET", url, params=params, headers=_cpanel_headers(account), timeout=30, verify=True)
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
        resp = _http("POST", url, data=data, files=files, headers=_cpanel_headers(account),
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
    resp = _http("GET", url, params=params, headers=_cpanel_headers(account), timeout=120, verify=True)
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
    resp = _http("GET", url, params=params, headers=_cpanel_headers(account), timeout=30, verify=True)
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
    lookup_resp = _http("GET", lookup_url, params=lookup_params, headers=_cpanel_headers(account), timeout=15, verify=True)
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
    resp = _http("GET", url, params=params, headers=_cpanel_headers(account), timeout=30, verify=True)
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
    resp = _http("GET", url, headers=_cpanel_headers(account), timeout=60, verify=True)
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
    resp = _http("GET", f"{TG_BASE}/getFile", params={"file_id": file_id}, timeout=10)
    resp.raise_for_status()
    file_path = resp.json()["result"]["file_path"]

    # Download the actual file
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    resp = _http("GET", download_url, timeout=60)
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
_pending_slot_recovery = {}  # chat_id -> {account_idx, domains, retry}

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
                "• /setup — deploy a website\n"
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
        if chat_id in _pending_slot_recovery:
            del _pending_slot_recovery[chat_id]
            cancelled = True
        tg_send(chat_id, "🚫 Cancelled." if cancelled else "Nothing to cancel.")
        return

    # Command: /close — close the browser
    if text == "/close":
        if not BROWSER_FLOWS_ENABLED:
            tg_send(chat_id, "⚠️ This command is temporarily disabled.")
            return
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
        with _auth_lock:
            snapshot = sorted(APPROVED_USERS.items())
        if not snapshot:
            tg_send(chat_id, "No approved users.")
        else:
            lines = ["👥 *Approved Users*\n"]
            for uid, info in snapshot:
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
        with _auth_lock:
            existed = target_id in APPROVED_USERS
            if existed:
                del APPROVED_USERS[target_id]
                _save_approved_users(APPROVED_USERS)
        if existed:
            tg_send(chat_id, f"✅ User `{target_id}` has been revoked.")
            tg_send(int(target_id), "🔒 Your access has been revoked by the admin.")
            log.info(f"User {target_id} revoked by admin")
        else:
            tg_send(chat_id, f"User `{target_id}` is not in the approved list.")
        return

    # Command: /email — create email account
    if text == "/email" or text.startswith("/email "):
        if not BROWSER_FLOWS_ENABLED:
            tg_send(chat_id, "⚠️ This command is temporarily disabled.")
            return
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
        if step in ("awaiting_name", "awaiting_notify_email"):
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
        if not BROWSER_FLOWS_ENABLED:
            tg_send(chat_id, "⚠️ This command is temporarily disabled.")
            return
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
                "Send the company email — I'll look up the name & address:\n"
                "`info@company.com`\n\n"
                "_Or paste full details:_\n"
                "`Company: 2-3 Logistics Corp\n"
                "Email: info@2-3logisticscorp.com\n"
                "Address: 508 Linden Dr, Round Lake, IL 60073`")
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
    """Start API-based domain purchase flow."""
    log.info(f"Domain purchase requested: {domain}")

    if len(GODADDY_API_ACCOUNTS) == 0:
        tg_send(chat_id, "🔴 No GoDaddy API accounts configured in `.env`")
        pending_buy.pop(chat_id, None)
        return

    # If multiple accounts and none selected yet, show picker
    if account_idx is None and len(GODADDY_API_ACCOUNTS) > 1:
        pending_buy[chat_id] = pending_buy.get(chat_id, {})
        pending_buy[chat_id]["step"] = "awaiting_buy_account"
        pending_buy[chat_id]["domain"] = domain
        buttons = []
        for i, acc in enumerate(GODADDY_API_ACCOUNTS):
            buttons.append([{"text": acc["label"], "callback_data": f"buy_acc:{i}:{domain}"}])
        tg_send(chat_id,
                f"💰 *Purchase* `{domain}`\n\nWhich GoDaddy account?",
                reply_markup={"inline_keyboard": buttons})
        return

    if account_idx is None:
        account_idx = 0
    account = GODADDY_API_ACCOUNTS[account_idx]

    tg_send(chat_id, f"🔍 Checking availability for `{domain}`...")

    try:
        available, price = check_domain_availability(domain, account)

        if not available:
            pending_buy[chat_id]["step"] = "awaiting_domain"
            tg_send(chat_id, f"❌ `{domain}` is not available.",
                    reply_markup={"inline_keyboard": [[
                        {"text": "🔄 Try Another Domain", "callback_data": "buy_retry_domain"},
                        {"text": "❌ Cancel", "callback_data": "buy_cancel"},
                    ]]})
            return

        price_str = f"${price:.2f}" if price else "unknown"
        pending_buy[chat_id] = {
            "step": "awaiting_buy_confirm",
            "domain": domain,
            "account_idx": account_idx,
            "price": price_str,
        }

        tg_send(chat_id,
                f"✅ `{domain}` is available — *{price_str}/yr* (1 Year)\n\nProceed with purchase?",
                reply_markup={"inline_keyboard": [[
                    {"text": "💰 Proceed to Purchase", "callback_data": "buy_proceed"},
                    {"text": "❌ Cancel", "callback_data": "buy_cancel"},
                ]]})

    except Exception as e:
        log.error(f"Domain availability check error: {e}")
        tg_send(chat_id, f"🔴 Error checking domain:\n`{e}`")
        pending_buy.pop(chat_id, None)


def _execute_domain_purchase(chat_id):
    """Purchase the domain via GoDaddy API."""
    state = pending_buy.get(chat_id, {})
    domain = state.get("domain", "unknown")
    account_idx = state.get("account_idx", 0)
    account = GODADDY_API_ACCOUNTS[account_idx]

    try:
        tg_send(chat_id, f"💳 Purchasing `{domain}`...")
        result = purchase_domain(domain, account)
        log.info(f"Domain purchased: {domain} — {result}")
        tg_send(chat_id,
                f"✅ *Domain purchased!* `{domain}`\n\n"
                f"Want to set up hosting now?",
                reply_markup={"inline_keyboard": [[
                    {"text": "🌐 Setup Website", "callback_data": f"setup:{domain}"},
                    {"text": "❌ Done", "callback_data": "buy_cancel"},
                ]]})
        pending_buy.pop(chat_id, None)

    except Exception as e:
        log.error(f"Domain purchase error for '{domain}': {e}")
        tg_send(chat_id, f"🔴 Purchase failed for `{domain}`:\n`{e}`")
        pending_buy.pop(chat_id, None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WEBSITE GENERATION FLOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Field mapping: label in user message → internal field name
_GENERATE_FIELDS = {
    "company": "company_name",
    "email": "email",
    "address": "full_address",
    "job": "job_title",
    "pay": "pay_range",
    "home": "home_time",
    "home short": "home_time_short",
    "home detail": "home_time_detail",
    "experience": "min_experience",
    "perks": "perks",
}

_GENERATE_REQUIRED = ["company_name", "email", "full_address"]

# A message that is ONLY an email address triggers CSV auto-fill.
_BARE_EMAIL_RE = re.compile(r"^\s*([^@\s]+@[^@\s]+\.[^@\s]+)\s*$")


def _ask_route_type(chat_id):
    """Advance the generate flow to the route-type picker."""
    pending_generate[chat_id]["step"] = "awaiting_route_type"
    tg_send(chat_id, "🛣️ *Route type for this job?*",
            reply_markup={"inline_keyboard": [[
                {"text": "🚛 OTR", "callback_data": "gen_route:otr"},
                {"text": "🏠 Regional", "callback_data": "gen_route:regional"},
                {"text": "🎲 Random", "callback_data": "gen_route:random"},
            ]]})


def _apply_company_record(chat_id, rec):
    """Fill the generate state from a company_lookup record, then ask route type."""
    state = pending_generate[chat_id]
    company = rec["legal_name"]
    state["company_name"] = company
    state["company_short"] = company
    state["address"] = rec.get("address", "")
    state["city_state"] = rec.get("city_state", "")
    state.pop("company_candidates", None)
    loc = ", ".join(p for p in (rec.get("address"), rec.get("city_state")) if p)
    tg_send(chat_id, f"✅ *{company}*\n{loc}")
    _ask_route_type(chat_id)


def _handle_email_lookup(chat_id, email):
    """Look the email's company up in the CSV and route to fill/picker/fallback."""
    state = pending_generate[chat_id]
    state["email"] = email
    state["domain"] = email.split("@", 1)[1]
    matches = company_lookup.lookup(email)
    if len(matches) == 1:
        _apply_company_record(chat_id, matches[0])
    elif len(matches) > 1:
        state["company_candidates"] = matches
        buttons = [[{"text": f"{m['legal_name']} — {m['city_state']}",
                     "callback_data": f"gen_company:{i}"}]
                   for i, m in enumerate(matches)]
        tg_send(chat_id,
                f"🏢 Found {len(matches)} companies with that name. Which location?",
                reply_markup={"inline_keyboard": buttons})
    else:
        tg_send(chat_id,
                "🔍 Couldn't find that company in the list.\n\n"
                "Paste the details instead:\n"
                "`Company: ...\nEmail: ...\nAddress: ...`")


def _handle_generate_input(chat_id, raw_text):
    """Parse the single-message info block and generate."""
    state = pending_generate[chat_id]

    # A lone email address -> auto-fill company + address from the CSV.
    m = _BARE_EMAIL_RE.match(raw_text)
    if m:
        _handle_email_lookup(chat_id, m.group(1))
        return

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
        ("Company", "company_name"), ("Email", "email"), ("Address", "full_address"),
    ] if field not in parsed]

    if missing:
        tg_send(chat_id, f"⚠️ Missing required fields: {', '.join(missing)}\n\nPlease resend with all fields.")
        return

    # Derive domain from email (everything after @)
    email = parsed["email"]
    if "@" in email:
        parsed["domain"] = email.split("@", 1)[1]
    else:
        tg_send(chat_id, "⚠️ Invalid email format. Must contain `@`.")
        return

    # Use company name for logo text
    parsed["company_short"] = parsed["company_name"]

    # Split full address into street + city/state/zip at first comma
    full_addr = parsed.pop("full_address")
    if "," in full_addr:
        street, city_part = full_addr.split(",", 1)
        parsed["address"] = street.strip()
        parsed["city_state"] = city_part.strip()
    else:
        parsed["address"] = ""
        parsed["city_state"] = full_addr.strip()

    # Merge parsed into state, then ask for route type
    state.update(parsed)
    _ask_route_type(chat_id)


def _generate_random_job_info(route_choice="random"):
    """Generate random job info for website and job description."""

    # ── Job title ──
    otr_titles = [
        "OTR CDL-A Truck Driver",
        "OTR CDL-A Company Driver",
        "OTR Class A Driver",
        "OTR Company Driver — CDL-A",
        "CDL-A OTR Truck Driver",
    ]
    regional_titles = [
        "Regional CDL-A Truck Driver",
        "Regional CDL-A Company Driver",
        "Regional Class A Driver",
        "Regional Company Driver — CDL-A",
        "CDL-A Regional Truck Driver",
    ]
    if route_choice == "otr":
        is_otr = True
    elif route_choice == "regional":
        is_otr = False
    else:
        is_otr = random.random() < 0.5
    job_title = random.choice(otr_titles if is_otr else regional_titles)

    # ── Pay range ($1,200–$1,800, spread of $200–$300) ──
    spread = random.choice([200, 250, 300])
    low = random.randrange(1200, 1800 - spread + 1, 50)
    high = low + spread
    pay_range = f"${low:,} – ${high:,} / week"

    # ── Home time (based on job type) ──
    if is_otr:
        weeks_out = random.choice([2, 3])
        days_home = random.choice([3, 4, 5])
        home_time = f"Home every {weeks_out} weeks for {days_home} days"
        home_time_short = f"{weeks_out} Weeks Out"
        home_time_detail = f"Home {days_home} Days"
        routes_type = "OTR Routes"
    else:
        home_options = [
            ("Home weekly", "Weekly", "Home Weekends"),
            ("Home every weekend", "Weekly", "Home Weekends"),
            ("Home every 1-2 weeks", "1-2 Weeks Out", "Home 2 Days"),
            ("Home every week for 2 days", "Weekly", "Home 2 Days"),
        ]
        home_time, home_time_short, home_time_detail = random.choice(home_options)
        routes_type = "Regional Routes"

    # ── Experience ──
    exp_options = ["6 months", "1 year", "1 year", "1 year", "2 years"]  # weighted toward 1 year
    min_experience = random.choice(exp_options)
    # Short version for card display
    exp_short_map = {"6 months": "6 Mo. Exp", "1 year": "1 Yr. Exp", "2 years": "2 Yr. Exp"}
    fourth_card_value = exp_short_map.get(min_experience, min_experience)

    # ── Perks (6–8 total, always include 401k + one insurance) ──
    insurance = random.choice(["Health insurance", "Dental & Vision insurance"])
    fixed_perks = ["401(k) with match", insurance]
    other_perks = [
        "Fuel card", "Fuel discount", "Paid orientation",
        "Paid time off", "Passenger ride along program", "Performance bonus",
        "Pet & Rider program", "Referral program", "Safety equipment provided",
    ]
    random.shuffle(other_perks)
    num_other = random.randint(4, 6)  # 2 fixed + 4-6 others = 6-8 total
    perks = fixed_perks + other_perks[:num_other]
    random.shuffle(perks)

    return {
        "job_title": job_title,
        "pay_range": pay_range,
        "home_time": home_time,
        "home_time_short": home_time_short,
        "home_time_detail": home_time_detail,
        "min_experience": min_experience,
        "fourth_card_value": fourth_card_value,
        "fourth_card_label": "Min. Required",
        "routes": "Multi-State" if not is_otr else "48 States",
        "routes_type": routes_type,
        "perks": perks,
    }


def _finish_generate(chat_id):
    """Generate the website and job description, send to user."""
    state = pending_generate.pop(chat_id)
    tg_send(chat_id, "⏳ Generating website and job description...")

    try:
        from website_generator import generate_website_from_blocks, generate_job_description

        # Build info: company details from user, job info auto-generated
        company = state["company_name"]
        route_choice = state.get("route_type", "random")
        job_info = _generate_random_job_info(route_choice=route_choice)

        info = {
            "company_name": company,
            "company_short": state.get("company_short", company.split()[0]),
            "domain": state["domain"],
            "email": state["email"],
            "address": state.get("address", ""),
            "city_state": state["city_state"],
        }
        info.update(job_info)

        # Show what was auto-generated
        perks_str = ", ".join(info["perks"])
        tg_send(chat_id,
                f"🎲 *Auto-generated job info:*\n"
                f"Job: {info['job_title']}\n"
                f"Pay: {info['pay_range']}\n"
                f"Home: {info['home_time']}\n"
                f"Experience: {info['min_experience']}\n"
                f"Perks: {perks_str}")

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
            elif _is_addon_limit_error(error_msg):
                log.error(f"cPanel addon cap hit for {domain}")
                _offer_free_slot(chat_id, account_idx,
                                 {"kind": "setup", "domain": domain,
                                  "account_idx": account_idx})
                return
            else:
                log.error(f"cPanel domain creation failed: {error_msg}")
                tg_send(chat_id, _friendly_cpanel_error(error_msg))
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


def _list_addon_domains(account: dict) -> list:
    """Return the account's addon domains (addon only — not main/parked)."""
    url = f"{account['url']}/execute/DomainInfo/list_domains"
    resp = _http("GET", url, headers=_cpanel_headers(account), timeout=15, verify=True)
    resp.raise_for_status()
    data = resp.json().get("data", {})
    return list(data.get("addon_domains", []))


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
        resp = _http("GET", url, headers=_cpanel_headers(account), timeout=15, verify=True)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        all_domains = (list(data.get("addon_domains", []))
                       + list(data.get("parked_domains", []))
                       + [data.get("main_domain", "")])
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
        pending_email[chat_id]["step"] = "awaiting_name"
        tg_send(chat_id,
                f"📧 *Email Setup for* `{domain}`\n\n"
                f"👤 First and last name?\n"
                f"Example: `John Doe`")
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

    if step == "awaiting_name":
        parts = raw_text.strip().split(None, 1)
        if len(parts) < 2:
            tg_send(chat_id, "⚠️ Need both first and last name. Example: `John Doe`")
            return
        state["first_name"] = parts[0]
        state["last_name"] = parts[1]
        state["username"] = parts[0].lower()
        tg_send(chat_id, f"Email: `{state['username']}@{state['domain']}`")
        state["step"] = "awaiting_admin"
        tg_send(chat_id,
                "🔐 *Administrator permissions?*",
                reply_markup={
                    "inline_keyboard": [[
                        {"text": "Yes", "callback_data": "email_admin:yes"},
                        {"text": "No", "callback_data": "email_admin:no"},
                    ]]
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
    bot = None

    try:
        from email_automation import GoDaddyEmailBot

        # Reuse existing browser if it's open for the same account (this chat)
        existing = active_browser.get(chat_id)
        if existing and getattr(existing, 'account_idx', None) == account_idx and existing._page:
            bot = existing
            active_browser.pop(chat_id)
            tg_send(chat_id, f"⏳ Reusing open browser, navigating to email form...")
            log.info(f"Reusing existing browser for account {account_idx}")
        else:
            # Close old browser if it's a different account or stale (this chat)
            if existing:
                try:
                    existing.close()
                except Exception:
                    pass
                active_browser.pop(chat_id, None)
                log.info("Closed previous browser (different account or stale)")

            # Check if another chat has a browser open on the same account
            # (only one browser can lock a profile at a time)
            for other_cid, other_bot in list(active_browser.items()):
                if getattr(other_bot, 'account_idx', None) == account_idx:
                    log.info(f"Closing browser left open by chat {other_cid} on account {account_idx}")
                    try:
                        other_bot.close()
                    except Exception:
                        pass
                    active_browser.pop(other_cid, None)
                    tg_send(other_cid, f"ℹ️ Browser was closed — another user started `/email` on the same account.")

            tg_send(chat_id, f"⏳ Opening browser and navigating to GoDaddy ({account['email']})...")
            bot = GoDaddyEmailBot(
                email=account["email"],
                password=account["password"],
                account_idx=account_idx,
                headless=EMAIL_HEADLESS,
            )
            bot.open()

        bot.go_to_create_email(domain)

        dates = bot.get_expiration_dates(_domain=domain)
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
        pending_email.pop(chat_id, None)
        # Keep browser open for reuse or manual inspection
        if bot and bot._page:
            active_browser[chat_id] = bot
            tg_send(chat_id, f"🔴 Browser automation failed:\n`{e}`\n\nBrowser left open — retry with `/email` or `/close` when done.")
        else:
            tg_send(chat_id, f"🔴 Browser automation failed:\n`{e}`")


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

def _manual_cpanel_removal_msg(chat_id, domain, account, retry_ctx=None):
    """Tell the user to remove a specific domain manually in cPanel (auto-removal failed)."""
    markup = None
    if retry_ctx is not None:
        markup = {"inline_keyboard": [[
            {"text": "🔁 Retry deploy", "callback_data": "freeslot_retry"},
        ]]}
    tg_send(chat_id,
            f"⚠️ Couldn't remove `{domain}` automatically (cPanel refused / no access).\n\n"
            f"Remove it manually: log into cPanel → *Domains / Addon Domains* → "
            f"delete `{domain}`.\n"
            f"cPanel: {account['url']}",
            reply_markup=markup)


def _offer_free_slot(chat_id, account_idx, retry_ctx):
    """On the addon cap, offer to remove a domain (buttons) and retry the deploy."""
    account = CPANEL_ACCOUNTS[account_idx]
    tg_send(chat_id,
            "🔴 This hosting account is full — the 50 addon-domain limit has been "
            "reached.\nYou can remove a domain to free a slot, then retry.")
    # Stash retry context first so the Retry button works on every path below.
    _pending_slot_recovery[chat_id] = {
        "account_idx": account_idx, "domains": [], "retry": retry_ctx,
    }
    try:
        domains = _list_addon_domains(account)
    except Exception as e:
        log.error(f"Could not list addon domains: {e}")
        domains = []
    if not domains:
        # Can't list the account's domains — guide the user to free a slot
        # manually (don't name the domain being deployed; it isn't in cPanel).
        tg_send(chat_id,
                "⚠️ I couldn't list this account's domains to remove one "
                "automatically.\nFree a slot manually: log into cPanel → "
                "*Domains / Addon Domains* → delete a domain, then tap Retry.\n"
                f"cPanel: {account['url']}",
                reply_markup={"inline_keyboard": [[
                    {"text": "🔁 Retry deploy", "callback_data": "freeslot_retry"},
                ]]})
        return
    _pending_slot_recovery[chat_id]["domains"] = domains
    buttons = [[{"text": f"🗑 {d}", "callback_data": f"freeslot_rm:{i}"}]
               for i, d in enumerate(domains)]
    buttons.append([{"text": "❌ Cancel", "callback_data": "freeslot_cancel"}])
    tg_send(chat_id, "Which domain should I remove to free a slot?",
            reply_markup={"inline_keyboard": buttons})


def _fetch_company_data(url):
    """Fetch a deployed site and return (company_data, partial). Reads the
    embedded company-data JSON when present (partial=False); else falls back to
    a domain->CSV lookup for name/address (partial=True, job specifics absent);
    else (None, False)."""
    from website_generator import extract_company_data
    u = (url or "").strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    html = None
    for verify in (True, False):
        try:
            html = _http("GET", u, timeout=20, verify=verify).text
            break
        except Exception as e:
            log.warning(f"appeal fetch (verify={verify}) failed: {e}")
    if html:
        data = extract_company_data(html)
        if data:
            return data, False
    domain = u.split("//", 1)[-1].split("/", 1)[0]
    matches = company_lookup.lookup(domain)
    if len(matches) == 1:
        m = matches[0]
        return {
            "company_name": m["legal_name"], "address": m.get("address", ""),
            "city_state": m.get("city_state", ""), "domain": domain,
            "owner_name": "", "perks": [],
        }, True
    return None, False


def _deploy_to_cpanel(chat_id, domain, zip_path, account_idx):
    """Create the domain, upload + extract the zip, delete the server-side zip.

    Takes explicit params (no _pending_deploys / _pending_slot_recovery access),
    so both the original deploy and the post-removal retry call it the same way.
    """
    account = CPANEL_ACCOUNTS[account_idx]

    # Create domain on cPanel
    tg_send(chat_id, f"🌐 Adding `{domain}` to hosting ({account['label']})...")
    try:
        result = cpanel_create_domain(domain, account)
        errors = result.get("errors")
        if errors:
            error_msg = str(errors)
            if "already" in error_msg.lower() or "exists" in error_msg.lower():
                tg_send(chat_id, f"ℹ️ `{domain}` already exists in hosting. Continuing...")
            elif _is_addon_limit_error(error_msg):
                _offer_free_slot(chat_id, account_idx,
                                 {"kind": "generate", "domain": domain,
                                  "zip_path": zip_path, "account_idx": account_idx})
                return
            else:
                tg_send(chat_id, _friendly_cpanel_error(error_msg))
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


def handle_callback(callback_query_id, chat_id, message_id, data):
    """Handle an inline button press."""
    log.info(f"[{chat_id}] Callback: {data}")
    tg_answer_callback(callback_query_id)

    # Admin: approve/deny user access
    if data.startswith("approve:"):
        target_id = data.split(":", 1)[1]
        with _auth_lock:
            user_info = _pending_approvals.pop(target_id, {"name": "Unknown", "username": ""})
            APPROVED_USERS[target_id] = user_info
            _save_approved_users(APPROVED_USERS)
        tg_edit_message(chat_id, message_id, f"✅ User `{target_id}` approved.")
        tg_send(int(target_id), "✅ Your access has been approved! Send /start to begin.")
        log.info(f"User {target_id} approved by admin")
        return

    if data.startswith("deny:"):
        target_id = data.split(":", 1)[1]
        with _auth_lock:
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

    if data == "buy_retry_domain":
        pending_buy[chat_id] = pending_buy.get(chat_id, {})
        pending_buy[chat_id]["step"] = "awaiting_domain"
        tg_edit_message(chat_id, message_id, "🔄 Trying another domain.")
        tg_send(chat_id, "What domain? Example: `mysite.com`")
        return

    if data.startswith("gen_company:"):
        state = pending_generate.get(chat_id)
        candidates = state.get("company_candidates") if state else None
        if not candidates:
            tg_edit_message(chat_id, message_id, "⚠️ No active generate flow.")
            return
        try:
            idx = int(data.split(":", 1)[1])
            rec = candidates[idx]
        except (ValueError, IndexError):
            tg_edit_message(chat_id, message_id, "⚠️ Invalid choice.")
            return
        tg_edit_message(chat_id, message_id, f"📍 {rec['legal_name']} — {rec['city_state']}")
        _apply_company_record(chat_id, rec)
        return

    if data.startswith("gen_route:"):
        route = data.split(":", 1)[1]  # otr, regional, or random
        state = pending_generate.get(chat_id)
        if not state:
            tg_edit_message(chat_id, message_id, "⚠️ No active generate flow.")
            return
        label = {"otr": "🚛 OTR", "regional": "🏠 Regional", "random": "🎲 Random"}.get(route, route)
        tg_edit_message(chat_id, message_id, f"Route type: {label}")
        state["route_type"] = route
        _finish_generate(chat_id)
        return

    if data.startswith("buy_acc:"):
        # Account picker callback: buy_acc:IDX:domain
        parts = data.split(":", 2)
        idx = int(parts[1])
        domain = parts[2]
        tg_edit_message(chat_id, message_id, f"Account: {GODADDY_API_ACCOUNTS[idx]['label']}")
        _start_domain_purchase(chat_id, domain, account_idx=idx)
        return

    if data == "buy_proceed":
        state = pending_buy.get(chat_id, {})
        domain = state.get("domain", "unknown")
        price = state.get("price", "unknown")
        tg_edit_message(chat_id, message_id, f"💰 `{domain}` — {price}/yr")
        tg_send(chat_id,
                f"⚠️ *Confirm purchase*\n\n"
                f"Domain: `{domain}`\n"
                f"Price: *{price}/yr*\n\n"
                f"This will charge your GoDaddy account. Buy now?",
                reply_markup={"inline_keyboard": [[
                    {"text": "💰 Buy Now", "callback_data": "buy_confirm"},
                    {"text": "❌ Cancel", "callback_data": "buy_cancel"},
                ]]})
        return

    if data == "buy_confirm":
        tg_edit_message(chat_id, message_id, "⏳ Purchasing...")
        _execute_domain_purchase(chat_id)
        return

    if data == "buy_cancel":
        pending_buy.pop(chat_id, None)
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
    if data.startswith("freeslot_rm:"):
        rec = _pending_slot_recovery.get(chat_id)
        if not rec or not rec.get("domains"):
            tg_edit_message(chat_id, message_id, "⚠️ No active recovery.")
            return
        try:
            idx = int(data.split(":", 1)[1])
            domain = rec["domains"][idx]
        except (ValueError, IndexError):
            tg_edit_message(chat_id, message_id, "⚠️ Invalid choice.")
            return
        tg_edit_message(chat_id, message_id, f"🗑 Remove `{domain}`?")
        tg_send(chat_id, f"⚠️ Permanently remove `{domain}` from hosting?",
                reply_markup={"inline_keyboard": [[
                    {"text": "✅ Yes, Remove", "callback_data": f"freeslot_confirm:{idx}"},
                    {"text": "❌ Cancel", "callback_data": "freeslot_cancel"},
                ]]})
        return

    if data.startswith("freeslot_confirm:"):
        rec = _pending_slot_recovery.get(chat_id)
        if not rec or not rec.get("domains"):
            tg_edit_message(chat_id, message_id, "⚠️ No active recovery.")
            return
        try:
            idx = int(data.split(":", 1)[1])
            domain = rec["domains"][idx]
        except (ValueError, IndexError):
            tg_edit_message(chat_id, message_id, "⚠️ Invalid choice.")
            return
        account = CPANEL_ACCOUNTS[rec["account_idx"]]
        retry_ctx = rec.get("retry")
        tg_edit_message(chat_id, message_id, f"⏳ Removing `{domain}`...")
        try:
            result = cpanel_remove_domain(domain, account)
            if result.get("errors"):
                log.error(f"Slot-recovery removal failed: {result.get('errors')}")
                _manual_cpanel_removal_msg(chat_id, domain, account, retry_ctx=retry_ctx)
                return
        except Exception as e:
            log.error(f"Slot-recovery removal error: {e}")
            _manual_cpanel_removal_msg(chat_id, domain, account, retry_ctx=retry_ctx)
            return
        # Success — offer retry. Keep domains list index-stable (don't mutate):
        # the original list message's buttons stay valid; a tap on an already-
        # removed domain safely yields cPanel "not found" -> manual fallback.
        tg_send(chat_id, f"✅ `{domain}` removed.",
                reply_markup={"inline_keyboard": [[
                    {"text": "🔁 Retry deploy", "callback_data": "freeslot_retry"},
                ]]})
        return

    if data == "freeslot_cancel":
        _pending_slot_recovery.pop(chat_id, None)
        tg_edit_message(chat_id, message_id, "🚫 Cancelled.")
        return

    if data == "freeslot_retry":
        rec = _pending_slot_recovery.pop(chat_id, None)
        retry_ctx = rec.get("retry") if rec else None
        if not retry_ctx:
            tg_edit_message(chat_id, message_id, "⚠️ Nothing to retry.")
            return
        tg_edit_message(chat_id, message_id, "🔁 Retrying...")
        if retry_ctx["kind"] == "generate":
            _deploy_to_cpanel(chat_id, retry_ctx["domain"],
                              retry_ctx["zip_path"], retry_ctx["account_idx"])
        elif retry_ctx["kind"] == "setup":
            _start_website_setup(chat_id, retry_ctx["domain"],
                                 account_idx=retry_ctx["account_idx"])
        return

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
                _manual_cpanel_removal_msg(chat_id, domain, account)
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
        state["step"] = "awaiting_name"
        acc = GODADDY_ACCOUNTS[idx]
        tg_edit_message(chat_id, message_id, f"Account: {acc['email']}")
        tg_send(chat_id,
                f"👤 First and last name?\n"
                f"Example: `John Doe`")
        return

    if data.startswith("email_admin:"):
        choice = data.split(":")[1]
        state = pending_email.get(chat_id)
        if not state:
            return
        state["admin"] = (choice == "yes")
        state["password"] = "Iamawesome98"
        state["step"] = "awaiting_notify_email"
        tg_edit_message(chat_id, message_id, f"Admin: {'Yes' if state['admin'] else 'No'}")
        tg_send(chat_id,
                "📬 Send account info to which email?",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "smfleet02@gmail.com", "callback_data": "email_notify:smfleet02@gmail.com"}],
                        [{"text": "phillhr57@gmail.com", "callback_data": "email_notify:phillhr57@gmail.com"}],
                    ]
                })
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
        _deploy_to_cpanel(chat_id, deploy["domain"], deploy["zip_path"], idx)
        return

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN LOOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def tg_set_commands():
    """Register bot commands so they appear in Telegram's menu."""
    commands = [
        {"command": "start", "description": "Show welcome message"},
        {"command": "setup", "description": "Deploy website to hosting"},
        {"command": "generate", "description": "Generate website + job description"},
        {"command": "run_autossl", "description": "Run AutoSSL for a domain"},
        {"command": "remove_domain", "description": "Remove a domain from hosting"},
        {"command": "cancel", "description": "Cancel current operation"},
        {"command": "users", "description": "List approved users (admin)"},
        {"command": "revoke", "description": "Revoke user access (admin)"},
    ]
    try:
        _http("POST", f"{TG_BASE}/setMyCommands",
                      json={"commands": commands}, timeout=10)
        log.info("Bot commands registered with Telegram")
    except Exception as e:
        log.warning(f"Failed to register commands: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONCURRENCY: dispatcher + per-chat worker threads
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_chat_workers = {}            # chat_id -> ChatWorker
_workers_lock = threading.Lock()


class ChatWorker:
    """One daemon thread + queue per chat. Processes that chat's updates in order."""

    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.queue = queue.Queue()
        self.thread = threading.Thread(
            target=self._run, name=f"chat-{chat_id}", daemon=True
        )
        self.thread.start()

    def submit(self, update):
        self.queue.put(update)

    def _run(self):
        while True:
            update = self.queue.get()
            try:
                process_update(update)
            except Exception:
                log.exception(f"Worker error processing update for chat {self.chat_id}")
                try:
                    tg_send(self.chat_id, "⚠️ Something went wrong, please try again.")
                except Exception:
                    pass


def _get_worker(chat_id):
    """Get (or lazily create) the worker for a chat."""
    with _workers_lock:
        worker = _chat_workers.get(chat_id)
        if worker is None:
            worker = ChatWorker(chat_id)
            _chat_workers[chat_id] = worker
        return worker


def _handle_unapproved(chat_id, msg):
    """Main-thread access-request flow for an unapproved user (deduped, runs once)."""
    str_id = str(chat_id)
    with _auth_lock:
        already = str_id in _pending_approvals
        if not already:
            user = msg.get("from", {})
            _pending_approvals[str_id] = {
                "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Unknown",
                "username": user.get("username", ""),
            }
    if already:
        return
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


def process_update(update):
    """Route an already-authorized update to the right handler (runs on a worker)."""
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        if "document" in msg:
            handle_document(chat_id, msg["document"], msg)
            return
        text = msg.get("text", "")
        if text:
            handle_message(chat_id, text, msg.get("message_id"))
    elif "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")
        handle_callback(cb["id"], chat_id, cb["message"]["message_id"], data)


def dispatch(update):
    """Main-thread routing: authorize, then enqueue to the chat's worker."""
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        if not is_authorized(chat_id):
            _handle_unapproved(chat_id, msg)
            return
        _get_worker(chat_id).submit(update)

    elif "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")
        # Admin approve/deny: only the admin may trigger; handled on a worker.
        if data.startswith("approve:") or data.startswith("deny:"):
            if str(chat_id) == ADMIN_CHAT_ID:
                _get_worker(chat_id).submit(update)
            return
        if not is_authorized(chat_id):
            return
        _get_worker(chat_id).submit(update)


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
            try:
                dispatch(update)
            except Exception:
                log.exception("Dispatch error")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
        print("\n  Bot stopped.")
