---
name: fullstack-harness-claude-code
description: "Launch PLAN-v5/RUN-v10 Harness nodes from a Claude Code host. Use only after the shared core classifies work as large and selects Claude orchestration. This adapter probes Dynamic Workflow and direct Agent capability, maps PLAN model options, and launches exact authorized nodes; it does not own shared state, review, integration, handoff, or cleanup."
---

# Full-Stack Harness: Claude Code Adapter

## Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. Use this adapter only for a Claude Code-hosted large run. It selects launch mechanics and grants no authorization.

A PLAN node is selectable here when its `allowed_providers` includes `claude_code`. `preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Claude Code host.

## Capability Snapshot

Observe Workflow, direct Agent tools, `EnterWorktree`, permission mode, slots, completion channel, tool-profile enforcement, and model/effort support. Record the result under `runtime_adapter` independently from authorization.

Prefer:

```text
dynamic_workflow + parent_managed_worktree + agent_result
-> direct subagents with parent-owned isolation
-> sequential_parent
```

Never run parallel writers in `shared_checkout`.

## Provider Defaults

Reserve the parent's premium model for the parent's own coordination and planning. Preserve explicit user and PLAN choices. Otherwise:

- implementation: `sonnet`, `high`;
- routine frontend, backend, visual, and integration review: `sonnet`, `medium`;
- final unified-head review: `sonnet`, `xhigh`;
- bounded mechanical, exploration, research, and test/log work: `haiku`, `low` or `medium`.

Raise delegated effort to `xhigh` only for security, migration, difficult correctness/debugging, broad architecture, or genuine ambiguity. Raise a delegated model above `sonnet` only when the user explicitly names that node. Pass PLAN-selected `model` and `reasoning_effort` as `model` and `effort` without silent substitution.

## Dispatch

Follow every `dispatchable_nodes[].required_actions` exactly. Never infer extra authorization.

1. Validate PLAN/RUN and record the accepted wave.
2. Allocate one exact-base parent-managed worktree and authorized branch per write mission. Verify repository, branch/ref, HEAD, and clean `git status --porcelain`.
3. Render `WORKER_GOAL.template.md` with the node, scope, skills, verifier, permission boundary, result-contract path, Claude Code worker contract, effective `CLAUDE.md` repository context paths, and shared `AGENTS.md` governance paths. Keep automatic context discovery enabled. Do not apply Codex or Pi worker mechanics.
4. Partition the accepted frontier into homogeneous `tool_profile` groups. Each group gets its own bounded call. Never put a `mission_write` node beside a `code_review_readonly` or `visual_review_readonly` node.
5. Use `CLAUDE_GRAPH_WORKFLOW.template.js` for any group containing review nodes or for a mixed original frontier. Use `CLAUDE_DYNAMIC_WORKFLOW.template.js` only for an originally all-write, single-profile mission group.
6. A `tool_profile` is a prompt/result contract, not permission-level tool removal. Review nodes inherit host tools and must be validated as read-only.
7. Do not ask for user input inside Workflow. Return a blocked/refinement result and let the parent resolve it.
8. Validate each result against live worktree, branch, head, scope, commits, and verifier evidence.

The workflow contains flat parent-owned siblings. Workers and reviewers do not delegate, edit PLAN/RUN, integrate, push, or clean up. After serial integration, dispatch fresh read-only reviewers against the exact unified integration SHA, then run one planned broad final validation.

## Context And Handoff

Use the shared Repository Context Contract and the Serialized Same-Repository Host Handoff in `../fullstack-harness-engineering/references/execution-state-model.md`. This adapter adds no alternate state or handoff rules.

## Provider Boundary

There is no mechanism in this adapter to invoke Codex. Do not probe for an installed Codex CLI or plugin as a substitute route. Report an ineligible node as `runtime_unavailable`; before readiness, a node with no planned host is a blocking gap unless the user accepts later deferral.

## Failure

One failed node does not cancel passing siblings. Preserve failed, cancelled, dirty, and partial worktree evidence. Fall back only to another observed native driver, fewer workers, or the recorded `sequential_parent` route, and record why.
