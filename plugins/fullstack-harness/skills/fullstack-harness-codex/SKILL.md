---
name: fullstack-harness-codex
description: "Codex runtime adapter for Full Stack Harness engineering. Use only when the active host is Codex and a large plan needs app tasks, app-managed worktrees, or direct subagents. This adapter is host-native only: it executes exclusively codex-provider PLAN nodes and does not own PLAN/RUN schemas, shared verification, or cleanup."
---

# Full-Stack Harness: Codex Runtime Adapter

## Load Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. Use its size gate, PLAN/RUN state, authorization ledger, verification ladder, and integration rules. Load this adapter only for a Codex-hosted run that actually needs runtime orchestration. Do not load the Claude Code adapter in the same parent.

This adapter selects launch mechanics; it grants no authorization.

## Capability Snapshot

Before the first edit or worker launch, inspect the current Codex session:

- project/thread create, read, message, and completion polling surfaces prove `app_threads`;
- direct child-agent tools prove `subagents`;
- the current permission mode, worktree isolation, Git metadata reachability, slots, completion channel, temp/cache/network needs, and model options define usable capacity.

Codex app task tools may be discoverable but not loaded into the initial tool list. Before recording `app_threads` as unavailable, search the current Codex tool surface for project listing, top-level task/thread creation, follow-up messaging, and bounded thread waiting. A direct subagent is not a substitute for a user-owned top-level Codex task: the task has its own conversation in the left sidebar and its own app-managed worktree.

Record observations under `runtime_adapter` independently from authorization. Choose the strongest observed and authorized route:

```text
app_task + app_managed_worktree + thread_poll
-> direct subagents with one writer and explicit isolation
-> sequential parent
```

Do not cap the configured write-worker maximum at a small fixed number; set it generously high per the core's Default Runtime And Wave Policy, and let observed worker slots, isolation capacity, and the dependency-ready conflict-free frontier size determine the effective wave — it may still end up smaller. Never run parallel writers in `shared_checkout`.

## Codex Provider Defaults

Preserve an explicit user or PLAN choice. Otherwise, for new PLAN-v5 runtime-worker nodes:

- for general-purpose nodes and backend implementation, prefer Codex `gpt-5.6-terra` with `high` reasoning;
- frontend/UI implementation uses Codex `gpt-5.6-sol` with `high` reasoning;
- routine deterministic `backend_code` review uses Codex `gpt-5.6-terra` with `medium`;
- routine `frontend_code` and visual review use Codex `gpt-5.6-sol` with `medium` reasoning;
- the run's final review — the final synthesis pass over the integration head — uses Codex `gpt-5.6-sol` with `xhigh` reasoning by default, not as an exception;
- for bounded mechanical edits, discovery, or inexpensive preflight work (codebase exploration, documentation/API research, test/log analysis), prefer Codex's fastest/cheapest available model with `low` or `medium` reasoning instead of the general-purpose/implementation defaults above;
- raise a mission node's effort to `xhigh`, or a routine review node's effort above `medium`, only for security, migration, difficult correctness, difficult debugging, broad architecture, or genuine ambiguity.

Pass non-null PLAN-selected values to task creation as `model` and `thinking`. Never silently substitute a rejected model, effort, permission mode, or tool profile; revise the affected runtime policy and reselect. The review defaults above are the declared host substitution for the core's Claude Code review defaults on a codex-only host — a recorded policy choice, not a silent substitution.

## Launch Selected Codex App Tasks

Use this route only with exact authorization for `spawn_subagents`, `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, and `create_local_commits` across the selected run, missions, and targets. Integration remains separate. When the user requests independent Codex tasks or worktrees, preserve that outer topology: create one top-level Codex task per selected mission/worktree before any task-local Multi-agent work. Never collapse those missions into direct subagents of the coordinator. `../fullstack-harness-engineering/references/worktree-thread-orchestration.md` states the topology rules this procedure has to preserve.

Do not stop after printing a non-empty app-task wave. After validating PLAN/RUN, selecting the ready frontier, and recording the accepted wave, consume every `dispatchable_nodes` entry:

1. Resolve the current Codex project once.
2. Allocate the worker and lease identity, then recheck pre-allocation `*` grants only for app-assigned task/worktree identities; recheck every already-known branch, commit, mission, and worker target exactly.
3. Build the initial prompt from `../fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md`, including plan digest, immutable base, scope, tasks, resources, verifiers, permission boundary, the mission's `required_skills` list, and nested policy. Tell the app task directly to use its authorized multi-agent policy.
4. Create one top-level app-managed worktree task per selected mission from the recorded current integration branch/ref resolved from target-repository instructions; when the repository defines no other model that ref is the run's own `codex/<short-name>` branch, cut from the recorded current default-branch SHA. Each task is an independent conversation visible in the Codex left sidebar. Record the returned thread ID or queued client-thread ID; never invent it from a mission name and never replace this step with coordinator-owned subagents.
5. Poll with bounded backoff: start at 15 seconds, double the interval after each unchanged poll up to a 5-minute ceiling, and treat a thread as stalled after 30 minutes with no observed status change — record the thread as blocked in RUN with the stall evidence and stop polling that thread instead of polling indefinitely. The stalled mission's attempt counts against its `max_attempts`; the parent either retries within that budget or takes over the worktree itself. This poll-timeout budget is independent from a mission's `max_attempts` retry count and from the worker-level three-consecutive-no-progress-iteration guardrail (`../fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md`). Send necessary follow-up through the thread message surface, and preserve terminal, blocked, interrupted, and partial results.
6. Observe the actual Git common directory, path, branch/ref, base, head, changed files, and commit ancestry. Require one task-local read-only reviewer to review the proposed diff after implementation and bind its result to the final worktree head. If the task could not run that reviewer, the parent must run an equivalent read-only review before integration.
7. Send pre-integration blocking findings back to the original task/thread. Repair them inside that task's existing worktree and branch, run its focused verifier on a changed head, then re-arm the same review node and review the new head again. Do not create a repair mission or replacement worktree for this loop. Only then may the parent serially integrate the mission into the resolved target-repository integration branch.

App-managed worktrees may start detached. When durable handoff is required, create the authorized branch/ref early. The task is the sole writer in its worktree. Never assume a managed worktree also isolates ports, databases, queues, caches, secrets, or third-party sandboxes.

## Launch Selected Codex Read-Only Review Nodes

A `verifier`/review node (`backend_code`, `frontend_code`, or `visual` review) never requests `create_app_managed_worktrees`, `create_local_branches`, or `create_local_commits` — per `../fullstack-harness-engineering/scripts/select_ready_nodes.py`, a read-only review node's required actions are only `create_user_owned_tasks` (for the `app_threads` driver) and `spawn_subagents`. Do not route it through the mission worktree-allocation steps above.

1. Resolve the exact SHA under review (the mission or integration head named by the accepted wave). Do not allocate a new worktree, branch, or commit for this node.
2. Create one app task (or direct subagent, if that route is selected) scoped read-only to that exact SHA, using the reviewer's role/task description from the PLAN node and its own `model`/`thinking` values.
3. Poll it with the same bounded-backoff and stall rules as a mission task above.
4. Record `review_head_sha`, decision, and findings in RUN. A PASS binds only to that exact SHA; a later local integration or push invalidates it per `../fullstack-harness-engineering/references/verification-gates.md`.

## Nested Read-Only Subagents

A mission is `non-trivial` when its task list spans more than one file or module boundary, or changes business logic rather than pure configuration, copy, or a mechanical rename/move; a single mechanical edit confined to one file is `trivial` and may report an allowed triviality reason instead of launching a child.

Every non-trivial app-task mission gets a depth-one policy capped at three direct read-only children when current capability and `spawn_subagents` authorization are both proven. Eligible pre-edit lanes are codebase exploration, documentation/API research, and test/log analysis. After implementation, one direct child must perform the final proposed-diff review on the current worktree head. This is the inner layer: each left-sidebar task coordinates its own children after the outer task-per-worktree wave exists.

When child capability is unknown, launch a no-edit handshake, poll it, record the result, and send an enabled or disabled policy before implementation. Enable it only when the allowed roles include `reviewer`. With an enabled policy, the post-edit reviewer is mandatory for a non-trivial mission; `partial` or `unavailable` activity without a completed exact-head PASS reviewer cannot return `worker_passed`. Children never write, run mutating generators or shared-state services, spawn further agents, edit PLAN/RUN, create Git objects, integrate, or clean up. The app task reconciles their evidence and reports the reviewer's exact head, decision, findings, and `subagent_activity`. After validating that result, the parent copies the completed reviewer child into the worker's canonical `nested_review_evidence`; the mission cannot transition to integration without that retained exact-head PASS record. If the handshake proves the child runtime or reviewer role unavailable, assign a disabled policy before implementation. A trivial or disabled-policy mission, and a graph-backed direct worker with no nested policy, still needs an equivalent parent-owned read-only review recorded as a terminal exact-head `review_workers[]` PASS before the mission may transition to integration.

## Provider Boundary

This adapter is host-native only. A PLAN node is selectable here when its `allowed_providers` includes `codex`. `preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Codex host when `codex` is allowed. There is no mechanism in this adapter to invoke Claude Code, and no fallback that lets a `claude_code`-only node execute under Codex.

When the ready frontier includes a node whose `allowed_providers` does not include `codex`, do not attempt to launch it and do not probe for a Claude Code CLI, binary, or plugin as a substitute route. Record that node as deferred with the selector's `runtime_unavailable` reason, leave it out of the accepted wave, and report it so a run hosted by an allowed provider can pick it up. This is expected steady state for a mixed-provider PLAN running under a single-host session, not an error to work around — but only if the user acknowledged that deferral at Plan Readiness. Before readiness passes, verify every `runtime_worker` node is executable on some host this delivery will actually use; a node no planned host can run is a blocking readiness gap, not steady state.

## Failure And Fallback

Use the recorded fallback driver or fewer workers only when capability, isolation, permission, dependency, conflict, or resource evidence requires it. Record the reason. Preserve failed or cancelled task/worktree evidence; never reset or remove it automatically. If no isolated route remains, use one sequential parent writer and continue from canonical PLAN/RUN state. An explicit request for independent left-sidebar Codex tasks is different: do not replace it with direct subagents or sequential parent execution. Report the missing task/thread capability and stop at that boundary.
