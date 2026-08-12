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


def _format_job_list(jobs, max_jobs):
    shown = jobs[:max_jobs]
    lines = []

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

    return lines


def format_message(jobs, max_jobs, wfh_jobs=None):
    """
    Format message with two sections:
    - Onsite/Hybrid (Internshala + Himalayas South India)
    - WFH/Remote (Himalayas purely remote)
    """
    if not jobs and not wfh_jobs:
        return "😴 No new matches this run."

    lines = []
    
    # Add Onsite/Hybrid section if there are onsite/hybrid jobs
    if jobs:
        shown = jobs[:max_jobs]
        header = f"� <b>Onsite/Hybrid Jobs ({len(shown)})</b>\n"
        lines.append(header)
        lines.extend(_format_job_list(jobs, max_jobs))
        lines.append("")  # Empty line separator
    
    # Add WFH/Remote section if there are WFH jobs
    if wfh_jobs:
        wfh_shown = wfh_jobs[:max_jobs]
        wfh_header = f"🌍 <b>WFH/Remote Jobs ({len(wfh_shown)})</b>\n"
        lines.append(wfh_header)
        lines.extend(_format_job_list(wfh_jobs, max_jobs))
    
    return "\n".join(lines)


def format_digest_message(jobs, max_jobs, days_quiet, wfh_jobs=None):
    """
    Full-refresh digest: sent when nothing NEW has come through for a
    while, so this shows everything CURRENTLY matching the filters
    (ignoring dedup) as a "here's what's still live" check-in, rather
    than leaving the person wondering if the bot is still working.
    
    Uses the same two-section structure as format_message.
    """
    if not jobs and not wfh_jobs:
        return (
            f"📋 <b>Refresh check-in</b>\n\n"
            f"No new matches for {days_quiet} days, and nothing currently "
            f"matches your filters either. Bot's still running fine - just a quiet stretch."
        )

    lines = []
    
    # Add Onsite/Hybrid section if there are onsite/hybrid jobs
    if jobs:
        shown = jobs[:max_jobs]
        header = (
            f"🏢 <b>Onsite/Hybrid Jobs — Currently Live ({len(shown)})</b>\n"
            f"No new postings for {days_quiet} days, so here's everything still "
            f"matching your filters right now (may include jobs you've seen before):\n"
        )
        lines.append(header)
        lines.extend(_format_job_list(jobs, max_jobs))
        lines.append("")  # Empty line separator
    
    # Add WFH/Remote section if there are WFH jobs
    if wfh_jobs:
        wfh_shown = wfh_jobs[:max_jobs]
        wfh_header = f"🌍 <b>WFH/Remote Jobs — Currently Live ({len(wfh_shown)})</b>\n"
        lines.append(wfh_header)
        lines.extend(_format_job_list(wfh_jobs, max_jobs))
    
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