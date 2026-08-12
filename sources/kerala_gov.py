"""
Kerala government internship source module.

Pulls from Knowledge Mission Kerala's internship listing page, which
was the only Kerala govt. portal that showed live, individual
postings with stipend info rather than a single static application
form (checked July 2026).

Like technopark_infopark.py, the selectors below are a best-effort
starting point - verify against the live page and adjust before
relying on this.
"""

import requests
from bs4 import BeautifulSoup
from job_model import make_job

URL = "https://skills.knowledgemission.kerala.gov.in/local/hiringcompany/apply_internships_cards.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def fetch(config):
    jobs = []
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[kerala_gov] fetch failed: {e}")
        return jobs

    soup = BeautifulSoup(resp.text, "html.parser")
    # ADJUST once you've inspected the real page structure.
    cards = soup.select("div.card, div.internship-card")

    for card in cards:
        try:
            title_el = card.select_one(".job-role, h5, h4")
            company_el = card.select_one(".industry, .company")
            stipend_el = card.select_one(".stipend")
            link_el = card.select_one("a")

            title = title_el.get_text(strip=True) if title_el else None
            company = company_el.get_text(strip=True) if company_el else None
            stipend = stipend_el.get_text(strip=True) if stipend_el else None
            link = link_el["href"] if link_el and link_el.has_attr("href") else URL

            if not title:
                continue

            jobs.append(make_job(
                title=title,
                company=company,
                location="Kerala",
                employment_type="Internship",
                stipend=stipend,
                date_posted=None,
                link=link,
                source="Kerala Gov (Knowledge Mission)",
                description=None,  # Kerala Gov doesn't provide description in listing view
            ))
        except Exception as e:
            print(f"[kerala_gov] skipped one card due to parse error: {e}")
            continue

    return jobs
