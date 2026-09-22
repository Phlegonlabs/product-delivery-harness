# General Runtime Adapter

Use this contract only when managed work needs native execution. Direct work needs no adapter preflight. Every host uses the same contract; there are no provider sections, model catalogs, fixed launch commands, or bundled runtime workflow scripts.

## Observe The Current Session

The agent reads the current tool descriptions and effective repository instructions, resolves deferred tools when available, and maps native capabilities to the contract below. A host name, installed package, CLI binary, or agent file does not prove a usable worker surface. Do not probe for another runtime's CLI, binary, or plugin as a substitute route.

Record the observed host identity as a lowercase `runtime_adapter.provider`, or `generic` when it is unknown. The identity grants no capability. A PLAN node is eligible on the current host exactly when its `allowed_providers` includes that host. `preferred_provider` is advisory ordering among allowed hosts; it never blocks the current host. A mismatch defers with `runtime_unavailable`; do not bridge to another host.

Record `available_drivers` in the order appropriate to the requested topology and observed capabilities. The selector uses that order, independently of provider name. Include `sequential_parent` last as the safe fallback. Never replace explicitly requested independent app tasks with direct subagents or sequential parent execution.

| Driver | Required observed capability | Runtime axes |
| --- | --- | --- |
| `app_threads` | Resolve the project; create, inspect, message and wait for a distinct user-owned task; allocate its managed worktree | `app_task` + `app_managed_worktree` + `thread_poll` |
| `subagents` | Launch a fresh child by stable identity and receive its terminal result | `subagent` + `parent_managed_worktree` or read-only `shared_checkout` + `agent_result` or `report_file` |
| `sequential_parent` | The current parent performs the work in the assigned checkout | `parent` + `parent_managed_worktree` + `agent_result` |

These names describe capabilities, not tool names. The agent selects the actual native calls from the current session. For schema 10/11 ready or running delegation, record `detection_source: observed` and `capability_probe` facts with status and concrete evidence for every advertised delegated driver. App facts are `app_project_list`, `app_thread_create`, `app_thread_read`, `app_thread_message`, `app_thread_wait`, and `app_managed_worktree`; child facts are `direct_subagent_spawn` and `direct_agent_result`. Unrelated surfaces need no probe. `unobserved` or `unavailable` cannot prove an advertised driver. Capability is independent of authorization; a missing grant does not erase an available capability.

Confirm fresh context, workspace binding, permission inheritance, terminal result identity, cancellation/recovery behavior, and actual capacity before dispatch. When the host cannot satisfy the selected contract, block that work or use another observed route under the existing authorization. `sequential_parent` cannot satisfy a fresh independent review node.

## Models, Roles And Context

There is no built-in model or effort default. Null PLAN options preserve the host's installed defaults, role-to-model mapping and fallback order. Pass explicit PLAN options only when the current native interface supports them; never substitute a different model silently or pretend an unsupported option was applied. Unsupported explicit choices block that node. Record actual resolved role, model, effort and any host-owned fallback in existing result evidence. Do not install roles, change provider credentials, or edit runtime configuration to make a route appear available.

Discover the effective instruction chain from repository root to the assigned checkout and include its ordered paths in the bounded context packet. Keep automatic context discovery enabled. Do not inject another runtime's instruction file as this host's instructions. Observe the installed skill identity separately from the actually loaded identity; unknown loaded identity stays unknown.

## Authorization And Dispatch

The parent owns authorization, PLAN/RUN, dispatch, leases, integration and lifecycle actions. This adapter grants none of them and does not own shared state. Follow every `dispatchable_nodes[].required_actions` exactly. Never infer extra authorization. A review app task needs `create_user_owned_tasks`; a direct-subagent review needs `spawn_subagents`. A capability probe that launches a child needs the same applicable authorization.

1. Validate PLAN/RUN and accept the selected frontier. Reserve runtime reviews with `reserve-review-dispatch` before launch; never reconstruct a receipt afterward.
2. Allocate only authorized exact-base worktrees and branches. Before allocating any write, verify repository, branch/ref, HEAD, and clean `git status --porcelain`. Never run parallel writers in `shared_checkout`. One mission has one writer; parallel writes require separate worktrees and non-overlapping scopes.
3. Render `../assets/templates/WORKER_GOAL.template.md` with the mission or review, scope, skills, verifier, permission boundary, result contract, exact base or review SHA, and context paths. Every worker and reviewer is a fresh sibling; do not replay the parent transcript. No worker or reviewer spawns another agent, edits PLAN/RUN, integrates, pushes, or cleans up. RUN-v11 forbids task-local child agents.
4. Use the observed native calls to launch all selected siblings before waiting. A blocking launch must run asynchronously. Apply the host's actual restrictions; a prompt or profile label is not permission-level tool removal. Keep write and read-only scopes separate and verify reviewer read-only behavior.
5. Bind the real task/worker identity and observed checkout to `lease-worker`; `--task-thread-id` is app-task-only. Wildcard receipts never grant authority. When a task must be created before its exact identity is known, `accept-wave` is the durable pre-create boundary. Put run ID, PLAN revision/digest, wave ID and mission ID in its packet. If creation returns ambiguously, inspect existing tasks/worktrees for a unique exact packet and base match. Bind the unique match or block; never automatically create a duplicate or delete an orphan.
6. Subscribe or block on terminal child/status events; prefer cursor waits when supported. Do not repeatedly read unchanged tasks. Use bounded polling only when no wait/event surface exists, and record its reason and cost in `runtime_metrics`.
7. Validate each terminal result immediately against live worktree, branch, head, scope, commits and verifier evidence, then stream its ready pre-integration review while siblings continue. Integration stays serial. After integration, launch fresh read-only reviewers against the exact unified integration SHA, then one planned broad final validation. Security always runs with `code_security_verification`; only non-security review may use a recorded byte-identical skip.

Reserve non-runtime nodes before their checks or actions, execute outside the RUN lock, then record `record-node-result` evidence. Native task completion is not a verification PASS. Native caches, resumes and retries never replace current authorization, Git reconciliation or exact-SHA evidence.

## Reviewer Tools

For `runtime_capabilities.reviewer_tools.chrome_devtools`, launch a read-only probe through the exact selected driver after its launch is authorized. Inside that fresh reviewer, attach to the required browser target and perform a deterministic inspection. Record the actual lowercase surface identifier, provider, driver, `probe_scope: reviewer_session`, session ID and evidence. This is not a review attempt and cannot update review state. An available surface cannot be `none`, `unknown` or `unobserved`. Parent browser access, an installed package or a launch flag is not proof; record unavailable and defer when the reviewer cannot perform the check.

Give each reviewer one bounded packet: scoped diff, acceptance, evidence, tool capability and unresolved findings. Refer to PLAN/RUN by path. A changed SHA invalidates the review PASS.

## Version, Handoff And Failure

Record `runtime_adapter.version_gate` and follow `runtime-upgrades.md`. A host with no observable own-version is never deferred for that reason alone; the loaded Harness identity and selected capabilities still need evidence. A `compatible_old` session finishes only its active wave. After an update, mark `restart_required`, start a fresh session and re-probe; never hot-upgrade a worker.

Use the Repository Context Contract, Serialized Same-Repository Host Handoff in `execution-state-model.md`, and `runtime-performance.md`. This adapter adds no alternate state or handoff rules and no alternate upgrade rules. Preserve failed, cancelled, stalled, dirty and partial evidence. One failed node does not cancel passing siblings. Reduce concurrency or use another observed native driver only within existing grants; never reset or remove evidence automatically.

The former platform-specific launch templates and `dynamic_workflow`/`workflow_runs` compatibility path are removed. Historical files remain untouched; they are not executable through this contract. Resume unfinished work only after explicit replanning and fresh capability, identity and authorization checks. Do not relabel historical results or silently migrate a live RUN.

There is no mechanism in the adapter layer to invoke another provider. Do not stop after printing a non-empty app-task wave; consume every accepted dispatch entry.
