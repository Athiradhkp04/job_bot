"""
RemoteOK source module (remoteok.com/api).

A single unauthenticated JSON endpoint returning the most recent
remote postings - no key, no pagination, no scraping. The first
element of the response is RemoteOK's legal/terms object rather than a
job, so it's skipped by checking for an `id` field instead of by
position.

Their API terms ask for attribution and a link back; every job is sent
with its RemoteOK URL and the source name is shown in the WFH section
header, which satisfies that.
"""

import requests

from job_model import make_job
from sources.common import days_ago_text, format_salary, remote_location

API_URL = "https://remoteok.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-bot/1.0; +https://github.com/Athiradhkp04/job_bot)"
}


def _to_job(entry):
    salary = format_salary(
        entry.get("salary_min"),
        entry.get("salary_max"),
        currency="USD",
        period="year",
    )

    return make_job(
        title=entry.get("position"),
        company=entry.get("company"),
        location=remote_location(entry.get("location")),
        employment_type="Full-time (Remote)",
        stipend=salary,
        date_posted=days_ago_text(entry.get("date") or entry.get("epoch")),
        link=entry.get("url"),
        source="RemoteOK",
        apply_url=entry.get("apply_url") or entry.get("url"),
    )


def fetch(config):
    src_cfg = config["sources"].get("remoteok", {})
    limit = src_cfg.get("max_jobs", 200)

    resp = requests.get(API_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    entries = resp.json()

    jobs = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        try:
            jobs.append(_to_job(entry))
        except Exception as e:
            print(f"[remoteok] skipped one entry: {e}")
        if len(jobs) >= limit:
            break

    return jobs
