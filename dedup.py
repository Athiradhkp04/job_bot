"""
Tiny state-file based dedup. Stores a hash -> first-seen-date map in
a small JSON file (a few KB at most for realistic job volumes).
Entries older than `prune_after_days` are dropped each run so the
file never grows unbounded.
"""

import json
import os
from datetime import datetime, timedelta
from job_model import job_hash


def load_seen(state_file):
    if not os.path.exists(state_file):
        return {}
    try:
        with open(state_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable state file - start fresh rather than crash
        return {}


def save_seen(state_file, seen):
    with open(state_file, "w") as f:
        json.dump(seen, f, indent=2)


def prune_old(seen, prune_after_days):
    cutoff = datetime.utcnow() - timedelta(days=prune_after_days)
    pruned = {}
    for h, date_str in seen.items():
        try:
            seen_date = datetime.strptime(date_str, "%Y-%m-%d")
            if seen_date >= cutoff:
                pruned[h] = date_str
        except ValueError:
            # Malformed entry - drop it rather than keep bad data
            continue
    return pruned


def identify_new_jobs(jobs, config):
    """
    Returns only the jobs not already present in the state file.
    Does NOT persist them yet - marking as seen happens after
    the message is sent, so only actually-sent jobs get marked.
    """
    dedup_cfg = config.get("dedup", {})
    state_file = dedup_cfg.get("state_file", "seen_jobs.json")
    prune_after_days = dedup_cfg.get("prune_after_days", 30)

    abs_path = os.path.abspath(state_file)
    print(f"[dedup] reading state file from: {abs_path}")

    seen_before_prune = load_seen(state_file)
    print(f"[dedup] state file has {len(seen_before_prune)} entries before pruning")

    seen = prune_old(seen_before_prune, prune_after_days)
    if len(seen) != len(seen_before_prune):
        print(f"[dedup] pruned {len(seen_before_prune) - len(seen)} entries older than {prune_after_days} days")

    new_jobs = []
    already_seen_count = 0

    for job in jobs:
        h = job_hash(job)
        if h not in seen:
            new_jobs.append(job)
        else:
            already_seen_count += 1

    print(f"[dedup] of {len(jobs)} filtered jobs: {len(new_jobs)} new, {already_seen_count} already seen")
    return new_jobs


def mark_jobs_as_seen(jobs, config):
    """
    Marks the given jobs as seen by persisting their hashes to the state file.
    Only call this for jobs that were actually sent in a message.
    """
    dedup_cfg = config.get("dedup", {})
    state_file = dedup_cfg.get("state_file", "seen_jobs.json")
    prune_after_days = dedup_cfg.get("prune_after_days", 30)

    seen = load_seen(state_file)
    seen = prune_old(seen, prune_after_days)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    for job in jobs:
        h = job_hash(job)
        seen[h] = today

    save_seen(state_file, seen)
    print(f"[dedup] marked {len(jobs)} jobs as seen, saved {len(seen)} total entries")


# Legacy function for backward compatibility - now wraps the new flow
def filter_new_jobs(jobs, config):
    """
    Legacy function - now just calls identify_new_jobs + mark_jobs_as_seen.
    Used only for backward compatibility if anything still calls this directly.
    """
    new_jobs = identify_new_jobs(jobs, config)
    mark_jobs_as_seen(new_jobs, config)
    return new_jobs