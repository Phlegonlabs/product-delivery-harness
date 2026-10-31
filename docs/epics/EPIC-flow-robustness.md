# Flow Robustness, GTM Reach And PRD Review

Status: complete on `feat/flow-robustness` as 0.74.0; PR #164 green and ready to merge; tag, install and consumer adoption follow the merge
Design workflow: enhancement
UI impact: none (skill rules, templates and scripts; no product UI in this repository).

## Problem And Baseline

Managed runs broke in the middle. The owner's consumer repos record the same causes: a RUN left `running` for six weeks with no lock (jolvex-platform), reviewers interrupted at a 540-second route cap before a verdict (hk-car-care EPIC-006), a first review wave lost to a worker route's turn cap (ticketradar EPIC-005), review lineages exhausted into waivers or new RUNs, and environment failures (browser CSP console errors, a Node version off the stack pin) counted as review findings. An autonomous `/goal` loop also stalls at owner gates the Harness asks mid-run, and the `codex-goal-prompt` skill knew nothing about the Harness. On the product side, the PRD was checked only by its author before the owner approved it, and a later portfolio review found defects in two approved PRDs. The go-to-market skill still covered the 0.65 channel set while the suite had grown to 22 surface classes.

Baseline: `ef327ff6` (0.73.0 on `main`). Branch `feat/flow-robustness`, clean at start except the untracked local `task/` scratch directory.

## Accepted Scope

Owner instruction on 2026-10-31: fix every finding of the suite review with multiple agents, then review by Fable.

- Resume from one command: `inspect_harness_run.py` prints a Next block with the state and one recommended command; a `running` RUN without a lock needs an owner decision before selection.
- Seven managed stage cards, each at most 300 words, so the parent acts from the card and reads the long contract only on failure.
- A Harness launch brief template (`HARNESS_GOAL.template.md`) carrying the authorization ledger, pre-recorded owner decisions, the gates that always stop, environment facts and resume rules; `codex-goal-prompt` gains a Harness Mode that uses it.
- Route caps (time, turns, bytes) recorded per assignment; briefs and review packets sized to the route before launch; workers commit verified work and return `REFINEMENT_REQUEST` before the cap.
- An environment preflight at plan readiness; a failed row blocks readiness as `environment`, not as a mission or review failure.
- Product Definition: a Product Thesis readback before closed-set decisions, one independent read-only PRD review plus one targeted recheck before Product Definition Approval, and a ten-question owner review guide at the approval request.
- Go-to-market: a persisted messaging record, lifecycle messaging for the Growth Contract re-engagement mechanisms, developer, store and Hong Kong and Taiwan channel playbooks, channel candidates by track, and a launch runbook bound to the PRD Launch Window.
- A fourth standalone skill, `customer-discovery`, for user interviews whose findings become `RA-*` candidates.

Not in scope: closing or resuming the stale jolvex-platform RUN (owner decision in that repo), a version bump or release, installing the bundle, and any change to consumer pins.

## Acceptance

| ID | Expected outcome | Verification |
| --- | --- | --- |
| FR-1 | `inspect_harness_run.py` prints a `Next:` block first with one of six states and one recommended command | `test_inspect_harness_run.py`, `test_inspect_parent_drift.py`, `test_candidate_resume.py` |
| FR-2 | `references/stages/stage-cards.md` has seven cards, each at most 300 words, naming only existing commands and flags | word count per section; `docs_weight.py` |
| FR-3 | `HARNESS_GOAL.template.md` exists with the ledger, decisions, stopping gates, environment facts and resume rules; `codex-goal-prompt` routes Harness repos to it | file review; agents repo commit `c0bde79` |
| FR-4 | Delegation, adapter, verification-gates and WORKER_GOAL state the route caps, the packet split rule and the pre-cap commit rule | `test_skill_contract.py`, `test_launch_packet.py`, `test_documented_commands.py` |
| FR-5 | Readiness names the environment preflight rows and blocks on a failed row with an `environment` reason | `test_skill_contract.py`, `test_harness_manifest.py`, `test_new_run.py` |
| FR-6 | Product Definition runs the thesis readback, the independent review and recheck, and presents the owner review guide; READMEs describe the same budget | `test_pre_delivery_self_review.py`, `test_skill_contract.py`, `test_cross_skill_pipeline.py` |
| FR-7 | Go-to-market references, templates and SKILL.md describe the messaging record, lifecycle messaging, the new playbook sections, channels by track and the launch runbook | `test_enhancement_entry_contract.py`, link check |
| FR-8 | `standalone-skills/customer-discovery` passes the activation and metadata checks; the standalone count is four | `test_enhancement_entry_contract.py`, `check_skill_spec.py` |
| FR-9 | One independent review on the unified candidate, then the Required Verification matrix once on the final SHA | review record below; CI or local shards |

## Document Impact

Parent-owned: `skills/delivery-harness/SKILL.md`, the four READMEs, this Epic, `docs/DOCUMENTS.md`, and the `codex-goal-prompt` skill in the agents repository. Worker packages: WP1 inspector Next block; WP2 stage cards; WP3 launch brief template; WP4 route caps; WP5 environment preflight; WP6a messaging record and lifecycle; WP6b playbooks, channels by track and launch runbook; WP7 customer-discovery; WP8 PRD review, thesis readback and owner guide. Each worker ran as GLM-5.3 Flash through T3 `delegate_task` in its own worktree with explicit file ownership.

## Change Log

- 2026-10-31: suite review delivered in chat; owner asked to fix all findings with multiple agents and review by Fable. Branch `feat/flow-robustness` created at `ef327ff6`. Nine workers dispatched; `codex-goal-prompt` Harness Mode committed in the agents repository as `c0bde79`.
- 2026-10-31: all nine packages integrated serially on `feat/flow-robustness` (`35e60ebc`). Two workers (WP4 route caps, WP6b playbooks) ended in a runtime error; WP4's finished edits were recovered from its worktree and trimmed under the 1200-word worker template cap, WP6b was relaunched and landed on its second attempt. Parent-owned edits: `skills/delivery-harness/SKILL.md` entry rules (trimmed to 1996 words under the 2000 cap), the four READMEs, this Epic.
- 2026-10-31: independent review at `35e60ebc` by Claude Fable 5.1 as the Harness parent, after the profile hook refused Fable as a child model on both the native Agent route and `delegate_task`. The parent did not author the nine worker packages; its own edits (WP4 recovery, SKILL.md, READMEs) are self-reviewed and named here. Blocking findings, all repaired: the inspector's `select` state recommended `record-observation` while no lock was held (`0f031419`); the launch brief pointed at a RUN `Next action:` line that exists only in `MISSION_RUNBOOK.template.md` (`0f031419`); the customer-discovery `RA-*` table claimed to mirror the research assessment but used `Evidence`/`Source` columns it does not have (`aa6762f7`). Non-blocking notes, also repaired: Card 5 omitted `--evidence` on `record-node-result`, Card 1 called a stale lock an owner decision, Card 7 cited "Managed Run Archive" with the wrong case, the brief pre-filled the console policy fact and said the brief and cards own every rule (`0f031419`); the self-review order sentence read badly (`c4316ad0`); an Instagram link placement was stated as fact (`15860b3d`). Checks after repair: inspector, parent-drift, candidate-resume, skill-contract, pre-delivery-self-review, enhancement-entry, cross-skill-pipeline suites exit 0; card word counts 171 to 297; relative links in changed docs all resolve.
- 2026-10-31: not done here, by scope: the stale jolvex-platform RUN (an owner decision in that repo), any version bump, release, bundle installation or consumer re-pin. Worker worktrees under `~/.t3/worktrees/product-delivery-harness/` and their `t3/*` branches remain until the owner confirms removal.
- 2026-10-31: Required Verification matrix ran once on the working tree whose skill, script, template and README bytes equal `aa6762f7` (only `docs/epics` and `docs/DOCUMENTS.md` changed after it). Results, logs under the local `task/flow-robustness/matrix/`: `check_skill_spec.py` exit 0; `pyflakes` exit 0; `docs_weight.py` exit 0 (+2,763 words, baseline v0.73.0); harness suite 107 modules passed, 0 failed, 592 s with 8 workers; golden path OK; product-definition-builder suite OK; ui-design-builder suite OK (2 skipped); design-system-compiler suite exit 0; `git diff --check` clean. CI on the PR head is the matrix of record.
- 2026-10-31: owner accepted the handoff proposal. WP10 (GLM-5.3 Flash, worktree) added one fixed `## Handoff` block to `EPIC.template.md`, the checkpoint and entry rules in `task-and-handoff.md`, the Epic shape sentence in `bounded-enhancement.md`, Card 1 and Card 7, managed closeout, the PRD, UI, go-to-market and growth-review stage exits, and a pinning test (`2126db42`, `d40e3d56`, `66fe51bb`); the four READMEs name the block (`1a46a676`). Fable review as parent: no blocking finding; three notes repaired in `59f5851f` (duplicate heading inside the template fence, Card 1 read-first placement, Output list conjunction). Affected suites after the repair: enhancement-entry, skill-contract, governance-entry-routes, pre-delivery-self-review, documented-commands, readme-structure, docs-weight, cross-skill-pipeline, the product-definition-builder and ui-design-builder suites, all exit 0; `check_skill_spec.py` and `git diff --check` clean. The full matrix is not rerun for this docs-only isolated repair; CI on the PR head is the matrix of record.
- 2026-10-31: owner asked to finish every suggested follow-up. Added the `mvp`-first recommendation for small new products (`84ffb210`) and the 0.74.0 release surfaces, including `package-lock.json` left at 0.72.0 by the 0.73.0 release (`793c39e3`). Opened PR #164. Codex review found two real inspector bugs (a cancelled run fell through to `select`; a recovered failure kept the run in `reconcile`), fixed in `4df1d5cb` with tests and in Card 1 (`a99592f3`); both threads answered and resolved. CI on `a99592f3`: all 14 jobs passed. Removed the eleven worker worktrees and merged `t3/*` branches; the crashed WP4 worktree's uncommitted diff is kept at the local `task/flow-robustness/wp4-worktree-uncommitted.patch`. The jolvex-platform RUN `RUN-PD-R8-01` reads `stale_no_lock` in the new inspector; both its finished mission heads are on jolvex `main` and its integration branch is gone. It was left untouched: another live session holds that checkout and the RUN is pinned to 0.45.0, so pause, cancel or resume stays the owner's decision (recommended: cancel).

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / feat/flow-robustness / PR #164 head / none (untracked local task/ only)
Stage and skill: source maintenance release 0.74.0; direct route
Inputs consumed (path + hash or revision): base main ef327ff6; agents repo c0bde79 (codex-goal-prompt Harness Mode)
Approvals in force (gate, owner, date, candidate): owner "fix all ... review by fable" and "以上你建議的都做完它" 2026-10-31, covering PR, merge, tag, install, re-pin and cleanup
Done and verified (command, exit code): CI on a99592f3, 14 of 14 jobs pass; local full matrix at aa6762f7 content exit 0
Remaining: merge #164, tag v0.74.0, run install.sh, adopt 0.74.0 in consumer repos
Blocked / waiting (gate name or owner decision): jolvex-platform RUN-PD-R8-01 pause, cancel or resume (recommended cancel)
Next action (one command or one owner decision): gh pr merge 164 --merge
Next owner (skill or human): parent session, then owner for the jolvex RUN
```
