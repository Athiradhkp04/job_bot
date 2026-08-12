"""
Applies config.yaml filter rules to a list of normalized jobs.
Pure function - no side effects, easy to test/tweak independently.
"""

import re

STIPEND_NUMBER_RE = re.compile(r"[\d,]+")

# Experience range patterns: "0-2 years", "1-3 years", "2+ years", etc.
EXPERIENCE_RANGE_RE = re.compile(r"(\d+)\s*[-–to]\s*(\d+)\s*(years?|yrs?)", re.IGNORECASE)
EXPERIENCE_MIN_RE = re.compile(r"(\d+)\+?\s*(years?|yrs?)", re.IGNORECASE)

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


def parse_experience_requirement(job_text):
    """
    Parse experience requirement from job text (title, description, etc.).
    Returns the upper bound of the experience range in years, or None if no
    requirement is found.
    
    Examples:
    - "0-2 years" -> 2
    - "1-3 years" -> 3 (rejected since > 2)
    - "0-5 years" -> 5 (rejected since > 2)
    - "2+ years" -> 2 (acceptable)
    - "Entry-level" -> None (no numeric requirement, passes)
    - "Fresher" -> None (no numeric requirement, passes)
    """
    if not job_text:
        return None
    
    text_lower = job_text.lower()
    
    # Check for experience range patterns like "0-2 years", "1-3 years"
    range_match = EXPERIENCE_RANGE_RE.search(text_lower)
    if range_match:
        lower_bound = int(range_match.group(1))
        upper_bound = int(range_match.group(2))
        return upper_bound
    
    # Check for patterns like "2+ years", "3 years experience"
    min_match = EXPERIENCE_MIN_RE.search(text_lower)
    if min_match:
        min_years = int(min_match.group(1))
        return min_years
    
    return None


def passes_experience_filter(job):
    """
    Check if job passes the experience-level filter.
    - Jobs with no numeric experience requirement pass by default
    - Jobs with upper bound > 2 years are rejected
    - Jobs with "fresher" keyword pass regardless of numeric range
    """
    title = job.get("title", "")
    description = job.get("description", "")
    
    # Combine all text that might contain experience info
    full_text = f"{title} {description}".lower()
    
    # Check for fresher keyword - strong positive signal
    if "fresher" in full_text:
        return True
    
    # Parse experience requirement
    upper_bound = parse_experience_requirement(full_text)
    
    # No numeric requirement found - passes by default
    if upper_bound is None:
        return True
    
    # Reject if upper bound exceeds 2 years
    if upper_bound > 2:
        return False
    
    return True


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

    excluded_locations = filters.get("excluded_locations")
    if excluded_locations and _contains_any(location, excluded_locations):
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

    # Apply experience-level filtering
    if not passes_experience_filter(job):
        return False

    return True


def apply_filters(jobs, config):
    filters = config.get("filters", {})
    return [job for job in jobs if passes_filters(job, filters)]