"""
Helpers shared by the API-backed sources (FresherGo and the four
remote-job APIs).

The HTML scrapers read human-written text like "3 days ago" and
"₹ 10,000 /month" straight off the page. APIs give timestamps and
numeric salary fields instead, so each of them would otherwise
re-invent the same two conversions back into the wording the rest of
the pipeline already parses. That's what lives here.
"""

from datetime import datetime, timezone

SALARY_PERIODS = {
    "annual": "/year",
    "annually": "/year",
    "yearly": "/year",
    "year": "/year",
    "monthly": "/month",
    "month": "/month",
    "weekly": "/week",
    "hourly": "/hour",
    "hour": "/hour",
}


def days_ago_text(posted):
    """
    Renders a posting time as the relative wording `filter.parse_age_in_days`
    understands, so no API source needs its own age handling. Accepts a
    Unix timestamp or an ISO 8601 string.
    """
    if posted is None or posted == "":
        return None

    if isinstance(posted, (int, float)):
        try:
            posted_dt = datetime.fromtimestamp(posted, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        try:
            posted_dt = datetime.fromisoformat(str(posted).strip().replace("Z", "+00:00"))
        except ValueError:
            return None

    if posted_dt.tzinfo is None:
        posted_dt = posted_dt.replace(tzinfo=timezone.utc)

    days = (datetime.now(timezone.utc) - posted_dt).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    return f"{days} days ago"


def format_salary(low, high, currency=None, period=None):
    """
    Builds the salary string shown in Telegram. The currency stays in
    the text on purpose - `filter.parse_stipend_value` reads it to
    decide whether the Rs/month thresholds apply to this figure.
    """
    low = low or None
    high = high or None
    if low is None and high is None:
        return None

    period_text = SALARY_PERIODS.get((period or "").lower(), "")
    if low is not None and high is not None and high != low:
        amount = f"{low:,} - {high:,}"
    else:
        amount = f"{(low if low is not None else high):,}"

    return " ".join(part for part in ((currency or "").strip(), amount, period_text) if part)


def remote_location(*details):
    """
    Everything from the remote-job APIs is remote by definition, so the
    location is prefixed rather than replaced: "Remote" is what
    `location_rules.always_allow` matches on and what marks a job for
    the WFH section, while the geography behind it stays visible (and
    still subject to `excluded_locations`).
    """
    parts = []
    for detail in details:
        if isinstance(detail, (list, tuple)):
            parts.extend(str(d).strip() for d in detail if d)
        elif detail:
            parts.append(str(detail).strip())

    unique = [p for i, p in enumerate(parts) if p and p not in parts[:i]]
    where = ", ".join(unique)
    if not where or where.lower() in ("remote", "anywhere", "worldwide"):
        return "Remote"
    return f"Remote · {where}"
