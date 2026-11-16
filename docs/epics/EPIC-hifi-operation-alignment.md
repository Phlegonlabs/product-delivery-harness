# HiFi Checks Aligned With PRD Operations

Status: N3 (R7) implemented; not independently reviewed; pull-request review must cover is_product_control
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

The owner made only these two statements for this work, both on 2026-11-16: 「Harness 工具落差走 A」 and 「在 Harness 專案開新對話交給 GPT-6.1-Sol」.
The jolvex-platform Harness parent supplied the repair instructions and the local-commit limit.
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

### Review history and N3 repair

The jolvex-platform Harness parent relayed the protected reviewers' results below.

| Review | Exact head | Relayed protected-review result |
| --- | --- | --- |
| Initial independent review | `b0dab02a` | FAIL with blocking F1–F5. |
| Targeted recheck | `ce5837da` | F1–F5 resolved; N1 blocking. |
| Scoped re-review 1 | `3c133d59` | N1 resolved; N2 blocking. |
| Scoped re-review 2 | `3d043588` | N1 stays resolved; N2 pointer escape resolved; N3 blocking. |

The jolvex-platform Harness parent set the scoped re-review budget; both runs are spent.
This N3 repair commit has had no independent review.
The pull-request review must cover `is_product_control`.

- N3 adds only the specified native focusability conditions to keyboard discovery; pointer, passive, native-tag and role rules stay unchanged.
- Working-tree focused checks pass: 14 product-contract tests and 30 operation-alignment tests, both exit 0.
- Both callers reject keyboard handlers on the specified focusable elements; plain summary and passive handlers remain accepted.
- The earlier N1/N2 regression cases remain in the focused suite.
- Final candidate commands, exits, hashes and platform skips live under `C:/Users/mps19/AppData/Local/Temp/pdh-hifi-n3-repair-20261116-95cb20f1/`.
- Use its `verification.md`, `commands.jsonl` and `final-candidate.json` for test evidence; those records do not constitute independent review.

### Isolated N2 repair of reviewed 3c133d59

- The jolvex-platform Harness parent relayed the protected reviewers' results: N1 resolved on `3c133d59`.
- The parent supplied the exact N2 pointer/keyboard repair instruction.
- Pointer activation counts with any tabindex or none; keyboard activation counts with any tabindex attribute or native focusability.
- Other handlers never establish a control; native interactive tags and the shared role set stay unchanged.
- Focused tests pass: 30 operation-alignment tests and 13 product-contract tests, both exit 0.
- Before committing, the UI suite passes 640 tests, the compiler suite passes 240 tests, and the golden path passes one test.
- All three precommit commands exit 0; each browser suite retains two Windows permission/symlink skips.
- Tests check both missing operation IDs and terminal-surface rejection, including negative-tabindex click and keyboard handlers.
- Passive animation/focus cases pass at tabindex -1 and 0; checkbox roles still fail on terminal surfaces.
- Final candidate reruns, exits, hashes and skips live under `C:/Users/mps19/AppData/Local/Temp/pdh-hifi-n2-repair-20261116-4f806be9/`.
- Use its `verification.md`, `commands.jsonl` and `final-candidate.json` for the exact-head scoped re-review.

### Isolated N1 repair of reviewed ce5837da

- The jolvex-platform Harness parent relayed the protected reviewers' results: F1–F5 resolved on `ce5837da`; N1 blocking.
- Working-tree checks: `test_hifi_product_contract.py` passes 13 tests; `test_hifi_operation_alignment.py` passes 30 tests; both exit 0.
- Passive heading animation and focus handlers pass at `tabindex="-1"` and `tabindex="0"`.
- Ten activation handlers still need operation IDs on reachable custom controls; checkbox roles remain controls even at negative tabindex.
- Final candidate commands, exits, hashes and platform skips are recorded under `C:/Users/mps19/AppData/Local/Temp/pdh-hifi-n1-repair-20261116-a5c81e6b/`.
- Use its `verification.md`, `commands.jsonl` and `final-candidate.json` for the scoped re-review candidate and results.
- The earlier full matrix passed on `ce5837da`; it is historical evidence, not a fresh run for N1.
- The jolvex-platform Harness parent requested affected checks for N1 and no third full matrix unless those checks fail.

### Consolidated repair of reviewed b0dab02a

- F5 (R5/R6): All 30 operation-alignment tests and 11 product-contract tests pass (exit 0), including supporting-textarea focus theft for click and keyboard and valid opener sequences.
- F4 (R1): The focus-handler negative browser test and five feedback contract/browser tests pass (exit 0); unchanged feedback hashes still reject focus-only mutations.
- F3 (R7): test_hifi_product_contract.py: 11 tests, exit 0; all 11 roles and inline widgets rejected on terminal surfaces. Terminal and Supporting focused tests: exit 0.
- F2 (R3): test_hifi_operation_alignment.py -k NotApplicable -v: 2 tests, exit 0; complete and partial legacy n/a markers accepted; missing real cases rejected.
- F1 (R5): test_hifi_operation_alignment.py -k Supporting -v: 5 tests, exit 0; all four action types and button/link roles rejected.
The independent read-only review of `b0dab02a` returned FAIL with F1–F5. This repair does not claim reviewer acceptance.

The final candidate's command ledger and full-matrix summary live under
`C:/Users/mps19/AppData/Local/Temp/pdh-hifi-review-repair-68dd091926f845bda566656c34cd24a2/`.
Use `commands.jsonl` for command exits and `full-matrix/summary.txt` for the clean candidate SHA and each matrix step.
The handoff report records the final results without changing that tested SHA.

### Initial implementation evidence

- R10: all ten adoption rows name concrete evidence-package edits or unchanged fields. The package's 52 file hashes and PRD hash stayed unchanged.
- Required checks: skill spec and changed-file pyflakes passed. Markdown anchor tests passed. Documentation weight increased by 790 words.
- Regression runs: UI suite 629 tests, exit 0, two Windows POSIX skips; Product Definition suite 467 tests, exit 0; golden path one test, exit 0.
- Read-only package run: `--only UI-001,UI-004`, exit 1. All 48 screen cases and reviewer measurements passed; 150 of 216 interactions passed.
- The 66 package interaction failures need adoption: 30 hidden/unmarked controls, 12 missing cross-page state links and 24 equal-endpoint state attempts.
- The full matrix command was not run. A preliminary Harness suite was cancelled after 687 seconds in Windows installer fixtures; its processes exited. No installed skills changed.
- Final commands, exit codes and exact-head observations are retained under `C:/Users/mps19/AppData/Local/Temp/pdh-hifi-alignment-fb0c2a53f419494daa967cb17a2a2b13/verification.md`.
- R2 follow-up: seven state-focused tests passed, exit 0, including encoded Unicode and punctuation across two pages. Wrong links and equal-endpoint state actions still fail.

- R6 follow-up: compiler suite passed 240 tests, exit 0, with two Windows platform skips. Both exact runtimes pass; altered runtime bytes fail.

- R9: test_markdown_anchor_links.py: 3 tests, exit 0; docs_weight.py --baseline 9abe4b9e: exit 0, +744 words.

- R8: test_hifi_operation_alignment.py -k zoom: Chromium test, exit 0; inline widths 195/600 render at 390/1200, then reset.

- R7: test_hifi_operation_alignment.py -k Terminal: 2 tests, exit 0; test_hifi_product_contract.py: 9 tests, exit 0.

- R6: test_hifi_operation_alignment.py: 18 tests, exit 0; test_reviewer_integration.py: 17 tests, exit 0.

- R5: test_hifi_operation_alignment.py -k Supporting: 2 tests, exit 0, with unknown-control and cross-surface negative cases.

- R4: test_hifi_operation_alignment.py: 10 tests, exit 0; existing Chromium interaction test: exit 0.

- R3: test_hifi_operation_alignment.py: 8 tests, exit 0; final NotApplicable case rerun exit 0 without mocks.

- R2: test_hifi_operation_alignment.py: 7 tests, exit 0, including Chromium across two pages.

- R1: `test_hifi_operation_alignment.py` passed four tests, including real Chromium, exit 0. Text and form-value changes pass; inert focus fails.

## Change Log

- 2026-11-16: Correct instruction attribution to the jolvex-platform Harness parent. The owner supplied only the two statements quoted above.

- 2026-11-16: N3 (R7) repair: add native focusability to keyboard discovery and preserve plain summaries. No independent review; PR review must cover `is_product_control`.

- 2026-11-16: N2 (R7) repair: separate unconditional pointer activation from focus-capable keyboard activation; keep passive handlers, native tags and roles unchanged.

- 2026-11-16: N1 (R7) repair: require reachable activation handlers for custom-control discovery; preserve passive focus targets and native/ARIA controls.

- 2026-11-16: F5 (R5/R6) repair: Record supporting-field focus and reject theft outside the opener and target sequence.

- 2026-11-16: F4 (R1) repair: Focus and settle feedback controls before the activation baseline.

- 2026-11-16: F3 (R7) repair: share interactive-role and tabindex/inline-handler discovery across control parsers and terminal-surface rejection.

- 2026-11-16: F2 (R3) repair: keep declared :n/a markers and target cases optional; retained markers pass and missing real-state cases still fail.

- 2026-11-16: F1 (R5) repair: restrict the supporting-field exemption to data-entry fields; action input types and button/link roles need operation IDs.

- 2026-11-16: R2 follow-up aligns static state-link encoding with the reviewer's encodeURIComponent, including punctuation, slashes and non-ASCII state names.

- 2026-11-16: R10 records per-requirement consumer edits and the unchanged-package diagnostic result. No consumer adoption, version bump or publication occurred.

- 2026-11-16: R6 follow-up adds the disclosure runtime to the compiler's exact allowlist and retains the previous runtime. Modified runtimes still fail.

- 2026-11-16: R1 follow-up preserves diagnostic `--only` runs during feedback adoption. Selected equal-endpoint state attempts still fail in Chromium.

- 2026-11-16: R9 aligns connected-HiFi and stage rules, groups interaction instructions and leaves README histories and version unchanged.

- 2026-11-16: R8 zooms the query container at half inline size and retains the nominal rendered width.

- 2026-11-16: R7 accepts empty operation lists and control-free packages; PRD none still rejects rendered product controls.

- 2026-11-16: R6 adds live same-surface disclosures and ordered opener activation, with strict target focus and post-opening feedback proof.

- 2026-11-16: R5 binds supporting fields with data-control-for and keeps unbound fields and buttons rejected.

- 2026-11-16: R4 activates the first visible repeated control, records its visible count and checks every navigation anchor.

- 2026-11-16: R3 skips :n/a product markers and matrix pairs while retaining real-state coverage failures and Overview reasons.

- 2026-11-16: R2 accepts exact cross-page state links, observes arrival and retains wrong-link rejection.

- 2026-11-16: R1 adds same-endpoint feedback, direct PRD kind mapping and validated optional observations. Existing state endpoint rejection remains.

- 2026-11-16: specified from the jolvex-platform dry run. Code locations were read at `9abe4b9e`. No code changed.

## Adoption note (R10)

These edits belong to the consumer author after adoption. None were made in the evidence worktree.
The observed package still has 125 equal-endpoint interactions with `kind: state`.
Its PRD parses as 570 operations without errors. The examples below use its actual IDs and pages.
The entry SHA-256 is `3068b0d684774e39f9f2b0149f9e9046d10b757339be11c3c3d63c0a733a8903`.
The PRD SHA-256 is `0cf5187b98beb17be3bbe637cc8194b22aaf042b4b47a48c3beb0a981ccf642b`.

| Requirement | Consumer edit and concrete example |
| --- | --- |
| R1 | Change equal-endpoint, non-page manifest operations to `kind: feedback`. `OP-UI-036-home` in `index.html` keeps `UI-036/ready` at both ends. Its `ui-036-home` control must produce the PRD-defined observable feedback without reloading the page. Do not invent an `empty` destination or treat focus as feedback. |
| R2 | Keep `OP-UI-050-recrawl-confirm` as `kind: state`. In `admin-evidence.html`, make every `ui-050-recrawl-confirm` instance an anchor with `href="admin-crawl.html#hifi-state=UI-037/ready"`. Preserve the approved endpoints. |
| R3 | Keep `loading:n/a` on `UI-001` in `redirect.html`. Keep its Overview reason. Add no product marker, state button or state/target variant for it. |
| R4 | Keep `data-navigation-id="ui-036-articles"` on repeated rows in `index.html`; do not create an operation per row. Every instance must link to `admin-articles.html`. The driver records the visible count and activates the first visible instance. |
| R5 | In `admin-agents.html`, replace `data-control-id="ui-040-save"` on supporting textarea/select fields with `data-control-for="ui-040-save"`. Keep the save button's `data-control-id` and its operation. |
| R6 | In `home.html`, add `data-product-menu` to the existing `button[data-menu-toggle]`. Keep `aria-expanded` and its unique `aria-controls="k3-menu--ready-320"` binding. Use one toggle handler; avoid connecting both the old toggle handler and the canonical handler. For editor/dialog controls, add `data-product-disclosure`, `aria-expanded` and a unique same-surface panel ID through `aria-controls`. |
| R7 | Keep `UI-001`'s `controls: []` in the manifest and its `ui-001-redirect` navigation. No artificial button is needed. This PRD currently has no `operations: none` surface. Only an approved control-free surface may use both empty lists; do not remove its redirect operation. |
| R8 | Change no product CSS for the axis. Recapture `home.html` at target 390 under `zoom-200`: the canvas query width is 195 CSS px and its rendered width remains 390. |
| R9 | Use the updated connected-HiFi and matrix references when repairing this package. The staged `docs/design/.ui-staging/epic058-r1/ui-design.md` must point to newly measured evidence after the package changes. No old receipt becomes a fresh PASS. |
| R10 | Recompute sibling hashes and the `index.html` identity after adopting these edits. Replace the diagnostic dry-run evidence with a fresh full run, including `observed.change`, `observed.instances` and any `observed.openers`. Retain the original dry run and owner decisions. |

The checker and driver remain in their existing entry modules because these changes share their manifest and receipt joins.
The focused tests use the existing fixtures. A separate helper module would split those joins without reducing responsibilities.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / hifi-operation-alignment / this commit / none
Stage and skill: source maintenance; N3 repair attributed to R7, not independently reviewed
Inputs consumed (path + hash or revision): reviewed 3d043588; the jolvex-platform Harness parent relayed the protected reviewers' results: N1 and N2 pointer escape resolved, N3 blocking; scoped budget spent; released main 9abe4b9e
Approvals in force (gate, owner, date, candidate): owner statements on 2026-11-16: 「Harness 工具落差走 A」 and 「在 Harness 專案開新對話交給 GPT-6.1-Sol」; the jolvex-platform Harness parent instructed local commits only; push, PR, tag, installation and version bump are not authorized
Done and verified (command, exit code): working-tree focused product-contract 14 and operation-alignment 30 tests, exit 0; final candidate commands and exits are in the N3 evidence directory above
Remaining: pull-request review must cover is_product_control; this N3 repair commit has had no independent review
Blocked / waiting (gate name or owner decision): scoped re-review budget spent (two); independent review deferred to the pull-request review
Next action (one command or one owner decision): at the separately authorized pull-request review, review is_product_control and the N3 regression cases on the recorded candidate SHA
Next owner (skill or human): pull-request reviewer after separate PR authorization
```
