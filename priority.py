"""
Assigns each job a priority rank based on config.yaml's filters.role_groups
list (list order = priority order), so that when there are more matches
than fit in one Telegram message, higher-priority roles are kept and
lower-priority ones are the first to be dropped - unless a group defines
a stipend bypass (e.g. Digital Marketing jumps to top priority if it
pays above a threshold).

This reads the SAME role_groups config that filter.py uses for
inclusion/exclusion, so filtering and ordering can never drift out of
sync with each other.

Lower rank number = higher priority = shown first / kept first.
"""

from filter import parse_stipend_value, find_matching_group


def assign_rank(job, role_groups):
    stipend_value = parse_stipend_value(job.get("stipend", ""))
    matched_group = find_matching_group(job.get("title", ""), role_groups)

    if not matched_group:
        return len(role_groups)

    rank = role_groups.index(matched_group)
    bypass_threshold = matched_group.get("bypass_if_stipend_above")
    if bypass_threshold is not None and stipend_value is not None and stipend_value > bypass_threshold:
        return 0

    return rank


def sort_by_priority(jobs, config):
    role_groups = config.get("filters", {}).get("role_groups", [])
    if not role_groups:
        return jobs
    return sorted(jobs, key=lambda job: assign_rank(job, role_groups))