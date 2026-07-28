---
name: fullstack-harness-claude-code
description: "Claude Code runtime adapter for Full Stack Harness engineering. Use only when the active host is Claude Code and a large plan needs Dynamic Workflow, parent-managed worktrees, or direct subagents. This adapter is host-native only: it executes exclusively claude_code-provider PLAN nodes and does not own shared PLAN/RUN schemas, shared verification, GitHub landing, merge, deployment, or cleanup."
---

# Full-Stack Harness: Claude Code Runtime Adapter

## Load Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. Use its size gate, PLAN/RUN state, authorization ledger, verification ladder, and integration rules. Load this adapter only for a Claude Code-hosted run that needs runtime orchestration. Do not load the Codex adapter in the same parent.

This adapter selects Dynamic Workflow launch mechanics. Remote landing remains in `../fullstack-harness-github-landing/SKILL.md` and stays unloaded for local-only work.

## Capability Snapshot

Before the first production edit or launch, inspect the active Claude Code session:

- an observed Workflow tool proves `dynamic_workflow`;
- direct Agent tools prove `subagents` only for the declared route;
- `EnterWorktree`, current permission mode, slots, completion channel, tool-profile enforcement, and model/effort support define usable capacity.

Record observations under `runtime_adapter` independently from authorization. Prefer:

```text
dynamic_workflow + parent_managed_worktree + agent_result
-> direct subagents with one writer and explicit isolation
-> sequential parent
```

Do not cap the configured write-worker maximum at a small fixed number; set it generously high per the core's Default Runtime And Wave Policy, and let observed worker slots, isolation capacity, and the dependency-ready conflict-free frontier size determine the effective wave — it may still end up smaller. Never run parallel writers in `shared_checkout`.

## Claude Provider Defaults

Reserve the parent's own top-tier model — whichever premium model opened the current session, such as `claude-fable-5` — for the parent's own coordination and planning. Do not assign it to a delegated node by default. Preserve explicit user and PLAN choices. Otherwise, for new PLAN-v5 runtime-worker nodes, a delegated implementation or review node defaults to Claude Code `sonnet`; a node doing bounded, mechanical, or purely read-only work (exploration, research, test/log analysis, discovery, inexpensive preflight checks) instead defaults to `haiku`, per the core's Runtime Binding point 6:

- frontend/UI implementation, general-purpose, and backend mission nodes use `sonnet` with `high` effort;
- routine `frontend_code`, `backend_code`, and visual review use `sonnet` with `medium` effort;
- raise a delegated node's effort to `xhigh` — while keeping its model at `sonnet` — only for security, migration, difficult correctness, broad architecture, or genuine visual ambiguity;
- raise a delegated node's model above `sonnet` only on an explicit user request naming that specific node;
- bounded/mechanical/discovery/read-only nodes use `haiku` with `low` or `medium` reasoning effort instead of `sonnet` — this is a lower tier than the `sonnet` default above, not a request to raise a node's model above `sonnet`, so it does not need the explicit-user-request bullet above.

Pass each node's PLAN-selected `model` (and non-null `reasoning_effort` as `effort`) from its `runtime_binding` directly into that node's own `agent()` call inside the Workflow script, or into the `model`/`effort` parameters of a direct `Agent` tool call. Do not silently widen tools or substitute a rejected model or effort; revise policy and reselect.

## Launch Native Claude Dynamic Workflow

Use `subagent` + `parent_managed_worktree` + `agent_result` only with exact authorization for `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, and `create_local_commits` across the selected scope.

1. Validate PLAN/RUN and record the accepted ready wave.
2. Allocate one collision-resistant branch, lease, and exact-base worktree per mission under `.claude/worktrees/<run>-<mission>-<attempt>/`.
3. Build immutable handoffs from `../fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md`.
4. Route by wave composition, not schema version alone: for a single-role, all-mission wave (no review node, one tool profile), call `../fullstack-harness-engineering/assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js`. For a typed wave that mixes mission and review nodes, or that must enforce per-node tool profiles or `EnterWorktree`, call `../fullstack-harness-engineering/assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js`. The flat script covers single-role all-mission waves in supported schemas; a typed graph does not by itself require the graph script unless the wave mixes roles or needs per-node tool enforcement.
5. In the typed-graph route (`CLAUDE_GRAPH_WORKFLOW.template.js`), mission and review prompts instruct every agent to call `EnterWorktree` on its exact existing path and verify root, branch, and base before repository access, and instruct review agents not to edit, commit, or run mutating tools. The profile is a label on the node, not a tool allowlist — the child inherits the parent's tools, so record this as a runtime limitation rather than claiming permission-level prevention. In the flat route (`CLAUDE_DYNAMIC_WORKFLOW.template.js`), there is no `EnterWorktree` tool or allowlist enforcement — the mission prompt instructs the agent in plain English to enter the existing worktree path and verify root, branch, and base before any repository action, and it returns blocked if it cannot bind (see `../fullstack-harness-engineering/references/worktree-thread-orchestration.md`).
6. Group waves by tool profile only. Pass each node's own `model`/`reasoning_effort` (from its `runtime_binding`) into that node's `agent()` call — a single Workflow call may freely mix models and reasoning efforts across nodes, since each spawned agent call selects its own. Do not mix tool profiles (mission-write vs. read-only review) in one call.
7. Do not ask for user input inside a running Workflow. Return a blocked/refinement result, let the parent resolve it, then start a later attempt.
8. Validate each `agent_result` against live worktree, branch, head, scope, and verifier facts before serial integration.

The workflow coordinates sibling mission agents and remains flat. Mission workers do not delegate, modify PLAN/RUN, integrate, push, open a PR, deploy, or clean up. If Dynamic Workflow is unavailable, use the recorded fallback rather than an untracked fan-out.

## Provider Boundary

This adapter is host-native only. A PLAN node is selectable here when its `allowed_providers` includes `claude_code`. `preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Claude Code host when `claude_code` is allowed. There is no mechanism in this adapter to invoke Codex, and no fallback that lets a `codex`-only node execute under Claude Code.

When the ready frontier includes a node whose `allowed_providers` does not include `claude_code`, do not attempt to launch it and do not probe for an installed Codex CLI or plugin as a substitute route. Record that node as blocked on provider mismatch, leave it out of the accepted wave, and report it so a run hosted by an allowed provider can pick it up. This is expected steady state for a mixed-provider PLAN running under a single-host session, not an error to work around.

## Failure And Fallback

One failed node does not cancel passing siblings. Preserve failed and cancelled worktree evidence; never reset or delete it automatically. Fall back only to another available native driver (direct subagents, then sequential parent), fewer workers, or the recorded sequential route, and record the evidence for that decision.
