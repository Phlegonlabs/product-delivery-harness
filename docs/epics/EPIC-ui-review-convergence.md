# EPIC-ui-review-convergence: fewer UI review passes and less browser time

Status: candidate for 0.95.0 on branch `ui-review-speed`; not yet published
Design workflow: enhancement
UI impact: none (review rules, evidence rules and UI scripts; no product UI)

## Problem And Baseline

On 2026-11-19 the owner asked why UI testing takes so long in every project and why each review pass finds new problems. Read-only analysis of jolvex-platform, agentkiosk, hk-car-care and mark-six-3d found UI rounds of 50 to 146 hours. The time went to evidence rework, repair and re-check cycles, and review waves that grew far past the rule's two reviewers: jolvex's first wave inspected all 5,285 captures under a 540-second reviewer cap and ran as 16 agents. A mid-round Harness install changed identities and forced rework. Baseline: `main` `0613b863` (v0.94.0).

Owner decisions, 2026-11-19: stop the running UI threads; remove the 9-minute reviewer cap (the profile guard now allows up to 7,200 seconds; that file is outside this repository); keep three direction studies (the one-study-first change was cancelled); delete review packets once their review passes; the real problem is too many reviews, each finding new problems.

## Accepted Scope

- A review wave is two reviewers, never split by page group. They look by eye at each page at its smallest target, every machine-flagged case and the axis sample.
- A re-review closes the earlier findings and judges the repair. A defect already present in unchanged content is a next-round note, except a regression the repair caused or a high or critical security finding.
- `review_evidence.py ready` before a wave or re-review. A hang or driver failure gets one rerun, then goes to the owner.
- Matrix driver: per-page and per-operation restart budgets that give the same rows at any worker count; a failed restart blocks only its page; `text-split`; the intermediate sweep on the axis sample's states without repeated interactions; seconds per kind of work in the summary line.
- Delivery parity recaptures only the routes a repair names, with per-page HiFi carry.
- A round keeps its Harness version until it closes. `review_input.py --remove` deletes a passed packet.
- Raw capture output stays out of Git; the approval check lists cited captures missing from the index.
- Stopping a process tree never follows a reused Windows parent id (matrix driver and release packager).

Not in scope: fewer interaction attempts (every operation at every target with click and keyboard is 86% of the remaining measured work; that is a coverage decision for the owner); `--only` narrowing the reviewer pass (0.6% of the measured jolvex run, and the reviewer contract is package-wide); a targeted after-repair recapture option.

## Change Log

| Change | Commits |
| --- | --- |
| Round version freeze; passed packets removed | `13bc5916`, `c8e835f7`, `4529bd1a` |
| Per-page and per-operation restart budgets | `78cb8a69`, `6f0cb27c`, `8de2338b` |
| `text-split` measurement | `80ed463f`, `f0627065`, `fc0ab193` |
| Readiness check; repeated hangs go to the owner | `f310b74f`, `139ecd3c`, `23019436` |
| Parity recapture by repair scope; per-page HiFi carry | `168b5304`, `ab8e6daf`, `efe6b985`, `82dca668` |
| Raw captures out of Git; cited captures in the index | `b78f9903`, `dc915f57`, `e0a1bdc5`, `262e44aa`, `49bcd930` |
| Intermediate sweep on the axis sample, no repeated interactions; earlier receipts stay valid | `0b32d38b`, `fd61517b` |
| Where a run's time went | `ea0775c8` |
| Process-tree stop ignores reused parent ids | `020e2c91` |
| Two-reviewer waves, the visual inspection set, re-check scope | `cd351ab3`, `a895c923`, `1d76654e`, `5a17d1ea` |
| Release 0.95.0 | `cb7f022f` |

## Review And Repairs

Workers W1 to W4, W6, W6b and W7 (Claude Opus 5.5) each wrote one change in its own worktree; the parent cherry-picked them onto `ui-review-speed` and resolved two conflicts by keeping both sides. W5 (one direction study first) was cancelled by the owner's decision.

Matrix-flow review on `efe6b985`: three read-only GPT-6.1 Sol scopes (matrix size, driver code, capture speed) and one GLM-5.3 Flash documentation check. The parent reproduced each blocking finding before repair:

- An operation split across workers spent one budget per worker: four workers gave three FAIL rows where one gave two. Fixed by making an operation's attempts one work item.
- A failed restart at a phase start aborted the run with exit 2. It now blocks only the next page's work.
- The readiness check could never pass a permanent tool limit. A repeated hang now goes to the owner after one rerun.
- The intermediate sweep covered every state, derived ones included, where the rubric names the axis sample. On the last jolvex public run (756 base cases, four workers, 44.6 minutes) it took 630 cases; the axis sample takes 150.
- The axis sample is per surface in the driver and was per page in the rules; the rules now say surface.
- The GLM finding (text split missing from the self-review list) was already fixed in `fc0ab193`.
- Not changed: a hyphen or soft hyphen inside a figure (Chromium never breaks an ASCII hyphen before a digit, UAX #14 LB21 and LB25); a raised digit read as a second line (synthetic only); per-character range calls (about 25 ms per dense case, estimated).

A separate GPT-6.2 Sol analysis named repeated interactions in the intermediate sweep. The jolvex sidecars showed its size: the sweep reran all 4,344 interaction attempts with the same id, target, trigger and result as the base run, 3,477 of 7,356 measured worker-seconds. The sweep now runs none.

While testing, the parent found that a process-tree test counted ten processes of a chat app as driver survivors: the driver had been given the reused id of that app's dead parent. `taskkill /T` follows that stale link, so a hung-driver stop could kill an unrelated program; both tree stops now check creation times.

## Verification

Pending: the full Required Verification matrix, the final review point and pull-request CI.

## Consumer Impact

Earlier approvals stay valid: an intermediate receipt with every interaction row still passes. Consumers adopt between rounds, never during one. No consumer is pinned above 0.94.0.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / ui-review-speed / cb7f022f / task/ (untracked)
Stage and skill: source maintenance of the skill suite; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main 0613b863 (v0.94.0); owner requests of 2026-11-19
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): unknown; not run in this round
Approvals in force (gate, owner, date, candidate): owner, 2026-11-19: fix with Opus 5.5 workers, run the Harness flow, commit, push and merge
Done and verified (command, exit code): focused driver, checker, readiness and packager suites, exit 0
Remaining: full matrix, final review point, pull request, CI, merge, tag, install; then the ten-repository check and backend end-to-end tests the owner asked for
Blocked / waiting (gate name or owner decision): whether to sample interaction attempts (owner)
Next action (one command or one owner decision): run the full matrix and the final review point on the candidate
Next owner (skill or human): parent
```
