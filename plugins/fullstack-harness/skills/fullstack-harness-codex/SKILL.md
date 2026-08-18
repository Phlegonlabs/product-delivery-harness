---
name: fullstack-harness-codex
description: "Launch PLAN-v5/RUN-v10 Harness nodes from a Codex host. Use only after the shared core classifies work as large and selects Codex orchestration. This adapter probes Codex app-task and direct-subagent capability, maps PLAN model options, and launches exact authorized nodes; it does not own shared state, review, integration, handoff, or cleanup."
---

# Full-Stack Harness: Codex Adapter

## Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. Use this adapter only for a Codex-hosted large run. It selects launch mechanics and grants no authorization.

A PLAN node is selectable here when its `allowed_providers` includes `codex`. `preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Codex host.

## Capability Snapshot

Before the first launch, observe all eight Codex surfaces: `app_project_list`, `app_thread_create`, `app_thread_read`, `app_thread_message`, `app_thread_wait`, `app_managed_worktree`, `direct_subagent_spawn`, and `direct_agent_result`. Search the current Codex tool surface before marking lazy-loaded thread tools unavailable.

For RUN-v10, record each surface under `runtime_adapter` as `available`, `unavailable`, or `unobserved` with evidence. Ready/running state contains no required `unobserved` surface. Derive `app_threads` only from all six app surfaces and `subagents` only from both direct-agent surfaces.

Prefer the strongest observed and authorized route:

```text
app_task + app_managed_worktree + thread_poll
-> direct subagents with parent-owned isolation
-> sequential_parent
```

Never run parallel writers in `shared_checkout`.

## Provider Defaults

Preserve explicit user and PLAN choices. Otherwise:

- general and backend implementation: Codex `gpt-5.6-terra`, `high`;
- frontend/UI implementation: Codex `gpt-5.6-sol`, `high`;
- routine deterministic `backend_code` review: Codex `gpt-5.6-terra`, `medium`;
- routine frontend, visual, or integration review: Codex `gpt-5.6-sol`, `medium`;
- final unified-head review: Codex `gpt-5.6-sol`, `xhigh`;
- bounded exploration, documentation/API research, and test/log analysis: the fastest suitable model at `low` or `medium`.

Raise effort only for security, migration, difficult correctness/debugging, broad architecture, or genuine ambiguity. Pass PLAN-selected `model` and `thinking` without silent substitution.

## Dispatch

Use each `dispatchable_nodes[].required_actions` exactly.

### Mission app tasks

1. Resolve the current Codex project once.
2. Allocate lease, identity, exact-base app-managed worktree, and authorized branch/ref. Verify repository, HEAD, branch/ref, and clean `git status --porcelain`.
3. Render `WORKER_GOAL.template.md` with the mission, write/deny scope, skills, verifier, permission boundary, completion channel, result-contract path, Codex worker contract, and effective `AGENTS.override.md` / `AGENTS.md` repository context paths. Keep `AGENTS.md` context discovery enabled; do not inject `CLAUDE.md` as Codex instructions. RUN-v10 forbids task-local child agents.
4. Create one top-level left-sidebar app task per selected mission. Do not replace a requested app task with a coordinator subagent.
5. Poll with bounded backoff: 15 seconds, doubling to five minutes. After 30 minutes without status change, record a stalled attempt and stop polling that task.
6. Observe live Git head, diff, scope, commits, and ancestry. Validate the result before the core's exact-head review and integration sequence.

Do not stop after printing a non-empty app-task wave; consume every accepted dispatch entry.

### Read-only reviews

A review app task needs `create_user_owned_tasks`; a direct-subagent review needs `spawn_subagents`. It needs no write worktree, branch, or commit grant. Bind it to one exact SHA, record its outcome, and invalidate the PASS when that SHA changes.

## Flat Parent-Owned Delegation

Codex explorers, mission workers, and reviewers are sibling nodes dispatched by the Harness parent. No worker or reviewer spawns another agent. After serial integration, dispatch fresh read-only reviewers against the exact unified integration SHA, then run one planned broad final validation on the fixed candidate.

## Context And Handoff

Use the shared Repository Context Contract and the Serialized Same-Repository Host Handoff in `../fullstack-harness-engineering/references/execution-state-model.md`. This adapter adds no alternate state or handoff rules.

## Provider Boundary

There is no mechanism in this adapter to invoke Claude Code. Do not probe for a Claude Code CLI, binary, or plugin as a substitute route. Report an ineligible node as `runtime_unavailable`; before readiness, a node with no planned host is a blocking gap unless the user accepts later deferral.

## Failure

Preserve failed, cancelled, stalled, dirty, and partial task/worktree evidence. Use a recorded fallback or fewer workers only when capability, isolation, permission, dependency, conflict, or resource evidence requires it. Never replace explicitly requested independent app tasks with direct subagents or sequential parent execution.
