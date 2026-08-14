---
name: fullstack-harness-pi
description: "Pi runtime adapter for Full Stack Harness engineering. Use only when the active host is Pi and a large PLAN needs Pi's installed subagent roles and model configuration. It executes only pi-provider nodes, preserves parent-owned worktrees and authorization, and leaves model selection to Pi."
---

# Full-Stack Harness Pi Adapter

## Load Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. Load this adapter only after `System Review And Route` classifies the work as large and the active host is Pi. Do not also load the Codex or Claude Code adapter.

A PLAN node is selectable here when its `allowed_providers` includes `pi`. `preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Pi host. This adapter executes no `codex`-only or `claude_code`-only node and never invokes either runtime as a bridge.

## Capability Snapshot

Observe the current Pi session before dispatch. A configured package, CLI binary, or agent file alone does not prove a usable worker surface.

- Record `provider: pi`.
- Record `subagents` only when the current Pi session exposes the installed subagent workflow and can return a terminal child result.
- Always record `sequential_parent` as the fallback.
- For delegated mission writes, use `worker_runtime: subagent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result` or `report_file`.
- If the subagent surface is absent or incomplete, keep the graph plan-backed and use the core's real `sequential_parent` route. Do not imitate delegation.

## Preserve Pi Role And Model Routing

Pi owns role-to-model selection. Preserve its installed agent definitions, model scope, reasoning settings, and fallback chain.

- Do not copy the Codex or Claude Code per-node model defaults into a Pi node.
- For `pi` provider options, omit `provider_options.pi` or use `{"model": null, "reasoning_effort": null}`. A non-null Harness reasoning effort is unsupported for Pi.
- Route frontend or UI implementation to Pi's installed `frontend_designer` role.
- Route backend, API, data, infrastructure, or general implementation to Pi's installed `worker` role.
- Route exact-head read-only review to Pi's installed `reviewer` role.
- Use `scout` or `researcher` only for an explicitly bounded read-only lane. They are not implementation writers.
- Do not invent a missing role or model. Record the actual resolved role, model, fallback, run id, and terminal status in evidence when Pi reports them.

Harness controls mission scope and acceptance; Pi controls which configured model fulfills the selected role.

## Dispatch Selected Nodes

Follow each `dispatchable_nodes[].required_actions` exactly. Never infer extra authorization.

1. The parent creates the mission lease, branch, and parent-managed worktree from the recorded `batch_base_sha` before launch. It verifies the expected repository, assigned branch/ref, exact base HEAD, and empty `git status --porcelain` before dispatch.
2. Render `WORKER_GOAL.template.md` with the selected node's immutable runtime binding, exact worktree path, file ownership from bounded `write_scope`, required skills, verifier, and stop conditions.
3. Use Pi's installed subagent workflow entrypoint. Give every run a stable key, explicit agent role, exact task, and the allocated worktree as `cwd`. Keep Pi context discovery enabled: never pass `--no-context-files` or `-nc`. Supply the Pi worker contract and Pi's effective per-directory context selection in native priority order: `AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`. Pi loads only the first match in each directory, so when `AGENTS.md` exists do not also inject `CLAUDE.md`. Require the child to read every selected path before any repository action.
4. Forked subagent context requires a persisted Pi parent session. With `--no-session`, launch a fresh child context instead; do not retry the same forked mode after Pi rejects it.
5. Use one foreground run for a bounded mission, or wait for every asynchronous run to reach a terminal state before closing the wave. Never present a final result while Pi jobs remain active.
6. One mission has one writer. Parallel writes require separate parent-managed worktrees and non-overlapping scopes; otherwise run them sequentially.
7. A Pi child must not delegate again. It returns `WORKER_RESULT` or `REFINEMENT_REQUEST`; the Harness parent observes the returned head and diff, validates scope and verifier evidence, and owns integration.
8. After implementation closes, dispatch graph review nodes to the read-only `reviewer` role against the exact returned SHA. After all passing mission heads integrate serially, dispatch fresh `reviewer` runs against the exact unified integration SHA. Neither mission writers nor pre-integration review results are reused. A role's internal fallback does not weaken either exact-head PASS gate.
9. After the fresh integration reviewers pass, run the one planned broad final validation against the fixed candidate SHA. Focused task, worker, and integration checks remain part of normal execution.

The parent may use Pi's workflow script to call a single role or a bounded set of independent roles. All roles are parent-owned siblings and none may delegate. The workflow is transport only: PLAN/RUN, authorization, worktree allocation, review, integration, and final verification remain owned by the Harness parent.

## Serialized Same-Repository Host Handoff

Host A must close the active wave before Host B continues: `RUN.active_wave.status` is neither `active` nor `proposed`. The `active_wave` object remains part of RUN; absence is not a handoff signal. Preserve canonical PLAN/RUN and graph state, then review the current exact head SHA before selecting another wave.

Host B re-probes the current Pi runtime. If that review returns `fix_required`, route the repair to the original host; the old review is invalid. Cross-machine handoff is unsupported until a future schema adds portable repository and state identity. This adapter is a host-native executor, not an in-session bridge.

## Failure Handling

- Record a rejected or unavailable configured model as a Pi launch failure. Do not silently pin another Harness model; Pi's declared fallback policy decides whether another model is tried.
- Preserve failed node, lease, run id, and evidence. Replan or use `sequential_parent` only through the shared core.
- Stop when the requested Pi role is missing and role choice would change the user's intended result.
