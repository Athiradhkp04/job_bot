# Windsurf Brief — Job Bot v2 Iteration

Read this whole document before writing any code. It tells you what to
read first, what you're building, what you must not break, and where
you have real freedom to make your own calls.

---

## Step 1 — Get oriented in the existing project

This is not a new project. It's an existing, working, deployed bot.
Location: `C:\Users\athir\Projects\job_bot` (local clone of a private
GitHub repo at `github.com/Athiradhkp04/job_bot`).

**Before touching anything, read `README.md` in the project root.** It
covers setup, how the pipeline works end to end, and known fragility
points. Do not skip this — the codebase has real history behind
decisions that aren't obvious from the code alone (e.g. why the
Internshala scraper parses by URL pattern instead of CSS class — that
was a lesson learned the hard way, not an arbitrary choice).

After the README, skim the actual source files to confirm your mental
model matches reality:
- `main.py` — orchestrates the whole pipeline, single entry point
- `job_model.py` — the normalized job shape every source must produce
- `filter.py` — role/location/stipend/age filtering logic
- `priority.py` — two-key sort (role tier, then location tier)
- `dedup.py` — state-file based deduplication with pruning
- `notify.py` — Telegram message formatting and sending
- `notify_state.py` — tracks last-send-date for the digest feature
- `sources/internshala.py` — the only currently-active source; **read
  this one closely**, it's the reference pattern every new source module
  should follow
- `config.yaml` — all tunable behavior lives here; no code changes
  needed to adjust filters, priorities, or thresholds
- `.github/workflows/job_bot.yml` — how this runs (GitHub Actions cron,
  3x/day, commits state files back to the repo after each run)

Then read `jobbot_v2_todo_windsurf.md` (provided alongside this brief)
— that's the verified research for this specific iteration: confirmed
working sources, confirmed dead ends, and what still needs testing.
Everything in that document was checked against live sources, not
guessed — treat its "confirmed" vs "not verified" labels as accurate.

---

## Step 2 — What this iteration is actually trying to achieve

Three goals, in priority order:

1. **Add credible new job sources beyond Internshala** — primarily
   FresherGo (freshergo.com), which the research doc confirms is
   scrapeable and fresher-specific. Secondarily, the four verified free
   WFH APIs (RemoteOK, Himalayas, Jobicy, Arbeitnow).
2. **Add a distinct "Top WFH Jobs" section** to the Telegram message,
   visually separate from the main Kerala/India-focused job list,
   sourced only from globally credible, known companies (i.e., roles
   verified as coming from an official company career page, not a
   third-party's opinion of what's legitimate).
3. **Attempt to fix Technopark/Infopark** via the two aggregator sites
   identified in the research doc, before considering a headless-browser
   rebuild.

Indeed, Naukri, Foundit, and the Kerala Gov source are explicitly OUT of
scope this iteration — confirmed dead ends, don't revisit them.

---

## Step 3 — Constraints (do not violate these without asking first)

These aren't preferences — they're the actual reasons this project is
built the way it is, and breaking them would undo real decisions:

- **Must stay free to operate indefinitely.** No paid APIs, no paid
  scraping services, no infrastructure requiring a credit card. This is
  why Indeed/Naukri/Foundit are excluded — every real option for them
  costs money. If a new source requires payment at any tier beyond a
  free tier with no card required, don't add it — flag it instead.
- **No database.** State persistence stays as flat JSON files
  (`seen_jobs.json`, `notify_state.json`) committed back to the repo by
  the GitHub Actions workflow. This was a deliberate choice, not a
  limitation — don't "upgrade" to SQLite or Postgres.
- **No headless browser unless genuinely necessary.** Try the static-HTML
  path for Technopark/Infopark first. Only reach for Playwright if that
  fails, and even then, scope it narrowly — don't restructure the whole
  project around browser automation for two secondary sources.
- **New sources must follow the existing module contract.** Every
  `sources/*.py` file must expose a `fetch(config) -> list[job_dict]`
  function, returning jobs built via `job_model.make_job(...)`. Don't
  invent a parallel data path — `main.py`, `filter.py`, `priority.py`,
  and `notify.py` all assume this one shape. This is what let the
  original bot go from 1 source to a filterable, prioritized multi-role
  system without rewriting the pipeline — preserve that.
- **Parse by stable patterns, not fragile CSS selectors.** The
  Internshala scraper was rewritten once already after a site redesign
  silently broke CSS-class-based parsing (returned `"Untitled role"` for
  every job, with no errors thrown — a worse failure mode than a crash).
  Any new HTML-scraping source (not JSON API) should identify listings by
  URL pattern or another structural signal that's unlikely to change on
  a redesign, the same way `internshala.py` and the FresherGo research
  both point toward doing.
- **Config-driven, not hardcoded.** Role keywords, location rules,
  stipend thresholds, and source enable/disable flags all belong in
  `config.yaml`. If you're tempted to hardcode a value "just for now,"
  don't — that's exactly the pattern this project was built to avoid.
- **Every external fetch needs a real try/except.** One source failing
  (rate limit, timeout, site down) must never crash the whole run — see
  how `collect_all_jobs()` in `main.py` already isolates per-source
  failures. Follow that pattern for every new source.

---

## Step 4 — Where you have real freedom

- **How you structure the FresherGo source module internally** — the
  research doc gives you confirmed URLs and field availability, not a
  prescribed code structure. Design the parser however's cleanest, as
  long as it follows the `fetch(config) -> list[job_dict]` contract.
- **Whether the WFH section is a second Telegram message or a second
  section within one message.** This wasn't decided in planning — pick
  whichever is cleaner to implement well, and document the choice in a
  code comment so it's not mysterious later.
- **How aggressively to paginate each new source.** Follow Internshala's
  precedent (`max_pages_per_category` in config, stop early on a short
  page) but the exact page limits per source are your call based on
  what each source's actual volume looks like.
- **Whether WFH postings share the existing `role_groups` filter or get
  their own matching logic.** The research doc flags this as an open
  question — reasonable arguments exist both ways (consistency vs.
  global companies phrasing titles differently than Indian internship
  boards). Make a call, document why, and it's fine even if it's later
  revisited.
- **Exact company list for the "curated highlight" source** (Priority 3
  in the research doc) — the 6 confirmed companies are a floor, not a
  ceiling. If you verify more companies via FresherGo's own search
  (`freshergo.com/search?q={company}`) and confirm they're legitimate,
  feel free to add them.
- **Code style and internal organization** — match the existing
  project's conventions (docstrings explaining *why*, not just what;
  print-based logging for GitHub Actions log visibility) but you're not
  constrained to mirror `internshala.py`'s exact internal structure if a
  cleaner approach fits a given source better.

---

## Step 5 — Definition of done for this iteration

- FresherGo source module built, tested against real fetched data,
  returning properly normalized jobs
- At least the 4 WFH APIs integrated as additional sources
- A visibly distinct WFH section appears in the Telegram output when WFH
  matches exist
- Technopark/Infopark either fixed via the static-HTML path, or a clear
  written note explaining why that path didn't work and headless-browser
  effort wasn't justified this iteration
- `config.yaml` updated to enable/configure all new sources, following
  the existing pattern (each source has an `enabled` flag)
- Nothing existing breaks — the current Kerala/India Internshala pipeline
  keeps working exactly as it does today
- A quick manual run (not just unit-level testing) confirming the full
  pipeline — fetch through Telegram send — still completes without
  errors

If something in the research doc turns out to be wrong once you actually
build against it (e.g. FresherGo's structure has changed, or a "not
verified" company turns out to have no real board), that's expected —
update the finding, don't silently work around it.
