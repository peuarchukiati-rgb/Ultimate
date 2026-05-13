"""
Ultimate Bot — daily BNI content → Ultimate voice → LINE chap group
Runs via GitHub Actions cron.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from src.fetch import fetch_fallback_article, fetch_new_articles
from src.rewrite import rewrite_to_ultimate_voice
from src.push import push_to_line_group

SEEN_FILE = Path("seen.json")
STATS_FILE = Path("stats.jsonl")
MAX_PER_RUN = 1  # ship 1 article per run — quality over volume


def load_seen() -> set[str]:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2, ensure_ascii=False))


def write_stat(record: dict) -> None:
    """Append one JSON line to stats.jsonl. Each cron run produces one line —
    queryable later via jq / sqlite for run history, model fallback usage,
    source distribution, etc. without needing to scrape Actions logs."""
    line = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **record,
    }
    with STATS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def _source_of(url: str) -> str:
    """Domain name from article link, used as the source label in stats."""
    try:
        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"


def main() -> int:
    seen = load_seen()
    print(f"[info] seen={len(seen)} articles tracked")

    articles = fetch_new_articles(seen=seen, limit=MAX_PER_RUN)

    if not articles:
        # Fallback: push a random existing article so every cron run produces a
        # visible LINE message. Lets us confirm schedule reliability without
        # waiting on the source feed. Don't add to seen — it stays repostable.
        fallback = fetch_fallback_article()
        if not fallback:
            print("[info] no articles in feed — exit clean")
            write_stat({"outcome": "noop", "mode": "empty_feed"})
            return 0
        print(f"[info] no new articles — reposting: {fallback['title']}")
        try:
            rewritten, meta = rewrite_to_ultimate_voice(fallback)
            push_to_line_group(rewritten, source_url=fallback["link"])
            print(f"[ok] reposted: {fallback['title']}")
            write_stat({
                "outcome": "ok",
                "mode": "fallback",
                "source": _source_of(fallback["link"]),
                "title": fallback["title"][:100],
                "guid": fallback["guid"],
                **meta,
            })
        except Exception as e:
            print(f"[err] fallback push failed: {e}", file=sys.stderr)
            write_stat({
                "outcome": "err",
                "mode": "fallback",
                "source": _source_of(fallback["link"]),
                "title": fallback["title"][:100],
                "guid": fallback["guid"],
                "error": str(e)[:200],
            })
        return 0

    print(f"[info] fetched {len(articles)} new article(s)")

    for article in articles:
        print(f"[info] processing: {article['title']}")
        try:
            rewritten, meta = rewrite_to_ultimate_voice(article)
            push_to_line_group(rewritten, source_url=article["link"])
            seen.add(article["guid"])
            print(f"[ok] pushed: {article['title']}")
            write_stat({
                "outcome": "ok",
                "mode": "new",
                "source": _source_of(article["link"]),
                "title": article["title"][:100],
                "guid": article["guid"],
                **meta,
            })
        except Exception as e:
            print(f"[err] failed on {article['guid']}: {e}", file=sys.stderr)
            write_stat({
                "outcome": "err",
                "mode": "new",
                "source": _source_of(article["link"]),
                "title": article["title"][:100],
                "guid": article["guid"],
                "error": str(e)[:200],
            })
            # Don't add to seen on failure — retry next run
            continue

    save_seen(seen)
    print(f"[done] seen={len(seen)} after run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
