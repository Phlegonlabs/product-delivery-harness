# Generate, verify and correct with platform ordering

Status: complete
UI impact: none

## Problem And Baseline

Released source `aab39d0545a95b3ae2b972cf7843dcf8eadb7cf4` already supports
bounded task, mission and integration correction. Feature completion and approved
Web/iOS order are not explicitly joined to executable acceptance gates.

## Accepted Scope

On 2026-10-04 the owner approved the proposed Generate -> Verify -> Correct
method and requested multi-agent implementation. Retain one writer per checkout.
Use direct source maintenance with serial writers and one integration verification
sequence. Do not create consumer product documents or PLAN/RUN for this task.

Define measurable loops across stages and execution levels. Link feature outcomes
to existing final gates. Put owner-selected platform order in canonical architecture
and check its frozen join to PLAN dependencies. Keep both platforms' interfaces
and design obligations upstream. Separate historical platform handoff evidence from
fresh unified-candidate regression. Preserve retry budgets and human decisions.

## Acceptance And Dependencies

| Contract | Expected result | Verification |
| --- | --- | --- |
| Bounded loops | Clear target, scope, verifier, feedback and stopping condition; success stops the loop | Skill/spec checks and semantic review |
| Feature acceptance | Contributing missions precede declared acceptance gates; current-head results required | Positive and negative PLAN/closeout tests |
| Platform sequence | Approved surface order and required TEST IDs join to completion-mission verification and strict dependencies | Product parser, frozen-source join and graph regressions |
| Compatibility | Unmarked historical packages keep their contracts; marked malformed inputs fail closed | Legacy, duplicate, spoofed-marker and stale-source tests |
| Integration | No scheduler, new state store, zero-bug claim or unrelated policy change | Full applicable local suite and independent source/security review |

## Document Impact

Update the applicable canonical skills, references, templates and all four README
descriptions in the same logical changes. Keep consumer release branch policy.
No product UI or visual evidence applies. Existing ignore patterns cover Python
cache and dependencies; task logs and receipts stay outside Git.

## Implementation Design

Use the approved `platform-delivery/1` section in canonical architecture. It records
whole-platform order, stable release surfaces, required TEST IDs, completion signals,
shared surfaces and interface ARCH IDs. Keep existing Product approval authority.
Absent markers retain legacy behavior; present malformed markers fail closed.
New authoring requires an explicit protocol or justified single-platform exemption.

PLAN v6 may declare `platform_delivery` stage mappings with mission IDs, a completion
mission ID and that mission's integration verifier IDs. Use the last substantive
mission as the stage handoff. Every contributing mission precedes it through
pass-only dependencies. It precedes every next-platform mission the same way.
Mission integration retains PASS at its actual integrated SHA. This is historical
stage-start evidence, not proof of current platform health.

Verifier `acceptance_test_ids` joins commands to required upstream tests. Feature
Must traces may declare `acceptance_gate_ids` referencing existing final gates.
Every contributing mission precedes those gates through pass-only dependencies.
The final gates cover both platforms at the current unified SHA. Existing candidate
invalidation and retry budgets remain unchanged. Route-only reachability is not
a completion dependency. No new scheduler or RUN state is needed.

Serialize Product-contract, Harness-contract and cross-stage guidance writers.
Each writer owns its files, tests and same-outcome README descriptions. The parent
owns the index, integration checkpoint and final independent source/security review.

## Change Log

| Observation | Scope and evidence | Verification and remaining work |
| --- | --- | --- |
| 2026-10-04 entry | Clean baseline above; branch codex/loop-engineering. Independent loop and platform explorers plus read-only architecture assignment dispatched. | Design underway; no implementation verified. Installed skill 0.61.0 observed previously; loaded identity remains unknown. |
| 2026-10-04 P1 | Product parser `platform_delivery.py`, package checker opt-in integration, focused regressions, Product guidance, and four README behavior notes on branch `codex/loop-engineering`, based on `74d401a6a13d8ecb2f99f4417ffdb87fec8372b6` and the approved architecture contract. | Working-tree verification: 13 `test_platform_delivery.py` tests PASS; 80 `test_product_package_checker.py` tests PASS; `pyflakes`, `docs_weight.py`, and `git diff --check` PASS. Logs stay under the task-owned external check directory. Commit pending in this change; PLAN sequence mapping remains for the Harness writer. |
| 2026-10-04 10:13 -07:00 H1 | Branch codex/loop-engineering; baseline 92dd8756. Working-tree H1 adds `platform_delivery_contract.py`, PLAN/runtime/packet joins, standalone planned `PRD-*` feature gates, focused tests and shared fixture support, canonical PRD TEST authority in `delivery_acceptance_io.py`, Harness contracts/templates and four README descriptions. Product files remain at 92dd8756. The 659-line module is kept together: it owns one fail-closed PLAN-to-architecture and acceptance join; shape, dependency paths, verifier annotations and gates share the same canonical decision. | Passed at this working-tree scope: platform contract 28; manifest 117; verifier runtime 20 (2 Windows skips); source join 32; review packet 9; selector 64; graph 45; closeout 8; transition 15 (1 skip); delivery acceptance 43; eval contract 21 (1 skip); skill contract 60; scoped pyflakes. `check_skill_spec.py`, `docs_weight.py` and final diff checks run before commit. Remaining: parent post-H1 Product parser repairs, G1 guidance/Windows inventory, full fixed-candidate validation and independent review. |
| 2026-10-04 P1 repair | Baseline `da8a916d75b567b2b5a5048b6979b8cb7559210f` was clean. Product repair changes only `platform_delivery.py`, `test_platform_delivery.py`, and this Epic row. Active protocol markers are now counted globally and must resolve to exactly one marker inside the canonical section. Stage IDs reuse Release Targets' `KEBAB_RE`. Exported parser and checker APIs are unchanged. The 518-line module stays together because it owns one responsibility: fail-closed parsing and normalization of the `platform-delivery/1` contract; splitting helpers would create an unused boundary without a second consumer. | Working-tree verification: 14 `test_platform_delivery.py` tests PASS; 80 `test_product_package_checker.py` tests PASS; scoped `pyflakes`, `check_skill_spec.py`, `docs_weight.py`, and `git diff --check` PASS. Final log: `p1-repair-final-9cea5246d9c04349ba0d7b4356625fb6.log` under the task-owned external check directory. Full fixed-candidate suite and independent review remain pending. |
| 2026-10-04 P1 review repair | Baseline `594266c3c3c658c42eab9509e26ab1fdcf99f76f`. Review hardening changes only the Product parser, its focused tests, and this row. The duplicate-marker fixture now places its second active marker in an explicit `## Notes` section, so it independently proves global placement instead of relying on the fixture's trailing Observability section. Stage validation restores the prior meaningful/placeholder check before the lowercase kebab check and asserts rejection of the covered `todo` stage. | Working-tree verification: 14 `test_platform_delivery.py` tests PASS; 80 `test_product_package_checker.py` tests PASS; scoped `pyflakes`, `check_skill_spec.py`, `docs_weight.py`, and `git diff --check` PASS. Log: `p1-review-repair-35a2d155861740b3af566fd26707849e.log`; the same suite is rerun after this row. Full fixed-candidate suite and independent review remain pending. |
| 2026-10-04 G1 guidance and CI inventory | Baseline `507544862ea4a943da9910acfaa28a8ebe662a9b` was clean. G1 adds the shared `gen-verify-correct.md`, one pointer in each of the seven SKILL entrypoints, a Traditional Chinese workflow section, one reconciled flow overview in each README, and the Epic/index update. It preserves the committed P1/H1 platform and feature paragraphs. CI adds `test_platform_delivery_contract.py` to `WINDOWS_NATIVE_FILES` and raises the planner fixture expectation to 13 files; it uses existing `--allow-unmeasured` timing policy and no workflow mutation. The first skill-contract run found the Harness word cap at 3,621; a concise same-scope pointer repair and clarified broaden rule produced the passing final bytes. | Final working-candidate verification: `check_skill_spec.py` exit 0; `docs_weight.py` exit 0; `test_skill_contract.py` 60 tests PASS; `test_ci_test_shards.py` 13 tests PASS; `test_ci_candidate_gate.py` 12 tests PASS; `git diff --check` exit 0. Captured PID and 120-second deadline logs: `summary.json` under `g1-final-bookkeeping` in the task visualization directory. The parent-owned final unified-check and review authority is [loop-engineering-result.md](C:/Users/mps19/.codex/visualizations/2026/10/04/01a106f3-1755-7b42-873e-dbd7ebc45feb/loop-engineering-result.md), written after fixed-SHA checks and review. Source remains unreleased; push, PR merge, tag, and install remain outside this task. |
| 2026-10-04 H1 repair | Baseline `da8af88c3b7be9403bb3546c38178176f31c0f19` was clean. Consolidated review found five defects: combined feature/platform rejection, strict legacy authority initialization, unmarked historical gate forcing, omitted UI stage ownership, and skipped semantic joins on run-None/legacy-pin paths. Commit `8b80e2a151473b320955e92ad357e2883a0fdaa0` adds one marker-aware exact-byte platform/source join for strict and materialized legacy paths, optional legacy feature metadata, mandatory mappings only for real `platform-delivery/1` contracts or explicit mappings, explicit UI-ID stage ownership, shared-fixture compatibility tests, drift and byte-reuse regressions, and marked-only README/reference wording. The 756-line platform module stays together because shape, architecture order, authority, dependencies, UI ownership, verifier annotations and acceptance gates form one fail-closed PLAN join; splitting would add a boundary without separate ownership. | Verification for commit `8b80e2a151473b320955e92ad357e2883a0fdaa0`: platform contract 39 PASS; Harness manifest 117 PASS; strict authority 22 PASS; validate-plan 32 PASS; source binding 8 PASS; design join 2 PASS; review packet 9 PASS; Harness v11 30 PASS; module size 3 PASS; README structure 5 PASS; skill contract 60 PASS. Scoped `py_compile`, `pyflakes`, `check_skill_spec.py`, `docs_weight.py`, and `git diff --check` PASS. A 300-second full Harness attempt reached unrelated eval tests without test failure and was stopped at its deadline; it is incomplete evidence, not PASS. Parent full matrix and fixed-SHA review remain next. |
| 2026-10-04 structural source-join repair | Baseline `c151b53b61f2f4d89c8a249742ec058bb07c98c5` was clean. Review marked it FIX_REQUIRED because declared architecture resolution depended on a mapping or Product approval marker, the shared join indexed unresolved PRD bytes, and malformed PLAN platform shapes could reach semantic traversal. Commit `45da03d64d8390b3c3da7134496ec311a825355e` materializes each declared architecture row once without the later approved-package fallback, requires unique declared architecture rows, passes optional resolution results safely, rejects adopted marker/mapping decisions that are not approved, requires readable frozen PRD and successful Required-Yes authority after adoption, and returns before platform traversal when shape validation fails. New public, legacy-pin, strict, CLI, malformed-source, marker-visibility, authority and shape tests cover the source-join family. | Verification for commit `45da03d64d8390b3c3da7134496ec311a825355e`: platform contract 49 PASS; Harness manifest 117 PASS; strict authority 22 PASS; validate-plan 32 PASS; source binding 8 PASS. Scoped `py_compile`, `pyflakes`, `check_skill_spec.py`, `docs_weight.py`, and `git diff --check` PASS. No new full Harness discovery was run; the parent owns fresh review and the complete matrix on the new final HEAD. |
| 2026-10-04 combined-fixture test repair | Baseline `c13156c87081b5bb8d10ee3e2b2884b29a08d0ea` was clean. Review found no remaining source/security blocker but marked the round FIX_REQUIRED because the combined positive test mutated a throwaway PLAN instead of the materialized PLAN, omitted its feature gate/dependency, selected error fragments instead of requiring an empty result, and used shared `ARCH-001` when canonical architecture adopted `ARCH-002`. Commit `7e4e7a469c5de262fc297b1a738d2433ab0f7304` repairs only that fixture and its negatives: it mutates and materializes one PLAN, aligns shared ARCH authority, proves the mutated PRD hash and revision authority, asserts the feature trace/gate/TEST/mapping/dependency fields, requires public `errors == []`, and adds isolated no-gate, no-TEST-coverage and no-dependency negatives with their exact diagnostics. | Verification for commit `7e4e7a469c5de262fc297b1a738d2433ab0f7304`: platform/public-route module 50 PASS; validate-plan 32 PASS; Harness manifest 117 PASS. Scoped `py_compile`, `pyflakes`, `check_skill_spec.py`, `docs_weight.py`, and `git diff --check` PASS. Unique 120-second-deadline logs are `test-repair-platform-*.log`, `test-repair-validate-plan-*.log`, and `test-repair-manifest-*.log`. No full Harness discovery was run; fresh independent review and the complete matrix remain parent-owned. |
| 2026-10-04 H3 security-fixture repair | Baseline `2cb6d5a78dd38e7b2e551db980f7bdde784d5d65` was clean. The parent's H3 matrix was not PASS at that exact SHA: Harness discovery ran 1,628 tests with 23 failures and 20 skips, Product discovery ran 297 tests with one failure, and its other PASS evidence stayed tied to that SHA. Twenty-two failures shared `carry_security_requirement`'s hard-coded `N-FINAL`/`final` assumption; the graph-revision case also missed TEST-003 and named `final` instead of the template's actual final gate. Commit `0d243f1d836b80d0cca7ce0f532408dab2140dad` derives the existing mission node, final gate, graph verifier node and security TEST binding from the PLAN and adds full `validate_plan` regressions for the regular fixture and shipped template. `manifest_fixtures.py` remains the shared route-valid fixture authority at 1,688 lines; the narrow helper repair stays there so existing callers do not gain a second fixture authority. | Complete verification for commit `0d243f1d`: new-run 11 PASS; task view 13 PASS; transition 15 PASS (1 skip); manifest 119 PASS; platform/feature 50 PASS; security join 14 PASS; validate-plan 32 PASS; strict authority 22 PASS; hybrid publication 2 PASS; archive module 40 PASS (1 skip, 372.830 seconds). The first two archive attempts stopped at 120 and 300 seconds and are retained only as incomplete evidence; captured parents and children exited. Scoped `py_compile`, `pyflakes`, `check_skill_spec.py`, and `git diff --check` PASS. The parent-owned fresh full Harness matrix remains next. |
| 2026-10-04 H3 Product interview repair | Baseline `1750453fcc3128f3720797a47748f0b705550723` was clean after the helper repair. H3's sole Product failure was `test_open_ended_interview_has_three_adaptive_segments`: Segment 3 had five prompts instead of the accepted maximum of four. Commit `67f4fc49587c81e10962fdad254eff644baf69ae` folds owner-selected platform order and required stage tests into the existing release/channel/availability prompt, keeps exactly three adaptive segments, and retains the concrete single-platform `not-required` rule in internal capture guidance. The four READMEs stay unchanged because their three-segment and platform-contract meanings remain accurate. | Verification on the exact working-tree content committed as `67f4fc49`: focused interview contract test PASS; full Product suite 297 PASS in 35.675 seconds; `check_skill_spec.py`, `docs_weight.py`, and `git diff --check` exit 0. The interrupted runner completed before cleanup inspection; no owned Product-discovery process remained. Retained logs are `t2-product-discover-20261004-130638.err.log` and `.out.log` in the external check directory. |
| 2026-10-04 13:12 -07:00 takeover checkpoint | Branch `codex/loop-engineering`; observed HEAD `67f4fc49587c81e10962fdad254eff644baf69ae`. GPT-6.1 Sol with Extra High reasoning assessed both repair diffs and the unfinished Epic evidence. The helper uses the PLAN's existing final gate and graph identities. The interview keeps four prompts and all platform capture obligations. No further source repair was needed; this change finishes the existing Epic record. | Fresh `check_skill_spec.py`, six-directory `pyflakes`, `docs_weight.py`, and `git diff --check` exit 0. Each check used a 120-second deadline; all recorded processes exited. Receipt: `sol-takeover-ba88fe5c13234b8298f41fdc7ab6c34e-summary.json` in the external check directory. No unit suite was repeated. Fresh independent review and one complete matrix remain parent-owned on the final bookkeeping HEAD. |
| 2026-10-05 08:07 UTC platform dependency repair | Baseline `77e917e3d6bdc9688b7bc98032faaa01f7c8c89d` was clean on `codex/loop-engineering`. Hosted CI `37280293645` at that baseline had all 20 jobs successful, but the review remained blocked at P2. This working-tree repair changes only `skills/delivery-harness/scripts/platform_delivery_contract.py`, its focused test, and this Epic row. `_dependency_adjacency` now retains every graph node, traverses the complete pass-only dependency subgraph, and `_reaches_mission` maps platform mission IDs back to graph node IDs. Contributor-to-completion and previous-completion-to-next-stage checks therefore accept verifier and approval intermediaries. Route segments still cannot satisfy the barrier, and direct mission chains remain compatible. The four READMEs need no edit because their existing wording already says dependency paths. Scoped document sync is `review_required` only for unobserved loaded identity, first observation, and known retired README pointers; no drift baseline exists in this source checkout. | The first platform rerun retained failures for both new contributor positives because its fixture omitted `N-M3`; the fixture was corrected. Final focused evidence: platform 52 PASS, graph 45 PASS, selector 64 PASS, `py_compile` and scoped `pyflakes` exit 0, `check_skill_spec.py` exit 0, `docs_weight.py` exit 0. Each unit and script check ran under the corrected external deadline supervisor with minimum 1,200 seconds; all recorded roots and children exited. Unique external log prefixes are `platform-dependency-platform-r2-h4b-8237a0be`, `platform-dependency-graph-h4b-3c9210d5`, `platform-dependency-selector-h4b-4ef39e71`, `platform-dependency-skill-spec-h4b-40da5a6e`, and `platform-dependency-docs-weight-h4b-e1ee8e45`; the failed first fixture run is `platform-dependency-platform-h4b-b3a041af`. Fresh full CI and fresh Sol review remain required on the new repair SHA. |
| 2026-10-05 08:45 UTC integrated platform barrier repair | Baseline `99806ff663904575b8613671123f4d710de20514` was clean after its fast-forward from the retained branch. Fresh Sol review marked main P1 FIX_REQUIRED with confidence 93: a platform dependency path could pass through a single-mission pre-integration runtime review after only `worker_passed`, affecting contributor-to-completion and stage-completion-to-next-stage paths. Hosted CI `37282843937` at that baseline had all 20 jobs successful, but it could not validate the review finding. This working-tree repair keeps selector and transition source unchanged. Platform traversal now excludes only the selector-matching dependency edge from a covered mission into its single-mission pre-integration runtime review. Deterministic verifiers, approvals, direct mission paths, guarded alternate paths, and integration-stage runtime reviews remain safe witnesses. The change adds direct and guarded handoff/contributor regressions, integration-review positives, and a realistic `worker_passed` plus pre-review PASS selector state with `M2.depends_on=[]`; public platform validation rejects that unsafe-only state. Release surfaces move to 0.62.1, the four 0.62.0 histories become unreleased preparation included in 0.62.1, and descriptive README text excludes pre-integration runtime reviews. No tag or installation exists. | The first platform run `platform-0621-platform-h4b-e023dc8c` exposed only under-specified runtime fixture state: `_logical_reasons` also returned execution/plan/status reasons. The corrected fixture sets a running, ready, authorized RUN. Final evidence: platform 56 PASS; graph 45 PASS; selector 64 PASS; transition 15 PASS (1 skip); skill contract 60 PASS; scoped compile and six-directory pyflakes exit 0; `check_skill_spec.py`, `docs_weight.py`, and `git diff --check` exit 0. Every check used the corrected external supervisor at minimum 1,200 seconds; roots and children exited. Check prefixes are `platform-0621-platform-r2-h4b-fccd8a46`, `platform-0621-graph-h4b-9a0ffc8b`, `platform-0621-selector-h4b-b1d65b68`, `platform-0621-transition-h4b-f2463833`, `platform-0621-contract-h4b-0bb94190`, `platform-0621-spec-h4b-67b21b91`, `platform-0621-pyflakes-h4b-64e3b621`, `platform-0621-docs-h4b-508b8122`, and `platform-0621-diff-h4b-112c1e63`. Fresh full CI, fresh Sol review, tag, and official installation remain required for 0.62.1; publication stays blocked until those exact-SHA receipts exist. |
| 2026-10-05 09:01 UTC malformed review metadata guard | Baseline `bf1d615d051cb833e2ca6333c3cc4408264e76f0` was clean. Fresh Sol review found P2 1: `_dependency_adjacency` called `len()` on unvalidated runtime-review `mission_ids`, so null or integer metadata crashed public current validation after graph-shape diagnostics; string or malformed-list metadata could otherwise establish a platform barrier. The repair changes only `platform_delivery_contract.py`, its focused test, and this row. `_unsafe_review_dependency` now treats missing, malformed, invalid-stage or invalid-list runtime-review metadata as non-proving before traversal. The fixture uses `allowed_outcomes=['pass','blocked']` and covers null, scalar, string, invalid-item and duplicate-list cases without entering the separate repair-route traversal issue. Public current, direct frozen/run-None, legacy-pin and CLI paths are covered. Structured graph diagnostics remain unchanged. | RED log `platform-0621-guard-red-h4b-fea9bc7a`: 5 failures and 1 error, including the exact `len()` `TypeError` for integer metadata. GREEN checks: platform 58 PASS (`platform-0621-guard-green-h4b-d84be3a4`), graph 45 PASS (`platform-0621-guard-graph-h4b-bbb5dd1c`), selector 64 PASS (`platform-0621-guard-selector-h4b-8dcbf031`), and `check_skill_spec.py` exit 0 (`platform-0621-guard-spec-h4b-418401bd`). Scoped compile and pyflakes exit 0; `git diff --check` exit 0 (`platform-0621-guard-diff-h4b-0cf8ed05`). All checks used the external supervisor with 1,200-second deadlines; roots and children exited. Feature-gate coverage, fresh CI and fresh Sol review remain pending. |
| 2026-10-05 09:04 UTC feature gate runtime review coverage | Baseline `51f57d9dd2b8cef9e74dfef2087a7912b8cdaeb1` was clean. This test-only commit closes P2 2: the filtered dependency helper lacked direct coverage for declared feature `acceptance_gate_ids`. New fixtures bind `REQ-001` to the `final` gate and replace M1's direct path with runtime-review paths. A single-mission pre-integration review shortcut fails; a deterministic gate before the same review passes; an integration-stage review passes; and an unmarked legacy direct path remains valid. The first fixture run `platform-0621-feature-tests-h4b-6889d083` retained the safe M1-to-M2 platform edge and therefore masked the M1 shortcut; the isolated run `platform-0621-feature-tests-r2-h4b-b06e9122` produced the exact expected M1 acceptance-gate failure. | Final focused checks: platform 62 PASS (`platform-0621-feature-tests-green-h4b-c7b4bf9e`), graph 45 PASS (`platform-0621-feature-graph-h4b-859f3d30`), selector 64 PASS (`platform-0621-feature-selector-h4b-2a0ec965`), transition 15 PASS with 1 skip (`platform-0621-feature-transition-h4b-26a0541c`), skill contract 60 PASS (`platform-0621-feature-contract-h4b-e8630a92`), `check_skill_spec.py` exit 0 (`platform-0621-feature-spec-h4b-f134e44d`), six-directory pyflakes exit 0 (`platform-0621-feature-pyflakes-h4b-fe294252`), `docs_weight.py` exit 0 (`platform-0621-feature-docs-h4b-08712652`), and `git diff --check` exit 0 (`platform-0621-feature-diff-h4b-6de9e4fd`). All used the external supervisor with 1,200-second deadlines; roots and children exited. Fresh full CI and fresh Sol review remain pending; no release readiness claim is made. |
| 2026-10-05 09:16 UTC malformed review stage guard | Baseline `3aba1aedb83639f6a933a1a2cd81be6ce01a11a9` was clean. Fresh Sol review found P2 3: platform and graph stage checks tested untyped metadata against a set before checking `str`, so JSON list or object stage values crashed current validation. This one malformed-stage concern changes `platform_delivery_contract.py`, the matching graph diagnostic check, focused tests, and this row. Both guards now require a string before membership. An omitted stage keeps the existing `preintegration` default. Tests cover null, scalar, list and object stage values for platform and feature barriers; structured graph diagnostics; combined public current validation; CLI exit/output; frozen/run-None and legacy-pin routes; and omitted-stage behavior. No broader validation cleanup was made. | RED platform log `platform-0621-stage-red-platform-h4b-a289e101`: 65 tests, 5 errors and 1 failure, including unhashable list/dict stage in platform and feature traversal. RED graph log `platform-0621-stage-red-graph-json-h4b-f265d76d`: 45 tests, 2 errors from the same unchecked graph membership. GREEN checks: platform 65 PASS (`platform-0621-stage-green-platform-r2-h4b-5fdb8a5b`), graph 45 PASS (`platform-0621-stage-green-graph-h4b-39f89cc4`), selector 64 PASS (`platform-0621-stage-selector-h4b-3f28f6d3`), transition 15 PASS with 1 skip (`platform-0621-stage-transition-h4b-565c62f5`), skill contract 60 PASS (`platform-0621-stage-contract-h4b-2ab08094`), `check_skill_spec.py` exit 0 (`platform-0621-stage-spec-h4b-ef205492`), six-directory pyflakes exit 0 (`platform-0621-stage-pyflakes-h4b-4ef07dab`), and `docs_weight.py` exit 0 (`platform-0621-stage-docs-h4b-13755f90`). Scoped compile and pyflakes also exit 0. Logs stay checkout-external; supervisors used 1,200-second deadlines and all roots and children exited. Fresh full CI and fresh Sol review remain required; focused PASS is not release readiness. |

## Results And Remaining Work

H1 is committed at `da8a916d75b567b2b5a5048b6979b8cb7559210f`. Its focused
platform, manifest, verifier-runtime, source-join, review, selector, graph,
closeout, transition, acceptance, eval, and skill-contract results remain the
recorded evidence for that exact change. P1 is committed at
`92dd875607fd00cde3ccf7581f671694e0097f9a`; its later review repairs are
committed at `594266c3c3c658c42eab9509e26ab1fdcf99f76f` and
`507544862ea4a943da9910acfaa28a8ebe662a9b`. Their Product parser and checker
results also remain exact-change evidence.

P1 adds the exported `parse_platform_delivery(architecture_text, prd_text, *, require=False)`
API. It returns a contract with `protocol`, `mode`, owner/status, ordered stages,
stage IDs/surfaces/test IDs, shared surfaces, and shared ARCH IDs, or `None` for
an absent active legacy section. The opt-in checker flag requires the contract and
approved status.

G1 adds cross-stage loop ownership, human/read-only boundaries, focused-first
verification with full required escalation, exact-candidate reuse rules, feature
and platform gate joins, and the Windows-native inventory entry for the new
Harness contract test. This row records focused checks run on the working
candidate before its atomic G1 commit. The external fixed-SHA report named in the
G1 row is the authority for final unified checks and review; until that report
exists, those final outcomes remain pending and do not invalidate the committed
focused results above.

The consolidated review repair is committed at
`8b80e2a151473b320955e92ad357e2883a0fdaa0`. Its focused results above belong to
that exact source content. The parent-owned full matrix and independent review
must run on the final observed HEAD after this record.

The structural source-join repair is committed at
`45da03d64d8390b3c3da7134496ec311a825355e`. It supersedes `c151b53b` as the
parent's review/matrix target without changing the historical evidence above.

The combined-fixture test repair is committed at
`7e4e7a469c5de262fc297b1a738d2433ab0f7304`. Review found `c13156c8` clean for
source and security; this test-only commit supersedes it as the target for the
parent's fresh review and complete matrix.

The H3 matrix at `2cb6d5a78dd38e7b2e551db980f7bdde784d5d65` was not PASS. Its
complete suites remain historical evidence for that SHA. The security-fixture
repair `0d243f1d836b80d0cca7ce0f532408dab2140dad` and Product interview repair
`67f4fc49587c81e10962fdad254eff644baf69ae` supersede it as the parent's fresh
full-matrix target. The external final report remains pending.

The takeover document check retained `review_required`: loaded identity is unknown,
the scoped inventory has no baseline, and README migration/history names need
semantic review. Those names describe retired skills, not current routing.
The observed installed bundle is `0.61.0`, with digest
`15f1f68a4f8675ed884cc8551549470af7463f2dcbbdb01f004e94a69677e778`.
Its installed template matches the canonical source template. Shared instructions
are current with the documented source-repository exceptions: source paths,
required reading, main-only Git flow, module size, and omitted consumer stages.
No AGENTS or ignore change was needed. Existing ignore rules cover Python caches
and dependencies; the new check logs remain outside this repository.

The source is unreleased. Push, PR merge, release tag, and local skill
installation remain outside this task.

## Release Follow-up

On 2026-10-05, the owner authorized commit, push, merge and installation.
The observed baseline is clean `8f827694a2ddbea9d83669cebde446cbe2c5c417`
on `codex/loop-engineering`. Released main remains `aab39d0545a95b3ae2b972cf7843dcf8eadb7cf4`.
The implementation candidate passed 11 local checks and independent Sol review.
Its external receipt retains 2,478 tests, 24 skips and no failures.

Prepare 0.62.0 by updating package metadata, VERSION, four README badges/history,
and the RUNBOOK default. The lockfile version follows package metadata.
This introduces no generated artifact or ignore change. UI impact is `none`.
The new fixed candidate requires complete verification and independent review.
Publish that exact work-branch SHA and merge its reviewed PR directly to main.
Preserve atomic history. Verify server tree equality and the new exact main SHA.
Tag verified main and use the official installer once at a quiescent boundary.
The release result belongs in the checkout-external `loop-engineering-release.md`
beside the implementation report. Publication, checks and installation remain
pending until their actual receipts exist.
