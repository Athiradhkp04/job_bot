"""
Tracks the last date a Telegram message containing actual jobs (either
a normal "new matches" message or a full-refresh digest) was sent.
Used to trigger the digest feature: if N consecutive days pass with
nothing but "no new matches" runs, send a full snapshot of everything
currently matching the filters instead of staying silent.

Separate from dedup.py's seen_jobs.json, which tracks individual job
hashes rather than send history - different purpose, different file.
"""

import json
import os
from datetime import datetime


def load_last_send_date(state_file):
    if not os.path.exists(state_file):
        return None
    try:
        with open(state_file, "r") as f:
            data = json.load(f)
            return data.get("last_send_date")
    except (json.JSONDecodeError, OSError):
        return None


def record_send(state_file, date_str=None):
    date_str = date_str or datetime.utcnow().strftime("%Y-%m-%d")
    with open(state_file, "w") as f:
        json.dump({"last_send_date": date_str}, f, indent=2)


def days_since_last_send(state_file):
    """
    Returns the number of days since the last recorded send, or None if
    there's no record yet (e.g. first-ever run) - callers should treat
    None as "eligible immediately" since there's no baseline to compare.
    """
    last_send_date = load_last_send_date(state_file)
    if not last_send_date:
        return None
    try:
        last_date = datetime.strptime(last_send_date, "%Y-%m-%d")
        return (datetime.utcnow() - last_date).days
    except ValueError:
        return None