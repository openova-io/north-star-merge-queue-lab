# north-star-merge-queue-lab

This is a throwaway repository for one experiment. It is archived when the
experiment ends and is kept only as evidence. Nothing here is product code.

The question: how does a GitHub merge queue behave when a release-writer bot
pushes version-bump commits straight to `main` while pull requests wait in the
queue?

## What is in it

| Path | Role |
|---|---|
| `release/chart-version`, `release/slot-pin` | Two version files. The release writer moves them. A consistent `main` has the same value in both. |
| `work/` | Files that the lab pull requests add. They never touch `release/`. |
| `scripts/fake-ci.py` | A CI stand-in that needs no runner. It posts the required commit statuses `dummy-5`, `dummy-15` and `dummy-30` after 30, 90 and 180 seconds (they stand for workflows of 5, 15 and 30 minutes, scaled down ten times), and `pin-match`, which fails when the two version files differ in the tested tree. It does this for every pull-request head and every merge-group head, and it records the queue and `main` every 3 seconds. The organisation's hosted runners were saturated, so Actions jobs would have measured runner waits, not the queue. |
| `.github/workflows/probe.yaml` | One small Actions job on `pull_request`, `merge_group` and pushes to `main`. It records the event, who pushed, the tested commit message and the two version files. It shows whether Actions runs on the merge-group commit and whether a push starts the workflows that listen for pushes. |
| `.github/workflows/writer-gha.yaml` | Tries a release-writer push with the workflow's own token. |
| `scripts/release-writer.sh` | Plays the release writer: one commit that moves both files, or two commits (bump, then pin). |
| `scripts/reactive-writer.py` | Calls the release writer after every merge from the queue, as a deploy pipeline would. |
| `scripts/open-prs.sh` | Opens the small lab pull requests of one run. |

The rulesets on `main` and `rc/**` are set through the REST API. The results
are in `evidence/RESULTS.md`; the raw logs are next to it.

`scripts/enqueue.sh`, `scripts/stagger-enqueue.sh`, `scripts/api-prs.sh`,
`scripts/window-pr.sh`, `scripts/analyze.py` and `scripts/collect-runs.py`
drive the runs and read the results.
