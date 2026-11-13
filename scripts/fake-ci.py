#!/usr/bin/env python3
"""A CI stand-in that needs no runner, plus the queue recorder.

The organisation's hosted-runner pool is shared and was saturated during the
experiment, so the timed dummy checks are posted as commit statuses from this
script instead of Actions jobs. The merge queue treats a required commit status
exactly like a required check run.

For every new pull-request head and every new merge-group head it posts:
  dummy-5   success after  30 s  (stands for 5 minutes)
  dummy-15  success after  90 s  (stands for 15 minutes)
  dummy-30  success after 180 s  (stands for 30 minutes)
  pin-match after 5 s: success when release/chart-version == release/slot-pin
            in the tested tree (the PR's merge commit, or the merge-group head), else failure
It also appends every change of (main head, queue entries) to <snapshots.jsonl>.

Usage: fake-ci.py <owner/repo> <snapshots.jsonl> <statuses.jsonl> <stop-file>
"""
import heapq
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

repo, snap_out, stat_out, stop = sys.argv[1:5]
owner, name = repo.split("/")
DURATIONS = {"dummy-5": 30, "dummy-15": 90, "dummy-30": 180}
PIN_DELAY = 5

Q = """
query($o:String!,$n:String!){ repository(owner:$o,name:$n){
  ref(qualifiedName:"refs/heads/main"){ target{ oid ... on Commit { messageHeadline } } }
  pullRequests(states:OPEN, first:50){ nodes{ number headRefOid potentialMergeCommit{ oid } } }
  mergeQueue(branch:"main"){ entries(first:50){ nodes{
    position state enqueuedAt headCommit{ oid } baseCommit{ oid } pullRequest{ number } } } }
}}
"""
FILES = """
query($o:String!,$n:String!,$a:String!,$b:String!){ repository(owner:$o,name:$n){
  a: object(expression:$a){ ... on Blob { text } }
  b: object(expression:$b){ ... on Blob { text } }
}}
"""


def append(path, obj):
    # The host disk can be full for a moment; GitHub keeps the authoritative record.
    try:
        with open(path, "a") as f:
            f.write(json.dumps(obj) + "\n")
    except OSError:
        pass


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gql(query, **v):
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, val in v.items():
        args += ["-f", f"{k}={val}"]
    out = subprocess.run(args, capture_output=True, text=True, timeout=30, check=True).stdout
    return json.loads(out)["data"]["repository"]


def post(sha, context, state, desc, kind, ref):
    rc = subprocess.run(
        ["gh", "api", "-X", "POST", f"/repos/{repo}/statuses/{sha}", "-f", f"state={state}",
         "-f", f"context={context}", "-f", f"description={desc}"],
        capture_output=True, text=True, timeout=30).returncode
    append(stat_out, {"t": now(), "sha": sha, "kind": kind, "ref": ref,
                      "context": context, "state": state, "desc": desc, "rc": rc})


def pin_state(tree_sha):
    r = gql(FILES, o=owner, n=name, a=f"{tree_sha}:release/chart-version", b=f"{tree_sha}:release/slot-pin")
    v, p = (r["a"] or {}).get("text", "").strip(), (r["b"] or {}).get("text", "").strip()
    return ("success" if v == p else "failure"), f"chart-version={v} slot-pin={p}"


seen = set()
events = []  # heap of (due, seq, sha, context, kind, ref, tree)
seq = 0
last_snap = None
live_groups = set()

while not os.path.exists(stop):
    try:
        r = gql(Q, o=owner, n=name)
    except Exception as exc:
        append(snap_out, {"t": now(), "error": str(exc)[:200]})
        time.sleep(3)
        continue
    entries = r["mergeQueue"]["entries"]["nodes"] if r["mergeQueue"] else []
    snap = {"main": r["ref"]["target"]["oid"], "main_subject": r["ref"]["target"].get("messageHeadline"),
            "queue": [{"pr": e["pullRequest"]["number"], "pos": e["position"], "state": e["state"],
                       "group_head": (e["headCommit"] or {}).get("oid"),
                       "base": (e["baseCommit"] or {}).get("oid"), "enqueued": e["enqueuedAt"]}
                      for e in entries]}
    if snap != last_snap:
        append(snap_out, {"t": now(), **snap})
        last_snap = snap
    t = time.time()
    targets = []
    for pr in r["pullRequests"]["nodes"]:
        tree = (pr["potentialMergeCommit"] or {}).get("oid")
        if tree:
            targets.append((pr["headRefOid"], "pr", f"#{pr['number']}", tree))
    live_groups = set()
    for e in entries:
        h = (e["headCommit"] or {}).get("oid")
        if h:
            live_groups.add(h)
            targets.append((h, "group", f"#{e['pullRequest']['number']}", h))
    for sha, kind, ref, tree in targets:
        if sha in seen:
            continue
        seen.add(sha)
        for ctx, d in DURATIONS.items():
            seq += 1
            heapq.heappush(events, (t + d, seq, sha, ctx, kind, ref, tree))
        seq += 1
        heapq.heappush(events, (t + PIN_DELAY, seq, sha, "pin-match", kind, ref, tree))
    while events and events[0][0] <= time.time():
        _, _, sha, ctx, kind, ref, tree = heapq.heappop(events)
        if kind == "group" and sha not in live_groups:
            append(stat_out, {"t": now(), "sha": sha, "kind": kind, "ref": ref, "context": ctx,
                              "state": "skipped", "desc": "group no longer in the queue"})
            continue
        if ctx == "pin-match":
            state, desc = pin_state(tree)
        else:
            state, desc = "success", f"waited {DURATIONS[ctx]} s"
        post(sha, ctx, state, desc, kind, ref)
    time.sleep(3)
