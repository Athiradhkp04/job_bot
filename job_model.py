"""
Common job data shape used by every source module.
Every source's fetch() function must return a list of these dicts,
so filter.py, dedup.py, and notify.py never need to know which
source a job came from.
"""

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query parameters that describe where a click came from rather than
# which job it points at. Everything else in the query is kept, since
# plenty of boards put the job id there ("?gh_jid=123", "?jobId=456")
# and dropping it would merge two openings at the same employer into
# one - which dedup would then treat as already sent forever.
TRACKING_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "ref",
    "referrer",
    "source",
    "src",
}


def make_job(title, company, location, employment_type, stipend,
             date_posted, link, source, apply_url=None):
    """
    Build a normalized job dict. Fields that a source can't find
    should be passed as None - downstream code handles that gracefully.

    `apply_url` is the employer-side destination a listing points at
    (an ATS page, or the aggregator the listing was syndicated from).
    Aggregators re-publish each other - FresherGo, for instance, carries
    a large share of Himalayas and Arbeitnow postings - so the same role
    reaches us under several different wrapper links. The apply URL is
    the one identifier those copies agree on, which is what makes it the
    dedup basis rather than `link`.
    """
    return {
        "title": (title or "Untitled role").strip(),
        "company": (company or "Unknown company").strip(),
        "location": (location or "Not specified").strip(),
        "employment_type": (employment_type or "Not specified").strip(),
        "stipend": (stipend or "Not disclosed").strip(),
        "date_posted": (date_posted or "Unknown").strip(),
        "link": (link or "").strip(),
        "apply_url": (apply_url or "").strip(),
        "source": source,
    }


def normalize_url(url):
    """
    Strips the parts of a URL that vary between copies of the same
    posting without changing where it points: scheme, a leading "www.",
    tracking parameters, fragments, query-parameter order, and a
    trailing slash.
    """
    if not url:
        return ""
    parts = urlsplit(url.strip())
    if not parts.netloc:
        return url.strip().lower().rstrip("/")

    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    query = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS and not key.lower().startswith("utm_")
    )

    normalized = urlunsplit(("", host, parts.path.rstrip("/"), urlencode(query), ""))
    return normalized.lstrip("/").lower()


def job_hash(job):
    """
    Stable identifier for dedup, preferring the apply URL so the same
    role syndicated through two different boards collapses to one entry.
    Falls back to the listing link (which is what sources predating
    apply_url provide, so their existing state-file hashes stay valid),
    then to title+company if there's no link at all.
    """
    basis = (
        normalize_url(job.get("apply_url"))
        or job.get("link")
        or f"{job['title']}|{job['company']}"
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()
