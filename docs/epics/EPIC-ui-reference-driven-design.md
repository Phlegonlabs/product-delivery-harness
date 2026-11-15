# EPIC-ui-reference-driven-design: UI design works from captured references and checks itself against them

Status: in_progress; candidate 0.81.0 on local branch `ui-reference-driven-design`, verified, not pushed, not reviewed, not installed
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
| URD-4 | `slop_scan.py` reports ten patterns, clusters at three, honors `--allow`, ignores the reviewer shell | `test_slop_scan.py` (26 tests) |
| URD-5 | `capture_sheet.py` writes a self-contained board or comparison page with hashes | `test_capture_sheet.py` (9 tests); renders at 1440 light and dark, 390 light |
| URD-6 | `visual_inputs.py` lists reference captures for `direction` and `hifi`, leaves `implementation` unchanged | `test_visual_inputs.py` (24 tests) |
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

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Reference-driven UI design (0.81.0 candidate) | Accepted Scope above | `7e1f1af4..b846a36e`, 23 commits on `ui-reference-driven-design` | Matrix at `b846a36e`: all nine steps exit 0 (`task/ui-reference-driven-design/matrix-b846a36e/summary.txt`). Independent review, push, PR, tag, install and consumer re-pin remain |

## Results And Remaining Work

Matrix at `b846a36e` against base `7e1f1af4` (`python skills/delivery-harness/scripts/ci_test_shards.py matrix --base 7e1f1af4 --log-dir task/ui-reference-driven-design/matrix-b846a36e --workers 8`, with `PDH_REQUIRE_BROWSER_TESTS=1`): skill spec, pyflakes, docs weight, harness (629 s), golden path, product (463 tests), ui (535 tests), design-system (222 tests) and the diff check all exit 0; result `pass`. The summary's `dirty: yes` is the untracked `task/` directory that holds the briefs and these logs. The run was local; CI has not run because nothing is pushed.

Sheet renders from synthetic full-page captures (not tracked): before the layout fix a 1440-wide capture showed as a strip about 270 px wide; after it, comparison rows show both captures at column width and a board shows three entries per row with scrolling wells. No horizontal overflow at 1440 or 390.

Docs weight against v0.80.0: `ui-design-builder` +1,475 words, `delivery-harness` +379, total +1,854. The ratchet is visibility only.

Open:

- No independent review has read this diff. The parent reviewed its own three fixes.
- `slop_scan.py` is heuristic and static. It reads inline CSS and `style` attributes, finds only the ten named patterns, and has not been run on a real consumer HiFi package.
- `fix/agentkiosk-ui-compiler-contract` (`31edbcf4`) is still local and unmerged. It touches `check_ui_design_contract.py`, `docs/DOCUMENTS.md` and its own Epic; whichever branch lands second rebases its `Current Epic` line and takes the next version.
- Five worker worktrees under `~/.t3/worktrees/product-delivery-harness/` hold only commits already on this branch. Removal waits for the owner.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / ui-reference-driven-design / b846a36e plus this record commit / task/ untracked
Stage and skill: source maintenance, direct route (no PLAN/RUN)
Inputs consumed (path + hash or revision): main 7e1f1af4 (v0.80.0); captions of https://www.youtube.com/watch?v=-bv2xKQzZio read 2026-11-15; task/ui-reference-driven-design briefs
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): not run; this source repository omits the consumer template sections by design, and no Harness skill workflow was invoked
Approvals in force (gate, owner, date, candidate): owner instruction 2026-11-15 to refine the UI flow with Sonnet 5.5 writers; branch from main and owner-connected reference tools chosen the same day; local commits only
Done and verified (command, exit code): ci_test_shards.py matrix --base 7e1f1af4 at b846a36e (exit 0, result pass); prepare_release.py --check (exit 0)
Remaining: independent diff-scoped review; push and PR to main; tag v0.81.0; install; consumer re-pin
Blocked / waiting (gate name or owner decision): owner decision to review and publish the branch
Next action (one command or one owner decision): owner decides whether to run the protected read-only review and open the PR
Next owner (skill or human): human
```
