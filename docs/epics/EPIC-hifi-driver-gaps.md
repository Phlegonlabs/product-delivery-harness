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
| G4 | Repeated page timeouts cannot block unrelated pages; output order stays deterministic. | Serial and worker recovery regressions; full stable-package run. Pending. |

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| G1 navigation state | Validator, driver, reviewer runtime and two contracts | `test_hifi_driver_gaps.py` | Three focused tests pass in Chromium; wrong state and bare nondefault links fail. Parent review pending. |
| G2 repeated selection | Driver, observation validation and two contracts | G1 commit `9e4d4509`; focused G2 tests | Chosen index is bounded by the visible count; inert selected controls still fail. Parent review pending. |
| G3 data entry | Driver and two contracts | G2 commit `9ea7f18e`; focused field tests | User input retains source-change and focus proof. Parent review pending. |

## Adoption Note

Consumer edits belong to the consumer author. This work changes no consumer bytes.

| Requirement | Required adoption and evidence-package example |
| --- | --- |
| G1 | Rebuild every page with the updated canonical reviewer runtime. The assembler preserves an existing runtime, so regenerate from author sources or replace the complete marked runtime segment. For `OP-UI-IOS-AUTH-reauth`, use `ios-ledger.html#hifi-state=UI-IOS-TABS/ready`. Language, term and save/cancel links must name their declared nondefault destinations. Recompute child hashes and the entry identity; recapture all affected interactions. |
| G2 | Keep one operation ID on every cycle segment of `OP-UI-IOS-TABS-cycle` in `ios-ledger.html`. Give segments their actual ARIA selection state. No manifest split or runtime rebuild is required for G2. Recapture with the new driver; it records `observed.instanceIndex`. |
| G3 | Keep `OP-UI-IOS-DETAIL-note` on its note field and `OP-UI-IOS-SOURCE-currency` on its currency select. No artificial save button, manifest change or runtime rebuild is needed for G3. Ensure the field accepts entry and its real handlers run. Recapture both click and keyboard attempts. |
| G4 | Pending implementation. |

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / hifi-driver-gaps / 9ea7f18e plus G3 candidate / scoped source files
Stage and skill: source maintenance; no consumer workflow activated
Inputs consumed (path + hash or revision): source baseline d1e25594; consumer archive 4a6aaa4b; first-round Epic
Template audit: unknown; parent owns release; no seeded instruction changes in this scope
Approvals in force (gate, owner, date, candidate): the two owner statements above; parent authorizes G1-G4 local commits only
Done and verified (command, exit code): focused G1-G3 suite exit 0, seven tests with Chromium; alternate probe regression exit 0
Remaining: G4; final verification; real-package run; independent review and release
Blocked / waiting (gate name or owner decision): no implementation blocker
Next action (one command or one owner decision): implement G4 after the G3 commit
Next owner (skill or human): this writer, then jolvex-platform Harness parent
```
