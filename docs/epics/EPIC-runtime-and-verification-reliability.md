# EPIC-runtime-and-verification-reliability: Measured execution and dependable verification

Status: locally_verified_release_repair

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

## 0.53.1 Browser Verification Repair — 2026-09-24 UTC

PR #120 merged candidate `8f466066548b717863c61be0965d826c7357d591` as main `3a0c37a292dbd8a2ff788d707a00680ff3c6d240`. Both trees are `cc21f3fa13a83d4747214a24a89682a9b878efaf`. Candidate PR CI passed Linux and Windows. The branch's first Linux attempt exceeded the HiFi browser scenario's 45-second outer deadline; its failed-job rerun passed without source changes. Fresh main CI `35958536799` then hit the same outer deadline. No product assertion was reported in either timeout, but the logs do not identify the stalled operation. This is a repeated test reliability failure, not a passing release gate. No `v0.53.0` tag was created.

GLM Flash diagnostic run `20260923-215720-752b21e93ffc4f069dd04b305cb64ddd` inspected the failure read-only. The long scenario performs multiple page/history transitions and about 50 browser calls. The sibling Wireframe scenario took about 22 seconds on the first failing runner and 1.4 seconds on the successful PR runner. Both scripts prefer system Edge before bundled Chromium, despite CI provisioning Chromium. A second GLM Flash task prepares a bounded repair: select bundled Chromium in required mode, retain optional local Edge fallback and every product assertion, add phase diagnostics and a separate total deadline for the long scenario.

The owner approved exact branch `codex/skills-browser-ci-0.53.1`, version 0.53.1 and reuse of the existing reliability worktree, then reiterated `remember to commit and push pr review`. Earlier commit, push, PR and merge authority continues for this repair. A fresh fetch observed main at `3a0c37a292dbd8a2ff788d707a00680ff3c6d240`; the new branch was cut from that exact SHA with a clean checkout. UI impact remains none. Scope is the browser test harness, matching four-language README guidance, required version pins and this release record. No new artifact class or ignore rule is needed.

The prior installer successfully matched all 284 tracked skill files to 0.53.0 and preserved all 320 previous installed files under `C:/Users/mps19/.agents/skill-backups/product-delivery-harness/20260923-215041/`, including the modified `select_verifiers.py`. External release evidence is under `%TEMP%/pdh-release-053-8f46606/`. Loaded session identity remains unknown. The repair needs focused real-browser checks, the complete candidate suite, PR review, mandatory post-push installation and exact-main verification before the 0.53.1 tag.

### Repair Verification Checkpoint

GLM Flash run `20260923-221332-d9d26cdacd034076836c0f298390ec50` returned the test-file patch. The parent integrated it and corrected its assumption that Python's default timeout traceback displays captured child output: the small browser runner now raises a diagnostic failure containing that output. A real child-process regression prints a completed phase, reaches its two-second deadline and verifies that the failure retains the phase. Required mode directly launches bundled Chromium; optional local Edge fallback and every product assertion remain. The long HiFi total deadline is 90 seconds; Wireframe remains 35 seconds and Playwright operation limits are unchanged. Browser close errors cannot hide the original test error.

All commands ran from the repository root. Focused browser tests passed 5/5, including both real Chromium scenarios and the diagnostic regression. The full required-browser UI suite passed 279/279 in 56.030 seconds. All 60 skill-contract tests passed after the 0.53.1 version pins changed. Specification checks, all six pyflakes directories, docs weight and diff checks passed. Evidence under `%TEMP%`: `pdh-reliability-browser-repair-focused-27eb010b6b1146e582b396ed96acff06.log`, `pdh-reliability-browser-repair-ui-full-b5d8c0c34ac347a6ba9ddd79689a93ab.log`, `pdh-reliability-browser-repair-version-966260384f2e4042ba8654941a63941b.log`, and the `pdh-reliability-repair-{spec,pyflakes,docs-weight}-*.log` files. The complete exact-candidate CI remains pending and is required before merge.

Commit `fda2acb` records the independently verified browser repair and matching README descriptions. Version pins and release history use their own following commit; this documentation-only commit records the verification checkpoint. No production behavior changed, no worker remains active and no cleanup was performed. The final clean candidate SHA, complete-diff PR review, CI, installation backup and resulting main evidence will be bound externally under `%TEMP%/pdh-release-0531/` before the release tag.

## Runtime Resume Repair — 2026-09-24 UTC

The owner requested a cross-repository review of repeated RUNs, mismatched missions and SHA drift, then authorized local repairs on `codex/runtime-resume-repair` in `C:/Users/mps19/Documents/GitHub/product-delivery-harness-runtime-repair`. Baseline and observed HEAD are `82911eaac1e0f91c48d9591c9c5cf43898d73708`. The original checkout's untracked `scripts/design/hifi_model.py` remains outside scope. This is routine maintenance with UI impact `none`; no product PRD, design artifact or target-project RUN is changed. Existing references and four READMEs remain the behavior contract. No PLAN/RUN is created for this direct repair.

The local review found these distinct states. Repository records are evidence of recorded state, not runtime process liveness:

- Overbet's retained RUN 9 had all five missions integrated. Commit `f74dae6` describes opening RUN 10 after an E2E repair moved HEAD beyond a successful gate. Current commit `8885f34e1242a571972ead824642c8f7dfb679c3` says M1 replay but its tree equals its first parent's tree. This is concrete repeated coordination/integration with no resulting tree change.
- Hardwareprices records RUN complete at local HEAD `4bd22e12c86db8409578a7cb224916a7fcc27af9`, but its canonical integration SHA `93e30709287e0d8fa15d0be0a0d4b1c3fd6b5f42` is not a local object. Canonical gates remain planned; an unsupported `completion` object contains prose PASS claims. Current validation rejects the record. Removing that field only in memory exposed further errors; the repository file was not edited.
- Jolvex's recorded running state names a different branch/head from its current dirty checkout. Agentic Commons has a ready RUN with an explicit cancelled control state and later direct work. Both contain legacy runtime records. Neither establishes a currently running process or authorizes automatic migration.

The current 0.54.0 source reproduces historical verifier heads being compared to mutable current heads/checkpoints, succeeded gates refusing a new attempt after a repair, bracketed literal route paths being rejected as scope patterns, and unrelated worktrees blocking resume while ready states bypass reconciliation. Acceptance requires preserving history and completed missions, exact current PASS coverage, bounded retry budgets, fresh integration/security review after candidate changes, and fail-closed checks on relevant dirty, missing, divergent or out-of-scope work. No replay of completed missions or automatic new RUN is an acceptable recovery.

GLM Flash writable run `20260924-035137-db9e0d1437b847709834c34b5bda4a08` failed with HTTP 429 after partial edits to six scripts. Those bytes were preserved and not accepted as complete. Two read-only follow-ups were stopped when the owner explicitly requested `use sol 5.6 high`; GPT-5.6 Sol high now owns bounded repairs. The parent reviews the combined diff and validates it independently. Test dependencies were separately authorized and installed in this checkout; personal skills were not updated. Commit, push, merge, target-project RUN migration and cleanup are outside this authorization.

Baseline focused verification passed 75 tests before edits. Working-tree repair validation is pending. Logs and temporary runner artifacts remain outside the checkout; root `node_modules/` and Python bytecode use existing ignore rules. No new artifact class needs a new ignore rule. The final checkpoint will record the changed-byte fingerprint and actual test results. Loaded skill identity remains unobserved; installed Harness 0.54.0 and its shared AGENTS template were observed. A saved source hash is not proof of the session-loaded version.

### Concurrent Target-Repository Observation

A later read-only checkpoint observed external changes during this repair. Overbet advanced from `8885f34` through `2f04a53` (record M1 integration) to `14eca8af05fef0f3f4783f47a68e715cb1ca208e` (batch gate and wave-2 acceptance); its RUN/tasks view remain dirty. Hardwareprices advanced from `4bd22e1` through `8153013` to `5e37d851401d83e9d7950311b2048e7f98f18682` with deployment/activation commit messages and a clean tree. Its local `core.hookspath` now blocks hardened Git observation. These are observed/unverified external changes; their intent and authorization were not audited here. No target files or Git configuration were changed by this repair. Inspector validation must distinguish a blocked Git observation from an aligned repository.

### Prevention In The Skills

The owner asked to turn the incidents into a prevention policy, not only individual fixes. `delivery-harness/SKILL.md` now makes recovery before replacement explicit; execution-state, verification and runtime-adapter references define the concrete behavior. The four READMEs describe the same contract. These rules apply across hosts because RUN ownership and evidence checks belong to the shared core.

| Failure family | Preventive rule | Enforcement and regression evidence |
| --- | --- | --- |
| A gate passes, a repair changes SHA, then the whole run is replayed | Keep the unchanged PLAN in the same RUN; preserve completed missions and revalidate the changed candidate under the existing attempt budget | Guarded candidate reconciliation and reservation; `test_candidate_resume.py`; repair-attempt attribution and exact authorization passed final source review; broad verification is recorded below |
| Historical SHA/lease records fail when the current checkpoint advances | Retain the original context and check current PASS separately | `harness_manifest.py`; `test_historical_verifier_evidence.py`, including fresh-lease intermediate state and refusal to reuse the old lease as current PASS |
| Missions or tasks match by title/prose instead of identity | Bind run ID, PLAN revision/digest, mission/task, attempt, lease and exact SHA; use guarded result transitions | Existing result/worker validation plus the historical-evidence regressions; unsupported completion prose cannot replace canonical gate records |
| Dynamic route names are treated as patterns | Treat observed filenames literally; keep write-scope pattern grammar separate | `validate_changed_path`; dynamic-route and unsafe-path tests in `test_select_verifiers.py` |
| Unrelated or old worktrees block current recovery | Inspect current parent and bound workspaces; preserve unrelated and historical work | `test_runtime_resume_worktrees.py`; current dirty/missing/wrong-head cases remain denied |
| Inspection looks quiet while parent/candidate state diverges | Report parent branch/head, canonical object availability and blocked Git observations separately from process liveness | `test_inspect_parent_drift.py`; process liveness remains unknown until observed by its owning runtime |
| A retry or new RUN silently replenishes the budget | Carry cumulative attempts and failure-family limits; require the existing explicit grant procedure when exhausted | Existing graph/review lineage validators plus candidate budget tests; a fresh RUN is not a recovery shortcut |
| RUN says complete but canonical gates or tasks view disagree | Validate canonical state, exact candidate and generated view as separate checks; never infer PASS from prose | Existing closeout validators and `render_tasks_view.py --check`; read-only cross-repository audit found Hardwareprices outside this contract |

The operating sequence is: inspect identity and live state, reconcile existing work, reserve the exact attempt, execute once, record verified evidence, then render/check the tasks view. An ambiguous native launch is inspected for its existing identity before another launch. Only a new initiative or an explicitly authorized formal revision/replan starts a new pair; it never relabels the old pair. Legacy records and pinned active runtimes are not automatically migrated by this source repair.

Documentation alone cannot stop an agent with unrestricted file access from hand-editing RUN. The implementation therefore guards supported transition paths, preserves receipts and validates current evidence. Direct JSON edits, false human attestations and unobserved external processes remain outside what a local schema validator can prove. The required response is an explicit reconciliation gap, not an invented PASS.

### Repair Review And Validation Freeze

GPT-5.6 Sol high completed the bounded repairs. Review required two additional safeguards before the broad test run: candidate adoption must bind the current failed verifier/review receipt and one exact task, with existing exact commit/integration grants; and live sibling workers must not prevent a passed mission from entering streaming review merely because their phase is still running. Focused tests cover both. Candidate recovery rejects unexplained blocked/contract-gap receipts, exhausted budgets, unrelated scopes, active work and a changed final Git observation. Inactive routed skipped integration reviews fail closed before mutation because their old tree proof cannot safely be carried to a new candidate; no graph schema or review bypass was added.

Validation started on the fixed skills fingerprint `506d3134bc946933d1e3fdbc399ab29ad7996c27da0cca3ad25e59ccd351fb9d` in working-tree state at HEAD `82911eaac1e0f91c48d9591c9c5cf43898d73708`. Evidence directory: `C:/Users/mps19/AppData/Local/Temp/pdh-runtime-repair-validation-j3_8hak0`. Skill specification, all six Pyflakes directories and documentation-weight checks passed; full suites are running. The runner verifies the same skills fingerprint after every phase. Four new regression sources have intent-to-add entries so installer tests see the correct source inventory; no content is staged and no commit was made.

The installed 0.54.0 shared AGENTS template has SHA-256 `1677220abf249a21b7b3967aada7b8a7339f0d614a85958132ea938b908c78e7`. Applicable shared rules are current by meaning; repository-specific source paths and stricter Git/release rules are retained. No AGENTS rewrite is needed. Document sync reports only first-baseline review and unknown loaded identity; it grants no runtime migration. Source/test/lock files remain tracked or visible, while dependencies and bytecode match existing ignore rules.

Final independent GPT-5.6 Sol high source review found no remaining blocker after the receipt/authorization, live streaming and inactive-skip safeguards. Parent review independently reran the historical-evidence tests and inspector tests. The real Hardwareprices read-only diagnostic now reports `git_observation_status: blocked`, `needs_reconciliation: true` and a generic metadata/configuration-guard warning without exposing configuration values. The formal fixed-SHA security gate remains `UNVALIDATED` because this authorized delivery is an uncommitted local candidate; the review is not an invented release/security PASS.

### First Broad Verification Attempt

The first Harness suite in `pdh-runtime-repair-validation-j3_8hak0` exposed three failures: two close-wave/next-wave cases in `test_close_wave.py` and the exact tasks-view checkpoint set in `test_harness_transition.py`. The parent stopped this known-failing suite after 263.25 seconds, after inspecting its PID/command and children, then confirmed termination. The negative process exit records this deliberate stop; the suite did not complete and is not a PASS. Earlier specification, Pyflakes and docs-weight phases passed on the frozen fingerprint. Focused reproduction is retained at `%TEMP%/pdh-runtime-repair-full-failures-focused.log`; repairs and a new complete run are required.

The close-wave failures exposed a legitimate intermediate state: a mission integration verifier runs on the observed parent before `record-integration` stores its final SHA. For a merge, that parent SHA can differ from the worker SHA. Pending evidence now requires a current passed worker with matching mission, worker and lease identities, a null `integrated_sha`, and the exact observed parent SHA. Completed integration evidence remains bound to its recorded lineage. The regression includes a valid intermediate RUN, different worker/merge heads, rejection of an arbitrary head, and rejection of an unrelated observed head after integration. The tasks-view assertion now includes the new reconciliation checkpoint. These corrections preserve current exact-SHA checks; they do not relabel historical evidence.

### Complete Harness Attempt And Release Continuation

The next full Harness run completed 1,201 tests in 1,759.070 seconds with three failures and 16 skips. Evidence: `%TEMP%/pdh-runtime-repair-validation-c3hjscm5`, frozen skills fingerprint `cd17b4ff351559aef79048b05757a7e3eaa184c4696336d35455e0b2faabf46a`. Two failures concern v11 review reservation; the third is the main skill's 3,600-word context limit (3,787 observed). This is failed verification, not a release PASS. The prevention detail was moved into the execution-state reference with a short main-skill pointer; the main skill is now 3,597 words and all 60 skill-contract tests pass. Review reservation diagnosis remains in progress.

The owner subsequently requested commit, push, merge and local skills update after completion. A fresh fetch observed remote `main` at `b4ffe691b97265d5a76817c2e0ccf457e084fa54` (0.53.1). The existing repair base contains four earlier commits through `82911ea`, already proposed in PR #122, for Design Brief, PRD refinement and handoff document audit. The parent requested confirmation of whether publication includes those prior changes; no publication or merge occurs while that scope remains unresolved. Local runtime repair and verification continue. No target-project RUN migration or cleanup is authorized by this release request.

Both v11 failures were fixture drift: the CLI fixture rebound the parent checkout to its temporary repository but retained the old parent worktree observation. The fixture now records the exact temporary parent and preserves the current worker observation, then requires a valid RUN before writing. No production guard was relaxed. The writer and independent reviewer each passed the two reported cases and all 23 v11 tests, plus Pyflakes and diff checks. Production source is frozen.

Four atomic commits record the reviewed runtime outcomes: `3ef2257` literal changed paths, `91102c4` historical verifier identities, `cc58fd0` parent/candidate inspection, and `758bf7d` same-RUN candidate/workspace recovery with the fixture correction. Documentation records the prevention contract separately. Formal fixed-SHA security review and the complete candidate suite remain required before publication. Release evidence will be retained outside the checkout at `C:/Users/mps19/AppData/Local/Temp/pdh-runtime-release-11ae5aa8051341518f0ffa70879872a1/`, binding exact candidate/main SHAs, scope decision, gates, PR, installation backup and tag read-back. This avoids rewriting a verified candidate merely to record its own SHA. The original checkout still has only its unrelated untracked `scripts/`; no cleanup occurred.

The owner confirmed that the four existing 0.54.0 preparation commits should be reviewed, verified and published together with these repairs. The combined candidate uses version 0.54.1; remote tags `v0.54.0` and `v0.54.1` were absent at preparation, so the four README histories identify 0.54.0 as unpublished preparation included in this release. The owner then requested fixing omitted `frontend-design` use for Wireframe and HiFi before publication. That added same-release outcome is tracked in [EPIC-ui-reviewer-integration.md](EPIC-ui-reviewer-integration.md). Publication remains held until the expanded candidate passes review and verification; the earlier commit/push/merge/install authorization remains in force for completion.

Final preparation checkpoint: frontend authoring repair `e67bfa9` and technical-role prompt repair `cb0e651` passed independent source review and focused tests. Version preparation is committed at `cf331b17102c735da930e0939b067c6b7c6ac237`; all four README descriptions/history, package and lockfile, Harness VERSION, RUNBOOK default and pinned assertions agree on 0.54.1. Prior Design Brief, PRD and handoff Epic statuses now distinguish committed continuation from historical working-tree observations. The final bookkeeping commit will bind these records; security and complete suite results will be written to the external evidence directory already named above. No full candidate PASS, push, merge, tag or installation is claimed yet. Gitignore checks confirm dependencies, bytecode and local .env remain ignored while sources and lockfiles remain tracked. The original checkout is still at 82911ea with only its unrelated untracked scripts/. Shared installed 0.54.0 template rules remain current by meaning; no AGENTS rewrite or generated tasks view is needed for this direct task.

### Fixed-Candidate Review Correction

Fresh security and correctness review of clean candidate `d640f21b84c92c4b291aa2bb8d6939ffa86cacbc` reproduced a parent-inspection gap: a modified tracked file with unchanged branch/HEAD produced `live_dirty: true` but `comparison_state: aligned`, no warning and CLI exit 0. Existing mutation transitions still enforce dirty-state guards; this is a misleading recovery diagnostic, not a demonstrated authorization bypass. The candidate is held for a bounded inspector warning and regression test. The old candidate review remains historical; a new fixed-SHA review and complete regression are required after the correction. No push, merge or installation has occurred.

Correction committed as `4be704556bf20d59ea0440976111a4154b732cc0`: relevant parent dirt now emits a generic warning, requires reconciliation and exits 1. Only an ordinary modification of the exact in-repository tracked RUN passed to the inspector is exempt; RUN plus product changes and an untracked RUN still fail. No status contents are exposed. The writer passed all 10 parent-drift tests, scoped Pyflakes and global diff checks; parent reviewed the code and exception. The final full candidate and main suites will run through the canonical GitHub workflow, including required Chromium; local focused Windows results remain separate from CI evidence. The earlier incomplete/failed broad local attempts remain recorded above and are not relabeled as passing.

Fresh review of replacement candidate `6ab0ec4498f53f0531b27c03ac7f9cc0e2c109eb` found a related incomplete-observation case: failed `git status` could produce null dirtiness while branch/HEAD/object checks still led to available/aligned and exit 0. The candidate remains unpublished. The inspector repair now also needs a generic incomplete-observation warning for unavailable required Git probes; unknown values must not become a positive alignment result. Execution-side mutation guards are unchanged. Historical candidate reports remain external evidence, and a new fixed-SHA review is required.

The incomplete-probe correction covers HEAD, branch and status together. Missing required observations in an available repository now report partial/unavailable, a generic warning, reconciliation and exit 1; metadata guards still report blocked, and a non-repository retains its existing explicitly unknown informational state. The writer passed 11 parent-drift tests, scoped Pyflakes and diff checks; the parent reviewed the bounded 10-line production change and fault-injection regressions. No authorization or execution mutation path changed. New exact-candidate review and CI are still pending.
