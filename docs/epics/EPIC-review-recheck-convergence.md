# Review Recheck Convergence

Status: candidate verified; publication pending
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
- Scope-disjoint carry-forward, direct route only: a review PASS at SHA X stays valid for descendant Y when every X..Y path is outside the review scope and non-executable (docs, Epic, evidence, README). Record the origin SHA and the path list; never relabel the PASS as fresh. Managed runs keep `reconcile-coordination-head` and gate freshness.
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
| P3b READMEs, CHANGELOG, Epic, version 0.68.0 | GLM-5.3 Flash worker, worktree `t3-6e139aef` | `9a4187b0`..`e1303c49`, integrated `8f9cee93` | `test_skill_contract.py` 63 OK, `check_skill_spec.py`, `git diff --check` |
| P3a rules: triage, re-check scope, repair gate, environment blocks, carry-forward, security applicability, review points | GLM-5.3 Flash worker, worktree `t3-2977e2f9` | `d6746d99`..`45f57ac4`, integrated `00de4171` | `test_skill_contract.py` 64 OK, `docs_weight.py` +756 words |
| P2 re-check packet section and `recheck` contract | GLM-5.3 Flash worker, worktree `t3-9f87ac5e` | `bfe70eba`, `66f09e6c`, integrated `6271c09c` | `test_review_recheck_packet.py` 7 OK, packet suites 40 OK |
| P1 `--note` and `--blocker-class environment` with validator support | GLM-5.3 Flash worker, worktree `t3-61a0fe4d`; the worker hit its 100-turn limit before committing, the parent verified the clean work and committed it | `60e1f4f9`, integrated `3fa44429` | `test_review_triage.py` 5 OK, review suites 38 OK, `test_harness_v11.py`, `test_graph_closeout.py` 8, `test_close_wave.py` 41 |
| Review round 1 at `3fa44429` | Protected GPT-6.1 Sol xhigh read-only reviewer; T3 Opus route refused by the profile hook. Two first attempts were environment-blocked (git unusable in the read-only sandbox: WinError 1920, "cannot come back to cwd"); refunded under the new rule, then re-run with a git-free identity protocol (parent-supplied diff, commit log and tracked-file SHA-256 manifest in `review-input/`) | runs `20261025-150037-5b92a1f5` (scripts, security PASS) and `20261025-150041-1fe75ddb` (rules) | `fix_required`: R1-B1 closeout kept rejecting an environment-blocked worker; R1-B2 the historical-review predicate rejected it after a repair head; R2-B1 the security carry-forward contradicted managed gate freshness; R2-B2 cap said per node, code counts per lineage. Notes: packet bullet prefix, UTF-8 truncation, RRC-4 mapping |
| Consolidated repair | Parent: carry-forward limited to the direct route, cap wording per lineage, packet bullet, RRC-4; GLM-5.3 Flash worker (`t3-f59f4906`): both manifest predicates admit environment-blocked workers, two new tests | `baf034a1`, `bbe65e49`, `b1bcc90a`, `572ab4bb`, `353b4c5d`, integrated `d5e7a930` | focused suites per commit; `test_review_triage.py` 7 OK, review suites 47 OK, `test_historical_integration_review.py` 9 OK |
| Targeted re-check at `d5e7a930` | Same protected reviewer with the four prior findings, prior notes and repair range `3fa44429..d5e7a930`; security lens full scope | run `20261025-153751-5a215491` | PASS; F1-F4 resolved; security PASS; notes: N2 UTF-8 truncation unchanged (backlog), N4 two prose lags |
| Prose alignment after the re-check | Docs-only: historical-review paragraph names environment-blocked entries; Epic carry-forward summary gains the direct-route qualification | `9f2b420f` | Carried forward from the `d5e7a930` PASS under the direct-route rule; paths: `references/execution-state-model.md`, this Epic |

## Verification

Full Required Verification matrix on an immutable detached checkout of `d5e7a930` (log `matrix-d5e7a930.log` in the task directory `%LOCALAPPDATA%/Temp/pdh-review-convergence-20261025/`): `check_skill_spec.py`, pyflakes across all six script trees and `docs_weight.py` exit 0; delivery-harness 1554 tests OK (19 skipped); golden path 1 OK; product-definition-builder 200 OK; ui-design-builder 349 OK (2 skipped); design-system-compiler 214 OK (2 skipped); product-activation 68 OK; seo-growth-review 21 OK; `git diff --check` exit 0. An earlier matrix at `3fa44429` ran in the parent's working checkout and reported one failure caused by the parent editing a reference mid-run; it is superseded, not evidence.

Independent review: `3fa44429` `fix_required` (two reviewers, scripts and rules), repaired once, `d5e7a930` PASS with security PASS. Two environment-blocked attempts were refunded and did not count. Opus 5.5 was requested for review but the profile hook refuses T3 review roles without an enforced read-only transport; GPT-6.1 Sol xhigh through the protected reviewer was used instead, per the owner's fallback instruction.

## Remaining Work

- Publication: PR from `fix/review-recheck-convergence` to `main`, CI on the exact candidate, tag `v0.68.0`, and consumer syncs. No push, PR or installation is authorized by this record.
- Backlog notes: repair-diff truncation can split a UTF-8 character (`render_review_packet.py`); the refund-cap test has no successor-node shared-lineage case; the closeout test removes the diagnostic but does not drive a full closeout.
- The git-free reviewer identity protocol (`review-input/` diff, log and SHA-256 manifest) worked where the read-only sandbox cannot run git; consider adopting it in the reviewer packet so environment blocks stop recurring.
- Task-owned checkouts under the task directory and the four T3 worktrees are retained; removal is a separate action.
