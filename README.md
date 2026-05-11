# Ultimate Bot

Daily BNI Global content → rewritten in Ultimate voice → pushed to chap LINE group.

Runs automatically every day at 9:00 AM Bangkok time via GitHub Actions.

---

## What it does

1. ดึง RSS feed จาก `bni.com/feed/` (BNI Global blog ทางการ)
2. หาบทความใหม่ที่ยังไม่เคย push (track ใน `seen.json`)
3. ส่งให้ Gemini 2.5 Flash rewrite — โดย **อ้างอิง `UltimateEngine.md` เป็น source-of-truth** (chapter's operating doc). Voice ออกมาเป็น chapter's own voice ไม่ใช่ generic.
4. Push เข้า LINE chap group ผ่าน Messaging API
5. Commit `seen.json` กลับ repo (track state)

ไม่มี approval gate. ผิดลบทีหลัง.

> **Why UltimateEngine.md?** เป็น chapter's operating document (open by design). ทุกการ rewrite ดึง voice จาก §2 Operating Philosophy + §10 Values → consistent + authentic. ตัวไฟล์ใน repo, แก้ตามจริงได้, bot pick up อัตโนมัติทุก run.

---

## Deploy (one-time setup)

### 1. Push repo to GitHub

```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/<your-username>/ultimate-bot.git
git push -u origin main
```

### 2. Get LINE credentials

จาก [LINE Developers Console](https://developers.line.biz/console/) → channel ของ chap OA:

- **Channel access token** (Messaging API tab → "Issue" long-lived token)
- **Group ID** ของ chap LINE group ที่ OA เป็นสมาชิก

> หา Group ID: เพิ่ม OA เข้า group → ส่งข้อความใน group → check webhook log หรือใช้ [LINE Webhook tester](https://developers.line.biz/console/) → จะเห็น `source.groupId`

### 3. Get Gemini API key (ฟรี ไม่ต้องบัตรเครดิต)

[aistudio.google.com](https://aistudio.google.com/apikey) → "Get API key" → "Create API key in new project"

ฟรี 1,500 req/วัน, 1M tokens/นาที. ของเราใช้แค่ 1 req/วัน → ใต้ limit เยอะ.

> **Note:** Free tier ของ Gemini ใช้ prompt ของเราไป train model ของ Google. ของที่ส่งเป็น BNI public blog rewrite — ไม่มี member data, ไม่มี secret. OK ใช้ฟรีได้.

### 4. Add secrets to GitHub repo

Repo Settings → Secrets and variables → Actions → New repository secret:

| Name | Value |
|------|-------|
| `GEMINI_API_KEY` | AIza… |
| `LINE_CHANNEL_ACCESS_TOKEN` | (long token) |
| `LINE_CHAP_GROUP_ID` | C… |

### 5. Test manually

GitHub repo → Actions tab → "Ultimate Bot — Daily" workflow → **Run workflow** (manual trigger)

ดู log. ถ้าเขียวหมด → ดูใน chap LINE group ว่าข้อความมาถูกไหม

### 6. Done

จาก step 5 ลงไป workflow จะรันเองทุกเช้า 9:00 น. ไทย (= 02:00 UTC)

---

## Adjustments

**เปลี่ยนเวลา push:**
แก้ `cron` ใน `.github/workflows/daily.yml` (format: minute hour * * *, UTC)

**เปลี่ยนจำนวนบทความต่อรอบ:**
แก้ `MAX_PER_RUN` ใน `run.py` (default = 1)

**เปลี่ยน voice:**
- ตัว doctrine + values: แก้ `UltimateEngine.md` (bot อ่านจากไฟล์นี้ทุก run)
- ตัว operational rules (ความยาว, format): แก้ `VOICE_INSTRUCTIONS` ใน `src/rewrite.py`

**Reset state (ทดสอบใหม่):**
แก้ `seen.json` ให้เป็น `[]` แล้ว commit push

---

## Cost

- LINE Messaging API: ฟรี 500 messages/เดือน (Communication plan). 1 push/วัน × 30 = 30 messages/เดือน → ใต้ limit เยอะ
- Gemini API: **ฟรี** (Google AI Studio free tier — 1,500 req/วัน). 1 push/วัน → ใช้ 0.07% ของ quota
- GitHub Actions: ฟรี (public repo) หรือ 2000 min/เดือน (private). 1 run = ~30 วินาที × 30 วัน = 15 นาที/เดือน

**Total: $0/เดือน — Giver's Gain doctrine intact** 🎁

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
