# EPIC-runtime-and-verification-reliability: Measured execution and dependable verification

Status: release_authorized_candidate

## Problem And Baseline

The 2026-09-23 review found optional browser checks in CI, incomplete task-file detection, a schema-4-only golden path, no producer for runtime metrics, repeated retirement warnings, and translation checks that could miss omitted sections. The four READMEs and canonical skill contracts define this bundle; this repository has no current product PRD.

Baseline: `baf7e22b05a7f2776ee8b205395204ff21cbdcb5` (0.52.0). The owner accepted all review items and requested GPT-6 Luna high subagents. The owner explicitly approved branch `codex/skills-reliability-0.53.0` and worktree `C:/Users/mps19/Documents/GitHub/product-delivery-harness-reliability`. The original checkout's untracked `scripts/design/hifi_model.py` remains outside this scope.

## Accepted Scope

Use the direct route with one active writer and sequential verification. Update canonical checkers, tests, CI, affected contracts, four READMEs and version pins for a local 0.53.0 candidate. UI impact: none; reviewer product behavior and approved product designs are unchanged. Synthetic fixtures may represent UI scenarios. Gitignore impact: ignore root `node_modules/` introduced by pinned browser test dependencies.

The owner authorized local implementation, Luna delegation and the exact branch/worktree above. This record grants no commit, push, promotion, tag, user-skill installation or cleanup authority. Preserve existing action and exact-source gates. Two repair rounds per root-cause family remain the default stopping boundary.

## Acceptance And Dependencies

Priority after review: first repair the real cross-skill failures and make browser CI mandatory; next tighten maintenance routing and translation coverage; then add runtime observations and reduce repeated reading and warning noise. Runtime measurements support later optimization decisions; this candidate does not claim a faster model or delivery cycle.

| Contract / test scope | Expected outcome | Verification | Dependency |
| --- | --- | --- | --- |
| Reviewer browser CI | Real browser cases run; missing required prerequisites fail | Pinned local browser suite; CI configuration review | Node, Playwright, Chromium |
| Design workflow | Canonical and legacy task paths are detected; invalid maintenance is visible | Focused workflow regressions | Current review-workflow contract |
| Cross-skill lifecycle | Schema-5, required compiler pair, Harness, Activation and SEO share real validated sources; incremental and maintenance coverage retained | Real checker CLIs and focused scenario tests | Synthetic common fixture |
| Runtime performance | Actual transition timings, unknown values retained, repeatable measurements | Transition regressions and bounded benchmark | Existing metrics schema and atomic write guards |
| Document sync | Retirement prose is quiet; unresolved pointers and unknown identity remain visible | Document-sync regression suite | No approval state in snapshots |
| Bilingual review and reading | Omitted structure/literals fail; same-session repeated reads can reuse verified unchanged bytes | Translation regressions and measured reference sets | Human semantic review remains required |

## Document Impact

| Changed source | Affected live artifact | Required recheck |
| --- | --- | --- |
| Checkers, CI and metrics | Four READMEs; affected skill references | Skill specification, lint, contract tests |
| Maintenance routing | Root AGENTS guidance | Compare with canonical review-workflow contract |
| 0.53.0 candidate | Package, lock, VERSION, RUNBOOK default, README badges/history, version tests | Version pins and full suite |
| Review result | This Epic, DOCUMENTS index and linked prior Epics | Final working-tree checkpoint |

## Change Log

| Observation / request | Scope and evidence | Verification and remaining work |
| --- | --- | --- |
| 2026-09-23 initial observation | Approved worktree/branch above; baseline and observed HEAD both `baf7e22b05a7f2776ee8b205395204ff21cbdcb5`; clean at creation | Direct local candidate; no exact committed candidate yet |
| 2026-09-23 browser CI, working-tree | `.github/workflows/harness-ci.yml`, `.gitignore`, package files and `test_reviewer_browser.py`; Node 24.19.0 and Playwright 1.62.1 pinned, required browser mode added | `npm ci` and Chromium provisioning passed; four focused tests passed, including two real browser cases and prerequisite behavior. Evidence: `C:/Users/mps19/AppData/Local/Temp/pdh-reviewer-browser-pinned-package-20260923.log`. Full suite pending |
| 2026-09-23 installed skill observation | Installed VERSION remains 0.52.0. Installed digest `1388c2a136bc47b7a732fb7ff67ee0ecbffe669f29393d01a2d910f438bd889e` differs from baseline source digest `b966d4250068b7b87fb665c03f76e771e90f45d616b8507c9b49d8f874321e96` only at `delivery-harness/scripts/select_verifiers.py` | External change observed / unverified; purpose and decision source unknown. Not adopted or overwritten. Session-loaded digest remains unobserved. Entry sync evidence: `C:/Users/mps19/AppData/Local/Temp/pdh-reliability-entry-document-sync-20260923.json` |

## Results And Remaining Work

The owner changed the remaining worker model to GLM Workers `glm-5.3-flash` during this round. Native Luna work was stopped at its checkpoint. The dispatcher requires a clean checkout for direct writes, so GLM receives read-only patch tasks against these existing uncommitted bytes; the parent integrates and verifies the returned patch. Earlier Luna results remain evidence. The four README descriptions, root maintenance routing and 0.53.0 candidate version pins are now synchronized; this is not publication or installation.

### 2026-09-23 checker checkpoint

The working tree now contains canonical task-file detection, UI-impact-aware maintenance summaries, narrow retirement-catalog filtering, translation structure/literal checks and same-session reading reuse guidance. Focused results: workflow 6 passed; document sync 25 passed and 1 Windows symlink-privilege skip; translation 12 passed; UI evidence 21 passed. Logs: `%TEMP%/pdh-reliability-{design_workflow,document_sync,translations,review_evidence}-20260923-final.log`. Initial retirement-regex grouping and numeric-count failures were corrected before those runs. Parent review identified a remaining numeric unit-prefix false-positive case for follow-up.

The shared lifecycle prototype exposed a real schema-5 integration failure: the Harness loader removes the UI script path before the checker lazily imports its own sibling modules. The UI checker now imports `review_evidence` and `operation_coverage` during module initialization, with the required product-parser path initialized first. Fresh subprocess checks without a PYTHONPATH workaround passed the required compiler pair, `new_run.py`, Harness plan/result and Activation stages. Prototype import/string-rebinding errors were test-construction errors, not product defects. The real SEO stage exposed a separate missing stack/repository-context handoff to its nested Activation checker; repair and final integrated regression remain pending.

The pre-edit reading-set inventory is `%TEMP%/pdh-reading-measurement-20260923.json`: 526,882 gross bytes and 503,773 unique bytes for the explicitly selected entry/product/UI/Harness references. The 23,109 repeated bytes are three repeated reads of the same document-sync contract. These counts exclude target product inputs and are not model-token or latency measurements. The source-reading rule keeps every invocation's inventory/identity check and permits reuse only for unchanged bytes whose full content remains available in the same session.

### 2026-09-23 lifecycle checkpoint

The new `test_lifecycle_golden_path.py` passes through the real compiler, Harness creation/plan/result checks, verified-source ready Activation and dated SEO lifecycle CLI using the same schema-5 package and release identity. It runs in normal Harness test discovery, without an opt-in flag or upstream validation mocks. The UI imports repair remains in place; `check_seo_review.py` now passes stack text and repository root through package and nested Activation validation. Focused checks passed: lifecycle 1, SEO 17, Activation 56, workflow 6, selected Harness joins/maintenance/pause/resume 5, and the original opt-in schema-4 golden path 1. Scoped pyflakes and diff checks passed. Evidence: `%TEMP%/lifecycle-golden-path-restore-final.log`, `lifecycle-seo-tests.log`, `lifecycle-activation-tests.log`, `lifecycle-maintenance-resume-tests.log`, and `lifecycle-legacy-schema4-golden.log`.

The source-binding negative case corrupts the compiler's wireframe binding, proves rejection, then refreshes it while retaining PRD/architecture/stack/HiFi bytes. It is binding recovery, not a product enhancement. Incremental scope is tested separately by `test_enhancement_requires_scope_and_detects_preserved_change`. Retained historical-pair maintenance uses schema 4; the new full release chain uses schema 5. Harness pause/resume gates are executable tests. Product Activation's staging-resume instructions have no dedicated executable flow and are not claimed as automated coverage. The new test restores the import path it observed before loading fixture helpers so it does not delete paths owned by other test modules.

Implementation and required verification are in progress. Browser evidence is local Windows evidence, not a completed GitHub CI run. Preserve the separate historical 0.52.0 results. Record final scoped diff identity, full tests, review findings and unresolved criteria here before handoff. Publication and installed-skill changes need their own exact authorization.

### 2026-09-24 verification checkpoint (UTC)

Five complete suites passed on the working tree: Product Definition 232, UI Design 278, Design System 99 (3 Windows-specific skips), Activation 56 and SEO 17. Both real Chromium reviewer cases executed in required mode. Logs are the `pdh-reliability-{product-definition-builder,ui-design-builder,design-system-compiler,product-activation,seo-growth-review}-*.log` files from 03:54-03:55 UTC under `%TEMP%`. The schema-5 lifecycle and remaining Harness gates still need the final runtime candidate.

GLM Flash run `20260923-204229-4042bc69fd464f82935cb628df9a123f` returned the numeric-prefix patch successfully. Its outer wrapper failed only while printing Unicode after child exit 0; the output encoder was repaired for later checks. Parent inspection also found numeric backtracking could turn `200msomething` into `20`; the boundary now excludes letters, digits and underscores. All 15 translation regressions passed, followed by the complete Product Definition suite above.

The first runtime proposal, GLM run `20260923-204229-33aec177f57549e7b50747d45288b53a`, exceeded its 600-second deadline. The wrapper inspected and terminated that task's process tree. No proposal was applied. Two smaller read-only GLM Flash tasks now cover production timing/summary code and regression tests separately; no OpenAI worker fallback was used. The advisory document-sync observation reports only unknown loaded identity and first-baseline review, with no retired-catalog warnings. It grants no approval or installed-skill migration.

### 2026-09-24 runtime and review checkpoint (UTC)

GLM Flash production proposal `20260923-205413-59f1572907c94dc6af6682625ca58eaa` and test proposal `20260923-205413-56007b1557a84898981a1e5adaea2f85` both completed. The production worker reported a rejected write attempt in its read-only sandbox; source edits were integrated by the parent only. Parent review corrected provider identity to `generic`, refused malformed metrics instead of repairing them, retained unknown durations as null, exposed verifier timings even when runtime metrics are absent, and preserved legacy schemas. The test fixture was bound to its actual synthetic Git HEAD.

Nine focused runtime tests passed: append/history preservation, lazy initialization, malformed-history rejection, failed validation, competing RUN replacement, read-only watchdog, independent verifier observations, unknown versus measured zero, and no run-time inference from phase sums. Evidence: `%TEMP%/pdh-reliability-runtime-focused-5a6406fd5e8440b1bff04aeda2b8f299.log`. Event `complete` means the preparation phase only; validation, later packet/request rendering, persistence and projection are outside its duration. Failed persistence never saves the candidate event.

The paired benchmark used the exact baseline Git archive and one restored synthetic fixture, alternating source order for 12 pairs. Baseline CLI median was 354.407 ms (320.082-790.301); candidate median was 351.361 ms (310.259-523.409). All 24 commands succeeded; each candidate produced one preparation event, measuring 4-6 ms. The overlapping ranges do not establish a speed improvement. Raw samples, fixture hashes, source hashes and environment are in `%TEMP%/pdh-reliability-paired-final-20260924/paired-results.json`; the measurement script is `%TEMP%/harness-runtime-metrics-paired-c9a100fb85714d9abed4125aecc413c3/paired_benchmark.py`. These numbers are not model latency, tokens, whole-delivery time or critical path.

Skill specification, all six script-directory pyflakes checks and docs weight passed. Documentation weight changed from 155,704 to 156,103 words (+399 against v0.52.0); this is a document-size observation, not a context-token count. Complete-diff advisory review found no unresolved blocking issue in the candidate. Formal security status remains `UNVALIDATED` because these are uncommitted bytes; no exact-SHA PASS was issued. Report: `%TEMP%/pdh-reliability-advisory-review-20260924.md`.

### 2026-09-24 installer verification correction (UTC)

The first complete Harness run executed 1,165 tests and reported 9 failures, 2 errors and 16 skips. All failures/errors were in installer tests: the installer correctly rejected the two new untracked test files before the intended scenario could start. The source bytes were unchanged. The parent registered only `test_lifecycle_golden_path.py` and `test_runtime_observations.py` with `git add -N`; this is intent-to-add, not a staged content change or commit. Installer rejection of untracked sources remains intact. The first log is retained at `%TEMP%/pdh-reliability-harness-full-b7e89df722a545fd9e9c6cc04037420e.log`. Focused installer checks and the complete Harness suite are being rerun against the same code bytes with the correct source inventory. The separate opt-in golden path and diff check passed.

The focused installer rerun passed all 15 tests in 356.228 seconds, including both foreign-race sentinels, rollback, marker failures, locks, junctions and Windows short-path handling. Evidence: `%TEMP%/pdh-reliability-installers-after-intent-f7c2a9c0189440aba11ed4f521b864ba.log`. No installer source was changed and no personal skills directory was updated. These tests use synthetic destinations under the test framework's temporary directories.

## Final Local Result — 2026-09-24 UTC

The six accepted reliability areas are implemented and verified as a local 0.53.0 candidate. The priority order remains cross-skill correctness and mandatory browser CI, then maintenance/translation checks, then observability and repeated-reading reduction. No full-delivery speed improvement is claimed.

| Verification | Result | Evidence under `C:/Users/mps19/AppData/Local/Temp/` |
| --- | --- | --- |
| Harness full rerun | 1,165 tests; OK, 16 skipped; 825.065 seconds | `pdh-reliability-harness-final-5853e9bf58ae409d9571d7b3f6c9b297.log` |
| Opt-in legacy golden path | 1 passed | `pdh-reliability-golden-opt-in-cf46b671ef1d4ef5af5c06a09dc2e081.log` |
| Product Definition | 232 passed | `pdh-reliability-product-definition-builder-2908b3292ae3436b907c735329321842.log` |
| UI Design, required browser mode | 278 passed, including both real browser cases | `pdh-reliability-ui-design-builder-31a9a0b851a64a8b9e94383ec177f111.log` |
| Design System | 99 tests; OK, 3 skipped | `pdh-reliability-design-system-compiler-d8f7ba8121204a7b9d71021f32582650.log` |
| Activation | 56 passed | `pdh-reliability-product-activation-8003d41da8204cf183460303e8b162e7.log` |
| SEO | 17 passed | `pdh-reliability-seo-growth-review-9dcd36213fd64bd0a8e6a433bf345751.log` |
| Skill specification | Passed | `pdh-reliability-skill-spec-cd3f31c02dcd400ebf4f76d7b38399a8.log` |
| Pyflakes, all required directories | Passed | `pdh-reliability-pyflakes-bb48f818b5844ec78bc84c4330dcf804.log` |
| Documentation weight | Completed; +399 words | `pdh-reliability-docs-weight-22d6b78419524252a48090debdef6d59.log` |

The six full suites contain 1,847 tests. With the separately enabled golden path, 1,829 passed and 18 were skipped for Windows symlink privilege, POSIX ownership/descriptor/process-group or file-mode requirements. Linux CI has not run in this local-only task. Browser checks did not skip. The original failed Harness attempt remains in the record above; the final complete rerun passed on the same source bytes after the two source-inventory intent entries were added.

Final source fingerprint: `4ebf5da6e6772ec3c77906a71e16373b13c998d23dc3e33c62dedc87cd84c935`, covering 30 changed/new source and configuration paths. It matches the fingerprint before broad verification. The inventory excludes Epic/index checkpoint records to avoid recursive logging; these records were separately reviewed and diff-checked. Inventory and exact working-tree status: `%TEMP%/pdh-reliability-final-identity-1d61e858335a4cedb9e9e4b56488516b.json`.

Repository/branch/HEAD remain the approved reliability worktree, `codex/skills-reliability-0.53.0`, and `baf7e22b05a7f2776ee8b205395204ff21cbdcb5`. There is no staged content or new commit. The two new Harness tests have intent-to-add entries; the new Epic and package lock remain visible untracked files. Root `node_modules/` and Python bytecode are ignored; package lock and source/tests are not ignored. The original main checkout still has only its preexisting untracked `scripts/design/hifi_model.py`.

This closes the authorized local implementation and verification scope. Commit, exact-SHA security review, publication, main promotion, tag and personal-skill installation remain separate steps; none occurred here. The working-tree security review stays `UNVALIDATED` for the formal gate. Installed-source drift and unknown loaded identity remain explicit observations, not silently accepted or repaired state. No task verification or GLM worker process remains active.

## Release Authorization And Commit Checkpoint — 2026-09-24 UTC

The owner subsequently instructed: `commit and push pr merge`. This authorizes committing this reviewed candidate, publishing `codex/skills-reliability-0.53.0` to `https://github.com/Phlegonlabs/product-delivery-harness.git`, creating its PR and promoting it to `main` through repository protection. The exact candidate is fixed by the final bookkeeping commit; external release evidence binds that full SHA before publication and merge. Release tagging and the mandatory post-push local installer follow repository release rules. No cleanup was requested.

Fresh remote observation and fetch found `main` still at baseline `baf7e22b05a7f2776ee8b205395204ff21cbdcb5`; the candidate remote branch and `v0.53.0` tag were absent. GitHub requires a PR, a passing `validate` check and squash merge. Local atomic commits retain the individual outcomes; the protected-main squash mechanism is verified by exact tree equality followed by the complete suite and a fresh security review at its resulting SHA.

The source/configuration fingerprint remains `4ebf5da6e6772ec3c77906a71e16373b13c998d23dc3e33c62dedc87cd84c935`. No implementation bytes changed after the successful local suites. Seven atomic commits record the verified changes:

- `782b994` — required browser CI and pinned prerequisites.
- `45ece05` — canonical workflow presence and maintenance classification.
- `bbe8697` — cross-skill lifecycle context and real CLI regression.
- `43b7cb3` — translation structure and numeric literal checks.
- `15def61` — retired catalogs, live references and same-session reading reuse.
- `5b77617` — measured transition preparation and read-only summaries.
- `5cd1f05` — version 0.53.0 pins and history.

This final bookkeeping change records the checkpoint and prior Epic links. Current installed digest remains `1388c2a136bc47b7a732fb7ff67ee0ecbffe669f29393d01a2d910f438bd889e`; session-loaded identity is unobserved. Document sync reports that identity gap and first-baseline review only. Installation must retain the existing modified `select_verifiers.py` in an installer backup. No other active skill-using task was observed before release preparation. Exact candidate/main CI, structured security receipts, PR, installation backup and tag read-back are retained as external release evidence so this record need not self-reference its commit.
