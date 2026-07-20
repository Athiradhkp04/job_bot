"""
Applies config.yaml filter rules to a list of normalized jobs.
Pure function - no side effects, easy to test/tweak independently.
"""

import re

STIPEND_NUMBER_RE = re.compile(r"[\d,]+")

AGE_PATTERNS = [
    (re.compile(r"^today$", re.IGNORECASE), 0),
    (re.compile(r"^yesterday$", re.IGNORECASE), 1),
    (re.compile(r"^few hours? ago$", re.IGNORECASE), 0),
    (re.compile(r"^(\d+)\s+hours?\s+ago$", re.IGNORECASE), "hours"),
    (re.compile(r"^few days? ago$", re.IGNORECASE), 1),
    (re.compile(r"^(\d+)\s+days?\s+ago$", re.IGNORECASE), "days"),
    (re.compile(r"^few weeks? ago$", re.IGNORECASE), 14),
    (re.compile(r"^(\d+)\s+weeks?\s+ago$", re.IGNORECASE), "weeks"),
    (re.compile(r"^(\d+)\s+months?\s+ago$", re.IGNORECASE), "months"),
]


def _contains_any(text, keywords):
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def parse_age_in_days(date_posted_str):
    if not date_posted_str:
        return None
    s = date_posted_str.strip()

    for pattern, unit in AGE_PATTERNS:
        match = pattern.match(s)
        if not match:
            continue
        if isinstance(unit, int):
            return unit
        number = int(match.group(1))
        if unit == "hours":
            return 0
        if unit == "days":
            return number
        if unit == "weeks":
            return number * 7
        if unit == "months":
            return number * 30

    return None


def parse_stipend_value(stipend_str):
    if not stipend_str:
        return None
    s = stipend_str.lower()
    if "unpaid" in s:
        return 0
    numbers = STIPEND_NUMBER_RE.findall(stipend_str)
    if not numbers:
        return None
    values = [int(n.replace(",", "")) for n in numbers]
    value = min(values)
    if re.search(r"/\s?(year|annum)", s):
        value = value / 12
    return value


def passes_location_rules(location, stipend_value, location_rules):
    if not location or location == "Not specified":
        return True

    location_lower = location.lower()

    always_allow = location_rules.get("always_allow", [])
    if _contains_any(location_lower, always_allow):
        return True

    for rule in location_rules.get("conditional", []):
        group_locations = rule.get("locations", [])
        if _contains_any(location_lower, group_locations):
            min_stipend = rule.get("min_stipend", 0)
            if stipend_value is None:
                return True
            return stipend_value > min_stipend

    return False


def find_matching_group(title, role_groups):
    """
    Returns the first role_group whose keywords match the title, or None
    if the job doesn't belong to any configured group at all.
    """
    for group in role_groups:
        if _contains_any(title, group.get("keywords", [])):
            return group
    return None


def passes_filters(job, filters):
    title = job.get("title", "")
    location = job.get("location", "")
    stipend = job.get("stipend", "")
    date_posted = job.get("date_posted", "")

    role_groups = filters.get("role_groups", [])
    matched_group = find_matching_group(title, role_groups)
    if not matched_group:
        return False

    if filters.get("exclude_keywords") and _contains_any(title, filters["exclude_keywords"]):
        return False

    if not matched_group.get("bypass_location_and_stipend", False):
        location_rules = filters.get("location_rules")
        if location_rules:
            stipend_value = parse_stipend_value(stipend)
            if not passes_location_rules(location, stipend_value, location_rules):
                return False

    max_age_days = filters.get("max_age_days")
    if max_age_days is not None:
        age_days = parse_age_in_days(date_posted)
        if age_days is not None and age_days > max_age_days:
            return False

    return True


def apply_filters(jobs, config):
    filters = config.get("filters", {})
    return [job for job in jobs if passes_filters(job, filters)]