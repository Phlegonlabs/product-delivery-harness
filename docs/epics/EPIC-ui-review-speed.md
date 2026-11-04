# UI Review Speed

Status: branch `ui-review-speed` integrating; not released
Design workflow: enhancement
UI impact: none (review rules, evidence rules, two scripts and documentation; no product UI changes).

## Problem And Baseline

One HiFi round in hk-car-care (9 iPhone surfaces, 2 size classes) took 9 days from direction selection to Visual Approval and 6 more days of evidence-only work after the owner had accepted the design.

| Measured | Value |
| --- | --- |
| Base matrix (surface x state x target) | 150 cases, 75 PRD states |
| Full matrix recaptured per repair round | 4 times (`surface-normal-01..04`) |
| Screenshots for the final candidate | 3,377 PNG, 701 JSON |
| Browser time for the formal surface check (receipt timestamps) | 918 minutes |
| Reduced-motion run | 12 cases, about 100 minutes |
| Independent reviewer dispatches in the round | at least 10; three hit a 540 s route deadline with no verdict |

Causes: PRD states were multiplied by overlay sub-states; carry-forward required unchanged page bytes while HiFi pages inline all CSS; every stress axis ran over the whole matrix; `ui-design-builder` shipped no matrix driver, so each project wrote its own; isolated repairs had no cap; motion evidence needed video and frame sampling per intent per target; reviewers re-judged whole machine-produced matrices; the round kept producing receipts after acceptance; a mid-round install change blocked the exit identity check.

Owner direction (2026-11-04): every Epic, change or PRD should finish in one shot; flow speed beats refinement loops.

Baseline: `main` `df52638a` (v0.75.4).

## Accepted Scope

- `derivedStates` on PRD UI surfaces and the Approved target; a derived state is captured once at the surface's smallest target. Checkers accept the field and reject an unknown parent or a cycle.
- First-wave stress axes sampled on representative cases (rubric First-Wave Audit Axes).
- Isolated repairs capped at two scoped re-reviews after the one re-review; later open rows go to Visual Approval as listed advisories or blocks.
- Render fingerprint carry-forward replaces byte equality; diff-first re-review and parity; one capture per case.
- Motion evidence per intent: trigger frame, end-state frame, reduced-motion duration check, one representative target. The checker expects one target per intent.
- `ui-design-builder/scripts/hifi_matrix_capture.py`: one browser context over the whole matrix, geometry probe, render fingerprint, `--carry-from`, sampled axes, ui-output/3 output plus a `matrix-capture.json` sidecar.
- `delivery-harness/scripts/parity_capture.py`: fewer browser round trips, identical/changed classification, `--carry-from`, per-tuple durations.
- Verify-then-sample review for browser matrices; packets sized to the route before launch; a deadline with no verdict is environment-blocked and re-dispatched as smaller scoped calls; browser capability probes reused per session.
- Owner acceptance closes the design round; the round finishes on its entry bundle pin.
- Tool-driven HiFi author self-review.

Kept unchanged: owner decisions, exact-SHA binding, read-only reviewers, security review, HiFi 85/80 thresholds, the one-wave-plus-one-re-check budget, data safety.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| URS-1 | `derivedStates` parses, joins PRD to target, rejects unknown parent and cycles; matrix holds derived states once | `test_prd_derived_states.py`, `test_derived_states.py` |
| URS-2 | Sampling, cap, fingerprint and diff-first rules are stated once and cross-referenced | `test_review_matrix_docs.py`, `test_skill_contract.py` |
| URS-3 | Matrix driver captures the fixture matrix in one context, carries unchanged fingerprints, samples axes, writes an accepted ui-output/3 | `test_hifi_matrix_capture.py` (41 tests, one real Chromium run) |
| URS-4 | Motion receipts match one representative target per intent | `test_ui_design_contract.py` |
| URS-5 | Parity script classifies pairs, carries identical tuples, records durations | `test_parity_capture.py` (50 tests) |
| URS-6 | READMEs describe the flow in four languages | `test_skill_contract.py` |

## Execution Record

Five Sonnet 5.5 writers (claude-t3-direct, effort xhigh) in separate worktrees with disjoint file ownership; the parent integrated serially and applied each writer's requested cross-file edits.

- W1 `t3/shrink-ui-matrix-cap-repairs` 4fb43327: derived states, axis sampling, repair cap.
- W2 `t3/streamline-ui-review-evidence` c8f7acc5: fingerprint carry-forward, diff-first, one capture per case, motion, harness gates.
- W3 `t3/hifi-matrix-capture` 74278da3: matrix driver, tests, `references/matrix-capture.md`.
- W5 `t3/streamline-ui-review-lifecycle` 5a55568e: review method, packet sizing, capability receipts, acceptance closes the round, entry pin, tool-driven self-review, review record size.
- W4 `t3/parity-capture-diff-first` fdcb80f6: one load per side per route, board image paths, identical/changed/carried classification, `--carry-from`, durations. Round trips per pair 9.0 to 6.3, 3.7 when carried.
- W6 READMEs: pending.

Parent commits: SKILL.md cap sentence, CLI inventory, cross-reference reconciliation, fingerprint-only carry in the driver, one motion target in the checker.

## Open

- Docs weight is up about 2,500 words against v0.75.3, 832 of them the new matrix-capture page. The ratchet is visibility only.
- `hifi_reviewer.py` still requires a state-view variant at every target for a derived state (authoring side). The PLAN parity matrix still treats derived states as ordinary states.
- `--derived-once` in the matrix driver takes a `--derived <json>` map; it does not yet read `derivedStates` from the Approved target.
- No script records an owner waiver of a required check before Visual Approval; the checker still rejects an approval dated before the newest receipt.
- Verify-then-sample caps the random PASS sample at 20 rows.
