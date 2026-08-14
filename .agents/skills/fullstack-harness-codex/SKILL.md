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

For a RUN-v10 adapter with `provider: codex` and `detection_source: observed`, record the machine-validatable `capability_probe` before Plan Readiness. Probe all eight surfaces independently: `app_project_list`, `app_thread_create`, `app_thread_read`, `app_thread_message`, `app_thread_wait`, `app_managed_worktree`, `direct_subagent_spawn`, and `direct_agent_result`. Each entry has exactly `status` (`available`, `unavailable`, or `unobserved`) plus non-empty `evidence`. A ready/running run may contain no `unobserved` entry. The validator derives `app_threads` only when all six app surfaces are available and `subagents` only when both direct-agent surfaces are available, then requires `available_drivers` to match that result in Codex priority order. If App Threads is proven, omitting it is a blocking `capability_snapshot_mismatch`, not a permitted downgrade.

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

Use only the action keys in each accepted `dispatchable_nodes[].required_actions`, rechecking their exact targets before launch. An app-task mission uses its outer task/worktree actions and never receives `spawn_subagents`; RUN-v10 forbids task-local child agents. A direct parent-owned subagent route still needs its own `spawn_subagents` action. Worktree, branch, commit, and integration actions remain separate. When the user requests independent Codex tasks or worktrees, preserve that outer topology: create one top-level Codex task per selected mission/worktree. Never collapse those missions into children of another worker. `../fullstack-harness-engineering/references/worktree-thread-orchestration.md` states the topology rules this procedure has to preserve.

Do not stop after printing a non-empty app-task wave. After validating PLAN/RUN, selecting the ready frontier, and recording the accepted wave, consume every `dispatchable_nodes` entry:

1. Resolve the current Codex project once.
2. Allocate the worker and lease identity, then recheck pre-allocation `*` grants only for app-assigned task/worktree identities; recheck every already-known branch, commit, mission, and worker target exactly.
3. Build the initial prompt from `../fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md`, including plan digest, immutable base, file ownership, tasks, resources, verifiers, permission boundary, the Codex worker contract, the ordered effective `AGENTS.override.md`/`AGENTS.md` repository context paths, the mission's `required_skills` list, and the disabled nested policy. Keep automatic `AGENTS.md` context discovery enabled, do not inject `CLAUDE.md` as Codex instructions, and state that the task must not delegate.
4. Create one top-level app-managed worktree task per selected mission from the recorded current integration branch/ref resolved from target-repository instructions; when the repository defines no other model that ref is the run's own `codex/<short-name>` branch, cut from the recorded current default-branch SHA. Before dispatch, verify the task worktree belongs to the expected repository, has the assigned branch/ref and exact base HEAD, and has empty `git status --porcelain`. Each task is an independent conversation visible in the Codex left sidebar. Record the returned thread ID or queued client-thread ID; never invent it from a mission name and never replace this step with coordinator-owned subagents.
5. Poll with bounded backoff: start at 15 seconds, double the interval after each unchanged poll up to a 5-minute ceiling, and treat a thread as stalled after 30 minutes with no observed status change — record the thread as blocked in RUN with the stall evidence and stop polling that thread instead of polling indefinitely. The stalled mission's attempt counts against its `max_attempts`; the parent either retries within that budget or takes over the worktree itself. This poll-timeout budget is independent from a mission's `max_attempts` retry count and from the worker-level three-consecutive-no-progress-iteration guardrail (`../fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md`). Send necessary follow-up through the thread message surface, and preserve terminal, blocked, interrupted, and partial results.
6. Observe the actual Git common directory, path, branch/ref, base, head, changed files, and commit ancestry. The task launches no helper. The parent/review graph must produce and record the terminal exact-head review PASS before integration.
7. Send pre-integration blocking findings back to the original task/thread. Repair them inside that task's existing worktree and branch, run its focused verifier on a changed head, then re-arm the same review node and review the new head again. Do not create a repair mission or replacement worktree for this loop. Only then may the parent serially integrate the mission into the resolved target-repository integration branch.

App-managed worktrees may start detached. When durable handoff is required, create the authorized branch/ref early. The task is the sole writer in its worktree. Never assume a managed worktree also isolates ports, databases, queues, caches, secrets, or third-party sandboxes.

## Launch Selected Codex Read-Only Review Nodes

A `verifier`/review node (`backend_code`, `frontend_code`, or `visual` review) never requests `create_app_managed_worktrees`, `create_local_branches`, or `create_local_commits`. Follow the review node's own `dispatchable_nodes[].required_actions`: an app-thread review needs `create_user_owned_tasks`, while a direct-subagent review needs `spawn_subagents`. Do not route it through the mission worktree-allocation steps above or require both actions by default.

1. Resolve the exact SHA under review (the mission or integration head named by the accepted wave). Do not allocate a new worktree, branch, or commit for this node.
2. Create one app task (or direct subagent, if that route is selected) scoped read-only to that exact SHA, using the reviewer's role/task description from the PLAN node and its own `model`/`thinking` values.
3. Poll it with the same bounded-backoff and stall rules as a mission task above.
4. Record `review_head_sha`, decision, and findings in RUN. A PASS binds only to that exact SHA; a later local integration or push invalidates it per `../fullstack-harness-engineering/references/verification-gates.md`.

## Flat Parent-Owned Delegation

Codex app tasks, direct mission workers, explorers, and reviewers are sibling nodes dispatched by the Harness parent. No worker or reviewer spawns another agent. Read-only exploration may run in parallel before writing when scopes and resources permit; exact-head mission review and fresh unified-head review are separate parent-owned nodes. RUN-v10 uses an omitted or disabled `nested_subagent_policy`, and every worker reports nested activity as not applicable.

After all review-passing mission heads integrate serially, dispatch fresh read-only reviewers against the exact unified integration SHA. Do not reuse mission-worker identity or a pre-integration PASS as the integration review. When those reviewers pass, run the one planned broad final validation against the fixed candidate SHA.

## Serialized Same-Repository Host Handoff

A host handoff is a serialized boundary in one repository, not an in-session bridge. Host A must close the active wave before handing off; Host B may start only when `RUN.active_wave.status` is neither `active` nor `proposed`. The `active_wave` object remains part of RUN; do not treat an absent object as proof that handoff is safe. Preserve the canonical PLAN/RUN and graph state, including `run_id`, `plan_id`, `plan_revision`, `plan_digest_sha256`, `graph_revision`, the integration branch, and the current exact head SHA. Do not reconstruct state from chat or an uncommitted patch.

Host B re-probes the current Codex runtime and authorization surface, reopens the canonical state, and performs the required exact-head review before selecting a new wave. If that review returns `fix_required`, route the repair back to Host A's existing mission/worktree ownership; the old review is invalid as soon as the repair changes the head, and Host B must review the new exact SHA before continuing. There is no automatic cross-host invocation. Cross-machine handoff is unsupported until a future schema defines portable repository and state identity.

## Provider Boundary

This adapter is host-native only. A PLAN node is selectable here when its `allowed_providers` includes `codex`. `preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Codex host when `codex` is allowed. There is no mechanism in this adapter to invoke Claude Code, and no fallback that lets a `claude_code`-only node execute under Codex.

When the ready frontier includes a node whose `allowed_providers` does not include `codex`, do not attempt to launch it and do not probe for a Claude Code CLI, binary, or plugin as a substitute route. Record that node as deferred with the selector's `runtime_unavailable` reason, leave it out of the accepted wave, and report it so a run hosted by an allowed provider can pick it up. This is expected steady state for a mixed-provider PLAN running under a single-host session, not an error to work around — but only if the user acknowledged that deferral at Plan Readiness. Before readiness passes, verify every `runtime_worker` node is executable on some host this delivery will actually use; a node no planned host can run is a blocking readiness gap, not steady state.

## Failure And Fallback

Use the recorded fallback driver or fewer workers only when capability, isolation, permission, dependency, conflict, or resource evidence requires it. Record the reason. Preserve failed or cancelled task/worktree evidence; never reset or remove it automatically. If no isolated route remains, use one sequential parent writer and continue from canonical PLAN/RUN state. An explicit request for independent left-sidebar Codex tasks is different: do not replace it with direct subagents or sequential parent execution. Report the missing task/thread capability and stop at that boundary.
