#!/usr/bin/env bash
# Open <count> small pull requests through the API only (no checkout needed),
# so the release writer can keep using the local checkout meanwhile.
# Usage: api-prs.sh <run-label> <count>
# PR_FOOTER, when set, is appended to each pull-request body; COMMIT_TRAILER to each commit.
set -euo pipefail
repo=openova-io/north-star-merge-queue-lab
label="$1"; count="$2"
base=$(gh api "repos/$repo/git/ref/heads/main" --jq .object.sha)
for n in $(seq 1 "$count"); do
  br="lab/$label-$n"
  gh api -X POST "repos/$repo/git/refs" -f ref="refs/heads/$br" -f sha="$base" >/dev/null
  msg="lab: add work file $label-$n"
  [ -n "${COMMIT_TRAILER:-}" ] && msg="$msg

$COMMIT_TRAILER"
  gh api -X PUT "repos/$repo/contents/work/$label-$n.txt" -f message="$msg" -f branch="$br" \
    -f content="$(printf 'run %s, pull request %s\n' "$label" "$n" | base64 -w0)" >/dev/null
  body="Lab pull request $label-$n. It adds one file under work/ and nothing else.

Work-Package: LAB-$label-$n"
  [ -n "${PR_FOOTER:-}" ] && body="$body

$PR_FOOTER"
  url=$(gh pr create -R "$repo" --base main --head "$br" --title "lab: $label-$n" --body "$body")
  echo "$(date -u +%FT%TZ) opened $br $url"
done
