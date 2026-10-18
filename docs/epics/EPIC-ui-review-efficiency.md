# UI Review Efficiency

Status: in_progress
Design workflow: enhancement
UI impact: none (review contracts and validators; no product UI changes).

## Problem And Baseline

HiFi can meet every dimension threshold and still fail the overall-score threshold.
Repairs also repeat the complete qualitative review, even when their impact is limited.
Baseline: `bf56ab27744a4c1b95c08040eabfb4b021b2fbcc`, observed `origin/main`, in the `9e8f` source checkout.
The owner approved branch `ui-review-thresholds`; the initial working tree was clean.

## Accepted Scope

The owner accepted this outcome in chat on 2026-10-18:

- Keep Impeccable critique and audit mandatory.
- Keep every dimension threshold, concrete blocking finding, evidence requirement and human approval.
- Continue recording the actual overall score, but make it advisory.
- Require concrete evidence and completion criteria for requested repairs.
- Recheck repairs and affected consumers without starting another broad qualitative search.
- Preserve current-candidate evidence, the complete required browser matrix and existing attempt limits.

The follow-up about repeated review waves is part of this review-efficiency scope.
Managed mission, integration and security review policies remain separate; no scheduler change is assumed.
Local edits and atomic commits are authorized. Push, release and installation are not authorized.
This is one coupled source contract with one writer and focused verification; no PLAN/RUN is needed.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| URE-1 | A HiFi candidate below 90 overall passes when every dimension and required check passes. | Contract and diagnostic regression tests |
| URE-2 | Low dimensions, concrete defects, missing Impeccable and stale evidence still fail. Legacy Wireframe thresholds stay unchanged. | Positive and negative regressions |
| URE-3 | Initial review is complete; repair review targets known defects and affected consumers. Current receipts and complete required coverage remain mandatory. | Cross-contract tests and independent source review |

## Document Impact

UI rubric, review workflow, stage procedure, evidence guidance and the four READMEs describe the same readiness and repair rules.
The diagnostic and strict UI checkers retain their current formats and report identities.
No local-only file class or Gitignore change is introduced.

## Change Log

| Observation | Scope and result | Evidence and remaining work |
| --- | --- | --- |
| 2026-10-18 entry | Created the owner-approved branch from the observed baseline. Source inspection found two numeric enforcement sites and repeated qualitative-review rules. | Implementation, focused verification and exact-candidate independent review pending. |
| 2026-10-18 navigation repair | Positive grading tests exposed order-dependent navigation pairing. Correct observations could manufacture defects and another repair wave. | Three dedicated tests reproduced red and then passed green. Pair matching prefers the observed destination; wrong, duplicate and missing observations still fail. The combined working-tree diagnostic suite passed 23 tests. Evidence: external `ui-review-efficiency` logs. Independent review remains pending. |
| 2026-10-18 advisory score | Navigation repair committed as `b1b149c2`. Removed the overall threshold from diagnostic repair eligibility and strict HiFi readiness. | Working-tree checks passed: UI contract 58, diagnostic 23, UI skill contract 13, Pyflakes, source specification and documentation weight. A documentation phrase assertion failed once and passed after restoring its established phrase. All dimension, Impeccable, stale-input and legacy Wireframe failures remain covered. |

The touched validators exceed 500 lines but retain their existing contract-entry responsibilities.
This change removes two conditions and preserves their public interfaces; no module split is justified here.
Document sync remains `review_required` when the loaded skill identity and prior snapshot are unobserved.

## Results And Remaining Work

No release, installation or product visual-quality result is claimed.
