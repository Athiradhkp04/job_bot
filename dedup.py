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


def filter_new_jobs(jobs, config):
    """
    Returns only the jobs not already present in the state file,
    and updates + saves the state file with the new jobs' hashes.
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

    today = datetime.utcnow().strftime("%Y-%m-%d")
    new_jobs = []
    already_seen_count = 0

    for job in jobs:
        h = job_hash(job)
        if h not in seen:
            new_jobs.append(job)
            seen[h] = today
        else:
            already_seen_count += 1

    print(f"[dedup] of {len(jobs)} filtered jobs: {len(new_jobs)} new, {already_seen_count} already seen")

    save_seen(state_file, seen)
    print(f"[dedup] saved {len(seen)} total entries back to state file")
    return new_jobs