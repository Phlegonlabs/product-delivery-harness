# EPIC-parallel-checks: run the full check and the UI check at the same time

Status: published as 0.86.0 on 2026-11-17 (PR #193, `main` `176be53b`, tag `v0.86.0`); installed the same day (five-skill contract `ace80228…`); consumers adopted 0.87.0 directly, see EPIC-design-flow
Design workflow: enhancement
UI impact: none (one capture script flag, review rules, the source test runner and two CI jobs; no product UI in this repository).

## Problem And Baseline

The owner said the full check, the UI full check and the UI review stage are slow, and asked whether they can run concurrently and be split by situation.

Three read-only explorers and two parent measurements, 2026-11-17:

| Where | How it ran | Measured |
| --- | --- | --- |
| HiFi matrix capture in a consumer | one Node process, one Chromium, one page; every case in turn | agentkiosk final capture: 304 cases, about 21 minutes, about 3.4 s per case |
| Final review | one reviewer carried the code, security and visual lenses in turn | not measured |
| Broad final validation | started only after the review converged | not measured |
| Source UI suite | one `unittest discover`, modules in turn | 157 s; 68 s with one process per module |

Real packages put most cases on one page (ticketradar 158 of 222, hk-car-care 54 of 150), so a split by page alone would not help them.

The split by situation already existed in the rules: no visual lens and no UI matrix without a UI change, affected pages only after a repair, changed-file selection for a failed final suite, `security: not_applicable` for a docs-only diff. What was missing is concurrency.

Baseline: `main` `3a553df7` (v0.85.0).

## Accepted Scope

Owner instructions, 2026-11-17: do it with several agents on Claude Sonnet 5.5; keep the number of headless browsers down, because about ten at once overloaded the machine.

- PC-1: `hifi_matrix_capture.py --workers N` (1 to 4, default 1) spreads the cases, interaction attempts, reviewer passes and axis passes over N browser drivers by a fixed partition and writes one merged output.
- PC-2: one review point is dispatched as concurrent per-lens read-only calls (code, security, visual) on the same SHA; the parent merges them into one finding set and one repair loop.
- PC-3: on the direct route the broad final validation may start with the review on the same unchanged candidate. Managed runs keep their declared graph.
- PC-4: the source verification matrix runs the product, ui and design-system suites with one process per module; the browser suites are capped at three modules at a time; the two Linux CI jobs for those suites use the same runner.

Kept unchanged: exact-SHA binding, read-only reviewers, one consolidated finding set, the two-pass review budget, the owner request for several reviewers of the same lens, no reuse of evidence after a repair, the managed graph, every CI job name.

## Acceptance

| ID | Expected outcome | Verification |
| --- | --- | --- |
| PC-1 | The partition is deterministic and complete; the merged output equals the serial output apart from timestamps, durations and page-load transcript rows; a page one browser cannot open fails as in a serial run and a row that already failed stays failed; a driver out of restarts blocks only its share; no driver process is left behind, also when a start is interrupted; a repeated axis is refused | `test_hifi_matrix_capture.py` (107 tests), `test_hifi_matrix_capture_workers.py` (27), fake drivers and real Chromium |
| PC-2 | The per-lens rule is stated once in `verification-gates.md`; the managed stage card, the PLAN template and the delegation contract agree | `test_skill_contract.py` |
| PC-3 | The ladder, the final gate sentence and the direct-route steps allow the overlap; the managed sentence keeps the dependency | `test_skill_contract.py` |
| PC-4 | The three suites run module-parallel with the browser variables; a zero-test module fails; a failing module's output is in the step log; browser suites never exceed three modules | `test_ci_test_shards.py` (17); the full matrix below |

## Execution Record

Direct Fan-Out: three Claude Sonnet 5.5 writers (claude-t3-direct, effort high), one worktree each, from `3a553df7`. The parent merged each branch when it returned.

| Part | Result |
| --- | --- |
| W2, PC-2 and PC-3 | merged (`755211c0`, `51dd8870`, `3ec90907`). Documents and one test module; no script change. A managed security result must report every `required_tools` entry of its node, so a managed node that requires a browser splits two ways (code; security with visual), not three. |
| W3, PC-4 | merged (`daebb7cd`, `2b6b2372`). Product 75 s to about 35 s, ui 253 s to 73 s, design-system 117 s to 58 s, measured while other writers loaded the machine. |
| Parent | `4b96438b`: browser suites capped at three modules, CI lowered from four to three, after the owner's report of about ten open browsers. |
| W1, PC-1 | merged (`aa48d21c`, `88d80c8b`). The writer's run died once on an HTTP 403 before the provider and was resumed in the same thread. |

Found on the way (PC-1): the one-browser run was wrong on real packages. The driver reopened a page only when its own page variable changed, so a page that navigated by itself left later attempts on the wrong page, and product state left by one attempt changed the next. Every interaction attempt now reloads its source page, for every worker count. On the ticketradar copy (222 cases, 782 attempts) interaction failures went from 341 to 232, and two serial runs agree with each other where they did not before.

Measured on that copy, each run alone: `--workers 1` 1803 s, `--workers 4` 697 s (about 2.6 times), identical rows.

## Review And Repairs

One review point on `b801975d`, sent as three scoped read-only calls at the same time (GPT-6.1 Sol, effort high), code and security lenses each.

| Scope | Verdict | Blocking findings |
| --- | --- | --- |
| Runner and CI | PASS | none |
| Rules | FIX_REQUIRED | the managed stage card and the PLAN template still told the parent to dispatch one reviewer carrying every lens |
| Capture | FIX_REQUIRED | an interrupted start could leave a driver running after cleanup; a page-load failure did not carry across shares or phases; a repeated axis gave two workers the same capture file names |

Repairs: `752ea8c3` (rules, parent), `3c0ce20d`, `d65cf836`, `6d5011b4` (capture, W1).

Targeted re-check on `2a8a2fb2`: rules PASS; capture two of three resolved, one left: adopting an unopened page turned a row that had already failed into BLOCKED. Isolated repair `79f6b1ed` (parent): a failed row stays FAIL. Scoped review on `d897060c`: PASS.

Security lens: pass in every call that carried it; `not_applicable` for the scoped repair.

Review notes not acted on: the browser-suite cap test asserts the printed worker count, not the executor's limit; the runner has no explicit regression case for CRLF, skipped-only or import-error output; `security-review.md` still says a reviewer returns security "beside its other-lens findings"; in the interrupted-start tests, two of four did not fail when the fix was removed in a simulation.

## Verification

- Full matrix on `2a8a2fb2`: `ci_test_shards.py matrix --base origin/main --workers 8`, result pass. Harness 789.2 s (128 modules), golden path 5.5 s, product 28.2 s, ui 74.5 s, design-system 58.2 s, skill spec, pyflakes, docs weight and diff check pass.
- On `d897060c` (the two-line repair after it): both capture test modules with browser tests required, 134 tests, exit 0; pyflakes exit 0; `git diff --check origin/main HEAD` exit 0.
- CI on the pull request head is the candidate's full run. Its first two runs failed in `linux-required-browser` on one test, `test_demo_gallery_runs_sandboxed_and_interactive`: the first gallery frame never became ready. A longer wait (`aa28b742`) did not help, which showed the cause: the gallery page marks a frame ready when the frame reports its size, and on a loaded runner the first frame reports before the page listens and never reports again. That is a defect in the `design-system-compiler` gallery runtime that the serial suite had been hiding. This round does not fix it, because the fix changes the generated preview bytes of every `design-system/4` package; the module now runs alone after the parallel batch (`SERIAL_FILES`).

Open defect for a later round: the gallery runtime can miss the first frame's size report under load, leaving that plate at its default height.

## Change Log

- 2026-11-17: published as 0.86.0 and installed. CI passed 14 of 14 on `f1c24be4` after the gallery module moved to the serial path; scoped review of the two CI repairs PASS; the merge commit is tree-equal to the candidate (`promotion_readback.py post`: `tree_equal_S`).
- 2026-11-17: reviewed, repaired and verified; release surfaces set to 0.86.0.
- 2026-11-17: round opened; scope and acceptance recorded; three writers started.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / main / 176be53b (v0.86.0) / none
Stage and skill: source maintenance; release complete
Inputs consumed (path + hash or revision): main 3a553df7 (v0.85.0); agentkiosk and ticketradar evidence read for timings only
Approvals in force (gate, owner, date, candidate): owner 2026-11-17 "OK 做吧" after the parent stated it would push, open the pull request, merge after CI, tag v0.86.0 and install; consumer re-pins are not covered
Done and verified (command, exit code): full matrix on 2a8a2fb2, result pass; capture modules on d897060c, exit 0; review PASS on d897060c
Remaining: the gallery runtime race. Consumers skipped 0.86.0 and adopted 0.87.0 (EPIC-design-flow, Change Log)
Blocked / waiting (gate name or owner decision): none
Next action (one command or one owner decision): the owner decides whether to fix the gallery runtime race
Next owner (skill or human): owner
```
