"""
Assigns each job a priority rank based on:
  1. filters.role_groups (list order = priority order) - PRIMARY sort key
  2. filters.location_priority - SECONDARY sort key within the same role
     tier, so e.g. a Kerala Data Analyst posting shows before an
     Ahmedabad one even though both are "core" tier.

This reads the SAME role_groups/location_priority config that filter.py
uses for inclusion/exclusion, so filtering and ordering can never drift
out of sync with each other.

Lower rank = higher priority = shown first / kept first when the
message cap is hit.
"""

from filter import parse_stipend_value, find_matching_group, _contains_any


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


def assign_rank(job, config):
    filters = config.get("filters", {})
    role_groups = filters.get("role_groups", [])
    location_priority_cfg = filters.get("location_priority", {})

    stipend_value = parse_stipend_value(job.get("stipend", ""))
    role_rank = assign_role_rank(job, role_groups, stipend_value)
    location_rank = assign_location_rank(job.get("location", ""), stipend_value, location_priority_cfg)

    return (role_rank, location_rank)


def sort_by_priority(jobs, config):
    role_groups = config.get("filters", {}).get("role_groups", [])
    if not role_groups:
        return jobs
    return sorted(jobs, key=lambda job: assign_rank(job, config))