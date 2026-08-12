# Job Bot

Finds new job/internship postings matching your filters and sends you a
Telegram message, 3x a day. No dashboards, no auto-apply, no AI summaries.

## How it works
1. Fetches postings from Internshala (South India) and Himalayas (Entry-level remote jobs).
2. Filters them using the rules in `config.yaml` (role keywords, location, stipend, experience level, age).
3. Drops anything already sent to you (tracked in `seen_jobs.json`).
4. Sends the top matches as one Telegram message with two sections:
   - **Onsite/Hybrid Jobs** — Internshala (South India) + Himalayas (South India onsite/hybrid)
   - **WFH/Remote Jobs** — Himalayas (Entry-level remote jobs globally)
5. Exits. Runs again on the next scheduled trigger.

If nothing new turns up for a couple of days, it sends a "refresh
check-in" digest instead — everything currently matching your filters,
including jobs you've already seen — so a quiet stretch is
distinguishable from a broken bot. Configured under `digest:`.

## Sources

|| Source | Type | Status |
||---|---|---|
|| Internshala | HTML scrape | **on** — South India internships + fresher jobs (19 locations) |
|| Himalayas | JSON API | **on** — Entry-level remote jobs globally + South India onsite/hybrid |
|| Indeed | — | off — blocks non-browser traffic (403) |
|| FresherGo | — | off — requires paid plan for actual applications |
|| RemoteOK | — | off — requires paid plan for actual applications |
|| Jobicy | — | off — requires paid plan for actual applications |
|| Arbeitnow | — | off — requires paid plan for actual applications |
|| Technopark/Infopark | — | off — JS-rendered |
|| Kerala Gov | — | off — JS-rendered, returned 0 jobs |

All active sources are free with no API key and no account. Nothing here costs
money to run, which is a hard constraint on adding new ones.

Notes on the active sources:

- **Internshala** fetches from 19 South India locations (Kerala, Tamil Nadu, Karnataka, Andhra Pradesh, Telangana, Puducherry cities) using concurrent requests (5 at a time) to manage runtime. Uses URL-pattern parsing for stability, not fragile CSS classes.
- **Himalayas** provides Entry-level remote jobs globally (since Entry-level roles are concentrated outside South India) with South India locations prioritized via the existing ranking system. Also includes South India onsite/hybrid jobs.
- **Experience filtering** rejects jobs requiring >2 years experience upper bound, prioritizes "fresher" keyword when present.

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
python main.py
```
Each source prints how many jobs it found and whether it failed, so the
console output (and the GitHub Actions log) shows exactly where a bad
run went wrong. A full run takes ~40 seconds.

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
