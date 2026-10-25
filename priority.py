"""
Assigns each job a priority rank based on:
  1. filters.role_groups (list order = priority order) - PRIMARY sort key
  2. filters.location_priority - SECONDARY sort key within the same role
     tier, so e.g. a Kerala Data Analyst posting shows before an
     Bangalore one even though both are "core" tier.
  3. Analytical keyword boost - SMALL bonus for jobs with analytics keywords
  4. Date bonus - SMALL bonus for newer postings

This reads the SAME role_groups/location_priority config that filter.py
uses for inclusion/exclusion, so filtering and ordering can never drift
out of sync with each other.

Lower rank = higher priority = shown first / kept first when the
message cap is hit.
"""

from filter import parse_stipend_value, find_matching_group, _contains_any, _contains_word_boundary, parse_age_in_days
from datetime import datetime, timedelta


def assign_role_rank(job, role_groups, stipend_value):
    matched_group = find_matching_group(job.get("title", ""), role_groups)
    if not matched_group:
        return len(role_groups)

    rank = role_groups.index(matched_group)
    bypass_threshold = matched_group.get("bypass_if_stipend_above")
    if bypass_threshold is not None and stipend_value is not None and stipend_value > bypass_threshold:
        return 0

    return rank


def assign_location_rank(location, stipend_value, location_priority_cfg):
    default_rank = location_priority_cfg.get("default_rank", 99)

    if not location or location == "Not specified":
        return default_rank

    for tier in location_priority_cfg.get("tiers", []):
        if not _contains_any(location, tier.get("locations", [])):
            continue

        if "rank" in tier:
            return tier["rank"]

        min_stipend = tier.get("min_stipend", 0)
        clears_bar = stipend_value is not None and stipend_value > min_stipend
        rank_key = "rank_if_above" if clears_bar else "rank_if_below"
        rank = tier.get(rank_key)
        return rank if rank is not None else default_rank

    return default_rank


def assign_analytical_boost(job):
    """
    Small priority boost for jobs with analytical keywords.
    Returns a negative value (lower = higher priority) if analytics signals present.
    """
    title = job.get("title", "").lower()
    analytical_keywords = ["excel", "sql", "power bi", "tableau", "dashboard", "kpi", "reporting", "analysis", "analytics", "mis", "data"]
    
    if _contains_any(title, analytical_keywords):
        return -0.1  # Small boost for analytics keywords
    return 0


def assign_date_boost(job):
    """
    Small priority boost for newer postings.
    Returns a negative value (lower = higher priority) based on posting date.
    Newest postings get highest boost.
    """
    date_posted = job.get("date_posted", "")
    age_days = parse_age_in_days(date_posted)
    
    if age_days is None:
        return 0
    if age_days == 0:
        return -0.2  # Fresh jobs get highest boost
    elif age_days == 1:
        return -0.1  # Yesterday jobs get small boost
    else:
        return 0  # Older jobs get no boost


def assign_rank(job, config):
    filters = config.get("filters", {})
    role_groups = filters.get("role_groups", [])
    location_priority_cfg = filters.get("location_priority", {})

    stipend_value = parse_stipend_value(job.get("stipend", ""))
    role_rank = assign_role_rank(job, role_groups, stipend_value)
    location_rank = assign_location_rank(job.get("location", ""), stipend_value, location_priority_cfg)
    analytical_boost = assign_analytical_boost(job)
    date_boost = assign_date_boost(job)

    # Combine ranks: role_rank (primary), location_rank (secondary), then boosts
    # Lower values = higher priority
    return (role_rank, location_rank, analytical_boost + date_boost)


def sort_by_priority(jobs, config):
    role_groups = config.get("filters", {}).get("role_groups", [])
    if not role_groups:
        return jobs
    return sorted(jobs, key=lambda job: assign_rank(job, config))