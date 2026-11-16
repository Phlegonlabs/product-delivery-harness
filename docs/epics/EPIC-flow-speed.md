# EPIC-flow-speed: a managed run keeps going when a mission needs one more path

Status: candidate for 0.84.0 on branch `flow-speed`; not yet published
Design workflow: enhancement
UI impact: none (worker-result validation, two transition commands, reference links; no product UI in this repository).

## Problem And Baseline

The owner asked where the whole flow loses time. Commit timestamps of one consumer managed delivery (agentkiosk, checker v1, Harness 0.76.1) answer it: 53.5 hours from the first RUN to closeout, 7 RUNs and 6 PLAN revisions.

| Where the time went | Hours | Cause |
| --- | --- | --- |
| Write-scope corrections | about 21 | each one needed a PLAN revision, an owner approval and a new RUN |
| Final review and repairs | about 21 | review, consolidated repair, two isolated repairs |
| Mission work | about 11 | M1 to M9 |

The scope corrections, from that repository's `docs/goal/DECISIONS.md`:

- DEC-001, DEC-004: a mission had to change files that an already integrated mission owned.
- DEC-002, DEC-005: a task commit needed a file that the PLAN gave to the next task of the same mission. DEC-005 was a two-line fix; its RUN ran for ten hours and the work passed every verifier.
- DEC-008: the launch packet left `package.json` scripts out of a repair's scope.
- DEC-010: the parent's result packet named the previous attempt's lease. `record-worker-result` recorded the validation issues as a failed attempt and used the repair node's only attempt.

The owner approved all ten decisions with the recommended option.

The review loop in the second row was already fixed in 0.76.1 and 0.79 (re-check scope, consolidated isolated repair).

Baseline: `main` `c8c4d569` (v0.83.2).

## Accepted Scope

Owner instructions, 2026-11-16: loosen the scope rules, run the work with several Opus 5.5 agents, then commit, push, publish and re-pin the consumers.

- A task commit may touch any path in its mission's write scope that some task of the mission lists. A task `write_scope` is a planning hint. Task order is still enforced.
- `harness_transition.py amend-scope` records a path in the running RUN's `scope_amendments`. PLAN bytes, revision and digest do not change. The parent runs it without an owner turn.
- `record-worker-result --check` and `record-node-result --check` validate and write nothing.
- Whole-file links on the mandatory reading path become section links.

Kept unchanged: the mission write scope as the boundary, deny scopes, parent-owned files, the acceptance-register protection, the 12 ledger actions, the PLAN revision procedure for anything `amend-scope` refuses, the RUN schema version.

Not in this round: one-command receipts for the design-system compile stage (the rules were not read yet), and release batching (a working habit, not a source change).

## Acceptance

| ID | Expected outcome | Verification |
| --- | --- | --- |
| FS-1 | A task commit on a sibling task's path validates; a path outside the mission scope, a denied path, a parent-owned file and the acceptance register still fail; task order still fails | `test_task_scope_hint.py` (9 tests), `test_validate_worker_result.py` (34) |
| FS-2 | `amend-scope` adds a row and leaves PLAN bytes and digest unchanged; every refusal leaves RUN bytes unchanged; overlap with an integrated mission passes and with a pending or running mission fails | `test_amend_scope.py` (22) |
| FS-3 | A worker result on an amended path validates, at the mission level and in a task commit slice | `test_amend_scope.py`, `test_task_scope_hint.py` |
| FS-4 | `--check` with a wrong-lease packet exits non-zero and leaves RUN byte-identical; the corrected packet then records | `test_record_result_check.py` (6) |
| FS-5 | Documented command lines parse with the real parser; every new anchor resolves | `test_documented_commands.py`, `test_markdown_anchor_links.py` |
| FS-6 | Mandatory reading is lower | `docs_reading_budget.py`: delivery-harness 32,017 to 26,137 words, product-definition-builder 38,169 to 35,889 |

## Execution Record

Run as a Direct Fan-Out: four Claude Opus 5.5 writers (effort high), one worktree each, from `c8c4d569`. The parent merged each branch when it returned.

| Part | Result |
| --- | --- |
| A, task scope | merged. The writer kept one check the brief did not name: a mission path that no task lists still fails, because that is what stops a task commit from writing the acceptance register. |
| C, result check | merged. Confirmed that worker-result issues found after the node binding is accepted are recorded as a failed attempt; without `--check` that is unchanged. |
| D, reading links | merged. Raised the `managed-delivery.md` size ceiling from 2,400 to 2,450 words to fit 17 section links. |
| B, `amend-scope` | merged. One conflict in `stage-cards.md` Card 5, where B and C both added a sentence and a command; both kept. |

Parent repairs after integration:

- The task-slice check from A read only the PLAN scope, so a path added with `amend-scope` still failed there. It now reads the effective mission scope.
- `managed-delivery.md` still linked `verification-gates.md` whole at two lines outside D's scope. Anchoring them took delivery-harness from 31,629 to 26,137 words.
- Card 5 command order: `amend-scope` sits before the `--check` line, because C's test pins the check directly before the record call.

Review: the owner asked for a direct pull request. The pull request's CI is the one full matrix, and its Codex review is the independent read. No separate protected review ran.

## Change Log

- 2026-11-16: four parts merged on `flow-speed`; release surfaces set to 0.84.0.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / flow-speed / this commit / untracked task/ only
Stage and skill: source maintenance
Inputs consumed (path + hash or revision): main c8c4d569 (v0.83.2); agentkiosk checker-v1-delivery docs/goal/DECISIONS.md and PLAN.md revision notes
Approvals in force (gate, owner, date, candidate): owner 2026-11-16: commit, push, pull request, merge, publish, install, re-pin consumers, remove this round's branches
Done and verified (command, exit code): focused modules above, exit 0
Remaining: pull request CI, merge, tag v0.84.0, install, consumer adoption, branch cleanup
Blocked / waiting (gate name or owner decision): none
Next action (one command or one owner decision): open the pull request
Next owner (skill or human): this source-maintenance parent
```
