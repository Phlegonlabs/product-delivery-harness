# EPIC-cloudflare-preview-flow: branch previews before main

Status: in_progress

## Problem And Baseline

Consumer delivery requires ordinary candidates to land on permanent `development` before `main`.
The owner requested PR or branch previews instead, including Cloudflare-hosted products.
Baseline: clean detached `8a47dab37b0d7e6ffcfce447ad94f686aeae6f98`, Harness 0.62.3.

## Accepted Scope

On 2026-10-14, the owner confirmed PR/branch Preview replaces `development` and selected `codex/cloudflare-preview-flow`.
Update local source, validators, templates, tests and four README descriptions. Create local atomic commits.
UI impact: none. Gitignore impact: none. One parent writer uses the direct route and one verification sequence.
No push, installation, release, deployment, branch deletion or external configuration is authorized.

New contracts use `main-preview/1`, with both ordinary and hotfix work based on frozen remote `main`.
Harness 0.63 introduces this contract without changing PLAN-v6 or RUN-v11 fields.
Retain pinned `dual-branch/1` and older candidate contracts, including their correction lineage.
The `development` stage remains the non-production target vocabulary; it does not require a Git branch.

## Acceptance And Dependencies

| Requirement / TEST ID | Expected outcome | Verification / environment | Dependency |
| --- | --- | --- | --- |
| PREVIEW-01 | New runs require main-preview/1, frozen main ancestry and matching architecture | Branch, manifest, plan and new-run tests | Source 0.63 pin |
| PREVIEW-02 | Legacy pins retain their source policy; malformed or mismatched pins fail | Negative protocol and archive tests | None |
| PREVIEW-03 | Candidate Preview replaces development landing; main and production retain exact-version gates | Contract, deployment and product-package tests | None |
| PREVIEW-04 | Cloudflare chooses native Previews when supported and records isolated resources and limitations | Source contract and deployment tests | Wrangler 4.135.0+ in consuming projects |
| PREVIEW-05 | Live instructions, templates, workflow and four READMEs agree | Source checks and independent fixed-SHA review | None |

## Document Impact

Branch policy and release-source owners, deployment and Product Definition references, templates, four READMEs and numbered workflow change together.
Historical Epics, release notes, archived RUNs and owner approvals remain intact.
Source AGENTS intentionally keeps its source-only Git and deployment exceptions.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| First observation and accepted Preview route | Repository `product-delivery-harness`; baseline/observed HEAD `8a47dab3`; owner-selected branch `codex/cloudflare-preview-flow` | Working-tree implementation; EXP-BRANCH, EXP-PREVIEW and ARCH-PREVIEW read-only assignments | Verification and fixed-candidate review pending |
| Implement version-pinned main/Preview routing | PREVIEW-01–05; validators, templates, CI, live workflow and four READMEs; UI none | Working-tree candidate based on `8a47dab3`; detailed evidence in the linked result below | 388 affected Harness/CI tests, 300 Product Definition tests, new Preview archive test, four legacy dual-branch archive tests and archive-move smoke passed |
| Retain failed diagnostics and recovery | New strict version rules exposed five fixtures without version pins; two follow-up fixture/CI assertions also needed repair | External logs retain the original failures. A combined supplemental run reached its 420-second deadline and its owned process tree exited | Completed focused groups replace no release obligation; full release matrix remains pending |
| Repair retained dual-branch instructions after independent review | One P2 finding across five locations in operating rules, lifecycle, orchestration and GOAL checklist | Candidate `5de8434c` received security PASS but holistic changes requested; follow-up working-tree repair retains historical pins | Add focused contract checks and obtain fresh review on the repaired commit; final outcome remains in the linked receipt |

## Results And Remaining Work

Installed Harness version: 0.62.3. Loaded bundle identity is unobserved.
Document inventory reports first-observation review and unknown loaded identity; neither is a verification PASS.
Formal release, installation and migration of existing consumer repositories are outside this task.

The exact candidate, independent review and final outcome are authoritative in [preview-flow-result.md](C:/Users/mps19/.codex/visualizations/2026/10/15/01a13d9d-64d7-7fa2-97fe-73d39b523f32/preview-flow-result.md).
The linked receipt is written after the fixed candidate review; this checkpoint does not predeclare its result.
