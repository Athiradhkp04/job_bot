"""
Arbeitnow source module (arbeitnow.com/api/job-board-api).

Free JSON API, no key, `?page=N` pagination. Unlike the other three
APIs here, Arbeitnow is a general Europe-focused board rather than a
remote-only one, and most of its volume is on-site German-language
roles. `remote_only` therefore defaults to true - without it this
source would contribute a lot of listings that can never match, at the
cost of a slower run for nothing.
"""

import requests

from job_model import make_job
from sources.common import days_ago_text, remote_location

API_URL = "https://www.arbeitnow.com/api/job-board-api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-bot/1.0; +https://github.com/Athiradhkp04/job_bot)"
}


def _to_job(entry):
    job_types = entry.get("job_types") or []
    employment_type = ", ".join(job_types) if job_types else "Not specified"
    location = entry.get("location")

    return make_job(
        title=entry.get("title"),
        company=entry.get("company_name"),
        location=remote_location(location) if entry.get("remote") else location,
        employment_type=employment_type,
        stipend=None,
        date_posted=days_ago_text(entry.get("created_at")),
        link=entry.get("url"),
        source="Arbeitnow",
        apply_url=entry.get("url"),
    )


def fetch(config):
    src_cfg = config["sources"].get("arbeitnow", {})
    max_pages = src_cfg.get("max_pages", 2)
    remote_only = src_cfg.get("remote_only", True)

    jobs = []
    for page in range(1, max_pages + 1):
        resp = requests.get(API_URL, params={"page": page}, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        entries = payload.get("data", [])
        if not entries:
            break

        for entry in entries:
            if remote_only and not entry.get("remote"):
                continue
            try:
                jobs.append(_to_job(entry))
            except Exception as e:
                print(f"[arbeitnow] skipped one entry: {e}")

        print(f"[arbeitnow] page {page}: {len(jobs)} kept so far")

        if not payload.get("links", {}).get("next"):
            break

    return jobs
