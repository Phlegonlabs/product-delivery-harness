# Review Recheck Convergence

Status: in_progress
Design workflow: enhancement
UI impact: none (review contracts, attempt scripts and documentation; no product UI changes).

## Problem And Baseline

Three consumer projects looped review → repair → review on the same defects. AgentKiosk spent its two default repair rounds plus one owner extension on one verifier failure family reviewed by GPT reviewers, and lost two more rounds to a read-only sandbox that denied `git status` and to a branch rename. agentic-commons ran review rounds R1-R4 with three parallel code reviewers on one candidate.

The Harness transition amplified the loop: it rejected any PASS that carried findings, the re-check packet carried no prior findings or repair diff, and environment-blocked attempts consumed the two-attempt budget.

Baseline: `main` `7bec932d` (v0.67.0). Branch `fix/review-recheck-convergence`, clean at start.

## Accepted Scope

Owner requests in chat on 2026-10-25: "review 重審的問題如何可以解決" and "這套 skills 裏面的流程如何可以優化，讓 review 次數減少".

- Finding triage: a reviewer returns blocking findings (defect against accepted scope, TEST obligations, security, correctness) and non-blocking notes (style, decorative, suggestions). Only blocking findings produce `fix_required`; `record-review-attempt --note` records notes with a PASS and routes them to the backlog or Epic.
- Scoped re-check: the re-check packet carries the prior reviewed head, the prior blocking findings, prior notes and the repair range `<prior>..<head>` with its diff. The reviewer gives a verdict per prior finding (resolved / unresolved / superseded), inspects the repair range and direct consumers, keeps the security lens at full scope, and reports anything else as a note.
- Environment-blocked attempts: `record-review-attempt --result blocked --blocker-class environment` (checkout or branch mismatch, permission denial, unavailable runtime, interrupted before inspection) keeps the attempt log and worker entry and refunds the node attempt, at most two refunds per review lineage per RUN. It is never a verdict or a PASS.
- Pre-review repair gate: a repair reaches the reviewer only with the author's focused verifier PASS at the new head and, for a failure family, the family's acceptance matrix. Otherwise it returns to the author and costs no review attempt.
- One reviewer per candidate carries every lens. Parallel reviewers need an explicit owner request and still return one consolidated finding set.
- The direct-route security lens applies to executable diffs: code, configuration, dependencies, CI, infrastructure, secrets, data access. A docs, copy, Epic, evidence or bookkeeping-only diff records `security: not_applicable (<reason>)` with the path list instead of `UNVALIDATED`.
- Scope-disjoint carry-forward: a review PASS at SHA X stays valid for descendant Y when every X..Y path is outside the review scope and non-executable (docs, Epic, evidence, PLAN/RUN bookkeeping, README). Record the origin SHA and the path list; never relabel the PASS as fresh.
- Planned review points are recorded at System Review And Route with a reason for each beyond one combined review plus one re-check.

Kept unchanged: owner decisions, exact-SHA security freshness for code changes, HiFi 85/80, Impeccable, Visual Approval, the authorization ledger, `max_attempts` at most 2, and data safety. UI and PRD review waves were already cut to one wave in 0.66.0.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| RRC-1 | Triage splits blocking findings from notes; only blocking findings set `fix_required`; notes record with a PASS | `test_review_triage.py` |
| RRC-2 | The re-check packet carries the prior head, prior blocking findings, notes and the repair range with its diff | `test_review_recheck_packet.py` |
| RRC-3 | Environment-blocked attempts refund the node attempt within two refunds per review lineage per RUN and never count as a verdict | `test_review_triage.py` |
| RRC-4 | The repair gate requires the author verifier PASS at the new head and a failure-family acceptance matrix before dispatch | `test_skill_contract.py` (rule text; dispatch refusal is a parent duty, not a transition) |
| RRC-5 | One reviewer carries every lens; parallel review needs an owner request and returns one finding set | `test_skill_contract.py` |
| RRC-6 | The security lens covers executable diffs; non-executable diffs record `security: not_applicable (<reason>)` with paths | `test_skill_contract.py` |
| RRC-7 | Scope-disjoint carry-forward records origin SHA and paths and never relabels a PASS fresh | `test_skill_contract.py` |
| RRC-8 | Review points beyond one combined review plus one re-check carry a recorded reason | `test_skill_contract.py` |

README consistency across the four languages is covered by the `test_skill_contract.py` version assertions and `test_readme_structure.py`.

## Document Impact

`SKILL.md` and the review references (P3a), `record-review-attempt` and `render_review_packet.py` with their tests (P1 and P2), and the four READMEs plus `docs/DOCUMENTS.md` (this package).

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| pending | pending | pending | pending |

## Verification

pending
