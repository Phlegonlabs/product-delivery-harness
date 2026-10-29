# Review Budget And MVP Profile

Status: candidate verified; publication pending
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

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| V4 READMEs, CHANGELOG, Epic, version 0.70.0 | GLM-5.3 Flash worker | `aa0615a3`..`a4ccde28`, integrated `d2e7f317` | `test_skill_contract.py` 65 OK, `test_readme_structure.py` 3 OK |
| V3 UI and PRD review budget, mvp profile | GLM-5.3 Flash worker | `7a196566`..`5b51b643`, integrated `b3e8200e` | ui contract 22 OK, pdb contract 57 OK |
| V1 delivery rules: two-review budget, Isolated Repair Protocol, mvp profile | GLM-5.3 Flash worker | `93d77749`..`d86ca157`, integrated `a1d65faa`; parent gap fixes `0e4ac721`, `9d703b05`, `67fd7d0a` | delivery contract 67 OK |
| V2 scoped review transitions, coverage chain, scoped packet | GLM-5.3 Flash workers (two sessions; the first hit its turn limit after step 1) | `d35455dc`..`15486b38`, integrated `c7cbaafb` | `test_scoped_review.py` 17 OK |
| Review round 1 at `c7cbaafb` | Protected GPT-6.1 Sol xhigh, four narrow scopes; the scripts scope timed out (environment block) | runs `20261026-105605-*` | rules: 5 blocking (packet flag, budget guard, no PASS anchor, security closeout, trust-boundary refund); UI: 2 blocking (fifth owner gate, forced design system); docs PASS |
| Consolidated repair | GLM workers for scripts and UI, parent for prose | `a3e26820`..`49509e08`, `30b2b652`..`582467c8`, `5db50287`, integrated `cf0ec8a1` | full matrix at `cf0ec8a1` green |
| Targeted re-check at `cf0ec8a1` | four narrow scopes | runs `20261026-114421-*` | all 7 prior findings resolved; 6 new in the repair range (pathspec exclusion, reservation at the cap, zero-step anchor, git-failure fallback, security anchor, UI checker direction and empty reason) |
| Isolated repairs, rounds 1-4 under the new protocol | GLM workers (scripts, closeout, UI checker) and parent (prose, anchor residuals) | `802ca0d5`..`20e65ebc`, `c4bb269b`, `df63efeb`, `88ea278b`, `5a7fd21c`, `b2f3a846`, `54fc51e9` | scoped reviews `20261026-123841-*`, `-132546-*`, `-133439-*`, `-134113-*`, final `20261026-13xxxx` PASS; each round shrank the finding set (6 → 4 → 2 → 1 → 1 → 0) |

## Verification

Full Required Verification matrix on an immutable detached checkout of `b2f3a846` (log `matrix-b2f3a846.log` under `%LOCALAPPDATA%/Temp/pdh-review-budget-20261026/`): `check_skill_spec.py`, pyflakes across the six script trees and `docs_weight.py` exit 0; delivery-harness 1618 OK (19 skipped); golden path 1 OK; product-definition-builder 226 OK; ui-design-builder 355 OK (2 skipped); design-system-compiler 214 OK (2 skipped); product-activation 68 OK; seo-growth-review 21 OK; `git diff --check` exit 0. Earlier full runs at `c7cbaafb`, `cf0ec8a1`, `20e65ebc` and `67d85fbd` were also green.

The final head `54fc51e9` changes `harness_manifest.py` and one test module after that run; affected suites on an immutable checkout of `54fc51e9` (`affected-54fc51e9.log`): scoped suites 39 OK, `test_graph_closeout.py` 8, `test_historical_integration_review.py` 9, `test_harness_v11.py` 24, review suites 47, delivery contract 67, pyflakes and `check_skill_spec.py` exit 0.

Independent review: `c7cbaafb` `fix_required`, one consolidated repair, `cf0ec8a1` re-check `fix_required` inside the repair range, then four isolated-repair rounds with scoped reviews, final scoped review of `54fc51e9` PASS with security PASS. The round ran under the rules it introduces: two full reviews, then isolated repairs with scoped reviews and no extra global round.

## Remaining Work

- Publication: PR from `feat/review-budget-and-mvp-profile` to `main`, CI on the exact candidate, tag `v0.70.0`, consumer syncs. Nothing here authorizes a push, PR or installation.
- Backlog notes from review: declared-path coverage has no success-channel receipt; the cross-node attribution test uses an unregistered node and a filtered error list; no regression for foreign attribution with the current node's lineage; the delivery test suite needs sharding (27 minutes per full run).
- The growth skills review (go-to-market, product-activation, seo-growth-review) for reach and clicks is a separate follow-up.
