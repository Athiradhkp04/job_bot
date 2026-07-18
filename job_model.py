"""
Common job data shape used by every source module.
Every source's fetch() function must return a list of these dicts,
so filter.py, dedup.py, and notify.py never need to know which
source a job came from.
"""

import hashlib


def make_job(title, company, location, employment_type, stipend,
             date_posted, link, source):
    """
    Build a normalized job dict. Fields that a source can't find
    should be passed as None - downstream code handles that gracefully.
    """
    return {
        "title": (title or "Untitled role").strip(),
        "company": (company or "Unknown company").strip(),
        "location": (location or "Not specified").strip(),
        "employment_type": (employment_type or "Not specified").strip(),
        "stipend": (stipend or "Not disclosed").strip(),
        "date_posted": (date_posted or "Unknown").strip(),
        "link": (link or "").strip(),
        "source": source,
    }


def job_hash(job):
    """
    Stable identifier for dedup. Based on link primarily (most unique),
    falling back to title+company if a link is somehow missing.
    """
    basis = job.get("link") or f"{job['title']}|{job['company']}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()
