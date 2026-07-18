"""
Applies config.yaml filter rules to a list of normalized jobs.
Pure function - no side effects, easy to test/tweak independently.
"""


def _contains_any(text, keywords):
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def passes_filters(job, filters):
    title = job.get("title", "")
    location = job.get("location", "")
    employment_type = job.get("employment_type", "")

    # Must match at least one desired role keyword
    if filters.get("roles") and not _contains_any(title, filters["roles"]):
        return False

    # Must NOT match any exclude keyword
    if filters.get("exclude_keywords") and _contains_any(title, filters["exclude_keywords"]):
        return False

    # Location: accept if any configured location substring matches,
    # OR if location is unknown (don't over-filter on missing data)
    allowed_locations = filters.get("locations")
    if allowed_locations and location and location != "Not specified":
        if not _contains_any(location, allowed_locations):
            return False

    return True


def apply_filters(jobs, config):
    filters = config.get("filters", {})
    return [job for job in jobs if passes_filters(job, filters)]
