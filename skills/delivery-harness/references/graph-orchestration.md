# Typed Graph Orchestration

Use this reference for current PLAN schema v6 and RUN schema v11 typed graphs, conditional routing, retries, and graph traces. Historical schema pairs use their exact pinned bundle and are never migrated silently.

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

- The stable org graph is the role contract: planner, mission worker, frontend reviewer, backend reviewer, visual reviewer, security reviewer, approval owner, integrator, and lifecycle owner. Roles define responsibility, context, tools, and handoff shape; they are not persistent live processes.
- The temporary work graph is the canonical PLAN graph plus RUN graph state for one delivery. It owns current nodes, dependencies, routes, attempts, evidence, and runtime bindings.

Instantiate stable roles through existing node kinds, executors, review types, mission contracts, and parent ownership. Change the work graph only through a parent-owned PLAN revision, accepted refinement, bounded route, retry, cancellation, or supersession. Do not let a workflow script or worker mutate graph state directly.

## Authority And Projection

Keep one control plane:

```text
PLAN graph definition
-> parent graph scheduler
-> runtime-neutral launch directive
-> reserved node attempt (RUN lock)
-> native agent, command, external wait, or human executor outside the lock
-> validated node result and evidence
-> record-node-result (RUN lock)
-> RUN graph state
-> next frontier
```

PLAN owns static nodes, edges, outcomes, attempt limits, and runtime policy. RUN owns node attempts, outcomes, edge traversals, runtime bindings, and evidence. Git and live runtime observations remain separate facts. Do not add another graph database or let a workflow script edit PLAN/RUN.

## System Review And Route Precedes The Graph

`System Review And Route` is defined in `execution-state-model.md` and runs before this graph exists. The only graph-specific rule: it is not a PLAN node and never appears in RUN `graph_state`.

If the large route has no usable agent capability, write missions may still run as `sequential_parent` while each PLAN mission remains `executor: runtime_worker`, one mission at a time. An independent runtime-review node cannot use the same parent context as its fresh reviewer and remains `independent_reviewer_unavailable` until a suitable driver or allowed host exists. See `execution-state-model.md`'s `sequential_parent` definition for the binding, authorization, and blocking rules; keep the mission on its existing runtime-worker executor.

For current PLAN v6 typed graphs, use graph dependency edges as the only cross-mission ordering source; older schemas follow `legacy-pins.md#run-schemas-before-v11`. Task dependencies remain flat, same-mission, and acyclic.

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
runtime_worker  -> parent or an observed native worker
harness_parent  -> serialized parent lifecycle/gate action (not a mission)
local_command   -> deterministic verifier command
external_system -> polling or event observation
human           -> explicit approval or contract decision
```

PLAN v6 requires each `local_command` or `harness_parent` verifier node to reference a `batch_verifiers` or `final_gates` entry. Every declared batch/final gate needs at least one such node; multiple nodes may share a gate. Task, worker, and mission-integration verifiers use their existing execution paths, not deterministic graph nodes. A `runtime_worker` review may reference any declared verifier, but does not execute its command or fill `batch_gate_results` / `final_gate_results`. These checks do not change validation of older schemas used for recovery.

The node is the workflow identity. A task, host session, process, worktree, or worker ID is an attempt binding recorded in RUN, never the node ID.

Non-mission nodes follow a durable reserve/execute/record protocol. The parent reserves an `approval`, `external_wait`, `lifecycle`, or deterministic batch/final verifier attempt with `reserve-node-attempt` under the RUN lock, performs the check, wait, or lifecycle side effect outside that lock, and records the matching outcome and evidence with `record-node-result` under a new short lock. A local verifier reservation persists its exact request and attempt nonce in RUN before `--request-out` is published. `verifier_runtime.py` guards the Git checkout before and after execution and echoes that nonce. The tracked RUN dirty exception remains content-protected across the subprocess and is rehashed before result recording, so candidate code cannot alter coordination state while returning PASS. An interrupted verifier closes as `blocked` with a blocker and no fabricated result. A lifecycle transition is an evidence receipt only; it never invokes Git, a process, or a remote service, and lifecycle work retries only through an explicit bounded route.

Task/worker, mission-integration, batch, and final verifiers declare an explicit `host` policy: fresh exact-SHA evidence and source/Git guards in the bound checkout. Worktrees and read-only declarations do not provide process confinement. Container verifiers in older pins follow `legacy-pins.md#container-verifiers-before-066`.

Harness 0.38+ PLANs contain no `push` lifecycle node and RUN push stays false. Archive and publication follow `branch-promotion-contract.md#managed-run-archive-before-promotion`; a pre-0.38 recovery PLAN follows `legacy-pins.md#pre-038-run-branch-push`.

`lease-worker` accepts an already active exact execution identity or materializes one only when the matching action has an active wildcard grant. The wildcard remains the user's authorization scope; appending an exact target to the receipt does not set `authorized` or expand the grant. Lifecycle and push targets are never materialized here. The lease also derives the selector's provider, driver, model, effort, worker runtime, workspace mode, and completion channel, and rejects incompatible caller flags. Current drivers do not dispatch app tasks; historical identities remain under their exact pinned bundle.

A verifier using `runtime_worker` is a read-only review node, not a mission. Its `review` contract names `type` (`frontend_code`, `backend_code`, `visual`, or `security`), optional `lenses` (the lens list of a combined review; `type` is its widest lens in the order security, visual, frontend_code, backend_code), optional `stage` (`preintegration` by default or `integration`), reviewed mission IDs, repository scope, and required evidence. A `security` node must use the integration stage, cover every PLAN mission, and declare scope that contains every covered mission write scope. RUN binds the attempt in `review_workers[]` to one exact current covered-mission worktree or integrated SHA. Persist that binding with `harness_transition.py reserve-review-dispatch` after selection and before the runtime side effect. Complete only that reserved attempt with `record-review-attempt`; a raw launch or log-only verdict is never accepted. It never receives a mission lease, write scope, branch, or commit authority.

For full-stack UI delivery, use this default shape:

```text
contract freeze
  -> frontend mission, backend mission (worker_passed, then the Worker Result Gate)
  -> serial integration into one unified head
  -> one combined review, lenses [code, visual if UI, security] --fix_required--> one consolidated repair, then one targeted re-check
  -> one broad final deterministic validation on the fixed candidate SHA
```

A review node reports every blocking finding it can establish in one bounded pass. Under `review_policy: final_candidate` it depends on the integrated missions and becomes ready once every covered mission is integrated and `integration_head_sha` exists, except for the untouched conditional repair below; the parent re-arms it after `reconcile-candidate-head` records the repair. A `fix_required` result is parent-side correction handling: wait until every required review of that candidate has returned, deduplicate findings by file, location, and root cause, and send the consolidated set once, per `gen-verify-correct.md`. Non-blocking suggestions go to the Epic backlog and never make `fix_required`. A repair changes the candidate SHA and invalidates the prior integration review. The `security` lens never skips: it loads the project's `code_security_verification` binding and evaluates the unified trust boundaries from a fresh context. Under `per_mission`, each mission also has a pre-integration review node that depends on its mission, consumes its `worker_passed` head, and returns `fix_required` to the original task and worktree; the same node re-arms on the changed head, and non-security integration reviews may skip under `verification-gates.md`'s Fresh integration review gate. Runtime review nodes follow the attempt budget in the Root-Cause Repair Escalation section below. Scope missions per feature batch (`execution-task-decomposition.md#mission-cohesion-gate`).

PLAN `required_reviews` lists the applicable review types. Validation requires a matching runtime-worker verifier for every listed type; a combined node counts for each lens it lists, so the planner cannot mark a review required only in prose. Every new RUN also requires an explicit `security_review` policy: code delivery uses `required`; a non-code delivery may use `not_applicable` only with a reason. Older valid PLAN/RUN pairs remain readable and are never silently rewritten. The security review uses `code_review_readonly`, covers all missions, and runs before broad final validation. Render each reviewer a compact packet with the exact reviewed SHA, its declared scope, scoped changed paths/diff, applicable acceptance rows, required evidence, skill-binding slot when applicable, the security review's `required_checks` with the `execution_key` of each check's PASS at that SHA, and unresolved prior findings (`render_review_packet.py --max-diff-bytes N` bounds the diff — default 50000 bytes, truncation marked in the packet heading). Refer to PLAN/RUN by identity and path instead of copying their full manifests into the prompt.

### Optional Repair-Only Mission

A `final_candidate` PLAN may predeclare one isolated consolidated repair mission using existing graph fields.
The repair node has `max_attempts: 1` and only one incoming `fix_required` route from the final review.
That route has `max_traversals: 1`; a bounded `pass` route returns from repair to the same review.
The review has `max_attempts: 2` and covers the repair mission in `review.mission_ids` and its write scope.
Keep normal implementation dependencies on the review; do not add a repair-to-review dependency that blocks the first review.

```json
[
  {"id":"E-FINAL-REPAIR","kind":"route","from":"N-FINAL-REVIEW","to":"N-REPAIR","on_outcomes":["fix_required"],"max_traversals":1},
  {"id":"E-REPAIR-RECHECK","kind":"route","from":"N-REPAIR","to":"N-FINAL-REVIEW","on_outcomes":["pass"],"max_traversals":1}
]
```

This is a pattern, not a new schema flag or scheduler.
The first review may run while that repair alone remains untouched: queued mission, dormant node, zero attempts and untraversed route.
Every other covered mission must already be integrated.
A first-review PASS leaves the repair dormant; closeout recognizes the untaken route without inventing a repair PASS or integration.
A `fix_required` activates the repair's one authorized writer attempt.
Record its result, integrate it and run its focused integration checks through the normal mission protocol.
The bounded pass route then permits one fresh targeted recheck on the repaired unified SHA.
A failed recheck ends the review budget; remaining findings enter the Isolated Repair Protocol in `verification-gates.md` as scoped repairs that consume no review attempt.

All source, scope, authorization, security, browser and evidence gates still apply.
A repair not declared before execution needs the existing owner-authorized PLAN revision procedure.
A PLAN without `review_policy` retains `per_mission` semantics; this initial-review exception does not apply to it.

## Root-Cause Repair Escalation

Use one review, one consolidated repair, and one targeted re-check (`gen-verify-correct.md`). Group the repair by root cause and freeze its acceptance matrix before writing. A scope or contract gap returns upstream.

Carry consumed attempts across revisions by stable mission + review surface + root-cause lineage. Replacing a node never resets that budget. The scripts enforce each node's `max_attempts`; the parent retains the cross-revision history. A failed re-check stops at `blocked`. One third attempt needs the owner's quoted decision, changed strategy, and acceptance matrix recorded in `docs/goal/DECISIONS.md`. The successor node permits only that one attempt.

## Multi-Reviewer Fan-Out

Agent configuration and AGENTS instructions select review staffing. Fan-out needs an explicit user request or a recorded high-impact risk. Declare N verifier nodes that judge the same thing: the same `review.type` and `lenses`, the same reviewed `mission_ids` and `scope`, and the same incoming `dependency` edges, so every reviewer binds the SAME exact worktree or integrated SHA. Each has its own node ID and attempt, and is an independent read-only review: never a mission, never granted write scope, a lease, or commit authority. The parent dispatches every reviewer and none may delegate. They count as normal `runtime_worker` review nodes for `required_reviews` validation and the shared runtime budget.

Reconciliation is a PARENT-SIDE convention, not a graph feature. The parent combines the N independent outcomes into ONE proceed/block decision. Each reviewer's own `outcome` and `findings` are recorded on its `run.review_workers` entry, separate from `node_states[node_id].last_outcome` (the parent's routing verdict), so historical findings remain on the record.

- **Any-blocks (current rule).** Treat the surface as `fix_required`/blocked if ANY active current-head reviewer returns `fix_required`; proceed only when every planned current-head review node and worker is an exact-head PASS. After the repair produces a changed head, re-arm every planned sibling review node, including siblings that passed the stale head. Under `per_mission`, an active current-head `fix_required`, dormant review, stale SHA, or missing worker blocks integration, and historical or superseded attempts stay for audit without satisfying the current set. Name the rule in the human plan view.

## Dependency And Route Edges

`dependency` means the target consumes a completed prerequisite. It always uses outcome `pass`, has no traversal count, and the complete dependency subgraph must be acyclic.

`route` means the target activates only for named source outcomes such as `pass`, `fix_required`, `retryable_failure`, `blocked`, or `contract_gap`.

One exception to the plain reading above: a review node's `pass` edge to a deterministic (`local_command` or `harness_parent`) gate must be a `route`, not a `dependency`, even though the gate does consume a completed prerequisite. Validation requires it — `dependency` there fails with "review pass requires an outgoing route to a deterministic final gate".

Incoming routes are OR-matched: one matching route activates the target. Incoming dependencies are AND-matched: every source must pass. Use several routes into one node only for alternative paths, such as a first review and a repair re-review. When a final gate must wait for several reviewers, route each review's `pass` to its own gate, then join those gates into the final gate with `dependency` edges. Several `pass` routes into one final gate would let it run after the first reviewer passes while another is still pending or returned `fix_required`.

Platform handoffs do not use the review-route exception. In `platform-delivery/1`, connect stage contributors to the completion mission and that completion mission to every next-stage mission with dependency paths. Keep feature-acceptance paths dependency-only so all carrying missions AND into the accepting gate. Routes remain correction and review controls, not platform completion evidence.

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
- its phase is `dormant` or `ready` and its attempt budget remains; the scripts enforce node-local `max_attempts`, while the parent preserves cumulative review history across revisions;
- all dependency sources succeeded with `pass`, except that, under `per_mission`, a planned pre-integration review may consume a covered mission's validated `worker_passed` exact head before the parent integrates it;
- at least one incoming route matches when route edges exist (OR, not AND; see Dependency And Route Edges), except that the same pre-integration dependency activates the review's initial attempt while a matching repair route activates later attempts;
- no node blocker remains;
- mission nodes still have a queued or ready mission state.

Provider composition is a readiness question, not a selector question. `scripts/harness_graph.py` accepts an `allowed_providers` list that excludes the running host on purpose — a host mismatch is a RUN-time fact, not an authoring error — and `scripts/select_ready_nodes.py` then defers such a node with `runtime_unavailable` for as long as the run lasts. Nothing below readiness catches a PLAN that no available host can finish. So before Plan Readiness passes, check every `runtime_worker` node's `allowed_providers` against the hosts this delivery will actually run under, not just the next selected route. A node no available host can execute is a blocking readiness gap: widen its `allowed_providers`, arrange the run on the other host, or have the user explicitly acknowledge it as deferred and record that acknowledgement in the plan. Do not let readiness pass and surface it later as a `runtime_unavailable` deferral — by then the early missions have already integrated.

Before mission launch, `python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan docs/goal/PLAN.md --run docs/goal/RUN.md --repo-root <absolute-root> record-observation` records the host and PLAN revision/digest. Global flags precede the subcommand. Missing or stale required observations block readiness. Browser and external/mutable checks retain their own nodes and authorization.

The selector first computes the logical graph frontier, then resolves runtime bindings and action authorization. It applies the existing write-scope and runtime-resource conflict rules to ready mission nodes. Write-capable `runtime_worker` nodes draw from the minimum of PLAN capacity, runtime capacity, and currently available worker slots. Runtime reviewers and writers share the observed worker-slot budget; reviewers do not consume writer isolation capacity. Approval and external-wait directives do not consume an agent slot unless their declared executor launches one. Read-only nodes never bypass action authorization. The selector returns a derived selector-only `execution_route`: `managed_sequential` for fewer than two actually selected safe write missions and `parallel_graph` for two or more. This label is not a PLAN/RUN field and does not replace the separate `runtime_driver` transport binding. Non-runtime nodes remain explicit directives such as `run_verifier`, `await_approval`, `poll_external`, or `run_lifecycle_action`.

The parent must reserve a selected non-runtime directive before executing it. `reserve-node-attempt` is the short RUN-locked reservation; the deterministic batch/final verifier, approval, external wait, or lifecycle side effect runs after that lock is released. `record-node-result` then reacquires the lock, requires the matching attempt and evidence, records the declared outcome, and traverses matching route edges. It does not perform the lifecycle action and cannot be replaced by a log-only result.

## Runtime Binding

PLAN declares `allowed_providers`, optional `preferred_provider`, and optional `provider_options` keyed by an allowed host. Every provider follows the same rules. A model or effort preference is not proof of support. Null `model` and `reasoning_effort` preserve the current host's installed defaults and role/fallback configuration; no catalog or provider-specific default is bundled.

Select the current host only when it is allowed; otherwise defer with `runtime_unavailable`. `preferred_provider` never excludes an allowed current host and never permits a provider bridge; pre-0.58 pins: `legacy-pins.md#pre-058-runtime-dispatch`. An explicitly configured external bridge still requires the host to be allowed plus both external-invocation and spawn grants; a preferred provider alone never permits it. Copy explicit PLAN options into each worker's `runtime_binding`; the parent checks support against the actual native interface before launch. Unsupported explicit options block that node, without substitution.

The parent uses `runtime-adapters.md` to map observed native tools to the selected generic driver. Read-only and write scopes remain separate. A tool-profile label or prompt is not permission-level tool removal; enforce the required boundary and validate actual scope and Git results. Native launch, result, retry and resume APIs belong to the host, not a bundled script. They never change graph readiness, authorization, result validation or integration rules.

Host policy maps logical writer/reviewer responsibilities to actual native or bridge executors.
The parent records the actual session, model, effort and result origin in attempt evidence.
A result is accepted only from its launched session; a failed start records `blocked` and the actual host error.

Models and roles configured by the user remain authoritative. Preserve their declared fallback policy and record the actual resolved role, model and effort; never change installed definitions or manually redispatch to another provider.

## Retry And Replay

Retry one failed node by creating a new attempt on the same graph revision. Replay a subgraph only after every affected downstream node is reset or superseded under a new parent-owned state transition.

For non-runtime nodes, a retry always starts with a fresh `reserve-node-attempt`; the prior receipt remains terminal evidence. An interrupted approval, external wait, lifecycle action, or deterministic verifier is not left `running`: record `blocked` with `record-node-result` and preserve its evidence. A `retryable_failure` may directly re-arm only approval, external-wait, and deterministic-verifier work while budget remains; lifecycle work requires an explicit bounded route because its side effect may be unknown.

Never reuse:

- an old attempt ID;
- an expired lease or authorization;
- stale plan, graph, base, or head identity;
- a prior successful verifier result after its input head changed;
- a failed worker report as if the retry replaced its evidence.

Do not retry the same failed approach more than twice. A runtime review is stricter: `max_attempts` cannot exceed 2 and attempts count cumulatively per the Root-Cause Repair Escalation section above. After the bound is exhausted, remaining findings continue as isolated repairs with scoped reviews; no successor review node is authored.

### Bounded Loop Method

Before the first iteration, freeze the scope, permitted actions and input versions.
Record the measurement command, baseline, success predicate and regression gate.
Set time, attempt and cost limits in existing task stop conditions.
For managed work, use existing PLAN acceptance and verifier declarations.
For direct work, keep this information in the existing task record.
Validate that the measurement can distinguish the intended change before comparing candidates.
Use supported execution deadlines and check required spending evidence before another iteration.
An unavailable required measurement blocks continuation.

Run one hypothesis per iteration:

1. Observe current state and reconcile the active attempt.
2. Make the change within the accepted write scope.
3. Run the fixed measurement and regression gate.
4. Record the candidate SHA, input versions, result and evidence in the existing task or RUN record.

Before continuing, check the remaining budget and existing route or repair authority.
Retain rejected candidates, measurements and failure history.
Rejection grants no reset, rollback, cleanup, deletion or new attempt budget.
Once acceptance passes, stop; do not require a minimum iteration count.
Never lower a gate to make an experiment pass.

After a wake, honor pause, cancellation and completion first.
Reconcile live attempts and Git before dispatch.
Observe capabilities and contract identity.
Recheck action grants and use the current selector for managed work.
If an operation's effect is unknown, inspect and reconcile it before another mutation.
The parent records success, exhaustion, invalid measurement or a contract gap through existing outcomes and evidence.
A wake does not authorize a retry, task or schedule.
This method adds no scheduler, state store, runtime field or remote transport.

## Validation And Integration

Use this order:

```text
validate PLAN/RUN
-> select graph frontier
-> re-observe runtime and Git
-> reserve the selected non-runtime attempt under the RUN lock
-> execute its check, wait, or lifecycle side effect outside the lock
-> record-node-result with evidence and traverse routes
-> reserve the exact review dispatch in RUN when applicable
-> allocate mission attempt and workspace when applicable
-> execute adapter
-> validate node result
-> record-worker-result validates evidence and atomically updates RUN
-> integrate serially
-> run integration and batch verifiers
-> update RUN graph and mission state
-> recompute frontier
```

A node result is a candidate. Only a mission node with an integrated mission PASS may become `succeeded` with outcome `pass`. A completed task, native run, process exit, worker commit, or structured JSON response alone does not satisfy downstream dependencies.
