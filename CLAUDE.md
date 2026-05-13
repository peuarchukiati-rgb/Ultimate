# CLAUDE.md

Project-level context for Claude Code sessions. Keep this short; the codebase is small enough that reading it is fast.

## What this is

A scheduled job that picks one new article at random from a curated set of business-insight RSS feeds (currently Seth Godin, James Clear, Farnam Street — see `FEEDS` in `src/fetch.py`), rewrites it in the chap's voice via Gemini, and pushes to the BNI Ultimate chap LINE group. Public repo, intentionally open.

## Architecture

```
cron-job.org  ──POST workflow_dispatch──▶  GitHub Actions  ──▶  run.py
                                                                  │
                            fetch RSS ──▶ filter seen ──▶ rewrite ──▶ LINE push
                                                              │
                                                       commit seen.json
```

Key files: `run.py` (orchestrator) · `src/fetch.py` · `src/rewrite.py` · `src/push.py` · `UltimateEngine.md` (voice source-of-truth, loaded into the Gemini system prompt every run) · `.github/workflows/daily.yml`.

## Scheduling lives outside this repo

**The cron schedule is in cron-job.org, not in `daily.yml`.** GitHub Actions' free-tier `schedule` trigger dropped ~8/9 hourly runs during testing, so we removed it and let an external scheduler hit `POST /repos/{owner}/{repo}/actions/workflows/daily.yml/dispatches`. The workflow has only `workflow_dispatch:` — to change cadence, edit the cronjob in cron-job.org. To re-enable GH's own schedule, accept the unreliability.

Credentials path: cron-job.org holds a fine-grained PAT (Actions: Read+Write on this repo only). PAT rotation is on the operator's calendar; if dispatches start returning 401, the PAT expired.

## Thai content in source files is intentional

Do not "translate" these:
- `src/rewrite.py` `VOICE_INSTRUCTIONS` — Gemini prompt that defines the bot's Thai output voice; English examples are deliberate code-switch references.
- `src/push.py` LINE footer (`— อ่านต้นฉบับ:`) — appears in messages to the Thai chap audience.

System-level docs (README.md, this file, commit messages, PR bodies) are English.

## Fallback behavior

When `fetch_new_articles` returns empty, `run.py` calls `fetch_fallback_article()` and pushes a random existing RSS entry (any source) **without** updating `seen.json` — so the entry stays repostable and we can observe cron firings even on days when no source has posted anything new. The bot is therefore not idempotent: running it twice within the same hour will push twice. This is why scheduling is single-sourced (cron-job.org only).

## LINE quota awareness

Free tier = 500 push messages/month. Hourly cron = ~720/month → over budget if sustained. Hourly is intentionally a verification window; once reliability is confirmed, drop the cron-job.org cadence to 2x/day or 2x/week.

## Local debugging

Bot can run locally with the three env vars set (`GEMINI_API_KEY`, `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHAP_GROUP_ID`):

```bash
GEMINI_API_KEY=... LINE_CHANNEL_ACCESS_TOKEN=... LINE_CHAP_GROUP_ID=... python run.py
```

Manual remote trigger (uses gh CLI's stored token, no PAT needed):
```bash
gh workflow run daily.yml --repo peuarchukiati-rgb/Ultimate
gh run watch --repo peuarchukiati-rgb/Ultimate
```

## Stats (`stats.jsonl`)

Every cron run appends one JSON line to `stats.jsonl` (committed alongside `seen.json`). Schema:

```json
{"ts":"2026-05-13T04:00:00Z","outcome":"ok","mode":"new","source":"fs.blog","title":"...","guid":"...","model":"gemini-2.5-flash","primary_attempts":1,"used_fallback_model":false}
```

Fields: `outcome` ∈ {ok, err, noop}, `mode` ∈ {new, fallback, empty_feed}, `model` ∈ {gemini-2.5-flash, gemini-2.5-flash-lite}.

Query without leaving the terminal — no Supabase, no Actions log scraping:

```bash
# How many runs used Pro fallback?
jq -r 'select(.used_fallback_model)' stats.jsonl | wc -l

# Source distribution over last 24 runs
tail -24 stats.jsonl | jq -r .source | sort | uniq -c

# Show all error runs
jq -r 'select(.outcome=="err") | "\(.ts) \(.error)"' stats.jsonl

# Success rate
echo "$(jq -r 'select(.outcome=="ok")' stats.jsonl | wc -l) / $(wc -l < stats.jsonl)"
```

Want SQL? Pipe into sqlite:
```bash
sqlite-utils insert stats.db runs stats.jsonl --nl  # one-time
sqlite-utils stats.db "SELECT model, COUNT(*) FROM runs GROUP BY model"
```

## Common pitfalls

- **"Cron isn't firing"** — check cron-job.org execution history first, not GitHub. GitHub only sees what cron-job.org dispatches.
- **HTTP 401 in cron-job.org logs** — PAT expired or revoked. Rotate via GitHub Settings → Developer settings → Fine-grained tokens.
- **HTTP 204 in cron-job.org but no Actions run** — workflow file on `main` is broken or the `ref` in the dispatch body points to a missing branch.
- **Actions green but no LINE message** — check the `Run bot` step log; usually LINE token expired or group ID changed.
- **`chore: update seen articles` commit absent** — means no new article *and* fallback ran (fallback doesn't touch seen.json). Not a bug.

## Voice work

Voice spec lives in two places by design: `UltimateEngine.md` (chapter doctrine — edit when the chapter's stance changes) and `VOICE_INSTRUCTIONS` in `src/rewrite.py` (operational rules — edit when message format/length/register needs tuning). Both are loaded as the Gemini system prompt every run.

When iterating on voice, the typical loop is: edit prompt → commit → `gh workflow run` → read LINE output → repeat. `seen.json` may need to be reset (`echo '[]' > seen.json && git commit`) to re-pull articles for re-testing.
