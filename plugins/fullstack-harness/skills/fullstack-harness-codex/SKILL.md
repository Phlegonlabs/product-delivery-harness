---
name: fullstack-harness-codex
description: "Codex runtime adapter for Full Stack Harness engineering. Use only when the active host is Codex and a large plan needs app tasks, app-managed worktrees, or direct subagents. This adapter is host-native only: it executes exclusively codex-provider PLAN nodes and does not own PLAN/RUN schemas, shared verification, GitHub landing, merge, deployment, or cleanup."
---

# Full-Stack Harness: Codex Runtime Adapter

## Load Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. Use its size gate, PLAN/RUN state, authorization ledger, verification ladder, and integration rules. Load this adapter only for a Codex-hosted run that actually needs runtime orchestration. Do not load the Claude Code adapter in the same parent.

This adapter selects launch mechanics; it grants no authorization. GitHub CI, PR review, merge, and remote landing belong to `../fullstack-harness-github-landing/SKILL.md` and remain unloaded for local-only work.

## Capability Snapshot

Before the first production edit or worker launch, inspect the current Codex session:

- project/thread create, read, message, and completion polling surfaces prove `app_threads`;
- direct child-agent tools prove `subagents`;
- the current permission mode, worktree isolation, Git metadata reachability, slots, completion channel, temp/cache/network needs, and model options define usable capacity.

Record observations under `runtime_adapter` independently from authorization. Choose the strongest observed and authorized route:

```text
app_task + app_managed_worktree + thread_poll
-> direct subagents with one writer and explicit isolation
-> sequential parent
```

Use three as the configured write-worker maximum; the effective wave may be smaller. Never run parallel writers in `shared_checkout`.

## Codex Provider Defaults

Preserve an explicit user or PLAN choice. Otherwise, for new PLAN-v4 runtime-worker nodes:

By default, prefer Codex `gpt-5.6-terra` with `xhigh` reasoning for general-purpose nodes and backend implementation.

- for general-purpose nodes and backend implementation, prefer Codex `gpt-5.6-terra` with `xhigh` reasoning;
- frontend/UI implementation uses Codex `gpt-5.6-sol` with `xhigh` as the Codex option;
- routine deterministic `backend_code` review uses Codex `gpt-5.6-terra` with `medium`;
- raise review effort only for security, migration, difficult correctness, broad architecture, or genuine ambiguity.

Pass non-null PLAN-selected values to task creation as `model` and `thinking`. Never silently substitute a rejected model, effort, permission mode, or tool profile; revise the affected runtime policy and reselect.

## Launch Selected Codex App Tasks

Use this route only with exact authorization for `spawn_subagents`, `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, and `create_local_commits` across the selected run, missions, and targets. Integration remains separate.

Do not stop after printing a non-empty app-task wave. After validating PLAN/RUN, selecting the ready frontier, and recording the accepted wave, consume every `launch_directives` entry:

1. Resolve the current Codex project once.
2. Allocate the worker and lease identity, then recheck pre-allocation `*` grants only for app-assigned task/worktree identities; recheck every already-known branch, commit, mission, and worker target exactly.
3. Build the initial prompt from `../fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md`, including plan digest, immutable base, scope, tasks, resources, verifiers, permission boundary, and nested policy.
4. Create one app-managed worktree task per selected mission from the recorded integration branch/ref. Record the returned thread ID or queued client-thread ID; never invent it from a mission name.
5. Poll with bounded backoff, send necessary follow-up through the thread message surface, and preserve terminal, blocked, interrupted, and partial results.
6. Observe the actual Git common directory, path, branch/ref, base, head, changed files, and commit ancestry. Validate before serial parent integration.

App-managed worktrees may start detached. When durable handoff is required, create the authorized branch/ref early. The task is the sole writer in its worktree. Never assume a managed worktree also isolates ports, databases, queues, caches, secrets, or third-party sandboxes.

## Nested Read-Only Subagents

Every non-trivial app-task mission gets a depth-one policy capped at three direct read-only children when current capability and `spawn_subagents` authorization are both proven. Eligible lanes are codebase exploration, documentation/API research, test/log analysis, and post-edit proposed-diff review.

When child capability is unknown, launch a no-production-edit handshake, poll it, record the result, and send an enabled or disabled policy before implementation. With an enabled policy, at least one useful child must run unless the result records an allowed triviality/capability reason. Children never write, run mutating generators or shared-state services, spawn further agents, edit PLAN/RUN, create Git objects, integrate, land, deploy, or clean up. The app task reconciles their evidence and reports `subagent_activity`.

## Provider Boundary

This adapter is host-native only. A PLAN node is selectable here only when its `allowed_providers` includes `codex` and, when the node declares a `preferred_provider`, the current host still satisfies it. There is no mechanism in this adapter to invoke Claude Code, and no fallback that lets a `claude_code`-only node execute under Codex.

When the ready frontier includes a node whose required or preferred provider is `claude_code` and does not also allow `codex`, do not attempt to launch it and do not probe for a Claude Code CLI, binary, or plugin as a substitute route. Record that node as blocked on provider mismatch, leave it out of the accepted wave, and report it so a Claude-Code-hosted run can pick it up. This is expected steady state for a mixed-provider PLAN running under a single-host session, not an error to work around.

## Failure And Fallback

Use the recorded fallback provider or fewer workers only when capability, isolation, permission, dependency, conflict, or resource evidence requires it. Record the reason. Preserve failed or cancelled task/worktree evidence; never reset or remove it automatically. If no isolated route remains, use one sequential parent writer and continue from canonical PLAN/RUN state.
