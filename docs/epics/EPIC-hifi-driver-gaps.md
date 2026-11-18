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
The parent added G5 after the protected repair recheck passed at `b1760b79`.
G5 permits one proved focus return after an operation closes a declared layer.
The parent's local release commit `79df5eaa` sets 0.88.0 and stays in place; this writer changes no version.
The parent reports the scoped review of G5 head `f4463dc6` returned FAIL with N1 and N2.
The scoped review supplied those findings; the parent requested one isolated G5 repair and one later scoped re-review.
The repair records closure at the return event and records all product focus, including unmarked elements.
Opening a layer may transfer focus into that layer; unrelated focus, extra transfers and returns to an open panel still fail.
The parent reports the re-review of `7d9a911b` resolved N1 and N2 but returned FAIL for N3.
N3 restricts focus returns to panels that contained the operated control before activation.
Containing panels are checked innermost first; if nested panels close together, any closed containing panel's opener may receive the single return.
The parent authorizes one atomic G5 repair and one last scoped re-review for this family.

## Acceptance

| ID | Outcome | Evidence |
| --- | --- | --- |
| G1 | Exact navigation state anchors work; bare default links remain valid; stale selections cannot redirect product arrivals. | Static and Chromium positive/negative navigation tests. |
| G2 | Repeated controls prefer an unselected visible instance and record its index. | Chromium tests cover all four ARIA attributes and the all-selected inert fallback. |
| G3 | Data-entry controls receive user input; disabled, read-only and unchanged fields fail. | Chromium regressions cover input, textarea, selects in both directions, and rejected fields. |
| G4 | Repeated page timeouts cannot block unrelated pages; output order stays deterministic. | Serial, four-worker and Chromium timeout regressions; full stable-package run recorded in the handoff ledger. |
| G5 | Each activation permits one proved layer entry or a return to the opener of a closed containing panel; intervening focus fails. | Chromium click and keyboard tests cover event ordering, unmarked detours, closed siblings, nested containing panels, layer entry, historical runtimes and reviewer-origin focus. |

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
| G5 closed-layer focus return | Parent-requested driver, receipt validation, two contracts and regressions; based on `79df5eaa` | `test_g5_cancel_returns_focus_only_to_the_closed_layer_opener`, `test_g5_focus_return_rejects_unrelated_focus_and_still_open_layers`, `test_g5_focus_return_observation_names_one_panel` | First development check exposed reviewer heading focus in the expanded listener. Corrected driver-gap tests (18) and operation-alignment tests (32) exit 0. Final exact-head exits belong to the G5 ledger below. Scoped protected re-review follows this commit. |
| N1 / N2, isolated G5 repair | Event-time closure and complete product-focus recording; proved entry into a newly opened layer; driver, receipt schema, two contracts and focused tests | `test_hifi_focus_capture.py`; based on reviewed head `f4463dc6` | Focus tests (10), existing driver-gap tests (18), full UI suite (728) and compiler suite (240) exit 0. A development navigation failure exposed reviewer heading setup; exact runtime hashes and direct call locations now identify it. Final matrix and four-surface consumer results belong to the repair ledger below. One scoped re-review follows this repair. |
| N3 / G5 repair | Restrict return eligibility to panels containing the control before activation; preserve nested outer returns when both containing panels close | `test_n3_closing_two_siblings_cannot_return_to_the_unrelated_opener`, `test_n3_return_to_the_containing_panel_leaves_the_sibling_open`, `test_n3_nested_returns_accept_closed_containing_panels_from_inner_to_outer` | The unchanged driver reproduced false acceptance for click and keyboard, including control reparenting during activation. Corrected focus tests (13) and driver-gap tests (18) exit 0. Final exact-head command exits belong to the N3 ledger below. One last scoped re-review remains. |
| Codex PR #197 review, P2 / G1 | Ignore cancelled product-link arrivals after all click handlers; flush fast document arrivals on pagehide; refresh the runtime pin and fixture | `test_cancelled_product_click_preserves_saved_state_after_reload`, `test_cancelled_click_can_reload_during_dispatch_without_an_arrival`, `test_uncancelled_arrival_does_not_depend_on_timer_or_click_propagation`; based on `31dba09d` | Six cancellation variants reproduced the saved-state reset before repair. Five arrival tests and seven compiler compatibility tests exit 0. F3/F4 remain covered. Final requested command exits belong to the G1 cancellation ledger below. Parent owns push and merge. |

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
The parent reports the targeted protected recheck of `b1760b79` returned PASS: F1-F4 resolved, with no new finding.
The parent reports G5's scoped review of `f4463dc6` returned FAIL with N1 and N2.
N1 found that later closure could excuse an earlier return to an open panel.
N2 found that an unmarked focus detour could disappear before a valid return.
The isolated repair captures panel visibility synchronously at each focus event and retains every product focus event.
It also proves optional focus entry into a newly opened layer.
Reviewer heading focus stays recorded separately, identified by the exact accepted runtime body and direct call location.
Both historical runtime bodies stay supported; this repair changes no runtime bytes or compiler pins.
The parent reports the scoped re-review of `7d9a911b` returned FAIL: N1 and N2 resolved, with N3 still blocking.
N3 found that closing a sibling panel could excuse returning focus to its unrelated opener.
This repair snapshots only open panels containing the operated control before activation, ordered innermost first.
If the activation closes inner and outer containing panels, either panel's opener may receive the single return.
A panel that did not contain the control is never eligible, even if the operation closes it or moves the control into it.
The receipt still records one nonempty panel ID; its validation needs no change.
The parent reports the final scoped G5 re-review of `8371ee0a` returned PASS.
On 2026-11-18 the owner said 「發佈」; the parent pushed `31dba09d` and opened PR #197.
The parent then requested the local G1 repair for the valid Codex PR review finding recorded in the Change Log.

| Finding / requirement | Repair and regression | Verification |
| --- | --- | --- |
| F1 / G3 | Preserve field clicks that already apply a different destination. `test_f1_field_activation_can_hide_the_source_before_entry` covers click, keyboard, entry-driven transitions and inert rejection. | Reproduced `locator.inputValue` timeout before repair; focused regression and entry checks exit 0. |
| F2 / G4 | Carry exhausted page budgets into parallel intermediate work. `test_f2_exhausted_page_stays_blocked_when_intermediate_work_changes_workers` moves source-page cases across workers 0 and 1. | Pre-repair intermediate PASS reproduced; repaired source rows are BLOCKED and the other page passes. Regression and worker suite exit 0. |
| F3 / G1 | Persist the resolved arrival before reload. `test_f3_product_arrival_replaces_saved_selection_before_reload` covers bare, default-fragment and different-fragment arrivals. | Bare arrival/reload failed before repair; all cases and seven compiler compatibility tests now exit 0. |
| F4 / G1 | Clear same-document arrival markers. `test_f4_same_page_arrival_preserves_later_reviewer_selection_on_reload` covers fragment navigation, Overview, reviewer selection and reload. | Pre-repair reset reproduced. Repaired selection survives reload; bare same-page document links still reset correctly. All 15 focused tests and seven compiler compatibility tests exit 0. |

The repaired runtime body digest is `dd2bfce3eafc311011ad89f0b64bb99a59e6f50bf1140e62e4432b850bb4400a`.
Final exact-head suite exits and cleanup results belong to the repair ledger linked below.
Earlier full-matrix and consumer results belong to `5247a3cb`; they are not fresh repair evidence.

## Adoption Note

Consumer edits belong to the consumer author. This work changes no consumer bytes.
F3, F4 and the Codex PR cancellation repair require the final runtime, even if an earlier candidate runtime was copied.
The current compiler fixture pins that runtime's exact digest; the frozen 0.87.0 fixture preserves the two historical runtimes.

| Requirement | Required adoption and evidence-package example |
| --- | --- |
| G1 | Rebuild every page with the updated canonical reviewer runtime. The assembler preserves an existing runtime, so regenerate from author sources or replace the complete marked runtime segment. For `OP-UI-IOS-AUTH-reauth`, use `ios-ledger.html#hifi-state=UI-IOS-TABS/ready`. Language, term and save/cancel links must name their declared nondefault destinations. Recompute child hashes and the entry identity; recapture all affected interactions. |
| G2 | Keep one operation ID on every cycle segment of `OP-UI-IOS-TABS-cycle` in `ios-ledger.html`. Give segments their actual ARIA selection state. No manifest split or runtime rebuild is required for G2. Recapture with the new driver; it records `observed.instanceIndex`. |
| G3 | Keep `OP-UI-IOS-DETAIL-note` on its note field and `OP-UI-IOS-SOURCE-currency` on its currency select. No artificial save button, manifest change or runtime rebuild is needed for G3. Ensure the field accepts entry and its real handlers run. Recapture both click and keyboard attempts. |
| G4 | No HTML or manifest edit is needed. Run the candidate driver on the full package with `--workers 4`. Run the applicable intermediate sweep with the repaired driver too. Exhausted page budgets carry into that sweep across workers. A timed-out `index.html` leaves unrelated pages available. Retain failed and blocked rows. |
| G5 | No consumer edit or runtime rebuild is needed. Recapture `OP-UI-IOS-SOURCE-picker-cancel` with the repaired driver. The parent reports eight rows failed on the valid focus return. Close a panel that contained the operated control before returning focus to its opener. Nested containing panels are checked innermost first; closing both permits either opener as the single return. The driver records `observed.focusReturn`; opening a layer may instead record `observed.focusEntry`. Both proofs use visibility at the event and completion. An unmarked detour, a second transfer, a sibling opener or a never-open panel still fails. |

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / hifi-driver-gaps / G1 cancellation repair after 31dba09d; exact head and dirty paths in cancellation ledger / runtime template, compiler pin and fixture, browser regressions and this Epic
Stage and skill: source maintenance; no consumer workflow activated
Inputs consumed (path + hash or revision): source baseline d1e25594; consumer archive 4a6aaa4b; first-round Epic
Template audit: unknown; parent owns release; no seeded instruction changes in this scope
Approvals in force (gate, owner, date, candidate): owner said 發佈 on 2026-11-18; parent authorizes one atomic local G1 repair for the Codex PR finding and listed checks; parent retains push, merge and release
Done and verified (command, exit code): parent reports final G5 review PASS on 8371ee0a; six cancelled-click cases reproduce the P2 finding before repair; five arrival tests and seven compiler compatibility tests exit 0; final requested exits belong to the cancellation ledger
Remaining: parent push and PR #197 merge/release checks; consumers rebuild with the corrected G1 runtime
Blocked / waiting (gate name or owner decision): parent push and merge after local verification
Next action (one command or one owner decision): read exact head and final command exits from the cancellation ledger, then push the local G1 repair
Next owner (skill or human): jolvex-platform Harness parent after local verification
```

Final command exits, process deadlines, stable-package results and the exact candidate SHA are retained at:
`C:/Users/mps19/AppData/Local/Temp/pdh-hifi-gaps-bd14cf1f4643457e8363c63a30161dd4/`.
Use `commands.jsonl` and `verification.md`; earlier failed development checks stay in the ledger.
No local test result constitutes independent review or consumer approval.

Consolidated repair evidence is retained at:
`C:/Users/mps19/AppData/Local/Temp/pdh-hifi-review-repair-2173cf2cffa149dab553015dec24a6d7/`.
Its `commands.jsonl` and final `verification.md` preserve command exits, exact-head results and process cleanup.

G5 evidence is retained at:
`C:/Users/mps19/AppData/Local/Temp/pdh-hifi-g5-8a878fd2765c47769dddaafd85ee03a2/`.
Its ledger retains the failed development run and fresh final checks; that failure also triggers a full-matrix rerun.

The isolated G5 repair evidence is retained at:
`C:/Users/mps19/AppData/Local/Temp/pdh-hifi-g5-repair-95a523309241474ebe6beddef386e6eb/`.
Its ledger retains development failures, final command exits, source identity, process cleanup and the four-surface consumer check.

The N3 repair evidence is retained at:
`C:/Users/mps19/AppData/Local/Temp/pdh-hifi-g5-n3-c50d10dd6bd24a189da724d829360d74/`.
Its ledger retains the failing baseline regressions, corrected checks, exact final head and process cleanup.

The Codex PR #197 G1 cancellation repair evidence is retained at:
`C:/Users/mps19/AppData/Local/Temp/pdh-hifi-g1-cancel-d562ab6e565b4806a315a760d9936fd3/`.
Its ledger retains the failing cancellation baseline, corrected browser cases, exact final head and requested command exits.
