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
- **`src/website_generator.py`** — Website HTML generator + Indeed job description generator for trucking companies

### main.py sections

- **Telegram Bot** — `tg_send()`, `tg_edit_message()`, `tg_answer_callback()`, `tg_get_updates()`, `tg_send_photo()`, `tg_send_document()`, `tg_delete_message()` for raw Telegram API calls
- **GoDaddy API** — `check_domain_availability()` (GET `/v1/domains/available`), `purchase_domain()` (POST `/v1/domains/purchase`)
- **cPanel API** — `cpanel_create_domain()` (API2 AddonDomain), `cpanel_upload_file()` (UAPI Fileman), `cpanel_extract_file()` and `cpanel_delete_file()` (API2 Fileman::fileop)
- **Bot Handlers** — `handle_message()` routes text input, `handle_callback()` routes inline button presses, `handle_document()` processes zip uploads
- **Buy Flow** — `pending_buy` dict: ask domain → check availability → show price → purchase
- **Email Flow** — `pending_email` dict: multi-step state machine (username → name → admin → password → notify email → browser launch → expiration → confirm → submit). Password messages auto-deleted for security
- **Website Flow** — `pending_website_domain` dict: pick cPanel account → create domain → wait for zip → upload → extract → delete zip
- **Generate Flow** — `pending_generate` dict: collect company info step by step → generate HTML + job description → send zip + text to Telegram
- **Browser Management** — `active_browser` dict: keeps browser open after email creation, `/close` command to close it
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
2. `go_to_create_email(domain)` — follows manual flow: Overview → Set up accounts → Get Started (M365) → enter domain → Continue → Create single email tab. Handles SSO login if session expired
3. `get_expiration_dates()` — scrapes expiration dropdown (handles both dropdown and single-value cases)
4. `fill_form()` — fills all form fields, selects expiration date
5. `submit()` — clicks Create button, navigates back to Overview
6. `close()` — cleans up browser resources

### website_generator.py

Two generation modes:
- `generate_website_from_template(info)` — **primary** (used by `/generate`): picks a random template from `templates/`, does find-and-replace of company name/domain/email/address/city, swaps template images for random stock photos. Falls back to `generate_website()` if no templates exist
- `generate_website(info)` — **fallback**: builds HTML from scratch with f-string templating. Randomizes color scheme (10 options), font pair (12 options), hero taglines, section content
- `generate_job_description(info)` — produces Indeed-ready markdown with randomized section titles
- Template originals are defined in `_TEMPLATE_ORIGINALS` dict (maps template dir name → original company info for replacement)
- Sections: Nav → Hero → How We Work → About/Coverage → Careers (highlights only) → Contact → Footer
- All CSS inline, responsive, scroll animations, hamburger menu

## Logging

Logger name: `automation`. INFO to console (stdout), DEBUG to `logs/automation.log`. Debug screenshots from browser automation failures are saved as `logs/debug_*.png`.

## Supporting Directories

- `assets/stock_images/` — stock photos bundled into generated websites by `website_generator.py`
- `templates/` — real website HTML templates (one folder per template, each with `index.html`). Used by `generate_website_from_template()` for find-and-replace generation
- `flow/` — reference screenshots documenting the GoDaddy Email & Office manual flow (not used by code)
- `Websites/` — example generated website outputs (not used by code)
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
- Recommendation popups/modals can appear — `_dismiss_popups()` handles these
- SSO login is two-step (username then password) with unpredictable redirect timing — `_ensure_logged_in()` checks and handles it
- **Never use `wait_for_load_state("networkidle")`** — GoDaddy's SPA never stops making network requests. Use `"domcontentloaded"` + `wait_for_timeout()` instead
- Per-account persistent profiles (`browser_data/account_N/`) keep sessions alive across restarts
- Browser runs with `headless=False` — GoDaddy's anti-bot detection is more aggressive against headless browsers
- When only one expiration date exists, there's no dropdown — just static text. `get_expiration_dates()` handles both cases

## Notes

- No tests or linting configured — this is a single-user automation tool
- CLAUDE.md is gitignored (local-only, not committed to the repo)
- `.env` is loaded by a custom `_load_env()` function (no python-dotenv dependency)
- All three source files are standalone scripts with no shared base classes or utility modules
