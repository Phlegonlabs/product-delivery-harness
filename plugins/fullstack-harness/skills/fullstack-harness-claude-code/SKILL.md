---
name: fullstack-harness-claude-code
description: "Claude Code runtime adapter for Full Stack Harness engineering. Use only when the active host is Claude Code and a large plan needs Dynamic Workflow, parent-managed worktrees, or guarded Codex execution through codex:codex-rescue. This adapter does not own shared PLAN/RUN schemas, GitHub landing, merge, deployment, or cleanup."
---

# Full-Stack Harness: Claude Code Runtime Adapter

## Load Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. Use its size gate, PLAN/RUN state, authorization ledger, verification ladder, and integration rules. Load this adapter only for a Claude Code-hosted run that needs runtime orchestration. Do not load the Codex adapter in the same parent.

This adapter selects Dynamic Workflow and cc-codex launch mechanics. Remote landing remains in `../fullstack-harness-github-landing/SKILL.md` and stays unloaded for local-only work.

## Capability Snapshot

Before the first production edit or launch, inspect the active Claude Code session:

- an observed Workflow tool proves `dynamic_workflow`;
- direct Agent tools prove `subagents` only for the declared route;
- `EnterWorktree`, current permission mode, slots, completion channel, tool-profile enforcement, and model/effort support define usable capacity;
- an installed Codex CLI or plugin directory does not prove `codex:codex-rescue` is callable.

Record observations under `runtime_adapter` independently from authorization. Prefer:

```text
dynamic_workflow + parent_managed_worktree + agent_result
-> direct subagents with one writer and explicit isolation
-> sequential parent
```

Use three as the configured write-worker maximum; the effective wave may be smaller. Never run parallel writers in `shared_checkout`.

## Claude Provider Defaults

Preserve explicit user and PLAN choices. Otherwise, for new PLAN-v4 runtime-worker nodes:

- frontend/UI implementation prefers pinned `claude-fable-5` with `high` effort;
- general-purpose and backend nodes keep Claude Code `sonnet` as the availability fallback to the core plan's Codex preference;
- routine `frontend_code` review uses `claude-fable-5` with `medium`; routine visual review uses the same model and effort;
- raise review effort only for security, migration, difficult correctness, broad architecture, or genuine visual ambiguity.

Pass non-null PLAN-selected Claude effort as `--effort`. Do not silently widen tools or substitute a rejected model or effort; revise policy and reselect.

## Launch Native Claude Dynamic Workflow

Use `subagent` + `parent_managed_worktree` + `agent_result` only with exact authorization for `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, and `create_local_commits` across the selected scope.

1. Validate PLAN/RUN and record the accepted ready wave.
2. Allocate one collision-resistant branch, lease, and exact-base worktree per mission under `.claude/worktrees/<run>-<mission>-<attempt>/`.
3. Build immutable handoffs from `../fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md`.
4. For the older flat schema-v6-or-v7 route, call `../fullstack-harness-engineering/assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js`. For PLAN-v4 graph waves, call `CLAUDE_GRAPH_WORKFLOW.template.js` through the shared bridge/guard contract.
5. Mission and read-only review profiles include `EnterWorktree`. Before repository access, every agent enters the exact existing path and verifies root, branch, and base. Review profiles omit `Edit`, `Write`, `NotebookEdit`, and `Bash`.
6. Group external/runtime waves by selected model, effort, and tool profile. Do not mix incompatible bindings in one call.
7. Do not ask for user input inside a running Workflow. Return a blocked/refinement result, let the parent resolve it, then start a later attempt.
8. Validate each `agent_result` against live worktree, branch, head, scope, and verifier facts before serial integration.

The workflow coordinates sibling mission agents and remains flat. Mission workers do not delegate, modify PLAN/RUN, integrate, push, open a PR, deploy, or clean up. If Dynamic Workflow is unavailable, use the recorded fallback rather than an untracked fan-out.

## Launch External Codex From Claude Code

Use this route only for a ready PLAN-v4/RUN-v9 write node allowed to use Codex. External Codex reviews are disabled in v1; select another allowed provider or defer.

1. Keep Claude Code as the only PLAN/RUN writer, scheduler, integration owner, and landing/deployment owner.
2. Record observed cc-codex plugin metadata as `unknown`; do not claim availability from installation alone.
3. Run `../fullstack-harness-engineering/scripts/validate_codex_wave.py --mode preflight` only when a ready node prefers or requires Codex. It must confirm exact `invoke_external_runtime` for `runtime:codex`, `spawn_subagents`, and the required pre-allocation worktree/branch grants.
4. Invoke `../fullstack-harness-engineering/assets/templates/CLAUDE_CODEX_PREFLIGHT.template.js` only with guard output. Availability requires one read-only `codex:codex-rescue` Agent using `--wait --fresh` in an isolated Agent worktree and the exact success marker.
5. For writes, create a pending worker record with null worktree/branch fields, rerun the guard in wave mode, then invoke `CLAUDE_CODEX_GRAPH_WORKFLOW.template.js`. It starts one fresh Agent per mission with `isolation: "worktree"`; the Codex worker does not delegate.
6. Require exactly one `HARNESS_NODE_RESULT_V1_BEGIN` / `HARNESS_NODE_RESULT_V1_END` candidate. Missing, duplicate, malformed, or identity-mismatched markers are not success.
7. Independently verify the returned absolute path, branch/ref, head, common Git directory, fixed-base ancestry, exact changed-file set, scope, commits, and verifiers. Record runtime-assigned allocation only after those checks, then integrate passing commits serially.

The outer Workflow task/run ID is the runtime evidence. cc-codex does not expose an inner Codex thread ID, so leave it null. Do not poll private cc-codex state or resume a prior thread; every retry is a new graph attempt with `--fresh`.

## Failure And Fallback

One failed node does not cancel passing siblings. Preserve failed and cancelled worktree evidence; never reset or delete it automatically. Fall back only to a PLAN-allowed provider, fewer workers, or the recorded sequential route, and record the evidence for that decision.
