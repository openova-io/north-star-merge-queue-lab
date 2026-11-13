#!/usr/bin/env bash
# Wait until the head of main is a bump commit (the window between the two
# release-writer commits), then open one pull request through the API.
# Usage: window-pr.sh <run-label>
set -uo pipefail
repo=openova-io/north-star-merge-queue-lab
while :; do
  s=$(gh api "repos/$repo/commits/main" --jq .commit.message 2>/dev/null | head -1)
  case "$s" in *"bump chart version"*) echo "$(date -u +%FT%TZ) window open: $s"; bash "$(dirname "$0")/api-prs.sh" "$1" 1; exit 0;; esac
  sleep 3
done
