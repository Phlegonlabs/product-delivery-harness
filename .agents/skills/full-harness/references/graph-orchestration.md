# Typed Graph Orchestration

Use this reference for current PLAN schema v6 and RUN schema v11 typed graphs, conditional routing, retries, and graph traces. Older typed-graph schema pairs remain validatable as manifests but cannot be selected or executed.

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

## System Review And Route Precedes The Graph

`System Review And Route` is defined in `execution-state-model.md` and runs before this graph exists. The only graph-specific rule: it is not a PLAN node and never appears in RUN `graph_state`.

If the large route has no usable agent capability, write missions may still run as `sequential_parent` while each PLAN mission remains `executor: runtime_worker`, one mission at a time. An independent runtime-review node cannot use the same parent context as its fresh reviewer and remains `independent_reviewer_unavailable` until a suitable driver or allowed host exists. See `execution-state-model.md`'s `sequential_parent` definition for the binding, authorization, and blocking rules; keep the mission on its existing runtime-worker executor.

For current PLAN v6 typed graphs, use graph dependency edges as the only cross-mission ordering source. PLAN v4 uses the same graph rule. PLAN v2 and v3 retain the legacy `missions[].depends_on` DAG. Task dependencies remain flat, same-mission, and acyclic.

## Nodes And Executors

Use these node kinds:

```text
mission       -> one existing mission contract and write unit
verifier      -> a declared deterministic verifier or typed read-only runtime review
approval      -> an explicit human decision
external_wait -> review or another observed external state
lifecycle     -> one authorization-ledger action owned by the parent
```

Use these executors:

```text
runtime_worker  -> parent, Codex, Claude, or another observed worker provider
harness_parent  -> serialized parent lifecycle/gate action (not a mission)
local_command   -> deterministic verifier command
external_system -> polling or event observation
human           -> explicit approval or contract decision
```

The node is the workflow identity. A thread, Claude session, process, worktree, or worker ID is an attempt binding recorded in RUN, never the node ID.

A `push` lifecycle node must declare an exact branch `target`. When `target` is absent the selector falls back to `"*"`, and schema v11 forbids `"*"`-scoped grants for head-bound actions, so a target-less push node is permanently `action_not_authorized`.

A verifier using `runtime_worker` is a read-only review node, not a mission. Its `review` contract names `type` (`frontend_code`, `backend_code`, or `visual`), optional `stage` (`preintegration` by default or `integration`), reviewed mission IDs, repository scope, and required evidence. RUN binds the attempt in `review_workers[]` to one exact current covered-mission worktree or integrated SHA. Persist that binding with `harness_transition.py reserve-review-dispatch` after selection and before the runtime side effect. Complete only that reserved attempt with `record-review-attempt`; a raw launch or log-only verdict is never accepted. It never receives a mission lease, write scope, branch, or commit authority.

For full-stack UI delivery, use this default shape:

```text
contract freeze
  -> frontend mission -> frontend_code review --fix_required--> same frontend task/worktree
  -> backend mission  -> backend_code review  --fix_required--> same backend task/worktree
  -> serial integration into one unified head
  -> fresh integration-stage reviewers --fix_required--> bounded repair mission
  -> one broad final deterministic validation on the fixed candidate SHA
```

Keep frontend and backend review separate when both surfaces exist. Combine them only for a genuinely single-surface change and record the reason. A pre-integration review reports every blocking finding it can establish in one bounded pass; do not stop after the first finding or open another review merely to confirm it. A `fix_required` result is parent-side correction handling: deduplicate findings by file, location, and root cause, send the consolidated set to the original mission task/thread, keep its existing worktree and branch, require its focused verifier on a changed head, then re-arm the same review node. Do not model that correction as a new mission or create a new worktree from an integration branch that lacks the reviewed head. Current PLAN v6 runtime review nodes allow at most two total attempts: the initial review plus one repair re-review, followed by a blocked or human-owned exit. Integration-stage reviewers are fresh parent-dispatched agents and become ready only after every covered mission is integrated and `integration_head_sha` exists. Skip that dispatch when the integration head's tree is byte-identical to a tree an already-passed pre-integration review of the same type covers — the reviewed commit itself, or a merge commit with the same tree recorded as `integration.integration_tree_sha` and `review_workers[].tree_sha` — and record the node as `skipped`. A dispatched integration reviewer reads a seam-scoped packet: the per-mission reviewed heads are listed and the pass focuses on what combination changed. They may use bounded repair-route nodes because repair worktrees start from the reviewed integration head. A repair changes the candidate SHA and invalidates the prior integration review. This shape names one frontend mission and one visual review for readability; scope each pair to one page (or a small, genuinely tightly-coupled group of pages) per `contract-and-traceability.md`'s mission-granularity corollary, and repeat the shape per page/group rather than letting one frontend mission span the whole UI matrix with a single visual review fired once at the end.

PLAN `required_reviews` lists the applicable review types. Validation requires a matching runtime-worker verifier for every listed type, so the planner cannot mark a review required only in prose. Use an empty list only when none of the three review surfaces applies, and record that rationale in the human plan view. Render each reviewer a compact packet with the exact reviewed SHA, its declared scope, scoped changed paths/diff, applicable acceptance rows, required evidence, and unresolved prior findings. Refer to PLAN/RUN by identity and path instead of copying their full manifests into the prompt.

## Root-Cause Repair Escalation

The parent turns a `fix_required` result into one consolidated repair packet, not a checklist of isolated examples. Group findings by semantic root cause and failure family. For each family, include the affected primitive, all known variants, the narrow approach that failed or is rejected, the structural repair objective, the acceptance-matrix cases that prove the family is closed, and the review attempts already consumed across PLAN revisions.

Escalate from local correction to structural repair when any of these is true:

- two or more findings are adjacent variants of the same parsing, validation, serialization, protocol, state-machine, or boundary primitive;
- a re-review finds another variant of a family the repair claimed to close; or
- the proposed repair adds another special-case branch without proving that the input grammar or state space is closed and bounded.

Structural repair means the smallest coherent change that closes the named family, not an automatic rewrite or abstraction. A regular expression remains acceptable for a genuinely closed local grammar; an open grammar needs an appropriate scanner, parser, state machine, or other structure-aware mechanism. Freeze the failure-family matrix in the task acceptance criteria before writing. If the structural change does not fit the mission scope or frozen contract, the worker returns `REFINEMENT_REQUEST` or `contract_gap` before another mutation.

Review limits follow a stable mission + review surface + root-cause lineage, not only the current node ID. A PLAN revision carries forward prior attempts and unresolved findings in its owner-decision source, mission stop conditions, and review packet. It does not reset the default initial-plus-one-re-review budget. Once that cumulative budget is exhausted, stop at `blocked`. One successor structural-repair generation may receive exactly one additional review attempt only when the retained failure family is still open and an explicit owner decision names its decision ID in the exact quoted user turn, approves the changed strategy and acceptance matrix, and records the user-turn reference. The lineage may use this gate once. A broad request to continue the project does not satisfy it. The successor review node sets `max_attempts` to only that remaining allowance; it never receives a fresh default of two.

## Multi-Reviewer Fan-Out

One review node per surface is the required planning default. Same-surface fan-out multiplies context and review cost, so add it only when the user explicitly requests independent reviewers or a recorded high-impact risk justifies them — security-sensitive code, destructive or irreversible migrations, or genuinely ambiguous visual judgment. Prefer one reviewer with the appropriate reasoning effort for routine work. Record the reason in the human plan view whenever fan-out is used.

Express it with the existing typed graph mechanism; no new PLAN or RUN schema field is required. Instead of one `kind: "verifier"` node for the surface, declare N verifier nodes that are identical in what they judge:

- same `review.type` (`frontend_code`, `backend_code`, or `visual`);
- same reviewed `mission_ids` and repository `scope`;
- the same incoming `dependency` edges, so every reviewer binds to the SAME exact covered-mission worktree or integrated SHA;
- each its own node ID, its own attempt, and no shared state with the others — an independent read-only review, never a mission, and never granted write scope, a lease, or commit authority.

These still count as normal `runtime_worker` review nodes for `required_reviews` validation (each is a matching verifier for its type) and for the shared runtime budget. Every reviewer is dispatched by the parent and none may delegate. Give the reviewers different `reasoning_effort` or providers if you want diversity of judgment; keep any delegated Claude Code model at `sonnet` per the Runtime Binding rules.

Reconciliation is a PARENT-SIDE convention, not a graph feature. The N reviewer results are independent node outcomes; the parent combines them into ONE proceed/block decision. For a single-mission pre-integration review, a `fix_required` decision goes back to the original mission task/worktree. After the mission produces a changed head, re-arm every planned sibling review node for that surface, including siblings that passed the stale head. Before integration, every planned single-mission review node directly reached from that mission and every active current-head `review_workers[]` attempt must retain an exact-head PASS. One active current-head `fix_required`, dormant review, stale SHA, or missing worker blocks integration. Historical or superseded attempts remain preserved for audit and do not satisfy or bypass the current set. A review that covers multiple missions is a post-integration batch review and cannot replace the required single-mission worktree review. A PLAN without that eligible review remains blocked from integrating the mission. For post-integration review, the decision may drive the surface's bounded repair route. Name the any-blocks rule in the human plan view so reconciliation is auditable. Each reviewer's own `outcome` and `findings` are recorded on its `run.review_workers` entry, separate from `node_states[node_id].last_outcome` (the parent's routing verdict), so historical findings remain on the record.

- **Any-blocks (current rule).** Treat the surface as `fix_required`/blocked if ANY active current-head reviewer returns `fix_required`; proceed only when every planned current-head review node and worker is an exact-head PASS. Use this rule for every pre-integration surface, including subjective visual judgment, so one unresolved finding cannot enter integration.

## Dependency And Route Edges

`dependency` means the target consumes a completed prerequisite. It always uses outcome `pass`, has no traversal count, and the complete dependency subgraph must be acyclic.

`route` means the target activates only for named source outcomes such as `pass`, `fix_required`, `retryable_failure`, `blocked`, or `contract_gap`.

One exception to the plain reading above: a review node's `pass` edge to a deterministic (`local_command` or `harness_parent`) gate must be a `route`, not a `dependency`, even though the gate does consume a completed prerequisite. Validation requires it — `dependency` there fails with "review pass requires an outgoing route to a deterministic final gate".

A route cycle is valid only when:

- every route edge inside the cycle has `max_traversals`;
- the cycle has an edge to a node outside the cycle;
- every new attempt receives a new attempt ID and preserves old evidence;
- exhaustion routes to a blocked or human-owned stop rather than silently continuing.

Do not add an expression language. Put complex decisions in a verifier node and route on its declared outcome.

Every `runtime_worker` or parent-executed mission declares at least one failure outcome: prefer `retryable_failure`, otherwise use `blocked`. The selector copies that permitted `failure_outcome` into the immutable workflow handoff so a null or failed agent never emits an outcome the PLAN forbids.

## Serialized Same-Repository Host Handoff

Defined once in `execution-state-model.md`. The only graph-specific rule: the graph does not gain a host-handoff node or a second state store.

## Readiness And Outcomes

Run `scripts/select_ready_nodes.py` for PLAN v6 with RUN v11. A node is logically ready only when:

- plan readiness and execution authorization are current;
- RUN `control.desired_state` is `running`; `paused` and `cancelled` fail closed for every node;
- its phase is `dormant` or `ready` and its attempt budget remains; runtime reviews consume the stable `review.lineage_id` budget in `RUN.review_lineages`, not a fresh node-local budget after replan;
- all dependency sources succeeded with `pass`, except that a current RUN-v11 runtime review may consume a covered mission's validated `worker_passed` exact head before the parent integrates it;
- at least one incoming route matches when route edges exist, except that the same pre-integration dependency activates the review's initial attempt while a matching repair route activates later attempts;
- no node blocker remains;
- mission nodes still have a queued or ready mission state.

Provider composition is a readiness question, not a selector question. `scripts/harness_graph.py` accepts an `allowed_providers` list that excludes the running host on purpose — a host mismatch is a RUN-time fact, not an authoring error — and `scripts/select_ready_nodes.py` then defers such a node with `runtime_unavailable` for as long as the run lasts. Nothing below readiness catches a PLAN that no available host can finish. So before Plan Readiness passes, check every `runtime_worker` node's `allowed_providers` against the hosts this delivery will actually run under, not just the next selected route. A node no available host can execute is a blocking readiness gap: widen its `allowed_providers`, arrange the run on the other host, or have the user explicitly acknowledge it as deferred and record that acknowledgement in the plan. Do not let readiness pass and surface it later as a `runtime_unavailable` deferral — by then the early missions have already integrated.

The selector first computes the logical graph frontier, then resolves runtime bindings and action authorization. It applies the existing write-scope and runtime-resource conflict rules to ready mission nodes. Write-capable `runtime_worker` nodes draw from the minimum of PLAN capacity, runtime capacity, and currently available worker slots. Read-only nodes — reviews, approvals, and external waits — draw from their own budget of the same size, because they consume no isolation capacity and cannot write; charging them against the writer budget only let a streaming review starve the writer it exists to overlap with. Read-only nodes never bypass action authorization. The selector returns a derived selector-only `execution_route`: `managed_sequential` for fewer than two actually selected safe write missions and `parallel_graph` for two or more. This label is not a PLAN/RUN field and does not replace the separate `runtime_driver` transport binding. Non-runtime nodes remain explicit directives such as `run_verifier`, `await_approval`, `poll_external`, or `run_lifecycle_action`.

## Runtime Binding

PLAN runtime policy declares `allowed_providers`, an optional `preferred_provider`, and optional `provider_options` keyed by an allowed provider. Plan Mode chooses these values from mission complexity, latency/cost needs, and the user's explicit model preference. Codex and Claude Code options contain `model` plus a nullable `reasoning_effort`; keep effort null when the provider default is intentional. Pi keeps `model` null so its installed role, primary model, and fallback order remain authoritative, but may carry a non-null per-node `reasoning_effort`. Generic providers keep both values null. Model names are portable strings because the destination host remains authoritative for its current catalog. RUN records the actual host and its observed capabilities. A provider, model, or effort preference is not proof that the destination supports it.

Use this Plan Mode order only while authoring options for the provider that will execute the node. These Codex and Claude Code defaults are not cross-provider fallback hints. After the current host resolves a node to Pi, skip the Codex/Claude model choices below, keep `provider_options.pi.model` null, and use the installed Pi role and its declared fallbacks. A delegated Claude Code node never defaults above `sonnet`: reserve any stronger pinned Claude model — whichever premium model opened this session, such as `claude-fable-5` — for the parent's own coordination and planning, not for a node the parent hands off. For a node whose work is bounded, mechanical, or purely read-only (see point 6 below), default its Claude Code model to `haiku` instead of `sonnet` — reserve `sonnet` as the default for every node whose work involves real implementation judgment or review, and reserve anything above `sonnet` for the parent's own coordination and planning as already stated.

1. Preserve an explicit user-selected provider, model, or reasoning effort.
2. For high-risk architecture, security, migration, difficult debugging, or difficult correctness, raise reasoning effort to `xhigh` for the chosen Codex or Claude Code option while keeping a delegated Claude Code node's model at `sonnet`. The run's final review — the final synthesis pass over the integration head — needs no trigger: it runs at `xhigh` by default (Codex `gpt-5.6-sol`, Claude Code `sonnet`).
3. For general-purpose nodes and backend implementation, prefer Codex `gpt-5.6-terra` with `high` reasoning; keep Claude Code `sonnet` with `high` reasoning as the availability fallback.
4. Frontend/UI implementation prefers Codex `gpt-5.6-sol` with `high` reasoning; a delegated Claude Code node still defaults to `sonnet` with `high` reasoning rather than a stronger pinned model.
5. Choose review effort from risk without switching the selected provider. On a Codex host, routine deterministic `backend_code` review uses `gpt-5.6-terra` with `medium`; on a Claude Code host, routine `frontend_code` and visual review use `sonnet` with `medium`. On a Pi host, every review uses the installed `reviewer` role with a null PLAN model. Raise review effort to `high` or `xhigh` only for security, migration, difficult correctness, broad architecture, or genuinely ambiguous visual judgment — a Claude Code model itself stays `sonnet`. The run's final review is not routine: it uses Codex `gpt-5.6-sol` with `xhigh` on a Codex host, Claude Code `sonnet` with `xhigh` on a Claude Code host, or the installed Pi `reviewer` with `xhigh` on a Pi host.
6. For bounded mechanical edits, discovery, or inexpensive preflight work, prefer a fast model with low or medium reasoning: Codex's fastest/cheapest available model for that lane, or a delegated Claude Code node's model set to `haiku` (not `sonnet`) with `low` or `medium` reasoning effort. This covers read-only exploration, documentation/API research, test/log analysis, and other bounded discovery work — not implementation or review nodes, which stay at the tiers already set in points 2 through 5.
7. When the current catalog or destination support is not observed, leave Codex values null for the host default or use Claude's portable `sonnet` default. Do not invent a model identifier.

These are planning decisions, not execution authorization. Keep different reasoning-effort choices on different nodes when their work differs; do not raise every worker to the parent task's reasoning level by default.

For a runtime worker, select deterministically:

1. preferred allowed provider when it matches the current host provider;
2. current host provider when allowed;
3. otherwise defer with `runtime_unavailable`: a node whose allowed/preferred providers do not include the current host is not executable on this host, with no cross-host fallback.

After choosing a provider, the selector binds that provider's PLAN options. If none were declared, Codex keeps null model/effort values for the host default, Claude production waves use `sonnet`, and Pi keeps both values null so the selected Pi role resolves its configured model and fallback. Every launch directive includes the complete binding (`runtime_binding.model`, `.reasoning_effort`) and the parent copies it to the allocated RUN mission or review worker. Codex task creation maps non-null `model` and `reasoning_effort` to `model` and `thinking`. A Claude Code host passes each node's own `model` (and non-null `reasoning_effort` as `effort`) directly into that node's own `agent()` call inside the Workflow script — one Workflow call may freely mix models and reasoning efforts across its nodes, since selection happens per spawned agent, not per wave. A Pi host passes the mission surface to its installed role (`frontend_designer`, `worker`, or `reviewer`), keeps the resolved base model and fallback order, applies any non-null PLAN effort through Pi's per-run thinking suffix, and records what Pi actually reports.

Codex app threads, Claude Dynamic Workflow, and Pi subagents remain execution adapters. They do not change graph readiness, authorization, result validation, or integration rules. A destination rejecting a model/effort pair is a launch failure to record and replan; it is not permission to silently substitute another Harness model. Pi may use only its already-declared role fallback policy.

Derive a Claude tool profile from existing node semantics instead of using it as a permission claim: missions use `mission_write`, frontend/backend reviews use `code_review_readonly`, and visual reviews use `visual_review_readonly`. Group Claude waves by tool profile only; model and reasoning effort do not require separate waves since each node's `agent()` call already carries its own. A profile is a label carried on the node, not a tool allowlist: the workflow script validates that the wave's node kinds match the profile and writes the corresponding instructions into each agent's prompt, and the child inherits the parent's tools. Mission prompts instruct the agent to enter its worktree before any repository action; review prompts instruct it to read only and not to edit, commit, or run mutating tools. Read-only-ness here is enforced by the mission contract, the structured result, and scope/Git validation on the way back — not by removing tools from the child. Do not claim permission-level delegation prevention. A PLAN review that requires `chrome_devtools` carries that explicit requirement beside the profile and dispatches only after the exact Claude reviewer surface has a fresh `claude_in_chrome` child-session probe.

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

Do not retry the same failed approach more than twice. A runtime review is stricter: `max_attempts` cannot exceed 2, meaning one initial review and at most one repair re-review. Count attempts cumulatively for the same mission, surface, and root-cause lineage across successor PLAN revisions. Replanning changes the contract; it does not erase the attempt history. After the configured or cumulative bound is exhausted, stop at `blocked` and identify the required decision. Apply the explicit structural-repair owner gate above before authoring any successor review node.

## Validation And Integration

Use this order:

```text
validate PLAN/RUN
-> select graph frontier
-> re-observe runtime and Git
-> reserve the exact review dispatch in RUN when applicable
-> allocate mission attempt and workspace when applicable
-> execute adapter
-> validate node result
-> validate worker result and actual diff
-> integrate serially
-> run integration and batch verifiers
-> update RUN graph and mission state
-> recompute frontier
```

A node result is a candidate. Only a mission node with an integrated mission PASS may become `succeeded` with outcome `pass`. A completed thread, Claude workflow, process exit, worker commit, or structured JSON response alone does not satisfy downstream dependencies.
