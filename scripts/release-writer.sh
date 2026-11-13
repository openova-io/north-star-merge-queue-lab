#!/usr/bin/env bash
# Plays the release writer: a bot that pushes version-bump commits straight to
# main, outside the merge queue.
#
#   release-writer.sh one          one commit that moves chart-version and slot-pin together
#   release-writer.sh bump         commit 1: move chart-version only (main is inconsistent after it)
#   release-writer.sh pin          commit 2: move slot-pin to the value of chart-version
#   release-writer.sh two <secs>   bump, wait <secs>, pin
#
# WRITER_REMOTE picks the remote (default origin), so the same script pushes
# with a deploy key, a user token or the workflow token. WRITER_TRAILER, when
# set, is appended to each commit message.
set -euo pipefail

remote="${WRITER_REMOTE:-origin}"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

sync() {
  git fetch -q "$remote" main
  git checkout -q -B writer FETCH_HEAD
}

next_version() { awk -F. '{printf "%d.%d.%d\n", $1, $2, $3 + 1}' release/chart-version; }

commit() {
  git add release/
  if [ -n "${WRITER_TRAILER:-}" ]; then
    git commit -q -m "$1" -m "$WRITER_TRAILER"
  else
    git commit -q -m "$1"
  fi
}

push() {
  local out rc
  set +e
  out=$(git push "$remote" HEAD:refs/heads/main 2>&1)
  rc=$?
  set -e
  echo "$(ts) push rc=$rc sha=$(git rev-parse HEAD) subject=$(git log -1 --format=%s)"
  echo "$out" | sed 's/^/  | /'
  last_out="$out"
  return $rc
}

# Retry only when the queue moved main between our fetch and our push.
# A refusal by a rule is final.
with_retry() {
  local i
  for i in 1 2 3; do
    last_out=""
    if "$@"; then return 0; fi
    case "$last_out" in
      *"fetch first"*|*"non-fast-forward"*|*"stale info"*) echo "$(ts) retry $i: main moved under us" ;;
      *) return 1 ;;
    esac
  done
  return 1
}

one() {
  sync
  local v; v=$(next_version)
  echo "$v" > release/chart-version
  echo "$v" > release/slot-pin
  commit "chore(release): bump and pin $v [release-writer]"
  push
}

bump() {
  sync
  local v; v=$(next_version)
  echo "$v" > release/chart-version
  commit "chore(release): bump chart version to $v [release-writer]"
  push
}

pin() {
  sync
  local v; v=$(cat release/chart-version)
  echo "$v" > release/slot-pin
  commit "chore(release): pin slot to $v [release-writer]"
  push
}

case "${1:-}" in
  one)  with_retry one ;;
  bump) with_retry bump ;;
  pin)  with_retry pin ;;
  two)  with_retry bump; echo "$(ts) waiting ${2:-60}s before the pin commit"; sleep "${2:-60}"; with_retry pin ;;
  *)    echo "usage: $0 one|bump|pin|two <secs>" >&2; exit 2 ;;
esac
