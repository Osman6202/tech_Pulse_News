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
    all_tweets: List[Dict] = []
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
    unique = [t for t in all_tweets if not (t["url"] in seen or seen.add(t["url"]))]  # type: ignore[func-returns-value]
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
