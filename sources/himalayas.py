"""
Himalayas API source module.

Himalayas provides a public JSON API at himalayas.app/jobs/api with no
authentication required. Returns remote job listings from various companies.

This module fetches jobs from Himalayas and filters them for:
1. Entry-level seniority only (no Mid-level, Senior, Manager, Executive)
2. "fresher" keyword presence in title, excerpt, or description
3. Two output categories:
   - WFH/Remote: jobs with no location restrictions (purely remote)
   - South India onsite/hybrid: jobs matching configured South India locations
"""

import requests
from job_model import make_job

API_URL = "https://himalayas.app/jobs/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def _parse_age_in_days(timestamp):
    """
    Parse Himalayas Unix timestamp to days ago.
    Himalayas provides Unix timestamps in seconds.
    """
    try:
        from datetime import datetime
        posted_date = datetime.fromtimestamp(timestamp)
        now = datetime.now(posted_date.tzinfo)
        days_ago = (now - posted_date).days
        if days_ago == 0:
            return "Today"
        elif days_ago == 1:
            return "Yesterday"
        else:
            return f"{days_ago} days ago"
    except (ValueError, TypeError):
        return None


def _contains_fresher_keyword(job_data):
    """
    Check if job contains "fresher" keyword in title, excerpt, or description.
    This is a strong positive signal regardless of numeric experience ranges.
    """
    text_to_check = ""
    text_to_check += job_data.get("title", "").lower()
    text_to_check += " " + job_data.get("excerpt", "").lower()
    text_to_check += " " + job_data.get("description", "").lower()
    return "fresher" in text_to_check


def _is_entry_level(job_data):
    """
    Check if job is Entry-level seniority.
    Himalayas provides seniority as an array like ["Entry-level", "Mid-level"].
    We only accept jobs that include "Entry-level".
    """
    seniority = job_data.get("seniority", [])
    return "Entry-level" in seniority


def _matches_south_india_location(job_data, south_india_locations):
    """
    Check if job matches any configured South India location.
    locationRestrictions is an array like ["India", "Kerala"].
    We check if any restriction matches our configured South India locations.
    """
    restrictions = job_data.get("locationRestrictions", [])
    if not restrictions:
        return False  # No restrictions means WFH, not South India specific
    
    restrictions_lower = [r.lower() for r in restrictions]
    for south_loc in south_india_locations:
        if south_loc.lower() in restrictions_lower:
            return True
    return False


def _is_pure_remote(job_data):
    """
    Check if job is purely remote (no location restrictions).
    Jobs with empty locationRestrictions array are considered fully remote.
    """
    restrictions = job_data.get("locationRestrictions", [])
    return len(restrictions) == 0


def fetch(config):
    """
    Fetch jobs from Himalayas API and filter for Entry-level + fresher roles.
    Returns two lists: (wfh_jobs, south_india_jobs)
    
    Note: Himalayas API returns paginated results (default 20 per page).
    We fetch multiple pages to get more results, since Entry-level roles
    in South India may be sparse. Number of pages is configurable via max_pages.
    """
    src_cfg = config["sources"].get("himalayas", {})
    if not src_cfg.get("enabled", False):
        return [], []

    south_india_locations = src_cfg.get("south_india_locations", [])
    max_pages = src_cfg.get("max_pages", 3)  # Default to 3 pages (60 jobs)

    jobs_data = []
    
    # Fetch multiple pages to get more results
    for page in range(max_pages):
        offset = page * 20  # Himalayas uses 20 jobs per page
        try:
            url = f"{API_URL}?offset={offset}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            page_jobs = data.get("jobs", [])
            if not page_jobs:
                break
            jobs_data.extend(page_jobs)
            print(f"[himalayas] fetched {len(page_jobs)} jobs at offset {offset}")
        except requests.RequestException as e:
            print(f"[himalayas] API fetch failed at offset {offset}: {e}")
            break

    wfh_jobs = []
    south_india_jobs = []
    
    for job_data in jobs_data:
        try:
            # Filter by seniority: only Entry-level
            if not _is_entry_level(job_data):
                continue
            
            # Check for fresher keyword (strong positive signal)
            has_fresher_keyword = _contains_fresher_keyword(job_data)
            
            title = job_data.get("title", "Untitled role")
            company = job_data.get("companyName", "Unknown company")
            employment_type = job_data.get("employmentType", "Not specified")
            
            # Build location string from restrictions
            restrictions = job_data.get("locationRestrictions", [])
            if restrictions:
                location = ", ".join(restrictions)
            else:
                location = "Remote"
            
            # Build salary string
            min_salary = job_data.get("minSalary")
            max_salary = job_data.get("maxSalary")
            salary_period = job_data.get("salaryPeriod", "")
            if min_salary and max_salary:
                stipend = f"${min_salary:,} - ${max_salary:,} {salary_period}"
            elif min_salary:
                stipend = f"${min_salary:,}+ {salary_period}"
            else:
                stipend = "Not disclosed"
            
            # Parse posted time from Unix timestamp
            timestamp = job_data.get("pubDate")
            date_posted = _parse_age_in_days(timestamp) if timestamp else "Unknown"
            
            link = job_data.get("applicationLink", "")
            
            # Add fresher indicator to title if keyword found
            if has_fresher_keyword:
                title = f"{title} (Fresher)"

            job = make_job(
                title=title,
                company=company,
                location=location,
                employment_type=employment_type,
                stipend=stipend,
                date_posted=date_posted,
                link=link,
                source="Himalayas",
                description=job_data.get("description", ""),
            )
            
            # Categorize job based on location
            if _is_pure_remote(job_data):
                wfh_jobs.append(job)
            elif _matches_south_india_location(job_data, south_india_locations):
                south_india_jobs.append(job)
                
        except Exception as e:
            print(f"[himalayas] skipped one job: {e}")
            continue

    print(f"[himalayas] processed {len(jobs_data)} total jobs from API")
    print(f"[himalayas] returned {len(wfh_jobs)} WFH jobs, {len(south_india_jobs)} South India jobs")
    return wfh_jobs, south_india_jobs
