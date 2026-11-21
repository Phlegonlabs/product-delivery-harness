# EPIC-ui-one-shot: HiFi interactions that pass on the first full run

Status: in_progress (0.98.0 in PR #211; review and final measurement done, landing pending)
Design workflow: enhancement
UI impact: none (driver, reviewer runtime, readiness check and contracts; no product UI)

## Problem And Baseline

On 2026-11-20 the owner learned that Modern Web Guidance would not fix the UI failures and asked for a complete look ("完整地看一次全部的東西"), then for 0.98.0, then for every cause to be fixed so that a UI round passes in one shot ("我要所有的 UI 都是 One Shot 能解決掉所有的問題，不要再出現這些內容了").

The 2026-11-19 runs of eight HiFi packages had 623 failing operations of 1,293. Seven of the eight packages were committed between 2026-09-24 and 2026-11-06, before the driver rules they fail: the focus and destination checks came in v0.80.0 (2026-11-07), the navigate-link, same-state and unreachable-control checks in v0.85.0 (2026-11-16), and the state-control fieldset in v0.76.0 (2026-11-04). Only jolvex's package was made under current rules, and 11 of its 604 operations failed.

A scratch driver copy that records each focus target traced 258 focus-failing attempts in agentkiosk, hk-car-care, jolvex and ticketradar. In every one, focus first landed on the control, then the product moved it to new content: the new view's heading, a status message, an opened section, or the next page's heading on load. The output contract allowed only a move into a declared layer or back to an opener, and it passed a control that vanished and left focus on the page body.

Root causes of the 623: focus moved to new content, the only reason, 399; mobile menus the driver could not open, 53 (native details in dilution-radar and agentkiosk, a CSS checkbox menu in agentic-commons-site); destinations the page does not reach, 47; no state-control fieldset (hardwareprices), 35; navigation declared on a control that is not a link to the page, 35; same-state operations declared as state changes, 33; controls hidden in the declared starting state, 21.

## Accepted Scope

Owner decisions, 2026-11-20: "做成 0.98.0" for the end-state focus rule and native details disclosures; then fix every cause so that a round passes in one shot, and look further.

Delivered in 0.98.0:
- The driver judges an operation by where focus ends. The control takes focus first and may keep it. While it is still shown, focus may move only into content the activation showed. When a panel that held it closed, focus returns to that panel's opener or moves into new content. When it went for another reason, focus stays inside the destination surface. Focus on the body, outside that surface, or on a control hidden while holding it, is lost. A page the operation loads keeps its own initial focus. The reason names which case failed.
- When a state change through the reviewer runtime hides the focused product control, the runtime moves focus to the new view's first visible heading, or to the view itself. Production code follows the same rule (UI implementation contract rule 10). The driver reads where focus ends only after two animation frames and their timers, because products often move focus once the new view has rendered.
- A closed native details opens through its summary, with or without an id, including content that CSS also hides while closed. A details without a unique id is recorded as `details:<n>`.
- An operation from a disabled or `aria-disabled` control fails at once with a message saying how to fix the declaration, instead of waiting out the 30-second action limit. An unreachable control's message names its declared starting state and the two fixes.
- `review_evidence.py ready` refuses a capture without all five stress axes, or without `--intermediate` when a surface has two or more numeric widths. The HiFi self-review names the full command.

Not in this round: the seven older packages. Their manifests and markup were approved under older rules; updating them changes approved bytes, so it belongs to each repository's next UI round (see Consumer Impact).

## Change Log

| Change | Commits |
| --- | --- |
| End-state focus rule | `3aaca143` |
| Native details disclosures; content CSS hides inside them | `a690828e`, `121acf56` |
| Full axis sample at readiness | `53e00e6a` |
| Disabled controls named | `7fbdadd8` |
| Details without an id | `1088d15f` |
| Runtime focus after a hidden control | `6b22c3b3` |
| Unreachable control names its starting state | `2a83c441` |
| Focus read after the product's next frames | `935e4976` |
| Release 0.98.0; this Epic | `7608e3c4`, `57b0d7e3` |
| Review point repairs: inherited disabled state; same-document navigation, closing details and held details; contract wording | `fd1dea27`, `7f8a01c8`, `1b730240` |
| Review record | `e86102df` |
| Re-check repairs: a details beside its declared panel; focus back to a closed panel's opener anywhere; details layers keyed apart | `9d42860a`, `ea09aaf5`, `a69f9bfd` |
| Pull request review repair: runtime focus past a heading that cannot take it | `bc73f382` |
| Measurement repair: a navigation or state change that arrives by a real fragment change is judged like a loaded page | `07b2ef4e`, `49cc360c`, `685553d0` |
| Re-check record and final measurement | this commit |

## Measurement

Decision rule set before the first re-run: ship the focus rule if failing operations fall by at least 300, and stop for the owner if jolvex gains more than 30 newly failing operations.

First re-run (driver `a690828e`, the eight packages copied unchanged, no axes): failing operations 623 to 292; 396 fixed (ticketradar 151, ticketradar-en-app 138, hk-car-care 76, agentkiosk 23, jolvex 8); 65 newly failing, all focus lost when a retry, reread, confirm or tab control disappeared with its view (jolvex 39, hk-car-care 26). jolvex passed the stop line, so the result went to the owner, who asked for every cause to be fixed; the runtime focus default is that fix.

Final re-run (driver `935e4976`): jolvex and hk-car-care ran with the 0.98.0 runtime put between their runtime markers, as re-assembly from the current template does; the other four ran unchanged.

Re-run after the review repairs (driver `e86102df`, same setup): five packages matched the final re-run operation by operation, but jolvex went from 3 to 31 failing operations. The R1 repair, which kept the focus rule for navigation inside the same document, also judged links to their own page's `#hifi-state=` fragment, which the reviewer runtime handles like a new page. A first repair (`07b2ef4e`) still asked for focus in the destination surface; a scoped re-run of the 19 jolvex surfaces that held a failing operation fixed 15 and left 13 menu links failing. A trace showed why: the runtime's arrival heading sat in a hidden view, the product closed its menu, and focus stayed on the page body, as after a page load. With `685553d0` the same scoped re-run left the same 3 failing operations as the final re-run, and none newly failing. ticketradar's and ticketradar-en-app's UI-005, which hold their only focus-related failure, did not change in either re-run. The other three packages have no failing operation with a focus reason, and the later repairs change only how focus is judged. None of the six has a `details` that a declared opener names, a `summary` declared as a panel, or a page-dispatched `hashchange`, the cases the other repairs after `e86102df` touch. So the final column holds for `685553d0`.

| Package | 2026-11-19 | First re-run | Final |
| --- | --- | --- | --- |
| agentkiosk | 38 | 15 | 10 |
| dilution-radar | 70 | 70 | 20 |
| hk-car-care, new runtime | 93 | 43 | 16 |
| jolvex, new runtime | 11 | 42 | 3 |
| ticketradar | 185 | 34 | 34 |
| ticketradar-en-app | 170 | 32 | 32 |

No operation that passed on 2026-11-19 fails in the final run. agentic-commons-site (24) and hardwareprices (32) were not re-run: no change after the first re-run touches their failures. Across the eight packages, failing operations fell from 623 to 171.

What remains sits in the packages, and each failure now names its cause:
- jolvex: three operations declared out of its long-content stress state, which the page does not leave.
- dilution-radar: 19 controls declared to start a loading state that no script handles, and one navigation link.
- agentkiosk: a URL field declared as the submit control, and links whose click does not leave the page.
- hk-car-care: controls its declared starting state does not show, such as a cancel button that appears only after editing, and three deletion states without state controls.
- ticketradar and ticketradar-en-app: pre-0.85 navigation and same-state declarations, confirm buttons disabled in their starting state, and an admin retry that closes its panel without returning focus.

## Review

Review point, gpt-6.1-sol xhigh read-only, on `57b0d7e3`: HOLD, four blocking findings and two notes, all repaired.
- R1: every navigate operation skipped the final-focus check, so a same-document navigation (`history.pushState`) that left focus on the page passed. The check is now skipped only when a new document loaded.
- R2: the contract allowed focus to stay on a shown control and also failed focus outside the destination surface. Staying on a shown control stays allowed, as in a list beside its detail; the surface rule applies once focus leaves the control.
- R3: an open native details holding the control was no return panel. It is now, and the driver asks `checkVisibility` whether an element is shown, because a closed details keeps its content's boxes in current Chrome.
- R4: an id-free details was found again by its place after its opener step. It is now held by element.
- R5 (note): a control disabled through a fieldset or an `aria-disabled` ancestor still timed out. The check now uses `:disabled` and an `aria-disabled` ancestor.
- R6 (note): matrix-capture.md's reachability summary did not mention native details.

After the repairs, each of 18 broken variants of the driver, the runtime and the readiness check failed a test; the UI suite (36 modules) and the design-system suite (20) passed with browsers.

Targeted re-check on `e86102df`: fix_required, two findings.
- R7: the details layer replaced a declared panel's layer on the same element, so a `details` that a declared opener hid failed its return to that opener.
- R8: the contract failed focus outside the destination once it left the control, while the driver accepted a return to a closed panel's opener anywhere, as before this release. The contract now allows that return, as a menu button takes focus back after its item changes the view; the reviewer accepted it.

Scoped re-check on `ea09aaf5`: R7 resolved, one regression from the repair. R9: keying the details layer by its summary replaced a declared panel whose element is that summary. Details layers now have a key of their own place. Scoped re-check on `a69f9bfd`: PASS.

Codex review on PR #211 (P2): when a state change hid the focused control, the runtime could pick a heading inside a closed `details` or an `inert` region, whose `focus()` does nothing. The runtime now asks `checkVisibility()` and tries each visible heading until one takes focus, then the view itself. Scoped review on `bc73f382`: PASS, one note.

The jolvex regression in Measurement was found by the re-run, not by a review. Scoped review of `07b2ef4e`: fix_required, F1: any `hashchange` event, even one the page dispatched without changing its fragment, counted as an arrival. Only the browser's own event counts now. Re-check on `49cc360c`: PASS. Scoped review of `685553d0`, which judges a navigation or state arrival like a loaded page and keeps feedback operations under the rule: PASS, one note.

Review points this round: one full review and seven scoped re-checks, each on a repair the previous point, the pull request review or the measurement found. The full review applied the security lens; the scoped reviews of `bc73f382` (the runtime pin), `07b2ef4e` and `685553d0` (the arrival exemption) applied it to their changes; the other repairs touch no trust boundary. The commit that records this changes only this Epic, so the PASS on `685553d0` carries to it under scope-disjoint carry-forward (`685553d0..` path list: `docs/epics/EPIC-ui-one-shot.md`).

Next-round notes: no test asserts that the runtime removes a `tabindex` it added when focus did not land, or that it falls back to the view itself; the arrival tests cover only navigate operations, not a same-page state operation; browser tests are missing for a declared details that holds a dialog and for an opener moved outside every surface.

## Consumer Impact

Rounds keep their recorded Harness version. A new round on 0.98.0 gets the new runtime when its HiFi is assembled from the current template, and its readiness check needs the full command. A package from before 0.85.0 that a round reuses needs, in that round: re-assembly from the current template (state controls and runtime), same-state operations declared as `feedback`, navigation declared only on links to the declared page, and operations started from states that show and enable their control. The checker and the driver name each of these.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / focus-end-state / this commit, code at `685553d0` / task/ (untracked)
Stage and skill: source maintenance of the skill suite; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main 272fa168 (v0.97.0); the eight HiFi packages of the 2026-11-19 runs, copied to scratch
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): pending; rerun after 0.98.0 is installed
Approvals in force (gate, owner, date, candidate): owner, 2026-11-20: "做成 0.98.0"; then fix every cause so a round passes in one shot
Done and verified (command, exit code): see Measurement and Review; all 14 checks on PR #211 passed on `685553d0`
Remaining: CI on this commit, merge PR #211, tag v0.98.0, install; each older package's update in its repository's next UI round
Blocked / waiting (gate name or owner decision): none
Next action (one command or one owner decision): merge PR #211 once CI passes on this commit
Next owner (skill or human): parent session
```
