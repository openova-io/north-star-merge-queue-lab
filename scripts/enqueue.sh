#!/usr/bin/env bash
# Add pull requests to the merge queue of main. Usage: enqueue.sh <number>...
set -euo pipefail
repo=openova-io/north-star-merge-queue-lab
for n in "$@"; do
  id=$(gh api "repos/$repo/pulls/$n" --jq .node_id)
  gh api graphql -f query='mutation($id:ID!){ enqueuePullRequest(input:{pullRequestId:$id}){ mergeQueueEntry{ position state } } }' -f id="$id" \
    --jq "\"$(date -u +%FT%TZ) enqueued #$n position=\(.data.enqueuePullRequest.mergeQueueEntry.position) state=\(.data.enqueuePullRequest.mergeQueueEntry.state)\""
done
