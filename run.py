"""
Ultimate Bot — daily BNI content → Ultimate voice → LINE chap group
Runs via GitHub Actions cron.
"""
import json
import os
import sys
from pathlib import Path

from src.fetch import fetch_new_articles
from src.rewrite import rewrite_to_ultimate_voice
from src.push import push_to_line_group

SEEN_FILE = Path("seen.json")
MAX_PER_RUN = 1  # ship 1 article per run — quality over volume


def load_seen() -> set[str]:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2, ensure_ascii=False))


def main() -> int:
    seen = load_seen()
    print(f"[info] seen={len(seen)} articles tracked")

    articles = fetch_new_articles(seen=seen, limit=MAX_PER_RUN)
    if not articles:
        print("[info] no new articles — exit clean")
        return 0

    print(f"[info] fetched {len(articles)} new article(s)")

    for article in articles:
        print(f"[info] processing: {article['title']}")
        try:
            rewritten = rewrite_to_ultimate_voice(article)
            push_to_line_group(rewritten, source_url=article["link"])
            seen.add(article["guid"])
            print(f"[ok] pushed: {article['title']}")
        except Exception as e:
            print(f"[err] failed on {article['guid']}: {e}", file=sys.stderr)
            # Don't add to seen on failure — retry next run
            continue

    save_seen(seen)
    print(f"[done] seen={len(seen)} after run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
