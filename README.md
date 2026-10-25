# Job Bot

Finds new job/internship postings matching your filters and sends you a
Telegram message, 3x a day. No dashboards, no auto-apply, no AI summaries.

## How it works
1. Fetches postings from Internshala (South India) and Himalayas (Entry-level remote jobs).
2. Filters them using the rules in `config.yaml` (role keywords, location, stipend, experience level, age).
3. Identifies new jobs (compares against `seen_jobs.json`).
4. Sorts by priority (role group, then location, with small boosts for analytics keywords and newer postings).
5. Caps at top 20 jobs per message (configurable).
6. Sends the top matches as one Telegram message with two sections:
   - **Onsite/Hybrid Jobs** — Internshala (South India) + Himalayas (South India onsite/hybrid)
   - **WFH/Remote Jobs** — Himalayas (Entry-level remote jobs globally)
7. Marks only the sent jobs as "seen" in `seen_jobs.json`.
8. Exits. Runs again on the next scheduled trigger.

**Important:** Jobs beyond the max_jobs cap (21+) remain unmarked and will appear in future runs when higher-priority jobs age out or are displaced. This prevents permanent loss of valid jobs due to the display cap.

If nothing new turns up for a couple of days, it sends a "refresh
check-in" digest instead — everything currently matching your filters,
including jobs you've already seen — so a quiet stretch is
distinguishable from a broken bot. Configured under `digest:`.

## Sources

| Source | Type | Status |
|---|---|---|
| Internshala | HTML scrape | **on** — South India internships + fresher jobs (22 locations: Kerala cities, Bangalore, Hyderabad, Goa, Pondicherry, Tamil Nadu cities) |
| Himalayas | JSON API | **on** — Entry-level remote jobs globally + South India onsite/hybrid |
| Indeed | — | off — blocks non-browser traffic (403) |
| FresherGo | — | off — requires paid plan for actual applications |
| RemoteOK | — | off — requires paid plan for actual applications |
| Jobicy | — | off — requires paid plan for actual applications |
| Arbeitnow | — | off — requires paid plan for actual applications |
| Technopark/Infopark | — | off — JS-rendered |
| Kerala Gov | — | off — JS-rendered, returned 0 jobs |

All active sources are free with no API key and no account. Nothing here costs
money to run, which is a hard constraint on adding new ones.

Notes on the active sources:

- **Internshala** fetches from 22 South India locations (Kerala cities, Bangalore, Hyderabad, Goa, Pondicherry, Tamil Nadu cities) using concurrent requests (5 at a time) to manage runtime. Uses URL-pattern parsing for stability, not fragile CSS classes.
- **Himalayas** provides Entry-level remote jobs globally (since Entry-level roles are concentrated outside South India) with South India locations prioritized via the existing ranking system. Also includes South India onsite/hybrid jobs.
- **Experience filtering** rejects jobs requiring >2 years experience upper bound, prioritizes "fresher" keyword when present.

## Role targeting

The bot targets ANALYST + OPERATIONS MIX roles for freshers (0-2 years experience):

**Tier 1 (Core) - Top priority, bypasses location/stipend rules:**
- Data Analyst / Data Scientist / Business Analyst / Business Intelligence / BI Developer / Power BI
- MIS Executive / Insights Analyst / Reporting Analyst / KPI / Dashboard
- Operations Analyst / Business Operations Analyst

**Tier 2 (Ops Analytics & HR Analytics) - Location/stipend rules apply:**
- Business Operations / Process Analyst / Process Associate / Program Coordinator / Project Coordinator
- ERP Analyst / ERP Intern / Strategy Analyst / Supply Chain Analyst / Procurement Analyst
- HR Analyst / People Analytics / Talent Analytics / Recruitment Analytics / Workforce Analytics
- Marketing Analyst / Product Analyst / Research Analyst / RevOps Analyst

**Tier 3 (Gated Operations) - Requires analytics keywords (Excel, SQL, Power BI, Tableau, Dashboard, KPI, Reporting, Analysis, Analytics, MIS, Data):**
- Operations Intern / Project Management Intern / Client Success / Implementation
- HR Intern / HR Operations / HR Executive / Recruitment / Talent Acquisition / Logistics

**Tier 3 (Generic Catchall) - Lowest priority:**
- Junior Analyst / Associate Analyst

**Excluded (rejected regardless of match):**
- QA / Quality Assurance / Tester / Testing / SDET
- Software Developer / Java Developer / Web Developer / App Developer / Mobile Developer / Full Stack
- Network Engineer / Cyber
- Tax / Telecaller / Sales Executive / Content Writer / Graphic Design / Video Editor
- Customer Support / Customer Service / Data Entry
- Financial Analyst / Equity Research / Clinical / Pharma / Insurance / Legal / Nursing

**Matching behavior:**
- Word-boundary matching is used for bare technical keywords (python, sql, machine learning) to avoid substring matches
- Bare keywords require a data/analyst/analytics context term in the title to match
- Core keyword matches are never dropped by exclude keywords (e.g., "Power BI Developer" is kept)

## Recent improvements

- **Dedup fix:** Only jobs actually sent in messages are marked as "seen" — overflow jobs (beyond max_jobs cap) remain unmarked and will appear in future runs
- **Concurrent requests:** Internshala uses 5 parallel workers, reducing runtime from 214s to 42s
- **Message splitting:** Telegram messages >4096 chars are automatically split into sequential messages
- **Global remote:** Himalayas WFH branch includes all Entry-level remote jobs globally, not just South India

## One-time setup

### 1. Create a Telegram bot
- Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`,
  follow the prompts. You'll get a **bot token** (looks like
  `123456:ABC-DEF...`).
- Message your new bot anything (so it can message you back).
- Get your **chat ID**: message [@userinfobot](https://t.me/userinfobot),
  it replies with your numeric ID.

### 2. Add secrets in GitHub
Repo → Settings → Secrets and variables → Actions → New repository secret:
- `TELEGRAM_BOT_TOKEN` → your bot token
- `TELEGRAM_CHAT_ID` → your chat ID

The workflow in `.github/workflows/job_bot.yml` runs automatically at
8 AM, 2 PM, and 9 PM IST, and commits the updated state files back to
the repo after each run.

## Testing locally
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
python main.py              # Normal run (sends Telegram message)
python main.py --dry-run    # Dry run (no Telegram send, prints output)
```
Each source prints how many jobs it found and whether it failed, so the
console output (and the GitHub Actions log) shows exactly where a bad
run went wrong. A full run takes ~40 seconds.

Dry-run mode includes per-source, per-role-group, and per-location-tier
reporting, plus the top 10 ranked jobs.

## Scraper fragility

The HTML-backed source needs occasional maintenance; the JSON API doesn't.

`internshala.py` parses job cards by their `/internship/detail/` URL
pattern, **not** by CSS class. That's deliberate: the original
class-based version broke silently after a redesign, returning
"Untitled role" for every job without raising anything — a worse failure
mode than a crash.

If it goes quiet, check whether the site changed its detail-page URL
shape before assuming the parsing itself needs a rewrite.

## Tweaking filters
Everything under `filters:` in `config.yaml` is meant to be edited
freely — role keywords, excluded keywords, locations, stipend
thresholds, max age of postings. No code changes needed.

`role_groups` drives both **what passes** the filter and **what order**
results appear in: list order is priority order. `location_priority` is
the secondary sort within a role tier.

Stipend thresholds are in Rs/month. Pay quoted in another currency is
treated as unknown rather than converted — the job still passes and
sorts at its default rank.

## Adding a new source later
1. Create `sources/newsource.py` with a `fetch(config)` function that
   returns a list of jobs via `job_model.make_job(...)`.
2. Add it to `SOURCE_MODULES` in `main.py`.
3. Add its config block under `sources:` in `config.yaml`, with an
   `enabled` flag.

Sources must never crash the run: `collect_all_jobs()` isolates each one
in a try/except, and anything doing several requests should handle
per-request failures itself too.
