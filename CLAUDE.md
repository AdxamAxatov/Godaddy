# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram bot that automates GoDaddy operations: domain purchases, website deployment (cPanel), and M365 email account creation (Playwright browser automation). All interaction happens through Telegram — no CLI interaction.

## Running

```bash
source .venv/Scripts/activate   # Windows Git Bash
python main.py                  # Starts Telegram long-polling loop
```

## Dependencies

Python 3.12, managed via a local `.venv`. Key packages: `requests`, `playwright`. Browser automation uses the system's real Chrome (`channel="chrome"`), not Playwright's bundled Chromium, to avoid GoDaddy's bot detection.

## Architecture

Two files:

- **`main.py`** (~970 lines) — Telegram bot, GoDaddy API, cPanel API, and all bot flow logic (state machines for website setup and email creation)
- **`email_automation.py`** — `GoDaddyEmailBot` class: Playwright browser automation for GoDaddy Email & Office email creation (login, form fill, submit)

### main.py sections

- **Telegram Bot** — `tg_send()`, `tg_edit_message()`, `tg_answer_callback()`, `tg_get_updates()`, `tg_send_photo()`, `tg_delete_message()` for raw Telegram API calls
- **GoDaddy API** — `check_domain_availability()` (GET `/v1/domains/available`), `purchase_domain()` (POST `/v1/domains/purchase`)
- **cPanel API** — `cpanel_create_domain()` (API2 AddonDomain), `cpanel_upload_file()` (UAPI Fileman), `cpanel_extract_file()` and `cpanel_delete_file()` (API2 Fileman::fileop)
- **Bot Handlers** — `handle_message()` routes text input, `handle_callback()` routes inline button presses, `handle_document()` processes zip uploads
- **Email Flow** — Multi-step state machine in `pending_email` dict: username → name → admin → password → notify email → browser launch → expiration selection → confirmation → submit
- **Website Flow** — `pending_website_domain` dict: create cPanel domain → wait for zip upload → upload → extract → delete zip
- **Main Loop** — `run()` flushes stale updates on startup, sends startup message, then polls Telegram

### email_automation.py

`GoDaddyEmailBot` class drives GoDaddy's Email & Office web UI:
1. `open()` — launches real Chrome with anti-detection flags
2. `login()` — GoDaddy SSO (two-step: username then password, flexible redirect handling)
3. `go_to_create_email(domain)` — navigates to email form URL, clicks "Create single email" tab (page defaults to "Create multiple emails"), dismisses popups
4. `get_expiration_dates()` — scrapes `<select>` dropdown options
5. `fill_form()` — fills all form fields using `get_by_label()` selectors
6. `submit()` — clicks Create button

## Configuration

All config loaded from `.env` via custom `_load_env()` (no python-dotenv). Key groups:
- **GoDaddy API**: key/secret, environment (`production`/`ote` sandbox), registrant contact
- **GoDaddy Login**: email/password for browser automation (Email & Office has no API)
- **Telegram**: bot token, authorized chat ID
- **cPanel**: URL, username, API token

## API Gotchas

- GoDaddy contact fields use `nameFirst`/`nameLast` (NOT `firstName`/`lastName`)
- GoDaddy prices are in microdollars (divide by 1,000,000 for USD)
- OTE sandbox requires its own account, API keys, and payment method at sso.ote-godaddy.com
- Auth header format: `sso-key {API_KEY}:{API_SECRET}`
- cPanel extraction uses API2 `Fileman::fileop` with `op=extract` (UAPI `Fileman::extract` does not exist on this server)
- cPanel permanent deletion uses API2 `Fileman::fileop` with `op=unlink` (skips trash)
- cPanel addon domains require `rootdomain` from `DomainInfo::list_domains`

## GoDaddy Email & Office UI Quirks

- The email creation page defaults to "Create multiple emails" tab — must click "Create single email" tab first
- GoDaddy detects Playwright's bundled Chromium ("Your browser is a bit unusual...") — must use `channel="chrome"` with real Chrome
- Recommendation popups/modals can appear after login or navigation — `_dismiss_popups()` handles these
- SSO login is two-step (username screen, then password screen) with unpredictable redirect timing
