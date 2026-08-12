"""
Technopark / Infopark source module.

NOTE: I could not verify the live HTML structure of these sites from
this environment (their domains aren't reachable from here to test
against). The selectors below are a best-effort starting point based
on typical listing-page patterns - you WILL likely need to inspect
the actual page (right-click -> Inspect on a job card) and adjust the
CSS selectors before this reliably returns results. Treat this as a
scaffold, not a finished scraper.

Technopark's official listings (if centralized) typically live under
a "careers" or "jobs" section of technopark.org. Infopark similarly
under infopark.in. If neither park publishes a centralized feed,
this module may need to loop over individual company pages instead -
that's a bigger change, flag it if the single-page approach turns up
nothing.
"""

import requests
from bs4 import BeautifulSoup
from job_model import make_job

TECHNOPARK_URL = "https://technopark.org/job-openings"
INFOPARK_URL = "https://infopark.in/companies/job-openings"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def _fetch_page(url, park_name):
    jobs = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[{park_name}] fetch failed: {e}")
        return jobs

    soup = BeautifulSoup(resp.text, "html.parser")
    # Generic fallback: look for common job-card patterns.
    # ADJUST THIS once you've inspected the real page structure.
    cards = soup.select("div.job-listing, div.job-card, tr.job-row, li.job-item")

    for card in cards:
        try:
            title_el = card.select_one("h3, h4, a.job-title, td.title")
            company_el = card.select_one(".company, .company-name, td.company")
            location_el = card.select_one(".location, td.location")
            link_el = card.select_one("a")

            title = title_el.get_text(strip=True) if title_el else None
            company = company_el.get_text(strip=True) if company_el else None
            location_text = location_el.get_text(strip=True) if location_el else park_name
            link = link_el["href"] if link_el and link_el.has_attr("href") else None
            if link and link.startswith("/"):
                base = "https://technopark.org" if "technopark" in park_name.lower() else "https://infopark.in"
                link = base + link

            if not title:
                continue

            jobs.append(make_job(
                title=title,
                company=company,
                location=location_text,
                employment_type="Not specified",
                stipend=None,
                date_posted=None,
                link=link,
                source=park_name,
                description=None,  # Technopark/Infopark don't provide description in listing view
            ))
        except Exception as e:
            print(f"[{park_name}] skipped one card due to parse error: {e}")
            continue

    return jobs


def fetch(config):
    jobs = []
    jobs.extend(_fetch_page(TECHNOPARK_URL, "Technopark"))
    jobs.extend(_fetch_page(INFOPARK_URL, "Infopark"))
    return jobs
