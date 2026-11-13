#!/usr/bin/env python3
"""Summarise one run: per pull request, time from first 'added to the merge queue'
to 'merged', removals from the queue, and how many merge groups were built for it.

Usage: analyze.py <owner/repo> <snapshots.jsonl> <first-pr> <last-pr>
"""
import json
import statistics
import subprocess
import sys
from datetime import datetime

repo, snaps, first, last = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
owner, name = repo.split("/")
Q = """
query($o:String!,$n:String!,$p:Int!){ repository(owner:$o,name:$n){ pullRequest(number:$p){
  title mergeCommit{ oid }
  timelineItems(first:100, itemTypes:[ADDED_TO_MERGE_QUEUE_EVENT, REMOVED_FROM_MERGE_QUEUE_EVENT, MERGED_EVENT]){
    nodes{ __typename
      ... on AddedToMergeQueueEvent { createdAt }
      ... on RemovedFromMergeQueueEvent { createdAt reason beforeCommit{ oid } }
      ... on MergedEvent { createdAt commit{ oid } } } } } } }
"""


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


groups = {}
for line in open(snaps):
    d = json.loads(line)
    for e in d.get("queue", []):
        if e.get("group_head"):
            groups.setdefault(e["pr"], set()).add(e["group_head"])

rows = []
for p in range(first, last + 1):
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={Q}", "-f", f"o={owner}", "-f", f"n={name}",
                          "-F", f"p={p}"], capture_output=True, text=True, check=True).stdout
    pr = json.loads(out)["data"]["repository"]["pullRequest"]
    ev = pr["timelineItems"]["nodes"]
    added = [ts(e["createdAt"]) for e in ev if e["__typename"] == "AddedToMergeQueueEvent"]
    removed = [(e["createdAt"], e["reason"]) for e in ev if e["__typename"] == "RemovedFromMergeQueueEvent"]
    merged = [ts(e["createdAt"]) for e in ev if e["__typename"] == "MergedEvent"]
    secs = int((merged[0] - added[0]).total_seconds()) if added and merged else None
    rows.append({"pr": p, "title": pr["title"], "added": len(added), "removed": removed,
                 "groups_built": len(groups.get(p, ())), "queue_seconds": secs,
                 "merge_commit": (pr["mergeCommit"] or {}).get("oid")})

for r in rows:
    print(json.dumps(r))
vals = [r["queue_seconds"] for r in rows if r["queue_seconds"] is not None]
if vals:
    print(json.dumps({"merged": len(vals), "of": len(rows), "median_seconds": statistics.median(vals),
                      "min_seconds": min(vals), "max_seconds": max(vals),
                      "removals": sum(len(r["removed"]) for r in rows),
                      "groups_built": sum(r["groups_built"] for r in rows)}))
