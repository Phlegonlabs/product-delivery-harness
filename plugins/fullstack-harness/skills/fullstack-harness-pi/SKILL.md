---
name: fullstack-harness-pi
description: "Launch PLAN-v5/RUN-v10 Harness nodes from a Pi host. Use only after the shared core classifies work as large and selects Pi orchestration. This adapter preserves Pi's installed role, model, and fallback routing while the Harness parent owns scope, worktrees, validation, and integration."
---

# Full-Stack Harness: Pi Adapter

## Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. Use this adapter only for a Pi-hosted large run. It selects launch mechanics and grants no authorization.

A PLAN node is selectable here when its `allowed_providers` includes `pi`. `preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Pi host. This adapter never invokes Codex or Claude Code as a bridge.

## Capability Snapshot

Observe the current Pi session and record the result under `runtime_adapter` independently from authorization. A package, CLI binary, or agent file does not prove a usable worker surface.

- Record `subagents` only when the session exposes the installed workflow and terminal child results.
- Always record `sequential_parent` as fallback.
- Use `worker_runtime: subagent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result` or `report_file` for delegated writes.
- If the worker surface is incomplete, use the core's real `sequential_parent`; do not imitate delegation.

## Preserve Pi Routing

Pi owns role-to-model selection. Preserve installed agent definitions, model scope, reasoning, and fallback order.

- Omit `provider_options.pi` or use `{"model": null, "reasoning_effort": null}`.
- Frontend/UI implementation uses the installed `frontend_designer` role.
- Backend, data, infrastructure, and general implementation use `worker`.
- Exact-head read-only review uses `reviewer`.
- `scout` and `researcher` are bounded read-only lanes.
- Record the actual resolved role, model, fallback, run id, and terminal status. Never invent a missing role or silently pin a Harness model.

## Dispatch

Follow every `dispatchable_nodes[].required_actions` exactly. Never infer extra authorization.

1. Allocate lease, authorized branch, and exact-base parent-managed worktree. Verify repository, branch/ref, HEAD, and clean `git status --porcelain`.
2. Render `WORKER_GOAL.template.md` with the node, scope, skills, verifier, permission boundary, result-contract path, Pi worker contract, and Pi's effective per-directory context selection: `AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`. Keep Pi context discovery enabled; never pass `--no-context-files` or `-nc`. When `AGENTS.md` exists do not also inject `CLAUDE.md`.
3. Launch the installed role with a stable key and the assigned worktree as `cwd`. Forked subagent context requires a persisted Pi parent session. With `--no-session`, launch a fresh child context instead.
4. One mission has one writer. Parallel writes require separate worktrees and non-overlapping scopes.
5. A Pi child must not delegate again. It returns the shared result contract; the parent validates live Git facts.
6. Wait for every asynchronous run to reach a terminal state before closing the wave. A missing process plus a dirty or advanced worktree is interrupted evidence, not `worker_running` proof.
7. Dispatch `reviewer` against each returned exact head. After serial integration, dispatch fresh `reviewer` runs against the exact unified integration SHA, then run one planned broad final validation.

## Context And Handoff

Use the shared Repository Context Contract and the Serialized Same-Repository Host Handoff in `../fullstack-harness-engineering/references/execution-state-model.md`. This adapter adds no alternate state or handoff rules.

## Failure

Preserve failed node, lease, run id, dirty files, commits, and session evidence. A rejected model follows Pi's configured fallback policy. Use `sequential_parent` only through the shared core. Stop when the required role is missing and changing roles would change the intended result.
