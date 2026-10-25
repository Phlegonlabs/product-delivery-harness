# PRD Deltas And Ambition

Status: in_progress; worker packages pending integration
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
| pending | | | |

## Verification

Pending. Focused suites run per package before integration; the full Required Verification matrix runs once on the fixed integration candidate.

## Remaining Work

- Retrofit Jolvex, agentic-commons and AgentKiosk into a current `PRD.md` plus per-round deltas, one follow-up per project after this release.
