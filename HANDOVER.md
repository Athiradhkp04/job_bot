# Job Bot - Handover Document

## Project Overview

Job Bot is an automated job/internship notification system that:
- Fetches job postings from multiple sources (Internshala, Himalayas)
- Filters them based on role keywords, location, stipend, and experience level
- Sends filtered results via Telegram message 3x daily
- Runs on GitHub Actions with scheduled triggers

**Key constraint:** All sources must be free with no API keys or paid plans.

---

## Architecture & Data Flow

```
GitHub Actions (8 AM, 2 PM, 9 PM IST)
    ↓
main.py (entry point)
    ↓
1. Fetch Jobs (collect_all_jobs)
   ├─ Internshala: 19 South India locations × 7 categories (concurrent requests)
   └─ Himalayas: Entry-level remote jobs globally + South India onsite/hybrid
    ↓
2. Filter Jobs (apply_filters)
   ├─ Role keyword matching (role_groups)
   ├─ Exclude keyword matching
   ├─ Location rules (excluded_locations, location_rules)
   ├─ Stipend thresholds
   ├─ Experience level filtering (≤2 years, fresher keyword priority)
   └─ Age filtering (max 7 days)
    ↓
3. Deduplicate (filter_new_jobs)
   └─ Track seen jobs in seen_jobs.json (prunes entries >10 days old)
    ↓
4. Priority Sorting (sort_by_priority)
   ├─ Role group priority (config order)
   └─ Location priority (within role groups)
    ↓
5. Categorize for Message
   ├─ Onsite/Hybrid: Internshala + Himalayas South India
   └─ WFH/Remote: Himalayas global remote jobs
    ↓
6. Send Telegram (send_telegram_message)
   └─ Splits messages >4096 chars into multiple sequential messages
```

---

## Key Components

### Core Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, orchestrates the pipeline |
| `config.yaml` | All configuration (sources, filters, output rules) |
| `filter.py` | Filtering logic (role, location, stipend, experience, age) |
| `job_model.py` | Job data structure normalization (`make_job()`) |
| `priority.py` | Priority sorting by role group and location |
| `dedup.py` | Deduplication and state management |
| `notify.py` | Telegram message formatting and sending |
| `notify_state.py` | Digest trigger state management |

### Source Modules (`sources/`)

| File | Status | Details |
|------|--------|---------|
| `internshala.py` | **Active** | HTML scrape, 19 South India locations, concurrent requests |
| `himalayas.py` | **Active** | JSON API, Entry-level remote jobs globally |
| `indeed.py` | Disabled | Blocks non-browser traffic (403) |
| `technopark_infopark.py` | Disabled | JS-rendered, needs headless browser |
| `kerala_gov.py` | Disabled | JS-rendered, returned 0 jobs |

### Configuration Files

| File | Purpose |
|------|---------|
| `config.yaml` | Main configuration (sources, filters, output) |
| `seen_jobs.json` | Deduplication state (tracked in git) |
| `notify_state.json` | Digest trigger state (tracked in git) |

---

## Current Configuration

### Active Sources

**Internshala:**
- **Locations:** 19 South India cities (Kerala, TN, KA, AP, TS, PY)
- **Categories:** 5 internship categories + 2 fresher job categories
- **Pagination:** 1 page per category-location (133 total requests)
- **Concurrency:** 5 parallel requests (runtime: ~40 seconds)
- **Parsing:** URL-pattern based (not CSS classes) for stability

**Himalayas:**
- **WFH/Remote:** All Entry-level remote jobs globally (no location restriction)
- **South India:** Onsite/hybrid jobs matching South India locations
- **Pagination:** 3 pages (60 jobs total)
- **Filtering:** Entry-level seniority only, fresher keyword detection

### Filtering Rules

**Role Groups (priority order):**
1. **core** - Data Analyst/Scientist, Business Analyst, BI, ML, Python, SQL (bypasses location/stipend)
2. **seo** - SEO roles (location/stipend rules apply)
3. **analyst_adjacent** - Marketing/Product/Research/RevOps analysts
4. **hr** - HR roles (internship only)
5. **full_stack** - Full-stack development roles
6. **digital_marketing** - Digital marketing (bypasses to top if >10k/month)
7. **generic_analyst_catchall** - Broad "Junior Analyst" titles (lowest priority)

**Exclude Keywords:**
- Seniority: senior, lead, manager, 10+ years, principal
- Cross-industry noise: equity research, financial analyst, actuary, clinical, pharma, hospital, nursing, legal

**Location Rules:**
- **Excluded (hard ban):** Maharashtra (Mumbai, Pune, etc.)
- **Always Allow:** Remote, Hybrid, Kerala cities
- **Conditional (with stipend threshold):**
  - South India cities (Chennai, Bangalore, etc.): ₹8,000/month
  - North India cities (Noida, etc.): ₹15,000/month

**Experience Filtering:**
- Reject jobs with experience upper bound >2 years
- Prioritize "fresher" keyword (strong positive signal)
- Jobs with no numeric experience requirement pass by default

**Age Filtering:**
- Max 7 days old

### Output Configuration

- **Min jobs per message:** 10
- **Max jobs per message:** 20
- **Message structure:** Two sections
  - Onsite/Hybrid Jobs (Internshala + Himalayas South India)
  - WFH/Remote Jobs (Himalayas global remote)

### Digest Configuration

- **Enabled:** Yes
- **Trigger:** After 2 days with no new jobs
- **Purpose:** Shows all currently matching jobs (including seen ones) to distinguish quiet market from broken bot

---

## Recent Optimizations (Critical Context)

### 1. Concurrent Requests (Internshala)
- **Problem:** 133 sequential requests took 214 seconds (3.5 minutes)
- **Solution:** ThreadPoolExecutor with 5 concurrent workers
- **Result:** 214s → 42s (5.3x speedup)
- **No rate limiting observed** with 5 concurrent requests
- **Location:** `sources/internshala.py` line 175+

### 2. Telegram Message Splitting
- **Problem:** Messages >4096 chars caused Telegram API crashes
- **Solution:** `_split_message()` function in `notify.py`
- **Behavior:** Splits at newline boundaries, sends sequential messages
- **Location:** `notify.py` line 116+

### 3. Himalayas Global Remote
- **Problem:** 0 WFH results due to South India restriction (Entry-level roles concentrated elsewhere)
- **Solution:** Removed location restriction from WFH branch
- **Behavior:** WFH includes all Entry-level remote jobs globally, South India prioritized via ranking
- **Location:** `sources/himalayas.py` line 189+

### 4. Pagination Reduction
- **Problem:** 133 requests was too high for single-run duration
- **Solution:** Reduced from 2 pages to 1 page per category-location
- **Tradeoff:** Shallower depth, but full location coverage maintained
- **Location:** `config.yaml` line 49

---

## Testing Locally

### Prerequisites
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

### Run Full Pipeline
```bash
python main.py
```

**Expected runtime:** ~40 seconds
**Console output:** Shows job counts per source, filtering stats, dedup stats

### Test Individual Components

**Test a specific source:**
```python
import yaml
from sources import internshala
config = yaml.safe_load(open('config.yaml'))
jobs = internshala.fetch(config)
print(f"Got {len(jobs)} jobs")
```

**Test filtering:**
```python
from filter import apply_filters
filtered = apply_filters(jobs, config)
print(f"After filtering: {len(filtered)}")
```

**Test Telegram message formatting:**
```python
from notify import format_message, _split_message
message = format_message(jobs, max_jobs=20, wfh_jobs=wfh_jobs)
print(f"Message length: {len(message)}")
messages = _split_message(message)
print(f"Split into {len(messages)} messages")
```

---

## Troubleshooting Guide

### Issue: Source returns 0 jobs
**Check:**
1. Is source enabled in `config.yaml`?
2. Did site structure change? (check URL patterns in source module)
3. Is site blocking our requests? (check console for 403/429 errors)
4. For Internshala: Are categories/location slugs still valid?

### Issue: Telegram message not sending
**Check:**
1. Are `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` set as environment variables?
2. Is message >4096 chars? (check console for split message logs)
3. Did bot get blocked/banned? (check with @userinfobot)
4. Is bot token valid? (test with curl to Telegram API)

### Issue: Too many/few jobs
**Check:**
1. Role keyword matching: Are keywords too broad/narrow?
2. Location rules: Are thresholds too high/low?
3. Age filtering: Is `max_age_days` too restrictive?
4. Experience filtering: Are requirements too strict?

### Issue: Runtime too slow
**Check:**
1. Is `max_concurrent_requests` set in config? (should be 5)
2. Are too many sources enabled?
3. Is pagination too deep? (reduce `max_pages_per_category`)

### Issue: Seeing duplicate jobs
**Check:**
1. Is `seen_jobs.json` being committed to git?
2. Is dedup logic working? (check console dedup stats)
3. Are jobs using same apply URL? (check `job_model.job_hash`)

---

## Adding a New Source

### Steps

1. **Create source module:** `sources/newsource.py`
```python
import requests
from job_model import make_job

def fetch(config):
    src_cfg = config["sources"].get("newsource", {})
    if not src_cfg.get("enabled", False):
        return []
    
    jobs = []
    # Fetch and parse jobs
    # Each job must have: title, company, location, employment_type, stipend, date_posted, link, source, description
    job = make_job(
        title="Job Title",
        company="Company Name",
        location="Location",
        employment_type="Full-time",
        stipend="₹10,000/month",
        date_posted="Today",
        link="https://example.com/apply",
        source="NewSource",
        description="Job description"
    )
    jobs.append(job)
    return jobs
```

2. **Add to main.py:**
```python
from sources import newsource

SOURCE_MODULES = {
    # ... existing sources
    "newsource": newsource,
}
```

3. **Add config block in config.yaml:**
```yaml
sources:
  newsource:
    enabled: true
    # source-specific config
```

### Requirements
- **Never crash the run:** Wrap in try/except in `collect_all_jobs()`
- **Handle per-request failures:** If making multiple requests, handle individual failures
- **Free to use:** No API keys, no paid plans
- **Apply URL:** Provide employer-side apply URL for better dedup (not listing page URL)

---

## Important Constraints & Decisions

### Hard Constraints
1. **No paid plans:** All sources must be free
2. **No API keys:** No authentication required
3. **No account signup:** Must work without user accounts
4. **Never crash:** Each source isolated in try/except
5. **Non-abusive scraping:** Concurrent requests limited to 5, pagination minimized

### Design Decisions

**Why URL-pattern parsing for Internshala?**
- CSS class-based parsing broke silently after redesign
- URL patterns are more stable (e.g., `/internship/detail/`)
- Better failure mode: crash vs. returning "Untitled role" for everything

**Why global remote for Himalayas?**
- Entry-level roles concentrated outside South India (mostly US)
- South India prioritized via existing ranking system
- Better to see some remote jobs than zero

**Why concurrent requests instead of fewer locations?**
- Maintains full South India coverage (19 locations)
- 5.3x speedup (214s → 42s) without losing coverage
- No rate limiting observed with 5 concurrent workers

**Why two-section message structure?**
- Separates onsite/hybrid from fully remote for clarity
- Onsite: Internshala + Himalayas South India
- WFH: Himalayas global remote (prioritizes South India via ranking)

---

## Future Work Considerations

### Potential Improvements
1. **Re-enable Indeed:** Requires browser headers or user-agent rotation (currently blocked 403)
2. **Technopark/Infopark:** Needs headless browser (Playwright) - high overhead for low value
3. **Kerala Gov:** Investigate if JS-rendered now, or if page structure changed
4. **Internshala pagination:** Could increase to 2 pages if 1 page proves insufficient
5. **Experience filtering:** Could add more nuanced parsing (e.g., "1-3 years" range interpretation)

### Monitoring Needs
1. **Source uptime:** Track which sources return 0 jobs consistently
2. **Filter effectiveness:** Monitor false positives/negatives in role matching
3. **Runtime tracking:** Watch for performance degradation over time
4. **Telegram delivery:** Monitor for blocked messages or rate limits

### Scaling Considerations
1. **GitHub Actions limits:** Currently 42s × 3 runs/day = 63 minutes/month (3% of free tier)
2. **Request volume:** 133 requests per run, ~40,000 requests/month
3. **State file size:** Monitor `seen_jobs.json` growth (currently prunes after 10 days)

---

## Quick Reference

### Modify filters: Edit `config.yaml` → `filters:` section
### Change locations: Edit `config.yaml` → `sources:` → location lists
### Adjust concurrency: Edit `config.yaml` → `max_concurrent_requests`
### Test locally: `python main.py` with env vars set
### View state: Check `seen_jobs.json` and `notify_state.json`
### Add source: Create `sources/newsource.py`, add to `main.py`, update `config.yaml`

### Critical Files to Check When Debugging
1. `config.yaml` - Configuration
2. `main.py` - Pipeline orchestration
3. `filter.py` - Filtering logic
4. `sources/*.py` - Source-specific parsing
5. `notify.py` - Telegram sending
6. Console output - Job counts and error messages

---

## Contact & Context

This bot was developed with the following priorities:
1. **Reliability:** Never crash, isolate source failures
2. **Coverage:** Full South India location coverage
3. **Performance:** Fast enough for 3x/day schedule without hitting GitHub limits
4. **Cost:** Free to run, no paid dependencies
5. **Relevance:** Entry-level/fresher roles with experience filtering

The bot is scheduled via GitHub Actions cron at 8 AM, 2 PM, and 9 PM IST.
