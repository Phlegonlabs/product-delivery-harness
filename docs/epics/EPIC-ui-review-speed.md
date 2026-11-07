# UI Review Speed

Status: complete; v0.76.0 released 2026-11-04 (PR #178); 0.76.1 merged and installed 2026-11-06 (PR #179), tag pending; two follow-up fixes on `fix/compact-tracked-files-retention` unreleased
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
| URS-3 | Matrix driver captures the fixture matrix in one context, carries unchanged fingerprints, samples axes, writes an accepted ui-output/3 | `test_hifi_matrix_capture.py` (62 tests, four real Chromium runs) |
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
- W6 `t3/readme-faster-ui-review` f74b6285: four READMEs.
- Review: five diff-scoped protected reviews (gpt-6.1-sol, read-only); two timed out at 540 s and were re-dispatched as four smaller scopes. Findings repaired by the parent (parity carry identity, board URLs, one smallest-target rule, superset motion receipts, parity region rule, acceptance waiver wording, motion exception, cap duplicates) and by W7 (driver fingerprint media identity, path safety, width check, navigation transcript, overwrite guard, axis failures, per-channel pixel diff, derived-aware sampling, `--ui-design`).

Parent commits: SKILL.md cap sentence, CLI inventory, cross-reference reconciliation, fingerprint-only carry in the driver, one motion target in the checker.

### 0.76.1 Follow-Up

Candidate branch `review-speed-0761`, head `8f15687c`, base v0.76.0. A motion receipt validates without the HiFi bundle; `review_input.py` builds git-free review packets with a SHA-256 manifest; `security-review.md` accepts that manifest as the clean-checkout proof; `verification-gates.md` records the consolidated isolated repair and the baseline comparison gate; four README entries and the CHANGELOG rotation.

Verification at `8f15687c` (`task/release-0761/matrix-8f15687c/summary.txt`): skill spec, pyflakes, docs weight, harness suite (111 modules, 8 workers), golden path, the product-definition-builder, ui-design-builder and design-system-compiler suites and `git diff --check`, all exit 0.

Reviews: three protected read-only rounds (gpt-6.1-sol, xhigh) on `ea2c1d04`, `240ae793` and `8f15687c`; round 3 PASS on every scope.

Merged to `main` through PR #179 (`12eecf90`, 2026-11-06). Installed from `8f15687c` on 2026-11-06 (backup `20261106-023245`). Tag `v0.76.1` is not on origin; the agentkiosk re-pin and the formal motion collection have not run.

### Follow-Up Fixes (unreleased)

Branch `fix/compact-tracked-files-retention` from `8f15687c`:

- `6c4934bf` — `validate_harness_plan.py --repo-root` failed on every delta-mode PRD because the product-package join never passed the deltas directory; the join now derives `docs/product/deltas/` from the repository root when it exists.
- `1a7f035e` — each retained verifier execution copied the per-file tracked-file snapshot into `RUN.md` (48 MB for four verifiers on a 25k-file repository), which the write guard refuses; RUN now keeps the digest and count, and the external result file keeps the snapshot.

Verified: `python -B -m unittest tests.test_compact_tracked_files_retention tests.test_harness_contract_join_loader tests.test_harness_strict_authority` from `skills/delivery-harness/scripts` (26 tests, exit 0). No independent review, version bump or merge yet.

## Open

- Docs weight is up about 2,500 words against v0.75.3, 832 of them the new matrix-capture page. The ratchet is visibility only.
- `hifi_reviewer.py` still requires a state-view variant at every target for a derived state (authoring side). The PLAN parity matrix still treats derived states as ordinary states.
- No script records an owner waiver of a required check before Visual Approval; the checker still rejects an approval dated before the newest receipt.
- Verify-then-sample caps the random PASS sample at 20 rows.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Faster UI review (v0.76.0) | Accepted Scope above | PR #178 `ece15219` | Full matrix at the candidate; released and tagged 2026-11-04 |
| 0.76.1 follow-up | Motion receipts without the bundle, git-free review packets, consolidated repair | PR #179 `12eecf90` | `matrix-8f15687c` all exit 0; three protected review rounds; installed 2026-11-06; tag and agentkiosk re-pin pending |
| Deltas directory in the product-package join | Delta-mode PRDs failed `validate_harness_plan.py --repo-root` | `6c4934bf` | 26-test unittest run exit 0; review and release pending |
| Compact tracked-file retention in RUN | RUN manifest exceeded the write guard on large repositories | `1a7f035e` | `test_compact_tracked_files_retention.py` exit 0; review and release pending |

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / fix/compact-tracked-files-retention / 1a7f035e plus the record commits that follow / task/ untracked
Stage and skill: source maintenance, direct route (delivery-harness)
Inputs consumed (path + hash or revision): origin/main 12eecf90 (PR #179); task/release-0761/README.md, matrix-8f15687c/summary.txt and install.log (2026-11-06); git tags through v0.76.0
Approvals in force (gate, owner, date, candidate): local commits only; no push, tag, install or release authorized in this session
Done and verified (command, exit code): python -B -m unittest tests.test_compact_tracked_files_retention tests.test_harness_contract_join_loader tests.test_harness_strict_authority (26 tests, exit 0); git diff --check (exit 0)
Remaining: independent review of 6c4934bf and 1a7f035e; version bump and README entry at release; tag v0.76.1 on origin; agentkiosk re-pin; formal motion collection; local main is behind origin/main
Blocked / waiting (gate name or owner decision): owner decision to publish the branch and open its PR
Next action (one command or one owner decision): owner decides whether the two fixes ship as 0.76.2
Next owner (skill or human): human
```
