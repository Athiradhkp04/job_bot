# Job Bot

Finds new job/internship postings matching your filters and sends you a
Telegram message, 3x a day. No dashboards, no auto-apply, no AI summaries.

## How it works
1. Fetches postings from every source enabled in `config.yaml`.
2. Filters them using the rules in `config.yaml` (role keywords, location,
   stipend, age).
3. Drops anything already sent to you (tracked in `seen_jobs.json`).
4. Sends the top matches as one Telegram message, with remote roles in
   their own "Top WFH Jobs" section.
5. Exits. Runs again on the next scheduled trigger.

If nothing new turns up for a couple of days, it sends a "refresh
check-in" digest instead — everything currently matching your filters,
including jobs you've already seen — so a quiet stretch is
distinguishable from a broken bot. Configured under `digest:`.

## Sources

| Source | Type | Status |
|---|---|---|
| Internshala | HTML scrape | **on** — Kerala internships + fresher jobs |
| FresherGo | Embedded JSON | **on** — entry-level only, national + remote |
| RemoteOK | JSON API | **on** — remote |
| Himalayas | JSON API | **on** — remote |
| Jobicy | JSON API | **on** — remote |
| Arbeitnow | JSON API | **on** — remote only (see below) |
| Indeed | — | off — blocks non-browser traffic (403) |
| Technopark/Infopark | — | off — see below |
| Kerala Gov | — | off — JS-rendered, returned 0 jobs |

All sources are free with no API key and no account. Nothing here costs
money to run, which is a hard constraint on adding new ones.

Notes on the ones with quirks:

- **FresherGo** has no Kerala coverage — its Kerala/Kochi/Trivandrum city
  pages exist but return nothing — so it contributes remote roles plus
  the metro cities in `city_slugs`.
- **Arbeitnow** is a general Europe-focused board, not a remote one.
  `remote_only: true` filters out the on-site German-language roles that
  make up most of its volume.
- **Overlap is expected.** FresherGo re-publishes a large share of
  Himalayas and Arbeitnow postings. Dedup keys on the employer-side
  apply URL rather than the listing link, so those copies collapse into
  one entry — see `job_model.job_hash`.

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
run went wrong. A full run takes a few minutes, mostly Internshala and
FresherGo pagination.

## Scraper fragility

The two HTML-backed sources need occasional maintenance; the JSON APIs
don't.

`internshala.py` parses job cards by their `/internship/detail/` URL
pattern, **not** by CSS class. That's deliberate: the original
class-based version broke silently after a redesign, returning
"Untitled role" for every job without raising anything — a worse failure
mode than a crash.

`freshergo.py` reads the JSON payload FresherGo embeds in each listing
page instead of parsing the rendered cards, for the same reason: the
payload holds more (apply URL, exact posted date, structured salary)
and doesn't depend on generated Tailwind class names. If that payload
ever disappears, it falls back to a URL-pattern DOM parse.

If either goes quiet, check whether the site changed its detail-page URL
shape before assuming the parsing itself needs a rewrite.

## Technopark / Infopark

Still off, and the static-HTML path was checked properly this time
rather than assumed:

- **`technopark.org`** — JS-rendered, as before.
- **`technoparkjobs.com`** — a JS shell. Every route (`/`, `/jobs`,
  `/job-search`) returns the same ~2 KB of text with zero job links in
  the HTML.
- **`keralatechjobs.pages.dev`** — genuinely static and parseable, but it
  advertised **1 active job from 1 company** at the time of checking.
  Not worth a source module and a scheduled request 3x a day.

So the only remaining route is a headless browser, which would mean
adding Playwright plus a browser download to every scheduled run for two
secondary sources. Not justified while Internshala still covers Kerala.
Worth re-checking `keralatechjobs.pages.dev` occasionally — if its
listing count grows, it's the cheapest path back in.

## Tweaking filters
Everything under `filters:` in `config.yaml` is meant to be edited
freely — role keywords, excluded keywords, locations, stipend
thresholds, max age of postings. No code changes needed.

`role_groups` drives both **what passes** the filter and **what order**
results appear in: list order is priority order. `location_priority` is
the secondary sort within a role tier.

Stipend thresholds are in Rs/month. Pay quoted in another currency is
treated as unknown rather than converted — the job still passes and
sorts at its default rank. Adding conversion would mean depending on a
live exchange-rate API, which isn't worth it here.

## Adding a new source later
1. Create `sources/newsource.py` with a `fetch(config)` function that
   returns a list of jobs via `job_model.make_job(...)`. Pass
   `apply_url` if the source exposes the employer-side link — that's
   what dedup keys on.
2. Add it to `SOURCE_MODULES` in `main.py`.
3. Add its config block under `sources:` in `config.yaml`, with an
   `enabled` flag.

Sources must never crash the run: `collect_all_jobs()` isolates each one
in a try/except, and anything doing several requests should handle
per-request failures itself too.
