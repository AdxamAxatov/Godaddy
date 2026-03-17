# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot that automates GoDaddy operations: domain purchases, website generation & deployment (cPanel), and M365 email account creation (Playwright browser automation). All interaction happens through Telegram — no CLI interaction.

## Running

```bash
source .venv/Scripts/activate   # Windows Git Bash
python src/main.py              # Starts Telegram long-polling loop
```

## Dependencies

Python 3.12, managed via a local `.venv`. Key packages: `requests`, `playwright`. No `requirements.txt` — install with `pip install requests playwright`. Browser automation uses the system's real Chrome (`channel="chrome"`), not Playwright's bundled Chromium, to avoid GoDaddy's bot detection.

## Architecture

Three files in `src/`:

- **`src/main.py`** — Telegram bot, GoDaddy API, cPanel API, and all bot flow logic (state machines for buy, setup, email, generate)
- **`src/email_automation.py`** — `GoDaddyEmailBot` class: Playwright browser automation for GoDaddy Email & Office email creation
- **`src/website_generator.py`** — Block-based website HTML generator + Indeed job description generator for trucking companies

### main.py sections

- **Telegram Bot** — `tg_send()`, `tg_edit_message()`, `tg_answer_callback()`, `tg_get_updates()`, `tg_send_photo()`, `tg_send_document()`, `tg_delete_message()` for raw Telegram API calls
- **GoDaddy API** — `check_domain_availability()` (GET `/v1/domains/available`), `purchase_domain()` (POST `/v1/domains/purchase`)
- **cPanel API** — `cpanel_create_domain()` (API2 AddonDomain), `cpanel_upload_file()` (UAPI Fileman), `cpanel_extract_file()` and `cpanel_delete_file()` (API2 Fileman::fileop)
- **Bot Handlers** — `handle_message()` routes text input, `handle_callback()` routes inline button presses, `handle_document()` processes zip uploads
- **Buy Flow** — `pending_buy` dict: ask domain → check availability → show price → purchase. Supports multi-account picker
- **Email Flow** — `pending_email` dict: multi-step state machine (username → name → admin → password → notify email → browser launch → expiration (auto-skipped if single date) → confirm → submit). Password messages auto-deleted for security
- **Website Flow** — `pending_website_domain` dict: pick cPanel account → create domain → wait for zip → upload → extract → delete zip
- **Generate Flow** — `pending_generate` dict: collect company info step by step → generate HTML zip + Indeed HTML file → send both to Telegram
- **Browser Management** — `active_browser` dict: keeps browser open after email creation; reused on next `/email` if same account. `/close` command closes it
- **Main Loop** — `run()` flushes stale updates on startup, sends startup message, then polls Telegram

### Telegram bot commands

| Command | Action |
|---------|--------|
| `/buy` | Check domain availability + purchase |
| `/setup` | Add domain to cPanel + deploy website zip |
| `/email` | Create M365 email via browser automation |
| `/generate` | Generate website HTML + Indeed job description |
| `/close` | Close the browser |
| `/cancel` | Abort any active flow (closes browser if open) |
| `/start` | Show help |

All commands work standalone (bot asks for input) or with an argument (e.g. `/buy mysite.com`).

### email_automation.py

`GoDaddyEmailBot` class drives GoDaddy's Email & Office web UI following the real manual flow:
1. `open()` — launches real Chrome with per-account persistent profile (`browser_data/account_N/`)
2. `go_to_create_email(domain)` — follows manual flow: Overview → Set up accounts → Get Started (M365) → enter domain → Continue → Create single email tab. Retries navigation up to 3 times if interrupted by GoDaddy redirects. Handles SSO login if session expired
3. `get_expiration_dates()` — opens the dropdown (if it exists) and uses JS to read all options regardless of scroll/visibility. If only 1 date found, sets `_single_expiration = True` so `fill_form()` skips it. If no dropdown, reads static text
4. `fill_form()` — fills all form fields. Selects "Do not share" for Link domains via JS click (dropdown has its own scroller). Skips expiration dropdown if `_single_expiration`
5. `submit()` — clicks Create, then polls up to 20 seconds for a "No, thank you" phone notification offer and dismisses it, then navigates back to Overview
6. `close()` — cleans up browser resources

**`_dismiss_popups()`** handles: "Create an email account" modal (clicks Cancel with `force=True`), generic modal close buttons, recommendation overlays. Runs up to 3 rounds.

### website_generator.py

**Block-based generation** (`generate_website_from_blocks`) — the primary function called by `/generate`:
- Randomly picks one variant from each section pool: 5 hero × 5 process × 5 about × 5 careers × 4 contact = 2,500 layout combinations
- Combined with 10 color schemes × 12 font pairs = **300,000+ unique combinations**
- All CSS inline, responsive, scroll animations, hamburger menu
- All section blocks use CSS variables so color scheme fully controls the look
- Careers blocks always use `<div class="perk">TEXT</div>` for benefit items — consistent across all variants
- `generate_website(info)` — original scratch-built generator kept as reference/fallback (not called by bot)

**`generate_job_description(info)`** — outputs HTML fragments (not markdown) for pasting directly into Indeed's rich text editor:
- Randomly picks tone: `direct`, `professional`, or `conversational`
- Randomly shuffles section order (intro always first, EEO always last)
- 30 intro paragraph variations, 3 tone-matched duties/requirements pools
- Pay section presented 3 different ways
- Schedule section presented 3 different ways
- Randomly includes 0–2 optional sections: "Why Drivers Stay", "About {company}", "Apply Today" CTA
- 5 EEO statement variations
- Output is `<p>`, `<b>`, `<ul>/<li>`, `<i>` tags — paste into Indeed editor and it renders formatted

## Notification Email

The "Send account info to" field during `/email` flow shows two hardcoded buttons: `smfleet02@gmail.com` and `phillhr57@gmail.com`. User can also type a custom email. To change these, edit the `_handle_email_input` function in `main.py` where `step == "awaiting_password"`.

## Logging

Logger name: `automation`. INFO to console (stdout), DEBUG to `logs/automation.log`. Debug screenshots from browser automation failures are saved as `logs/debug_*.png`.

## Supporting Directories

- `assets/stock_images/` — stock photos (`hero_*.jpg`, `about_*.jpg`, `coverage_*.jpg`) bundled into generated websites
- `flow/` — reference screenshots documenting the GoDaddy Email & Office manual flow (not used by code)
- `browser_data/account_N/` — persistent Chrome profiles for each GoDaddy login account

## Configuration

All config loaded from `.env` via custom `_load_env()` (no python-dotenv). Key groups:
- **GoDaddy API**: key/secret, environment (`production`/`ote` sandbox), registrant contact
- **GoDaddy Login**: email/password for browser automation (Email & Office has no API)
- **Telegram**: bot token, authorized chat ID
- **cPanel**: URL, username, API token

### Multi-account support

All account types are numbered with `_1`, `_2`, etc. suffixes in `.env` (up to `_9`):
- **GoDaddy API**: `GODADDY_API_KEY_1`, `GODADDY_API_SECRET_1`, `GODADDY_API_LABEL_1`, plus per-account registrant contact (`REGISTRANT_FIRST_NAME_1`, etc.) → `GODADDY_API_ACCOUNTS` list
- **cPanel**: `CPANEL_URL_1`, `CPANEL_USERNAME_1`, `CPANEL_PASSWORD_1`, `CPANEL_LABEL_1` → `CPANEL_ACCOUNTS` list
- **GoDaddy Login** (browser): `GODADDY_EMAIL_1`, `GODADDY_PASSWORD_1` → `GODADDY_ACCOUNTS` list

Fallback: if no numbered vars found, loads legacy single-var config (e.g. `GODADDY_API_KEY`). Each GoDaddy login account gets its own browser profile (`browser_data/account_1/`, `account_2/`, etc.) so sessions don't conflict. When multiple accounts exist, the bot shows an inline keyboard picker. With a single account, selection is skipped.

## API Gotchas

- GoDaddy contact fields use `nameFirst`/`nameLast` (NOT `firstName`/`lastName`)
- GoDaddy prices are in microdollars (divide by 1,000,000 for USD)
- OTE sandbox requires its own account, API keys, and payment method at sso.ote-godaddy.com
- Auth header format: `sso-key {API_KEY}:{API_SECRET}`
- cPanel extraction uses API2 `Fileman::fileop` with `op=extract` (UAPI `Fileman::extract` does not exist on this server)
- cPanel permanent deletion uses API2 `Fileman::fileop` with `op=unlink` (skips trash)
- cPanel addon domains require `rootdomain` from `DomainInfo::list_domains`

## GoDaddy Email & Office UI Quirks

- Bot follows the real manual flow (Overview → Set up accounts → M365 → domain → single email tab) to avoid suspicious direct URL navigation
- GoDaddy detects Playwright's bundled Chromium — must use `channel="chrome"` with real Chrome
- **Never use `wait_for_load_state("networkidle")`** — GoDaddy's SPA never stops making network requests. Use `"domcontentloaded"` + `wait_for_timeout()` instead
- Initial `page.goto()` in `go_to_create_email()` retries up to 3 times — GoDaddy sometimes redirects mid-navigation which causes Playwright to throw a navigation conflict error
- "Link domains" dropdown has its own internal scroller — selecting "Do not share" must be done via JS (`document.querySelectorAll` + `.click()`) not Playwright locators
- After clicking Create, bot polls 20 seconds for a phone number notification offer ("No, thank you") before navigating back to Overview
- If a second `/email` is started while a browser is still open (user chose "Keep Open"), the existing browser is reused if it's the same account — avoids Playwright Sync API conflict from launching two instances
- Expiration date: if only 1 date exists, bot auto-selects it and skips asking the user
- Expiration dropdown options are read via JS (`[name="expirationDateDropDown"]`) after a 5-second wait — reads all DOM items regardless of scroll position
- `_dismiss_popups()` runs up to 3 rounds and handles: "Create an email account" modal, generic close/X buttons, Cancel links

## Notes

- No tests or linting configured — this is a single-user automation tool
- CLAUDE.md is gitignored (local-only, not committed to the repo)
- `.env` is loaded by a custom `_load_env()` function (no python-dotenv dependency)
- All three source files are standalone scripts with no shared base classes or utility modules
