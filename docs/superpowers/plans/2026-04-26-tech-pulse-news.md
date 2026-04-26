# Tech-Pulse-News Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained Windows desktop app that scrapes tech news, categorises it via a local LM Studio model, sends briefings to Telegram, and auto-starts on Windows login — no cloud APIs, no GitHub Actions, no manual steps after first install.

**Architecture:** A `customtkinter` GUI window (`gui.py`) owns the lifecycle: it spawns a `bot_listener.py` subprocess, drives an internal `Scheduler` (08:00 / 20:00 MYT full briefings + hourly alert scans), and exposes manual run buttons. All heavy work (`runner.py`) runs in daemon threads. A `pystray` tray icon keeps the process alive when the window is minimised. `install.ps1` creates a venv, installs deps, and writes a Windows Startup shortcut so the app launches on every login.

**Tech Stack:** Python 3.11+, customtkinter 5.2+, pystray 0.19+, Pillow 10+, schedule 1.2+, httpx 0.27, feedparser 6, playwright 1.49, python-telegram-bot 21.3, python-dotenv 1.0, pytest 8.2

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `app.py` | Create | Entry point: `os.chdir`, `load_dotenv`, `validate_config`, `MainWindow().mainloop()` |
| `gui.py` | Create | CTk window, tray icon, log queue, status poller, run-lock buttons, bot subprocess |
| `scheduler.py` | Create | `Scheduler` class: converts 08:00/20:00 MYT → local clock, fires callbacks in threads |
| `runner.py` | Create | `run_full()`, `run_alert()`, argparse `__main__` (for bot subprocess calls) |
| `config.py` | Create | Env vars (no Anthropic), `NEWS_SOURCES`, `validate_config()` |
| `logger.py` | Create | `get_logger()` + `add_gui_handler()` + pythonw stdout guard |
| `state.py` | Create | Dedup sent alert URLs in `state.json` |
| `scraper.py` | Create | Concurrent RSS + HTML scraper |
| `formatter.py` | Create | Build Telegram HTML messages |
| `sender.py` | Create | POST to Telegram API via httpx |
| `categorizer.py` | Create | LM Studio `/v1/chat/completions` only — raises on failure |
| `twitter.py` | Create | Playwright + Nitter, Windows Chrome user-agent |
| `bot_listener.py` | Create | Telegram bot: `RUN NEWS` / `RUN ALERT` → subprocess `runner.py` |
| `install.ps1` | Create | venv + deps + playwright + .env copy + Windows Startup shortcut |
| `.env.example` | Create | 5 placeholder lines |
| `requirements.txt` | Create | All pinned deps |
| `tests/conftest.py` | Create | Set env defaults for tests (no Anthropic key) |
| `tests/test_config.py` | Create | `validate_config()` logic |
| `tests/test_categorizer.py` | Create | LM Studio httpx mock, raise on failure |
| `tests/test_runner.py` | Create | `run_full`, `run_alert` patching runner module |
| `tests/test_scheduler.py` | Create | Timezone offset calculation, next_run_times |
| `tests/test_scraper.py` | Create | Feed parsing, freshness filter |
| `tests/test_formatter.py` | Create | Message building, split_message |
| `tests/test_sender.py` | Create | Telegram POST mock |

---

## Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `logs/.gitkeep`

- [ ] **Step 1: Create project directories**

```bash
cd C:/Users/cusma/projects/Tech-Pulse-News
mkdir -p tests logs
```

- [ ] **Step 2: Write `requirements.txt`**

```
feedparser==6.0.11
httpx==0.27.0
beautifulsoup4==4.12.3
playwright==1.49.0
python-telegram-bot==21.3
python-dotenv==1.0.1
customtkinter>=5.2.0
schedule>=1.2.0
pystray>=0.19.5
Pillow>=10.0.0
pytest==8.2.0
pytest-mock==3.14.0
```

- [ ] **Step 3: Write `.env.example`**

```
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
LM_STUDIO_HOST=http://localhost:1234
LM_STUDIO_MODEL=phi-3.5-mini-instruct
SCHEDULE_TZ=Asia/Kuala_Lumpur
```

- [ ] **Step 4: Write `tests/__init__.py`**

Empty file — makes `tests/` a package.

- [ ] **Step 5: Write `tests/conftest.py`**

```python
import os
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")
os.environ.setdefault("TELEGRAM_CHAT_ID", "123456")
os.environ.setdefault("LM_STUDIO_HOST", "http://localhost:1234")
os.environ.setdefault("LM_STUDIO_MODEL", "phi-3.5-mini-instruct")
os.environ.setdefault("SCHEDULE_TZ", "Asia/Kuala_Lumpur")
```

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt .env.example tests/ logs/
git commit -m "feat: project scaffold"
```

---

## Task 2: config.py

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
import os
import importlib


def test_validate_config_warns_on_placeholder_token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "your-telegram-bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456")
    import config
    importlib.reload(config)
    warnings = config.validate_config()
    assert any("TELEGRAM_BOT_TOKEN" in w for w in warnings)


def test_validate_config_warns_on_empty_chat_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "real-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "your-telegram-chat-id")
    import config
    importlib.reload(config)
    warnings = config.validate_config()
    assert any("TELEGRAM_CHAT_ID" in w for w in warnings)


def test_validate_config_returns_empty_when_valid(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "real-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "987654")
    import config
    importlib.reload(config)
    warnings = config.validate_config()
    assert warnings == []
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_config.py -v
```
Expected: `ImportError` or `AttributeError` — `config` module doesn't exist yet.

- [ ] **Step 3: Write `config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
LM_STUDIO_HOST = os.environ.get("LM_STUDIO_HOST", "http://localhost:1234")
LM_STUDIO_MODEL = os.environ.get("LM_STUDIO_MODEL", "phi-3.5-mini-instruct")
SCHEDULE_TZ = os.environ.get("SCHEDULE_TZ", "Asia/Kuala_Lumpur")

NEWS_SOURCES = [
    {"name": "Reuters Technology",    "url": "https://feeds.reuters.com/reuters/technologyNews"},
    {"name": "TechCrunch",            "url": "https://techcrunch.com/feed/"},
    {"name": "Ars Technica",          "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "The Verge",             "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Wired",                 "url": "https://www.wired.com/feed/rss"},
    {"name": "VentureBeat",           "url": "https://venturebeat.com/feed/"},
    {"name": "Hacker News",           "url": "https://news.ycombinator.com/rss"},
    {"name": "Engadget",              "url": "https://www.engadget.com/rss.xml"},
    {"name": "ZDNet",                 "url": "https://www.zdnet.com/news/rss.xml"},
    {"name": "BleepingComputer",      "url": "https://www.bleepingcomputer.com/feed/"},
    {"name": "The Register",          "url": "https://www.theregister.com/headlines.atom"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/"},
    {"name": "PC Gamer",              "url": "https://www.pcgamer.com/rss/"},
    {"name": "IGN",                   "url": "https://feeds.feedburner.com/ign/all"},
    {"name": "Kotaku",                "url": "https://kotaku.com/rss"},
    {"name": "Eurogamer",             "url": "https://www.eurogamer.net/?format=rss"},
    {"name": "GamesIndustry.biz",     "url": "https://www.gamesindustry.biz/feed/rss"},
    {"name": "9to5Google",            "url": "https://9to5google.com/feed/"},
    {"name": "Bloomberg Technology",  "url": "https://www.bloomberg.com/technology", "html": True},
]

NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
]

TWITTER_QUERIES = [
    "(tech OR AI OR cybersecurity OR hack OR startup OR gaming) (announcement OR launch OR breaking OR major)",
    "(OpenAI OR Anthropic OR Google AI OR major hack OR data breach OR ransomware)",
]

FRESHNESS_HOURS = 13


def validate_config() -> list[str]:
    """Return warning strings for unset or placeholder env values."""
    PLACEHOLDERS = {"your-telegram-bot-token", "your-telegram-chat-id", ""}
    warnings = []
    if TELEGRAM_BOT_TOKEN in PLACEHOLDERS:
        warnings.append("TELEGRAM_BOT_TOKEN not set — edit .env")
    if TELEGRAM_CHAT_ID in PLACEHOLDERS:
        warnings.append("TELEGRAM_CHAT_ID not set — edit .env")
    return warnings
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
pytest tests/test_config.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: config with validate_config, no cloud keys"
```

---

## Task 3: logger.py

**Files:**
- Create: `logger.py`

No unit tests for logger (handler attachment is a side-effect that's hard to test in isolation; integration-tested via categorizer/runner tests).

- [ ] **Step 1: Write `logger.py`**

```python
import logging
import sys
from logging.handlers import RotatingFileHandler
import os

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "tech_pulse.log")


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # pythonw.exe has no stdout — guard before adding console handler
    if sys.stdout is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(fmt)
        logger.addHandler(console_handler)

    return logger


def add_gui_handler(handler: logging.Handler) -> None:
    """Attach handler to the root logger so all module loggers emit to it."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
    root.addHandler(handler)
```

- [ ] **Step 2: Commit**

```bash
git add logger.py
git commit -m "feat: logger with GUI handler and pythonw stdout guard"
```

---

## Task 4: state.py

**Files:**
- Create: `state.py`

- [ ] **Step 1: Write `state.py`**

```python
import json
import os
from typing import Set

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")


def load_sent_urls() -> Set[str]:
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        return set(data.get("sent_alerts", []))
    except Exception:
        return set()


def save_sent_urls(urls: Set[str]) -> None:
    url_list = list(urls)[-500:]
    with open(STATE_FILE, "w") as f:
        json.dump({"sent_alerts": url_list}, f)


def mark_sent(url: str) -> None:
    urls = load_sent_urls()
    urls.add(url)
    save_sent_urls(urls)


def is_already_sent(url: str) -> bool:
    return url in load_sent_urls()
```

- [ ] **Step 2: Commit**

```bash
git add state.py
git commit -m "feat: state dedup"
```

---

## Task 5: scraper.py + formatter.py + sender.py

**Files:**
- Create: `scraper.py`
- Create: `formatter.py`
- Create: `sender.py`
- Create: `tests/test_scraper.py`
- Create: `tests/test_formatter.py`
- Create: `tests/test_sender.py`

- [ ] **Step 1: Write `scraper.py`**

```python
import feedparser
import httpx
from bs4 import BeautifulSoup
import datetime
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

from logger import get_logger
from config import FRESHNESS_HOURS

logger = get_logger(__name__)


def _is_fresh(entry) -> bool:
    published = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not published:
        return True
    pub_dt = datetime.datetime(*published[:6], tzinfo=datetime.timezone.utc)
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=FRESHNESS_HOURS)
    return pub_dt >= cutoff


def _scrape_html(source: dict) -> List[Dict]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TechPulseBot/1.0)"}
        resp = httpx.get(source["url"], headers=headers, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = []
        for tag in soup.find_all(["h2", "h3"], limit=20):
            a = tag.find("a", href=True)
            if not a:
                continue
            title = a.get_text(strip=True)
            href = urljoin(source["url"], a["href"])
            if title:
                articles.append({"title": title, "url": href, "summary": "", "source": source["name"]})
        return articles
    except Exception as e:
        logger.warning(f"HTML scrape failed for {source['name']}: {e}")
        return []


def fetch_feed(source: dict) -> List[Dict]:
    if source.get("html"):
        return _scrape_html(source)
    try:
        feed = feedparser.parse(source["url"])
        articles = []
        for entry in feed.entries:
            if not _is_fresh(entry):
                continue
            articles.append({
                "title": getattr(entry, "title", "").strip(),
                "url": getattr(entry, "link", ""),
                "summary": getattr(entry, "summary", "")[:300].strip(),
                "source": source["name"],
            })
        logger.info(f"Scraped {len(articles)} fresh articles from {source['name']}")
        return articles
    except Exception as e:
        logger.warning(f"Feed fetch failed for {source['name']}: {e}")
        return []


def fetch_all_sources(sources: Optional[List[Dict]] = None) -> List[Dict]:
    from config import NEWS_SOURCES
    sources = sources or NEWS_SOURCES
    all_articles = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_feed, src): src for src in sources}
        for future in as_completed(futures):
            all_articles.extend(future.result())
    return all_articles
```

- [ ] **Step 2: Write `formatter.py`**

```python
import datetime
from typing import List, Dict


def _now_myt() -> str:
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    myt = utc_now + datetime.timedelta(hours=8)
    return myt.strftime("%I:%M %p MYT · %B %d, %Y")


def _item_line(item: Dict) -> str:
    title = item.get("title", "")
    summary = item.get("summary", "")
    url = item.get("url", "")
    return f'· <b>{title}</b> → {summary}\n  🔗 <a href="{url}">{item.get("source", "")}</a>'


def format_full_briefing(categorized: Dict, mode: str = "morning") -> List[str]:
    label = "Morning Briefing" if mode == "morning" else "Evening Briefing"
    lines = [
        f"📰 <b>TECH PULSE — {label}</b>",
        f"🕐 {_now_myt()}",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    alerts = categorized.get("high_alerts", [])
    if alerts:
        lines.append("")
        lines.append("🚨 <b>HIGH ALERT</b>")
        for a in alerts:
            lines.append(f'🚨 <b>{a["title"]}</b>')
            lines.append(f'· {a.get("summary", "")}')
            lines.append(f'🔗 <a href="{a["url"]}">{a.get("source", "")}</a>')

    lines += ["", "━━━━━━━━━━━━━━━━━━━━━━", "📰 <b>FULL TECH FEED</b>", ""]

    sections = [
        ("🤖 <b>AI Developments</b>", categorized.get("ai", [])),
        ("🔐 <b>Cybersecurity</b>", categorized.get("cybersecurity", [])),
        ("🎮 <b>Gaming</b>", categorized.get("gaming", [])),
        ("💻 <b>Tech / Startups</b>", categorized.get("tech_startups", [])),
        ("⚠️ <b>Scandals</b>", categorized.get("scandals", [])),
    ]
    for header, items in sections:
        if not items:
            continue
        lines.append(header)
        for item in items:
            lines.append(_item_line(item))
        lines.append("")

    insight = categorized.get("quick_insight", "")
    if insight:
        lines += ["━━━━━━━━━━━━━━━━━━━━━━", "📈 <b>QUICK INSIGHT</b>", f"→ {insight}"]

    return split_message("\n".join(lines))


def format_alert_message(alert: Dict) -> str:
    now = _now_myt()
    return (
        f"🚨 <b>HIGH ALERT — BREAKING</b>\n\n"
        f'🚨 <b>{alert["title"]}</b>\n'
        f'· {alert.get("summary", "")}\n'
        f'🔗 <a href="{alert["url"]}">{alert.get("source", "")}</a>\n'
        f"⏱ Detected: {now}"
    )


def split_message(text: str, limit: int = 4096) -> List[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts
```

- [ ] **Step 3: Write `sender.py`**

```python
import httpx
import time
from typing import List

from logger import get_logger
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = get_logger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(text: str, retries: int = 1) -> bool:
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    for attempt in range(retries + 1):
        try:
            resp = httpx.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
            if resp.is_success:
                logger.info(f"Telegram message sent ({len(text)} chars)")
                return True
            logger.warning(f"Telegram API error: {resp.text}")
        except Exception as e:
            logger.warning(f"Telegram send attempt {attempt + 1} failed: {e}")
            if attempt < retries:
                time.sleep(5)
    logger.error("Failed to send Telegram message after retries")
    return False


def send_messages(parts: List[str]) -> None:
    for part in parts:
        send_message(part)
```

- [ ] **Step 4: Write `tests/test_scraper.py`**

```python
import datetime
import pytest
from unittest.mock import MagicMock, patch


def make_entry(title, link, summary, hours_ago=1):
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_ago)
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.published_parsed = t.timetuple()
    return entry


def test_fetch_feed_returns_articles():
    with patch("scraper.feedparser.parse") as mock_parse:
        mock_parse.return_value = MagicMock(
            entries=[make_entry("AI Model Launched", "https://ex.com/1", "Summary here")]
        )
        from scraper import fetch_feed
        result = fetch_feed({"name": "Test Source", "url": "https://ex.com/feed"})
    assert len(result) == 1
    assert result[0]["title"] == "AI Model Launched"
    assert result[0]["source"] == "Test Source"


def test_fetch_feed_skips_old_articles():
    with patch("scraper.feedparser.parse") as mock_parse:
        mock_parse.return_value = MagicMock(
            entries=[make_entry("Old News", "https://ex.com/2", "Old", hours_ago=25)]
        )
        from scraper import fetch_feed
        result = fetch_feed({"name": "Test Source", "url": "https://ex.com/feed"})
    assert result == []


def test_fetch_feed_handles_failure():
    with patch("scraper.feedparser.parse", side_effect=Exception("network error")):
        from scraper import fetch_feed
        result = fetch_feed({"name": "Bad Source", "url": "https://bad.url/feed"})
    assert result == []


def test_fetch_all_sources_combines_results():
    with patch("scraper.fetch_feed") as mock_fetch:
        mock_fetch.side_effect = [
            [{"title": "A", "url": "https://a.com", "source": "S1", "summary": ""}],
            [{"title": "B", "url": "https://b.com", "source": "S2", "summary": ""}],
        ]
        from scraper import fetch_all_sources
        result = fetch_all_sources([{"name": "S1", "url": "u1"}, {"name": "S2", "url": "u2"}])
    assert len(result) == 2
    assert {r["title"] for r in result} == {"A", "B"}
```

- [ ] **Step 5: Write `tests/test_formatter.py`**

```python
from formatter import format_full_briefing, format_alert_message, split_message

SAMPLE = {
    "high_alerts": [
        {"title": "Ransomware Attack", "summary": "200 hospitals hit", "url": "https://bc.com/1", "source": "BC"}
    ],
    "ai": [{"title": "GPT-5 Released", "summary": "Beats benchmarks", "url": "https://tc.com/2", "source": "TC"}],
    "cybersecurity": [],
    "gaming": [{"title": "GTA VI Delayed", "summary": "Q1 2027", "url": "https://ign.com/3", "source": "IGN"}],
    "tech_startups": [], "scandals": [],
    "quick_insight": "AI inference costs dropped 40% YoY",
}


def test_format_full_briefing_returns_list():
    parts = format_full_briefing(SAMPLE, mode="morning")
    assert isinstance(parts, list) and all(isinstance(p, str) for p in parts)


def test_format_full_briefing_contains_header():
    full = "".join(format_full_briefing(SAMPLE, mode="morning"))
    assert "TECH PULSE" in full and "Morning Briefing" in full


def test_format_full_briefing_contains_high_alert():
    full = "".join(format_full_briefing(SAMPLE))
    assert "HIGH ALERT" in full and "Ransomware Attack" in full


def test_format_full_briefing_contains_gaming():
    full = "".join(format_full_briefing(SAMPLE))
    assert "GTA VI Delayed" in full


def test_format_alert_message_contains_headline():
    alert = {"title": "Critical Zero-Day", "summary": "Affects 500M", "url": "https://ex.com", "source": "Ars"}
    msg = format_alert_message(alert)
    assert "Critical Zero-Day" in msg and "HIGH ALERT" in msg


def test_split_message_respects_limit():
    long_text = "A" * 10000
    parts = split_message(long_text, limit=4096)
    assert all(len(p) <= 4096 for p in parts)
    assert "".join(parts) == long_text
```

- [ ] **Step 6: Write `tests/test_sender.py`**

```python
from unittest.mock import patch, MagicMock


def test_send_message_posts_to_telegram():
    with patch("sender.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(is_success=True)
        from sender import send_message
        result = send_message("Hello Telegram")
    assert result is True
    assert mock_post.call_args[1]["json"]["text"] == "Hello Telegram"
    assert mock_post.call_args[1]["json"]["parse_mode"] == "HTML"


def test_send_message_retries_on_failure():
    with patch("sender.httpx.post") as mock_post:
        mock_post.side_effect = [Exception("network error"), MagicMock(is_success=True)]
        with patch("sender.time.sleep"):
            from sender import send_message
            result = send_message("Retry test")
    assert result is True and mock_post.call_count == 2


def test_send_messages_sends_all_parts():
    with patch("sender.send_message") as mock_send:
        mock_send.return_value = True
        from sender import send_messages
        send_messages(["part1", "part2", "part3"])
    assert mock_send.call_count == 3
```

- [ ] **Step 7: Run all tests so far**

```bash
pytest tests/test_scraper.py tests/test_formatter.py tests/test_sender.py -v
```
Expected: all PASSED (12 tests)

- [ ] **Step 8: Commit**

```bash
git add scraper.py formatter.py sender.py tests/test_scraper.py tests/test_formatter.py tests/test_sender.py
git commit -m "feat: scraper, formatter, sender with tests"
```

---

## Task 6: categorizer.py (LM Studio)

**Files:**
- Create: `categorizer.py`
- Create: `tests/test_categorizer.py`

The key change from the old project: uses LM Studio's OpenAI-compatible REST API via httpx. Raises on failure instead of returning None.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_categorizer.py
import json
import pytest
from unittest.mock import patch, MagicMock

SAMPLE_ITEMS = [
    {"title": "OpenAI releases GPT-5", "url": "https://tc.com/1", "summary": "New model", "source": "TechCrunch"},
    {"title": "Massive hospital ransomware", "url": "https://bc.com/2", "summary": "200 hospitals", "source": "BC"},
]

SAMPLE_RESPONSE = {
    "high_alerts": [{"title": "Massive hospital ransomware", "summary": "200 hospitals offline",
                     "url": "https://bc.com/2", "source": "BC"}],
    "ai": [{"title": "OpenAI releases GPT-5", "summary": "New model", "url": "https://tc.com/1", "source": "TC"}],
    "cybersecurity": [], "gaming": [], "tech_startups": [], "scandals": [],
    "quick_insight": "AI model releases are accelerating in 2026",
}


def _mock_lm_response(body: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"choices": [{"message": {"content": json.dumps(body)}}]}
    return resp


def test_categorize_items_returns_all_categories():
    with patch("categorizer.httpx.post", return_value=_mock_lm_response(SAMPLE_RESPONSE)):
        from categorizer import categorize_items
        result = categorize_items(SAMPLE_ITEMS)
    assert "high_alerts" in result and "ai" in result
    assert result["ai"][0]["title"] == "OpenAI releases GPT-5"
    assert result["quick_insight"] == "AI model releases are accelerating in 2026"


def test_categorize_returns_empty_dict_for_no_items():
    from categorizer import categorize_items
    result = categorize_items([])
    assert result["high_alerts"] == []
    assert result["ai"] == []


def test_categorize_raises_on_lm_studio_failure():
    with patch("categorizer.httpx.post", side_effect=Exception("connection refused")):
        from categorizer import categorize_items
        with pytest.raises(Exception, match="connection refused"):
            categorize_items(SAMPLE_ITEMS)


def test_categorize_strips_markdown_fences():
    fenced = "```json\n" + json.dumps(SAMPLE_RESPONSE) + "\n```"
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"choices": [{"message": {"content": fenced}}]}
    with patch("categorizer.httpx.post", return_value=resp):
        from categorizer import categorize_items
        result = categorize_items(SAMPLE_ITEMS)
    assert result["quick_insight"] == "AI model releases are accelerating in 2026"


def test_has_high_alerts_true():
    from categorizer import has_high_alerts
    assert has_high_alerts(SAMPLE_RESPONSE) is True


def test_has_high_alerts_false():
    from categorizer import has_high_alerts
    assert has_high_alerts({**SAMPLE_RESPONSE, "high_alerts": []}) is False
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_categorizer.py -v
```
Expected: ImportError — `categorizer` module doesn't exist yet.

- [ ] **Step 3: Write `categorizer.py`**

```python
import json
import httpx
from typing import List, Dict

from logger import get_logger
from config import LM_STUDIO_HOST, LM_STUDIO_MODEL

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a tech news editor. Categorize news items and return valid JSON only.
Never fabricate news. Only include items actually present in the input."""

CATEGORY_PROMPT = """Categorize these tech news items into the following JSON structure.
Only include real items from the input. Do not add items not in the input.

Categories:
- high_alerts: Major hacks/ransomware, big scandals, breakthroughs, massive product launches, major deals
- ai: AI model releases, partnerships, research breakthroughs
- cybersecurity: Hacks, breaches, vulnerabilities, incidents
- gaming: Game launches, platform updates, industry moves, gaming company news
- tech_startups: Funding rounds, acquisitions, product launches
- scandals: Legal disputes, policy conflicts, controversies
- quick_insight: (string, not array) One sharp trend or observation from the news

Return this exact JSON structure:
{{
  "high_alerts": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "ai": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "cybersecurity": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "gaming": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "tech_startups": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "scandals": [{{"title": "", "summary": "1 line", "url": "", "source": ""}}],
  "quick_insight": "one trend observation"
}}

News items to categorize:
{items}"""

_EMPTY_RESULT = {
    "high_alerts": [], "ai": [], "cybersecurity": [],
    "gaming": [], "tech_startups": [], "scandals": [],
    "quick_insight": "No news items found for this period.",
}


def categorize_items(items: List[Dict]) -> Dict:
    """Categorise items via LM Studio. Raises on connection or parse failure."""
    if not items:
        return dict(_EMPTY_RESULT)

    items_json = json.dumps(
        [{"title": i["title"], "url": i["url"], "summary": i["summary"], "source": i["source"]}
         for i in items],
        indent=2,
    )
    payload = {
        "model": LM_STUDIO_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": CATEGORY_PROMPT.format(items=items_json)},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    resp = httpx.post(f"{LM_STUDIO_HOST}/v1/chat/completions", json=payload, timeout=120)
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    result = json.loads(raw)
    logger.info(
        f"Categorized {len(items)} items — "
        f"{len(result.get('high_alerts', []))} alerts, "
        f"{len(result.get('ai', []))} AI, "
        f"{len(result.get('gaming', []))} gaming"
    )
    return result


def has_high_alerts(categorized: Dict) -> bool:
    return bool(categorized.get("high_alerts"))
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_categorizer.py -v
```
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add categorizer.py tests/test_categorizer.py
git commit -m "feat: categorizer using LM Studio, raises on failure"
```

---

## Task 7: twitter.py

**Files:**
- Create: `twitter.py`

- [ ] **Step 1: Write `twitter.py`**

Same logic as old project — only the user-agent changes to a Windows Chrome string.

```python
from playwright.sync_api import sync_playwright, Page
from typing import List, Dict
import re

from logger import get_logger
from config import NITTER_INSTANCES, TWITTER_QUERIES

logger = get_logger(__name__)

RESULTS_PER_QUERY = 20
_WINDOWS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def scrape_nitter_query(query: str, instance: str, page: Page) -> List[Dict]:
    encoded = query.replace(" ", "+").replace("(", "%28").replace(")", "%29")
    url = f"{instance}/search?q={encoded}&f=tweets"
    try:
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        tweets = []
        for item in page.query_selector_all(".timeline-item")[:RESULTS_PER_QUERY]:
            content_el = item.query_selector(".tweet-content")
            link_el = item.query_selector("a.tweet-link")
            if not content_el or not link_el:
                continue
            text = content_el.inner_text().strip()
            href = link_el.get_attribute("href") or ""
            tweet_url = "https://twitter.com" + href if href.startswith("/") else href
            score = sum(
                int(s.inner_text().strip().replace(",", ""))
                for s in item.query_selector_all(".tweet-stat")
                if re.match(r"^\d+$", s.inner_text().strip().replace(",", ""))
            )
            tweets.append({"text": text, "url": tweet_url, "score": score})
        return tweets
    except Exception as e:
        logger.warning(f"Nitter scrape failed ({instance}): {e}")
        return []


def fetch_twitter() -> List[Dict]:
    all_tweets = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=_WINDOWS_UA)
            page = context.new_page()
            for query in TWITTER_QUERIES:
                for instance in NITTER_INSTANCES:
                    results = scrape_nitter_query(query, instance, page)
                    if results:
                        all_tweets.extend(results)
                        logger.info(f"Got {len(results)} tweets from {instance}")
                        break
                else:
                    logger.warning(f"All Nitter instances failed for: {query[:50]}")
            browser.close()
    except Exception as e:
        logger.error(f"Playwright failed: {e}")
        return []

    seen: set[str] = set()
    unique = [t for t in all_tweets if not (t["url"] in seen or seen.add(t["url"]))]
    top = sorted(unique, key=lambda x: x["score"], reverse=True)[:20]

    return [
        {
            "title": t["text"][:120] + ("..." if len(t["text"]) > 120 else ""),
            "url": t["url"],
            "summary": t["text"][:300],
            "source": "X/Twitter",
        }
        for t in top
    ]
```

- [ ] **Step 2: Commit**

```bash
git add twitter.py
git commit -m "feat: twitter scraper with Windows Chrome user-agent"
```

---

## Task 8: runner.py

**Files:**
- Create: `runner.py`
- Create: `tests/test_runner.py`

`runner.py` mirrors `main.py` from the old project, with `categorize_items` raising on failure (caught here with try/except).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_runner.py
import pytest
from unittest.mock import patch, MagicMock

MOCK_ARTICLES = [
    {"title": "AI News", "url": "https://tc.com/1", "summary": "Big news", "source": "TechCrunch"}
]
MOCK_CATEGORIZED = {
    "high_alerts": [],
    "ai": [{"title": "AI News", "summary": "Big news", "url": "https://tc.com/1", "source": "TechCrunch"}],
    "cybersecurity": [], "gaming": [], "tech_startups": [], "scandals": [],
    "quick_insight": "AI is everywhere",
}


def test_run_full_sends_briefing():
    with patch("runner.fetch_all_sources", return_value=MOCK_ARTICLES), \
         patch("runner.fetch_twitter", return_value=[]), \
         patch("runner.categorize_items", return_value=MOCK_CATEGORIZED), \
         patch("runner.format_full_briefing", return_value=["message"]), \
         patch("runner.send_messages") as mock_send:
        from runner import run_full
        run_full()
    assert mock_send.called


def test_run_full_sends_error_message_on_categorizer_failure():
    with patch("runner.fetch_all_sources", return_value=MOCK_ARTICLES), \
         patch("runner.fetch_twitter", return_value=[]), \
         patch("runner.categorize_items", side_effect=Exception("LM Studio down")), \
         patch("runner.send_message") as mock_send_single:
        from runner import run_full
        run_full()
    assert mock_send_single.called
    assert "failed" in mock_send_single.call_args[0][0].lower()


def test_run_alert_silent_when_no_alerts():
    no_alerts = {**MOCK_CATEGORIZED, "high_alerts": []}
    with patch("runner.fetch_all_sources", return_value=MOCK_ARTICLES), \
         patch("runner.fetch_twitter", return_value=[]), \
         patch("runner.categorize_items", return_value=no_alerts), \
         patch("runner.send_message") as mock_send:
        from runner import run_alert
        run_alert()
    assert not mock_send.called


def test_run_alert_sends_when_high_alert_found():
    alert = {"title": "Ransomware", "summary": "Bad", "url": "https://bc.com/1", "source": "BC"}
    with_alert = {**MOCK_CATEGORIZED, "high_alerts": [alert]}
    with patch("runner.fetch_all_sources", return_value=MOCK_ARTICLES), \
         patch("runner.fetch_twitter", return_value=[]), \
         patch("runner.categorize_items", return_value=with_alert), \
         patch("runner.is_already_sent", return_value=False), \
         patch("runner.mark_sent"), \
         patch("runner.format_alert_message", return_value="🚨 Alert"), \
         patch("runner.send_message") as mock_send:
        from runner import run_alert
        run_alert()
    assert mock_send.called
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_runner.py -v
```
Expected: ImportError — `runner` module not found.

- [ ] **Step 3: Write `runner.py`**

```python
import argparse
import datetime

from scraper import fetch_all_sources
from twitter import fetch_twitter
from categorizer import categorize_items, has_high_alerts
from formatter import format_full_briefing, format_alert_message
from sender import send_messages, send_message
from state import is_already_sent, mark_sent
from logger import get_logger

logger = get_logger(__name__)


def _briefing_mode() -> str:
    myt_hour = (datetime.datetime.now(datetime.timezone.utc).hour + 8) % 24
    return "morning" if myt_hour < 14 else "evening"


def run_full() -> None:
    logger.info("Starting FULL briefing run")
    articles = fetch_all_sources()
    tweets = fetch_twitter()
    all_items = articles + tweets
    logger.info(f"Total items collected: {len(all_items)}")

    try:
        categorized = categorize_items(all_items)
    except Exception as e:
        logger.error(f"Categorization failed: {e}")
        send_message("⚠️ Tech Pulse: Categorization failed. Is LM Studio running?")
        return

    mode = _briefing_mode()
    parts = format_full_briefing(categorized, mode=mode)
    send_messages(parts)
    logger.info("FULL briefing sent")


def run_alert() -> None:
    logger.info("Starting ALERT scan")
    articles = fetch_all_sources()
    tweets = fetch_twitter()
    all_items = articles + tweets

    try:
        categorized = categorize_items(all_items)
    except Exception as e:
        logger.error(f"Alert scan categorization failed: {e}")
        return

    if not has_high_alerts(categorized):
        logger.info("No HIGH ALERTs detected — silent run")
        return

    for alert in categorized["high_alerts"]:
        url = alert.get("url", "")
        if is_already_sent(url):
            logger.info(f"Alert already sent: {alert['title']}")
            continue
        msg = format_alert_message(alert)
        sent = send_message(msg)
        if sent:
            mark_sent(url)
            logger.info(f"HIGH ALERT sent: {alert['title']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tech Pulse Runner")
    parser.add_argument("--mode", choices=["full", "alert"], required=True)
    args = parser.parse_args()
    if args.mode == "full":
        run_full()
    elif args.mode == "alert":
        run_alert()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_runner.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add runner.py tests/test_runner.py
git commit -m "feat: runner with LM Studio error handling"
```

---

## Task 9: bot_listener.py

**Files:**
- Create: `bot_listener.py`

- [ ] **Step 1: Write `bot_listener.py`**

```python
import subprocess
import sys
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from logger import get_logger
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = get_logger(__name__)

PYTHON = sys.executable
RUNNER_SCRIPT = os.path.join(os.path.dirname(__file__), "runner.py")
AUTHORIZED_CHAT_ID = str(TELEGRAM_CHAT_ID)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_chat.id) != AUTHORIZED_CHAT_ID:
        return
    text = (update.message.text or "").strip().upper()
    if text == "RUN NEWS":
        await update.message.reply_text("⏳ Running full scan...")
        logger.info("Manual trigger: RUN NEWS")
        subprocess.Popen([PYTHON, RUNNER_SCRIPT, "--mode", "full"])
    elif text == "RUN ALERT":
        await update.message.reply_text("⏳ Scanning for HIGH ALERTs...")
        logger.info("Manual trigger: RUN ALERT")
        subprocess.Popen([PYTHON, RUNNER_SCRIPT, "--mode", "alert"])


def run_bot() -> None:
    logger.info("Bot listener starting...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(poll_interval=2)


if __name__ == "__main__":
    run_bot()
```

- [ ] **Step 2: Commit**

```bash
git add bot_listener.py
git commit -m "feat: bot_listener pointing to runner.py"
```

---

## Task 10: scheduler.py

**Files:**
- Create: `scheduler.py`
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_scheduler.py
import datetime
from unittest.mock import patch, MagicMock, call
import schedule as schedule_lib


def test_scheduler_converts_myt_to_local_utc_plus8():
    """When machine timezone == MYT (UTC+8), local_hour == myt_hour."""
    # Simulate both clocks returning the same naive time (offset = 0)
    fake_dt = datetime.datetime(2026, 4, 26, 10, 0, 0)
    with patch("scheduler.datetime.datetime") as mock_dt, \
         patch("scheduler.schedule") as mock_sched:
        mock_dt.now.return_value = fake_dt
        mock_sched.every.return_value.day.at.return_value.do.return_value = MagicMock()
        mock_sched.every.return_value.hour.do.return_value = MagicMock()

        from scheduler import Scheduler
        s = Scheduler()

        # offset = 0 → local 8:00 and 20:00 should be scheduled
        s.start(on_full=lambda: None, on_alert=lambda: None)

    at_calls = [str(c) for c in mock_sched.every.return_value.day.at.call_args_list]
    assert any("08:00" in c for c in at_calls)
    assert any("20:00" in c for c in at_calls)


def test_scheduler_offset_est_minus5():
    """UTC-5 (EST): offset = -5, so 08:00 MYT → 03:00 local, 20:00 MYT → 15:00 local."""
    # local is UTC-5, MYT is UTC+8 → local = MYT - 13 hours
    local_now = datetime.datetime(2026, 4, 26, 10, 0, 0)   # 10:00 EST
    myt_now   = datetime.datetime(2026, 4, 26, 23, 0, 0)   # 23:00 MYT (same UTC moment)

    with patch("scheduler.datetime.datetime") as mock_dt, \
         patch("scheduler.schedule") as mock_sched:
        mock_dt.now.side_effect = [local_now, myt_now]
        mock_sched.every.return_value.day.at.return_value.do.return_value = MagicMock()
        mock_sched.every.return_value.hour.do.return_value = MagicMock()

        import importlib, scheduler as sched_mod
        importlib.reload(sched_mod)

        s = sched_mod.Scheduler()
        s.start(on_full=lambda: None, on_alert=lambda: None)

    at_calls = [c.args[0] if c.args else "" for c in mock_sched.every.return_value.day.at.call_args_list]
    # offset = 10 - 23 = -13 → (8 - 13) % 24 = 19, (20 - 13) % 24 = 7
    assert "19:00" in at_calls
    assert "07:00" in at_calls


def test_next_run_times_returns_sorted_datetimes():
    with patch("scheduler.schedule.jobs", [
        MagicMock(next_run=datetime.datetime(2026, 4, 26, 20, 0)),
        MagicMock(next_run=datetime.datetime(2026, 4, 26, 11, 0)),
    ]):
        from scheduler import Scheduler
        s = Scheduler()
        times = s.next_run_times()
    assert times[0] < times[1]
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_scheduler.py -v
```
Expected: ImportError.

- [ ] **Step 3: Write `scheduler.py`**

```python
import zoneinfo
import datetime
import threading
import time
import schedule

from config import SCHEDULE_TZ
from logger import get_logger

logger = get_logger(__name__)


class Scheduler:
    def __init__(self) -> None:
        self._running = False

    def start(self, on_full, on_alert) -> None:
        tz = zoneinfo.ZoneInfo(SCHEDULE_TZ)
        now_local = datetime.datetime.now()
        now_tz = datetime.datetime.now(tz).replace(tzinfo=None)
        offset = round((now_local - now_tz).total_seconds() / 3600)
        logger.info(f"Scheduler: {SCHEDULE_TZ} offset from local = {offset:+d}h")

        for myt_hour in (8, 20):
            local_hour = (myt_hour + offset) % 24
            schedule.every().day.at(f"{local_hour:02d}:00").do(
                lambda f=on_full: threading.Thread(target=f, daemon=True).start()
            ).tag("full")
            logger.info(f"Full briefing scheduled at local {local_hour:02d}:00 ({myt_hour:02d}:00 MYT)")

        schedule.every().hour.do(
            lambda a=on_alert: threading.Thread(target=a, daemon=True).start()
        ).tag("alert")
        logger.info("Alert scan scheduled every hour")

        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self) -> None:
        self._running = False
        schedule.clear()

    def _loop(self) -> None:
        while self._running:
            schedule.run_pending()
            time.sleep(30)

    def next_run_times(self) -> list[datetime.datetime]:
        return sorted(j.next_run for j in schedule.jobs if j.next_run)

    def next_full_run(self) -> datetime.datetime | None:
        jobs = [j for j in schedule.jobs if "full" in j.tags]
        return min((j.next_run for j in jobs), default=None)

    def next_alert_run(self) -> datetime.datetime | None:
        jobs = [j for j in schedule.jobs if "alert" in j.tags]
        return min((j.next_run for j in jobs), default=None)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_scheduler.py -v
```
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add scheduler.py tests/test_scheduler.py
git commit -m "feat: scheduler with MYT->local timezone conversion"
```

---

## Task 11: gui.py

**Files:**
- Create: `gui.py`

GUI components cannot be unit-tested automatically (Tk requires a display). Manual smoke test is in Task 13.

- [ ] **Step 1: Write `gui.py`**

```python
import os
import sys
import queue
import logging
import threading
import subprocess
import datetime
import tkinter

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw

import runner
from scheduler import Scheduler
from logger import get_logger, add_gui_handler
from config import validate_config
import httpx

logger = get_logger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class GUILogHandler(logging.Handler):
    def __init__(self, q: queue.Queue) -> None:
        super().__init__()
        self._q = q

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._q.put_nowait(self.format(record))
        except Exception:
            pass


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tech Pulse News")
        self.geometry("820x620")
        self.minsize(700, 500)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._ui_queue: queue.Queue[tuple] = queue.Queue()
        self._full_lock = threading.Event()
        self._alert_lock = threading.Event()
        self._log_lines: list[str] = []
        self._MAX_LINES = 200

        self._scheduler = Scheduler()
        self._bot_proc: subprocess.Popen | None = None
        self._tray_icon: pystray.Icon | None = None

        self._build_ui()
        add_gui_handler(GUILogHandler(self._log_queue))

        warnings = validate_config()
        for w in warnings:
            logger.warning(f"Config: {w}")

        self._start_bot_listener()
        self._scheduler.start(on_full=self._run_full_worker, on_alert=self._run_alert_worker)
        self._start_tray_icon()
        threading.Thread(target=self._status_poll_loop, daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(200, self._drain_queues)

    # ── UI layout ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Status bar
        status_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        status_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        status_frame.grid_columnconfigure(0, weight=1)
        self._lm_label = ctk.CTkLabel(status_frame, text="● LM Studio: checking…", text_color="gray")
        self._lm_label.grid(row=0, column=0, sticky="w", padx=12)
        self._bot_label = ctk.CTkLabel(status_frame, text="● Bot: starting…", text_color="gray")
        self._bot_label.grid(row=0, column=1, sticky="e", padx=12)

        # Schedule panel
        sched_frame = ctk.CTkFrame(self, corner_radius=6)
        sched_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(8, 4))
        sched_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(sched_frame, text="SCHEDULE", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(6, 0)
        )
        self._next_full_label = ctk.CTkLabel(sched_frame, text="Next briefing: —")
        self._next_full_label.grid(row=1, column=0, sticky="w", padx=10)
        self._next_alert_label = ctk.CTkLabel(sched_frame, text="Next alert scan: —")
        self._next_alert_label.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 6))

        # Controls
        ctrl_frame = ctk.CTkFrame(self, corner_radius=6)
        ctrl_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        ctk.CTkLabel(ctrl_frame, text="CONTROLS", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 0)
        )
        self._full_btn = ctk.CTkButton(ctrl_frame, text="▶ Run Full Briefing", command=self._on_run_full)
        self._full_btn.grid(row=1, column=0, padx=10, pady=6, sticky="w")
        self._alert_btn = ctk.CTkButton(ctrl_frame, text="▶ Run Alert Scan", command=self._on_run_alert)
        self._alert_btn.grid(row=1, column=1, padx=4, pady=6, sticky="w")

        # Activity log
        log_frame = ctk.CTkFrame(self, corner_radius=6)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=4)
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_frame, text="ACTIVITY LOG", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(6, 0)
        )
        self._log_box = ctk.CTkTextbox(log_frame, state="disabled", wrap="none",
                                        font=ctk.CTkFont(family="Consolas", size=11))
        self._log_box.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        # Bottom bar
        bottom_frame = ctk.CTkFrame(self, height=36, corner_radius=0)
        bottom_frame.grid(row=4, column=0, sticky="ew", padx=0, pady=0)
        ctk.CTkButton(bottom_frame, text="Open .env", width=100,
                      command=lambda: os.startfile(os.path.join(PROJECT_ROOT, ".env"))).pack(
            side="left", padx=10, pady=4
        )
        ctk.CTkButton(bottom_frame, text="Minimize to Tray", width=140,
                      command=self._on_close).pack(side="right", padx=10, pady=4)

    # ── Queue draining (main-thread only) ──────────────────────────────────

    def _drain_queues(self) -> None:
        # Log queue
        lines_added = 0
        while not self._log_queue.empty() and lines_added < 50:
            try:
                msg = self._log_queue.get_nowait()
                self._log_lines.append(msg)
                lines_added += 1
            except queue.Empty:
                break
        if self._log_lines[-self._MAX_LINES:] and lines_added:
            self._log_box.configure(state="normal")
            self._log_box.insert("end", "\n".join(self._log_lines[-lines_added:]) + "\n")
            # trim to MAX_LINES
            total = int(self._log_box.index("end-1c").split(".")[0])
            if total > self._MAX_LINES:
                self._log_box.delete("1.0", f"{total - self._MAX_LINES}.0")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")

        # UI queue
        while not self._ui_queue.empty():
            try:
                cmd, *args = self._ui_queue.get_nowait()
                if cmd == "lm_status":
                    ok, model_id = args
                    color = "#28a745" if ok else "#dc3545"
                    text = f"● LM Studio: {model_id}" if ok else f"● LM Studio: {model_id}"
                    self._lm_label.configure(text=text, text_color=color)
                    self._update_tray_color()
                elif cmd == "bot_status":
                    alive = args[0]
                    self._bot_label.configure(
                        text="● Bot: running" if alive else "● Bot: stopped",
                        text_color="#28a745" if alive else "#dc3545",
                    )
                    self._update_tray_color()
                elif cmd == "schedule":
                    self._next_full_label.configure(text=args[0])
                    self._next_alert_label.configure(text=args[1])
                elif cmd == "enable_btn":
                    btn = self._full_btn if args[0] == "full" else self._alert_btn
                    btn.configure(state="normal")
            except queue.Empty:
                break

        self.after(200, self._drain_queues)

    # ── Status polling (daemon thread) ─────────────────────────────────────

    def _status_poll_loop(self) -> None:
        while True:
            self._poll_lm_status()
            self._poll_bot_status()
            self._poll_schedule()
            threading.Event().wait(10)

    def _poll_lm_status(self) -> None:
        try:
            r = httpx.get(f"http://localhost:1234/v1/models", timeout=2)
            models = r.json().get("data", [])
            if models:
                self._ui_queue.put(("lm_status", True, models[0]["id"]))
            else:
                self._ui_queue.put(("lm_status", False, "running — no model loaded"))
        except Exception:
            self._ui_queue.put(("lm_status", False, "unreachable"))

    def _poll_bot_status(self) -> None:
        alive = self._bot_proc is not None and self._bot_proc.poll() is None
        self._ui_queue.put(("bot_status", alive))

    def _poll_schedule(self) -> None:
        now = datetime.datetime.now()

        def fmt(dt: datetime.datetime | None) -> str:
            if dt is None:
                return "—"
            delta = dt - now
            total = int(delta.total_seconds())
            if total < 0:
                return dt.strftime("%H:%M")
            h, rem = divmod(total, 3600)
            m = rem // 60
            return f"{dt.strftime('%H:%M')} (in {h}h {m:02d}m)"

        full_label = "Next briefing: " + fmt(self._scheduler.next_full_run())
        alert_label = "Next alert scan: " + fmt(self._scheduler.next_alert_run())
        self._ui_queue.put(("schedule", full_label, alert_label))

    # ── Tray icon ──────────────────────────────────────────────────────────

    def _make_tray_image(self, color: str) -> Image.Image:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse((8, 8, 56, 56), fill=color)
        return img

    def _update_tray_color(self) -> None:
        if self._tray_icon is None:
            return
        lm_ok = "unreachable" not in self._lm_label.cget("text")
        bot_ok = "running" in self._bot_label.cget("text")
        if lm_ok and bot_ok:
            color = "#28a745"
        elif not lm_ok and not bot_ok:
            color = "#dc3545"
        else:
            color = "#fd7e14"
        self._tray_icon.icon = self._make_tray_image(color)

    def _start_tray_icon(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda: self._ui_queue.put(("show",))),
            pystray.MenuItem("Exit", lambda: self._ui_queue.put(("exit",))),
        )
        icon = pystray.Icon(
            "TechPulse",
            self._make_tray_image("#fd7e14"),
            "Tech Pulse News",
            menu,
        )
        self._tray_icon = icon
        threading.Thread(target=icon.run, daemon=True).start()

    # ── Bot subprocess ─────────────────────────────────────────────────────

    def _start_bot_listener(self) -> None:
        script = os.path.join(PROJECT_ROOT, "bot_listener.py")
        if not os.path.exists(script):
            logger.warning("bot_listener.py not found — bot disabled")
            return
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self._bot_proc = subprocess.Popen([sys.executable, script], creationflags=flags)
        logger.info("Bot listener subprocess started")

    # ── Run buttons & workers ──────────────────────────────────────────────

    def _on_run_full(self) -> None:
        if self._full_lock.is_set():
            return
        self._full_btn.configure(state="disabled")
        threading.Thread(target=self._run_full_worker, daemon=True).start()

    def _on_run_alert(self) -> None:
        if self._alert_lock.is_set():
            return
        self._alert_btn.configure(state="disabled")
        threading.Thread(target=self._run_alert_worker, daemon=True).start()

    def _run_full_worker(self) -> None:
        if self._full_lock.is_set():
            return
        self._full_lock.set()
        try:
            runner.run_full()
        finally:
            self._full_lock.clear()
            self._ui_queue.put(("enable_btn", "full"))

    def _run_alert_worker(self) -> None:
        if self._alert_lock.is_set():
            return
        self._alert_lock.set()
        try:
            runner.run_alert()
        finally:
            self._alert_lock.clear()
            self._ui_queue.put(("enable_btn", "alert"))

    # ── Window lifecycle ───────────────────────────────────────────────────

    def _on_close(self) -> None:
        self.withdraw()

    def _show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def destroy(self) -> None:
        if self._tray_icon:
            self._tray_icon.stop()
        if self._bot_proc and self._bot_proc.poll() is None:
            self._bot_proc.terminate()
        self._scheduler.stop()
        super().destroy()
```

- [ ] **Step 2: Commit**

```bash
git add gui.py
git commit -m "feat: GUI dashboard with tray icon, scheduler, run buttons, log"
```

---

## Task 12: app.py

**Files:**
- Create: `app.py`

- [ ] **Step 1: Write `app.py`**

```python
import os
import sys

# MUST be first — startup shortcut may not preserve working directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from config import validate_config
from logger import get_logger
from gui import MainWindow

logger = get_logger(__name__)


def main() -> None:
    warnings = validate_config()
    for w in warnings:
        logger.warning(w)

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add app.py
git commit -m "feat: app entry point with chdir and dotenv"
```

---

## Task 13: install.ps1

**Files:**
- Create: `install.ps1`

- [ ] **Step 1: Write `install.ps1`**

```powershell
#Requires -Version 5.1
<#
.SYNOPSIS
    One-shot installer for Tech Pulse News.
    Run once from any PowerShell window — no admin required.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

# 1. Python version gate
$ver = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
if (-not $ver) { Write-Error "Python not found on PATH. Install Python 3.11+ and try again."; exit 1 }
if ([version]$ver -lt [version]"3.11") {
    Write-Error "Python $ver found but 3.11+ is required."
    exit 1
}
Write-Host "Python $ver OK" -ForegroundColor Green

# 2. Create venv
$Venv = Join-Path $Root "venv"
if (-not (Test-Path $Venv)) {
    Write-Host "Creating virtual environment…"
    python -m venv $Venv
}
$Pip    = Join-Path $Venv "Scripts\pip.exe"
$Python = Join-Path $Venv "Scripts\python.exe"
$Pythonw = Join-Path $Venv "Scripts\pythonw.exe"

# 3. Install dependencies
Write-Host "Installing dependencies…"
& $Pip install -r (Join-Path $Root "requirements.txt") -q

# 4. Install Playwright Chromium
Write-Host "Installing Playwright Chromium…"
& $Python -m playwright install chromium

# 5. Copy .env if missing
$EnvFile    = Join-Path $Root ".env"
$EnvExample = Join-Path $Root ".env.example"
if (-not (Test-Path $EnvFile)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host ".env created from .env.example — edit it before launching!" -ForegroundColor Yellow
} else {
    Write-Host ".env already exists — skipping copy" -ForegroundColor Cyan
}

# 6. Create logs directory
New-Item -Force -ItemType Directory (Join-Path $Root "logs") | Out-Null

# 7. Windows Startup shortcut (no admin — user's own Startup folder)
$StartupDir = [Environment]::GetFolderPath("Startup")
$LnkPath    = Join-Path $StartupDir "TechPulseNews.lnk"
$WS  = New-Object -ComObject WScript.Shell
$Lnk = $WS.CreateShortcut($LnkPath)
$Lnk.TargetPath       = $Pythonw
$Lnk.Arguments        = "`"$(Join-Path $Root 'app.py')`""
$Lnk.WorkingDirectory = $Root
$Lnk.Description      = "Tech Pulse News — local AI news agent"
$Lnk.Save()
Write-Host "Startup shortcut created: $LnkPath" -ForegroundColor Green

Write-Host ""
Write-Host "─────────────────────────────────────────" -ForegroundColor Cyan
Write-Host " Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host " Next steps:" -ForegroundColor White
Write-Host "  1. Open LM Studio → load phi-3.5-mini-instruct → Start Server"
Write-Host "  2. Edit .env:  notepad `"$EnvFile`""
Write-Host "  3. Launch now: & `"$Pythonw`" `"$(Join-Path $Root 'app.py')`""
Write-Host "─────────────────────────────────────────" -ForegroundColor Cyan
```

- [ ] **Step 2: Commit**

```bash
git add install.ps1
git commit -m "feat: install.ps1 one-shot Windows installer with startup shortcut"
```

---

## Task 14: Run full test suite

- [ ] **Step 1: Install deps into a test venv**

```bash
cd C:/Users/cusma/projects/Tech-Pulse-News
python -m venv venv
venv/Scripts/pip install -r requirements.txt -q
```

- [ ] **Step 2: Run all tests**

```bash
venv/Scripts/pytest tests/ -v
```
Expected output:
```
tests/test_config.py::test_validate_config_warns_on_placeholder_token PASSED
tests/test_config.py::test_validate_config_warns_on_empty_chat_id PASSED
tests/test_config.py::test_validate_config_returns_empty_when_valid PASSED
tests/test_categorizer.py::test_categorize_items_returns_all_categories PASSED
tests/test_categorizer.py::test_categorize_returns_empty_dict_for_no_items PASSED
tests/test_categorizer.py::test_categorize_raises_on_lm_studio_failure PASSED
tests/test_categorizer.py::test_categorize_strips_markdown_fences PASSED
tests/test_categorizer.py::test_has_high_alerts_true PASSED
tests/test_categorizer.py::test_has_high_alerts_false PASSED
tests/test_runner.py::test_run_full_sends_briefing PASSED
tests/test_runner.py::test_run_full_sends_error_message_on_categorizer_failure PASSED
tests/test_runner.py::test_run_alert_silent_when_no_alerts PASSED
tests/test_runner.py::test_run_alert_sends_when_high_alert_found PASSED
tests/test_scheduler.py::test_scheduler_converts_myt_to_local_utc_plus8 PASSED
tests/test_scheduler.py::test_scheduler_offset_est_minus5 PASSED
tests/test_scheduler.py::test_next_run_times_returns_sorted_datetimes PASSED
tests/test_scraper.py::test_fetch_feed_returns_articles PASSED
tests/test_scraper.py::test_fetch_feed_skips_old_articles PASSED
tests/test_scraper.py::test_fetch_feed_handles_failure PASSED
tests/test_scraper.py::test_fetch_all_sources_combines_results PASSED
tests/test_formatter.py::test_format_full_briefing_returns_list PASSED
tests/test_formatter.py::test_format_full_briefing_contains_header PASSED
tests/test_formatter.py::test_format_full_briefing_contains_high_alert PASSED
tests/test_formatter.py::test_format_full_briefing_contains_gaming PASSED
tests/test_formatter.py::test_format_alert_message_contains_headline PASSED
tests/test_formatter.py::test_split_message_respects_limit PASSED
tests/test_sender.py::test_send_message_posts_to_telegram PASSED
tests/test_sender.py::test_send_message_retries_on_failure PASSED
tests/test_sender.py::test_send_messages_sends_all_parts PASSED

29 passed
```

- [ ] **Step 3: Fix any failures before continuing**

If any test fails, fix the implementation until all 29 pass before moving to manual smoke test.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "test: all 29 tests passing"
```

---

## Task 15: Manual smoke test

Run these steps in order to verify the full system works end-to-end.

- [ ] **Step 1: Run install.ps1**

```powershell
cd C:\Users\cusma\projects\Tech-Pulse-News
PowerShell -ExecutionPolicy Bypass -File install.ps1
```
Expected: no errors, `.env` created, `venv/` created, startup shortcut at `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TechPulseNews.lnk`

- [ ] **Step 2: Edit `.env` with real credentials**

```
TELEGRAM_BOT_TOKEN=<real token>
TELEGRAM_CHAT_ID=<real chat id>
LM_STUDIO_HOST=http://localhost:1234
LM_STUDIO_MODEL=phi-3.5-mini-instruct
SCHEDULE_TZ=Asia/Kuala_Lumpur
```

- [ ] **Step 3: Start LM Studio, load phi-3.5-mini-instruct, start server**

Verify: `curl http://localhost:1234/v1/models` returns a model in `data[]`.

- [ ] **Step 4: Launch app**

```powershell
& "venv\Scripts\pythonw.exe" app.py
```
Expected: GUI window opens, status bar shows green LM Studio dot and model name, tray icon appears.

- [ ] **Step 5: Click "Run Full Briefing"**

Expected in log: `Starting FULL briefing run` → `Total items collected: N` → `Categorized N items` → `FULL briefing sent`
Expected in Telegram: full briefing message arrives.

- [ ] **Step 6: Click "Run Alert Scan"**

Expected in log: `Starting ALERT scan` → either `No HIGH ALERTs detected — silent run` or a HIGH ALERT Telegram message.

- [ ] **Step 7: Minimize to tray**

Click "Minimize to Tray" button. Window hides. Tray icon stays visible. Right-click tray → "Show" → window reappears.

- [ ] **Step 8: Restart PC**

Log back in. Tech Pulse News window should open automatically within 30 seconds of desktop load. No terminal window, no manual steps.

---

## Spec coverage self-review

| Requirement | Task |
|---|---|
| 100% local, no cloud APIs | Task 6 (LM Studio) |
| GUI dashboard window | Task 11 (gui.py) |
| Internal scheduler 08:00/20:00 MYT | Task 10 (scheduler.py) |
| Hourly alert scan | Task 10 |
| Auto-start on Windows login | Task 13 (install.ps1 shortcut) |
| Telegram delivery | Tasks 5, 8 |
| Bot listener (RUN NEWS / RUN ALERT) | Task 9 |
| Minimize to tray | Task 11 |
| Status indicators (LM Studio, bot) | Task 11 |
| Single `install.ps1` installer | Task 13 |
| No GitHub Actions / no Task Scheduler | N/A (scheduler.py handles it) |
| `validate_config()` warnings | Task 2 |
| Windows Chrome user-agent | Task 7 |
| All 29 tests pass | Task 14 |
