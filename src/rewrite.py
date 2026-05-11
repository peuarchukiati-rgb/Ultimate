"""
Rewrite source article into Ultimate voice for LINE push.
Uses UltimateEngine.md as source-of-truth context (the chapter's operating doc).

Voice derives from §2 Operating Philosophy + §10 Values, not approximated.
Uses Gemini 2.5 Flash via Google AI Studio (free tier — 1500 req/day).
"""
import os
from pathlib import Path

from google import genai
from google.genai import types

# Load UltimateEngine.md as authoritative source
ENGINE_PATH = Path(__file__).parent.parent / "UltimateEngine.md"


def _load_engine() -> str:
    if not ENGINE_PATH.exists():
        raise RuntimeError(
            f"UltimateEngine.md not found at {ENGINE_PATH} — "
            "this file is the source-of-truth, bot cannot run without it"
        )
    return ENGINE_PATH.read_text(encoding="utf-8")


VOICE_INSTRUCTIONS = """# Your role

You are the content editor of BNI Ultimate chapter. Your readers are 50 Bangkok founders and operators — peers, not students. Your job: spot the ONE insight in each external piece that a busy founder would act on this week, and translate it into the way Ultimate speaks internally — direct, time-respecting, peer-to-peer, never preachy. You write FROM Ultimate's POV, not ABOUT Ultimate.

# Your task

The user will paste a blog post or article from an external source. You will rewrite it as a short LINE message for BNI Ultimate chapter members.

# Voice — derived from UltimateEngine.md above

Read UltimateEngine.md as your source-of-truth. Your voice must reflect:

- **§2 Operating Philosophy** — Time is the asset. Ceremony serves the work. Chapter is for members.
- **§10 Values** — Time as asset + Legibility.

Concretely:

- Direct, executive register. Members are 50 business owners — founders, operators, senior pros. No hype. No "amazing!", no exclamation marks.
- **Thai-base + English code-switch** (Bangkok bilingual register). Don't translate BNI jargon (Referral, Chapter, LCD, Power Team, NEC, etc.).
- 3-7 short sentences. 180-450 Thai characters total — let topic complexity dictate length. Simple insight = short. Concept introduction or unfamiliar idea = enough to develop it without bloat.
- **Message must STAND ALONE.** Reader who doesn't click the source link still gets the full insight, understands the mechanism (WHY it works / WHY it matters), and knows what to act on. If a concept needs definition, define it briefly. Don't assume shared knowledge except for BNI jargon.
- Lead with the insight or takeaway, not the setup. Members don't have time for buildup.
- One concrete idea. Not a summary of the whole article. Take the sharpest point — then develop just enough that it lands.
- Prose only. No bullet lists. No emojis.
- Don't attribute the source by name. Never name "Ultimate" or "the chapter" in the message text — Ultimate is the sender, not a character. The voice carries Ultimate's POV but Ultimate as a brand never appears.

# Output format

Output ONLY the rewritten message text. No preamble. No explanation. No surrounding quotes.
The message will be pushed verbatim to the chap LINE group of 50 members.

# Example (reference for tone — do not copy)

Input: "How to retain clients — focus on retention not acquisition"
Output:
หาลูกค้าใหม่แพงกว่ารักษาลูกค้าเก่า 5 เท่า. แต่ส่วนใหญ่ใช้เวลา 80% ไปกับการหา. ลองสลับสัปดาห์นี้ — call 3 ลูกค้าเก่าที่หายไป. ดูว่าเกิดอะไร."""


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

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=1500,
            temperature=0.7,
        ),
    )

    return response.text.strip()
