#!/usr/bin/env bash
# Add pull requests to the merge queue one at a time, <gap> seconds apart.
# Usage: stagger-enqueue.sh <gap-seconds> <number>...
set -uo pipefail
gap="$1"; shift
for n in "$@"; do bash "$(dirname "$0")/enqueue.sh" "$n"; sleep "$gap"; done
