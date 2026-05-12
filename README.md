# Ultimate Bot

Daily BNI Global content → rewritten in Ultimate voice → pushed to the chap LINE group.

Runs automatically every day at 9:00 AM Bangkok time via GitHub Actions.

---

## What it does

1. Pulls the RSS feed from `bni.com/feed/` (the official BNI Global blog)
2. Finds new articles that haven't been pushed yet (tracked in `seen.json`)
3. Sends them to Gemini 2.5 Flash for rewriting — using **`UltimateEngine.md` as the source-of-truth** (the chapter's operating doc). The voice comes out as the chapter's own, not generic.
4. Pushes to the chap LINE group via the Messaging API
5. Commits `seen.json` back to the repo (state tracking)

No approval gate. If something's wrong, delete it after the fact.

> **Why UltimateEngine.md?** It's the chapter's operating document (open by design). Every rewrite pulls its voice from §2 Operating Philosophy + §10 Values → consistent + authentic. The file lives in the repo, edits stick, and the bot picks them up automatically every run.

---

## Deploy (one-time setup)

### 1. Push the repo to GitHub

```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/<your-username>/ultimate-bot.git
git push -u origin main
```

### 2. Get LINE credentials

From the [LINE Developers Console](https://developers.line.biz/console/) → your chap OA channel:

- **Channel access token** (Messaging API tab → "Issue" long-lived token)
- **Group ID** of the chap LINE group the OA belongs to

> Finding the Group ID: add the OA to the group → send a message in the group → check the webhook log or use the [LINE Webhook tester](https://developers.line.biz/console/) → you'll see `source.groupId`.

### 3. Get a Gemini API key (free, no credit card)

[aistudio.google.com](https://aistudio.google.com/apikey) → "Get API key" → "Create API key in new project"

Free tier: 1,500 req/day, 1M tokens/min. We use ~1 req/day → well under the limit.

> **Note:** Gemini's free tier uses your prompts to train Google's models. What we send is a rewrite of a public BNI blog post — no member data, no secrets. Free tier is fine.

### 4. Add secrets to the GitHub repo

Repo Settings → Secrets and variables → Actions → New repository secret:

| Name | Value |
|------|-------|
| `GEMINI_API_KEY` | AIza… |
| `LINE_CHANNEL_ACCESS_TOKEN` | (long token) |
| `LINE_CHAP_GROUP_ID` | C… |

### 5. Test manually

GitHub repo → Actions tab → "Ultimate Bot — Daily" workflow → **Run workflow** (manual trigger).

Watch the log. If everything is green → check the chap LINE group to confirm the message looks right.

### 6. Done

From step 5 onward the workflow runs every morning at 9:00 AM Bangkok time (= 02:00 UTC).

---

## Adjustments

**Change the push time:**
Edit `cron` in `.github/workflows/daily.yml` (format: `minute hour * * *`, UTC).

**Change the number of articles per run:**
Edit `MAX_PER_RUN` in `run.py` (default = 1).

**Change the voice:**
- Doctrine + values: edit `UltimateEngine.md` (the bot reads this every run).
- Operational rules (length, format): edit `VOICE_INSTRUCTIONS` in `src/rewrite.py`.

**Reset state (re-test from scratch):**
Set `seen.json` to `[]` and commit/push.

---

## Cost

- LINE Messaging API: free 500 messages/month (Communication plan). 1 push/day × 30 = 30 messages/month → well under.
- Gemini API: **free** (Google AI Studio free tier — 1,500 req/day). 1 push/day → uses 0.07% of quota.
- GitHub Actions: free (public repo) or 2000 min/month (private). 1 run = ~30 seconds × 30 days = 15 minutes/month.

**Total: $0/month — Giver's Gain doctrine intact** 🎁

---

## Architecture

```
GitHub Actions cron (daily 9am Bangkok)
    ↓
run.py → load seen.json
    ↓
src/fetch.py → bni.com/feed/ → filter unseen → return 1 article
    ↓
src/rewrite.py → Gemini 2.5 Flash (free tier) → Ultimate voice text
    ↓
src/push.py → LINE Messaging API → chap group
    ↓
run.py → save seen.json → commit + push to repo
```

---

## Next features (parked)

- Tier 2: Manual training/event reminders (cron + content file)
- Tier 3: Contextual nudges (Tue evening, Wed early morning)
- Both reuse `src/push.py` — add new schedulers when ready
