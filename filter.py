"""
Applies config.yaml filter rules to a list of normalized jobs.
Pure function - no side effects, easy to test/tweak independently.
"""

import re

STIPEND_NUMBER_RE = re.compile(r"[\d,]+")


def _contains_any(text, keywords):
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def parse_stipend_value(stipend_str):
    """
    Extracts a comparable numeric value from a stipend string.
    Returns:
      - 0 for "Unpaid"
      - the lower bound of a range (conservative - guarantees at least this much)
      - None if it can't be parsed (e.g. "Competitive stipend", "Not disclosed")
    """
    if not stipend_str:
        return None
    s = stipend_str.lower()
    if "unpaid" in s:
        return 0
    numbers = STIPEND_NUMBER_RE.findall(stipend_str)
    if not numbers:
        return None
    values = [int(n.replace(",", "")) for n in numbers]
    return min(values)


def passes_location_rules(location, stipend_value, location_rules):
    # No location data - don't over-filter on missing info
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
                # Can't verify stipend (e.g. "Competitive stipend") - benefit of the doubt
                return True
            return stipend_value > min_stipend

    # Location didn't match any allowed group at all
    return False


def passes_filters(job, filters):
    title = job.get("title", "")
    location = job.get("location", "")
    stipend = job.get("stipend", "")

    # Must match at least one desired role keyword
    if filters.get("roles") and not _contains_any(title, filters["roles"]):
        return False

    # Must NOT match any exclude keyword
    if filters.get("exclude_keywords") and _contains_any(title, filters["exclude_keywords"]):
        return False

    location_rules = filters.get("location_rules")
    if location_rules:
        stipend_value = parse_stipend_value(stipend)
        if not passes_location_rules(location, stipend_value, location_rules):
            return False

    return True


def apply_filters(jobs, config):
    filters = config.get("filters", {})
    return [job for job in jobs if passes_filters(job, filters)]