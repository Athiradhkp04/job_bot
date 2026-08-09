# Devin Handover — Job Bot v2

## Before anything else: check for unfinished work

This project was previously being worked on by Windsurf, locally, on my
machine. That session ended abruptly (my laptop's Windsurf shortcut
broke after shutdown — unrelated to the project itself). Before starting
new work:

1. Check `git log` and `git branch -a` on the repo for any commits or
   branches that aren't merged into `main` — there may be uncommitted or
   unmerged work from that session.
2. Check for any open pull requests.
3. If you find unfinished work, tell me what it is and what state it's
   in before proceeding — don't silently continue past it or overwrite
   it.

Repo: `github.com/Athiradhkp04/job_bot` (private).

---

## Step 1 — Read existing context first, in this order

1. `README.md` — project setup, architecture, how it runs
2. `WINDSURF_BRIEF.md` (already in the repo) — the previous iteration's
   brief: goals, constraints, and freedoms for this exact iteration.
   Everything in it still applies to you, not just to Windsurf — read it
   as if it were addressed to you directly.
3. `jobbot_v2_todo_windsurf.md` (already in the repo) — verified research
   for this iteration. Sources marked "confirmed" were checked against
   live data directly — treat them as fact, don't re-verify from
   scratch. Sources marked "not verified" or flagged as open questions
   still need checking.

Then skim `main.py`, `job_model.py`, `filter.py`, and
`sources/internshala.py` to see the existing pattern every new source
module must follow.

---

## Step 2 — What you're building

Same three goals as in `WINDSURF_BRIEF.md`:
1. Integrate FresherGo as a new source (highest priority — already
   confirmed scrapeable, see the research doc for verified URLs)
2. Add the 4 verified free WFH APIs (RemoteOK, Himalayas, Jobicy,
   Arbeitnow) as additional sources
3. Add a distinct "Top WFH Jobs" section to the Telegram output
4. Attempt Technopark/Infopark via the aggregator-site path before
   considering a headless browser

All constraints and freedoms defined in `WINDSURF_BRIEF.md` — free-to-
operate only, no database, config-driven, follow the existing
`fetch(config) -> list[job_dict]` module contract, parse by stable URL
patterns not fragile CSS — apply exactly as written there.

---

## Step 3 — How you work differs from how Windsurf worked (read this)

You operate in your own sandboxed cloud environment via the GitHub
integration, not on my local machine. Practical implications:

- **You'll be working via commits/PRs to the GitHub repo directly**, not
  editing files I can see in real time on my laptop. Open a feature
  branch for this work rather than committing straight to `main`.
- **Secrets:** the repo's GitHub Actions workflow already reads
  `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from GitHub repository
  secrets — you don't need those to build or test source-module logic
  itself, only if you need to test an actual end-to-end Telegram send.
  If you do need any credential to test something, ask me and I'll
  provide it through Devin's Secrets manager — never paste one into a
  chat message.
- **The universal guardrails in my Devin Knowledge Base apply to this
  project too** — nothing about this being "just a personal project"
  exempts it from those. In particular: don't make this repo public
  without asking me directly and separately, even if it comes up
  naturally while working (e.g. while drafting portfolio content).

---

## Step 4 — Definition of done (same as before, restated)

- FresherGo source module built and tested against real fetched data
- At least the 4 WFH APIs integrated
- Visible WFH section in Telegram output when matches exist
- Technopark/Infopark fixed via static-HTML path, or a written note
  explaining why that path didn't work
- `config.yaml` updated, following the existing per-source `enabled` flag
  pattern
- Existing Kerala/India Internshala pipeline still works exactly as
  before — nothing regresses
- A real manual run completes end to end without errors
- Open a PR against `main` rather than pushing directly, so I can review
  before it goes live on the automated 3x/day schedule
