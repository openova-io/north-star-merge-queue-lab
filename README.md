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
| `.github/workflows/dummy-5.yaml`, `dummy-15.yaml`, `dummy-30.yaml` | Dummy checks that only wait. They stand for workflows of 5, 15 and 30 minutes, scaled down ten times to 30, 90 and 180 seconds. They run on `pull_request` and `merge_group`. |
| `.github/workflows/pin-match.yaml` | Fails when the two version files differ. Runs on `pull_request`, `merge_group` and pushes to `main`. |
| `.github/workflows/push-probe.yaml` | Records who pushed to `main`. It shows whether a push starts the workflows that listen for pushes. |
| `.github/workflows/writer-gha.yaml` | Tries a release-writer push with the workflow's own token. |
| `scripts/release-writer.sh` | Plays the release writer: one commit that moves both files, or two commits (bump, then pin). |
| `scripts/reactive-writer.py` | Calls the release writer after every merge from the queue, as a deploy pipeline would. |
| `scripts/record.py` | Polls the merge queue and `main` and writes what changes. |

The rulesets on `main` and `rc/**` are set through the REST API. The results
are in `evidence/` once the run ends.
