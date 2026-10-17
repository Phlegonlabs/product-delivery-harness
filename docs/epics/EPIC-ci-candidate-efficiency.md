# EPIC-ci-candidate-efficiency: exact-candidate source CI and measured sharding

Status: complete

## Problem And Baseline

At `bdae1d82acfd24cdeb2866f5480ff4d4d73b0b61` (0.58.0), every branch push and
its pull request both ran the full workflow. Pull-request jobs did not all use
the same checkout identity, Windows defaulted to the event checkout, and the
PR whitespace base was always `origin/main`. The long Harness suite was one
monolithic job on each POSIX platform. There was no aggregate gate that made a
skipped matrix dependency fail the required check.

The accepted design source is
`C:/Users/mps19/Documents/Codex/2026-09-29/harness-flow-review-01a0ed97/流程與提速評估.md`,
MOD-B. This repository has no current product PRD; the change is source
repository maintenance with UI impact `none`.

## Accepted Scope

Owner-approved scope: deduplicate feature push/PR execution while covering
`main`, `development`, merge groups and exact-SHA manual releases; use one
candidate SHA in every job; make the required aggregate fail on skipped or
cancelled work; freeze release concurrency by SHA; use actual PR/merge bases;
retain golden path, required browser, installer and platform coverage; split
long suites using measured file timing; and align the consumer CI template
without source-only commands or provider assumptions.

Exclusions: no source branch-contract validators, release version, root
AGENTS.md, remote settings, installer, ruleset or promotion changes. No
child workers were authorized. The parent owns integration and any later
0.59 reconciliation.

## Acceptance And Dependencies

| Requirement / TEST ID | Expected outcome | Verification / environment | Dependency |
| --- | --- | --- | --- |
| CI-TRIGGER-1 | Feature pushes verify once by PR; protected pushes, merge queue and manual release remain covered | Focused source-workflow and template contract tests | Hosted CI |
| CI-CANDIDATE-1 | Every suite job checks and asserts one full canonical SHA | `test_ci_candidate_gate.py`, `test_ci_template_contract.py` | Hosted CI |
| CI-AGGREGATE-1 | Stable `validate` rejects failure, skip, cancel and timeout | Focused aggregate and shell contract tests | Main branch protection already names `validate` |
| CI-CONCURRENCY-1 | Manual release is keyed by SHA and cannot be cancelled by a later development push | Focused concurrency contract test | Hosted CI |
| CI-SHARD-1 | Harness discovery is partitioned exactly once; every launched file has positive tests; a failing file gives nonzero | Actual subprocess shard plans and failing-file regression | Measured Windows sample |
| CI-COVERAGE-1 | Golden path, Linux browser, macOS non-browser UI, installer and native platform checks remain | Focused workflow matrix tests | Hosted CI |
| CI-TEMPLATE-1 | Consumer template follows candidate/dedup principles without provider or source-suite coupling | `test_ci_template_contract.py` | Consumer adoption |
| CI-DOCS-1 | Four READMEs describe candidate selection, dedup, sharding limits and strict aggregate | Docs weight and README structure tests | None |

## Document Impact

| Changed source / requirement | Affected live artifact | Required recheck |
| --- | --- | --- |
| `.github/workflows/harness-ci.yml` | Source CI trigger, candidate, matrix and aggregate behavior | Source-workflow tests and hosted matrix |
| `skills/delivery-harness/scripts/ci_test_shards.py` | Discovery, timing balance, conservative fallback and aggregate gate | Shard helper tests |
| `skills/delivery-harness/ci-test-timings.json` | Windows sample weights and complete 84-file discovery inventory | Shard coverage tests |
| `skills/delivery-harness/assets/templates/PROJECT_CI.template.yml` | Consumer CI template | Template contract tests |
| Four READMEs | Verification and release descriptions | Docs weight and translation structure |

## Change Log

- Completion checkpoint: YAML repair `cd1d5a794ad20f657797cca8843c4cdd256faa56` is pushed and read back exactly on the work branch. The repaired source and template pass complete local YAML parsing and the 34-test CI suite; the 60 skill-contract and five README tests also pass. Actions run `36650936919` remains immutable failure evidence for original `688acf2`. The repaired feature push has no workflow run, matching the declared protected-branch-only push trigger; this is not hosted matrix success. The final seven-skill development installation matches repaired source, 379 files, verified backup `20260929-174323`, with dependencies available. Full exact-candidate review/matrix and formal release remain pending.

- 2026-09-29: source baseline `688acf2fb253d935615b1b582f23b13e72598d51`. The authorized work-branch push created Actions run `36650936919`, which failed before creating any jobs. A local complete YAML parse reproduces the error at concurrency line 32: the expression closure was at mapping indentation, outside a scalar. The source workflow and consumer template both contain this error in concurrency and DIFF_BASE_SHA. Use folded scalars to preserve one-line expression values, add whole-document parser tests and original-error negative fixtures, and add PyYAML to the existing test requirements. Trigger, candidate, base, concurrency and aggregate semantics remain unchanged. Focused verification and a repair push are pending; this is not a hosted matrix PASS or a release. The initial development install from `688acf2` succeeded with 378 byte-matched files and preserved verified 0.58.0 backup `20260929-173420`; the repaired skill bundle needs a further authorized installer transaction before handoff.

- Working-tree CI repair verification: 34 CI tests (including complete source/template YAML parses and two malformed closure fixtures), 60 skill-contract tests, five README-structure tests, skill specification, scoped Pyflakes, docs weight and full whitespace check pass. All checks ran from this repository root with finite deadlines and external logs. Four README descriptions now distinguish YAML parsing from text assertions. No UI, action-authorization, trigger or release policy changed; existing ignores cover Python caches and no local logs are introduced. Independent exact-candidate review and the complete release matrix remain UNVALIDATED, as recorded for the unreleased candidate; focused results are not their replacement.

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Add measured shard helper, focused tests and 84-entry timing inventory | Turn actual test discovery into deterministic four-way partitions and reject silent timing omissions | `db200c8` | Focused shard tests 7/7 and scoped pyflakes passed. Profile completed at 2026-09-29T16:01:58+00:00: 1,423 tests, 84 files, 19 skips, 9 failures and 2 errors caused by installer tests rejecting the then-untracked timing manifest. Durations are scheduling observations only. Raw results: `C:/Users/mps19/AppData/Local/Temp/pdh-ci-profile-20260929-084614/harness-profile-results.json`. Manifest source is `2026-09-29_windows-sample_python3.14`; it is not macOS/Linux measurement or release evidence. |
| Replace source workflow with exact-candidate trigger/matrix design | Stop duplicate feature runs, fix checkout identity and create strict aggregate | `a2b4041` | Candidate workflow tests 7/7, Harness skill-contract 60/60 and scoped pyflakes passed. Installer focused run did not complete under its local 180-second wrapper and is not claimed; it remains in the full Harness suite. |
| Fix shard path basename and Windows discovery interface | Relative paths matched zero files with `-p`, and basenames were compared to repo-relative discovery | `1d957e2` | Candidate tests 12/12, shard helper tests 7/7 and scoped pyflakes passed. New subprocess tests prove actual plans cover discovery and a failing discovered file exits nonzero. |
| Stream shard output to job-local logs | Avoid collecting potentially large suite output | `f9fa6b4` | Candidate tests 12/12 and scoped pyflakes passed. POSIX saves `PIPESTATUS[0]`; Windows saves `LASTEXITCODE` first. |
| Align consumer CI template | Apply the same candidate/dedup/aggregate principles without source-suite or provider assumptions | `09a83e0` | Template tests 6/6, skill contract 60/60 and scoped pyflakes passed. Stable consumer gate name remains `verify`. |
| Scan full native log for positive coverage | Buffered stdout can flush after the unittest summary | `0f16f17` | Candidate tests 12/12 passed. Windows prints a 10-line summary but checks the full log with `Select-String -Quiet`. |
| Describe CI candidate and scheduling behavior | Keep the documentation of record aligned in all four languages | `3f49d19` | Docs weight exit 0 and README structure tests 5/5 passed. |
| Fail closed on a missing or meaningless CI diff base | Manual runs could check an empty clean tree; an unavailable push base could self-diff against the new remote ref. Added required manual `base_sha`, verified ancestry, strict event-base resolution, and an explicit Git empty-tree comparison for an initial push | CI-DIFF task commit (this row is in the same record) | Focused helper 5/5, source workflow 12/12, template 6/6, skill contract 60/60, README structure 5/5, docs weight, scoped pyflakes and `git diff --check` passed with finite subprocess deadlines. No full suite or profile is in scope. |
| Make CI diff validation portable and preserve triple-dot semantics | The consumer template wrongly depended on a source checkout, direct base comparison could include advanced base-only edits, and inherited stdin made `git mktree` potentially interactive. The source helper now computes verified PR/merge-group merge bases with noninteractive Git calls; the consumer template uses equivalent inline Git checks | CI-DIFF repair commit (this row is in the same record) | Helper 6/6, template 7/7, source workflow 12/12, README structure 5/5, docs weight, scoped pyflakes and `git diff --check` passed with finite subprocess deadlines. No full suite or profile is in scope. |
| Remove profile output buffering and fail a bad Windows shard plan | Parent audit found unittest output captured in unused memory, and the Windows workflow parsed planner JSON before checking its exit. `profile_suite` now streams runner diagnostics to stderr; the planner exit is saved and checked before JSON parsing | CI stream/exit audit commit (this row is in the same record) | Helper 7/7, candidate gate 12/12, skill contract 60/60, scoped pyflakes and `git diff --check` passed with finite subprocess deadlines. No profile or full suite was run. |
| Update the macOS shard assertion for GitHub matrix expansion | Full 0.59 suite showed the test expected four literal `--shard-index` strings while the accepted workflow uses one templated command and `shard: [0, 1, 2, 3]`; macOS four-shard coverage was unchanged | 0.59 focused repair commit (this row is in the same record), parent suite `97f2fae3` | Focused test passed after failure reproduction; scoped pyflakes and `git diff --check` passed. No workflow implementation change was needed. |
| Align the repository restore-rule test with 0.59 installer ownership | The test required retired wording, while accepted rules require automatic rollback and previous-tag reinstall that backs up the bad copy; added explicit assertions for that rule and protected backups | 0.59 governance-test repair commit (this row is in the same record), accepted source `c203ab4d` | Focused test passed after failure reproduction; scoped pyflakes and `git diff --check` passed. Installer implementation, backups and rollback behavior were unchanged. |

## Results And Remaining Work

Local HEAD before this record is `3f49d198c3bf7dde2a688dc68429164645618ba8`.
The focused results above cover the new scheduling behavior and descriptive
docs, not a full local release suite and not hosted CI. No performance
percentage is claimed because no before/after hosted matrix has been run.

Scoped document sync reports `review_required`: loaded skill identity was not
observed, this is the first baseline review, and the four READMEs contain
historical retirement names in release history. It is an inventory finding,
not an approval. No snapshot was saved.

Remaining: exact-SHA full local verification, hosted Linux/macOS/Windows CI,
security review, integration with the parent's separate `c203ab4` README
changes and 0.59 changes, and fresh discovery reconciliation. Files added by
0.59 work after the profile—such as `test_branch_policy.py` and a frontend
`test_contract_source_binding.py`—are not in the timing sample. CI currently
schedules them explicitly with `--allow-unmeasured` at the maximum measured
weight. Full required verification and release decisions remain open. The
source aggregate keeps the name `validate`, matching the currently observed
required main check; no remote ruleset change is made here.


## 2026-10-03 Release Aggregate Repair

- Baseline: `codex/harness-flow-modernization`, clean candidate `77c5ab135cb03edd85c0d7263ed9d2f21cfe42d9`. User requested push, formal publication and local skills update. Scope remains CI-AGGREGATE-1 source maintenance, UI impact `none`; the parent is the only writer. No ignore pattern or artifact class is introduced; logs remain outside the checkout.
- Hosted run [37106737321](https://github.com/Phlegonlabs/product-delivery-harness/actions/runs/37106737321) completed all 19 test/quality jobs successfully, then failed `validate`: the common dispatcher called `run_gate(root, arguments)` but the handler accepted only `arguments`. This is a failed candidate gate, not a successful matrix. Original logs are retained under `C:/Users/mps19/AppData/Local/Temp/pdh-release-20261002-trrq9aed/`.
- The old local full Harness check was cancelled after 839.633 seconds for this bounded repair, without a completed verdict. The recorded test PID/start/command were verified before stopping; its Windows job removed three remaining owned children and confirmed zero live job members. Product 257, UI 319 (required Chromium), compiler 134 (4 Windows platform skips), Activation 65, SEO 21 and golden path 1 passed on the old SHA; these do not certify the replacement candidate.
- Repair round 1: align the gate handler with the existing two-argument dispatcher. Preserve strict success-only semantics. Add public-CLI regressions for nine successes, each failed/skipped/cancelled/timed-out/empty/unknown result, and absent results. Update the four README CI descriptions. The new tests reproduced seven failures before repair; the full shard-helper file then passed 10/10. Exact check records: `release-gate-cli-red-process.json` and `release-gate-cli-green-process.json`; both jobs exited with zero remaining processes.
- The normal Opus final review of 77c5 was stopped by weekly quota 429 with no tools used and no verdict. No model substitution occurred. The owner exception request for the replacement fixed candidate review and remaining manual-reference exploration remains pending. Earlier catalog-only Astra permission is not expanded by this record.
- Remaining: commit this one repair after focused workflow/static checks, push its exact SHA to the work branch, rerun the complete local and hosted release matrix, and complete independent full-diff/security and manual-reference exploration. Main/development promotion, ruleset/bootstrap decisions, v0.59.0 tag/release and official skill installation remain pending. No protected branch was modified.
- Working-tree verification at parent 77c5ab1: all CI discovery/workflow/helper regressions 37/37 and README structure 5/5 passed; scoped Pyflakes, Agent Skills specification and whitespace checks passed. Check records are release-gate-workflow-checks-process.json and release-gate-readme-check-process.json; both report zero remaining owned processes. This entry and repair form one atomic follow-up commit; final exact-SHA checks remain fresh work.

- 2026-10-03 CI-PROFILE-DEADLINE-1 at parent `b90dd378f4c721fd3bb1e5817a8ee70da700d9b6`, branch `codex/harness-flow-modernization`: independent correctness review found that the profile timeout was checked only after an in-process test file returned. A stuck import or test could run forever. Each file now runs through the existing owned-process-tree helper with the remaining total deadline; its diagnostics stream to the caller without collecting unused output. A timed-out file is recorded separately and supplies no completed timing. Completed observations survive, while import errors, empty files and test failures remain failures. Zero seconds starts no file; negative and nonfinite deadlines are rejected. This restores the existing timeout contract, with UI impact `none` and no new public flow or local artifact class.
- Working-tree verification for CI-PROFILE-DEADLINE-1: shard helper 13/13 passed, including hung imports/tests, descendant exit, partial results, streamed diagnostics and fail-fast behavior. Existing host runtime 20 tests passed with two POSIX-only skips on Windows; Windows job cleanup and existing captured-output behavior passed. Scoped Pyflakes and whitespace checks passed. Tests ran from the root with actual 120/180-second deadlines and exited. Evidence is under `C:/Users/mps19/AppData/Local/Temp/pdh-worktree-merge-20261003-eb6k85jg/` in `profile-deadline-focused.log` and `profile-host-runtime-focused.log`. These bytes belong to this atomic repair; new candidate review and the full exact-SHA hosted matrix remain pending. Existing ignores cover Python caches; temporary logs and process records stay outside Git.
