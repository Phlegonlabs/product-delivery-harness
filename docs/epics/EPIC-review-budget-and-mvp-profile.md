# Review Budget And MVP Profile

Status: in_progress; worker packages pending integration
Design workflow: enhancement
UI impact: none (Harness review rules, managed route, READMEs and documentation; no product UI changes).

## Problem And Baseline

Even after 0.68.0, every repair re-bound the full review scope, and a second review round needed the owner's recorded explicit decision. Consumer rounds burned days on global re-reviews after small repairs, and the owner wants small projects delivered in a week.

Baseline: `3a58802b` (main, 0.69.0). Branch `feat/review-budget-and-mvp-profile`, clean at start.

## Accepted Scope

Owner decisions in chat on 2026-10-26:

- Two reviews pass. Each candidate stage (PRD package, UI HiFi, delivery candidate) gets at most one initial review and one targeted re-check; the owner-authorized extra round and successor review nodes are gone.
- Isolated repairs without global re-review. After the re-check, each remaining or new defect becomes one bounded repair with its own focused verifier and a scoped review of the repair diff only (finding, repair diff, direct consumers). The security lens joins only when the diff touches a trust boundary (PRD Security Requirements, auth, session, secrets, data access, dependencies, CI, infrastructure); a scoped PASS re-binds the repaired paths and the prior PASS carries forward for untouched paths; scoped reviews do not consume review attempts. Final UI Acceptance reruns only when the repair touches a UI surface, then only that surface. The broad regression suite runs once per candidate at the end; a failure there is an isolated repair followed by only the failing suites. The managed route carries this: `reconcile-candidate-head --repair-path` (with `--trust-boundary`) records repair scopes, `record-review-attempt --scoped` records a scoped PASS, closeout validates the coverage chain from the last full PASS, and the review packet renders a `## Scoped repair review` section.
- Speed target of one week. `Delivery profile: standard | mvp` is chosen by the owner at System Review and recorded in the PRD At a Glance. Under `mvp`: Stack Decision Checkpoint and Product Definition Approval in one owner call, research-first may end as documented assumptions, the discovery segments may compress to two turns, one direction study, HiFi for required surfaces, one wave plus one re-review, Visual Approval, design-system compilation only when required, one combined delivery review with Final UI Acceptance folded in plus one re-check, and at most four owner gates (approval with stack, Visual Approval, execution authorization, release). Target: a small project or an MVP in one week.

Kept unchanged: HiFi 85/80, Impeccable on the first wave, real-browser evidence, the security lens on executable diffs, data safety, exact-SHA binding and the authorization ledger. Legacy packages without the `mvp` profile or scoped-repair records stay valid.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| RBM-1 | The delivery rules and managed route implement the two-review budget and the isolated repair protocol: repair scopes with trust boundaries, `record-review-attempt --scoped`, closeout coverage chain from the last full PASS, and the `## Scoped repair review` packet section | `test_skill_contract.py` (delivery-harness) |
| RBM-2 | Scoped reviews enforce scope-bound carry-forward and the trust-boundary security join, and do not consume review attempts; a broad-validation failure becomes an isolated repair followed by only the failing suites | `test_scoped_review.py` |
| RBM-3 | The UI contract keeps one wave plus one re-review with the extra round removed, and post-repair Final UI Acceptance covers only the repaired surface | `test_skill_contract.py` (ui-design-builder) |
| RBM-4 | Product Definition records the `Delivery profile` owner choice at System Review in the PRD At a Glance and applies the `mvp` compression rules | `test_skill_contract.py` (product-definition-builder) |
| RBM-5 | The pre-delivery self-review reflects the two-review budget and isolated repairs at the author exits | `test_pre_delivery_self_review.py` |
| RBM-6 | The four READMEs describe the same release meaning and keep the version-history contract | `test_skill_contract.py` version assertions and `test_readme_structure.py` |

## Document Impact

Three sibling packages own the canonical rules under `skills/**` except the version surfaces: the delivery harness (two-review budget, isolated repair protocol, managed route commands, review packet and their tests, including `test_scoped_review.py` and `test_pre_delivery_self_review.py`), `ui-design-builder` (wave, re-review and post-repair UI acceptance rules and tests) and `product-definition-builder` (Delivery profile, System Review, PRD At a Glance and `mvp` compression rules and tests). This package owns `README.md`, `README.zh-TW.md`, `README.zh-CN.md`, `README.es.md`, `CHANGELOG.md`, this Epic, `docs/DOCUMENTS.md`, `package.json`, `package-lock.json`, `skills/delivery-harness/VERSION` and the `MISSION_RUNBOOK.template.md` `required_harness_version` default.

## Change Log

pending

## Verification

pending

## Remaining Work

- Consumer syncs after the release lands.
- The growth skills review (go-to-market, gtm-content, product-activation, seo-growth-review) for reach and clicks is a separate follow-up.
