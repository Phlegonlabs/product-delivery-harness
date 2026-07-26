# Typed Graph Orchestration

Use this reference for current PLAN schema v5 and RUN schema v10 typed graphs, conditional routing, retries, and graph traces. PLAN v4 with RUN v8 or v9 remains readable as an older typed-graph contract.

## Contents

- Org graph and work graph
- Authority and projection
- Nodes and executors
- Multi-reviewer fan-out
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

For current PLAN v5 typed graphs, use graph dependency edges as the only cross-mission ordering source. PLAN v4 uses the same graph rule. PLAN v2 and v3 retain the legacy `missions[].depends_on` DAG. Task dependencies remain flat, same-mission, and acyclic.

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

Keep frontend and backend review separate when both surfaces exist. Combine them only for a genuinely single-surface change and record the reason. Every correction loop is bounded and has a blocked or human-owned exit. This shape names one frontend mission and one visual review for readability; scope each pair to one page (or a small, genuinely tightly-coupled group of pages) per `contract-and-traceability.md`'s mission-granularity corollary, and repeat the shape per page/group rather than letting one frontend mission span the whole UI matrix with a single visual review fired once at the end.

PLAN `required_reviews` lists the applicable review types. Validation requires a matching runtime-worker verifier for every listed type, so the planner cannot mark a review required only in prose. Use an empty list only when none of the three review surfaces applies, and record that rationale in the human plan view.

## Multi-Reviewer Fan-Out

One review node per surface is the default and covers most work. But an independent review agent costs almost nothing next to a human reviewer, so for a high-risk review surface a planner MAY fan out to N independent reviewers of the same `review.type` and reconcile their verdicts, which catches more real issues than raising a single reviewer's `reasoning_effort` alone. This is an optional, additive planning choice: a PLAN with just one review node per surface is unchanged and fully valid. Reserve fan-out for surfaces where the extra reviewers pay for themselves — security-sensitive code, destructive or irreversible migrations, and genuinely ambiguous visual/taste judgment.

Express it with the existing typed graph mechanism; no new PLAN or RUN schema field is required. Instead of one `kind: "verifier"` node for the surface, declare N verifier nodes that are identical in what they judge:

- same `review.type` (`frontend_code`, `backend_code`, or `visual`);
- same reviewed `mission_ids` and repository `scope`;
- the same incoming `dependency` edges, so every reviewer binds to the SAME exact integrated or PR-head SHA;
- each its own node ID, its own attempt, and no shared state with the others — an independent read-only review, never a mission, and never granted write scope, a lease, or commit authority.

These still count as normal `runtime_worker` review nodes for `required_reviews` validation (each is a matching verifier for its type) and for the shared runtime budget. Give the reviewers different `reasoning_effort` or providers if you want diversity of judgment; keep any delegated Claude Code model at `sonnet` per the Runtime Binding rules.

Reconciliation is a PARENT-SIDE convention, not a graph feature. The N reviewer results are independent node outcomes; the parent combines them into ONE proceed/block decision and drives the surface's existing `fix_required` route edge from that combined decision (the repair loop, its bound, and its blocked/human-owned exit are unchanged). Name the rule in the human plan view so the reconciliation is auditable. Each reviewer's own `outcome` and `findings` are recorded on its `run.review_workers` entry, separate from `node_states[node_id].last_outcome` (the parent's single reconciled verdict used for routing and dependency readiness) — so a dissenting reviewer's finding stays on the record and auditable even after reconciliation folds it into a passing surface. Two patterns:

- **Any-blocks (unanimous pass required).** Treat the surface as `fix_required`/blocked if ANY reviewer returns `fix_required`. Use it for safety-critical surfaces — security-sensitive code, destructive migrations — where a single true finding matters more than reviewer agreement and a false block is cheaper than a missed defect. Every reviewer's blocking finding must be addressed before the surface proceeds.
- **Majority-pass.** Proceed when a majority of reviewers pass; route to `fix_required` only when a majority ask for it. Use it for more subjective or taste-driven judgment (typically `visual`) where one dissenting reviewer should not block indefinitely. Record the dissent, but do not let a lone minority verdict hold the surface. Use an odd N so majority is unambiguous.

Pick any-blocks when a missed issue is dangerous and a needless repair loop is cheap; pick majority-pass when the judgment is genuinely contestable and an over-strict single voter would stall delivery. When unsure, default to any-blocks, since it degrades to the single-reviewer behavior for N=1 and never lets a real blocking finding through.

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

Run `scripts/select_ready_nodes.py` for current PLAN v5 and RUN v10, and for supported PLAN-v4/RUN-v8-or-v9 typed graphs. A node is logically ready only when:

- plan readiness and execution authorization are current;
- its phase is `dormant` or `ready` and its attempt budget remains;
- all dependency sources succeeded with `pass`;
- at least one incoming route matches when route edges exist;
- no node blocker remains;
- mission nodes still have a queued or ready mission state.

The selector first computes the logical graph frontier, then resolves runtime bindings and action authorization. It applies the existing write-scope and runtime-resource conflict rules to ready mission nodes. All `runtime_worker` nodes, including read-only reviews, share the minimum of PLAN capacity, runtime capacity, and currently available worker slots. Reviews do not consume isolation capacity because they cannot write, but they never bypass action authorization or the shared runtime budget. Non-runtime nodes remain explicit directives such as `run_verifier`, `await_approval`, `poll_external`, or `run_lifecycle_action`.

## Runtime Binding

PLAN runtime policy declares `allowed_providers`, an optional `preferred_provider`, and optional `provider_options` keyed by an allowed provider. Plan Mode chooses these values from mission complexity, latency/cost needs, and the user's explicit model preference. Codex and Claude Code options contain `model` plus a nullable `reasoning_effort`; keep effort null when the provider default is intentional. Model names are portable strings because the destination host remains authoritative for its current catalog. RUN records the actual host and its observed capabilities. A provider, model, or effort preference is not proof that the destination supports it.

Use this Plan Mode order. A delegated Claude Code node never defaults above `sonnet`: reserve any stronger pinned Claude model (for example `claude-fable-5` or `claude-opus-4-8`) for the parent's own coordination and planning, not for a node the parent hands off. For a node whose work is bounded, mechanical, or purely read-only (see point 6 below), default its Claude Code model to `haiku` instead of `sonnet` — reserve `sonnet` as the default for every node whose work involves real implementation judgment or review, and reserve anything above `sonnet` for the parent's own coordination and planning as already stated.

1. Preserve an explicit user-selected provider, model, or reasoning effort.
2. For high-risk architecture, security, migration, difficult debugging, difficult correctness, or final synthesis, raise reasoning effort to `xhigh` for the chosen Codex or Claude Code option while keeping a delegated Claude Code node's model at `sonnet`.
3. For general-purpose nodes and backend implementation, prefer Codex `gpt-5.6-terra` with `high` reasoning; keep Claude Code `sonnet` with `high` reasoning as the availability fallback.
4. Frontend/UI implementation prefers Codex `gpt-5.6-sol` with `high` reasoning; a delegated Claude Code node still defaults to `sonnet` with `high` reasoning rather than a stronger pinned model.
5. Choose review effort from risk. Routine deterministic `backend_code` review uses Codex `gpt-5.6-terra` with `medium`; routine `frontend_code` and visual review use Claude Code `sonnet` with `medium`. Raise review effort to `high` or `xhigh` only for security, migration, difficult correctness, broad architecture, or genuinely ambiguous visual judgment — the Claude Code model itself stays `sonnet`.
6. For bounded mechanical edits, discovery, or inexpensive preflight work, prefer a fast model with low or medium reasoning: Codex's fastest/cheapest available model for that lane, or a delegated Claude Code node's model set to `haiku` (not `sonnet`) with `low` or `medium` reasoning effort. This covers read-only exploration, documentation/API research, test/log analysis, and other bounded discovery work — not implementation or review nodes, which stay at the tiers already set in points 2 through 5.
7. When the current catalog or destination support is not observed, leave Codex values null for the host default or use Claude's portable `sonnet` default. Do not invent a model identifier.

These are planning decisions, not execution authorization. Keep different reasoning-effort choices on different nodes when their work differs; do not raise every worker to the parent task's reasoning level by default.

For a runtime worker, select deterministically:

1. preferred allowed provider when it matches the current host provider;
2. current host provider when allowed;
3. otherwise defer with `runtime_unavailable`: a node whose allowed/preferred providers do not include the current host is not executable on this host, with no cross-host fallback.

After choosing a provider, the selector binds that provider's PLAN options. If none were declared, Codex keeps null model/effort values for the host default and Claude production waves use `sonnet`. Every launch directive includes the complete binding (`runtime_binding.model`, `.reasoning_effort`) and the parent copies it to the allocated RUN mission or review worker. Codex task creation maps non-null `model` and `reasoning_effort` to `model` and `thinking`. A Claude Code host passes each node's own `model` (and non-null `reasoning_effort` as `effort`) directly into that node's `agent()` call inside the Workflow script — one Workflow call may freely mix models and reasoning efforts across its nodes, since selection happens per spawned agent, not per wave.

Codex app threads and Claude Dynamic Workflow remain execution adapters. They do not change graph readiness, authorization, result validation, or integration rules. A destination rejecting a model/effort pair is a launch failure to record and replan; it is not permission to silently substitute another model.

Derive a Claude tool profile from existing node semantics instead of adding another PLAN field: missions use `mission_write`, frontend/backend reviews use `code_review_readonly`, and visual reviews use `visual_review_readonly`. Group Claude waves by tool profile only; model and reasoning effort do not require separate waves since each node's `agent()` call already carries its own. Every profile uses an exact allowlist. Mission profiles require `EnterWorktree` and the bounded write tools. Review profiles require `EnterWorktree` to bind reads to the validated `review_path`, but omit `Edit`, `Write`, `NotebookEdit`, and `Bash`; visual review consumes retained screenshots or other existing evidence until a new read-only browser tool is explicitly vetted for the Claude Code host.

Launch a graph wave that includes any review node, or that must enforce these tool profiles and per-node `EnterWorktree` at the runtime layer, with `assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js` (`scriptPath`, `tool_profile`, and typed `nodes[]` as structured `args`) — see `assets/templates/MISSION_RUNBOOK.template.md`. The flat `assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js` has no `node_kind`, `tool_profile`, or `EnterWorktree` handling and covers only single-role, all-mission waves.

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
