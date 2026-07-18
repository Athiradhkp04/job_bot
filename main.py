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
from notify import format_message, send_telegram_message

from sources import indeed, internshala, technopark_infopark, kerala_gov

SOURCE_MODULES = {
    "indeed": indeed,
    "internshala": internshala,
    "technopark_infopark": technopark_infopark,
    "kerala_gov": kerala_gov,
}


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        raw = f.read()
    # Substitute ${ENV_VAR} references with actual environment variables
    for key, value in os.environ.items():
        raw = raw.replace(f"${{{key}}}", value)
    return yaml.safe_load(raw)


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
            # One source failing should never kill the whole run
            print(f"[main] {name} failed entirely: {e}")
            continue
    return all_jobs


def main():
    config = load_config()

    raw_jobs = collect_all_jobs(config)
    print(f"[main] total raw jobs collected: {len(raw_jobs)}")
    print("[main] sample titles collected:")
    for job in raw_jobs[:15]:
        print(f"  - {job['title']}")

    filtered_jobs = apply_filters(raw_jobs, config)
    print(f"[main] jobs after filtering: {len(filtered_jobs)}")

    new_jobs = filter_new_jobs(filtered_jobs, config)
    print(f"[main] new jobs after dedup: {len(new_jobs)}")

    max_jobs = config.get("output", {}).get("max_jobs_per_message", 10)
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