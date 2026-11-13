#!/usr/bin/env python3
"""Call the release writer after every merge from the queue, as a deploy pipeline would.

Usage: reactive-writer.py <stop-file> <delay-before-bump> <delay-before-pin> [mode]
mode "two" (default): a bump commit, then a pin commit after <delay-before-pin> seconds.
mode "one": one commit that moves both files.
Runs from the lab checkout. Stops when <stop-file> exists.
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

stop, d_bump, d_pin = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
mode = sys.argv[4] if len(sys.argv) > 4 else "two"
remote = os.environ.get("WRITER_REMOTE", "origin")


def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main_head():
    subprocess.run(["git", "fetch", "-q", remote, "main"], check=True)
    sha = subprocess.run(["git", "rev-parse", "FETCH_HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    subj = subprocess.run(["git", "log", "-1", "--format=%s", "FETCH_HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    return sha, subj


def wait(secs):
    end = time.time() + secs
    while time.time() < end and not os.path.exists(stop):
        time.sleep(1)


last, _ = main_head()
print(f"{ts()} start at {last}", flush=True)
while not os.path.exists(stop):
    sha, _ = main_head()
    if sha != last:
        subjects = subprocess.run(["git", "log", "--format=%s", f"{last}..{sha}"],
                                  capture_output=True, text=True, check=True).stdout.splitlines()
        last = sha
        merges = [s for s in subjects if "[release-writer]" not in s]
        if merges:
            print(f"{ts()} queue merge seen at {sha[:12]}: {merges}", flush=True)
            wait(d_bump)
            if os.path.exists(stop):
                break
            if mode == "one":
                subprocess.run(["bash", "scripts/release-writer.sh", "one"])
            else:
                subprocess.run(["bash", "scripts/release-writer.sh", "bump"])
                wait(d_pin)
                subprocess.run(["bash", "scripts/release-writer.sh", "pin"])
            continue
    time.sleep(5)
print(f"{ts()} stop", flush=True)
