# EPIC-ui-reference-driven-design: UI design works from captured references and checks itself against them

Status: in_progress; candidate 0.81.0 on local branch `ui-reference-driven-design`, verified at `ba84417d`, reviewed once with one targeted re-check, not pushed, not installed
Design workflow: enhancement
UI impact: none (design-stage rules, two scripts, one helper change and documentation; no product UI). `capture_sheet.py` writes an owner-facing review page; its before/after renders are listed under Results.

## Problem And Baseline

The direction and HiFi author received a long prompt and prose about references. Nothing set how many references a round needs, nothing guaranteed the captures reached the author's task, and nothing put the HiFi candidate next to the direction the owner selected. The author's self-review covered geometry and console errors, not whether the result looked like the target or like a default template.

Owner direction (2026-11-15): refine the UI flow from Leon Lin's AI design workflow, as walked through in `https://www.youtube.com/watch?v=-bv2xKQzZio` (read from captions, not the primary article), and do the work with Sonnet 5.5 writers.

Baseline: `main` `7e1f1af4` (v0.80.0).

## Accepted Scope

| Idea from the source | Applied as |
| --- | --- |
| Short prompt, 9 to 12 reference images | Reference board for every new visual scope (floor of 5 under `mvp`); `visual_inputs.py` lists the captures in the author's task |
| Make the target first | The existing three direction studies; no new stage |
| Set the bar with a number; agents over-score | Author aims for a 99% direction match and records its estimate; the lead grader records its own first; a gap of 15 or more points is told to the author |
| Give it time | Frontend brief: quality over speed, ask blocking questions first, then build without check-ins |
| Ban the slop | Brief carries the ban list; `slop_scan.py` flags a page with three or more default patterns |
| Design first, motion second | HiFi static pass, self-check, motion pass; motion references get timing notes |
| Feedback with targets | Owner feedback as rows naming element, property and expected result; vague feedback gets a description back, not a guess |
| Let another model judge | Grading record names author and grader models; a different model family for the lead grader when agent policy offers one |

Owner decisions in this session: the work branch is cut from `main`, not stacked on `fix/agentkiosk-ui-compiler-contract`; an owner-connected reference MCP or browser tool may be used, and an agent never installs or connects one.

Not adopted: looping review rounds until a score clears (the one-wave, one-repair, one-re-review budget stays), an eight-hour default run, and any checker, schema, threshold or gate change. The direction match is a calibration record.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| URD-1 | Board rule, tool rule, motion notes and composition-before-motion are each stated once and linked | `test_skill_contract.py` (both skills), link check over the changed files |
| URD-2 | The frontend brief, direction prompt, workflow steps and both self-reviews carry the board, match, time and ban lines | `test_cross_skill_pipeline.py`, `test_pre_delivery_self_review.py`, `test_documented_commands.py` |
| URD-3 | Rubric, review packet and evidence rules record direction match, scan clusters and models without a new gate | `test_templates.py`, `test_review_matrix_docs.py` |
| URD-4 | `slop_scan.py` reports nine patterns, clusters at three, honors `--allow`, ignores the reviewer shell, and ends every input with exit 0 or exit 2 | `test_slop_scan.py` (88 tests) |
| URD-5 | `capture_sheet.py` writes a self-contained board or comparison page with hashes | `test_capture_sheet.py` (10 tests); renders at 1440 light and dark, 390 light |
| URD-6 | `visual_inputs.py` lists reference captures for `direction` and `hifi`, leaves `implementation` unchanged, and reports an unreadable folder as an error | `test_visual_inputs.py` (27 tests) |
| URD-7 | READMEs describe the flow in four languages; release surfaces agree | `prepare_release.py --check`, `test_skill_contract.py` |

## Document Impact

| Changed source | Affected live artifact | Required recheck |
| --- | --- | --- |
| `design-reference-guide.md`, `ui-design-intake.md`, `motion-and-media-routing.md`, `modern-design-sources.md`, `option-library/design.md` | Reference research in consumer UI rounds | Next new visual scope gathers a board |
| `delegation-contract.md`, `ui-design-pass.md`, `stages/ui-design.md`, `review-workflow.md`, `pre-delivery-self-review.md`, `worktree-thread-orchestration.md` | Every frontend dispatch brief and both author self-reviews | Next direction or HiFi dispatch |
| `ui-grading-rubric.md`, `review-evidence.md`, `output-contract.md`, `UI_REVIEW_PACKET.template.md`, `UI_DESIGN.template.md` | Grading record and review packets | Next diagnostic wave |
| Five-skill bundle bytes | Consumer pins | Re-pin after a release install |

## Execution Record

Five Sonnet 5.5 writers (`claude-t3-direct` / `claude-sonnet-5-5`, effort high) through `delegate_task`, one T3 worktree each from `7e1f1af4`, disjoint file ownership. Briefs: `task/ui-reference-driven-design/COMMON.md` and `W1.md` to `W5.md`. The parent (Claude Fable 5.2) read each diff and cherry-picked the commits in completion order.

- W3 `cba3f6e0`: Direction Match section, scan clusters as `H5` evidence, judge models, review packet fields, repair findings name element and property.
- W1 `98818332`: reference board, owner-connected tools, intake wording, motion notes, composition before motion, source record.
- W2 `c9c2adc8`: brief lines, direction prompt, workflow steps, self-review bullets, Owner Feedback section, comparison sheet at Visual Approval.
- W5 `27ab3a6b`: `capture_sheet.py`, reference captures in `visual_inputs.py`, `frontend-visual-inputs.md`.
- W4 `fb03bf7e`: `slop_scan.py`, tests, two fixtures.

Parent commits: brief lines scoped per stage (`dcba7077`); grading summary placeholder (`97246579`); sheet layout (`0bc498d9`), because an 80vh cap shrank a full-page capture to an unreadable strip; scanner thresholds (`59f03c1e`), because the first numbers missed the `#667eea` to `#764ba2` gradient and common cream canvases; CLI inventory (`4a5b6c41`); README rows (`ff1fe0b4`, with `0be0c927` restoring two phrases a test pins in the Chinese READMEs); version surfaces (`b846a36e`).

### Review And Repair

Review of `12df0d30`: four parallel protected read-only reviews (`run_gpt_review.py`, gpt-6.1-sol, effort high, git-free packets from `review_input.py`). Judging rules and release surfaces passed with no finding. The other three scopes returned 20 findings:

- Author rules, 3 blocking and 1 note: a researched board added an owner turn under `mvp` (`1bf22ff3`); a motion recording could not go on the board sheet (`28e77bda`); the no-copy rules contradicted the page-faithful route (`45b19055`); the study-stage estimate promised a grader check that does not exist (`0da471d8`).
- Tests, 5: link cleanup that fails on POSIX, unchecked embedded image bytes, untested title escaping, a hardcoded round that passed, a vacuous evidence-length check (`01ee1961`, and the last one in `4075d7aa`).
- Scripts, 11: `visual_inputs.py` reported an unreadable reference folder as an empty board (`6091f512`); ten in `slop_scan.py`, repaired by one Sonnet 5.5 writer as families (`4075d7aa`, R1 brief).

Targeted re-check of `12df0d30..9e5a1a56`, three scopes: the four rule findings and the five test findings closed. Left over: a metadata permission error still read as an empty board (`4bf64376`); one new test multiplied its input by zero (`c6e0c47c`); and eight defects in `slop_scan.py`, all in the parts the first repair had added (selector matching, variable scope, hand-written HTML stripping, number parsing).

The parent did not repair those eight one by one. A second Sonnet 5.5 writer removed the parts that needed an engine (`ba84417d`, R2 brief): the `pill-badge-row` pattern and all selector matching are gone, `var()` is replaced once or the declaration is not read, the HTML parser excludes the reviewer shell, emoji use a pinned list, and `main` turns any exception into exit 2. The script went from 621 lines to 504. The parent ran every reproduction from the re-check against the result (44 probes, all pass; 32,000 selectors against 32,000 elements in 0.3 s, linear).

The review budget is one review and one targeted re-check, and both are spent. `ba84417d` has not been independently reviewed.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Reference-driven UI design (0.81.0 candidate) | Accepted Scope above | `7e1f1af4..b846a36e`, 23 commits on `ui-reference-driven-design` | Matrix at `b846a36e`: all nine steps exit 0 (`task/ui-reference-driven-design/matrix-b846a36e/summary.txt`). Independent review, push, PR, tag, install and consumer re-pin remain |
| Review repairs | Review And Repair above: four rule passages, three test modules, `visual_inputs.py`, `slop_scan.py` rewritten smaller | `12df0d30..ba84417d`, 11 commits | Matrix at `ba84417d`: all nine steps exit 0 (`task/ui-reference-driven-design/matrix-ba84417d/summary.txt`). The simplified scanner is not independently reviewed. Push, PR, tag, install and consumer re-pin remain |

## Results And Remaining Work

Matrix at `b846a36e` against base `7e1f1af4` (`python skills/delivery-harness/scripts/ci_test_shards.py matrix --base 7e1f1af4 --log-dir task/ui-reference-driven-design/matrix-b846a36e --workers 8`, with `PDH_REQUIRE_BROWSER_TESTS=1`): skill spec, pyflakes, docs weight, harness (629 s), golden path, product (463 tests), ui (535 tests), design-system (222 tests) and the diff check all exit 0; result `pass`. The summary's `dirty: yes` is the untracked `task/` directory that holds the briefs and these logs. The run was local; CI has not run because nothing is pushed.

Matrix at `ba84417d`, same command and base, after the review repairs: harness (791 s), golden path, product (463 tests), ui (601 tests), design-system (222 tests), skill spec, pyflakes, docs weight and the diff check all exit 0; result `pass`.

Sheet renders from synthetic full-page captures (not tracked): before the layout fix a 1440-wide capture showed as a strip about 270 px wide; after it, comparison rows show both captures at column width and a board shows three entries per row with scrolling wells. No horizontal overflow at 1440 or 390.

Docs weight against v0.80.0 at `ba84417d`: `ui-design-builder` +1,600 words, `delivery-harness` +389, total +1,989. The ratchet is visibility only.

Open:

- The simplified `slop_scan.py` (`ba84417d`) and the two last small fixes (`4bf64376`, `c6e0c47c`) have not been independently reviewed. Everything else was reviewed and re-checked.
- `slop_scan.py` is heuristic and static. It reads inline CSS and `style` attributes, finds only the nine named patterns inside what its Reads note states, and has not been run on a real consumer HiFi package.
- `fix/agentkiosk-ui-compiler-contract` (`31edbcf4`) is still local and unmerged. It touches `check_ui_design_contract.py`, `docs/DOCUMENTS.md` and its own Epic; whichever branch lands second rebases its `Current Epic` line and takes the next version.
- Seven worker worktrees of this round under `~/.t3/worktrees/product-delivery-harness/` (W1 to W5, R1, R2) hold only commits already on this branch. Removal waits for the owner.
- The next round, motion layer and catalog (0.82.0), stacks on this branch as `ui-motion-and-libraries`.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / ui-reference-driven-design / ba84417d plus this record commit / task/ untracked
Stage and skill: source maintenance, direct route (no PLAN/RUN)
Inputs consumed (path + hash or revision): main 7e1f1af4 (v0.80.0); captions of https://www.youtube.com/watch?v=-bv2xKQzZio read 2026-11-15; task/ui-reference-driven-design briefs; seven protected review results under the gpt-reviewer runs of 2026-11-15 and 2026-11-16
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): not run; this source repository omits the consumer template sections by design, and no Harness skill workflow was invoked
Approvals in force (gate, owner, date, candidate): owner instruction 2026-11-15 to refine the UI flow with Sonnet 5.5 writers; branch from main and owner-connected reference tools chosen the same day; owner agreed to the independent review the same day; local commits only
Done and verified (command, exit code): ci_test_shards.py matrix --base 7e1f1af4 at ba84417d (exit 0, result pass); prepare_release.py --check (exit 0); 44 scanner probes from the re-check (exit 0)
Remaining: push and PR to main; tag v0.81.0; install; consumer re-pin
Blocked / waiting (gate name or owner decision): owner decision to publish the branch
Next action (one command or one owner decision): owner names the SHA and how far to publish (push and PR, merge, tag, install, re-pin)
Next owner (skill or human): human
```
