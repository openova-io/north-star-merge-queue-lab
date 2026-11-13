# Results of the merge-queue experiment (2026-11-13)

The question: what happens to a GitHub merge queue when a release-writer bot
pushes version-bump commits straight to `main` while pull requests wait in it?

All times are UTC. Check durations are scaled down ten times: `dummy-5`,
`dummy-15` and `dummy-30` take 30, 90 and 180 seconds. The longest check is
180 seconds, so "twice the longest check" is 360 seconds.

## Set-up

- Ruleset `main` (id 27182199): merge queue, squash, build up to 5 groups at
  once, up to 5 pull requests per group, minimum group size 1, wait 5 minutes,
  all entries must be green, 60-minute check timeout. Required checks
  `dummy-5`, `dummy-15`, `dummy-30`, `pin-match` (not strict). A pull request
  is required, with zero approvals. No force push. No deletion.
- Ruleset `rc` (id 27182200) on `rc/**`: creation, update and deletion restricted.
- The timed checks are commit statuses posted by `scripts/fake-ci.py`. The
  organisation's hosted runners were saturated (see "Runner pool"), so Actions
  jobs would have measured runner waits instead of the queue.
- `probe.yaml` is a real Actions workflow on `pull_request`, `merge_group` and
  pushes to `main`. It is not a required check. It compares the two version files.
- The rulesets as applied are in `rulesets/`.

## Who can push to a `main` that requires the queue

| Pusher | Bypass setting | Result | Evidence |
|---|---|---|---|
| User token of an organisation owner | none | Refused: GH013, "Changes must be made through the merge queue" | `probes.log` P1 |
| Workflow token (`GITHUB_TOKEN`) | none | Refused: GH013 | run 43380240904 |
| GitHub Actions app as a bypass actor | — | The ruleset API refuses it: "Actor GitHub Actions integration must be part of the ruleset source or owner organization" | `rulesets/rc-gha.json` |
| Deploy key | `DeployKey`, always | The ruleset accepts the bypass entry, but no deploy key can be added: "Deploy keys are disabled for this repository" (organisation policy) | `rulesets/rc-dk.json` |
| User token | repository role admin, mode `pull_request` | Refused: GH013 | `probes.log` P4 |
| User token | repository role admin, mode `always` | Accepted: "Bypassed rule violations for refs/heads/main" | commit 7359e32 |
| User token on `rc/probe` | none, then repository role admin `always` | Refused ("creations being restricted"), then accepted | `probes.log` P3, P6 |

A GitHub App was not tried: creating one needs a web step by an organisation owner.

## Does a push start the workflows that listen for pushes?

Yes, for every push that was accepted.

- User-token pushes: every one started the push workflows. First one: run
  43380856047, with actor, pusher and sender all the user, sender type `User`.
- Queue merges: every one started them, with actor `github-merge-queue[bot]`
  (for example run 43382239369).
- The queue merges by moving `main` to the group commit. Five pull requests
  merged together make one push event (commit 98e1976).

## The runs

| Run | Pull requests | Writer behaviour | Writer commits | Median time in queue | Range | Groups built | Removed for failed checks |
|---|---|---|---|---|---|---|---|
| A | #1–#6, all enqueued at once | none | 0 | 229.5 s | 220–436 s | 6 | 0 |
| B | #7–#12, all at once | one consistent commit, 80 s into the groups | 1 | 333 s | 326–539 s | 11 | 0 |
| C | #13–#18, all at once | one consistent commit 60 s after each merge | 2 | 230 s | 225–508 s | 7 | 0 |
| D | #19–#26, one per minute (+ #27) | a bump commit 60 s after each merge, then a pin commit 60 s later | 8 | 362 s (8 PRs); 330 s with #27 | 207–936 s | 37 for 9 PRs | 3 |
| E | #28–#35, one per minute | two consistent commits, 60 s and 120 s after each merge | 6 | 446.5 s | 224–638 s | 27 | 0 |

Times run from "added to the merge queue" to "merged", read from the pull
request timelines (`runs/run-*-result.jsonl`). The stand-in adds about 50
seconds of fixed overhead to every merge (run A: 229.5 s for a 180 s check).

## What a push does to the queue

- Every writer push made while groups were in flight dropped all of them: 14
  of 14 pushes. The queue rebuilt the groups on the new `main` within 3 to 21
  seconds (`snapshots.jsonl`). The work already done by the dropped groups is lost.
- The entries keep their place. A pull request needs nothing after a
  consistent push: no re-run, no update, no re-enqueue.
- Actions runs of dropped groups are not cancelled. Group 4225973 was dropped
  at 07:30:29; its job still started at 07:34:31 and ran.

## The window between a bump commit and a pin commit

- A group built on a bump commit fails `pin-match`. The queue removes the
  first pull request of the failing groups ("failed_checks"), marks the others
  unmergeable and rebuilds them. Seen three times: #21 at 07:31:02 and again at
  07:38:38, #22 at 07:33:09.
- A removed pull request must be added again by hand. That was accepted at
  once; its own checks did not need to run again.
- A pull request opened inside the window (#27, opened 07:30:17) gets a red
  `pin-match` on its own head ("chart-version=1.0.5 slot-pin=1.0.4") and a red
  `probe` run. It cannot be enqueued: "Required status check pin-match is
  failing". It needed a branch update (07:35:03) and a full new check cycle
  before it could enter the queue (07:39:45). It merged at 07:43:39.
- The `probe` push run failed on all four bump commits pushed to `main`
  (d0367c8, b746926, 599670b, 241d321), and 19 merge-group runs failed.

## Other observations

- Actions ran on every merge-group commit: 88 `merge_group` runs, one for each
  group head, on refs `gh-readonly-queue/main/pr-<n>-<base sha>`. The run's
  actor is the account that added the pull request to the queue.
- The squash commit (setting "pull request title and description") carries the
  whole pull-request body, including the line `Work-Package: LAB-a-1`, both in
  the merge-group commit and on `main`. GitHub appends its own
  `Co-authored-by:` paragraph after the body, so that line is not in the last
  paragraph.
- With a minimum group size of 1, the "wait 5 minutes" setting never applies.

## Runner pool

The organisation is on the free plan: 20 hosted jobs at once, shared with
every other repository of the organisation. Of 134 lab jobs that finished, the
median wait for a runner was 79 s, the 75th percentile 362 s, the 90th
percentile 609 s and the longest 806 s. At the end 26 lab jobs had waited up to
15 minutes without a runner; they were cancelled. `actions-runs.tsv` has every job.
