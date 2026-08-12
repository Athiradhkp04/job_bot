"""
Internshala source module.

Internshala has no official public API, so this scrapes their public
listing pages. Their CSS class names change periodically (confirmed -
the original selectors here stopped working within days), so instead
of hardcoding fragile class names, this parses each job card by:
  1. Finding the title link via its URL pattern (/internship/detail/...
     or /job/detail/...) - much more stable than CSS classes.
  2. Reading the plain text lines in the card in order, and picking out
     stipend/duration/posted-date by their recognizable text patterns
     (e.g. "Rs X /month", "Rs X /year", "6 Months", "3 weeks ago").

Pulls from two sections:
  - Internships (BASE_URL) for the configured `categories` list.
  - Fresher full-time Jobs (FRESHER_JOBS_BASE_URL) for the configured
    `fresher_job_categories` list - added specifically so Data Analyst
    fresher job vacancies show up too, not just internships.

Fetches from multiple South India locations (configured in `locations` list)
to cover Kerala, Tamil Nadu, Karnataka, Andhra Pradesh, Telangana, and Puducherry,
matching the full scope defined in location_rules.conditional tiers.

Also paginates (page-2/, page-3/, etc.) since Internshala listing
pages only show the first ~20-30 cards on page 1 - anything beyond
that was previously being silently missed entirely.

If this still breaks in future, check whether Internshala changed the
detail-page URL pattern itself (unlikely) before assuming the regex
patterns below need updating.
"""

import re
import requests
from bs4 import BeautifulSoup
from job_model import make_job
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://internshala.com/internships/{category}-internship-in-{location}"
FRESHER_JOBS_BASE_URL = "https://internshala.com/fresher-jobs/{category}-jobs-in-{location}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

DETAIL_LINK_RE = re.compile(r"/(internship|job)/detail/")
STIPEND_RE = re.compile(
    r"(₹\s?[\d,]+(\s?-\s?₹?\s?[\d,]+)?\s?/\s?(month|year|annum)|unpaid|competitive stipend|performance based)",
    re.IGNORECASE,
)
DURATION_RE = re.compile(r"^\d+\s+months?$", re.IGNORECASE)
POSTED_RE = re.compile(
    r"^(few (hours|days|weeks) ago|\d+\s+(hour|hours|day|days|week|weeks|month|months)\s+ago|today|yesterday)$",
    re.IGNORECASE,
)
BADGE_RE = re.compile(r"^(actively hiring|early applicant|fast response|fresher job)$", re.IGNORECASE)


def _parse_card(card, employment_type="Internship", park_default_location="Kerala"):
    title_link = card.find("a", href=DETAIL_LINK_RE)
    if not title_link:
        return None

    title = title_link.get_text(strip=True)
    href = title_link.get("href", "")
    link = href if href.startswith("http") else ("https://internshala.com" + href)

    lines = [l.strip() for l in card.get_text("\n").split("\n") if l.strip()]

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

    if i < len(lines) and not STIPEND_RE.search(lines[i]) and not DURATION_RE.match(lines[i]):
        location = lines[i]
        i += 1

    for j in range(i, len(lines)):
        if STIPEND_RE.search(lines[j]):
            stipend = lines[j]
            break

    for l in lines:
        if POSTED_RE.match(l):
            posted = l
            break

    # Don't filter by location here - let filter.py handle it via excluded_locations and location_rules
    # This keeps the architecture consistent and allows proper location-based filtering

    return make_job(
        title=title,
        company=company,
        location=location or park_default_location,
        employment_type=employment_type,
        stipend=stipend,
        date_posted=posted,
        link=link,
        source="Internshala",
        description=None,  # Internshala doesn't provide description in listing cards
    )


def _fetch_listing(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[internshala] fetch failed for '{url}': {e}")
        return None


def _page_url(base_url, page):
    if page == 1:
        return base_url
    return base_url.rstrip("/") + f"/page-{page}/"


def _fetch_category(base_url_template, category, location, employment_type, max_pages):
    """
    Fetches a category across multiple pages, stopping early once a page
    comes back with few/no cards (either genuinely out of location-specific
    results, or Internshala's "no more matching, here's other opportunities"
    filler has kicked in).
    """
    jobs = []
    base_url = base_url_template.format(category=category, location=location)

    for page in range(1, max_pages + 1):
        url = _page_url(base_url, page)
        html = _fetch_listing(url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.individual_internship, div.individual_job")

        if not cards:
            print(f"[internshala] '{category}' in {location} page {page}: no cards, stopping pagination")
            break

        page_job_count = 0
        for card in cards:
            try:
                job = _parse_card(card, employment_type=employment_type, park_default_location=location.title())
                if job:
                    jobs.append(job)
                    page_job_count += 1
            except Exception as e:
                print(f"[internshala] skipped one card in '{category}' in {location} page {page}: {e}")
                continue

        print(f"[internshala] '{category}' in {location} page {page}: {page_job_count} jobs")

        if len(cards) < 10:
            break

    return jobs


def fetch(config):
    src_cfg = config["sources"]["internshala"]
    categories = src_cfg.get("categories", ["data-science"])
    fresher_job_categories = src_cfg.get("fresher_job_categories", [])
    locations = src_cfg.get("locations", ["kerala"])
    max_pages = src_cfg.get("max_pages_per_category", 3)
    max_concurrent = src_cfg.get("max_concurrent_requests", 5)  # Default to 5 concurrent requests

    jobs = []
    
    # Build list of all combinations to fetch
    combinations = []
    for category in categories:
        for location in locations:
            combinations.append((BASE_URL, category, location, "Internship", max_pages))
    
    for category in fresher_job_categories:
        for location in locations:
            combinations.append((FRESHER_JOBS_BASE_URL, category, location, "Full-time (Fresher)", max_pages))
    
    print(f"[internshala] fetching {len(combinations)} category-location combinations with max {max_concurrent} concurrent requests")
    
    # Fetch combinations in parallel
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        future_to_combo = {
            executor.submit(_fetch_category, *combo): combo 
            for combo in combinations
        }
        
        for future in as_completed(future_to_combo):
            combo = future_to_combo[future]
            try:
                combo_jobs = future.result()
                jobs.extend(combo_jobs)
            except Exception as e:
                base_url, category, location, emp_type, _ = combo
                print(f"[internshala] failed to fetch {category} in {location}: {e}")
                continue

    return jobs