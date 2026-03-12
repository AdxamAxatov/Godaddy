# GoDaddy Domain + Website Automation

Telegram bot that automates the full domain lifecycle — purchase a domain on GoDaddy, deploy a website via cPanel, and (coming soon) set up email — all from your phone.

## How It Works

### Flow 1: Domain Purchase

```
You (Telegram)                Bot                          GoDaddy API
     │                         │                              │
     │  "mysite.com"           │                              │
     │────────────────────────>│  GET /v1/domains/available   │
     │                         │─────────────────────────────>│
     │                         │         available + price    │
     │                         │<─────────────────────────────│
     │  "$12.99/yr"            │                              │
     │  [💰 Buy] [❌ Cancel]   │                              │
     │<────────────────────────│                              │
     │                         │                              │
     │  Tap "Buy"              │                              │
     │────────────────────────>│  POST /v1/domains/purchase   │
     │                         │─────────────────────────────>│
     │                         │              order confirmed │
     │                         │<─────────────────────────────│
     │  "✅ Purchased!"        │                              │
     │  [🌐 Setup] [⏭ Skip]   │                              │
     │<────────────────────────│                              │
```

1. **Send domain** — Type `mysite.com` in Telegram
2. **Availability check** — Bot replies with availability + price
3. **Confirm** — Tap Buy (nothing is charged without your tap)
4. **Purchase** — Bot buys the domain and shows order ID
5. **Website setup prompt** — Bot asks if you want to set up the website now

### Flow 2: Website Deployment

```
You (Telegram)                Bot                          cPanel API
     │                         │                              │
     │  "/setup mysite.com"    │                              │
     │────────────────────────>│  AddonDomain::addaddondomain │
     │                         │─────────────────────────────>│
     │                         │                  domain added│
     │                         │<─────────────────────────────│
     │  "Send me the .zip"     │                              │
     │<────────────────────────│                              │
     │                         │                              │
     │  📎 website.zip         │                              │
     │────────────────────────>│  Fileman::upload_files       │
     │                         │─────────────────────────────>│
     │                         │  Fileman::fileop (extract)   │
     │                         │─────────────────────────────>│
     │                         │                    extracted │
     │                         │<─────────────────────────────│
     │  "✅ Website deployed!" │                              │
     │<────────────────────────│                              │
```

1. **Start setup** — Send `/setup mysite.com` (or tap "Setup Website" after purchase)
2. **Domain added** — Bot adds the domain to cPanel hosting
3. **Send zip** — Bot asks for a `.zip` file with your website (HTML, CSS, images)
4. **Deploy** — Bot uploads the zip to `public_html/mysite.com/` and extracts it
5. **Live** — Website is live at `http://mysite.com`

### Security

Only your Telegram chat ID (configured in `.env`) can interact with the bot. Messages from other users are ignored.

## Setup

### Prerequisites

- Python 3.12+
- GoDaddy account with payment method on file
- GoDaddy API keys from [developer.godaddy.com/keys](https://developer.godaddy.com/keys)
- Telegram bot (create via [@BotFather](https://t.me/BotFather))
- cPanel hosting account (for website deployment)

### Installation

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install requests
```

### Configuration

All credentials live in `.env`:

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

# cPanel (for website deployment)
CPANEL_URL=https://your-server.secureserver.net:2083
CPANEL_USERNAME=your_cpanel_username
CPANEL_PASSWORD=your_cpanel_api_token

# GoDaddy Login (for future browser automation)
GODADDY_EMAIL=your_godaddy_email
GODADDY_PASSWORD=your_godaddy_password
```

### Running

```bash
python main.py
```

Bot starts polling Telegram. Send a domain name or use `/setup domain.com` to get started.

## Bot Commands

| Command | What it does |
|---------|-------------|
| `mysite.com` | Check availability and purchase |
| `/setup mysite.com` | Add domain to hosting and deploy website |
| `/start` | Show help message |

## Testing (Sandbox)

Set `GODADDY_ENV=ote` to use GoDaddy's sandbox — no real charges. Requires separate OTE API keys from [developer.ote-godaddy.com](https://developer.ote-godaddy.com/keys) and a payment method on the OTE account.

Switch to `GODADDY_ENV=production` with production API keys when ready to go live.

## APIs Used

| Service | Endpoint | Purpose |
|---------|----------|---------|
| GoDaddy | `GET /v1/domains/available` | Check domain availability |
| GoDaddy | `POST /v1/domains/purchase` | Purchase domain |
| cPanel API2 | `AddonDomain::addaddondomain` | Add domain to hosting |
| cPanel UAPI | `Fileman::upload_files` | Upload zip to server |
| cPanel API2 | `Fileman::fileop` (extract) | Extract zip on server |
| Telegram | Bot API (long-polling) | All user interaction |

## Planned: Email Automation

Next phase: browser automation (Selenium/Playwright) to create email accounts (e.g. `info@domain.com`) through GoDaddy's Email & Office dashboard, since GoDaddy has no API for email provisioning.
