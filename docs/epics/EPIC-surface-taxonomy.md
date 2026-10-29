# Surface Taxonomy And The Five-Skill Bundle

Status: candidate verified locally; independent review and publication pending
Design workflow: enhancement
UI impact: none (skill rules for consumer products, READMEs and documentation; no product UI in this repository).

## Problem And Baseline

After 0.72.0 the suite only knew one kind of project: a product with a PRD and one of three tracks (web, app, agent). The owner's actual projects are combinations of surfaces: a web app with an iOS app and an Instagram account, an MCP server with a README, a content channel with no code. Three skills carried machinery nobody used (a 2,000-line activation ledger that no consumer ever took past `pending`, a saved SEO review with zero consumers, a 146-line security skill that duplicated the harness gate), and the growth review could only read websites.

Baseline: `e1cd13a4` (0.72.0 on `main`). Branch `feat/surface-taxonomy`, clean at start.

## Accepted Scope

Owner decisions in chat on 2026-10-29:

- Add every surface the owner runs. One [Surface Catalog](../../skills/delivery-harness/references/surface-catalog.md) lists 22 build surface classes (adding `mcp_server`, `skill_or_plugin`, `library_or_sdk`, `messaging_bot`, `marketplace_app`, `assistant_listing`, `container_or_self_hosted`, `internal_service`) and five presence kinds (`social`, `video_channel`, `newsletter`, `community`, `docs_site`) written as `platform:handle` in the PRD Discovery Surfaces. The Shape row gains `tool` and `content` tracks; the Launch Window gains a Destination column; adding a surface later is one catalog row plus one vocabulary entry.
- Collapse `product-activation` into delivery-harness: External Console Setup rows are the actions, a Measurement Sources table in `docs/DEPLOYMENT.md` replaces `docs/ACTIVATION.md`, the setup catalog becomes `references/external-setup.md` by surface class, and the ACT digest machine, `check_activation.py` and the staging protocol are gone.
- Replace `seo-growth-review` with `growth-review`: one lens per surface, sources resolved from Measurement Sources, then stack decisions, then platform defaults (App Store Connect, Play Console, registries, platform insights; RevenueCat and the recorded auth provider never assumed). Inline output only; the saved review checker and template are retired.
- Fold `code-security-review` into `references/security-review.md`; the `code_security_verification` binding slot now pins that file's digest.
- Merge `gtm-content` into `go-to-market`; the Launch Reach Plan folds into the PRD Launch Window.
- Mechanical cleanups: dead helpers and the duplicate validator CLIs, the unused GOAL, EVAL_RUNBOOK and REFINEMENT_BACKLOG templates, and a DOCUMENTS template that lists stable documents instead of mirroring the file tree.

Deferred to later releases by the owner: the managed PLAN/RUN route, the legacy wireframe route, the option library, the zh-TW review copies, the per-skill prose-pin tests, the design-contract duplicate, and the RUN.md attestation bloat in dilution-radar.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| ST-1 | `release_targets.py` accepts the 22 surface classes and gates `Public discoverability: yes` on the discoverable set; `check_product_package.py` accepts five tracks, ten discovery kinds with the `platform:handle` form, the `growth` owner stage and the six-column Launch Window | product-definition-builder suite |
| ST-2 | `check_deployment.py` validates the optional Measurement Sources table and `--require-measurement-sources`; the lifecycle golden path carries one release through UI, Harness and the deployment record | `test_measurement_sources.py`, `test_lifecycle_golden_path.py` |
| ST-3 | The outcome review reads verified `MS-*` rows from `docs/DEPLOYMENT.md`; Product Definition seeds Measurement Sources rows instead of an activation record | `test_outcome_review.py` |
| ST-4 | `check_skill_bindings.py` pins `security-review.md` for the `code_security_verification` slot and reports a clear re-point finding for the old skill name | `test_skill_bindings.py` |
| ST-5 | The installer, contract digest, CI and shard runner list five skills; the four READMEs describe the same 0.73.0 meaning | `test_install_script.py`, `test_skill_contract.py`, `test_readme_structure.py` |

## Document Impact

Parent-owned: the two catalogs, the growth-review skill prose, the PRD contract prose, the harness skill-contract tests, the installer and release surfaces, this Epic and `docs/DOCUMENTS.md`. Worker-owned packages: W1 (surface classes and tracks in the checkers), W2a (deployment contract and template prose), W2b (Measurement Sources validation), W2c (outcome review and Product Definition seeding), W3 (go-to-market merge), W4 (dead code and validator CLI), W5 (security fold), W7 (templates and DOCUMENTS).

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Surface catalog, five-track Shape, external setup catalog, growth-review skill | Parent (Claude Fable 5.1) | `cae96f8e`, `4de089a6`, `df73bf72` | pdb contract OK, check_skill_spec OK |
| W1 surface classes and tracks in checkers | GLM-5.3 Flash worker; turn limit hit, tests committed by parent | `62d0c1bb`..`1a7e3582`, merged `43135ce5` | pdb suite 286 OK, deployment record and platform contract OK |
| W3 gtm-content into go-to-market | GLM-5.3 Flash worker | `18de3674`..`62ec140b`, merged `6bab9f79` | check_skill_spec OK |
| W5 security fold | GLM-5.3 Flash worker; turn limit hit, last three references and commit by parent | `f7932d38`, merged `ebfbb6aa` | skill bindings 9, packet and security suites OK |
| W7 templates and DOCUMENTS | GLM-5.3 Flash worker | `ad52db68`, `aebfe909`, merged `6f00385b` | document sync 28 OK |
| W4 dead code and shared validator CLI | GLM-5.3 Flash worker; turn limit hit after commits | `6d6625f1`, `128dc750`, merged `c8fc28d1` | validator, platform contract and verifier runtime suites OK |
| W2a activation collapse prose | GLM-5.3 Flash worker | `74530c74`..`0b828117`, merged `ce2a43e6` | delivery contract 65 OK after parent pin reconciliation `db9be347` |
| W2b Measurement Sources validation | GLM-5.3 Flash worker | `9144c174`, `c4bc49c6`, merged `3e86aec6` | measurement sources 14, deployment record 37 OK |
| Five-skill surfaces, READMEs, version 0.73.0, golden path | Parent | `6db9f5de`, `9ed13390`, `03d518b5`, `e09e3cd5`, `6bd742b7` | readme structure OK, golden path 1 OK |
| W2c outcome review reads Measurement Sources, seeding replaces the activation record | GLM-5.3 Flash worker | `797f60e7`..`653f5748`, merged `9beebe89` | pdb suite 274 OK in the worker tree |
| Retire `skills/product-activation`, last record mentions, governance and route pins | Parent | `91946ae0`, `a8ab0b29` | pdb suite 287 OK, delivery contract 65 OK, governance routes 7 OK, cli utf8 3 OK |

## Verification

Required Verification matrix on `a8ab0b29` (working tree identical to that commit; this Epic and `docs/DOCUMENTS.md` are the only later change), logs under `task/matrix-073/` (untracked scratch): `check_skill_spec.py` exit 0; pyflakes over the four remaining script trees clean; `docs_weight.py` grand total 193,875 → 191,363 words against v0.72.0; delivery-harness `ci_test_shards.py run --suite harness --workers 8` 107 modules passed, 0 failed, 539 s wall; `HARNESS_GOLDEN_PATH=1 test_golden_path.py` 1 OK; product-definition-builder 287 OK; ui-design-builder 356 OK (2 skipped); design-system-compiler 214 OK (2 skipped); `git diff --check` exit 0. CI has not run; the branch is local only.

Independent review: not yet run. The owner's protected GPT reviewer route is the next step before any publication.

## Remaining Work

- Consumer adoption 0.73.0: re-point the `code_security_verification` slot, move each `docs/ACTIVATION.md` Measurement Sources rows into `docs/DEPLOYMENT.md`, rename `seo-growth-review` bindings to `growth-review`, add presence surfaces to each PRD Growth Contract.
- Publication: PR `feat/surface-taxonomy` to `main`, CI on the exact candidate, tag `v0.73.0`, installer run. Nothing here authorizes a push, PR or installation.
