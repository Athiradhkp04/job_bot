# Job Bot

Finds new job/internship postings matching your filters and sends you a
Telegram message, 3x a day. No dashboards, no auto-apply, no AI summaries.

## How it works
1. Fetches postings from Indeed, Internshala, Technopark/Infopark, and
   Knowledge Mission Kerala (govt internships).
2. Filters them using rules in `config.yaml`.
3. Drops anything you've already been sent (tracked in `seen_jobs.json`).
4. Sends up to 10 new matches as one Telegram message.
5. Exits. Runs again on the next scheduled trigger.

## One-time setup

### 1. Create a Telegram bot
- Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`,
  follow the prompts. You'll get a **bot token** (looks like
  `123456:ABC-DEF...`).
- Message your new bot anything (so it can message you back).
- Get your **chat ID**: message [@userinfobot](https://t.me/userinfobot),
  it replies with your numeric ID.

### 2. Push this folder to a GitHub repo
```bash
cd job_bot
git init
git add .
git commit -m "Initial job bot"
git remote add origin <your-repo-url>
git push -u origin main
```

### 3. Add secrets in GitHub
Repo → Settings → Secrets and variables → Actions → New repository secret:
- `TELEGRAM_BOT_TOKEN` → your bot token
- `TELEGRAM_CHAT_ID` → your chat ID

That's it. The workflow in `.github/workflows/job_bot.yml` will run
automatically at 8 AM, 2 PM, and 9 PM IST.

## Testing locally before you rely on it
```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
python main.py
```
Check the console output - each source module prints how many jobs it
found, and whether it failed.

## Important: scraper selectors need verification

I wrote `internshala.py` and `indeed.py` based on their general page
structure, but sites change their HTML without notice, so treat
these as a starting point to verify, not guaranteed-working code.

`technopark_infopark.py` and `kerala_gov.py` are more speculative -
I couldn't load those specific pages to check their real structure,
so their CSS selectors are best-guess placeholders. Before relying
on these two:
1. Run `python main.py` locally and check if they return 0 jobs.
2. If so, open the actual site, right-click a job listing → Inspect,
   and update the `.select(...)` lines in that source file to match
   the real class names / tags.

This is the normal maintenance cost of scraping sites without an
official API - expect to revisit selectors every so often if a site
redesigns.

## Tweaking filters
Everything in the `filters:` section of `config.yaml` is meant to be
edited freely - roles, excluded keywords, locations, max age of
postings. No code changes needed.

## Adding a new source later
1. Create `sources/newsource.py` with a `fetch(config)` function that
   returns a list of jobs via `job_model.make_job(...)`.
2. Add it to `SOURCE_MODULES` in `main.py`.
3. Add its config block under `sources:` in `config.yaml`.
