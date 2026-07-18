"""
Indeed source module.

Indeed actively discourages scraping and often serves CAPTCHAs to
non-browser traffic, so this is the most likely module to need
maintenance over time. If this starts consistently returning zero
results, Indeed has probably changed something - check response
status codes first (403/429 = being blocked, not a parsing issue).

If this becomes too unreliable, consider dropping Indeed from the
active source list in config.yaml rather than fighting their
anti-bot measures indefinitely.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from job_model import make_job

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def fetch(config):
    src_cfg = config["sources"]["indeed"]
    query = src_cfg.get("query", "software engineer")
    location = src_cfg.get("location", "Kerala, India")

    url = (
        f"https://in.indeed.com/jobs?q={quote_plus(query)}"
        f"&l={quote_plus(location)}&fromage=3"
    )
    jobs = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[indeed] fetch failed: {e}")
        return jobs

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select("div.job_seen_beacon")

    for card in cards:
        try:
            title_el = card.select_one("h2.jobTitle span")
            company_el = card.select_one("span.companyName")
            location_el = card.select_one("div.companyLocation")
            link_el = card.select_one("h2.jobTitle a")
            salary_el = card.select_one("div.salary-snippet-container, div.metadata.salary-snippet-container")

            title = title_el.get_text(strip=True) if title_el else None
            company = company_el.get_text(strip=True) if company_el else None
            location_text = location_el.get_text(strip=True) if location_el else None
            link = ("https://in.indeed.com" + link_el["href"]) if link_el and link_el.has_attr("href") else None
            stipend = salary_el.get_text(strip=True) if salary_el else None

            jobs.append(make_job(
                title=title,
                company=company,
                location=location_text,
                employment_type="Not specified",
                stipend=stipend,
                date_posted=None,  # Indeed rarely exposes exact date in listing view
                link=link,
                source="Indeed",
            ))
        except Exception as e:
            print(f"[indeed] skipped one card due to parse error: {e}")
            continue

    return jobs
