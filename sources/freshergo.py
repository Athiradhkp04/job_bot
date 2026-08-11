"""
FresherGo source module (freshergo.com).

An entry-level-only job board: it filters out senior roles on its own
side, so almost everything it returns is already in scope for this bot.

Why this parses embedded JSON instead of job cards:
FresherGo is a Next.js app that ships each listing page's data as a
serialized payload inside `self.__next_f.push([...])` script tags, with
the same fields the visible cards are rendered from - title, company,
city, remote flag, salary, employment type, posted timestamp, and the
employer-side apply URL. Reading that payload is both richer than the
DOM (the cards don't show the apply URL or an exact posted date) and
far more stable than Tailwind class names, which are regenerated on
every redesign. That's the same lesson `internshala.py` learned the
hard way, applied one level up.

If FresherGo ever stops embedding that payload, `_parse_cards_fallback`
takes over: it finds listings by their `/jobs/{slug}-{uuid}` URL shape,
which is routing-level and unlikely to change silently.

Note on overlap: a large share of FresherGo listings are syndicated
from Himalayas and Arbeitnow, which this bot also polls directly. Those
duplicates collapse in dedup because every source reports the same
`apply_url` - see `job_model.job_hash`.
"""

import json
import re

import requests
from bs4 import BeautifulSoup

from job_model import make_job
from sources.common import days_ago_text, format_salary, remote_location

BASE = "https://freshergo.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# Detail-page URL shape: /jobs/{slug}-{uuid}. The trailing UUID is what
# separates a real listing from FresherGo's own /jobs/role/... and
# /jobs/city/... navigation links.
DETAIL_LINK_RE = re.compile(
    r"^/jobs/[^/]+-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
FLIGHT_PUSH_RE = re.compile(r"self\.__next_f\.push\(")
JOB_OBJECT_RE = re.compile(r'\{"id":"[0-9a-f]{8}-')
# Next.js prefixes serialized Date values with "$D".
DATE_PREFIX_RE = re.compile(r"^\$D")

EMPLOYMENT_TYPES = {
    "FULL_TIME": "Full-time",
    "PART_TIME": "Part-time",
    "INTERNSHIP": "Internship",
    "CONTRACT": "Contract",
    "TEMPORARY": "Temporary",
}

_DECODER = json.JSONDecoder()


def _get(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[freshergo] fetch failed for '{url}': {e}")
        return None


def _flight_payload(html):
    """
    Reassembles the Next.js streaming payload. Each `push` call carries
    one chunk of a single logical string, split at arbitrary points, so
    the chunks have to be concatenated before anything can be parsed
    out of them.
    """
    chunks = []
    for match in FLIGHT_PUSH_RE.finditer(html):
        try:
            value, _ = _DECODER.raw_decode(html, match.end())
        except ValueError:
            continue
        if isinstance(value, list) and len(value) > 1 and isinstance(value[1], str):
            chunks.append(value[1])
    return "".join(chunks)


def _extract_job_objects(html):
    """
    Pulls every embedded job record out of the payload. Objects are
    located by their opening `{"id":"<uuid>` and decoded individually,
    since the payload as a whole isn't valid JSON.
    """
    payload = _flight_payload(html)
    jobs = []
    seen_ids = set()

    for match in JOB_OBJECT_RE.finditer(payload):
        try:
            obj, _ = _DECODER.raw_decode(payload, match.start())
        except ValueError:
            continue
        if not isinstance(obj, dict) or "applyUrl" not in obj:
            continue
        job_id = obj.get("id")
        if job_id in seen_ids:
            continue
        seen_ids.add(job_id)
        jobs.append(obj)

    return jobs


def _posted_text(obj):
    # Next.js serializes Date values with a "$D" prefix in the payload.
    posted_at = obj.get("postedAt")
    if not posted_at:
        return None
    return days_ago_text(DATE_PREFIX_RE.sub("", posted_at))


def _location(obj):
    city = (obj.get("city") or "").strip()
    if obj.get("isRemote"):
        return remote_location(city)
    return city or None


def _to_job(obj):
    slug = obj.get("slug")
    job_id = obj.get("id")
    link = f"{BASE}/jobs/{slug}-{job_id}" if slug and job_id else obj.get("applyUrl")

    return make_job(
        title=obj.get("title"),
        company=obj.get("companyName"),
        location=_location(obj),
        employment_type=EMPLOYMENT_TYPES.get(obj.get("employmentType"), "Not specified"),
        stipend=format_salary(
            obj.get("salaryMin"),
            obj.get("salaryMax"),
            currency=obj.get("salaryCurrency"),
            period=obj.get("salaryPeriod"),
        ),
        date_posted=_posted_text(obj),
        link=link,
        source="FresherGo",
        apply_url=obj.get("applyUrl"),
    )


def _parse_cards_fallback(html):
    """
    DOM fallback for if the embedded payload ever disappears. Yields
    less than the payload does (no apply URL, no exact date), but a
    degraded result beats silently returning nothing.
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    for anchor in soup.find_all("a", href=DETAIL_LINK_RE):
        card = anchor.find_parent("li") or anchor.parent
        if card is None:
            continue

        heading = card.find(["h2", "h3"])
        title = heading.get_text(strip=True) if heading else None
        if not title:
            continue

        lines = [l.strip() for l in card.get_text("\n").split("\n") if l.strip()]
        company = None
        if title in lines:
            title_index = lines.index(title)
            if title_index + 1 < len(lines):
                company = lines[title_index + 1]

        jobs.append(make_job(
            title=title,
            company=company,
            location=None,
            employment_type="Not specified",
            stipend=None,
            date_posted=None,
            link=BASE + anchor["href"],
            source="FresherGo",
        ))

    return jobs


def _fetch_listing_page(url):
    html = _get(url)
    if not html:
        return None

    objects = _extract_job_objects(html)
    if objects:
        return [_to_job(obj) for obj in objects]

    jobs = _parse_cards_fallback(html)
    if jobs:
        print(f"[freshergo] no embedded payload at '{url}', used DOM fallback")
    return jobs


def _page_url(base_url, page):
    if page == 1:
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}page={page}"


def _fetch_paginated(base_url, label, max_pages):
    """
    Paginates until a page repeats results or comes back short, which
    is how FresherGo signals the end of a listing - it keeps serving
    HTTP 200 for pages (and slugs) that have nothing behind them.
    """
    jobs = []
    seen_links = set()

    for page in range(1, max_pages + 1):
        url = _page_url(base_url, page)
        page_jobs = _fetch_listing_page(url)
        if page_jobs is None:
            break
        if not page_jobs:
            print(f"[freshergo] '{label}' page {page}: no listings, stopping")
            break

        fresh = [job for job in page_jobs if job["link"] not in seen_links]
        seen_links.update(job["link"] for job in fresh)
        jobs.extend(fresh)
        print(f"[freshergo] '{label}' page {page}: {len(fresh)} jobs")

        if not fresh or len(page_jobs) < 20:
            break

    return jobs


def fetch(config):
    src_cfg = config["sources"]["freshergo"]
    max_pages = src_cfg.get("max_pages_per_listing", 3)

    jobs = []

    for slug in src_cfg.get("role_slugs", []):
        jobs.extend(_fetch_paginated(f"{BASE}/jobs/role/{slug}", f"role/{slug}", max_pages))

    for slug in src_cfg.get("city_slugs", []):
        jobs.extend(_fetch_paginated(f"{BASE}/jobs/city/{slug}", f"city/{slug}", max_pages))

    if src_cfg.get("include_remote_jobs", True):
        jobs.extend(_fetch_paginated(f"{BASE}/remote-jobs", "remote-jobs", max_pages))

    if src_cfg.get("include_internships", True):
        jobs.extend(_fetch_paginated(f"{BASE}/internships", "internships", max_pages))

    return jobs
