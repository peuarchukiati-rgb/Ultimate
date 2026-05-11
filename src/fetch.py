"""
Fetch new articles from bni.com RSS feed.
Returns list of dicts: {guid, title, link, summary, published, content}
"""
import re
from typing import Iterable

import feedparser

FEED_URL = "https://www.bni.com/feed/"


def _strip_html(html: str) -> str:
    """Quick HTML strip — RSS summaries are short."""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_new_articles(seen: set[str], limit: int = 1) -> list[dict]:
    """
    Pull RSS feed, return up-to-limit articles not in seen set.
    Newest first.
    """
    feed = feedparser.parse(FEED_URL)

    # Only fail if no entries AND bozo error — minor parse warnings are common
    if not feed.entries:
        if feed.bozo:
            raise RuntimeError(f"feed parse failed: {feed.bozo_exception}")
        # Empty feed (no new posts) is valid — return empty list below

    new = []
    for entry in feed.entries:
        guid = entry.get("id") or entry.get("link")
        if not guid or guid in seen:
            continue

        new.append({
            "guid": guid,
            "title": entry.get("title", "").strip(),
            "link": entry.get("link", "").strip(),
            "summary": _strip_html(entry.get("summary", "")),
            "published": entry.get("published", ""),
            "content": _strip_html(
                entry.get("content", [{}])[0].get("value", "")
                if entry.get("content") else entry.get("summary", "")
            ),
        })

        if len(new) >= limit:
            break

    return new
