# EPIC-001: Incremental design and interactive review

Status: in_progress

## Problem And Baseline

An enhancement could trigger a fresh all-screen design pass even though only one
feature changed. Reviewer pages also mixed product content with review metadata,
showed token values without useful specimens, and left some controls inert.

Baseline: Harness 0.47.0, `3f6d7d2ebad2899fe4045b99a2bb4f9bfa19a12a`.
This is internal skill maintenance (`HARNESS`), not a new product PRD.

## Accepted Scope

On 2026-09-20 the owner requested usable Wireframe/HiFi review, then clarified:
enhancements add or change only affected pages and necessary connecting controls.
Existing layout, content, style and identities stay unchanged outside that scope.
Complete artifact coverage is not permission to redesign the complete product.

Record small fixes in their existing Epic or direct task. Create an Epic for an
independent accepted outcome, not for each edit or failed test. Apply this rule
across Product Definition, UI authoring, compilation and delivery.

The owner requested local commits, branch push, PR and merge for the skill bundle.
The exact main-promotion gate still applies. No force push, branch/worktree cleanup,
website deployment or overwrite of the original website is included.

## Acceptance And Dependencies

| Requirement | Expected result | Verification |
| --- | --- | --- |
| HARNESS / incremental scope | Add affected Wireframe and HiFi pages; retain unrelated screens and the existing direction | Contract tests, preservation checks and exact-head review |
| HARNESS / reviewer | Left page/target controls, one product screen, real style specimens and separate state coverage | Wireframe and HiFi contract/runtime suites |
| HARNESS / interactions | Editable local controls retain input and perform declared actions | Search, clear, language, Enter, focus and overlay regressions |
| HARNESS / history | Epic selection and per-change history cover small fixes without duplicating PRD/RUN | Template and cross-skill contract tests |
| HARNESS / release | Required suites, golden path and fixed-SHA security review pass before publication | Repository verification and PR checks |

## Document Impact

Canonical changes are under `skills/`, plus this record and the four READMEs.
The shared bounded-enhancement rule owns Epic selection. UI guidance owns the
affected-screen design scope; the compiler retains unrelated entries. Existing
product, approval, authorization and release gates remain in place.

## Change Log

| Change | Reason and scope | Commit / evidence | Result |
| --- | --- | --- | --- |
| Wireframe composition | Explicit geometry, editable fields and preserved reviewer state | `496f70f`; 75 focused tests | Superseded by the repair below; not browser evidence |
| Wireframe search/overlay repair | Review found inert search and guaranteed wide-dialog overflow | `bfa0d8e`; 79 focused tests | Source/runtime checks pass; exact-head review pending |
| HiFi reviewer | Target/surface switching, specimens and source-bound evidence | Worker `7c67abf`; 22 contract and 4 runtime tests | Review found four blockers; repair in progress, not integrated |
| Incremental scope and Epic rules | Owner reported repeated full UI redraws | Current bounded change | In progress |

## Results And Remaining Work

The GLM attempt failed after partial work; the owner explicitly switched to local
Codex. Existing partial work and failed reviews were retained. No old human receipt
was rewritten and no new human approval was fabricated.

The separate website worktree is a draft, not part of this skill release. Its
whole-regeneration candidate is on hold under the owner's incremental scope rule.
Its original checkout was not overwritten. Six-topic content, copy reconciliation,
navigation coverage and browser/visual verification remain unresolved there.

Skill release gates and exact-candidate main authorization remain pending. Browser
policy prevents claiming a rendered website review; source/runtime tests are not
visual approval. Each repair and release result must be recorded here before closeout.
