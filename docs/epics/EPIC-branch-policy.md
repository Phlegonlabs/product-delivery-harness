# EPIC-branch-policy: dual-branch managed release policy

Status: complete

## Problem And Baseline

The 0.58 flow required every initial delivery and enhancement to start from remote `main` and refused `development` everywhere. The approved workflow needs ordinary releases to build from a frozen `development` base and hotfixes from `main`, while keeping both protected branches permanent and preserving local-only RUNs.

Baseline: repository checkout at detached `bdae1d82`, Harness 0.58.0, with no branch-policy field or dual-branch architecture marker.

## Accepted Scope

The approved MOD-C task authorizes source branch-policy implementation, affected Product Definition release contracts, current references/templates, four README descriptive sections, and this Epic. It authorizes local atomic commits and parent integration; pushes, installation, deletion, protected-branch mutation, frontend UI portions, root AGENTS, version bump, and final release suite are out of scope.

The accepted interface is:

- `PLAN.branch_policy` contains exactly protocol `dual-branch/1`, kind `ordinary|hotfix`, canonical `refs/remotes/<remote>/development` or `/main`, and the frozen full base SHA.
- 0.59+ current joins require the policy, the active architecture marker, and local base ancestry. Pre-0.59 pins keep old semantics; malformed pins grant nothing.
- Wave re-anchoring advances `integration` state only. The PLAN base stays frozen.
- Exact-A corrections retain their receipt-bound continuation exception but still carry policy/marker and strong archive provenance.
- Archive receipt/anchor/publication formats, `expected_main`, and `main_ref` remain unchanged.
- `main`, ordinary `development`, and the observed default branch are refused for cleanup, local and remote spellings included.

## Acceptance And Dependencies

| Requirement / TEST ID | Expected outcome | Verification / environment | Dependency |
| --- | --- | --- | --- |
| HARNESS-BRANCH-001 | Valid and malformed policy shapes, base refs, and old/malformed pins are distinguished | `test_branch_policy.py` | none |
| HARNESS-BRANCH-002 | Current joins use the canonical active parser and reject ambiguous/unknown markers | `test_validate_harness_plan.py`, `test_product_package_checker.py` | none |
| HARNESS-BRANCH-003 | Current RUN/archive validation fails without the policy even before a repo-root authority join | `test_harness_manifest.py` and archive/publisher validators | parent 0.59 version bump |
| HARNESS-BRANCH-004 | Local, remote, and observed-default protected targets cannot pass delete authorization | `test_lifecycle_cleanup_targets.py` | none |
| HARNESS-BRANCH-005 | New RUN/template and current docs describe the same flow | `test_new_run.py`, `test_skill_contract.py` | parent integration |
| HARNESS-JOIN-001 | `design-system/4` uses the canonical compiler checker for registry and pair validation | `test_contract_source_binding.py` | frontend digest repair integration |
| HARNESS-JOIN-002 | A fresh enhancement label cannot retain `ui-design/2`; a frozen validated maintenance record can | `test_contract_source_binding.py` | frontend digest repair integration |
| HARNESS-GOLDEN-001 | The enabled golden flow consumes genuine UI3/DS4 evidence, a frozen dual-branch base, and current approval hashes | `test_golden_path.py` with `HARNESS_GOLDEN_PATH=1` | frontend digest repair integration |
| HARNESS-GOLDEN-002 | The lifecycle golden flow uses the same current package and verifies DS4 pair staleness recovery | `test_lifecycle_golden_path.py` | frontend digest repair integration |
| HARNESS-PACKET-001 | Design authoring packet ordering follows the current wording without weakening either pinned skill or binding checks | `test_cross_skill_pipeline.py::test_design_authoring_worker_packet_requires_both_pinned_skills` | none |
| HARNESS-RENDER-001 | Tasks-view generation uses current dual-branch packaging while retaining renderer safety behaviors | `test_render_tasks_view.py` | none |

## Document Impact

| Changed source / requirement | Affected live artifact | Required recheck |
| --- | --- | --- |
| Dual-branch release policy | Harness PLAN/RUN contracts and templates | focused/final Harness suites |
| Architecture marker and protocol | Product Definition output, interview, agent graph, playbook | Product parser and contract tests |
| Protected landing/promotion flow | Promotion, deployment, execution-state, worktree, operating rules, READMEs | final docs/contract suite |

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Add dual-branch architecture parser | `release_targets.py`, marker protocol, and focused regression | `439ba7704980890a0922a4f14977f761ec08d45e` | 80 product-package tests passed |
| Add PLAN policy and 0.59 join | New helper, exact shape, frozen-base ancestry, strict marker join, and manifest validation | `1970e2351af9bf7bc65646bd7e122312f52a34fc` | 4 policy and 117 manifest tests passed |
| Harden joins, markers, types, corrections, and cleanup | Private parser registration, exact marker counts, old-pin mismatch, correction provenance, `validate_run` policy check, remote protected cleanup targets | `56d035f2323b1ec3ed0deae177f688b6692b87b1` | 6 policy, 32 strict PLAN, 11 new-run, 117 manifest, 80 product tests passed |
| Align live templates and contract tests | PLAN, Goal, Mission Runbook, Project Agents, Deployment, and contract assertions | `d96a84940541e9a92e074addcab6c5ae76209058` | 11 new-run, 4 project-template, 60 Harness contract tests passed |
| Update canonical live flow docs and READMEs | Branch-promotion, deployment, execution-state, worktree, operating rules, Product Definition sources, agent graph, four current README bullets | `ff3d72a3ae07f09515dc76dbd6ae48523bd29cd9` | 97 Product Definition contract tests and 60 Harness contract tests passed |
| Reject full remote protected delete targets | Fixed `main`, `development`, observed-default, and `refs/remotes/<remote>/<name>` cleanup guard without assuming origin | `42187d135defb405016aa3db2387b559c51ee46a` | 9 lifecycle-cleanup tests passed; archive suite 48 passed |
| Preserve observed-default remote protection | Protect full remote refs for any remote while documenting that unqualified slash names remain ordinary branches | `95c5847a6692c0ff218761850d99b507e8fe4c1c` | 10 lifecycle-cleanup tests passed |
| Define hotfix forward integration | Require separately authorized no-force integration A→current development, retain unrelated work, prove A ancestry, and verify new SHA T with its own gates | `ddd618de6591558515b1b90351c6814bd95542ea` | 60 Harness and 97 Product Definition contract tests plus docs weight passed |
| Dispatch DS4 through the canonical adapter | Add schema 4 to both Harness design-contract entry points; build a real branch-policy/UI3/DS4 fixture with base ancestry and exact empty findings | `6b2ad6139ea3e220df5d45720ada623370156073` | Focused module 6 PASS in 5.04 seconds; pyflakes passed |
| Restrict retained legacy UI | Remove the enhancement-label shortcut; require validated frozen maintenance evidence and reject fresh 0.59 enhancement UI2 | `c9da55de4e684a9f21d2de5810118f420e44335e` | Focused module 7 PASS in 6.44 seconds; pyflakes and whitespace checks passed |
| Upgrade golden packages to the current release contract | Replace legacy UI2/schema-3 golden construction with the shared genuine UI3/DS4 branch-policy fixture; bind traces to the real DS rule and retain plan-only fail-closed behavior | This atomic golden repair commit | Enabled golden and lifecycle golden each 1 PASS under a 300-second deadline; contract-source 7 PASS |
| Align packet route assertion with current wording | Commit `193fa149` intentionally changed “authoring or repair” to “authoring/repair”; update the stale exact test phrase while retaining binding, pinned-skill, actual-writer, no-grant and compilation-order checks | This atomic packet-test alignment commit | Focused packet test 1 PASS in 0.002 seconds; pyflakes and whitespace checks passed |
| Package tasks-view fixture for current joins | Add the active dual-branch marker and protected development source policy to the renderer fixture architecture; the PLAN template already supplied branch policy | This atomic renderer-fixture commit | Full focused module 13 PASS in 4.27 seconds under a 180-second deadline; pyflakes and whitespace checks passed |

## Results And Remaining Work

Earlier branch-policy and MOD-JOIN commits are integrated. The current golden repair is contained in the atomic commit that adds the HARNESS-GOLDEN rows.

The bounded archive suite passed 48 tests. A 300-second bounded run of the publisher suite timed out and was stopped; it needs the parent's longer final-suite budget. Remaining: parent integration, frontend overlap reconciliation, independent exact-head review, 0.59 final suite, release documentation/version-history ownership, and any final security review. No push, install, branch deletion, worktree removal, or protected-branch mutation was performed. Root AGENTS remains owner-owned for the parent's final main-only migration; this checkout observed VERSION 0.59.0 and did not edit it.

- 2026-10-03 consolidation repair, baseline `108ec8014b808ff40432ed0adf49dcefe76104ce` on `codex/harness-flow-modernization`: independent correctness review found that plan-only validation treated absent RUN as an old pin. Validate an explicit PLAN branch policy and architecture marker together; retain actual historical RUN rules and defer candidate ancestry until RUN exists. Update the golden-path expectation, branch-policy matrix, promotion reference and all four README descriptions. UI impact none. The new regression failed before the fix; working-tree checks then passed branch policy 9/9 and the full golden path 1/1, including missing marker/policy, invalid base, duplicate/unknown marker and old-pin rejection. Whitespace passed. Logs and the scoped diff/commit receipt are under `pdh-worktree-merge-20261003-eb6k85jg`. Fresh final-SHA CI and follow-up review remain pending; this check grants no execution or protected landing.
