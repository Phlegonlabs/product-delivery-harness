# EPIC-parallel-delivery: independent work runs at the same time, and a finished worktree merges back when its check passes

Status: in_progress; candidate 0.83.0 on local branch `parallel-delivery`, reviewed once with one re-check; not pushed, not installed
Design workflow: enhancement
UI impact: none (delivery routing rules, two read-only scripts, a seed value, UI design authoring rules and one checker rule; no product UI).

## Problem And Baseline

The owner observed that the suite sends one sub-agent at a time. Reading the suite and five consumer RUNs showed why:

- Four of five managed PLANs were a straight chain. Eight page missions with disjoint files waited on each other through review nodes, and every one claimed the same fixed dev-server port. Every wave held one mission while the host had three or four free slots.
- The PLAN template and `new_run.py` seeded `max_parallel_workers: 1` although the rules said not to cap it low.
- The size gate had two answers. One writer was `small`; two independently writable parts were `large` and needed a full PLAN/RUN. There was no light parallel route.
- UI design required one author for all three direction studies and the HiFi, and the checker enforced it.

Baseline: `main` `9b72801d` (v0.82.0).

## Accepted Scope

Owner instructions 2026-11-15 and 2026-11-16: research parallelism, including UI; run the work with multiple agents; add a light parallel route; when a worktree finishes and is confirmed fine, merge it back automatically.

- `worktree_fanout.py scopes`: before launch, check that parts' write scopes do not overlap.
- `worktree_fanout.py merge-check`: when a writer returns, decide whether its branch can merge now. Reasons are exact codes. It prints the merge command and never runs it.
- Direct Fan-Out (`references/direct-fan-out.md`): small work with independent parts gets one writer per worktree and no PLAN/RUN. The parent merges each part when its merge check passes, without waiting for siblings or the owner. One review on the unified head.
- Size gate: work is large when missions depend on each other or must outlive the session.
- `plan_width.py`: a report of a PLAN's parallel width, levels, critical path and findings, run before readiness. No gate.
- A dependency edge means consumption. Merge order and review order are not dependencies. The fixed-port case is named.
- The seed for `max_parallel_workers` is 8.
- UI design: one author per direction study, in parallel when the host has capacity. The HiFi keeps one author. Research and review readers launch together.

Kept unchanged: gates, approvals, owner turns, review budgets, push and cleanup authorization, the selector, PLAN and RUN schemas, every approved package.

Deferred: parallel HiFi page authoring behind a frozen foundation. Not planned: rolling writer scheduling without the wave barrier.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| PD-1 | `merge-check` reports every unsafe case with its reason and changes nothing in either checkout | `test_worktree_fanout.py` (32 tests) |
| PD-2 | `plan_width.py` matches the selector's ordering and rejects a PLAN it cannot measure | `test_plan_width.py` (18 tests); five consumer PLANs read back as expected |
| PD-3 | Documented commands parse with the real parsers; documented finding codes equal emitted codes | `test_documented_commands.py` (11 tests) |
| PD-4 | Three direction studies by three authors pass; a study checked by another agent fails | `test_ui_design_v3.py` (18 tests) |
| PD-5 | The seed is 8 in the template and `new_run.py`; a fresh RUN still selects one worker until capacity is observed | `test_new_run.py` (13 tests); reviewer probe of the selector budget |
| PD-6 | Rule text is consistent across the suite | `test_skill_contract.py` (71 tests), link and reading-budget tests, protected review of the rule group |

## Document Impact

- New: `skills/delivery-harness/references/direct-fan-out.md`, `scripts/plan_width.py`, `scripts/worktree_fanout.py`.
- Changed rules: `SKILL.md` (size gate, Direct Route), `managed-delivery.md`, `parallel-mission-selection.md`, `execution-task-decomposition.md`, `worktree-thread-orchestration.md`, `stage-cards.md`, `HARNESS_PLAN.template.md`, `delegation-contract.md`, `pre-delivery-self-review.md`, `governance/source-maintenance.md`, root `AGENTS.md`; in `ui-design-builder`: `ui-design-pass.md`, `stages/ui-design.md`, `review-workflow.md`, `output-contract.md`, `ui-grading-rubric.md`, `ui_design_v3.py`.
- Four READMEs: the size-decision sentence, the Directions row, the 0.83.0 entry.
- The consumer `PROJECT_AGENTS.template.md` did not change.

## Execution Record

Run as a Direct Fan-Out, the route this round adds. Six writers in separate worktrees, in two steps because the two documentation parts needed the scripts they describe.

| Part | Writer | Result |
| --- | --- | --- |
| W1 `plan_width.py` | GLM-5.3 Flash | merged; parent then kept repair missions out of the width |
| W2 `worktree_fanout.py` | GLM-5.3 Flash | merged; parent renamed the entry point to `main()` and registered both scripts in the CLI inventory |
| W3 seed 8 | GLM-5.3 Flash | merged |
| W5 UI direction authors | GLM-5.3 | merged |
| W4b managed width rules | GLM-5.3 Flash | merged with `merge-check` |
| W4a Direct Fan-Out rules | GLM-5.3 | `merge-check` reported `merge_conflict`: both documentation parts added a test to one shared file. Parent kept both tests. |

The conflict came from the parent's briefs, which gave both parts the whole test directory. The reference now says a test file is a write path and that the parent resolves an add-only conflict.

### Review And Repair

One protected read-only review (GPT-6.1 Sol, high) in three scoped calls at `8490b404`, then one consolidated repair and one targeted re-check at `2b616ea3`.

| Group | Findings | Repair |
| --- | --- | --- |
| Fan-out script | Trial merge wrote objects into the repository; an untracked or ignored file at an incoming path was missed; `--into` could differ from the checkout the command merges into | Temporary object directory and no index lock; `untracked_collision` and `--no-overwrite-ignore`; `--into` removed |
| Width script | Repair mission with a prerequisite lost conditional status; tie-break differed from the selector; a mission without a node was counted; a cycle through non-mission nodes went unseen; a cycle error was a traceback | All five repaired with tests |
| Rules | Fan-out grant created writer branches while `SKILL.md` said to ask before branch creation | The rule names the run branch; writer branches are runtime allocations |

Found by the parent on a real PLAN: a review that routes to a gate on `pass` did not order the mission behind the gate. Repaired in the same batch.

Re-check: eight of ten dispositions resolved. Two remained and were repaired in isolation with focused tests, without another review: a local file blocking an incoming directory, and mission ordering that walked through a conditional repair mission.

## Change Log

| Date | Change |
| --- | --- |
| 2026-11-16 | Round opened, six parts merged, version set to 0.83.0 |
| 2026-11-16 | Review, consolidated repair, re-check, two isolated repairs |

## Results And Remaining Work

- Full matrix at `8490b404`: pass (skill spec, pyflakes, docs weight, harness, golden path, product, UI, design-system, diff check).
- At `ba4a1db7`, after the repairs: the affected modules pass (`test_worktree_fanout`, `test_plan_width`, `test_skill_contract`, `test_documented_commands`, `test_cli_utf8_output`, the docs and governance tests, `test_new_run`), with pyflakes over all four script trees, `prepare_release.py --check` and the candidate diff check. The full matrix was not rerun on the repaired head; CI on the pull request is that run.
- Remaining: push and PR to `main`, tag `v0.83.0`, install, consumer re-pin.
- Left in place, awaiting owner confirmation before removal: six writer worktrees and one repair worktree under `~/.t3/worktrees/product-delivery-harness/`, their local branches, and two review clones under `~/.t3/scratch/review-0830-*`.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / parallel-delivery / ba4a1db7 plus this record commit / task/ untracked
Stage and skill: source maintenance, direct route as a Direct Fan-Out (no PLAN/RUN)
Inputs consumed (path + hash or revision): main 9b72801d; task/parallel-delivery briefs and reviews; PLAN/RUN files of five consumer repositories, read only
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): not run; this source repository omits the consumer template sections by design, and no Harness skill workflow was invoked
Approvals in force (gate, owner, date, candidate): owner instruction 2026-11-16 to run this with multiple agents, add the light parallel route and merge finished worktrees automatically; local commits only
Done and verified (command, exit code): ci_test_shards.py matrix --base 9b72801d at 8490b404 (exit 0, result pass); affected test modules, pyflakes and prepare_release.py --check at ba4a1db7 (exit 0)
Remaining: push and PR to main; tag v0.83.0; install; consumer re-pin
Blocked / waiting (gate name or owner decision): owner decision to publish
Next action (one command or one owner decision): owner names the SHA and how far to publish
Next owner (skill or human): human
```
