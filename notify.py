"""
Formats job list into a clean Telegram message and sends it via the
Bot API. Uses HTML parse mode for bold titles - simple, no external
Telegram library needed.
"""

import requests


def _escape_html(text):
    if not text:
        return text
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def format_message(jobs, max_jobs):
    if not jobs:
        return "😴 No new matches this run."

    shown = jobs[:max_jobs]
    lines = [f"🟢 <b>New Job Matches ({len(shown)})</b>\n"]

    for i, job in enumerate(shown, start=1):
        title = _escape_html(job["title"])
        company = _escape_html(job["company"])
        location = _escape_html(job["location"])
        employment_type = _escape_html(job["employment_type"])
        stipend = _escape_html(job["stipend"])
        date_posted = _escape_html(job["date_posted"])
        link = job["link"]

        lines.append(
            f"<b>{i}. {title} — {company}</b>\n"
            f"📍 {location} · {employment_type}\n"
            f"💰 {stipend}\n"
            f"🗓 {date_posted}\n"
            f"🔗 {link}\n"
        )

    if len(jobs) > max_jobs:
        lines.append(f"…and {len(jobs) - max_jobs} more not shown this round.")

    return "\n".join(lines)


def send_telegram_message(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[notify] failed to send Telegram message: {e}")
        print(f"[notify] response: {getattr(e.response, 'text', 'N/A')}")
        return False
