---
name: fullstack-harness-pi
description: "Launch PLAN-v6/RUN-v11 Harness nodes from a Pi host. Use only after the shared core classifies work as large and selects Pi orchestration. This adapter preserves Pi's installed role, model, and fallback routing while the Harness parent owns scope, worktrees, validation, and integration."
---

# Full-Stack Harness: Pi Adapter

## Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. Use this adapter only for a Pi-hosted large run. It selects launch mechanics and grants no authorization.

A PLAN node is selectable here when its `allowed_providers` includes `pi`. `preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Pi host. This adapter never invokes Codex or Claude Code as a bridge.

## Capability Snapshot

Observe the current Pi session and record the result under `runtime_adapter` independently from authorization. A package, CLI binary, or agent file does not prove a usable worker surface.

Record `pi --version` and the loaded Harness release in `runtime_adapter.version_gate`, then follow `../fullstack-harness-engineering/references/runtime-upgrades.md`. A `compatible_old` session may finish its already-active wave but cannot start the next wave. Update Pi with its native updater and a packaged Harness source with Pi's package updater only after an explicit user instruction; then mark `restart_required`, start a fresh Pi session, and re-probe. Never overwrite standalone skills or change installed roles, models, fallbacks, credentials, or unrelated packages as part of this gate.

- Record `subagents` only when the session exposes a role-aware Pi launch surface and terminal child results. The launch call must select the installed role by name and leave its base model unset. If a generic `agents.spawn` surface accepts `runner` and `model` but lacks a Pi role selector, it does not satisfy this capability; use `sequential_parent` instead of simulating a role with a name, prompt, tool list, or model override.
- Always record `sequential_parent` as fallback.
- Use `worker_runtime: subagent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result` or `report_file` for delegated writes.
- If the worker surface is incomplete, use the core's real `sequential_parent`; do not imitate delegation.

## Preserve Pi Routing

Pi owns role-to-model and fallback selection. Preserve installed agent definitions, model scope, and fallback order; PLAN may lower or raise reasoning effort per node without replacing the role's configured primary model.

- Keep `provider_options.pi.model` null. Set `reasoning_effort` per node when the plan has a latency tier; null preserves the installed role default.
- Once the host provider is Pi, ignore the shared Codex and Claude Code task-shape model preferences. Omit `model` from the Pi launch call; never translate a null Pi binding into a model search term or a provider bridge.
- Frontend/UI implementation uses the installed `frontend_designer` role.
- Backend, data, infrastructure, and general implementation use `worker`.
- Exact-head read-only review uses `reviewer`.
- `scout` and `researcher` are bounded read-only lanes.
- Use `medium` for bounded discovery, mechanical repair, and routine deterministic review; `high` for general implementation and risk-bearing mission review; and `xhigh` only for a justified high-risk or unified final synthesis. `max` and `ultra` require an explicit user choice or recorded exceptional risk.
- At launch, resolve the installed role's primary model and fallback order, keep that base routing, and apply the non-null PLAN effort through Pi's per-run thinking suffix. If the installed provider rejects the effort, block and revise the node; never silently fall back to a stronger effort.
- A rejected primary model may use only the installed role's declared fallback order. Do not manually respawn the node on another model or provider, even when that substitute is available to the parent.
- Record the actual resolved role, model, effort, fallback, run id, and terminal status. Never invent a missing role or silently pin a Harness model.

## Dispatch

Follow every `dispatchable_nodes[].required_actions` exactly. Never infer extra authorization.

1. Allocate lease, authorized branch, and exact-base parent-managed worktree. Verify repository, branch/ref, HEAD, and clean `git status --porcelain`.
2. Render `WORKER_GOAL.template.md` as a self-contained bounded context packet with the current mission slice, exact scope, skills, verifier, permission boundary, result-contract path, ordered repository context source paths, Pi worker contract, and Pi's effective per-directory context selection: `AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`. Refer to PLAN/RUN by identity and path instead of copying either manifest. Keep Pi context discovery enabled; never pass `--no-context-files` or `-nc`. When `AGENTS.md` exists do not also inject `CLAUDE.md`.
3. Launch `worker`, `frontend_designer`, `reviewer`, `scout`, and `researcher` through the role-aware Pi surface with explicit `context: "fresh"`, a stable key, the assigned worktree as `cwd`, and no base-model argument. A generic `agents.spawn` call without a Pi role selector is not a valid adapter launch. Fork only an `oracle` when inherited decision history is essential and record that reason. A mission must fit one bounded fresh-child slice whose fixed overhead stays small against its useful work; split it before readiness when it does not.
4. One mission has one writer. Parallel writes require separate worktrees and non-overlapping scopes.
5. A Pi child must not delegate again. It returns the shared result contract; the parent validates live Git facts.
6. Subscribe or block on terminal child/status events instead of fixed-interval polling. Process each terminal result immediately and stream its ready pre-integration review while sibling workers continue; close the wave only after every selected worker result is validated. Before the host deadline, request a checkpoint after the current tool returns when a slice is not converging; do not use timeout as the checkpoint. A missing process plus a dirty or advanced worktree is interrupted evidence, not `worker_running` proof.
7. Dispatch one fresh `reviewer` per applicable surface against each returned exact head. Give it only the exact SHA, scoped diff/paths, applicable acceptance rows, required evidence, and unresolved findings; refer to PLAN/RUN by path and identity instead of copying their full manifests. Allow only one repair re-review. After serial integration, dispatch only the planned fresh `reviewer` runs against the exact unified integration SHA; that unified-head pass is the final synthesis, so do not add another same-scope review while the SHA is unchanged. Then run one planned broad final validation.

## Context And Handoff

Use the shared Repository Context Contract and the Serialized Same-Repository Host Handoff in `../fullstack-harness-engineering/references/execution-state-model.md`, plus `../fullstack-harness-engineering/references/runtime-performance.md` and `../fullstack-harness-engineering/references/runtime-upgrades.md`. Record Pi queue, context, dispatch, wait, execute, review, verify, and integrate events in RUN-v11 `runtime_metrics` when applicable. This adapter adds no alternate state or handoff rules. It adds no alternate upgrade rules.

## Failure

Preserve failed node, lease, run id, dirty files, commits, and session evidence. A rejected model follows Pi's configured fallback policy without a parent-selected replacement. Use `sequential_parent` only through the shared core. Stop when the required role is missing, the launch surface cannot select it, or changing roles would change the intended result.
