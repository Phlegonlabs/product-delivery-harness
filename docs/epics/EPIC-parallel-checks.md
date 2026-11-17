# EPIC-parallel-checks: run the full check and the UI check at the same time

Status: in progress on `parallel-checks`; three writers running; not published
Design workflow: enhancement
UI impact: none (one capture script flag, review rules, the source test runner and one CI job; no product UI in this repository).

## Problem And Baseline

The owner said the full check, the UI full check and the UI review stage are slow, and asked whether they can run concurrently and be split by situation.

Three read-only explorers and two parent measurements, 2026-11-17:

| Where | How it runs today | Measured |
| --- | --- | --- |
| HiFi matrix capture in a consumer | one Node process, one Chromium, one page; every case in turn | agentkiosk final capture: 304 cases, about 21 minutes, about 3.4 s per case |
| Final review | one reviewer carries the code, security and visual lenses in turn | not measured |
| Broad final validation | starts only after the review converges | not measured |
| Source UI suite | one `unittest discover`, modules in turn | 157 s; 68 s with one process per module (28 modules pass) |

Real packages put most cases on one page (ticketradar 158 of 222, hk-car-care 54 of 150), so a split by page alone would not help them.

The split by situation already exists in the rules: no visual lens and no UI matrix without a UI change, affected pages only after a repair, changed-file selection for a failed final suite, `security: not_applicable` for a docs-only diff. What was missing is concurrency.

Baseline: `main` `3a553df7` (v0.85.0).

## Accepted Scope

Owner instruction, 2026-11-17: do it with several agents on Claude Sonnet 5.5.

- PC-1: `hifi_matrix_capture.py --workers N` spreads the cases, axis passes, interaction attempts and reviewer passes over N browser drivers by a fixed partition and writes one merged output. `--workers 1` stays the default and behaves as before.
- PC-2: one review point is dispatched as concurrent per-lens read-only calls (code, security, visual) on the same SHA; the parent merges them into one finding set and one repair loop.
- PC-3: on the direct route the broad final validation may start with the review on the same unchanged candidate. Managed runs keep their declared graph.
- PC-4: the source verification matrix runs the product, ui and design-system suites with one process per module, as the harness suite already runs; the `linux-required-browser` CI job uses the same runner.

Kept unchanged: exact-SHA binding, read-only reviewers, one consolidated finding set, the two-pass review budget, the owner request for several reviewers of the same lens, no reuse of evidence after a repair, the managed graph, every CI job name.

## Acceptance

| ID | Expected outcome | Verification |
| --- | --- | --- |
| PC-1 | The partition is deterministic and complete; the merged output equals the serial output apart from timestamps, durations and page-load transcript rows; it passes `validate_output` and builds a receipt; a driver out of restarts blocks only its share; no driver process is left behind | `test_hifi_matrix_capture.py`, fake-driver and real Chromium |
| PC-2 | The per-lens rule is stated once in `verification-gates.md` and the restating documents agree | `test_skill_contract.py` and the doc-asserting modules |
| PC-3 | The ladder, the final gate sentence and the direct-route steps allow the overlap; the managed sentence keeps the dependency | same |
| PC-4 | The three suites run module-parallel with the browser variables; a zero-test module fails; a failing module's output is in the step log | `test_ci_test_shards.py`; the CI job on the pushed branch |

## Execution Record

Direct Fan-Out: three Claude Sonnet 5.5 writers (claude-t3-direct, effort high), one worktree each, from `3a553df7`.

| Part | Files | Result |
| --- | --- | --- |
| W1, PC-1 | `ui-design-builder` capture script, its tests, `matrix-capture.md` | running |
| W2, PC-2 and PC-3 | `delivery-harness` SKILL.md, references, templates, root `CLAUDE.md`, pinned-phrase tests | running |
| W3, PC-4 | `ci_test_shards.py`, its tests, `harness-ci.yml` | running |

## Change Log

- 2026-11-17: round opened; scope and acceptance recorded; three writers started.
