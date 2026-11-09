# EPIC-initial-delivery-production-first: a first delivery lands on main and ships to production

Status: in progress on `feat/initial-delivery-production-first` (base `main` `1b70cd25`, 0.79.1); three Sonnet 5.5 writers, parent integrates
Design workflow: enhancement
UI impact: none (release rules, two checkers, templates and references; no product UI).

## Problem And Baseline

Every consumer PRD ends with a product that has never been deployed. The Harness still makes that first delivery build two deployed stages: a `development` target (`<name>-dev`, its own D1, Turnstile test keys, mail in test mode) that a branch Preview deploys to, and `production` on `main`. `release_targets.py` refuses an architecture whose surface lacks the development target; `check_deployment.py` refuses a `DEPLOYMENT.md` without the development row, cells and preview record. The six agentkiosk acceptance scenarios that need a deployed binding have waited since 2026-11-08 (DEC-009) on a dev Worker the owner never intended to build.

Owner direction (2026-11-09): the first delivery of a product, the one its single PRD produces, lands on `main` and is production. No preview stage for it. Preview is for the enhancements that follow, when there are users to protect.

Baseline: `main` `1b70cd25` (0.79.1). The 2026-10-14 change `5de8434c` replaced the `development` branch with branch previews but kept the development stage; `branch-promotion-contract.md` already classifies a delivery as `initial_delivery` or `enhancement` and routes both through preview acceptance.

## Accepted Scope

- Architecture marker `Initial delivery: production-first/1` under `## Release Targets`, beside `Release source policy: main-preview/1`. With it, a surface may declare only its production target. Without it, nothing changes.
- `release_targets.py`: parse the marker into `ReleaseTargetContract.initial_delivery_protocol`; drop the missing-development finding for marked packages; keep every check on a development target that is present.
- `check_deployment.py`: read `Delivery kind` from `## Branch Promotion`. For `initial_delivery` under a marked architecture, the development cells and the preview record lines may hold the exact literal `n/a — initial delivery: production is the first deployed environment`. For `enhancement`, the development target, cells and preview record are required as today, marker or not. Inconsistency between the record and the architecture is a finding.
- `branch-promotion-contract.md` and `deployment-contract.md`: the initial-delivery path skips preview acceptance; the production deploy of the main SHA and its smoke are the deployed verification; the first enhancement adds the development target and the preview.
- `delivery-acceptance-contract.md`: deployed-environment scenarios of an initial delivery run as production smoke rows under the existing production constraints (no synthetic fixtures, no mock auth); a scenario that cannot be production-safe is owner-descoped, never relabelled.
- Templates and operating rules updated to match; version 0.80.0 (the bundle gains a contract marker).

Kept unchanged: `main-preview/1`, the two-stage rule for enhancements, exact-SHA promotion, separate action-time authorization for push, landing and deploy, every security rule. The acceptance checker already enforces the production constraints.

Out of scope: agentkiosk's own adoption (its RUN-007 closes on the 0.76.1 pin; the architecture and DEPLOYMENT edits follow its bundle adoption).

## Missions

| Writer | Owns | Deliverable |
| --- | --- | --- |
| W1 | `skills/product-definition-builder/scripts/release_targets.py`, `check_product_package.py`, `platform_delivery.py` if needed, new test `tests/test_release_targets_initial_delivery.py`, `references/output-contract.md` | marker parsing, optional development target, output-contract text |
| W2 | `skills/delivery-harness/scripts/check_deployment.py`, `tests/test_deployment_record.py`, `tests/test_skill_contract.py` (delivery-harness), `assets/templates/DEPLOYMENT.template.md` | delivery-kind aware record checks, the `n/a` literal, template guidance |
| W3 | `references/branch-promotion-contract.md`, `deployment-contract.md`, `delivery-acceptance-contract.md`, `project-operating-rules.md`, `assets/templates/HARNESS_PLAN.template.md` | the rules, within the docs weight budget and the phrases `test_skill_contract.py` pins |
| parent | this Epic, `docs/DOCUMENTS.md`, version surfaces, integration, matrix, review | integration on the work branch, 0.80.0 entries, protected read-only GPT review of the diff |

Writers: `claude-t3-direct` / `claude-sonnet-5-5` / effort xhigh via `delegate_task`, one brief each, T3 worktrees from the Epic commit. Workers do not delegate, change models, push or edit files outside their row.

## Log

- 2026-11-09: branch cut from `1b70cd25`; Epic and briefs written; W1 to W3 dispatched.
