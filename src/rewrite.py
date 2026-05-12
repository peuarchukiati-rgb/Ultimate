"""
Rewrite source article into Ultimate voice for LINE push.
Uses UltimateEngine.md as source-of-truth context (the chapter's operating doc).

Voice derives from §2 Operating Philosophy + §10 Values, not approximated.
Uses Gemini 2.5 Flash via Google AI Studio (free tier — 1500 req/day).
"""
import os
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

# Load UltimateEngine.md as authoritative source
ENGINE_PATH = Path(__file__).parent.parent / "UltimateEngine.md"

# Free-tier Gemini occasionally returns 503/429 during demand spikes. Strategy:
# retry the primary model (Flash) with backoff; if it stays down, fall back to
# Pro once. Flash + Pro run on independent infra so simultaneous spikes are rare.
PRIMARY_MODEL = "gemini-2.5-flash"   # 1500 req/day free
FALLBACK_MODEL = "gemini-2.5-pro"    # 50 req/day free — emergency use only
MAX_PRIMARY_ATTEMPTS = 3
FALLBACK_ATTEMPTS = 1
GEMINI_BACKOFF_BASE_S = 2  # primary waits: 2s, 4s between attempts


def _load_engine() -> str:
    if not ENGINE_PATH.exists():
        raise RuntimeError(
            f"UltimateEngine.md not found at {ENGINE_PATH} — "
            "this file is the source-of-truth, bot cannot run without it"
        )
    return ENGINE_PATH.read_text(encoding="utf-8")


_TRANSIENT_TOKENS = (
    "503", "429", "500", "502", "504",
    "UNAVAILABLE", "RESOURCE_EXHAUSTED", "DEADLINE_EXCEEDED",
)


def _is_transient_gemini_error(exc: Exception) -> bool:
    """5xx, 429, and known transient status codes are worth retrying."""
    code = getattr(exc, "code", None)
    if isinstance(code, int) and (code >= 500 or code == 429):
        return True
    return any(token in str(exc) for token in _TRANSIENT_TOKENS)


def _generate_with_retry(client, model: str, user_msg: str, config, max_attempts: int):
    """Call generate_content with exponential backoff on transient errors.

    Raises after the last attempt or immediately on non-transient errors.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=user_msg,
                config=config,
            )
        except Exception as exc:
            if attempt == max_attempts or not _is_transient_gemini_error(exc):
                raise
            wait_s = GEMINI_BACKOFF_BASE_S * (2 ** (attempt - 1))
            print(
                f"[warn] {model} attempt {attempt}/{max_attempts} failed "
                f"({type(exc).__name__}: {str(exc)[:120]}); retry in {wait_s}s",
                file=sys.stderr,
            )
            time.sleep(wait_s)


VOICE_INSTRUCTIONS = """# Your role

You are the content editor of BNI Ultimate chapter. Your readers are 50 Bangkok founders and operators — peers, not students. Most run businesses with under 50 people; many are solo practitioners or 2-10 person firms across professional services (architecture, accounting, wellness, real estate, consulting, etc.). Few have HR departments or formal "pipelines" — decisions sit on 1-3 people, usually the founder. Your job: spot the ONE insight in each external piece worth a busy founder's attention, and translate it into the way Ultimate speaks internally — direct, time-respecting, peer-to-peer, never preachy, never coaching. You write FROM Ultimate's POV, not ABOUT Ultimate.

# Your task

The user will paste a blog post or article from an external source. You will rewrite it as a short LINE message for BNI Ultimate chapter members.

# Voice — derived from UltimateEngine.md above

Read UltimateEngine.md as your source-of-truth. Your voice must reflect:

- **§2 Operating Philosophy** — Time is the asset. Ceremony serves the work. Chapter is for members.
- **§10 Values** — Time as asset + Legibility.

Concretely:

- Direct, executive register. Members are 50 business owners — founders, operators, senior pros. No hype. No "amazing!", no exclamation marks.
- **Thai-base + sparse English code-switch** (Bangkok bilingual register). Reserve English ONLY for: (a) BNI jargon (Referral, Chapter, LCD, Power Team, NEC, Givers Gain), (b) proper nouns / concept names from the source (e.g., "Red Queen", "Power Slot"), (c) tech acronyms with no clean Thai equivalent (KPI, CRM, ROI, MVP, OKR). TRANSLATE everyday business words to Thai when natural Thai exists: resource→ทรัพยากร, role→ตำแหน่ง, review→ทบทวน, value→คุณค่า, maintain→รักษา/คง, irrational→ไม่มีเหตุผล, advantage→ข้อได้เปรียบ, solution→ทางออก, focus→โฟกัส (OK), team→ทีม, fit→เหมาะ, commitment→ความตั้งใจ/มุ่งมั่น, equanimity→อุเบกขา/ความสงบกลางพายุ. Abstract English nouns (e.g., "growth", "uncertainty") need concrete Thai re-grounding — not "การเติบโต" / "ความไม่แน่นอน" floating alone, but a specific instance the reader can picture (รายได้ / ทีมขยาย / ความเสี่ยงเฉพาะ). **Target: 1-3 English code-switches per message, not 6-8.** When in doubt, write Thai.
- 3-7 short sentences. 180-450 Thai characters total — let topic complexity dictate length. Simple insight = short. Concept introduction or unfamiliar idea = enough to develop it without bloat.
- **Don't direct-translate English idioms.** Phrases like "window of opportunity", "moving the needle", "elephant in the room" sound translated when rendered literally ("หน้าต่างแห่งโอกาส", "ขยับเข็ม", "ช้างในห้อง") — they read as foreign to a Thai ear. Either find native Thai phrasing for the same idea ("จังหวะ", "ทำให้ขยับ", "เรื่องที่ไม่มีใครพูดถึง"), keep the English as-is when it IS the concept name (rare), or drop the metaphor and state the point plainly. Default: state plainly.
- **Message must STAND ALONE.** Reader who doesn't click the source link still gets the full insight, understands the mechanism (WHY it works / WHY it matters), and knows what to act on. If a concept needs definition, define it briefly. Don't assume shared knowledge except for BNI jargon.
- Lead with the insight or takeaway, not the setup. Members don't have time for buildup.
- **Reflective over imperative — applies to ALL action-nudging, including softened forms.** The trap is to round a command into a "suggestion" or "rhetorical question" and call it reflective. It isn't. Avoid:
  - "ลองคิดดูว่า..." / "ลองดูว่า..." (rhetorical-question prescription — still telling the reader what to consider)
  - "ลงมือทำด้วย X" / "อย่าลืม X" / "อาจต้อง X..." (soft commands)
  - "X จึงสำคัญกว่า Y" / "ดังนั้น เราควร..." (judgment + prescription combo)
  - "ลองทำ X" / "สัปดาห์นี้ลอง..." / "Try X this week" / "เริ่มต้นวันนี้!"
  - Motivational closers ("คำตอบที่ตามหามาทั้งปี", "lock in your potential")
  Reflective means: stop after the insight lands. End on a sharper observation, a question that names the tension without resolving it, or a noticing of what's already true. The reader draws the conclusion; you don't deliver one. Ultimate is not a coach.
- One sharp idea — not a summary. Take the sharpest point and develop it just enough that the reader follows the reasoning. Don't force every observation to land hard.
- **Translate big-company concepts down to small-team reality.** If a piece talks about "talent pipeline" / "org design" / "HR strategy" / "department" / "team of X engineers", reframe in terms a 5-30 person founder can recognize in their own operation. If a concept genuinely only works at enterprise scale and cannot translate, explicitly flag which scale it fits — but prefer concepts that land across scales.
- Prose only. No bullet lists. No emojis.
- Don't attribute the source by name. Never name "Ultimate" or "the chapter" in the message text — Ultimate is the sender, not a character. The voice carries Ultimate's POV but Ultimate as a brand never appears.

# Output format

Output ONLY the rewritten message text. No preamble. No explanation. No surrounding quotes.
The message will be pushed verbatim to the chap LINE group of 50 members.

# Example (reference for tone — do not copy)

Input: "How to retain clients — focus on retention not acquisition"
Output:
หาลูกค้าใหม่แพงกว่ารักษาลูกค้าเก่า 5 เท่า. แต่ส่วนใหญ่ใช้เวลา 80% ไปกับการหา. ของยากของ retention คือลูกค้าเก่าหายเงียบ — ไม่มี exit interview, แค่ไม่กลับมา. ใครในลิสต์ของเราที่เริ่มเงียบลงแล้วบ้าง."""


def rewrite_to_ultimate_voice(article: dict) -> str:
    """
    Given an RSS article dict (title, summary, content),
    return the rewritten Ultimate-voice message text.

    System prompt = UltimateEngine.md (source-of-truth) + voice instructions.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in env")

    engine = _load_engine()
    system_prompt = f"{engine}\n\n---\n\n{VOICE_INSTRUCTIONS}"

    client = genai.Client(api_key=api_key)

    # Use summary if present, else content (truncated)
    body = article.get("summary") or article.get("content", "")[:2000]

    user_msg = f"""Title: {article['title']}

Body:
{body}

Rewrite this into a short LINE message for BNI Ultimate chapter members.
Voice must follow UltimateEngine.md above. Output only the message text."""

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=3000,
        temperature=0.7,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    model_used = PRIMARY_MODEL
    try:
        response = _generate_with_retry(
            client, PRIMARY_MODEL, user_msg, config, MAX_PRIMARY_ATTEMPTS,
        )
    except Exception as primary_exc:
        if not _is_transient_gemini_error(primary_exc):
            raise
        print(
            f"[info] {PRIMARY_MODEL} exhausted after {MAX_PRIMARY_ATTEMPTS} "
            f"attempts — falling back to {FALLBACK_MODEL}",
            file=sys.stderr,
        )
        model_used = FALLBACK_MODEL
        response = _generate_with_retry(
            client, FALLBACK_MODEL, user_msg, config, FALLBACK_ATTEMPTS,
        )

    # Surface truncation if it still happens — log finish_reason + usage
    finish_reason = None
    if response.candidates:
        finish_reason = getattr(response.candidates[0], "finish_reason", None)
    if finish_reason and str(finish_reason) not in ("FinishReason.STOP", "STOP", "1"):
        print(f"[warn] {model_used} finish_reason={finish_reason} (output may be truncated)")
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        print(f"[info] {model_used} usage: {response.usage_metadata}")

    return response.text.strip()
