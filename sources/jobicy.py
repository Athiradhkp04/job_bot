"""
Jobicy source module (jobicy.com/api/v2/remote-jobs).

Free JSON API, no key, one request per run. Supports a `count` cap and
an optional `geo` filter; `geo` is left configurable but unset by
default, since restricting to one region throws away remote roles that
are open worldwide.

Jobicy publishes a `jobLevel` per posting, so senior listings are
dropped here rather than relying on the title containing "senior".
"""

import requests

from job_model import make_job
from sources.common import days_ago_text, remote_location

API_URL = "https://jobicy.com/api/v2/remote-jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-bot/1.0; +https://github.com/Athiradhkp04/job_bot)"
}
MAX_COUNT = 50


def _to_job(entry):
    job_types = entry.get("jobType") or []
    employment_type = ", ".join(job_types) if job_types else "Not specified"

    return make_job(
        title=entry.get("jobTitle"),
        company=entry.get("companyName"),
        location=remote_location(entry.get("jobGeo")),
        employment_type=employment_type,
        stipend=None,
        date_posted=days_ago_text(entry.get("pubDate")),
        link=entry.get("url"),
        source="Jobicy",
        apply_url=entry.get("url"),
    )


def fetch(config):
    src_cfg = config["sources"].get("jobicy", {})
    count = min(src_cfg.get("max_jobs", 50), MAX_COUNT)
    excluded_levels = [s.lower() for s in src_cfg.get("excluded_levels", ["senior", "executive"])]

    params = {"count": count}
    geo = src_cfg.get("geo")
    if geo:
        params["geo"] = geo

    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    entries = resp.json().get("jobs", [])

    jobs = []
    for entry in entries:
        if str(entry.get("jobLevel", "")).lower() in excluded_levels:
            continue
        try:
            jobs.append(_to_job(entry))
        except Exception as e:
            print(f"[jobicy] skipped one entry: {e}")

    return jobs
