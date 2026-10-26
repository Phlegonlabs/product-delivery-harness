# PRD Deltas And Ambition

Status: PR #158 open; alignment repair reviewed; final CI pending
Design workflow: enhancement
UI impact: none (discovery interview, PRD contract, Harness rules and documentation; no product UI changes).

## Problem And Baseline

PRD rounds stack onto one cumulative file. Jolvex `PRD.md` reached 771 lines with dated round sections at top and bottom, 17 archived package folders keep the older states, and one Enhancement Impact Record shows only the latest round, so the approved current state is no longer readable on its own.

The Epic template forbade a PRD per Epic, so a round's changes had no document aligned with the Epic that delivered them. Discovery never asked the goal beyond the goal, who does this best today and with which instruments, a stretch target, an outside judge, or the crew beyond the builder.

Baseline: `1b4d243f` (0.68.0 candidate on `fix/review-recheck-convergence`). Branch `feat/prd-deltas-and-ambition`, clean at start.

## Accepted Scope

Owner decisions in chat on 2026-10-25:

- `PRD.md` holds only the approved current state, with no dated round headings. Each round publishes `docs/product/deltas/PRD-DELTA-<EPIC-ID>.md` (why, Enhancement Impact Record, changed/new/retired requirements with before/after and TEST IDs, decisions, approval, baseline and result PRD hashes, the ambition rung) plus a Traditional Chinese review copy, aligned one-to-one with that round's Epic.
- Retrofit the three consumer projects (Jolvex, agentic-commons, AgentKiosk) into current PRD plus deltas in a separate follow-up per project after this release.
- Full ambition depth: a fourth discovery interview segment ("Ambition"), a `## Ambition` PRD section (three-rung Goal Beyond The Goal ladder with an outside judge per rung, Depth, Range, Access needs; a `Stretch` column in Metrics), and `review lens` crew rows that may act as `domain:<field>` lenses.

Kept unchanged: acceptance still uses the TEST/metric target, owner approvals, the authorization ledger, review budgets and data safety. Legacy packages without delta mode or `## Ambition` stay valid.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| PDA-1 | Discovery asks the fourth Ambition segment (altitude, depth and tools, stretch target, outside judge, range) and `PRD.md` gains `## Ambition` with the rung ladder, Depth, Range and Access needs plus a Metrics `Stretch` column | `test_skill_contract.py` (product-definition-builder) |
| PDA-2 | `check_product_package.py` validates delta mode and the Ambition section, while legacy packages without either stay valid | `test_product_package_checker.py` |
| PDA-3 | Each round's delta and its Traditional Chinese review copy align one-to-one with that round's Epic | `test_review_translations.py` |
| PDA-4 | `check_prd_delta_scope.py` binds every mission/task trace ID to a new or revised ID of the bound delta (or a declared foundation ID) and requires a task for every required delta ID | `test_prd_delta_scope.py` |
| PDA-5 | The Epic template references its delta and records the ambition rung and outside judge, the PLAN freezes a `prd-delta` source, and `review lens` crew rows may become `domain:<field>` lenses carried by the one combined reviewer | `test_skill_contract.py` (delivery-harness) |
| PDA-6 | Document sync inventories delta files | document-sync tests |

README consistency across the four languages is covered by the `test_skill_contract.py` version assertions and `test_readme_structure.py`.

## Document Impact

Packages Q1-Q2: `skills/product-definition-builder/**` (interview, PRD template, `check_product_package.py` and its tests). Package Q3: `skills/delivery-harness/**` except the version surfaces (Epic template, PLAN source freeze, `check_prd_delta_scope.py`, review lenses, document sync and their tests). Package Q4: `README.md`, `README.zh-TW.md`, `README.zh-CN.md`, `README.es.md`, `CHANGELOG.md`, this Epic, `docs/DOCUMENTS.md`, `package.json`, `package-lock.json`, `skills/delivery-harness/VERSION` and the `MISSION_RUNBOOK.template.md` `required_harness_version` default.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Q4 READMEs, CHANGELOG, Epic, version 0.69.0 | GLM-5.3 Flash worker, worktree `t3-2ca25a9e` | `ddc3b911`..`6828d9a0`, integrated `9d4f239e` | `test_skill_contract.py` 64 OK, `test_readme_structure.py` 3 OK |
| Q1 PDB contract: Ambition segment, `## Ambition`, Stretch metrics, `prd-delta/1`, delta template, delta translation pairs | GLM-5.3 Flash worker, worktree `t3-8375d98b` | `f1d3bb88`..`08a6dac3`, integrated `8ad88880` | `docs_weight.py` +1249 words; five PDB contract assertions updated by the parent in `8a251aca`, Segment 4 prompts folded and shortened to the segment limits in `8a251aca` and `849dfec7` |
| Q3 Harness: Epic template binds the delta, `prd-delta` PLAN source and `foundation_trace_ids`, `check_prd_delta_scope.py`, `domain:<field>` lenses, delta inventory in document sync | GLM-5.3 Flash worker, worktree `t3-90b724db`; the worker hit its 100-turn limit, the parent verified the clean work and committed it | `b24801b0`, `644a491e`, `653a21cc`, integrated `38e55960` | `test_prd_delta_scope.py` 8 OK, `test_skill_contract.py` 65 OK, `test_validate_harness_plan*.py` 28 OK, `test_document_sync*.py` 28 OK |
| Q2 PDB checker: delta mode, Ambition validation, `--delta` translation check | GLM-5.3 Flash worker, worktree `t3-5954a9d0`; same 100-turn stop, parent-committed | `b3d68dea`, `aa6ce5b8`, `e1f36013`, integrated `26ea070c` | PDB suite 219 OK on the worker base |
| Review round 1 at `849dfec7` | Protected GPT-6.1 Sol xhigh, git-free identity protocol. Two half-candidate scopes timed out at the 540 s cap (environment blocks, refunded); four narrow scopes completed | runs `20261025-171101-8eba5a13` (PDB scripts), `-1cd09f15` (Harness scripts), `-b3eb2a91` (PDB rules), `-586d01bd` (Harness docs, PASS) | `fix_required`: delta approval block ignored; retired IDs rejected in the delta impact record; `Verbs:` regex crossed the newline; delta location could escape `--repo-root` (CWE-22); Required-Yes read only from a literal annotation; translation command lacked `--delta`. The full matrix at `849dfec7` also flagged the new script missing from the CLI UTF-8 inventory (`9e8e8f38`) and one load-induced motion-test flake that passed alone |
| Consolidated repair | GLM-5.3 Flash workers `t3-0629f594` (PDB checker, five commits) and `t3-b951b44c` (scope checker, three commits); parent prose `e92c461b` | `f143715a`..`b6e66e2a`, `26abf900`..`d6723c02`, integrated `bcb0a9e6` and `3c642b28` | PDB suite 225 OK; `test_prd_delta_scope.py` 18 OK |
| Targeted re-check at `3c642b28` | Three narrow scopes with the prior findings and repair range | runs `20261025-173252-d5c198a5` (PDB scripts PASS), `-8352adef` (Harness scripts `fix_required`), `-0d11fa95` (docs PASS) | All six prior findings resolved; one new finding inside the repair: the escape fixture wrote a fixed filename into the shared temp directory (CWE-377) |
| Owner-authorized third round | Owner answer in chat 2026-10-25 to the explicit extra-round request; fixture moved inside the test-owned directory, Range `none` row and both wide-table exceptions documented | `9dfb1eac`, `ee685e85`; re-check run `20261025-174123-dae157a0` | PASS, no notes |
| PR #158 alignment repair | GitHub review found valid Markdown alignment separators rejected by the scope checker; GLM-5.3 Flash repaired both table parsers | `2bd40262`; tree-equal main integration `a6fd7baa`; protected review `20261026-020616-97e04819` | Four new regressions failed before repair and passed afterward; full module 22 OK. Correctness and scoped security PASS at `a6fd7baa`; final CI pending |

## Verification

Full Required Verification matrix on an immutable detached checkout of `3c642b28` (log `matrix-3c642b28.log` under `%LOCALAPPDATA%/Temp/pdh-prd-deltas-20261025/`): `check_skill_spec.py`, pyflakes across the six script trees and `docs_weight.py` exit 0; delivery-harness 1574 OK (19 skipped); golden path 1 OK; product-definition-builder 225 OK; ui-design-builder 349 OK (2 skipped); design-system-compiler 214 OK (2 skipped); product-activation 68 OK; seo-growth-review 21 OK; `git diff --check` exit 0.

The final head `ee685e85` changes one test module and one reference after that run. Affected suites on an immutable checkout of `ee685e85` (`affected-ee685e85.log`): `test_prd_delta_scope.py` 18 OK, delivery `test_skill_contract.py` 65 OK, `test_cli_utf8_output.py` 3 OK, product-definition-builder 225 OK, `docs_weight.py`, `check_skill_spec.py` and `git diff --check` exit 0.

Independent review: `849dfec7` `fix_required` (four scopes), one consolidated repair, `3c642b28` re-check found one new defect in the repair, one owner-authorized extra round, `ee685e85` PASS. Security lenses passed on the scripts at `3c642b28` and on the test fixture at `ee685e85`. Two timed-out and no git-capable attempts were environment blocks under the 0.68.0 rule and did not count.

PR #158's original candidate `4b46736d` passed the full CI matrix. That result does not cover the alignment repair. The repair's focused tests originated at `2bd40262`; its tree equals `a6fd7baa`. Protected review at `a6fd7baa` verified file hashes before and after inspection and found no blocking findings or notes. Git identity and ancestry were parent-verified; tests were not rerun by the reviewer. Any following bookkeeping-only change retains those origins, not a fresh review result.

## Remaining Work

- Retrofit Jolvex, agentic-commons and AgentKiosk into a current `PRD.md` plus per-round deltas, one follow-up per project after this release.
- Source publication: the owner requested commit, push and merge. PR #158 targets `main` after #157 landed at `8abcd645`. Run CI on the repaired final candidate before merging. Formal tags, installation and consumer syncs remain separate release work.
- Backlog notes from review: `domain:<field>` labels accept control characters; a domain-only lens list leaves `review.type` unchecked; no successor-node shared-lineage refund-cap test; a PRD source location that is blank or a URL falls back to `docs/product/PRD.md` silently.
- Task-owned checkouts under the task directory and the T3 worker worktrees are retained; removal is a separate action.
