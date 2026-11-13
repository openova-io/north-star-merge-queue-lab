#!/usr/bin/env python3
"""Write every Actions run of the lab with its job timing to a TSV file.

Usage: collect-runs.py <owner/repo> <out.tsv>
Columns: run id, workflow, event, head sha, head branch, actor, conclusion,
job created, job started, job completed, runner wait in seconds.
"""
import json
import subprocess
import sys
from datetime import datetime

repo, out = sys.argv[1], sys.argv[2]


def api(path, jq=None):
    args = ["gh", "api", "--paginate", path] + (["--jq", jq] if jq else [])
    return subprocess.run(args, capture_output=True, text=True, timeout=120).stdout


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


SEL = "{id, name, event, head_sha, head_branch, actor: {login: .actor.login}, conclusion, status}"
runs = [json.loads(line) for line in
        api(f"/repos/{repo}/actions/runs?per_page=100", f".workflow_runs[] | {SEL}").splitlines() if line.strip()]
rows = []
for r in runs:
    jobs = [json.loads(line) for line in api(f"/repos/{repo}/actions/runs/{r['id']}/jobs",
                                             ".jobs[] | {created_at, started_at, completed_at}").splitlines() if line.strip()]
    for j in jobs or [{}]:
        c, s, e = ts(j.get("created_at")), ts(j.get("started_at")), ts(j.get("completed_at"))
        wait = int((s - c).total_seconds()) if c and s else ""
        rows.append([r["id"], r["name"], r["event"], r["head_sha"], r["head_branch"], r["actor"]["login"],
                     r.get("conclusion") or r["status"], j.get("created_at", ""), j.get("started_at") or "",
                     j.get("completed_at") or "", wait])
rows.sort(key=lambda x: x[7] or "")
with open(out, "w") as f:
    f.write("run\tworkflow\tevent\thead_sha\thead_branch\tactor\tconclusion\tjob_created\tjob_started\tjob_completed\trunner_wait_s\n")
    for row in rows:
        f.write("\t".join(str(x) for x in row) + "\n")
print(len(rows), "rows")
