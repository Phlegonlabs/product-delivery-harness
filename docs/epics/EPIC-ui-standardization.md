# EPIC-ui-standardization: build the shared parts once, measure before review, and end the review after one re-review

Status: implemented and verified on local branch `ui-review-one-pass` (2026-11-17); not pushed, no version bump, not installed
Design workflow: enhancement
UI impact: none in a product. HiFi packages may now carry one embedded product stylesheet.

## Problem And Baseline

The owner (2026-11-17): the HiFi stage runs for tens of hours, the design is repaired again and again, and every re-check finds something new and causes another re-check. Round caps in 0.66, 0.70 and 0.76 did not hold. Impeccable stays, and the UI must still be right.

Read-only studies of five consumer rounds (GLM-5.3 Flash explorers; the parent spot-checked the cited lines for agentkiosk and ticketradar):

| Observed | Value |
| --- | --- |
| Findings classified across agentkiosk, hk-car-care and ticketradar | 102 |
| Token or component level | 46% |
| Page content against the PRD | 26% |
| Page layout | 15% |
| Evidence, tooling or process | 10% |
| Reportable by a script (the classifier's judgment) | about 90% |
| agentkiosk round 4, rounds after the first wave | 8: four evidence-only, three reviewer matrix failures, two real misses |
| jolvex redesign (57 surfaces), one full matrix capture | about 6 hours; the first driver run came after nine journey slices |

The proposal was reviewed before any edit by GPT-6 Astra (high), Claude Opus 5.5 (high, the author's view) and GPT-6.1 Sol (high, protected read-only). Their corrections are in the scope below: no closed block list (a block needs proof instead), no per-journey approval locks, three layers instead of two, no cross-product component catalogue, formal design-system compilation stays after approval.

Baseline: `main` `d1e25594` (v0.87.0).

## Accepted Scope

- R1 Three layers: kit (tokens and every control with all states, one product stylesheet), composition, art. Any text or control is kit.
- R2 Kit and pilot first: built together from the selected study; author checks on the pilot; a pilot diagnosis with findings only; the owner's look, not a gate; one batch of fixes; kit lock; remaining journeys from the locked kit with checks after each journey. Skipped for a small product; an enhancement has no pilot.
- R3 Authors read the Impeccable craft floor before authoring; `impeccable` gains the allowed use `author_quality_reference`.
- R4 `hifi_matrix_capture.py --measure-a11y`: contrast, target size, text clip, focus visible, text growth, written to the sidecar's `a11y` object. No effect on results or the exit code.
- R5 One matrix capture per candidate: the author's last run on the frozen bytes. Reviewers never run the driver.
- R6 Return check: a missing obligation or a rejected receipt goes back to the same reviewer session. No evidence-only round.
- R7 Budget: pilot diagnosis, one wave, one consolidated repair, one re-review by the wave's own reviewers as a closure check, with one fix exchange inside it. The two scoped re-reviews are removed. An open block leaves the candidate `blocked` for the owner.
- R8 A block needs a reproduced failure, the rule it breaks and closure criteria.
- R9 `assemble_ui_review.py --product-css <file>` embeds one stylesheet identically in every page; the bundle check rejects drift once any page carries the markers.
- R10 The Impeccable authorization is asked at UI Design Intake.

Kept unchanged: receipt binding, the 85/80 thresholds, Visual Approval, Final UI Acceptance, direction studies, contract versions (`ui-design/3`, `ui-hifi/2`, `design-system/4`).

Not done: a lint for styles outside the kit; PRD content checks (the 26% class); the README sections and version entries, which belong to the release change.

## Execution Record

Six bounded writers on Claude Sonnet 5.5 (claude-t3-direct, effort high) in separate worktrees with disjoint files; the parent (Claude Fable 5.2, high) wrote the spec, integrated by cherry-pick and reviewed the unified diff. Four writers belong to this Epic:

- W1 `c891216d`: rubric (Block Proof, Review Budget, closure re-review), review evidence (Return Check), review workflow, review packet, `SKILL.md`.
- W2 `0d99b633`: stage card, design pass, intake, author self-review, external-skill manifest.
- W3 `4a6559ca`: `--measure-a11y` in the driver, tests in real Chromium, `matrix-capture.md`. It adds about 0.6 s on the fixture package.
- W4 `19779ab3`: `--product-css` in the assembler, the bundle check, `output-contract.md`.

An earlier dispatch of three writers on a narrower spec was cancelled on the owner's word before integration; its worktrees were left in place and not used.

## Review And Repairs

One parent review of the unified diff. Repairs, all by the parent:

- The budget table said "per candidate" for limits that hold per review cycle.
- The craft floor read was recorded in `### Frontend Design Usage`, whose rows the checker validates against the `frontend-design` snapshot; it is now recorded in the task record.
- The `UI_DESIGN.template.md` review summary names the pilot diagnosis and the fix exchange.
- Focus measurement read the "before" style while the control could still hold focus from the Tab press; it now blurs first.
- Two wording defects in `review-workflow.md` and `ui-design-pass.md`.

Accepted departure: W4 embeds the product block before the page's own styles but not after the reviewer block, because moving the reviewer block would change output without the flag.

Known limits: `--product-css` does not check that the file is inside the repository. No browser test loads a page with the embedded block. Contrast is `unmeasured` for text over art or gradients.

## Verification

On the branch head before the two wording repairs (`93082e6b`), logs under `task/ui-review-one-pass/verify/`:

- `ci_test_shards.py run --suite ui --workers 3` with required browser tests: 30 modules passed.
- `ci_test_shards.py run --suite harness --workers 6`: 128 modules passed.
- `pyflakes` on both script trees and `git diff --check`: clean.

After the wording repairs the document-pinning modules were rerun and passed. The full matrix command and CI have not run; they belong to the release candidate.

## Handoff

Nothing is pushed. To publish: add the README descriptive sections and version entries in four languages, run `prepare_release.py`, run the matrix on the candidate, open the PR. Trial the flow on the next new UI round and measure time to approval, capture time, repeated defect families, evidence-only work and owner visual corrections against agentkiosk round 4. In-flight rounds keep their entry pin.
