# Multi-Thread Orchestration Research Notes

Last reviewed: 2026-07-19. These notes capture capability facts behind the skill's orchestration guidance. Re-check the linked official sources and the current local CLI and plugin surfaces before changing behavior because Codex and Claude Code configuration, product behavior, and defaults can change independently of this skill.

Do not hard-code a local `codex-cli` version into portable guidance. Record the observed version in RUN evidence only when a specific behavior depends on it.

## Durable Decision

Represent orchestration as three independent capability axes:

```text
worker_runtime: parent | subagent | app_task
workspace_mode: shared_checkout | parent_managed_worktree | app_managed_worktree
completion_channel: agent_result | thread_poll | report_file | user_relay
```

This replaces the older single mode enum. A mode label hid important differences: a subagent is parent-owned while an app task is user-owned; a worktree can be parent- or platform-managed; and completion can arrive as a result, poll, report file, or user relay.

Schema v6 adds a small runtime adapter beside those axes. It records `provider`, observed `available_drivers`, and `detection_source`. The selector uses a deterministic provider route: Codex prefers app threads, Claude Code prefers Dynamic Workflow, both fall back to direct subagents when observed, and every provider has sequential parent execution as the final fallback. Provider routing does not replace authorization, isolation, or completion-channel checks.

The portable default favors an isolated worktree per mission over shared-checkout serialization even with no real parallelism in play, because it lets a mission implement and get verified independently before one controlled merge into the primary checkout's own base branch (`landing.base_branch` — commonly `main`) — see `execution-state-model.md`'s compact RUN-only paragraph for the exact default and its fallback. Read-only work may fan out freely; parallel writes additionally require complete file/runtime resource claims, an observable completion channel, a fixed committed base SHA, and explicit action-specific authorization.

Before any planner, scheduler, worker-capability scan, or external-runtime preflight, the skill uses a two-way project-size gate. Small work stays in the current parent with no PLAN/RUN or delegation by default. Large work enters managed planning and defaults every mission to its own worktree; scheduler fan-out beyond one mission at a time additionally requires at least two dependency-ready nonconflicting missions. Size means coordination scope and blast radius, not a raw file or line count. If direct work grows, checkpoint completed work and plan only the remainder.

For plan-backed multi-mission execution, runtime detection is now proactive and deterministic selection is the default immediately after Plan Readiness, so a missing launch grant produces one bundled request and reselection rather than a false claim that the preferred driver is unavailable — see `SKILL.md`'s Default Runtime And Wave Policy for the exact write-worker maximum and request/reselection mechanics. Shared-checkout writes remain serialized.

The skill uses a parent-to-mission-writer shape and keeps task implementation sequential within each mission. An app-task mission writer may now use bounded direct subagents for independent read-only exploration, research, test analysis, and review. This adds useful nesting without creating a second writer or changing the mission DAG.

The selector now emits deterministic, tool-agnostic launch directives for selected missions. It remains read-only. In a Codex app session that exposes project lookup plus thread create/read/message tools, the parent consumes those directives after accepting the wave: it creates one app-managed worktree thread per selected mission, polls completion, and validates results. This model-driven tool loop is the portable in-app launcher. A separate App Server client is needed only for event-driven orchestration outside the interactive parent task.

In Claude Code with Dynamic Workflow available, the selector also emits one wave-level launch bundle. The parent allocates mission branches/worktrees first, then runs a flat JavaScript workflow that starts sibling mission agents and returns structured result candidates. The workflow is an adapter over the same mission, authorization, result, and integration gates; it is not a second planning system.

Schema v8 adds a typed graph with strictly host-native provider binding. The host provider is the session actually running PLAN/RUN: Codex or Claude Code, never both. A ready node is eligible on the current host exactly when its `allowed_providers` includes that host. `preferred_provider` is advisory ordering among allowed hosts and never blocks an otherwise allowed current host; there is no cross-host preflight, no bridged process, and no declared fallback that lets one host launch the other. When a ready node's allowed providers do not include the current host, the selector records it as blocked on provider mismatch rather than probing or launching the other runtime. This is a deliberate simplification over an earlier design that let a Codex parent bridge into a separate Claude Code process, and let a Claude Code parent forward a request to an installed Codex agent: both cross-host routes added a second process boundary, a second identity-verification surface, and a second place for stale or ambiguous state to hide, without changing the underlying single-PLAN/RUN-parent invariant.

The current Codex app task creation surface accepts an explicit model and reasoning effort per task. Claude Code's Workflow tool accepts a model/effort override per spawned agent call, so Dynamic Workflow siblings need not inherit the outer invocation's model. The portable graph therefore stores provider-specific model options in PLAN, emits them in the runtime binding, and passes each node's own model/effort into that node's own launch call — a Codex app task at creation time, a Claude Dynamic Workflow node inside its `agent()` call. One same-host wave groups only by tool profile; it may freely mix models and reasoning efforts across its nodes. It does not hard-code a Codex model catalog because the destination host validates that evolving catalog at launch.

## Claude Code Dynamic Workflow

Official Claude Code documentation establishes these current facts:

- Dynamic Workflow requires Claude Code 2.1.154 or later. Saved workflow files live in `.claude/workflows` and are plain JavaScript.
- Workflow scripts coordinate agents through `agent()` and `pipeline()`. The script itself does not receive general filesystem or shell tools; spawned agents perform repository work through their allowed tools.
- Dynamic Workflow has no mid-run user input. Human approval or contract refinement must end the current workflow and continue in a later workflow after the parent updates canonical state.
- Pause and resume are session-scoped. A workflow can resume only from the same Claude Code session, so durable Harness state still belongs in PLAN/RUN and Git rather than in workflow memory.
- Spawned workflow agents run with `acceptEdits` and inherit the parent session's tool allowlist. A workflow is not an authorization or permission bypass.
- Since Claude Code v2.1.172, subagents can spawn nested subagents up to a fixed depth of five. The Harness v6 Dynamic Workflow adapter deliberately uses a stricter flat shape and omits the nested helper policy so worker budget, lease ownership, and the sole mission writer remain explicit.
- Agents can use worktree isolation. The Harness keeps parent-managed worktree allocation so exact branch/worktree actions remain visible in its existing authorization ledger and every mission starts from the same recorded base.
- Documented concurrency and per-run agent limits are product ceilings, not Harness budgets. Observe current capacity and keep the configured Harness worker maximum instead of hard-coding those ceilings.

The workflow template returns a structured array of complete `WORKER_RESULT` or `REFINEMENT_REQUEST` objects keyed internally by mission ID. The parent still verifies leases, base/head ancestry, actual paths, verifier evidence, and current Git state before integration. Claude Code's `Workflow` tool accepts the asset through `scriptPath` and the accepted wave through structured `args`; reusable named commands live under `.claude/workflows/`, and creating one remains a planned project write.

## Codex Subagents

Official Codex subagent documentation establishes these current facts:

- The main agent coordinates child agents, follow-up instructions, waits, and results.
- Subagents can be requested directly and can also be triggered by applicable skills or `AGENTS.md` instructions when the active configuration permits delegation. “Explicit request only” is not a universal platform invariant.
- `agents.max_depth` defaults to `1` and the Codex platform value is configurable. Independently of that platform flexibility, this harness deliberately applies a stricter depth-one maximum to task-local app-worker helpers so they cannot create grandchildren.
- `agents.max_threads` defaults to `6`, but the effective concurrency available to a task can be lower because of runtime configuration, active workers, product limits, or this harness's stricter budget.
- Parent-owned subagent results can return to the parent execution flow. Independently created app tasks are a different primitive and must not be assumed to have the same result channel.
- Codex app tasks can delegate independent work after a direct request or when applicable skill/`AGENTS.md` instructions request it. Merely enabling `features.multi_agent` does not force delegation; the task prompt still needs an applicable delegation rule.
- A non-trivial app-task worker can therefore be required by the harness skill and its initial prompt to start bounded subagents. The requirement is still subject to observed capability, inherited permissions, thread limits, and explicit `spawn_subagents` authorization.
- Official guidance recommends starting with read-heavy exploration, tests, triage, and summarization, and being more careful with concurrent write-heavy work.
- Subagents inherit the parent task's active permission mode and available tools. They can still surface approvals for tool-specific or sandbox-controlled actions; nested delegation is not an approval bypass.
- The desktop permission mode is selected beneath the composer and is inherited by subagents. `Approve for me` routes eligible requests to automatic review but does not change the sandbox boundary.
- Codex treats sandboxing and approvals as separate controls. `workspace-write` with `on-request` can still prompt for linked-worktree Git metadata outside the runtime workspace, package caches, blocked network destinations, or local/private bindings. Non-interactive full access is `danger-full-access` with approval policy `never`.
- Permission profiles can express a narrower reusable boundary across workspace roots, filesystem paths, network domains, local bindings, and Unix sockets. Existing tasks do not retroactively gain a newly selected boundary; observe the effective mode at each worker launch or restart.

Therefore the capability gate observes actual worker slots and completion behavior instead of inferring them from a version string or default configuration.

## Codex App Tasks And Worktrees

Official Codex app worktree documentation establishes these current constraints:

- Worktrees are the desktop app's supported isolation primitive for running independent tasks in parallel without disturbing the local checkout.
- App-created worktrees commonly start at detached `HEAD`. Work that must survive the task/worktree lifecycle needs a durable branch or ref, created only when authorized.
- Task-scoped managed worktrees are common, but permanent worktrees can host multiple tasks. Do not enforce “exactly one task per worktree” as a universal invariant.
- `.worktreeinclude` can copy required ignored local files into a managed worktree. It is not a substitute for checking secrets or environment isolation.
- The app keeps a recent set of managed worktrees (documented default: 15) and can remove older managed worktrees according to platform retention behavior.
- Codex-managed worktrees are not automatically deleted while their task is active, their conversation is pinned, or the worktree is permanent. Archiving the associated task or exceeding the configured retention limit can trigger deletion, and Codex saves a restorable snapshot first.

An authorization such as `remove_worktrees: false` controls harness-initiated cleanup only. It cannot promise that the platform will retain an app-managed worktree. Record `platform_lifecycle`, create a durable branch/ref early when needed, and do not leave unique verified work reachable only through detached `HEAD`.

Worktrees isolate files. They do not isolate ports, processes, databases, migration streams, queues, buckets, test identities, feature-flag namespaces, or external sandboxes.

## Local And GitHub Code Review

Official Codex review documentation establishes these current facts:

- Local `/review` runs in read-only mode and can review uncommitted changes or compare the current branch with a base branch. It is the pre-push review gate, not proof that GitHub reviewed the pushed head.
- GitHub review requires the repository to be connected to Codex Cloud with Code review enabled. Automatic reviews can review each new PR opened for review; `@codex review` is the manual trigger.
- Repository `AGENTS.md` files may define `## Review guidelines` that Codex uses during GitHub review.
- Codex GitHub review reports high-signal P0/P1 findings. Ordinary CI, repository rules, and required status checks remain separate controls.
- GitHub auto-merge merges a PR only after its required reviews and status checks pass, and the repository must have auto-merge enabled first.
- GitHub CLI supports an exact-head merge guard through `gh pr merge --match-head-commit <SHA>` and can combine it with squash and auto-merge.

The harness therefore records local diff review separately from GitHub review and binds GitHub CI/review evidence to the exact PR head SHA. A later push invalidates earlier evidence even if the PR number is unchanged. Because CI and Codex review are independent merge gates, the parent starts or observes both for the final pushed head as soon as PR state and authorization allow, polls them concurrently, and restarts both after a new push.

A landing adapter can direct the interactive parent to run a persistent GitHub loop: create or ready the PR, start or observe checks and Codex review in parallel, poll both, and submit an exact-head merge after every gate passes. The skill cannot turn on repository Automatic reviews or auto-merge by itself. Those remain repository settings, and changing them requires separate authorization; when Automatic reviews are not observed, the portable review trigger is `@codex review`.

The runtime adapters remain separate from this landing adapter. A Codex parent loads only the Codex adapter and executes only `codex`-provider nodes; a Claude Code parent loads only the Claude Code adapter and executes only `claude_code`-provider nodes. Local-only work does not load the GitHub adapter. This preserves one PLAN/RUN control plane while reducing default skill context and remote waiting.

For plan-backed shared-repository execution, the harness now surfaces the full launch and landing authorization set in one Plan Readiness checkpoint. Every action still has its own ledger entry and live pre-mutation recheck; the checkpoint only removes repeated prompts after the user has approved the exact path.

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
| `parent` | `shared_checkout` | `agent_result` | fallback only, one write mission at a time, for when worktree creation is unavailable or unauthorized |
| `subagent` | `shared_checkout` | `agent_result` | serialize writes; read-only fan-out is allowed |
| `subagent` | `parent_managed_worktree` | `agent_result` or `report_file` | default for plan-backed mission writes, one mission at a time or several after the full fan-out gate |
| `app_task` | `app_managed_worktree` | `thread_poll`, `report_file`, or `user_relay` | parallel writes only after full fan-out gate and lifecycle acknowledgement |

The `subagent` + `parent_managed_worktree` + `agent_result` row covers both direct parent-owned subagents and Claude Dynamic Workflow mission agents.

Inside the last row, the app task may coordinate up to three direct read-only helpers when the RUN policy and `spawn_subagents` authorization permit it. Those helpers return `agent_result` to the app task; they are not additional app tasks or write workers.

These are examples, not an exhaustive compatibility table. The parent must prove that the chosen combination exists in the current environment. If a completion channel or workspace primitive is missing, fall back to sequential execution.

## Re-Verification Checklist

Before changing orchestration guidance, re-check:

- The size gate still runs before managed planning and does not probe workers or external runtimes for small direct work.
- Codex subagent configuration keys, current defaults, delegation behavior, result/failure delivery, and effective thread/depth limits.
- Codex app worktree detached-HEAD behavior, permanent versus task-scoped worktrees, `.worktreeinclude`, and retention policy.
- Available thread/task tools in the current product surface and whether they support polling, messaging, creation, or only navigation.
- App Server event names and client subscription semantics before promising event-driven integration.
- Codex best-practice warnings for concurrent work on the same files and the current recommended use of worktrees.
- Claude Code Dynamic Workflow version gate, workflow directory, `agent()`/`pipeline()` contract, result schemas, pause/resume behavior, tool inheritance, and current capacity ceilings.
- Claude Code subagent nesting and worktree-isolation behavior before changing the flat workflow shape.
- Any other runtime's worker nesting, isolation, completion, and cleanup behavior before mapping it to these axes.

Record environment-specific observations in RUN evidence. Keep this reference about portable capability semantics.

## Rationale

1. Parallel writes in one checkout remain unsafe: declared scopes do not isolate lockfiles, build caches, generated files, dev servers, or local databases.
2. Worktree isolation is necessary but insufficient for full-stack fan-out because runtime resources still conflict.
3. Parent ownership of PLAN/RUN avoids multiple writers racing on orchestration state.
4. Worker verification and integration verification are separate facts; only integrated results unlock dependencies.
5. Orthogonal capability axes plus a small runtime adapter allow the same skill to route across Codex and Claude Code while degrading safely when a preferred driver is unavailable.

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
- GitHub auto-merge: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request
- GitHub CLI PR merge: https://cli.github.com/manual/gh_pr_merge
- Claude Code agent overview: https://code.claude.com/docs/en/agents
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code workflows: https://code.claude.com/docs/en/workflows
- Claude Code worktrees: https://code.claude.com/docs/en/worktrees
- Claude Code plugins: https://code.claude.com/docs/en/plugins
