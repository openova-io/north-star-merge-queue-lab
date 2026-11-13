#!/usr/bin/env python3
"""Poll the merge queue of main and the head of main; append each change as one JSON line.

Usage: record.py <owner/repo> <out.jsonl> <stop-file> [interval-seconds]
Stops when <stop-file> exists. Uses the gh CLI for GraphQL.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

repo, out, stop = sys.argv[1], sys.argv[2], sys.argv[3]
interval = float(sys.argv[4]) if len(sys.argv) > 4 else 5
owner, name = repo.split("/")

QUERY = """
query($o:String!,$n:String!){ repository(owner:$o,name:$n){
  ref(qualifiedName:"refs/heads/main"){ target{ oid ... on Commit { messageHeadline } } }
  mergeQueue(branch:"main"){ entries(first:50){ nodes{
    position state enqueuedAt estimatedTimeToMerge
    headCommit{ oid } baseCommit{ oid } pullRequest{ number } } } }
}}
"""

last = None
while not os.path.exists(stop):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        raw = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"o={owner}", "-f", f"n={name}"],
            capture_output=True, text=True, timeout=30, check=True).stdout
        r = json.loads(raw)["data"]["repository"]
        snap = {
            "main": r["ref"]["target"]["oid"],
            "main_subject": r["ref"]["target"].get("messageHeadline"),
            "queue": [
                {"pr": e["pullRequest"]["number"], "pos": e["position"], "state": e["state"],
                 "group_head": (e["headCommit"] or {}).get("oid"),
                 "base": (e["baseCommit"] or {}).get("oid"), "enqueued": e["enqueuedAt"]}
                for e in r["mergeQueue"]["entries"]["nodes"]] if r["mergeQueue"] else [],
        }
    except Exception as exc:  # keep polling through transient API errors
        snap = {"error": str(exc)[:200]}
    if snap != last:
        with open(out, "a") as f:
            f.write(json.dumps({"t": now, **snap}) + "\n")
        last = snap
    time.sleep(interval)
