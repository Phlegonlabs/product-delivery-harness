# Typed Graph Orchestration

Use this reference for PLAN schema v4, RUN schema v8 or v9, conditional routing, retries, or graph traces.

## Contents

- Org graph and work graph
- Authority and projection
- Nodes and executors
- Dependency and route edges
- Readiness and outcomes
- Runtime binding
- Retry and replay
- Validation and integration

## Org Graph And Work Graph

Use graph engineering as two layers without adding another scheduler:

- The stable org graph is the role contract: planner, mission worker, frontend reviewer, backend reviewer, visual reviewer, approval owner, integrator, and lifecycle owner. Roles define responsibility, context, tools, and handoff shape; they are not persistent live processes.
- The temporary work graph is the canonical PLAN graph plus RUN graph state for one delivery. It owns current nodes, dependencies, routes, attempts, evidence, and runtime bindings.

Instantiate stable roles through existing node kinds, executors, review types, mission contracts, and parent ownership. Change the work graph only through a parent-owned PLAN revision, accepted refinement, bounded route, retry, cancellation, or supersession. Do not let a workflow script or worker mutate graph state directly.

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

Every `runtime_worker` or parent-executed mission declares at least one failure outcome: prefer `retryable_failure`, otherwise use `blocked`. The selector copies that permitted `failure_outcome` into the immutable workflow handoff so a null or failed agent never emits an outcome the PLAN forbids.

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

PLAN runtime policy declares `allowed_providers`, an optional `preferred_provider`, and optional `provider_options` keyed by an allowed provider. Plan Mode chooses these values from mission complexity, latency/cost needs, and the user's explicit model preference. Codex and Claude Code options contain `model` plus a nullable `reasoning_effort`; keep effort null when the provider default is intentional. Model names are portable strings because the destination host remains authoritative for its current catalog. RUN records the actual host and its observed capabilities. A provider, model, or effort preference is not proof that the destination supports it.

Use this Plan Mode order. A delegated Claude Code node never defaults above `sonnet`: reserve any stronger pinned Claude model (for example `claude-fable-5` or `claude-opus-4-8`) for the parent's own coordination and planning, not for a node the parent hands off.

1. Preserve an explicit user-selected provider, model, or reasoning effort.
2. For high-risk architecture, security, migration, difficult debugging, difficult correctness, or final synthesis, choose the strongest suitable observed Codex option and higher reasoning; for a delegated Claude Code node, raise reasoning effort to `high` or `xhigh` while keeping the model at `sonnet`.
3. For general-purpose nodes and backend implementation, prefer Codex `gpt-5.6-terra` with `xhigh` reasoning; keep Claude Code `sonnet` as the availability fallback.
4. Frontend/UI implementation prefers Codex `gpt-5.6-sol` with `xhigh` reasoning; a delegated Claude Code node still defaults to `sonnet` with `high` reasoning rather than a stronger pinned model.
5. Choose review effort from risk. Routine deterministic `backend_code` review uses Codex `gpt-5.6-terra` with `medium`; routine `frontend_code` and visual review use Claude Code `sonnet` with `medium`. Raise review effort to `high` or `xhigh` only for security, migration, difficult correctness, broad architecture, or genuinely ambiguous visual judgment — the Claude Code model itself stays `sonnet`.
6. For bounded mechanical edits, discovery, or inexpensive preflight work, prefer a fast model with low or medium reasoning.
7. When the current catalog or destination support is not observed, leave Codex values null for the host default or use Claude's portable `sonnet` default. Do not invent a model identifier.

These are planning decisions, not execution authorization. Keep different reasoning-effort choices on different nodes when their work differs; do not raise every worker to the parent task's reasoning level by default.

For a runtime worker, select deterministically:

1. preferred allowed provider when it matches the current host provider;
2. current host provider when allowed;
3. otherwise defer with `runtime_unavailable`: a node whose allowed/preferred providers do not include the current host is not executable on this host, with no cross-host fallback.

After choosing a provider, the selector binds that provider's PLAN options. If none were declared, Codex keeps null model/effort values for the host default and Claude production waves use `sonnet`. Every launch directive includes the complete binding (`runtime_binding.model`, `.reasoning_effort`) and the parent copies it to the allocated RUN mission or review worker. Codex task creation maps non-null `model` and `reasoning_effort` to `model` and `thinking`. A Claude Code host passes each node's own `model` (and non-null `reasoning_effort` as `effort`) directly into that node's `agent()` call inside the Workflow script — one Workflow call may freely mix models and reasoning efforts across its nodes, since selection happens per spawned agent, not per wave.

Codex app threads and Claude Dynamic Workflow remain execution adapters. They do not change graph readiness, authorization, result validation, or integration rules. A destination rejecting a model/effort pair is a launch failure to record and replan; it is not permission to silently substitute another model.

Derive a Claude tool profile from existing node semantics instead of adding another PLAN field: missions use `mission_write`, frontend/backend reviews use `code_review_readonly`, and visual reviews use `visual_review_readonly`. Group Claude waves by tool profile only; model and reasoning effort do not require separate waves since each node's `agent()` call already carries its own. Every profile uses an exact allowlist. Mission profiles require `EnterWorktree` and the bounded write tools. Review profiles require `EnterWorktree` to bind reads to the validated `review_path`, but omit `Edit`, `Write`, `NotebookEdit`, and `Bash`; visual review consumes retained screenshots or other existing evidence until a new read-only browser tool is explicitly vetted for the Claude Code host.

Current Claude Code workflow agents inherit the outer allowlist, so the outer process's required `Workflow` permission is also visible to mission agents. The flat no-delegation rule is therefore enforced by the mission contract, structured result, scope/Git validation, and rejection of unplanned child work rather than by removing the `Workflow` tool from the child. Record this runtime limitation; do not claim permission-level delegation prevention.

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
