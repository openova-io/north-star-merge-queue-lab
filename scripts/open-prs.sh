#!/usr/bin/env bash
# Open <count> small pull requests for one run. Each adds one file under work/.
# Usage: open-prs.sh <run-label> <count>
# PR_FOOTER, when set, is appended to each pull-request body; COMMIT_TRAILER to each commit.
set -euo pipefail
label="$1"; count="$2"
git fetch -q origin main
for n in $(seq 1 "$count"); do
  br="lab/$label-$n"
  git checkout -q -B "$br" origin/main
  echo "run $label, pull request $n" > "work/$label-$n.txt"
  git add "work/$label-$n.txt"
  git commit -q -m "lab: add work file $label-$n" ${COMMIT_TRAILER:+-m "$COMMIT_TRAILER"}
  git push -q -f origin "$br"
  body="Lab pull request $label-$n. It adds one file under work/ and nothing else.

Work-Package: LAB-$label-$n"
  [ -n "${PR_FOOTER:-}" ] && body="$body

$PR_FOOTER"
  gh pr create --base main --head "$br" --title "lab: $label-$n" --body "$body" >/dev/null
  echo "$(date -u +%FT%TZ) opened $br"
done
git checkout -q --detach origin/main
