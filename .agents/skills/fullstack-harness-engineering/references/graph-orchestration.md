# Typed Graph Orchestration

Use this reference for PLAN schema v4, RUN schema v8 or v9, conditional routing, retries, graph traces, or mixed Codex and Claude execution.

## Contents

- Authority and projection
- Nodes and executors
- Dependency and route edges
- Readiness and outcomes
- Runtime binding
- Claude external runtime
- Retry and replay
- Validation and integration

## Authority And Projection

Keep one control plane:

```text
PLAN graph definition
-> parent graph scheduler
-> runtime-neutral launch directive
-> Codex, Claude, command, external wait, or human executor
-> validated node result
-> RUN graph state
-> next frontier
```

PLAN owns static nodes, edges, outcomes, attempt limits, and runtime policy. RUN owns node attempts, outcomes, edge traversals, runtime bindings, and evidence. Git and live runtime observations remain separate facts. Do not add another graph database or let a workflow script edit PLAN/RUN.

For PLAN v2 and v3, `missions[].depends_on` remains the canonical mission DAG. For PLAN v4, remove that field and use graph dependency edges as the only cross-mission ordering source. Task dependencies remain flat, same-mission, and acyclic.

## Nodes And Executors

Use these node kinds:

```text
mission       -> one existing mission contract and write unit
verifier      -> a declared deterministic verifier or typed read-only runtime review
approval      -> an explicit human decision
external_wait -> CI, review, deployment, or other observed external state
lifecycle     -> one authorization-ledger action owned by the parent
```

Use these executors:

```text
runtime_worker  -> Codex, Claude, or another observed worker provider
harness_parent  -> serialized parent action
local_command   -> deterministic verifier command
external_system -> polling or event observation
human           -> explicit approval or contract decision
```

The node is the workflow identity. A thread, Claude session, process, worktree, or worker ID is an attempt binding recorded in RUN, never the node ID.

A verifier using `runtime_worker` is a read-only review node, not a mission. Its `review` contract names `type` (`frontend_code`, `backend_code`, or `visual`), reviewed mission IDs, repository scope, and required evidence. RUN binds the attempt in `review_workers[]` to one exact current integrated or PR-head SHA. It never receives a mission lease, write scope, branch, or commit authority.

For full-stack UI delivery, use this default shape:

```text
contract freeze
  -> frontend mission -> frontend_code review --fix_required--> frontend repair
  -> backend mission  -> backend_code review  --fix_required--> backend repair
  -> integration / preview
  -> visual review --fix_required--> frontend or integration repair
  -> final deterministic gates
```

Keep frontend and backend review separate when both surfaces exist. Combine them only for a genuinely single-surface change and record the reason. Every correction loop is bounded and has a blocked or human-owned exit.

PLAN `required_reviews` lists the applicable review types. Validation requires a matching runtime-worker verifier for every listed type, so the planner cannot mark a review required only in prose. Use an empty list only when none of the three review surfaces applies, and record that rationale in the human plan view.

## Dependency And Route Edges

`dependency` means the target consumes a completed prerequisite. It always uses outcome `pass`, has no traversal count, and the complete dependency subgraph must be acyclic.

`route` means the target activates only for named source outcomes such as `pass`, `fix_required`, `retryable_failure`, `blocked`, or `contract_gap`.

A route cycle is valid only when:

- every route edge inside the cycle has `max_traversals`;
- the cycle has an edge to a node outside the cycle;
- every new attempt receives a new attempt ID and preserves old evidence;
- exhaustion routes to a blocked or human-owned stop rather than silently continuing.

Do not add an expression language. Put complex decisions in a verifier node and route on its declared outcome.

## Readiness And Outcomes

Run `scripts/select_ready_nodes.py` for PLAN v4 and RUN v8. A node is logically ready only when:

- plan readiness and execution authorization are current;
- its phase is `dormant` or `ready` and its attempt budget remains;
- all dependency sources succeeded with `pass`;
- at least one incoming route matches when route edges exist;
- no node blocker remains;
- mission nodes still have a queued or ready mission state.

The selector first computes the logical graph frontier, then resolves runtime bindings and action authorization. It applies the existing write-scope and runtime-resource conflict rules to ready mission nodes. All `runtime_worker` nodes, including read-only reviews, share the minimum of PLAN capacity, runtime capacity, and currently available worker slots. Reviews do not consume isolation capacity because they cannot write, but they never bypass action authorization or the shared runtime budget. Non-runtime nodes remain explicit directives such as `run_verifier`, `await_approval`, `poll_external`, or `run_lifecycle_action`.

## Runtime Binding

PLAN runtime policy declares `allowed_providers`, an optional `preferred_provider`, and optional `provider_options` keyed by an allowed provider. Plan Mode chooses these values from mission complexity, latency/cost needs, and the user's explicit model preference. Codex and Claude Code options contain `model` plus a nullable `reasoning_effort`; keep effort null when the provider default is intentional. Model names are portable strings because the destination host remains authoritative for its current catalog. RUN records the actual host and observed external runtimes. A provider, model, or effort preference is not proof that the destination supports it.

Use this Plan Mode order:

1. Preserve an explicit user-selected provider, model, or reasoning effort.
2. For high-risk architecture, security, migration, difficult debugging, or final synthesis, choose the strongest suitable observed option and higher reasoning.
3. For general-purpose nodes, backend implementation, and `backend_code` review, prefer Codex `gpt-5.6-terra` with `xhigh` reasoning; keep Claude Code `sonnet` as the availability fallback.
4. Frontend/UI implementation uses the pinned Claude model `claude-fable-5` with `high` reasoning. `frontend_code` review uses `claude-fable-5` with `xhigh` reasoning.
5. Preview and final visual-review nodes use `claude-fable-5` with `high` reasoning. All three frontend roles use Codex `gpt-5.6-sol` with `xhigh` reasoning when Claude is unavailable.
6. For bounded mechanical edits, discovery, or inexpensive preflight work, prefer a fast model with low or medium reasoning.
7. When the current catalog or destination support is not observed, leave Codex values null for the host default or use Claude's portable `sonnet` default. Do not invent a model identifier.

These are planning decisions, not execution authorization. Keep different model choices on different nodes when their work differs; do not raise every worker to the parent task's reasoning level by default.

For a runtime worker, select deterministically:

1. preferred allowed provider when available;
2. current host provider when allowed;
3. another observed allowed external provider;
4. otherwise defer with `runtime_unavailable`.

After choosing a provider, the selector binds that provider's PLAN options. If none were declared, Codex keeps null model/effort values for the host default and Claude production waves use `sonnet`. Every launch directive includes the complete binding and the parent copies it to the allocated RUN mission or review worker. Codex task creation maps non-null `model` and `reasoning_effort` to `model` and `thinking`. Claude nodes are grouped into one wave per selected model and effort; the immutable wave request carries both, and the bridge passes non-null effort with `--effort`. A bridge CLI model override must match the PLAN-selected model.

Codex app threads and Claude Dynamic Workflow remain execution adapters. They do not change graph readiness, authorization, result validation, or integration rules. A destination rejecting a model/effort pair is a launch failure to record and replan; it is not permission to silently substitute another model.

## Claude External Runtime

When Codex remains the parent and Claude Code is a worker provider:

1. Run `scripts/claude_runtime_bridge.py preflight` with the no-edit preflight workflow. Capability preflight defaults to `haiku`. Production uses the PLAN-selected wave model and defaults to `sonnet` only when PLAN omits a Claude option.
2. Record an available external runtime only after the Workflow tool executes the protocol-v1 script.
3. Require `invoke_external_runtime` for `runtime:claude_code` in addition to `spawn_subagents`. Write missions also require their normal worktree, branch, and commit actions; read-only review nodes do not.
4. Select ready Claude nodes. Allocate worktrees, branches, leases, and attempt IDs for write missions. Allocate a `review_workers[]` record with exact SHA, path, scope, and attempt ID for reviews.
5. Build one immutable wave request and call `claude_runtime_bridge.py run-wave`.
6. The bridge invokes `CLAUDE_GRAPH_WORKFLOW.template.js`; Claude agents use only assigned worktrees and return one node result per node.
7. Validate the wrapper with `validate_node_result.py`. Then validate mission worker payloads and observed Git facts with the existing worker validator, or validate review findings against the recorded review attempt and reviewed SHA.
8. Integrate accepted commits serially and update RUN before routing another edge.

The outer Claude process and workflow agents inherit the supplied tool allowlist. Never use a broad permission bypass as a connectivity shortcut. A preflight proves only runtime availability; it does not authorize a production wave.

When the user explicitly selected Claude Code full access and RUN records a ready `full_access` boundary, set the wave request `permission_mode` to `bypassPermissions`. The bridge emits `--dangerously-skip-permissions` while retaining the explicit tool allowlist. Do not invoke a local shell function such as `CC` through a shell; resolve the Claude executable directly and reproduce the recorded permission semantics without shell expansion.

## Retry And Replay

Retry one failed node by creating a new attempt on the same graph revision. Replay a subgraph only after every affected downstream node is reset or superseded under a new parent-owned state transition.

Never reuse:

- an old attempt ID;
- an expired lease or authorization;
- stale plan, graph, base, or head identity;
- a prior successful verifier result after its input head changed;
- a failed worker report as if the retry replaced its evidence.

Do not retry the same failed approach more than twice. After the configured attempt or route bound is exhausted, stop at `blocked` and identify the required decision.

## Validation And Integration

Use this order:

```text
validate PLAN/RUN
-> select graph frontier
-> re-observe runtime and Git
-> allocate attempt and workspace
-> execute adapter
-> validate node result
-> validate worker result and actual diff
-> integrate serially
-> run integration and batch verifiers
-> update RUN graph and mission state
-> recompute frontier
```

A node result is a candidate. Only a mission node with an integrated mission PASS may become `succeeded` with outcome `pass`. A completed thread, Claude workflow, process exit, worker commit, or structured JSON response alone does not satisfy downstream dependencies.
