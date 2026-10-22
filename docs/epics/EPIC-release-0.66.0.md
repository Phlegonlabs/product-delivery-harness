# Release 0.66.0: Fewer Review Rounds

Status: in progress (local candidate; PR, CI, main, tag, installation and consumer syncs pending)
Design workflow: enhancement
UI impact: none (skill contracts, validators and documentation; no product UI).

## Problem And Baseline

Every product and every Harness version paid many review rounds. AgentKiosk showed the cost: 8 HiFi review waves with 5 reviewers each, 3 Product Definition re-approvals, 29 tasks planned as 26 missions with 37 review nodes, and the Harness bundle re-adopted about five times mid-run. Its private bundles came from an unreleased Codex branch, so main never received that work.

Baseline: `origin/main` `32893537` (v0.65.3).

## Accepted Scope

Owner requests in chat on 2026-10-22: review the whole skill set (Product, UI, delivery, go-to-market, social content) on Fable once; change it with multiple Opus agents; review once on Opus 5.5; push, release, and sync every repository that uses the skills. No GPT review. Include the Codex AgentKiosk branch with the commit-boundary fix.

Kept: owner decisions, exact-SHA security review, HiFi 85/80, mandatory Impeccable critique and audit, real-browser evidence, Visual Approval, authorization and data-safety rules.

## Work

| Part | Source | Result |
| --- | --- | --- |
| Review boundaries | `review-batch-boundaries` (EPIC-review-batch-boundaries) | Feature-batch missions; one repair after all reviews; one contract per RUN |
| Codex AgentKiosk line | `integration-commit-recheck` (36 commits) | Compiler motion replay and CSP repairs, state coverage, retry head, role policy, integration ingestion, commit-boundary recheck (EPIC-integration-result-adoption) |
| Whole-skill review | Fable `claude-fable-5-1`, high, read-only | 83 gates (73 mandatory) inventoried; 7 change packages with disjoint files |
| P1 UI review scope | Opus writer, `ui-review-scope` | Scoped HiFi re-review, audit axes once, lead plus one Impeccable operator, repair classes, one revised direction study, carried rows, session reuse |
| P2 Diagnostic validator | Opus writer, `diagnostic-retention` | Retention values use the strict rule; no false defects |
| P3 Product contract gate | Opus writer, `product-contract-gate` | PRD check fails unreachable surfaces and opened states without exit; contract delta; one self-review; changed-section translation compare; two link inventories |
| P4 Identity churn | Opus writer, `identity-churn` | Design-round pin; identity finding once per session; audit reuse across compaction; one entry and one exit check |
| P5 Managed review topology | Opus writer, `managed-review-topology` | One combined-lens reviewer per mission; recorded clean merge chain skips the non-security code integration review; scoped final page quality |
| P6 Downstream read scope | Opus writer, `downstream-read-scope` | Compiler and Activation read the sections they use; preview browser inspection for motion, pseudo states and script-running Surface plates |
| P7 Token diet | Opus writer, `token-diet` | Entry checklist, legacy-pins file, deduplicated rules |
| Integration fixes | Parent | CSP diagnostic and loader fixtures cover the full manifest; ingestion fixture no longer leaks a test path; motion verifier writes UTF-8 |

## Verification

Recorded with the release candidate below. Earlier evidence: `review-batch-boundaries` full delivery-harness suite 1752 OK (21 skipped); release base `fc69958d` suites ui-design-builder 417, design-system-compiler 258 (5 skipped), product-definition-builder 306, product-activation 75, seo-growth-review 22, all OK.

## Remaining Work

Opus 5.5 review of the final candidate, PR and CI, main landing, tag, installation, and consumer syncs. AgentKiosk's active RUN adopts the release once at a quiescent boundary through its own parent.
