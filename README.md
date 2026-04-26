# Tech Pulse News

An AI-powered tech news aggregator that scrapes RSS feeds and websites, categorizes articles with a local LLM, and delivers scheduled briefings to Telegram.

## Features

- Scrapes tech news from RSS feeds and web pages (Playwright + BeautifulSoup4)
- Categorizes articles using a local LLM via LM Studio (OpenAI-compatible API)
- Sends formatted briefings to a Telegram channel or chat
- Full briefings at 8:00 AM and 8:00 PM (configurable timezone)
- Hourly alert scans for breaking news
- GUI dashboard (customtkinter) with system tray icon
- Telegram bot listener for on-demand commands
- One-shot Windows installer with startup shortcut

## Requirements

- Windows 10/11
- Python 3.11+
- [LM Studio](https://lmstudio.ai) with a loaded model (default: `phi-3.5-mini-instruct`)
- A Telegram bot token and chat ID

## Installation

```powershell
.\install.ps1
```

This will:
1. Create a virtual environment and install all dependencies
2. Install Playwright Chromium browser binaries
3. Create `.env` from `.env.example`
4. Add a startup shortcut to your Windows Startup folder

## Configuration

Edit `.env` after running the installer:

```env
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
LM_STUDIO_HOST=http://localhost:1234
LM_STUDIO_MODEL=phi-3.5-mini-instruct
SCHEDULE_TZ=Asia/Kuala_Lumpur
```

## Usage

1. Open LM Studio, load your model, and start the local server
2. Launch the app:

```powershell
.\venv\Scripts\pythonw.exe app.py
```

The GUI dashboard shows:
- LM Studio and bot connection status
- Next scheduled briefing and alert scan times
- Live activity log
- Buttons to trigger a full briefing or alert scan manually

Closing the window minimizes to the system tray. Right-click the tray icon to show or exit.

## Project Structure

```
app.py            # Entry point
gui.py            # Dashboard window and tray icon
runner.py         # Orchestrates scrape → categorize → send pipeline
scraper.py        # RSS + Playwright web scraping
categorizer.py    # LM Studio categorization via OpenAI-compatible API
formatter.py      # Formats articles for Telegram
sender.py         # Telegram message delivery
bot_listener.py   # Telegram bot command handler (subprocess)
scheduler.py      # Cron-style scheduler (8 AM/PM full, hourly alert)
state.py          # Deduplication state
config.py         # Env var loading and validation
logger.py         # Logging setup
install.ps1       # One-shot Windows installer
```

## Running Tests

```powershell
./Tech-Pulse-News
venv/Scripts/python.exe app.py
```
