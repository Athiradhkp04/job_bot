"""
Himalayas source module (himalayas.app/jobs/api).

Free JSON API, no key. Supports `limit` and `offset`, so this pages
through until it has the configured number of jobs or the API stops
returning full pages. The API silently caps `limit` at 20 per request
regardless of what's asked for, which is why `PAGE_SIZE` is fixed at
20 - asking for more and treating a short page as the end would stop
pagination after a single request.

Himalayas tags each posting with a `seniority` list, which is the one
place among these APIs where senior roles can be dropped before they
ever reach the title-based `exclude_keywords` filter - useful because
plenty of senior postings don't say "senior" in the title.
"""

import requests

from job_model import make_job
from sources.common import days_ago_text, format_salary, remote_location

API_URL = "https://himalayas.app/jobs/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-bot/1.0; +https://github.com/Athiradhkp04/job_bot)"
}
PAGE_SIZE = 20


def _is_too_senior(entry, excluded_seniority):
    seniority = [str(s).lower() for s in entry.get("seniority") or []]
    if not seniority:
        return False
    return all(s in excluded_seniority for s in seniority)


def _to_job(entry):
    link = entry.get("applicationLink") or entry.get("guid")

    return make_job(
        title=entry.get("title"),
        company=entry.get("companyName"),
        location=remote_location(entry.get("locationRestrictions")),
        employment_type=entry.get("employmentType") or "Not specified",
        stipend=format_salary(
            entry.get("minSalary"),
            entry.get("maxSalary"),
            currency=entry.get("currency"),
            period=entry.get("salaryPeriod"),
        ),
        date_posted=days_ago_text(entry.get("pubDate")),
        link=link,
        source="Himalayas",
        apply_url=link,
    )


def fetch(config):
    src_cfg = config["sources"].get("himalayas", {})
    limit = src_cfg.get("max_jobs", 200)
    excluded_seniority = [
        s.lower() for s in src_cfg.get("excluded_seniority", ["senior", "manager", "executive", "director"])
    ]

    jobs = []
    offset = 0

    while len(jobs) < limit:
        resp = requests.get(
            API_URL,
            params={"limit": PAGE_SIZE, "offset": offset},
            headers=HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        entries = resp.json().get("jobs", [])
        if not entries:
            break

        for entry in entries:
            if _is_too_senior(entry, excluded_seniority):
                continue
            try:
                jobs.append(_to_job(entry))
            except Exception as e:
                print(f"[himalayas] skipped one entry: {e}")

        if len(entries) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return jobs[:limit]
