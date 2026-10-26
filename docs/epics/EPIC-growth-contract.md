# Growth Contract, Product Tracks And The Agentic Operations Console

Status: candidate verified; publication pending
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
| GC-2 | Product Definition records the `Shape` row, `## Growth Contract` and the two new Segment 4 discovery prompts | `test_skill_contract.py::test_discovery_asks_about_return_visits_and_first_contact` (product-definition-builder) |
| GC-3 | The UI contract requires the track-specific surfaces, including the console's three core screens when `console: operations` | `test_skill_contract.py::test_required_surfaces_follow_the_product_track` (ui-design-builder) |
| GC-4 | Delivery foundations expand per track (SEO/GEO/AEO, deep links, push, measurement, directory metadata, `llms.txt`) and the architecture playbook holds the `agentic-operations-console` profile | `test_skill_contract.py` (delivery-harness) |
| GC-5 | Product Activation owns the `aso-and-store-launch`, `agent-directory` and `geo-readback` profiles, and seo-growth-review owns `pre_launch` mode and the Day 7 and Day 30 `growth_review` cadence | product-activation and seo-growth-review test suites |
| GC-6 | The four READMEs describe the same release meaning and keep the version-history contract at 0.71.0 | `test_skill_contract.py` version assertions and `test_readme_structure.py` |

## Document Impact

Four sibling packages (G1-G4) own the canonical rules under `skills/**` and `standalone-skills/**` except the version surfaces: product-definition-builder (the `Shape` row, `## Growth Contract`, interview prompts and the package checker), ui-design-builder (track-specific required surfaces and the console archetype), delivery-harness (the `agentic-operations-console` profile and per-track delivery foundations) and the growth skills product-activation, go-to-market, gtm-content and seo-growth-review (activation profiles, Launch Reach Plan, content pipeline and growth-review cadence). This package owns `README.md`, `README.zh-TW.md`, `README.zh-CN.md`, `README.es.md`, `CHANGELOG.md`, this Epic, `docs/DOCUMENTS.md`, `package.json`, `package-lock.json`, `skills/delivery-harness/VERSION` and the `MISSION_RUNBOOK.template.md` `required_harness_version` default.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| G1 PRD Shape row, Growth Contract, discovery prompts, console pattern | GLM-5.3 Flash worker | `25dc31ac`..`1f051c68`, integrated `b025e6af` | pdb contract 57 OK |
| G3 track surfaces, per-track foundations, activation profiles | GLM-5.3 Flash worker | `c5b762f9`..`1d091012`, integrated `f63a1d15` | ui contract 22, delivery contract 68, activation 68 OK |
| G4 Launch Reach Plan, Content Pipeline, pre_launch and growth_review | GLM-5.3 Flash worker; parent kept pre_launch inline (`5f76145a`) | `78f4342f`..`348d0932`, integrated `720c1c94` | seo-growth-review 21 OK |
| G5 READMEs, CHANGELOG, Epic, version 0.71.0 | GLM-5.3 Flash worker | `4ada8479`..`57b0a9e8`, integrated `782359e4` | delivery contract 67, readme structure 3 OK |
| G2 Shape and Growth Contract checker | GLM-5.3 Flash worker | `0c194e76`..`2b5c8088`, integrated `42ba2408` | pdb suite 248 OK |
| Review round 1 at `42ba2408` | Protected GPT-6.1 Sol xhigh; four scopes, then six narrower prose scopes rerun two at a time after load-induced timeouts | runs `20261026-144257-*`, `-15xxxx-*` | checker: 6 blocking (annotated headers, trace identifiers, per-journey console coverage, excluded SEO lines, quadratic companion regex, signed days); prose: Owner stage values and Day 0-7 rule, focused test pins, activation kind-to-profile mapping, SEO template Mode suffix; docs PASS after pins |
| Consolidated repair | GLM-5.3 Flash workers for the checker (two sessions, disjoint functions), parent for prose and pins | `b75bd617`..`dce344fe`, `af3d9276`..`aaf47c19`, `92108c9a`, `dabd7c1e`, `e6a094d2`, `ff107754` | pdb suite 272 OK; activation, seo, ui, delivery contract suites OK |
| Isolated repairs under the 0.70 protocol | Parent: annotation key, SEO exclusion scoping (three passes until per-occurrence fixed windows with word boundaries), day ranges, huge bounds, activation validator profile catalog, test path setup | `1cebd67b`, `e7ea6044`, `061c605b`; scoped reviews `20261026-15xxxx-*` | final scoped review of `061c605b` PASS; findings shrank 6 → 3 → 2 → 1 → 0 |

## Verification

Full Required Verification matrix on an immutable detached checkout of `42ba2408` (log `matrix-42ba2408.log` under `%LOCALAPPDATA%/Temp/pdh-review-budget-20261026/`): `check_skill_spec.py`, pyflakes across the six script trees and `docs_weight.py` exit 0; delivery-harness 1620 OK (19 skipped); golden path 1 OK; product-definition-builder 248 OK; ui-design-builder 355 OK (2 skipped); design-system-compiler 214 OK (2 skipped); product-activation 68 OK; seo-growth-review 21 OK; `git diff --check` exit 0.

Later heads changed only the product-definition-builder checker and tests, the product-activation validator and tests, and prose. Affected suites on immutable checkouts: `92108c9a` (pdb 269, ui contract 23), `ff107754` (pdb 272, activation 68, seo 21, ui contract 23, delivery contract 68, cross-skill pipeline 18), `1cebd67b` (pdb 272, activation 68), `e7ea6044` (pdb 272, activation 68), `061c605b` (pdb 272); pyflakes, `check_skill_spec.py` and `git diff --check` exit 0 each time.

Independent review: `42ba2408` `fix_required` across the checker and prose scopes, one consolidated repair, then isolated repairs with scoped reviews; final scoped review of `061c605b` PASS. Timed-out and transport-failed review attempts were environment blocks and did not count.

## Remaining Work

- Consumer retrofits: the three consumer projects' PRDs gain a `Shape` row and a `## Growth Contract`.
- Publication: PR chain `feat/review-budget-and-mvp-profile` (0.70.0) then `feat/growth-contract` (0.71.0) to `main`, CI on each exact candidate, tags, consumer syncs. Nothing here authorizes a push, PR or installation.
- Backlog notes from review: the Shape-row tests omit `n/a` prefix and longer-word exclusion variants; validator-level acceptance of the new activation profiles with architecture targets lacks a focused case; the growth_review cadence has no fallback example when no launch reach plan exists.
- Test-suite sharding for speed.
