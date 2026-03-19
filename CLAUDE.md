# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot that automates GoDaddy operations: domain purchases (browser automation), website generation & deployment (cPanel API), M365 email account creation (browser automation), AutoSSL, and domain removal. All interaction happens through Telegram — no CLI interaction.

## Critical Rules

- **Never use `wait_for_load_state("networkidle")`** — GoDaddy's SPA never stops making network requests. Use `"domcontentloaded"` + `wait_for_timeout()` instead
- **Never close browser on errors** — keep it open via `active_browser[chat_id]` so user can see what went wrong and use `/close` when done
- **Always use `channel="chrome"`** — GoDaddy detects Playwright's bundled Chromium and blocks it
- **Never read or expose `.env`** — contains credentials. Use `_load_env()` to access config values in code

## Running

```bash
source .venv/Scripts/activate   # Windows Git Bash
python src/main.py              # Starts Telegram long-polling loop
```

## Dependencies

Python 3.12, managed via a local `.venv`. Key packages: `requests`, `playwright`. No `requirements.txt` — install with `pip install requests playwright`. Browser automation uses the system's real Chrome (`channel="chrome"`), not Playwright's bundled Chromium, to avoid GoDaddy's bot detection.

## Architecture

Four files in `src/`:

- **`src/main.py`** — Telegram bot, GoDaddy API (legacy, kept as fallback), cPanel API, and all bot flow logic (state machines for buy, setup, email, generate, autossl, remove_domain)
- **`src/email_automation.py`** — `GoDaddyEmailBot` class: Playwright browser automation for GoDaddy Email & Office email creation
- **`src/domain_automation.py`** — `GoDaddyDomainBot` class: Playwright browser automation for GoDaddy domain purchasing
- **`src/website_generator.py`** — Block-based website HTML generator + Indeed job description generator for trucking companies

### State machine pattern

Each bot flow uses a `pending_*` dict keyed by `chat_id` to track multi-step conversations. The dict stores a `step` field that advances through the flow. `handle_message()` checks these dicts to route user input to the correct flow handler, and `handle_callback()` routes inline button presses. `/cancel` clears all pending dicts for the chat.

### main.py sections

- **Telegram Bot** — `tg_send()`, `tg_edit_message()`, `tg_answer_callback()`, `tg_get_updates()`, `tg_send_photo()`, `tg_send_document()`, `tg_delete_message()` for raw Telegram API calls
- **GoDaddy API** (legacy fallback) — `check_domain_availability()`, `purchase_domain()` — kept in code but not actively used since API keys are unavailable. Domain purchasing now uses browser automation
- **cPanel API** — `cpanel_create_domain()` (API2 AddonDomain), `cpanel_remove_domain()` (API2 AddonDomain::deladdondomain), `cpanel_upload_file()` (UAPI Fileman), `cpanel_extract_file()` and `cpanel_delete_file()` (API2 Fileman::fileop), `cpanel_run_autossl()` (UAPI SSL::start_autossl_check)
- **Bot Handlers** — `handle_message()` routes text input, `handle_callback()` routes inline button presses, `handle_document()` processes zip uploads
- **Buy Flow** — `pending_buy` dict: company name → Indeed check (optional, skippable) → domain → browser automation: search → show price → confirm → cart → extras → checkout. Stops at CVV entry page (not yet implemented)
- **Email Flow** — `pending_email` dict: multi-step state machine (username → name → admin → password → notify email → browser launch → expiration (auto-skipped if single date) → confirm → submit). Password messages auto-deleted for security
- **Website Flow** — `pending_website_domain` dict: pick cPanel account → create domain → wait for zip → upload → extract → delete zip
- **Generate Flow** — `pending_generate` dict: collect company info step by step → generate HTML zip + Indeed HTML file → send both to Telegram
- **AutoSSL Flow** — `pending_autossl` dict: domain → pick cPanel account → trigger AutoSSL via API
- **Remove Domain Flow** — `pending_remove_domain` dict: domain → pick cPanel account → verify domain exists → confirm → remove via API
- **Browser Management** — `active_browser` dict: keeps browser open after email creation, domain purchase errors, or checkout. Reused on next `/email` if same account. `/close` command closes it. **Never close browser on errors** — always keep open for user inspection
- **Main Loop** — `run()` flushes stale updates on startup, then polls Telegram

### Telegram bot commands

| Command | Action |
|---------|--------|
| `/buy` | Purchase a domain (browser automation) |
| `/setup` | Add domain to cPanel + deploy website zip |
| `/email` | Create M365 email via browser automation |
| `/generate` | Generate website HTML + Indeed job description |
| `/run_autossl` | Trigger AutoSSL for a domain (cPanel API) |
| `/remove_domain` | Remove a domain from cPanel hosting |
| `/close` | Close the browser |
| `/cancel` | Abort any active flow |
| `/start` | Show help |

All commands work standalone (bot asks for input) or with an argument (e.g. `/setup mysite.com`).

### domain_automation.py

`GoDaddyDomainBot` class drives GoDaddy's domain purchase flow via browser:
1. `open()` — launches real Chrome with per-account persistent profile, dismisses Chrome "Restore pages?" popup, accepts cookies
2. `search_domain(domain)` — navigates to `account.godaddy.com/products`, types domain in search box, checks availability. Returns `{available, price}`. Handles SSO login, retries on "upstream request timeout"
3. `select_term_and_add()` — selects 1 Year Term via JS click on card container, clicks buy button. **Buy button text varies by account** (A/B testing): "Make It Yours", "Get It", "Add to Cart" — all handled
4. `go_to_cart()` — clicks "View Cart" or "Continue to Cart" from bottom bar
5. `skip_extras()` — selects "No Domain Protection", "No Thanks" (email), clicks "Continue to Cart"
6. `prepare_checkout()` — ensures protection toggles are OFF, term is 1 Year, clicks "Ready for Checkout"
7. Flow stops at checkout page — CVV entry not yet implemented
8. `close()` — cleans up browser resources

### email_automation.py

`GoDaddyEmailBot` class drives GoDaddy's Email & Office web UI following the real manual flow:
1. `open()` — launches real Chrome with per-account persistent profile (`browser_data/account_N/`), accepts cookies
2. `go_to_create_email(domain)` — follows manual flow: Overview → Set up accounts → Get Started (M365) → enter domain → Continue → Create single email tab. Retries navigation up to 3 times if interrupted by GoDaddy redirects. Handles SSO login if session expired
3. `get_expiration_dates()` — opens the dropdown (if it exists) and uses JS to read all options regardless of scroll/visibility. If only 1 date found, sets `_single_expiration = True` so `fill_form()` skips it. If no dropdown, reads static text
4. `fill_form()` — fills all form fields. Selects "Do not share" for Link domains via JS click (dropdown has its own scroller). Skips expiration dropdown if `_single_expiration`
5. `submit()` — clicks Create, then polls up to 25 seconds for a "No, Thanks" phone notification offer and dismisses it, then navigates back to Overview
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
- `flow/` — reference screenshots documenting GoDaddy manual flows (email, domain purchase, SSL, domain removal). Not used by code
- `browser_data/account_N/` — persistent Chrome profiles for each GoDaddy login account

## Configuration

All config loaded from `.env` via custom `_load_env()` (no python-dotenv). Key groups:
- **GoDaddy API** (legacy): key/secret, environment (`production`/`ote` sandbox), registrant contact
- **GoDaddy Login**: email/password for browser automation (Email & Office and domain purchase have no API)
- **Telegram**: bot token, authorized chat ID
- **cPanel**: URL, username, API token

### Multi-account support

All account types are numbered with `_1`, `_2`, etc. suffixes in `.env` (up to `_9`):
- **GoDaddy API** (legacy): `GODADDY_API_KEY_1`, `GODADDY_API_SECRET_1`, `GODADDY_API_LABEL_1`, plus per-account registrant contact (`REGISTRANT_FIRST_NAME_1`, etc.) → `GODADDY_API_ACCOUNTS` list
- **cPanel**: `CPANEL_URL_1`, `CPANEL_USERNAME_1`, `CPANEL_PASSWORD_1`, `CPANEL_LABEL_1` → `CPANEL_ACCOUNTS` list
- **GoDaddy Login** (browser): `GODADDY_EMAIL_1`, `GODADDY_PASSWORD_1` → `GODADDY_ACCOUNTS` list (no `label` field — uses `email` for display)

Fallback: if no numbered vars found, loads legacy single-var config (e.g. `GODADDY_API_KEY`). Each GoDaddy login account gets its own browser profile (`browser_data/account_1/`, `account_2/`, etc.) so sessions don't conflict. When multiple accounts exist, the bot shows an inline keyboard picker. With a single account, selection is skipped.

## API Gotchas

- GoDaddy contact fields use `nameFirst`/`nameLast` (NOT `firstName`/`lastName`)
- GoDaddy prices are in microdollars (divide by 1,000,000 for USD)
- OTE sandbox requires its own account, API keys, and payment method at sso.ote-godaddy.com
- Auth header format: `sso-key {API_KEY}:{API_SECRET}`
- cPanel extraction uses API2 `Fileman::fileop` with `op=extract` (UAPI `Fileman::extract` does not exist on this server)
- cPanel permanent deletion uses API2 `Fileman::fileop` with `op=unlink` (skips trash)
- cPanel addon domains require `rootdomain` from `DomainInfo::list_domains`
- cPanel `deladdondomain` requires the `subdomain` parameter — must be looked up via `AddonDomain::listaddondomains` using `fullsubdomain` field (cPanel assigns these inconsistently, cannot be derived from domain name)

## Browser Automation Quirks

### General (applies to both email and domain bots)
- GoDaddy detects Playwright's bundled Chromium — must use `channel="chrome"` with real Chrome
- **Never use `wait_for_load_state("networkidle")`** — GoDaddy's SPA never stops making network requests. Use `"domcontentloaded"` + `wait_for_timeout()` instead
- Cookie consent must be accepted for session cookies to persist in browser profiles. `_accept_cookies()` runs after launch but needs a page loaded first. Some accounts may need manual acceptance on first run
- **Never close browser on errors** — keep it open via `active_browser[chat_id]` so user can see what went wrong and use `/close` when done
- Both bot classes share the same persistent profiles in `browser_data/account_N/` — only one browser instance per account can run at a time

### GoDaddy Email & Office UI
- Bot follows the real manual flow (Overview → Set up accounts → M365 → domain → single email tab) to avoid suspicious direct URL navigation
- Initial `page.goto()` in `go_to_create_email()` retries up to 3 times — GoDaddy sometimes redirects mid-navigation which causes Playwright to throw a navigation conflict error
- "Link domains" dropdown has its own internal scroller — selecting "Do not share" must be done via JS (`document.querySelectorAll` + `.click()`) not Playwright locators
- After clicking Create, bot polls 25 seconds for a phone number notification offer ("No, Thanks") before navigating back to Overview
- If a second `/email` is started while a browser is still open (user chose "Keep Open"), the existing browser is reused if it's the same account — avoids Playwright Sync API conflict from launching two instances
- Expiration date: if only 1 date exists, bot auto-selects it and skips asking the user
- Expiration dropdown options are read via JS (`[name="expirationDateDropDown"]`) after a 5-second wait — reads all DOM items regardless of scroll position
- `_dismiss_popups()` runs up to 3 rounds and handles: "Create an email account" modal, generic close/X buttons, Cancel links

### GoDaddy Domain Purchase UI
- Domain search starts from `account.godaddy.com/products` — uses the dashboard search box, not direct URL navigation
- Buy button text varies by account (GoDaddy A/B testing): "Make It Yours", "Get It", "Add to Cart" — code handles all variations
- 1 Year Term must be selected via JS clicking the card container, not just the text label
- Products page can return "upstream request timeout" — bot retries up to 3 times
- Chrome "Restore pages?" popup appears after unclean shutdown — bot dismisses it on launch
- Purchase flow stops at checkout page (CVV entry not yet implemented)

## Notes

- No tests or linting configured — this is a single-user automation tool
- CLAUDE.md is gitignored (local-only, not committed to the repo)
- `.env` is loaded by a custom `_load_env()` function (no python-dotenv dependency)
- All four source files are standalone scripts with no shared base classes or utility modules
- GoDaddy API functions for domain purchase are kept in code as fallback but not currently used (API keys unavailable)
