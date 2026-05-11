"""
Push rewritten message to LINE chap group via Messaging API.
"""
import os

import requests

LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"


def push_to_line_group(message: str, source_url: str = "") -> None:
    """
    Push a text message to the configured chap group.
    Source URL appended as small footer line if provided.
    """
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    group_id = os.environ.get("LINE_CHAP_GROUP_ID")

    if not token:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN not set")
    if not group_id:
        raise RuntimeError("LINE_CHAP_GROUP_ID not set")

    # Build full message with optional source footer
    if source_url:
        full_text = f"{message}\n\n— อ่านต้นฉบับ: {source_url}"
    else:
        full_text = message

    payload = {
        "to": group_id,
        "messages": [
            {"type": "text", "text": full_text}
        ],
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        LINE_PUSH_ENDPOINT,
        json=payload,
        headers=headers,
        timeout=15,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"LINE push failed [{response.status_code}]: {response.text}"
        )

    print(f"[ok] LINE push: {response.status_code}")
