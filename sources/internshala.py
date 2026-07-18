"""
Internshala source module.

Internshala has no official public API, so this scrapes their public
listing pages. Structure has historically been fairly stable, but if
this starts returning empty results, the CSS selectors below are the
first thing to check (their HTML classes do change occasionally).
"""

import requests
from bs4 import BeautifulSoup
from job_model import make_job

BASE_URL = "https://internshala.com/internships/{category}-internship-in-{location}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def fetch(config):
    src_cfg = config["sources"]["internshala"]
    category = src_cfg.get("category", "computer-science")
    location = src_cfg.get("location", "kerala")

    url = BASE_URL.format(category=category, location=location)
    jobs = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[internshala] fetch failed: {e}")
        return jobs

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select("div.individual_internship")

    for card in cards:
        try:
            title_el = card.select_one("h3.job-internship-name a")
            company_el = card.select_one("p.company-name")
            location_el = card.select_one("p.locations span a")
            stipend_el = card.select_one("span.stipend")
            posted_el = card.select_one("div.status-inactive, div.other_label_ribbon")

            title = title_el.get_text(strip=True) if title_el else None
            link = ("https://internshala.com" + title_el["href"]) if title_el and title_el.has_attr("href") else None
            company = company_el.get_text(strip=True) if company_el else None
            location_text = location_el.get_text(strip=True) if location_el else "Kerala"
            stipend = stipend_el.get_text(strip=True) if stipend_el else None
            posted = posted_el.get_text(strip=True) if posted_el else None

            jobs.append(make_job(
                title=title,
                company=company,
                location=location_text,
                employment_type="Internship",
                stipend=stipend,
                date_posted=posted,
                link=link,
                source="Internshala",
            ))
        except Exception as e:
            print(f"[internshala] skipped one card due to parse error: {e}")
            continue

    return jobs
