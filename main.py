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
from priority import sort_by_priority
from notify import format_message, format_digest_message, send_telegram_message
from notify_state import days_since_last_send, record_send

from sources import indeed, internshala, technopark_infopark, kerala_gov, himalayas

SOURCE_MODULES = {
    "indeed": indeed,
    "internshala": internshala,
    "technopark_infopark": technopark_infopark,
    "kerala_gov": kerala_gov,
    "himalayas": himalayas,
}


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        raw = f.read()
    for key, value in os.environ.items():
        raw = raw.replace(f"${{{key}}}", value)
    return yaml.safe_load(raw)


def collect_all_jobs(config):
    all_jobs = []
    himalayas_wfh_jobs = []
    himalayas_south_india_jobs = []
    
    for name, module in SOURCE_MODULES.items():
        src_cfg = config["sources"].get(name, {})
        if not src_cfg.get("enabled", False):
            continue
        print(f"[main] fetching from {name}...")
        try:
            if name == "himalayas":
                # Himalayas returns two lists: (wfh_jobs, south_india_jobs)
                wfh, south_india = module.fetch(config)
                himalayas_wfh_jobs.extend(wfh)
                himalayas_south_india_jobs.extend(south_india)
                print(f"[main] {name} returned {len(wfh)} WFH jobs, {len(south_india)} South India jobs")
                all_jobs.extend(wfh)
                all_jobs.extend(south_india)
            else:
                jobs = module.fetch(config)
                print(f"[main] {name} returned {len(jobs)} jobs")
                all_jobs.extend(jobs)
        except Exception as e:
            print(f"[main] {name} failed entirely: {e}")
            continue
    
    return all_jobs, himalayas_wfh_jobs, himalayas_south_india_jobs


def main():
    config = load_config()

    raw_jobs, himalayas_wfh_raw, himalayas_south_india_raw = collect_all_jobs(config)
    print(f"[main] total raw jobs collected: {len(raw_jobs)}")
    print("[main] sample titles collected:")
    for job in raw_jobs[:15]:
        print(f"  - {job['title']}")

    filtered_jobs = apply_filters(raw_jobs, config)
    print(f"[main] jobs after filtering: {len(filtered_jobs)}")

    new_jobs = filter_new_jobs(filtered_jobs, config)
    print(f"[main] new jobs after dedup: {len(new_jobs)}")

    new_jobs = sort_by_priority(new_jobs, config)

    # Separate jobs into Onsite/Hybrid and WFH/Remote sections
    # WFH/Remote: Himalayas jobs with no location restrictions
    # Onsite/Hybrid: Internshala + Himalayas South India jobs
    wfh_jobs = [job for job in new_jobs if job.get("source") == "Himalayas" and job.get("location") == "Remote"]
    onsite_hybrid_jobs = [job for job in new_jobs if job not in wfh_jobs]
    
    print(f"[main] WFH/Remote jobs: {len(wfh_jobs)}, Onsite/Hybrid jobs: {len(onsite_hybrid_jobs)}")

    max_jobs = config.get("output", {}).get("max_jobs_per_message", 10)
    digest_cfg = config.get("digest", {})
    digest_enabled = digest_cfg.get("enabled", False)
    digest_state_file = digest_cfg.get("state_file", "notify_state.json")
    trigger_after_days = digest_cfg.get("trigger_after_days_no_new", 2)

    if new_jobs:
        message = format_message(onsite_hybrid_jobs, max_jobs, wfh_jobs=wfh_jobs)
        record_send(digest_state_file)
    elif digest_enabled:
        days_quiet = days_since_last_send(digest_state_file)
        print(f"[main] no new jobs; days since last send: {days_quiet}")
        if days_quiet is None or days_quiet >= trigger_after_days:
            print(f"[main] triggering digest (threshold: {trigger_after_days} days)")
            all_current_matches = sort_by_priority(filtered_jobs, config)
            # Separate for digest too
            wfh_digest = [job for job in all_current_matches if job.get("source") == "Himalayas" and job.get("location") == "Remote"]
            onsite_digest = [job for job in all_current_matches if job not in wfh_digest]
            message = format_digest_message(onsite_digest, max_jobs, days_quiet or 0, wfh_jobs=wfh_digest)
            record_send(digest_state_file)
        else:
            message = format_message(onsite_hybrid_jobs, max_jobs, wfh_jobs=wfh_jobs)
    else:
        message = format_message(onsite_hybrid_jobs, max_jobs, wfh_jobs=wfh_jobs)

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