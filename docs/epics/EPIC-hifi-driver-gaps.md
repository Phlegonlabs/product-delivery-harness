# HiFi Driver Gaps

Status: in_progress; local source maintenance, awaiting parent review and release

## Problem And Baseline

Baseline: `d1e25594460cf9282f855b5c2b73a10bc9fce4e6` (`origin/main`, 0.87.0).
The jolvex-platform Harness parent reports four gaps after the first operation-alignment round.
Its EPIC-058 package has 57 surfaces, 52 pages and 570 PRD operations.
Slice 12 reports 2,314 passing light cases; the first whole run blocked 345 cases and 1,693 interaction attempts.
These are parent-supplied baseline numbers, not observations of this candidate.

The package and PRD are archived from consumer commit `4a6aaa4b` into a temporary evidence directory.
The live consumer worktree and its untracked driver outputs are read-only inputs.
The first round's rule still applies: preserve fake-interaction rejection and add observable proof for each accepted form.

## Accepted Scope

Owner, 2026-11-16: 「Harness 工具落差走 A」.
Owner, 2026-11-17: 「同意。你直接修改它，全部的問題。」.
The second statement approved another Harness repair round, following the first round's GPT-6.1-Sol project thread.
All other instructions and acceptance requirements come from the jolvex-platform Harness parent.
That parent owns independent review and release.
During this round, the parent approved adding the new exact runtime hash to the compiler allowlist.
Both existing hashes and the altered-runtime rejection remain required.

This writer commits locally on `hifi-driver-gaps` only.
No delegation, model change, push, PR, tag, install or version bump is authorized.
Review process documents, grading, copy rules and anchor-without-href discovery are excluded.
Existing passing packages must keep passing.

## Acceptance

| ID | Outcome | Evidence |
| --- | --- | --- |
| G1 | Exact navigation state anchors work; bare default links remain valid; stale selections cannot redirect product arrivals. | Static and Chromium positive/negative navigation tests. |
| G2 | Repeated controls prefer an unselected visible instance and record its index. | Chromium tests cover all four ARIA attributes and the all-selected inert fallback. |
| G3 | Data-entry controls receive user input; disabled, read-only and unchanged fields fail. | Chromium regressions cover input, textarea, selects in both directions, and rejected fields. |
| G4 | Repeated page timeouts cannot block unrelated pages; output order stays deterministic. | Serial, four-worker and Chromium timeout regressions; full stable-package run recorded in the handoff ledger. |

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| G1 navigation state | Validator, driver, reviewer runtime and two contracts | `test_hifi_driver_gaps.py` | Three focused tests pass in Chromium; wrong state and bare nondefault links fail. Parent review pending. |
| G2 repeated selection | Driver, observation validation and two contracts | G1 commit `9e4d4509`; focused G2 tests | Chosen index is bounded by the visible count; inert selected controls still fail. Parent review pending. |
| G3 data entry | Driver and two contracts | G2 commit `9ea7f18e`; focused field tests | User input retains source-change and focus proof. Parent review pending. |
| G4 page recovery | Driver, matrix suites and two contracts | G3 commit `b7b3ac0d`; focused recovery tests | Failed pages remain failed; unrelated pages continue. Parent review pending. |
| G1 compiler adoption | Exact runtime pin and historical-runtime regression fixture | G4 commit `fe0ff5db`; compiler compatibility suite | Preserve both older runtimes; reject modified bodies. Parent review pending. |
| G1 event compatibility | Record same-document arrivals only for navigate attempts | Pin follow-up `48758372`; state-hash Chromium regression | Same-page state hashes retain their existing transcript contract. Exact navigation links still require arrival proof. |
| F1 / G3 repair | Preserve a field activation that already reaches a different destination | Working-tree `test_f1_field_activation_can_hide_the_source_before_entry` | Focused regression exit 0; entry checks exit 0. Protected recheck pending. |
| F2 / G4 repair | Inherit base page budgets before parallel intermediate dispatch | F1 commit `e86d6754`; `test_f2_exhausted_page_stays_blocked_when_intermediate_work_changes_workers` | Regression and all 27 worker tests exit 0. Protected recheck pending. |
| F3 / G1 repair | Save the resolved product arrival before reload; refresh the current runtime pin and digest fixture | F2 commit `96ff70eb`; `test_f3_product_arrival_replaces_saved_selection_before_reload` | Browser regression and seven compiler compatibility tests exit 0. Both historical runtimes and altered-body rejection remain covered. |
| F4 / G1 repair | Clear fragment-arrival markers; keep bare document-arrival handling; refresh the runtime pin and digest fixture | F3 commit `fa118a28`; `test_f4_same_page_arrival_preserves_later_reviewer_selection_on_reload` | All 15 focused tests and seven compiler compatibility tests exit 0. Targeted protected recheck pending. |

G4 uses three recovery restarts per page rather than one budget for the browser.
The next timeout blocks that page's remaining work and still discards its hung browser.
Recovery-load failures also stay local to their source page.
This bounds the slow page without guessing a load duration from file size or changing the static worker split.
Page budgets survive later phases; output lists retain their existing order.
Only failure to start a fresh browser can block the worker.

The driver remains one module because recovery owns its existing case, interaction and phase joins.
The changed validator also retains its manifest and receipt joins. No unrelated split is needed.

## Protected Review And Consolidated Repair

The jolvex-platform Harness parent reports two protected GPT-6.1-Sol reviews of exact head `5247a3cb`.
The reviewers used a `review_input.py` clone, with identity proved by its manifest.
The protected review returned FAIL; the consolidated findings are F1-G3, F2-G4, F3-G1 and F4-G1 below.
The protected reviewers supplied the findings. The parent supplied these repair instructions and the one-commit-per-finding boundary.
This is one consolidated repair round. A targeted protected recheck follows on its exact final head.

| Finding / requirement | Repair and regression | Verification |
| --- | --- | --- |
| F1 / G3 | Preserve field clicks that already apply a different destination. `test_f1_field_activation_can_hide_the_source_before_entry` covers click, keyboard, entry-driven transitions and inert rejection. | Reproduced `locator.inputValue` timeout before repair; focused regression and entry checks exit 0. |
| F2 / G4 | Carry exhausted page budgets into parallel intermediate work. `test_f2_exhausted_page_stays_blocked_when_intermediate_work_changes_workers` moves source-page cases across workers 0 and 1. | Pre-repair intermediate PASS reproduced; repaired source rows are BLOCKED and the other page passes. Regression and worker suite exit 0. |
| F3 / G1 | Persist the resolved arrival before reload. `test_f3_product_arrival_replaces_saved_selection_before_reload` covers bare, default-fragment and different-fragment arrivals. | Bare arrival/reload failed before repair; all cases and seven compiler compatibility tests now exit 0. |
| F4 / G1 | Clear same-document arrival markers. `test_f4_same_page_arrival_preserves_later_reviewer_selection_on_reload` covers fragment navigation, Overview, reviewer selection and reload. | Pre-repair reset reproduced. Repaired selection survives reload; bare same-page document links still reset correctly. All 15 focused tests and seven compiler compatibility tests exit 0. |

The repaired runtime body digest is `3c016dead62a116b6c527604aa3480a5327d5887a94dad096928a6f49768bbe3`.
Final exact-head suite exits and cleanup results belong to the repair ledger linked below.
Earlier full-matrix and consumer results belong to `5247a3cb`; they are not fresh repair evidence.

## Adoption Note

Consumer edits belong to the consumer author. This work changes no consumer bytes.
F3 and F4 require the final repaired runtime, even if an earlier candidate runtime was copied.
The current compiler fixture pins that runtime's exact digest; the frozen 0.87.0 fixture preserves the two historical runtimes.

| Requirement | Required adoption and evidence-package example |
| --- | --- |
| G1 | Rebuild every page with the updated canonical reviewer runtime. The assembler preserves an existing runtime, so regenerate from author sources or replace the complete marked runtime segment. For `OP-UI-IOS-AUTH-reauth`, use `ios-ledger.html#hifi-state=UI-IOS-TABS/ready`. Language, term and save/cancel links must name their declared nondefault destinations. Recompute child hashes and the entry identity; recapture all affected interactions. |
| G2 | Keep one operation ID on every cycle segment of `OP-UI-IOS-TABS-cycle` in `ios-ledger.html`. Give segments their actual ARIA selection state. No manifest split or runtime rebuild is required for G2. Recapture with the new driver; it records `observed.instanceIndex`. |
| G3 | Keep `OP-UI-IOS-DETAIL-note` on its note field and `OP-UI-IOS-SOURCE-currency` on its currency select. No artificial save button, manifest change or runtime rebuild is needed for G3. Ensure the field accepts entry and its real handlers run. Recapture both click and keyboard attempts. |
| G4 | No HTML or manifest edit is needed. Run the candidate driver on the full package with `--workers 4`. Run the applicable intermediate sweep with the repaired driver too. Exhausted page budgets carry into that sweep across workers. A timed-out `index.html` leaves unrelated pages available. Retain failed and blocked rows. |

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / hifi-driver-gaps / F4 candidate after fa118a28; exact head in repair ledger / scoped runtime, pin, fixture and regression files
Stage and skill: source maintenance; no consumer workflow activated
Inputs consumed (path + hash or revision): source baseline d1e25594; consumer archive 4a6aaa4b; first-round Epic
Template audit: unknown; parent owns release; no seeded instruction changes in this scope
Approvals in force (gate, owner, date, candidate): the two owner statements above; parent authorizes one local repair commit per F1-F4 finding
Done and verified (command, exit code): protected review FAIL on 5247a3cb; all four regressions reproduced before repair; all 15 focused tests and seven compiler compatibility tests exit 0
Remaining: final-candidate suite results in repair ledger; targeted protected recheck and parent release
Blocked / waiting (gate name or owner decision): protected recheck pending after repair
Next action (one command or one owner decision): read exact head and final command exits from repair ledger, then run the targeted protected recheck
Next owner (skill or human): jolvex-platform Harness parent after local verification
```

Final command exits, process deadlines, stable-package results and the exact candidate SHA are retained at:
`C:/Users/mps19/AppData/Local/Temp/pdh-hifi-gaps-bd14cf1f4643457e8363c63a30161dd4/`.
Use `commands.jsonl` and `verification.md`; earlier failed development checks stay in the ledger.
No local test result constitutes independent review or consumer approval.

Consolidated repair evidence is retained at:
`C:/Users/mps19/AppData/Local/Temp/pdh-hifi-review-repair-2173cf2cffa149dab553015dec24a6d7/`.
Its `commands.jsonl` and final `verification.md` preserve command exits, exact-head results and process cleanup.
