"""
Entry point. Run this file to do one complete cycle:
fetch -> filter -> dedup -> notify -> exit.

No loops, no daemons - designed to be triggered by an external
scheduler (GitHub Actions cron, or a plain cron job) three times a day.
"""

import os
import sys
import yaml

from filter import apply_filters
from dedup import filter_new_jobs
from job_model import job_hash
from priority import sort_by_priority
from notify import format_message, format_digest_message, send_telegram_message
from notify_state import days_since_last_send, record_send

from sources import (
    arbeitnow,
    freshergo,
    himalayas,
    indeed,
    internshala,
    jobicy,
    kerala_gov,
    remoteok,
    technopark_infopark,
)

SOURCE_MODULES = {
    "indeed": indeed,
    "internshala": internshala,
    "freshergo": freshergo,
    "remoteok": remoteok,
    "himalayas": himalayas,
    "jobicy": jobicy,
    "arbeitnow": arbeitnow,
    "technopark_infopark": technopark_infopark,
    "kerala_gov": kerala_gov,
}


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        raw = f.read()
    for key, value in os.environ.items():
        raw = raw.replace(f"${{{key}}}", value)
    return yaml.safe_load(raw)


def deduplicate(jobs):
    """
    Collapses copies of the same posting within a single run, keeping
    the first one seen.

    This is separate from `dedup.py`, which answers "have I already SENT
    this?" across runs. This one answers "did two sources just hand me
    the same job?" - unavoidable now that aggregators re-publish each
    other, and it also stops one listing appearing on several FresherGo
    listing pages from being counted repeatedly. Doing it here means the
    digest path (which bypasses the state file) gets it too.
    """
    seen = set()
    unique = []
    for job in jobs:
        h = job_hash(job)
        if h in seen:
            continue
        seen.add(h)
        unique.append(job)
    return unique


def collect_all_jobs(config):
    all_jobs = []
    for name, module in SOURCE_MODULES.items():
        src_cfg = config["sources"].get(name, {})
        if not src_cfg.get("enabled", False):
            continue
        print(f"[main] fetching from {name}...")
        try:
            jobs = module.fetch(config)
            print(f"[main] {name} returned {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"[main] {name} failed entirely: {e}")
            continue
    return all_jobs


def main():
    config = load_config()

    raw_jobs = deduplicate(collect_all_jobs(config))
    print(f"[main] total raw jobs collected (after cross-source dedup): {len(raw_jobs)}")
    print("[main] sample titles collected:")
    for job in raw_jobs[:15]:
        print(f"  - {job['title']}")

    filtered_jobs = apply_filters(raw_jobs, config)
    print(f"[main] jobs after filtering: {len(filtered_jobs)}")

    new_jobs = filter_new_jobs(filtered_jobs, config)
    print(f"[main] new jobs after dedup: {len(new_jobs)}")

    new_jobs = sort_by_priority(new_jobs, config)

    max_jobs = config.get("output", {}).get("max_jobs_per_message", 10)
    digest_cfg = config.get("digest", {})
    digest_enabled = digest_cfg.get("enabled", False)
    digest_state_file = digest_cfg.get("state_file", "notify_state.json")
    trigger_after_days = digest_cfg.get("trigger_after_days_no_new", 2)

    if new_jobs:
        message = format_message(new_jobs, max_jobs)
        record_send(digest_state_file)
    elif digest_enabled:
        days_quiet = days_since_last_send(digest_state_file)
        print(f"[main] no new jobs; days since last send: {days_quiet}")
        if days_quiet is None or days_quiet >= trigger_after_days:
            print(f"[main] triggering digest (threshold: {trigger_after_days} days)")
            all_current_matches = sort_by_priority(filtered_jobs, config)
            message = format_digest_message(all_current_matches, max_jobs, days_quiet or 0)
            record_send(digest_state_file)
        else:
            message = format_message(new_jobs, max_jobs)
    else:
        message = format_message(new_jobs, max_jobs)

    bot_token = config["telegram"]["bot_token"]
    chat_id = config["telegram"]["chat_id"]

    if not bot_token or bot_token.startswith("${"):
        print("[main] ERROR: TELEGRAM_BOT_TOKEN not set. Skipping send.")
        sys.exit(1)
    if not chat_id or chat_id.startswith("${"):
        print("[main] ERROR: TELEGRAM_CHAT_ID not set. Skipping send.")
        sys.exit(1)

    success = send_telegram_message(bot_token, chat_id, message)
    if not success:
        sys.exit(1)

    print("[main] done.")


if __name__ == "__main__":
    main()