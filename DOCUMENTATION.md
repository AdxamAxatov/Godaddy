# GoDaddy Domain + Website + Email Automation

Telegram bot that automates the full domain lifecycle — purchase a domain on GoDaddy, generate and deploy a website via cPanel, and create M365 email accounts via browser automation — all from Telegram.

## Bot Commands

| Command | What it does |
|---------|-------------|
| `/buy` | Check domain availability and purchase |
| `/setup` | Add domain to cPanel hosting and deploy a website |
| `/email` | Create an M365 email account via browser automation |
| `/generate` | Generate a website + Indeed job description |
| `/close` | Close the browser (after email creation) |
| `/cancel` | Cancel any active flow and close browser if open |
| `/start` | Show help message |

All commands work standalone (bot asks for input) or with an argument (e.g. `/buy mysite.com`).

## Flows

### Flow 1: Domain Purchase (`/buy`)

```
You (Telegram)                Bot                          GoDaddy API
     |                         |                              |
     |  /buy                   |                              |
     |------------------------>|  "What domain?"              |
     |  mysite.com             |                              |
     |------------------------>|  GET /v1/domains/available   |
     |                         |----------------------------->|
     |                         |         available + price    |
     |                         |<-----------------------------|
     |  "$12.99/yr"            |                              |
     |  [Buy] [Cancel]         |                              |
     |<------------------------|                              |
     |                         |                              |
     |  Tap "Buy"              |                              |
     |------------------------>|  POST /v1/domains/purchase   |
     |                         |----------------------------->|
     |                         |              order confirmed |
     |                         |<-----------------------------|
     |  "Purchased!"           |                              |
     |  [Setup Website] [Skip] |                              |
     |<------------------------|                              |
```

1. Send `/buy` — bot asks for the domain
2. Type domain (e.g. `mysite.com`) — bot checks availability and shows price
3. Tap Buy — bot purchases the domain, shows order ID
4. Bot asks if you want to set up a website for this domain

### Flow 2: Website Generation (`/generate`)

```
/generate
  → Company name?           (e.g. "2-3 Logistics Corp")
  → Short name for logo?    (e.g. "2-3 Logistics")
  → Domain?                 (e.g. "2-3logisticscorp.com")
  → Contact email?
  → Street address?
  → City, State, Zip?
  → Job title?
  → Pay range?
  → Home time?
  → Home time short?
  → Home time detail?
  → Min experience?
  → Perks (one per line, send "done" when finished)
  → Bot generates and sends the .zip + Indeed job description
```

The generator:
- Picks a random color scheme (10 options) and font pair (12 options) each time
- Randomizes hero taglines, section content, and layout variations
- Produces a single `index.html` with all CSS inline + placeholder images
- Also generates an Indeed-ready job description with unique section titles
- Sends both the zip file and job description text directly in Telegram

### Flow 3: Website Deployment (`/setup`)

```
You (Telegram)                Bot                          cPanel API
     |                         |                              |
     |  /setup                 |                              |
     |------------------------>|  "What domain?"              |
     |  mysite.com             |                              |
     |------------------------>|  AddonDomain::addaddondomain |
     |                         |----------------------------->|
     |                         |                  domain added|
     |                         |<-----------------------------|
     |  "Send me the .zip"     |                              |
     |<------------------------|                              |
     |                         |                              |
     |  website.zip            |                              |
     |------------------------>|  Fileman::upload_files       |
     |                         |----------------------------->|
     |                         |  Fileman::fileop (extract)   |
     |                         |----------------------------->|
     |                         |                    extracted |
     |                         |<-----------------------------|
     |  "Website deployed!"    |                              |
     |<------------------------|                              |
```

1. Send `/setup` — bot asks for the domain
2. If multiple cPanel accounts, bot shows a picker (displays account label)
3. Bot adds the domain to cPanel hosting (skips if already exists)
4. Send a `.zip` file with your website (HTML, CSS, images)
5. Bot uploads, extracts, and deletes the zip — site is live

### Flow 4: Email Account Creation (`/email`)

This is a multi-step state machine that uses Playwright browser automation to drive GoDaddy's Email & Office web UI (there is no API for this).

```
/email
  |
  v
[1] Pick GoDaddy account       (button, if multiple accounts)
  |
  v
[2] Enter username              (e.g. "info" for info@domain.com)
  |
  v
[3] Enter first and last name   (e.g. "John Doe")
  |
  v
[4] Admin permissions?          (Yes / No button)
  |
  v
[5] Enter password              (message auto-deleted for security)
  |
  v
[6] Notification email          (button for default, or type custom)
  |
  v
[7] BROWSER LAUNCHES            (Chrome opens, logs in if needed, follows manual flow)
       |
       |  Step 1: Overview page -> click "Set up accounts"
       |  Step 2: Choose account type -> click "Get Started" (Microsoft 365)
       |  Step 3: Enter domain -> click Continue
       |  Step 4: Click "Create single email" tab
       |
  v
[8] Pick expiration date        (buttons scraped from the page)
  |
  v
[9] Bot fills form + screenshot (sent to Telegram for review)
  |
  v
[10] Confirm?                   (Create / Cancel button)
  |
  v
[11] SUBMITTED                  (bot clicks Create, navigates back to Overview)
  |
  v
[12] Close browser?             (Close / Keep Open button, or /close later)
```

After email creation, the browser stays open until you choose to close it. You can close it at any time with `/close`. Each GoDaddy account gets its own browser profile so sessions don't conflict.

## Setup

### Prerequisites

- Python 3.12+
- Google Chrome installed (browser automation uses real Chrome, not Playwright's Chromium)
- GoDaddy account with payment method on file
- GoDaddy API keys from [developer.godaddy.com/keys](https://developer.godaddy.com/keys)
- Telegram bot (create via [@BotFather](https://t.me/BotFather))
- cPanel hosting account (for website deployment)

### Installation

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install requests playwright
playwright install chromium
```

### Configuration

All credentials live in `.env`. Multiple cPanel and GoDaddy login accounts are supported with numbered suffixes (`_1`, `_2`, ... up to `_9`).

```env
# GoDaddy API
GODADDY_API_KEY=your_key_here
GODADDY_API_SECRET=your_secret_here
GODADDY_ENV=ote                     # "ote" for sandbox, "production" for real purchases

# Registrant Contact (WHOIS info)
REGISTRANT_FIRST_NAME=Jane
REGISTRANT_LAST_NAME=Doe
REGISTRANT_EMAIL=jane@gmail.com
REGISTRANT_PHONE=+1.5555550100
REGISTRANT_ADDRESS=123 Main St
REGISTRANT_CITY=Phoenix
REGISTRANT_STATE=AZ
REGISTRANT_POSTAL_CODE=85001
REGISTRANT_COUNTRY=US

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# cPanel Hosting Accounts (numbered _1, _2, etc.)
CPANEL_URL_1=https://your-server.secureserver.net:2083
CPANEL_USERNAME_1=your_cpanel_username
CPANEL_PASSWORD_1=your_cpanel_api_token
CPANEL_LABEL_1=your_account_label

# GoDaddy Login Accounts for browser automation (numbered _1, _2, etc.)
GODADDY_EMAIL_1=your_godaddy_email
GODADDY_PASSWORD_1=your_godaddy_password
```

### Running

```bash
source .venv/Scripts/activate
python src/main.py
```

Bot sends a startup message to Telegram when ready, then polls for commands.

## Testing (Sandbox)

Set `GODADDY_ENV=ote` to use GoDaddy's sandbox — no real charges. Requires separate OTE API keys from [developer.ote-godaddy.com](https://developer.ote-godaddy.com/keys) and a payment method on the OTE account.

Switch to `GODADDY_ENV=production` with production API keys when ready to go live.

## Project Structure

```
src/
  main.py               — Telegram bot, GoDaddy API, cPanel API, all flow logic
  email_automation.py   — GoDaddyEmailBot class (Playwright browser automation)
  website_generator.py  — Website HTML + job description generator
.env                    — Credentials (not committed)
browser_data/           — Per-account Chrome profiles (session cookies)
  account_1/            — Profile for GoDaddy account 1
  account_2/            — Profile for GoDaddy account 2
  ...
logs/                   — Log file and debug screenshots
  automation.log        — Runtime log (INFO to console, DEBUG to file)
  debug_*.png           — Screenshots captured on automation failures
```

## Security

- Only the Telegram chat ID configured in `.env` can interact with the bot — all other messages are ignored
- Password messages are automatically deleted from Telegram chat after being read
- Each GoDaddy account uses a separate persistent browser profile (`browser_data/account_N/`) — sessions survive restarts without conflicting

## APIs Used

| Service | Endpoint | Purpose |
|---------|----------|---------|
| GoDaddy | `GET /v1/domains/available` | Check domain availability |
| GoDaddy | `POST /v1/domains/purchase` | Purchase domain |
| GoDaddy | Email & Office web UI (Playwright) | Create M365 email accounts |
| cPanel API2 | `AddonDomain::addaddondomain` | Add domain to hosting |
| cPanel UAPI | `Fileman::upload_files` | Upload zip to server |
| cPanel API2 | `Fileman::fileop` (extract/unlink) | Extract zip / delete zip on server |
| Telegram | Bot API (long-polling) | All user interaction |
