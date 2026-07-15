# Multi-Thread Orchestration Research Notes

Last reviewed: 2026-07-14. These notes capture capability facts behind the skill's orchestration guidance. Re-check the linked official sources before changing behavior because Codex configuration, app behavior, and defaults can change independently of this skill.

Do not hard-code a local `codex-cli` version into portable guidance. Record the observed version in RUN evidence only when a specific behavior depends on it.

## Durable Decision

Represent orchestration as three independent capability axes:

```text
worker_runtime: parent | subagent | app_task
workspace_mode: shared_checkout | parent_managed_worktree | app_managed_worktree
completion_channel: agent_result | thread_poll | report_file | user_relay
```

This replaces the older single mode enum. A mode label hid important differences: a subagent is parent-owned while an app task is user-owned; a worktree can be parent- or platform-managed; and completion can arrive as a result, poll, report file, or user relay.

The portable default remains serialized writes in one checkout. Read-only work may fan out. Parallel writes require isolated eligible worktrees, complete file/runtime resource claims, an observable completion channel, a fixed committed base SHA, and explicit action-specific authorization.

The skill uses a parent-to-mission-writer shape and keeps task implementation sequential within each mission. An app-task mission writer may now use bounded direct subagents for independent read-only exploration, research, test analysis, and review. This adds useful nesting without creating a second writer or changing the mission DAG.

## Codex Subagents

Official Codex subagent documentation establishes these current facts:

- The main agent coordinates child agents, follow-up instructions, waits, and results.
- Subagents can be requested directly and can also be triggered by applicable skills or `AGENTS.md` instructions when the active configuration permits delegation. “Explicit request only” is not a universal platform invariant.
- `agents.max_depth` defaults to `1` and the Codex platform value is configurable. Independently of that platform flexibility, this harness deliberately applies a stricter depth-one maximum to task-local app-worker helpers so they cannot create grandchildren.
- `agents.max_threads` defaults to `6`, but the effective concurrency available to a task can be lower because of runtime configuration, active workers, product limits, or this harness's stricter budget.
- Parent-owned subagent results can return to the parent execution flow. Independently created app tasks are a different primitive and must not be assumed to have the same result channel.
- Codex app tasks can delegate independent work after a direct request or when applicable skill/`AGENTS.md` instructions request it. Merely enabling `features.multi_agent` does not force delegation; the task prompt still needs an applicable delegation rule.
- Official guidance recommends starting with read-heavy exploration, tests, triage, and summarization, and being more careful with concurrent write-heavy work.
- Subagents inherit the parent task's active permission mode and available tools. They can still surface approvals for tool-specific or sandbox-controlled actions; nested delegation is not an approval bypass.
- The desktop permission mode is selected beneath the composer and is inherited by subagents. `Approve for me` routes eligible requests to automatic review but does not change the sandbox boundary.
- Codex treats sandboxing and approvals as separate controls. `workspace-write` with `on-request` can still prompt for linked-worktree Git metadata outside the runtime workspace, package caches, blocked network destinations, or local/private bindings. Non-interactive full access is `danger-full-access` with approval policy `never`.
- Permission profiles can express a narrower reusable boundary across workspace roots, filesystem paths, network domains, local bindings, and Unix sockets. Existing tasks do not retroactively gain a newly selected boundary; observe the effective mode at each worker launch or restart.

Therefore the capability gate observes actual worker slots and completion behavior instead of inferring them from a version string or default configuration.

## Codex App Tasks And Worktrees

Official Codex app worktree documentation establishes these current constraints:

- App-created worktrees commonly start at detached `HEAD`. Work that must survive the task/worktree lifecycle needs a durable branch or ref, created only when authorized.
- Task-scoped managed worktrees are common, but permanent worktrees can host multiple tasks. Do not enforce “exactly one task per worktree” as a universal invariant.
- `.worktreeinclude` can copy required ignored local files into a managed worktree. It is not a substitute for checking secrets or environment isolation.
- The app keeps a recent set of managed worktrees (documented default: 15) and can remove older managed worktrees according to platform retention behavior.

An authorization such as `remove_worktrees: false` controls harness-initiated cleanup only. It cannot promise that the platform will retain an app-managed worktree. Record `platform_lifecycle`, create a durable branch/ref early when needed, and do not leave unique verified work reachable only through detached `HEAD`.

Worktrees isolate files. They do not isolate ports, processes, databases, migration streams, queues, buckets, test identities, feature-flag namespaces, or external sandboxes.

## Local And GitHub Code Review

Official Codex review documentation establishes these current facts:

- Local `/review` runs in read-only mode and can review uncommitted changes or compare the current branch with a base branch. It is the pre-push review gate, not proof that GitHub reviewed the pushed head.
- GitHub review requires the repository to be connected to Codex Cloud with Code review enabled. Automatic reviews can review each new PR opened for review; `@codex review` is the manual trigger.
- Repository `AGENTS.md` files may define `## Review guidelines` that Codex uses during GitHub review.
- Codex GitHub review reports high-signal P0/P1 findings. Ordinary CI, repository rules, and required status checks remain separate controls.

The harness therefore records local diff review separately from GitHub review and binds GitHub CI/review evidence to the exact PR head SHA. A later push invalidates earlier evidence even if the PR number is unchanged. The parent should request review again after the new checks pass.

## Completion And Event Notifications

A generic skill must not promise automatic cross-task callbacks:

- Parent-owned subagents may deliver `agent_result` through the orchestration runtime.
- A separate task may be observable through a product-provided thread polling tool.
- A durable report file can support handoff but still requires Git/runtime verification.
- Where no programmatic channel exists, the user may need to relay completion.

True event-driven Codex integration is an App Server client capability. App Server exposes notifications such as turn completion and thread status changes; a client must subscribe to and handle those events. The presence of this skill alone does not install that client or create an event channel.

## Capability Combinations

| Worker runtime | Typical workspace | Valid completion examples | Write concurrency rule |
|---|---|---|---|
| `parent` | `shared_checkout` | `agent_result` | one write mission at a time |
| `subagent` | `shared_checkout` | `agent_result` | serialize writes; read-only fan-out is allowed |
| `subagent` | `parent_managed_worktree` | `agent_result` or `report_file` | parallel writes only after full fan-out gate |
| `app_task` | `app_managed_worktree` | `thread_poll`, `report_file`, or `user_relay` | parallel writes only after full fan-out gate and lifecycle acknowledgement |

Inside the last row, the app task may coordinate up to three direct read-only helpers when the RUN policy and `spawn_subagents` authorization permit it. Those helpers return `agent_result` to the app task; they are not additional app tasks or write workers.

These are examples, not an exhaustive compatibility table. The parent must prove that the chosen combination exists in the current environment. If a completion channel or workspace primitive is missing, fall back to sequential execution.

## Re-Verification Checklist

Before changing orchestration guidance, re-check:

- Codex subagent configuration keys, current defaults, delegation behavior, result/failure delivery, and effective thread/depth limits.
- Codex app worktree detached-HEAD behavior, permanent versus task-scoped worktrees, `.worktreeinclude`, and retention policy.
- Available thread/task tools in the current product surface and whether they support polling, messaging, creation, or only navigation.
- App Server event names and client subscription semantics before promising event-driven integration.
- Codex best-practice warnings for concurrent work on the same files and the current recommended use of worktrees.
- Any other runtime's worker nesting, isolation, completion, and cleanup behavior before mapping it to these axes.

Record environment-specific observations in RUN evidence. Keep this reference about portable capability semantics.

## Rationale

1. Parallel writes in one checkout remain unsafe: declared scopes do not isolate lockfiles, build caches, generated files, dev servers, or local databases.
2. Worktree isolation is necessary but insufficient for full-stack fan-out because runtime resources still conflict.
3. Parent ownership of PLAN/RUN avoids multiple writers racing on orchestration state.
4. Worker verification and integration verification are separate facts; only integrated results unlock dependencies.
5. Orthogonal capability axes allow the same skill to degrade safely across CLI, app, subagent, and App Server environments without inventing unsupported automation.

## Sources

- Codex subagents: https://learn.chatgpt.com/docs/agent-configuration/subagents
- Codex app worktrees: https://developers.openai.com/codex/app/worktrees
- Codex App Server: https://developers.openai.com/codex/app-server
- Codex best practices: https://developers.openai.com/codex/learn/best-practices
- Codex changelog: https://developers.openai.com/codex/changelog
- Codex sandbox and approvals: https://learn.chatgpt.com/docs/sandboxing
- Codex permission profiles: https://learn.chatgpt.com/docs/permissions
- Codex local code review: https://developers.openai.com/codex/app/code-review
- Codex GitHub code review: https://developers.openai.com/codex/cloud/code-review
- Codex AGENTS.md guidance: https://developers.openai.com/codex/guides/agents-md
- Claude Code agent overview: https://code.claude.com/docs/en/agents
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
