"""
Internshala source module.

Internshala has no official public API, so this scrapes their public
listing pages. Their CSS class names change periodically (confirmed -
the original selectors here stopped working within days), so instead
of hardcoding fragile class names, this parses each job card by:
  1. Finding the title link via its URL pattern (/internship/detail/...)
     - much more stable than CSS classes.
  2. Reading the plain text lines in the card in order, and picking out
     stipend/duration/posted-date by their recognizable text patterns
     (e.g. "Rs X /month", "6 Months", "3 weeks ago").

If this still breaks in future, check whether Internshala changed the
detail-page URL pattern itself (unlikely) before assuming the regex
patterns below need updating.
"""

import re
import requests
from bs4 import BeautifulSoup
from job_model import make_job

BASE_URL = "https://internshala.com/internships/{category}-internship-in-{location}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

DETAIL_LINK_RE = re.compile(r"/internship/detail/")
STIPEND_RE = re.compile(
    r"(₹\s?[\d,]+(\s?-\s?₹?\s?[\d,]+)?\s?/\s?month|unpaid|competitive stipend|performance based)",
    re.IGNORECASE,
)
DURATION_RE = re.compile(r"^\d+\s+months?$", re.IGNORECASE)
POSTED_RE = re.compile(
    r"^(few (hours|days|weeks) ago|\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|today|yesterday)$",
    re.IGNORECASE,
)
BADGE_RE = re.compile(r"^(actively hiring|early applicant|fast response)$", re.IGNORECASE)


def _parse_card(card, park_default_location="Kerala"):
    title_link = card.find("a", href=DETAIL_LINK_RE)
    if not title_link:
        return None

    title = title_link.get_text(strip=True)
    href = title_link.get("href", "")
    link = href if href.startswith("http") else ("https://internshala.com" + href)

    lines = [l.strip() for l in card.get_text("\n").split("\n") if l.strip()]

    # Drop the title line(s) at the start so we don't re-read it as company
    while lines and lines[0] == title:
        lines.pop(0)

    company = None
    location = None
    stipend = None
    posted = None

    i = 0
    if i < len(lines) and BADGE_RE.match(lines[i]):
        i += 1
    if i < len(lines):
        company = lines[i]
        i += 1
    while i < len(lines) and BADGE_RE.match(lines[i]):
        i += 1

    # Next line is location, unless it's actually the stipend/duration line
    if i < len(lines) and not STIPEND_RE.search(lines[i]) and not DURATION_RE.match(lines[i]):
        location = lines[i]
        i += 1

    # Scan forward for stipend
    for j in range(i, len(lines)):
        if STIPEND_RE.search(lines[j]):
            stipend = lines[j]
            break

    # Scan all lines for a posted-date-shaped line (anchored match avoids
    # false positives inside description text)
    for l in lines:
        if POSTED_RE.match(l):
            posted = l
            break

    return make_job(
        title=title,
        company=company,
        location=location or park_default_location,
        employment_type="Internship",
        stipend=stipend,
        date_posted=posted,
        link=link,
        source="Internshala",
    )


def fetch(config):
    src_cfg = config["sources"]["internshala"]
    categories = src_cfg.get("categories", ["data-science"])
    location = src_cfg.get("location", "kerala")

    jobs = []

    for category in categories:
        url = BASE_URL.format(category=category, location=location)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[internshala] fetch failed for category '{category}': {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.individual_internship")

        for card in cards:
            try:
                job = _parse_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                print(f"[internshala] skipped one card in '{category}' due to parse error: {e}")
                continue

    return jobs