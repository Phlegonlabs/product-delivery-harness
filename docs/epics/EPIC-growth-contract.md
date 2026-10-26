# Growth Contract, Product Tracks And The Agentic Operations Console

Status: in_progress; worker packages pending integration
Design workflow: enhancement
UI impact: none (skill rules for consumer products, READMEs and documentation; no product UI in this repository).

## Problem And Baseline

After 0.70.0, the flow stopped at delivery. Growth goals — return visits on web, downloads and installs on app, connections and active runs on agent — had no contract from PRD to post-launch. App, agent and console needs appeared late or not at all, and discovery never asked why users return or where they first see the product.

Baseline: `5fa1f058` (0.70.0 candidate on `feat/review-budget-and-mvp-profile`). Branch `feat/growth-contract`, clean at start.

## Accepted Scope

Owner decisions in chat on 2026-10-26:

- Three product tracks with north stars: web (return visits), app (downloads and installs), agent (connections and active runs). Every project declares its shape on purpose through the PRD At a Glance `Shape` row — track, companion public surface and console type — and the checker validates it against journeys, UI surfaces and release targets.
- `## Growth Contract` lives in `PRD.md` next to `## Ambition`: north star with Day 7 and Day 30 targets and stretch, re-engagement mechanisms, discovery surfaces and a launch window. Discovery asks why people come back and where they first see the product.
- Agentic projects design the operations console on purpose: the architecture playbook's `agentic-operations-console` profile with configuration, execution, human-in-the-loop, cost and usage, quality and security modules, plus required journeys and tests when the shape says `console: operations`.
- Defaults the parent chose: the contract stays inside `PRD.md`, agent directories are an owner-selected list in the PRD, and this is release 0.71 separate from 0.70.

Kept unchanged: no publishing, scheduling or ad spend by the skills; no ranking promises; the authorization ledger; the security lens; data safety.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| GC-1 | The PRD package check validates the At a Glance `Shape` row and the `## Growth Contract` tables against journeys, UI surfaces and release targets | `test_product_package_checker.py` (Shape, Growth Contract) |
| GC-2 | Product Definition records the `Shape` row, `## Growth Contract` and the two new Segment 4 discovery prompts | `test_skill_contract.py` (product-definition-builder) |
| GC-3 | The UI contract requires the track-specific surfaces, including the console's three core screens when `console: operations` | `test_skill_contract.py` (ui-design-builder) |
| GC-4 | Delivery foundations expand per track (SEO/GEO/AEO, deep links, push, measurement, directory metadata, `llms.txt`) and the architecture playbook holds the `agentic-operations-console` profile | `test_skill_contract.py` (delivery-harness) |
| GC-5 | Product Activation owns the `aso-and-store-launch`, `agent-directory` and `geo-readback` profiles, and seo-growth-review owns `pre_launch` mode and the Day 7 and Day 30 `growth_review` cadence | product-activation and seo-growth-review test suites |
| GC-6 | The four READMEs describe the same release meaning and keep the version-history contract at 0.71.0 | `test_skill_contract.py` version assertions and `test_readme_structure.py` |

## Document Impact

Four sibling packages (G1-G4) own the canonical rules under `skills/**` and `standalone-skills/**` except the version surfaces: product-definition-builder (the `Shape` row, `## Growth Contract`, interview prompts and the package checker), ui-design-builder (track-specific required surfaces and the console archetype), delivery-harness (the `agentic-operations-console` profile and per-track delivery foundations) and the growth skills product-activation, go-to-market, gtm-content and seo-growth-review (activation profiles, Launch Reach Plan, content pipeline and growth-review cadence). This package owns `README.md`, `README.zh-TW.md`, `README.zh-CN.md`, `README.es.md`, `CHANGELOG.md`, this Epic, `docs/DOCUMENTS.md`, `package.json`, `package-lock.json`, `skills/delivery-harness/VERSION` and the `MISSION_RUNBOOK.template.md` `required_harness_version` default.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| pending | Worker packages G1-G5 land the canonical rules, READMEs, version surfaces and this Epic; entries record at integration | pending | pending |

## Verification

pending

## Remaining Work

- Consumer retrofits: the three consumer projects' PRDs gain a `Shape` row and a `## Growth Contract`.
- Test-suite sharding for speed.
