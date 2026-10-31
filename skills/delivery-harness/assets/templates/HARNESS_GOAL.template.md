# Harness Launch Brief

<!--
Instantiate this template as docs/goal/HARNESS_GOAL.md in the target project.
This file records owner statements made before launch. It grants nothing by itself.
The parent transcribes each yes row into the RUN `authorizations` ledger through the documented procedure. The RUN remains authoritative.
Fill instructions sit in HTML comments and <angle-bracket> placeholders. Replace every placeholder before launch.
-->

Use this brief when the owner runs the Harness inside an autonomous loop. It carries every decision the owner can give before launch. It records which gates always stop. It tells the run how to resume after a compaction or restart. At a gate, the run stops and asks; it never improvises.

## Invocation

<!-- Fill from the owner instruction and the `System Review And Route` record. -->

| Item | Value |
| --- | --- |
| Skill to invoke | `$delivery-harness`, or the upstream skill the owner names |
| Intent | <plan-only \| plan-then-stop \| plan-then-execute \| execute-ready-plan> |
| Delivery profile | <standard \| mvp> |
| Target repository root | <absolute path> |
| Base branch | <observed remote base and full SHA, e.g. refs/remotes/origin/main> |
| Run branch | <owner-named refs/heads/<name>; never an automatic prefix> |
| Host and observed drivers | <host identity; observed provider and ordered available drivers> |

Ask before branch creation. The owner names the run branch here. The run never invents a fixed prefix or name.

## Authorization Ledger

<!-- Every row starts `no`. Change a row to `yes` only for an explicit owner decision. Fill `targets` on the same row. Copy `source` from the Owner Signature at the end of this file. -->

| Action | Authorized | Targets | Expires when | Source |
| --- | --- | --- | --- | --- |
| invoke_external_runtime | no | <runtime:<provider>> | run_complete | <owner signature line and date> |
| spawn_subagents | no | <worker:<id>> | run_complete | <owner signature line and date> |
| create_user_owned_tasks | no | <task:<id>> | run_complete | <owner signature line and date> |
| create_local_worktrees | no | <worktree:<path>> | run_complete | <owner signature line and date> |
| create_app_managed_worktrees | no | <worktree:<path>> | run_complete | <owner signature line and date> |
| create_local_branches | no | <branch:refs/heads/<exact-run-branch>> | run_complete | <owner signature line and date> |
| create_local_commits | no | <branch:refs/heads/<exact-run-branch>> | run_complete | <owner signature line and date> |
| integrate_locally | no | <branch:refs/heads/<exact-run-branch>> | run_complete | <owner signature line and date> |
| push | no | none | - | fixed: stays no for every RUN |
| archive_worker_tasks | no | <exact target, e.g. task:<id>> | run_complete | <owner signature line and date> |
| remove_worktrees | no | <worktree:<path>> | run_complete | <owner signature line and date> |
| delete_branches | no | <branch:refs/heads/<name>> | run_complete | <owner signature line and date> |

Targets use only the five prefixes: `worker:`, `task:`, `worktree:`, `branch:`, and `runtime:`. Use `*` for a dimension only when the owner explicitly authorized that dimension run-wide. `lease-worker` refuses a mission launch whose grant lists `*` in `mission_ids`, so a mission lease needs exact mission IDs.

`expires_when` is `wave_closed`, `run_complete`, or `explicit_revocation`; `run_complete` is the default. `push` stays `no` for every RUN. Publishing archive candidate A and promoting `main` are separate post-RUN actions with separate owner authorization.

## Pre-Recorded Owner Decisions

<!-- The owner answers before launch. A blank cell means the run asks at the gate. -->

| Decision | Owner value | Source step |
| --- | --- | --- |
| Delivery profile | <standard \| mvp> | product-definition Workflow step 12 (`At a Glance` row); Harness MVP Week |
| Assumptions authorized for the discovery interview | <yes \| no> | product-definition Workflow step 3 |
| Stack Decision Mode | <owner review of one coherent recommendation plus alternatives \| layer-by-layer owner selection \| explicit delegation to the skill> | product-definition Workflow step 7 |
| Direction mode | <three studies \| one recommended direction (mvp)> | ui-design Workflow step 3 |
| Design System Need Gate expectation | <required \| not_required with its reason> | ui-design Workflow step 8 |
| Publish-path list approval rule | <approve the exact list the run presents \| leave staged> | product-definition Workflow step 20 |
| Run-branch name | <refs/heads/<name>> | Harness SKILL Non-Negotiable Boundaries |
| Archive and cleanup grants | <none (default) \| exact ledger rows> | branch-promotion-contract Managed RUN Archive Before Promotion; ledger rows `archive_worker_tasks`, `remove_worktrees`, `delete_branches` |
| Reviewer route and worker route | <routes the agent policy designates> | execution-state-model Runtime Capability Axes; runtime-adapters Adapter Routing |

Under `mvp`, the Stack Decision Checkpoint and Product Definition Approval are one owner call. The direction approval folds into the one Visual Approval. Compilation runs only when the recorded Need Gate is `required`.

## Gates That Always Stop

These gates stop the run for an owner decision. A pre-recorded decision removes none of them; execution authorization is the one gate this brief can pre-record.

- Product Definition Approval, with the Stack Decision Checkpoint (product-definition Workflow steps 14 and 15).
- Direction selection, outside `mvp` (ui-design Workflow step 3).
- Visual Approval (ui-design Workflow step 7).
- Execution authorization, when this brief does not pre-record it.
- Release or publication (branch-promotion-contract).
- Any external console write, including every step in `docs/DEPLOYMENT.md` External Console Setup.
- Any deletion or overwrite of local data (development-rules Protect Local Data).

At such a gate:

1. Write the gate request with verified absolute Markdown links into the task record and chat.
2. Record the node as blocked with reason `owner_gate`.
3. End the iteration.

Never guess an owner decision. Never open a second RUN to pass the gate.

## Environment Facts

<!-- Fill each row from the readiness preflight of the current session before the first dispatch. Record observed facts; never guess. -->

| Fact | Observed value |
| --- | --- |
| Toolchain versions versus stack pins | <toolchain version; pinned version; match or gap> |
| Browser automation availability | <observed browser tool or none> |
| Console error policy | <console messages the pinned browser logs by policy, such as CSP directives; record the log> |
| Reviewer route and caps | <route; seconds <n>; turns <n>; bytes <n>> |
| Worker driver and slots | <driver; available_worker_slots <n>> |
| Test runner baseline exit codes | <command; exit 0 is PASS> |

## Stop And Resume

- Session cap: stop at <n> wall-clock hours per session. Stop at a safe boundary; first record the `Next action:` line in the mission runbook's `## Goal And Checkpoint`.
- Stall rule: three consecutive no-progress iterations end the session. Record the blocker in the Epic or task record and pause the run with `pause --source <text>`.
- On compaction or restart, the first command is `python "<delivery-harness-skill-root>/scripts/inspect_harness_run.py" --repo-root <root>`. Follow its `Next` block, then the mission runbook's `## Goal And Checkpoint` `Next action:` line.
- A `running` RUN with no run lock needs one owner decision before selection: pause, cancel, or resume. Record it with the matching `harness_transition.py` subcommand; each requires `--source`.
- When the review budget is exhausted, route the remaining defects to the Isolated Repair Protocol (`references/verification-gates.md#isolated-repair-protocol`). Never open a new RUN for them.

## Goal Text

<!-- Paste this block as the `/goal` prompt. Keep it under 4,000 characters. -->

```text
End state: <outcome> on the owner-named run branch, with docs/goal/RUN.md complete.
Verified by: the PLAN verifiers and every RUN gate, each bound to the exact head SHA.
While preserving: approved PRD, architecture, stack and UI sources; local data; the run branch.
Use: docs/goal/HARNESS_GOAL.md, docs/goal/RUN.md, and the current stage cards; they point to every rule.
Between iterations: inspect first, then act, then record; run scripts/inspect_harness_run.py before selection and follow its Next block.
Guardrails: honor every recorded cap; one writer per checkout; never nest delegation; stop at every gate that always stops.
If blocked: record the node as blocked with reason owner_gate, write the gate request with verified links, and end the iteration.
```

## Owner Signature

<!-- The `source` of every yes row copies this signature line and date verbatim. A missing signature leaves every ledger row `no`. -->

```text
Owner: <name>
Date: <YYYY-MM-DD>
Statement: I approve this brief. I authorize each yes row in its Authorization Ledger within the targets and expiry recorded on that row, for the run named in Invocation. This brief records my statements; the RUN remains authoritative.
Brief revision: <n>
```
