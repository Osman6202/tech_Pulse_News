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
