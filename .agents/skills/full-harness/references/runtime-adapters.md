# Runtime Adapters

Use this reference only for a large managed run. Read `../SKILL.md` first, then apply the shared contract below plus exactly one provider section for the host detected at System Review And Route.

## Boundary

The adapter layer selects launch mechanics and provider-specific model options. It grants no authorization and does not own shared state, review, integration, handoff, or cleanup.

Any lowercase provider id is schema-valid. `codex`, `claude_code`, `pi`, and `generic` are the ids with dedicated sections; every other id runs the generic route below unchanged.

A PLAN node is selectable here when its `allowed_providers` includes the current host. `preferred_provider` is advisory ordering among allowed hosts; it never blocks the current host.

There is no mechanism in the adapter layer to invoke another provider. Do not probe for another runtime's CLI, binary, or plugin as a substitute route. Report an ineligible node as `runtime_unavailable`; before readiness, a node with no planned host is a blocking gap unless the user accepts later deferral.

## Shared Adapter Contract

These rules apply to every provider section below. A provider section adds only launch mechanics, capability facts, model options, and its context-file chain; it never adds authorization, state, handoff, or cleanup rules.

### Capability Snapshot

Observe the current host session and record the result under `runtime_adapter` independently from authorization. A package, CLI binary, or agent file does not prove a usable worker surface, and missing authorization must never make an available driver disappear.

### Version Gate

Record the normalized host version and loaded Harness release in `runtime_adapter.version_gate`, then follow `runtime-upgrades.md`. A `compatible_old` session may finish its already-active wave but cannot start the next wave. After a host or plugin update, mark `restart_required`, start a fresh session, and re-probe from it; never hot-upgrade a live worker or workflow. After re-probing, re-orchestrate the remaining work onto the new runtime per `runtime-upgrades.md`. Provider-specific restart mechanics live in each provider section.

### chrome_devtools Reviewer Probe

When a planned review requires `chrome_devtools`, launch one read-only capability-probe reviewer through the exact selected driver after its launch action is authorized, using the provider's probe surface below. Record `provider`, the actual `driver`, the provider's `surface`, `probe_scope: reviewer_session`, the reviewer session ID, and concise evidence under `runtime_capabilities.reviewer_tools.chrome_devtools`. The probe is not a review attempt and cannot update review state. Parent-session access, an installed package, or a CLI flag alone is not sufficient; record `unavailable` and let selection defer when the reviewer cannot produce the required in-session evidence.

### Dispatch Rules

- Follow every `dispatchable_nodes[].required_actions` exactly. Never infer extra authorization.
- Before allocating any write, verify repository, branch/ref, HEAD, and clean `git status --porcelain`.
- Never run parallel writers in `shared_checkout`. One mission has one writer; parallel writes require separate worktrees and non-overlapping scopes.
- Every worker and reviewer is a fresh sibling. Supply only the bounded context packet and do not replay the parent transcript.
- Workers and reviewers do not delegate, edit PLAN/RUN, integrate, push, or clean up. Do not ask for user input inside a child; a child that needs a contract decision returns a blocked/refinement result and the parent resolves it.
- Use one reviewer per applicable surface by default and allow only one repair re-review. After serial integration, dispatch only the planned fresh read-only reviewers against the exact unified integration SHA; that unified-head pass is the final synthesis, so do not add another same-scope review while the SHA is unchanged. Then run one planned broad final validation. Skip the unified dispatch when that head's tree is byte-identical to a tree an already-passed pre-integration review of the same type covers, and record the node as `skipped`; a dispatched unified reviewer reads a seam-scoped packet focused on what combination changed.
- Give a reviewer only the scoped diff/paths, applicable acceptance rows, required evidence, required tools with their capability evidence, and unresolved findings; refer to PLAN/RUN by path and identity instead of copying their full manifests.
- Validate each terminal result immediately against live worktree, branch, head, scope, commits, and verifier evidence, then stream its ready pre-integration review while sibling workers continue.

### Context And Handoff

Use the shared Repository Context Contract in `../SKILL.md` and the Serialized Same-Repository Host Handoff in `execution-state-model.md`, plus `runtime-performance.md` and `runtime-upgrades.md`. Record queue, context, dispatch, wait, execute, review, verify, and integrate events in RUN-v11 `runtime_metrics` when applicable. This adapter adds no alternate state or handoff rules. It adds no alternate upgrade rules.

### Failure

One failed node does not cancel passing siblings. Preserve failed, cancelled, stalled, dirty, and partial task/worktree evidence. Fall back only to another observed native driver, fewer workers, or the recorded `sequential_parent` route, and record why. Never reset or remove evidence automatically.

## Provider: codex

A PLAN node is selectable here when its `allowed_providers` includes `codex`.

### Codex Capability Snapshot

Before the first launch, observe all eight Codex surfaces: `app_project_list`, `app_thread_create`, `app_thread_read`, `app_thread_message`, `app_thread_wait`, `app_managed_worktree`, `direct_subagent_spawn`, and `direct_agent_result`. Search the current Codex tool surface before marking lazy-loaded thread tools unavailable.

For RUN-v11, record each surface under `runtime_adapter` as `available`, `unavailable`, or `unobserved` with evidence. Ready/running state contains no required `unobserved` surface. Derive `app_threads` only from all six app surfaces and `subagents` only from both direct-agent surfaces.

For `chrome_devtools`, the probe surface is raw CDP: inside that fresh reviewer session, verify the Chrome/browser plugin is loaded, attach to an inspectable Chrome tab, and make one raw CDP call such as `Runtime.evaluate` with a deterministic result. Record `provider: codex` and `surface: raw_cdp`. Record `unavailable` and let selection defer when the reviewer cannot attach or call raw CDP.

Record the observable Codex host version and loaded Harness release in `runtime_adapter.version_gate`. After a Codex or Harness update, mark `restart_required` and open a fresh top-level task before re-probing; never assume an existing task reloads changed runtime or skill files.

Prefer the strongest observed and authorized route:

```text
app_task + app_managed_worktree + thread_poll (cursor-based wait)
-> direct subagents with parent-owned isolation
-> sequential_parent
```

### Codex Provider Defaults

Preserve explicit user and PLAN choices. Otherwise:

- general and backend implementation: Codex `gpt-5.6-terra`, `high`;
- frontend/UI implementation: Codex `gpt-5.6-sol`, `high`;
- routine deterministic `backend_code` review: Codex `gpt-5.6-terra`, `medium`;
- routine frontend, visual, or integration review: Codex `gpt-5.6-sol`, `medium`;
- final unified-head review: Codex `gpt-5.6-sol`, `xhigh`;
- bounded exploration, documentation/API research, and test/log analysis: the fastest suitable model at `low` or `medium`.

Raise effort only for security, migration, difficult correctness/debugging, broad architecture, or genuine ambiguity. Pass PLAN-selected `model` and `thinking` without silent substitution.

### Codex Dispatch

Use each `dispatchable_nodes[].required_actions` exactly.

Mission app tasks:

1. Resolve the current Codex project once.
2. Allocate lease, identity, exact-base app-managed worktree, and authorized branch/ref. Verify repository, HEAD, branch/ref, and clean `git status --porcelain`.
3. Render `../assets/templates/WORKER_GOAL.template.md` with the mission, write/deny scope, skills, verifier, permission boundary, completion channel, result-contract path, Codex worker contract, and effective `AGENTS.override.md` / `AGENTS.md` repository context paths. Include the ordered repository context source paths. Keep `AGENTS.md` context discovery enabled; do not inject `CLAUDE.md` as Codex instructions. RUN-v11 forbids task-local child agents.
4. Create one top-level left-sidebar app task per selected mission. Do not replace a requested app task with a coordinator subagent.
5. Treat every top-level app task as a fresh bounded context packet. For direct sibling agents, explicitly start fresh and pass only the bounded context packet; never fork the parent conversation.
6. Prefer App Server status subscription or cursor-based `wait_threads`. Use one bounded wait for 1-8 tasks with each task's last cursor, process the first terminal or needs-attention result, then wait again with updated cursors. Do not repeatedly read unchanged tasks. Use bounded polling only when no wait/event surface exists, and record its wait time and fallback reason in `runtime_metrics`.
7. Observe live Git head, diff, scope, commits, and ancestry. Validate each terminal result immediately so its pre-integration review may overlap remaining workers, then integrate that mission serially once the review PASSes; only batch gates wait for wave close.

Do not stop after printing a non-empty app-task wave; consume every accepted dispatch entry.

Read-only reviews follow one rule. A review app task needs `create_user_owned_tasks`; a direct-subagent review needs `spawn_subagents`. It needs no write worktree, branch, or commit grant. Start it with fresh bounded context, bind it to one exact SHA, and give it only the scoped packet from the shared dispatch rules. When `chrome_devtools` is required, use raw CDP inside that same reviewer session for the live evidence named by PLAN. Record its outcome, and invalidate the PASS when that SHA changes.

### Flat Parent-Owned Delegation

Codex explorers, mission workers, and reviewers are sibling nodes dispatched by the Harness parent. No worker or reviewer spawns another agent. Use one reviewer per applicable surface by default and allow only one repair re-review. After serial integration, dispatch only the planned fresh read-only reviewers against the exact unified integration SHA; that unified-head pass is the final synthesis, so do not add another same-scope review while the SHA is unchanged. Then run one planned broad final validation on the fixed candidate.

Never replace explicitly requested independent app tasks with direct subagents or sequential parent execution.

## Provider: claude_code

A PLAN node is selectable here when its `allowed_providers` includes `claude_code`.

### Claude Code Capability Snapshot

Observe Workflow, direct Agent tools, `EnterWorktree`, permission mode, slots, completion channel, tool-profile enforcement, and model/effort support. Record the result under `runtime_adapter` independently from authorization.

For `chrome_devtools`, start the Claude Code host with Chrome integration enabled (`claude --chrome`). The probe surface is Claude in Chrome: the fresh reviewer child must resolve its deferred `mcp__claude-in-chrome__*` tools and successfully inspect a connected tab with a deterministic console or JavaScript check. Record `provider: claude_code` and `surface: claude_in_chrome`. This surface is Chrome integration, not arbitrary raw CDP; name it accurately. The flag, parent tools, or a connected parent tab alone is not enough.

Record the normalized Claude Code host version and loaded Harness release in `runtime_adapter.version_gate`. Dynamic Workflow requires Claude Code 2.1.154 or later. After a host or plugin update, mark `restart_required`, run `/reload-plugins` or restart Claude Code, and re-probe from the fresh session; never hot-upgrade a Workflow.

Prefer:

```text
dynamic_workflow + parent_managed_worktree + agent_result
-> direct subagents with parent-owned isolation
-> sequential_parent
```

### Claude Code Provider Defaults

Reserve the parent's premium model for the parent's own coordination and planning. Preserve explicit user and PLAN choices. Otherwise:

- implementation: `sonnet`, `high`;
- routine frontend, backend, visual, and integration review: `sonnet`, `medium`;
- final unified-head review: `sonnet`, `xhigh`;
- bounded mechanical, exploration, research, and test/log work: `haiku`, `low` or `medium`.

Raise delegated effort to `xhigh` only for security, migration, difficult correctness/debugging, broad architecture, or genuine ambiguity. Raise a delegated model above `sonnet` only when the user explicitly names that node. Pass PLAN-selected `model` and `reasoning_effort` as `model` and `effort` without silent substitution.

### Claude Code Dispatch

Follow every `dispatchable_nodes[].required_actions` exactly. Never infer extra authorization.

1. Validate PLAN/RUN and record the accepted wave.
2. Allocate one exact-base parent-managed worktree and authorized branch per write mission. Verify repository, branch/ref, HEAD, and clean `git status --porcelain`.
3. Render `../assets/templates/WORKER_GOAL.template.md` with the node, scope, skills, verifier, permission boundary, result-contract path, Claude Code worker contract, effective `CLAUDE.md` repository context paths, and shared `AGENTS.md` governance paths. Include the ordered repository context source paths. Keep automatic context discovery enabled. Do not apply Codex or Pi worker mechanics.
4. Partition the accepted frontier into homogeneous `tool_profile` groups. Each group gets its own bounded call. Never put a `mission_write` node beside a `code_review_readonly` or `visual_review_readonly` node.
5. Use `CLAUDE_GRAPH_WORKFLOW.template.js` for any group containing review nodes or for a mixed original frontier. Give each review node only its exact SHA and the scoped packet from the shared dispatch rules. A reviewer with required `chrome_devtools` resolves and uses its inherited Claude-in-Chrome tools inside that same child session; it returns blocked if they are absent. Use `CLAUDE_DYNAMIC_WORKFLOW.template.js` only for an originally all-write, single-profile mission group.
6. A `tool_profile` is a prompt/result contract, not permission-level tool removal. Review nodes inherit host tools and must be validated as read-only.
7. Do not ask for user input inside Workflow. Return a blocked/refinement result and let the parent resolve it.
8. Each Workflow or direct Agent is a fresh sibling. Treat `pipeline()` / `agent_result` terminal output as the completion event; consume each terminal result as soon as the host exposes it. Use bounded polling only when no event result is exposed, and record the fallback.

The workflow contains flat parent-owned siblings; workers and reviewers do not delegate, edit PLAN/RUN, integrate, push, or clean up.

## Provider: pi

A PLAN node is selectable here when its `allowed_providers` includes `pi`. This section never invokes Codex or Claude Code as a bridge.

### Pi Capability Snapshot

Observe the current Pi session and record the result under `runtime_adapter` independently from authorization.

Record `pi --version` and the loaded Harness release in `runtime_adapter.version_gate`. Update Pi with its native updater and update the installed Harness skill copies only after an explicit user instruction, per `runtime-upgrades.md`; then mark `restart_required`, start a fresh Pi session, and re-probe. Never overwrite standalone skills or change installed roles, models, fallbacks, credentials, or unrelated packages as part of this gate.

- Record `subagents` only when the session exposes a role-aware Pi launch surface and terminal child results. The launch call must select the installed role by name and leave its base model unset. If a generic `agents.spawn` surface accepts `runner` and `model` but lacks a Pi role selector, it does not satisfy this capability; use `sequential_parent` instead of simulating a role with a name, prompt, tool list, or model override.
- Always record `sequential_parent` as fallback.
- Use `worker_runtime: subagent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result` or `report_file` for delegated writes.
- If the worker surface is incomplete, use the core's real `sequential_parent` for missions; do not imitate delegation. `sequential_parent` cannot satisfy a fresh independent review node, so that node blocks until a role-aware Pi reviewer surface or another allowed host is available.

For `chrome_devtools`, the Pi `reviewer` role must load `npm:@narumitw/pi-chrome-devtools` and its strict tool allowlist must name the required `chrome_devtools_*` tools. Prefer the narrow `subagents.agentOverrides.reviewer.extensions` and `.tools` settings; `subagents.defaultExtensions` is acceptable only when every otherwise-unconfigured role should inherit the extension. An installed main-session package or a main Pi tool call is not proof. Launch the probe through the exact selected Pi driver (`/run reviewer ...` is the direct pi-subagents surface); inside that child call `chrome_devtools_list_pages` and one deterministic page/JavaScript inspection. Record `provider: pi`, `driver: subagents`, and `surface: pi_chrome_devtools`. If the extension, role, role-aware launcher, connected page, or child tools are absent, record `unavailable` and block rather than changing Pi roles or packages without explicit user instruction.

### Preserve Pi Routing

Pi owns role-to-model and fallback selection. Preserve installed agent definitions, model scope, and fallback order; PLAN may lower or raise reasoning effort per node without replacing the role's configured primary model.

- Keep `provider_options.pi.model` null. Set `reasoning_effort` per node when the plan has a latency tier; null preserves the installed role default.
- Once the host provider is Pi, ignore the shared Codex and Claude Code task-shape model preferences. Omit `model` from the Pi launch call; never translate a null Pi binding into a model search term or a provider bridge.
- Frontend/UI implementation uses the installed `frontend_designer` role.
- Backend, data, infrastructure, and general implementation use `worker`.
- Exact-head read-only review uses `reviewer`.
- `scout` and `researcher` are bounded read-only lanes.
- Use `medium` for bounded discovery, mechanical repair, and routine deterministic review; `high` for general implementation and risk-bearing mission review; and `xhigh` only for a justified high-risk or unified final synthesis. `max` and `ultra` require an explicit user choice or recorded exceptional risk.
- At launch, resolve the installed role's primary model and fallback order, keep that base routing, and apply the non-null PLAN effort through Pi's per-run thinking suffix. If the installed provider rejects the effort, block and revise the node; never silently fall back to a stronger effort.
- A rejected primary model may use only the installed role's declared fallback order. Do not manually respawn the node on another model or provider, even when that substitute is available to the parent.
- Record the actual resolved role, model, effort, fallback, run id, and terminal status. Never invent a missing role or silently pin a Harness model.

### Pi Dispatch

Follow every `dispatchable_nodes[].required_actions` exactly. Never infer extra authorization.

For every managed review, persist `harness_transition.py reserve-review-dispatch` before invoking Pi. The returned node, worker, attempt, SHA, path, driver, and runtime binding are the launch receipt. Pass that exact identity into the reviewer packet. If reservation fails, do not launch. A Pi result without the matching retained receipt is unplanned evidence and must not update RUN.

1. Allocate lease, authorized branch, and exact-base parent-managed worktree. Verify repository, branch/ref, HEAD, and clean `git status --porcelain`.
2. Render `../assets/templates/WORKER_GOAL.template.md` as a self-contained bounded context packet with the current mission slice, exact scope, skills, verifier, permission boundary, result-contract path, ordered repository context source paths, Pi worker contract, and Pi's effective per-directory context selection: `AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`. Refer to PLAN/RUN by identity and path instead of copying either manifest. Keep Pi context discovery enabled; never pass `--no-context-files` or `-nc`. When `AGENTS.md` exists do not also inject `CLAUDE.md`.
3. Launch `worker`, `frontend_designer`, `reviewer`, `scout`, and `researcher` through the role-aware Pi surface with explicit `context: "fresh"`, a stable key, the assigned worktree as `cwd`, and no base-model argument. A generic `agents.spawn` call without a Pi role selector is not a valid adapter launch. Fork only an `oracle` when inherited decision history is essential and record that reason. A mission must fit one bounded fresh-child slice whose fixed overhead stays small against its useful work; split it before readiness when it does not.
4. One mission has one writer. Parallel writes require separate worktrees and non-overlapping scopes.
5. A Pi child must not delegate again. It returns the shared result contract; the parent validates live Git facts.
6. Subscribe or block on terminal child/status events instead of fixed-interval polling. Process each terminal result immediately and stream its ready pre-integration review while sibling workers continue; close the wave only after every selected worker result is validated. Before the host deadline, request a checkpoint after the current tool returns when a slice is not converging; do not use timeout as the checkpoint. A missing process plus a dirty or advanced worktree is interrupted evidence, not `worker_running` proof.
7. Dispatch one fresh `reviewer` per applicable surface against each returned exact head only after its receipt is persisted. Give it only the receipt identity, exact SHA, and the scoped packet from the shared dispatch rules. When `chrome_devtools` is required, use the inherited Pi Chrome DevTools extension inside that same reviewer child. Complete the same reserved attempt with `record-review-attempt`; never append a log-only verdict.

### Pi Failure

Preserve failed node, lease, run id, dirty files, commits, and session evidence. A rejected model follows Pi's configured fallback policy without a parent-selected replacement. Use `sequential_parent` only through the shared core. Stop when the required role is missing, the launch surface cannot select it, or changing roles would change the intended result.

## Provider: generic

A PLAN node is selectable here when its `allowed_providers` includes `generic`.

Any host without a dedicated section above runs the generic route unchanged — nothing in the harness assumes one of the named runtimes. Current market hosts — Gemini CLI, Cursor, GitHub Copilot, Cline, Aider, Windsurf, OpenCode, and whatever comes next — run this route as-is; the names are illustrative, not a support list.

Selecting `generic` needs no host-detection pass. A session that is not evidently one of the three named hosts records `provider: generic` and runs this route directly; never probe for another runtime's CLI, binary, or plugin just to identify the host.

- Driver: `subagents` with parent-owned isolation when the session exposes a fresh-child launch surface that selects a child by stable key and returns terminal child results; otherwise the real `sequential_parent` from `worktree-thread-orchestration.md`. Always record `sequential_parent` as fallback.
- Version gate: record the host's own version when the host reports one, and always record the loaded Harness release in `runtime_adapter.version_gate`, then follow `runtime-upgrades.md`. A host with no observable own-version is never deferred for that reason alone — the gate's required observation is the loaded Harness release and the selected driver's live capability probe.
- Models: there is no generic model catalog. Pass PLAN-selected model and reasoning-effort options to the launch call only when the host accepts them, and record the resolved values; never substitute a different model silently.
- Context: discover the effective instruction chain from repository root to the selected checkout and keep automatic context discovery enabled. Do not inject another runtime's instruction file as this host's instructions.
- chrome_devtools: record `unavailable` unless the host exposes an in-reviewer browser surface; let selection defer rather than substituting the parent's browser session.
- Dispatch: launch each worker as a fresh child with the assigned worktree as `cwd` and only the bounded context packet; wait on terminal child results when the host exposes them, otherwise bounded polling recorded in `runtime_metrics`. A generic child must not delegate again. `sequential_parent` cannot satisfy a fresh independent review node; that node blocks until a capable child surface or another allowed host is available.

When a generic host gains its own section through `Adding A Provider`, that section replaces this one for that host.

## Adding A Provider

Running a new runtime needs no schema change at all:

1. Use its lowercase id — for example `gemini_cli` or `cursor` — in each runtime node's `allowed_providers`. Any such id is schema-valid, records as `runtime_adapter.provider`, and runs the Provider: generic route with the generic driver ladder.

Give a host its own section only when it has native mechanics worth pinning — a dedicated driver, model catalog, probe surface, or context chain:

1. Add the provider id to `RUNTIME_DRIVER_PRIORITY` in `scripts/harness_schema.py`.
2. Add one `## Provider: <id>` section above: the eligibility sentence, capability facts and probe surfaces, the driver ladder, provider model defaults, the launch procedure, and the context-file chain. It must reuse the shared contract instead of restating it.
3. Extend the adapter contract tests to pin the new section's rules.
4. Run the full verification suite from the repository root.

A provider section never adds authorization keys, alternate state, handoff, or upgrade rules; those live in the shared contract and the core references.
