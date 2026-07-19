"""
Assigns each job a priority rank based on config.yaml's priority tiers,
so that when there are more matches than fit in one Telegram message,
the most important roles (Data Analytics/Business Analytics/BI) are
kept and lower-priority ones (Digital Marketing) are the first to be
dropped - unless a tier defines a stipend bypass (e.g. Digital
Marketing jumps to top priority if it pays above a threshold).

Lower rank number = higher priority = shown first / kept first.
Jobs that don't match any configured tier get the lowest priority
(sorted last) rather than being dropped, since the role filter
upstream already ensures they're relevant to some degree.
"""

from filter import parse_stipend_value


def _matches_tier(title_lower, tier):
    keywords = tier.get("keywords", [])
    return any(kw.lower() in title_lower for kw in keywords)


def assign_rank(job, tiers):
    title_lower = job.get("title", "").lower()
    stipend_value = parse_stipend_value(job.get("stipend", ""))

    for rank, tier in enumerate(tiers):
        if _matches_tier(title_lower, tier):
            bypass_threshold = tier.get("bypass_if_stipend_above")
            if bypass_threshold is not None and stipend_value is not None and stipend_value > bypass_threshold:
                return 0  # bypass - treat as top priority
            return rank

    return len(tiers)


def sort_by_priority(jobs, config):
    tiers = config.get("priority", {}).get("tiers", [])
    if not tiers:
        return jobs
    return sorted(jobs, key=lambda job: assign_rank(job, tiers))