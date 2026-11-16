# HiFi Checks Aligned With PRD Operations

Status: implementing R1–R10; through R5 verified locally
Design workflow: enhancement
UI impact: none (checker, matrix driver and their references; no product UI in this repository).

## Problem And Baseline

The Product Definition tool accepts operations that the HiFi checker and the matrix driver cannot represent.
A consumer with an approved PRD then has two bad choices: write artificial PRD entries, or draw a less faithful HiFi.

The case is jolvex-platform EPIC-058: 57 surfaces on 52 pages, and 570 PRD operations (406 page, 127 feedback, 24 overlay, 9 state, 4 tab).
On a ten-surface driver dry run every screen case passed: 506 light cases and 176 native dark cases.
About a third of the interaction attempts failed for the reasons in the table below.
That consumer's earlier package passed only by pointing unrelated controls at an `empty` state.

Baseline: `9abe4b9e` (v0.83.1 on `main`).

Read-only evidence in the consumer worktree `C:/Users/mps19/.t3/worktrees/jolvex-platform/redesign-full-site-20261113`:

- package: `docs/design/ui-references/epic058-vd-r6-06/`
- PRD: `docs/product/PRD.md`
- staged contract: `docs/design/.ui-staging/epic058-r1/ui-design.md`
- dry-run summary: `docs/design/.ui-staging/epic058-r1/captures/hifi/driver-dryrun/dryrun-summary.json`

| Class | Failed attempts in the dry run | Rule that rejects it |
| --- | --- | --- |
| Repeated rows of one operation | 272 | `hifi_matrix_capture.py` `interact`: "product control is missing or not unique" |
| Form fields that share their button's ID | 32 | same driver rule; `_HiFiProductControls` demands an ID on every field |
| Menu and drawer toggles without a PRD operation | 162 | every ID needs an interaction, and every interaction needs a PRD operation |
| `state` operations that end on another page | 83 | `_validate_hifi_bundle`: "HiFi state interaction must stay on the same page" |
| Controls inside a closed dialog, editor or disclosure | 148 | the driver never opens a declared product opener |
| `zoom-200` with container queries | 34 | `axis()` zooms the surface while the query container keeps its width |
| Same-endpoint operations | not reached | `_validate_hifi_bundle`: "must declare an observable destination state" |
| `:n/a` states | not reached | `_validate_hifi_html`: "missing state coverage" for an n/a state |
| A surface with no control | 1 surface | `_validate_hifi_bundle`: `navigation` and `controls` must be non-empty |

"Not reached" means an earlier finding makes `_validate_hifi_bundle` return before the rule runs.

## Accepted Scope

Owner decision, 2026-11-16, relayed by the jolvex-platform Harness parent: 「Harness 工具落差走 A」.
Where an approved PRD describes real product behaviour and the HiFi tools reject it, fix the tools.

Each change keeps the rejection that protects against a fake interaction and adds its own observable proof.
A package that passes today must still pass.

Not in scope: a control drawn in a different state from its PRD source state, copy-status findings, and consumer adoption.

## Acceptance

| ID | Expected outcome | Verification |
| --- | --- | --- |
| R1 | Manifest kind `feedback` for a non-page operation whose destination equals its source. `hifi_coverage_findings` expects `feedback` for equal endpoints, `state` for different ones, `navigate` for `page`. A `state` interaction with equal endpoints stays an error. The driver passes a `feedback` attempt only when activation changes the source surface (DOM, attribute, text or form value; focus alone does not count) and the surface keeps its state. | focused tests for both directions; a browser test with one changing and one inert control |
| R2 | A `state` interaction may end on another page when every instance of its control is an `a` with `href` `<destination page>#hifi-state=<surface>/<state>`. The driver observes the arrival page, surface and state. | static tests; a browser test across two pages |
| R3 | The per-page marker check skips states that end in `:n/a`, as `_evidence_matrix` already does. No other check asks a page to render an n/a state. | static test with an n/a state |
| R4 | The driver accepts one or more visible instances of a control, activates the first visible one and records the instance count. Every `navigate` instance is still an `a` to the declared page. | browser test with a three-row list |
| R5 | `data-control-for="<control id>"` on a form field marks it as supporting that control. The field needs no ID and no interaction. The named control must exist in the same surface. A field with neither attribute is still an error. | static tests, including the unknown-control case |
| R6 | `data-product-disclosure` joins `data-product-menu` and `data-product-tab` under the same panel rules. An opener needs no ID and no interaction. Before activating a control that is attached but hidden, the driver opens the declared openers whose panels contain it, outermost first. A control that no opener reveals still fails. The focus rule states how opener clicks count. | static tests; browser tests for a menu, a nested disclosure and an unreachable control |
| R7 | A surface may declare an empty `navigation` or `controls` list. When its PRD operations are `none — <reason>`, both may be empty and the surface renders no product control. | static tests for both cases |
| R8 | Under `zoom-200`, a viewport target's query container has half the target's inline size while the rendered box keeps the target width. | browser test that reads the container width under the axis |
| R9 | References state every changed rule: `output-contract.md`, `matrix-capture.md` and any stage card or template that names manifest kinds, control IDs, openers, n/a states or the zoom axis. | `test_markdown_anchor_links.py`; `docs_weight.py` |
| R10 | An adoption note lists, per requirement, the exact attribute or manifest edit a package author makes, with one example from the evidence package. | the note in this Epic |

## Open Contract Question

`ui-output/3` fixes the exact keys of an interaction row.
R1, R4 and R6 record new observations: what changed, the instance count and the openers used.
Resolved before R1: keep `ui-output/3` and allow one optional, closed `observed` object on each interaction row.
`_bundle_transcript_findings` compared entire rows, so it must validate observations separately before comparing all existing required keys.
`review_evidence.build_receipt` preserves the interaction rows in the hashed output; it imposes no conflicting interaction key set.
Earlier navigate and state receipts remain valid without observations.
Feedback requires `change` with distinct lowercase `beforeSha256` and `afterSha256` values.
R4 and R6 extend the closed object with instance counts and opener panel IDs.

## Acceptance evidence

- R5: test_hifi_operation_alignment.py -k Supporting: 2 tests, exit 0, with unknown-control and cross-surface negative cases.

- R4: test_hifi_operation_alignment.py: 10 tests, exit 0; existing Chromium interaction test: exit 0.

- R3: test_hifi_operation_alignment.py: 8 tests, exit 0; final NotApplicable case rerun exit 0 without mocks.

- R2: test_hifi_operation_alignment.py: 7 tests, exit 0, including Chromium across two pages.

- R1: `test_hifi_operation_alignment.py` passed four tests, including real Chromium, exit 0. Text and form-value changes pass; inert focus fails.

## Change Log

- 2026-11-16: R5 binds supporting fields with data-control-for and keeps unbound fields and buttons rejected.

- 2026-11-16: R4 activates the first visible repeated control, records its visible count and checks every navigation anchor.

- 2026-11-16: R3 skips :n/a product markers and matrix pairs while retaining real-state coverage failures and Overview reasons.

- 2026-11-16: R2 accepts exact cross-page state links, observes arrival and retains wrong-link rejection.

- 2026-11-16: R1 adds same-endpoint feedback, direct PRD kind mapping and validated optional observations. Existing state endpoint rejection remains.

- 2026-11-16: specified from the jolvex-platform dry run. Code locations were read at `9abe4b9e`. No code changed.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / hifi-operation-alignment / this commit / none
Stage and skill: source maintenance; through R5
Inputs consumed (path + hash or revision): main 9abe4b9e (v0.83.1); the jolvex-platform evidence paths above
Approvals in force (gate, owner, date, candidate): owner 「Harness 工具落差走 A」 2026-11-16, relayed by the jolvex-platform Harness parent
Done and verified (command, exit code): test_hifi_operation_alignment.py -k Supporting: 2 tests, exit 0, with unknown-control and cross-surface negative cases.
Remaining: R6–R10; final verification; independent read-only review; separately authorized release
Blocked / waiting (gate name or owner decision): none for implementation; publication and installation are not authorized
Next action (one command or one owner decision): implement R6
Next owner (skill or human): this source-maintenance writer
```
