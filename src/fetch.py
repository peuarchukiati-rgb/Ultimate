"""
Fetch new articles from source RSS feeds.
Returns list of dicts: {guid, title, link, summary, published, content}
"""
import random
import re

import feedparser

# Multiple sources rotated randomly for variety. All English-language insight
# blogs with reliable RSS, comparable article length, and audience-fit for
# Thai SME founders. To rotate the set, edit this list — fetch_new_articles
# treats them as one pool and picks the next unseen article at random.
FEEDS = [
    "https://seths.blog/feed/",
    "https://jamesclear.com/feed",
    "https://fs.blog/feed/",
]


def _strip_html(html: str) -> str:
    """Quick HTML strip — RSS summaries are short."""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _entry_to_article(entry) -> dict | None:
    guid = entry.get("id") or entry.get("link")
    if not guid:
        return None
    return {
        "guid": guid,
        "title": entry.get("title", "").strip(),
        "link": entry.get("link", "").strip(),
        "summary": _strip_html(entry.get("summary", "")),
        "published": entry.get("published", ""),
        "content": _strip_html(
            entry.get("content", [{}])[0].get("value", "")
            if entry.get("content") else entry.get("summary", "")
        ),
    }


def _fetch_all_entries() -> list:
    """Pull every configured feed, return combined entry list.

    Skips feeds that fail to parse — one bad feed doesn't break the run.
    """
    combined = []
    for feed_url in FEEDS:
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            if feed.bozo:
                print(f"[warn] feed parse failed for {feed_url}: {feed.bozo_exception}")
            continue
        combined.extend(feed.entries)
    return combined


def fetch_new_articles(seen: set[str], limit: int = 1) -> list[dict]:
    """
    Pick a random source first, then return its first unseen entry. This
    balances source rotation even when one feed has a large backlog of
    already-seen entries (and another has tons of unseen). With a flat
    "shuffle everything" approach, a backlog-heavy feed dominates output.
    """
    feeds = FEEDS.copy()
    random.shuffle(feeds)

    new = []
    for feed_url in feeds:
        if len(new) >= limit:
            break
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            if feed.bozo:
                print(f"[warn] feed parse failed for {feed_url}: {feed.bozo_exception}")
            continue
        for entry in feed.entries:
            guid = entry.get("id") or entry.get("link")
            if not guid or guid in seen:
                continue
            article = _entry_to_article(entry)
            if article:
                new.append(article)
            if len(new) >= limit:
                break
    return new


def fetch_fallback_article() -> dict | None:
    """
    Random article from any configured feed regardless of seen status.
    Used when no NEW articles exist — keeps hourly cron visible in LINE.
    """
    entries = _fetch_all_entries()
    if not entries:
        return None
    return _entry_to_article(random.choice(entries))
