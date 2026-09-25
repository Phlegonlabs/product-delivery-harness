# Reference Flow Integration

Status: local implementation verified; release candidate pending exact-SHA CI and promotion
Workflow: bounded direct enhancement
UI impact: none

## Problem And Baseline

The skill bundle has stage-specific stack and design guidance, but researched cross-domain comparison material lives only in checkout-external drafts. Agents could miss a coherent option or accidentally treat research content as a second mandatory workflow.

This source repository has no product PRD or architecture package. The baseline is the clean candidate branch checkout at `ca3b5a4cad57cb2065a57ca46ff2014c279d1a32` on `codex/reference-flow-integration`. The accepted research baseline is draft r1.0, checked 2026-09-25.

## Accepted Scope

Ship one optional, maintained reference catalog with an English index and routing rules while retaining the researched Traditional Chinese domain content. Add a shared needs-first selection rule and concise conditional pointers in all seven canonical skills. Update all four README descriptive sections and index this Epic.

The scope excludes external evidence and workspace handoff files, draft README/skill-fit proposals as authority, absolute local paths, product PRDs, new runtime/subagent/install/network/deployment authority, forced vendors, and any change to approval, capability, native-evidence, exact-SHA, security, SEO, or existing GSAP routes. The owner's release follow-up adds the required 0.54.4 version bump.

The owner authorized this branch, GLM implementation, and then requested commit, push, merge, and local skills update. Exact-candidate promotion follows the branch-promotion contract. Deletion, moves, unrelated changes, and cleanup remain outside scope. This record preserves those instructions; it grants no actions itself.

## Acceptance And Dependencies

| Requirement | Expected outcome | Verification / environment | Dependency |
| --- | --- | --- | --- |
| RLIB-1 | The catalog has all 19 domains plus scenario, maintenance, and sources files; internal links resolve installation-portably. | `test_reference_library.py` from repository root | Draft r1.0, checked 2026-09-25 |
| RLIB-2 | The shared rule is needs-first, optional, keeps existing decisions, permits coherent comparison without forced vendors, records decisions in existing documents, and bounds official-source refresh. | Focused test and semantic review | None |
| RLIB-3 | Each canonical skill has one conditional pointer at its relevant stage and preserves existing gates and routes. | Focused test and semantic review | RLIB-2 |
| RLIB-4 | Four language-parallel README descriptions describe the catalog and required 0.54.4 release. | Semantic review and `git diff --check` | RLIB-1 |
| RLIB-5 | The bounded Epic and index are current; no product PRD is invented. | Semantic review | RLIB-1 |
| RLIB-6 | Focused tests prove coverage, relative link resolution, and that the catalog remains reference-only. | `python -m unittest ...test_reference_library.py` | RLIB-1–RLIB-5 |

## Document Impact

| Changed source | Affected live artifact | Required recheck |
| --- | --- | --- |
| Owner request and draft r1.0 | `skills/delivery-harness/references/option-library/*`, shared selection rule | Catalog/link focused tests |
| Owner request and seven skill contracts | Conditional pointers in each canonical `SKILL.md` | Skill specification and semantic review |
| README documentation-of-record rule | All four root READMEs | Cross-language semantic review |
| Repository change checkpoint rule | This Epic and `docs/DOCUMENTS.md` | Handoff audit |

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Integrate researched optional reference library | Add maintained comparison material and stage-local routing without creating a second workflow | Working tree on exact baseline; 22 imported catalog files, selection rule, English catalog index, seven skill pointers, four READMEs, Epic/index | Implementation added. Focused checks passed: skill specification, nine catalog tests, and `git diff --check`. The bonus docs-weight run was blocked by this sandbox's Git safe-directory mismatch; parent full verification remains pending |

## Results And Remaining Work

### Parent checkpoint, 2026-09-25

Repository: product-delivery-harness-design-flow-glm; branch: `codex/reference-flow-integration`; baseline and observed HEAD: `ca3b5a4cad57cb2065a57ca46ff2014c279d1a32`. Working-tree source fingerprint, excluding this Epic and index: `35ff9086f96d5287fd148daabb05b5da2e2c1401346ae5ad25540bff1582bb56`. GLM-5.3-Flash run `20260925-080646-9a7e1c8f7e9f4e1ca0b9132f2ced5307` finished successfully.

Parent review clarified adopted-context routing, installation-portable links, motion intake ownership, and optional runtime selection. Core entrypoint is 3599 words. Release metadata, lockfile, four README badges/history, runbook default, and version assertions now agree on 0.54.4. No UI runtime or product approval changed.

The first Harness run executed 1234 tests with 10 failures, 2 errors, and 16 skips: installer checks rejected untracked source files, and one core word-budget assertion failed. These results remain historical failures. After staging the source and shortening the entrypoint, all 15 installer rechecks and all 60 skill-contract tests passed. Other completed suites: Product Definition 235; UI 282 with required Chromium browser checks; compiler 99 with 3 skips; activation 56; SEO 17; golden path 1. Final specification, pyflakes, docs weight, nine reference tests, golden path, and staged/unstaged whitespace checks passed. A portable-layout check resolved 116 references. Full clean exact-candidate CI remains required before promotion; focused rechecks do not claim a fresh full local suite PASS.

Logs and final evidence are checkout-external under the task's temporary verification directories. No generated artifact class was introduced: node_modules, Python caches, and logs remain ignored; source, lockfile, and fixtures remain tracked. Original dirty checkout is untouched.

Document audit: no current product PRD or architecture exists in this source repository. The seven canonical entrypoints and four READMEs agree. Installed shared template observed at 0.54.3, SHA-256 `86cc1595619c097f79ef8e4234367e9ba8b056a9635bc24d372bcf417b024aa6`; shared AGENTS rules are current by meaning, with stricter source-repository release requirements retained. Loaded skill identity remains unobserved. Document-sync first-observation findings require semantic review and are not an approval or validation PASS.

Local implementation is complete. The release handoff and PR retain exact committed candidate/main identities, fresh security review, full CI, tag, and installer result. Those external results must be observed before claiming release completion; this pre-commit record makes no publication or installation claim.
