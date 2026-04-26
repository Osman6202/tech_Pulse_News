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
