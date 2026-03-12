# Code Explained — Line by Line

A learning guide that explains every part of `main.py` and what each piece does.

---

## 1. Imports (Lines 14–22)

```python
import requests          # Makes HTTP requests (like a browser visiting a URL, but in code)
import json              # Converts Python dicts ↔ JSON strings (the format APIs speak)
import logging           # Built-in Python logging — writes messages to console and files
import os                # Access environment variables (like reading from .env)
import sys               # System stuff — we use sys.stdout for console output
import re                # Regular expressions — pattern matching for validating domain names
import time              # time.sleep() — pause execution (used when polling fails)
from datetime import datetime, timezone  # Get current date/time in UTC
from pathlib import Path                 # Work with file paths in a clean way
```

**Why these?** Every import is a tool. `requests` talks to APIs. `json` formats data. `logging` records what happens. `os` reads secrets from `.env`. `re` validates input. None of these are third-party except `requests` — the rest come with Python.

---

## 2. Loading .env File (Lines 28–39)

```python
def _load_env():
    env_path = Path(__file__).parent / ".env"    # Find .env next to main.py
    if not env_path.exists():                     # If no .env file, skip
        return
    for line in env_path.read_text().splitlines():  # Read every line
        line = line.strip()
        if not line or line.startswith("#"):         # Skip empty lines and comments
            continue
        key, _, value = line.partition("=")          # Split "KEY=VALUE" into parts
        os.environ.setdefault(key.strip(), value.strip())  # Save to environment

_load_env()  # Run immediately when file loads
```

**What it does:** Reads the `.env` file and loads each `KEY=VALUE` pair into `os.environ` — Python's way of accessing environment variables. This keeps secrets out of the code.

**Why `setdefault`?** It only sets the value if the key doesn't already exist. So if you set a real environment variable on your system, it won't be overwritten by `.env`.

**Why not use `python-dotenv`?** We wrote our own loader to avoid an extra dependency. It's only 10 lines and does the same thing.

---

## 3. Configuration (Lines 45–70)

```python
GODADDY_API_KEY    = os.environ.get("GODADDY_API_KEY", "")
GODADDY_API_SECRET = os.environ.get("GODADDY_API_SECRET", "")
GODADDY_ENV        = os.environ.get("GODADDY_ENV", "ote")
```

**What it does:** Reads values from environment variables (which were loaded from `.env`). The second argument (`""` or `"ote"`) is the default if the key isn't found.

```python
REGISTRANT = {
    "nameFirst": os.environ.get("REGISTRANT_FIRST_NAME", ""),
    ...
}
```

**What it does:** Builds a dictionary (Python dict) with the contact info GoDaddy requires for domain registration (WHOIS data). This gets sent with every purchase request.

**Why `nameFirst` not `firstName`?** GoDaddy's API schema uses `nameFirst`/`nameLast`. We learned this the hard way — using `firstName` gave a 422 error.

---

## 4. Logging Setup (Lines 76–97)

```python
def setup_logging():
    logger = logging.getLogger("automation")   # Create a named logger
    logger.setLevel(logging.DEBUG)             # Capture everything from DEBUG up

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",  # Format: timestamp + level + message
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    ch = logging.StreamHandler(sys.stdout)     # Handler 1: print to console
    ch.setLevel(logging.INFO)                  # Console only shows INFO and above

    fh = logging.FileHandler(LOG_FILE)         # Handler 2: write to automation.log
    fh.setLevel(logging.DEBUG)                 # File captures everything (DEBUG too)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

log = setup_logging()
```

**What it does:** Sets up two places for log messages to go:
- **Console** — You see INFO, WARNING, ERROR while the bot runs
- **automation.log** — Everything including DEBUG for troubleshooting later

**Log levels (lowest to highest):** DEBUG → INFO → WARNING → ERROR → CRITICAL

**How to use it:** `log.info("something happened")`, `log.error("something broke")`

---

## 5. Telegram Bot Functions (Lines 103–144)

### Base URL
```python
TG_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
```
Every Telegram bot API call starts with this URL. Your bot token is like a password — it proves you own the bot.

### Sending a message
```python
def tg_send(chat_id, text, reply_markup=None):
    payload = {
        "chat_id":    chat_id,       # Who to send to
        "text":       text,           # The message text
        "parse_mode": "Markdown",     # Allow *bold*, `code`, etc.
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)  # Add buttons if provided
    resp = requests.post(f"{TG_BASE}/sendMessage", json=payload, timeout=10)
    resp.raise_for_status()  # Crash if Telegram returns an error
```

**What it does:** Sends a text message to a Telegram chat. The optional `reply_markup` parameter adds inline buttons (like Buy/Cancel).

**What is `json=payload`?** It tells `requests` to convert the Python dict to JSON and set the `Content-Type: application/json` header automatically.

**What is `raise_for_status()`?** If the HTTP response is 4xx or 5xx (an error), it throws an exception instead of silently failing.

### Answering button presses
```python
def tg_answer_callback(callback_query_id):
    requests.post(f"{TG_BASE}/answerCallbackQuery",
                  json={"callback_query_id": callback_query_id}, timeout=10)
```

**What it does:** When a user taps an inline button, Telegram shows a loading spinner. This call tells Telegram "I received it" and removes the spinner. Without this, the button looks stuck.

### Editing a sent message
```python
def tg_edit_message(chat_id, message_id, text):
```

**What it does:** Changes the text of a message the bot already sent. We use this to update "Purchase this domain?" to "Purchasing..." after the user taps Buy.

### Getting new messages (long-polling)
```python
def tg_get_updates(offset=None):
    params = {"timeout": 30}        # Wait up to 30 seconds for new messages
    if offset:
        params["offset"] = offset   # Only get messages after this ID
    resp = requests.get(f"{TG_BASE}/getUpdates", params=params, timeout=35)
```

**What it does:** Asks Telegram "any new messages?" and waits up to 30 seconds. If a message comes in during that time, it returns immediately. If not, it returns an empty list and we ask again. This is called **long-polling**.

**What is `offset`?** It tells Telegram "I already processed messages up to this ID, only give me newer ones." Without it, you'd get the same messages over and over.

**Why `timeout=35` but `"timeout": 30`?** The 30 is for Telegram's server (wait 30s for messages). The 35 is for the `requests` library (give up after 35s total). The extra 5s is buffer so `requests` doesn't time out before Telegram responds.

---

## 6. GoDaddy API Functions (Lines 150–198)

### Base URL selection
```python
GODADDY_BASE = (
    "https://api.godaddy.com"          # Real purchases, real money
    if GODADDY_ENV == "production"
    else "https://api.ote-godaddy.com"  # Sandbox, no charges
)
```

**What it does:** Picks which GoDaddy server to talk to based on your `GODADDY_ENV` setting. This is a **ternary expression** — Python's one-line if/else.

### Auth headers
```python
def _gd_headers():
    return {
        "Authorization": f"sso-key {GODADDY_API_KEY}:{GODADDY_API_SECRET}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }
```

**What it does:** Builds the HTTP headers that GoDaddy requires. The `Authorization` header is how GoDaddy knows it's you — like showing an ID badge. The `sso-key KEY:SECRET` format is GoDaddy-specific.

### Checking availability
```python
def check_domain_availability(domain: str) -> tuple[bool, float]:
    url  = f"{GODADDY_BASE}/v1/domains/available"
    resp = requests.get(url, headers=_gd_headers(), params={"domain": domain}, timeout=15)
    resp.raise_for_status()
    data      = resp.json()                         # Parse JSON response
    available = data.get("available", False)         # Is it available?
    price     = data.get("price", 0) / 1_000_000    # Convert microdollars to dollars
    return available, price
```

**What it does:** Calls GoDaddy's API to check if a domain is available and how much it costs.

**What are microdollars?** GoDaddy returns prices like `12990000` instead of `12.99`. Dividing by 1,000,000 converts to real dollars. They do this to avoid floating-point precision issues.

**What is `-> tuple[bool, float]`?** It's a type hint — it tells you (and your IDE) that this function returns two values: a boolean and a float. Python doesn't enforce it, it's just documentation.

### Purchasing a domain
```python
def purchase_domain(domain: str, years: int = 1) -> dict:
    payload = {
        "domain":    domain,
        "period":    years,          # How many years to register
        "renewAuto": True,           # Auto-renew when it expires
        "privacy":   False,          # WHOIS privacy protection (costs extra)
        "consent": {
            "agreedAt":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "agreedBy":      REGISTRANT["email"],
            "agreementKeys": ["DNRA"],   # Domain Name Registration Agreement
        },
        "contactAdmin":      REGISTRANT,  # All 4 contacts use the same info
        "contactBilling":    REGISTRANT,
        "contactRegistrant": REGISTRANT,
        "contactTech":       REGISTRANT,
    }
    resp = requests.post(url, headers=_gd_headers(), json=payload, timeout=30)
```

**What it does:** Sends a POST request to GoDaddy to buy the domain. The payload includes everything GoDaddy needs: which domain, for how long, who's registering it, and legal consent.

**Why 4 contacts?** ICANN (the organization that manages domains) requires separate Admin, Billing, Registrant, and Technical contacts. Most people use the same info for all four.

**What is `"DNRA"`?** Domain Name Registration Agreement — a legal requirement saying you agree to the terms of registering a domain.

---

## 7. Domain Validation (Lines 204–208)

```python
DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}$"
)
```

**What it does:** Creates a compiled regular expression (regex) that matches valid domain names like `mysite.com` or `sub.domain.co.uk`.

**Breaking down the pattern:**
- `^` — Start of string
- `[a-zA-Z0-9]` — First character must be a letter or number
- `[a-zA-Z0-9\-]{0,61}` — Middle can be letters, numbers, or hyphens (up to 61 chars)
- `[a-zA-Z0-9]` — Last character before the dot must be a letter or number
- `\.` — Literal dot
- `+` — One or more of the above groups (allows subdomains)
- `[a-zA-Z]{2,}$` — TLD must be at least 2 letters (.com, .io, .uk, etc.)

**Why `re.compile()`?** Pre-compiles the pattern so it's faster when used repeatedly. Without it, Python would re-parse the pattern every time.

---

## 8. Bot Handlers (Lines 214–285)

### handle_message — processes text messages
```python
def handle_message(chat_id, text):
    text = text.strip().lower()            # Clean up and lowercase

    if text == "/start":                   # Telegram sends this when user first opens bot
        tg_send(chat_id, "👋 *GoDaddy Domain Bot*...")
        return

    if not DOMAIN_RE.match(text):          # Not a valid domain format
        tg_send(chat_id, "⚠️ Invalid domain format...")
        return

    # If we get here, it's a valid domain
    tg_send(chat_id, f"🔍 Checking availability of `{domain}`...")
    available, price = check_domain_availability(domain)

    if not available:
        tg_send(chat_id, f"❌ `{domain}` is not available...")
        return

    # Available! Show Buy/Cancel buttons
    tg_send(chat_id, f"✅ `{domain}` is available — *${price:.2f}/year*...",
        reply_markup={
            "inline_keyboard": [[
                {"text": "💰 Buy", "callback_data": f"buy:{domain}"},
                {"text": "❌ Cancel", "callback_data": "cancel"},
            ]]
        })
```

**What is `inline_keyboard`?** Telegram's way of showing clickable buttons inside a message. Each button has display `text` and hidden `callback_data` that gets sent back when tapped.

**What is `f"buy:{domain}"`?** We encode the domain in the button's callback data so when the user taps Buy, we know which domain they want. Telegram sends back `"buy:mysite.com"` and we parse it.

**What is `${price:.2f}`?** An f-string format spec. `.2f` means "format as float with 2 decimal places" — so `12.9` becomes `12.90`.

### handle_callback — processes button taps
```python
def handle_callback(callback_query_id, chat_id, message_id, data):
    tg_answer_callback(callback_query_id)     # Remove loading spinner

    if data == "cancel":
        tg_edit_message(chat_id, message_id, "🚫 Purchase cancelled.")
        return

    if data.startswith("buy:"):
        domain = data.split(":", 1)[1]        # Extract domain from "buy:mysite.com"
        tg_edit_message(chat_id, message_id, f"⏳ Purchasing `{domain}`...")

        order = purchase_domain(domain)
        tg_send(chat_id, f"✅ *Domain purchased!*\n\nDomain: `{domain}`\nOrder ID: `{order_id}`")
```

**What is `split(":", 1)[1]`?** Splits `"buy:mysite.com"` at the first colon into `["buy", "mysite.com"]` and takes index `[1]` (the domain). The `1` limits it to one split, in case the domain somehow contains a colon.

---

## 9. Main Loop (Lines 291–347)

```python
def run():
    # Print startup banner...
    tg_send(TELEGRAM_CHAT_ID, "🤖 *Bot is online!*...")  # Notify user on Telegram

    offset = None
    while True:                              # Run forever
        updates = tg_get_updates(offset)     # Wait for new messages (up to 30s)

        for update in updates:
            offset = update["update_id"] + 1  # Mark this update as processed

            if "message" in update:           # It's a text message
                chat_id = update["message"]["chat"]["id"]
                if str(chat_id) != str(TELEGRAM_CHAT_ID):  # Not our authorized user
                    continue                                 # Ignore
                handle_message(chat_id, text)

            elif "callback_query" in update:  # It's a button press
                # Same auth check, then handle_callback(...)
```

**What is this loop?** It's the bot's heartbeat. It asks Telegram for updates, processes them, then asks again. Forever. This is how the bot stays "alive" and responsive.

**What is `offset`?** Each Telegram update has a unique ID. By sending `offset = last_id + 1`, we tell Telegram "I already handled everything up to here, only give me new stuff." Without this, the bot would re-process old messages on every loop.

**Why check `chat_id != TELEGRAM_CHAT_ID`?** Security. Only your personal Telegram account can use this bot. Anyone else who messages it gets ignored.

**What is `while True`?** An infinite loop. The bot runs until you press Ctrl+C or kill the process.

```python
if __name__ == "__main__":
    run()
```

**What is this?** Standard Python entry point. It means "only run `run()` if this file is executed directly (not imported as a module)."

---

## Concepts Summary

| Concept | Where Used | What It Means |
|---------|-----------|---------------|
| **API** | GoDaddy, Telegram | A URL you send data to and get data back from |
| **HTTP Methods** | GET (read), POST (create/send) | The "verb" of the request |
| **JSON** | Everywhere | Text format for structured data: `{"key": "value"}` |
| **Headers** | `_gd_headers()` | Extra info sent with a request (auth, content type) |
| **Environment Variables** | `os.environ` | System-level key/value storage for secrets |
| **Long-polling** | `tg_get_updates()` | Keep asking "anything new?" in a loop |
| **Inline Keyboard** | `reply_markup` | Clickable buttons in Telegram messages |
| **Callback Data** | `buy:domain.com` | Hidden data sent when a button is tapped |
| **Regex** | `DOMAIN_RE` | Pattern matching to validate text format |
| **f-strings** | `f"Hello {name}"` | Python string interpolation |
| **Type hints** | `-> tuple[bool, float]` | Documentation for function inputs/outputs |
| **raise_for_status()** | After API calls | Throw an error if HTTP response is bad |
