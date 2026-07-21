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

Use three as the configured write-worker maximum; the effective wave may be smaller. Never run parallel writers in `shared_checkout`.

## Claude Provider Defaults

Reserve the parent's own top-tier model — whichever model opened the current session (for example `claude-fable-5` or `claude-opus-4-8`) — for the parent's own coordination and planning. Do not assign it to a delegated node by default. Preserve explicit user and PLAN choices. Otherwise, for new PLAN-v4 runtime-worker nodes, every delegated node — mission (including frontend/UI implementation) and review alike — defaults to Claude Code `sonnet`:

- frontend/UI implementation, general-purpose, and backend mission nodes use `sonnet` with `high` effort;
- routine `frontend_code`, `backend_code`, and visual review use `sonnet` with `medium` effort;
- raise a delegated node's effort to `xhigh` — while keeping its model at `sonnet` — only for security, migration, difficult correctness, broad architecture, or genuine visual ambiguity;
- raise a delegated node's model above `sonnet` only on an explicit user request naming that specific node.

Pass each node's PLAN-selected `model` (and non-null `reasoning_effort` as `effort`) from its `runtime_binding` directly into that node's own `agent()` call inside the Workflow script, or into the `model`/`effort` parameters of a direct `Agent` tool call. Do not silently widen tools or substitute a rejected model or effort; revise policy and reselect.

## Launch Native Claude Dynamic Workflow

Use `subagent` + `parent_managed_worktree` + `agent_result` only with exact authorization for `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, and `create_local_commits` across the selected scope.

1. Validate PLAN/RUN and record the accepted ready wave.
2. Allocate one collision-resistant branch, lease, and exact-base worktree per mission under `.claude/worktrees/<run>-<mission>-<attempt>/`.
3. Build immutable handoffs from `../fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md`.
4. Route by wave composition, not schema version alone: for a single-role, all-mission wave (no review node, one tool profile), call `../fullstack-harness-engineering/assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js`. For a typed wave that mixes mission and review nodes, or that must enforce per-node tool profiles or `EnterWorktree`, call `../fullstack-harness-engineering/assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js`. The flat script covers schema v6 through v9 when the wave is single-role; a PLAN-v4 graph wave does not by itself require the graph script.
5. Mission and read-only review profiles include `EnterWorktree`. Before repository access, every agent enters the exact existing path and verifies root, branch, and base. Review profiles omit `Edit`, `Write`, `NotebookEdit`, and `Bash`.
6. Group waves by tool profile only. Pass each node's own `model`/`reasoning_effort` (from its `runtime_binding`) into that node's `agent()` call — a single Workflow call may freely mix models and reasoning efforts across nodes, since each spawned agent call selects its own. Do not mix tool profiles (mission-write vs. read-only review) in one call.
7. Do not ask for user input inside a running Workflow. Return a blocked/refinement result, let the parent resolve it, then start a later attempt.
8. Validate each `agent_result` against live worktree, branch, head, scope, and verifier facts before serial integration.

The workflow coordinates sibling mission agents and remains flat. Mission workers do not delegate, modify PLAN/RUN, integrate, push, open a PR, deploy, or clean up. If Dynamic Workflow is unavailable, use the recorded fallback rather than an untracked fan-out.

## Provider Boundary

This adapter is host-native only. A PLAN node is selectable here only when its `allowed_providers` includes `claude_code` and, when the node declares a `preferred_provider`, the current host still satisfies it. There is no mechanism in this adapter to invoke Codex, and no fallback that lets a `codex`-only node execute under Claude Code.

When the ready frontier includes a node whose required or preferred provider is `codex` and does not also allow `claude_code`, do not attempt to launch it and do not probe for an installed Codex CLI or plugin as a substitute route. Record that node as blocked on provider mismatch, leave it out of the accepted wave, and report it so a Codex-hosted run can pick it up. This is expected steady state for a mixed-provider PLAN running under a single-host session, not an error to work around.

## Failure And Fallback

One failed node does not cancel passing siblings. Preserve failed and cancelled worktree evidence; never reset or delete it automatically. Fall back only to another available native driver (direct subagents, then sequential parent), fewer workers, or the recorded sequential route, and record the evidence for that decision.
