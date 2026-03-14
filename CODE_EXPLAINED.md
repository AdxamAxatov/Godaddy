# Code Explained — Architecture Overview

A guide explaining how the codebase works, what each file does, and key concepts.

---

## File Structure

```
src/
  main.py               — The brain: Telegram bot + all API integrations + flow logic
  email_automation.py   — Browser automation for GoDaddy Email & Office
  website_generator.py  — HTML website + job description generator
```

---

## 1. main.py — The Bot

### How it starts

```python
_load_env()          # Reads .env file into os.environ
log = setup_logging() # Sets up console + file logging
run()                # Starts the Telegram polling loop
```

`run()` does three things on startup:
1. Registers bot commands with Telegram (so they show in the menu)
2. Flushes stale updates from when the bot was offline
3. Sends a "Bot is online!" message, then enters the infinite polling loop

### The polling loop

```python
while True:
    updates = tg_get_updates(offset)  # Wait up to 30s for new messages
    for update in updates:
        offset = update["update_id"] + 1  # Mark as processed
        # Route to handle_message(), handle_callback(), or handle_document()
```

Long-polling: the bot asks Telegram "anything new?", waits 30 seconds. If a message arrives, it returns immediately. If not, empty response, ask again.

### State machines

Each flow uses a dict to track what step the user is on:

| Dict | Flow | Purpose |
|------|------|---------|
| `pending_buy` | `/buy` | Awaiting domain input |
| `pending_website_domain` | `/setup` | Awaiting domain, account selection, or zip upload |
| `pending_email` | `/email` | Multi-step: username → name → admin → password → notify → browser → expiration → confirm |
| `pending_generate` | `/generate` | Multi-step: company info collection → generation |
| `active_browser` | `/close` | Holds browser instances that outlive the email flow |

### Multi-account support

cPanel and GoDaddy accounts are loaded from numbered `.env` vars (`_1`, `_2`, ...) into lists:
- `CPANEL_ACCOUNTS` — list of `{url, username, password, label}` dicts
- `GODADDY_ACCOUNTS` — list of `{email, password}` dicts

When multiple accounts exist, the bot shows inline keyboard buttons to pick one.

### Telegram API helpers

All Telegram communication goes through thin wrapper functions:
- `tg_send()` — send text message (with optional inline keyboard buttons)
- `tg_edit_message()` — update an existing message
- `tg_answer_callback()` — acknowledge a button press (removes loading spinner)
- `tg_send_photo()` — send an image
- `tg_send_document()` — send a file (zip)
- `tg_delete_message()` — delete a message (used for password security)
- `tg_get_updates()` — long-poll for new messages

---

## 2. email_automation.py — Browser Automation

### GoDaddyEmailBot class

Drives GoDaddy's Email & Office web UI using Playwright + real Chrome.

**Per-account browser profiles:** Each GoDaddy account gets its own persistent profile folder (`browser_data/account_1/`, `account_2/`, etc.). This means:
- Sessions/cookies persist across restarts
- Different accounts don't interfere with each other
- You can have Chrome open for personal use simultaneously

**The manual flow (what `go_to_create_email` does):**
1. Navigate to Overview (`productivity.godaddy.com/#/`)
2. Click "Set up accounts"
3. Click "Get Started" under Microsoft 365 Email
4. Type the domain, click Continue
5. Click "Create single email" tab
6. Form is now visible

**Why follow the manual flow?** Navigating directly via URL caused suspicious behavior — extra dropdowns appeared, DNS setup wizards popped up. Following the real manual flow avoids all of that.

**SSO login handling:** `_ensure_logged_in()` checks if the page redirected to SSO. If yes, `_do_sso_login()` fills username → password → waits for redirect. If cookies are valid, login is skipped entirely.

**Key quirks handled:**
- `_dismiss_popups()` — GoDaddy randomly shows recommendation modals
- Single expiration date = no dropdown, just static text (handled specially)
- Never use `networkidle` — GoDaddy's SPA never stops making requests

---

## 3. website_generator.py — Website Generation

### How it works

`generate_website(info)` takes a dict of company info and produces a zip file:

1. **Randomize style** — picks from 10 color schemes, 12 font pairs, multiple content variations
2. **Build HTML** — single `index.html` with all CSS inline, using f-string templating
3. **Create placeholders** — SVG placeholder images in `images/` folder
4. **Zip it** — packages into a downloadable zip file

`generate_job_description(info)` produces an Indeed-ready markdown job posting with randomized section titles.

### Website sections (always the same structure, different content/style)

- **Nav** — fixed header with logo, links, hamburger menu on mobile
- **Hero** — full-screen background image, tagline, CTA buttons, stat counters
- **How We Work** — 3-step process cards
- **About / Coverage** — two split-row sections with images and checklists
- **Careers** — job title, pay, 4 highlight cards, perks list, EEO statement
- **Contact** — info column + quote form
- **Footer** — logo, links, copyright

### Variation pools

| Element | Options |
|---------|---------|
| Color schemes | 10 (navy-blue, emerald-gold, slate-red, charcoal-amber, deep-teal, etc.) |
| Font pairs | 12 (Titillium Web + Source Sans, Rajdhani + Inter, Outfit + DM Sans, etc.) |
| Hero taglines | 10 variations |
| How We Work steps | 4 different sets |
| About/Coverage titles | 6 + 5 variations |
| Job description section titles | 6 different style sets |

---

## Key Concepts

| Concept | Where | What It Means |
|---------|-------|---------------|
| **Long-polling** | `tg_get_updates()` | Keep asking Telegram "anything new?" in a loop |
| **Inline keyboard** | `reply_markup` | Clickable buttons inside Telegram messages |
| **Callback data** | `buy:domain.com` | Hidden data sent back when a button is tapped |
| **State machine** | `pending_*` dicts | Track which step of a multi-step flow the user is on |
| **Persistent context** | Playwright | Browser profile that survives restarts (cookies, sessions) |
| **f-string templating** | `website_generator.py` | Python string interpolation to build HTML from data |
| **Microdollars** | GoDaddy API | Prices returned as integers (12990000 = $12.99) |
| **SSO** | GoDaddy login | Single Sign-On — one login page for all GoDaddy services |
