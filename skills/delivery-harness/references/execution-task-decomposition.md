# Execution Task Decomposition

Use this reference when ordering implementation tasks or refining a task that proves too broad. Execution-time refinement is bounded repair of a plan, not permission to grow an unbounded ID tree.

## Identity Model

Task IDs are flat, opaque, immutable identifiers within a mission:

```text
M1/T01
M1/T02
M2/T01
```

An ID contains only the owning mission and a stable task token. It does not encode ancestry, type, status, retry number, verifier, or acceptance scenario. Use separate fields:

```json
{
  "id": "M1/T03",
  "alias": "contract-verifier",
  "parent_task": "M1/T01",
  "legacy_task_ids": ["M1/OLD-07"],
  "split_reason": "independent_verifier",
  "refinement_generation": 1
}
```

- `alias` is a human-readable label and may improve without changing identity.
- `parent_task` records lineage; it is `null` for generation-zero tasks.
- `legacy_task_ids` is always a list and preserves historical references without making them canonical.
- `split_reason` is required for generation-one tasks.
- `refinement_generation` is `0` in the frozen plan and at most `1` after execution begins.

Do not reuse or renumber IDs after a plan is published. If historical data needs a new scheme, add a deterministic old-to-new mapping in `legacy_task_ids`.

## Mission Cohesion Gate

Run this gate for every proposed mission before PLAN readiness. A mission is a feature batch: one user-visible feature or one shared foundation, owned by one writer role. Its fine tasks keep their own atomic commits and verifiers.

Every mission adds fixed cost: worktree, handoff, result validation, one exact-head review per applicable surface, serial integration and integration reruns. Review is the largest of these, and review count follows mission count. Plan as few missions as the work allows.

Split a mission only when one of these is true:

- Parts need different writer roles, such as frontend and backend work.
- A shared contract or primitive must be frozen and integrated before dependent work starts.
- Parts are independent, and running them in parallel saves more time than one more review costs.
- The batch will not fit one worker session under the Runtime Slice Gate below.

Do not split a mission only because one clause could pass review alone, because parts use different focused verifiers, or because the feature spans several pages or endpoints. Make those parts separate tasks inside the mission. A one-task mission needs one of the reasons above, recorded in the PLAN. Before readiness, count the planned review nodes; when most missions carry a single task, merge them into feature batches.

Shared foundations do not justify a catch-all mission. A batch owns one feature or one foundation, not unrelated work that happens to touch the same router, auth boundary, migration directory, schema, or serialized resource. Freeze the smallest shared contract in its own predecessor mission when dependents need it, then use mission dependencies and serialized-resource claims. Expected merge conflicts are scheduling facts, not product cohesion.

For `platform-delivery/1`, map each mission that explicitly owns a `UI-*` surface to its `release_surface` stage. Put shared ARCH work in the first stage. Later missions may touch shared ARCH only when their dependencies retain the earlier platform regression.

Use task boundaries, not more missions, for every other step: each task has its own deliverable, verifier and atomic commit inside the mission. Do this before readiness; execution-time refinement is recovery for a mistaken estimate, not the normal planning path.

## What Deserves A Task

A refined task must have all of these properties:

- An independent deliverable that can be stated without referring to an internal step number.
- A bounded write scope contained by its mission scope.
- At least one upstream trace ID.
- An independent verifier with a pass/fail result.
- A commit-sized outcome, even when commit creation is not authorized. When commits are authorized, every executable task receives its own initial atomic commit before the next task begins. A later repair may add a separate atomic commit attributed to that same task, but one commit never satisfies multiple tasks.

Test cases, fault scenarios, browser sizes, retry attempts, and small implementation steps normally belong in the task's acceptance matrix. They are not separate tasks solely because they can be enumerated.

Apply the project's File Size Checkpoint when a touched module reaches 500 lines. Review its responsibilities during that task: split when doing so improves ownership and verification, otherwise record why it stays together. Request `REFINEMENT_REQUEST` only when the needed split exceeds the task's accepted scope. The line count is not a hard limit or an automatic refinement trigger.

`acceptance_matrix` is a canonical list on the PLAN task object. Updating it is a plan revision even when the task is not split.

When a task touches a required security boundary, its `trace_ids` name the existing upstream `PRD-*` and its acceptance-matrix `test_id` names the existing required `TEST-*`. The row proves the control, denial, and absence of unauthorized side effects using the declared verifier and retained evidence.

The parallel write unit is always a mission, and one feature batch maps to one mission. Tasks within one mission run sequentially in the same worker and workspace; refining a task never creates an additional parallel worker. Give the mission one explicit `write_scope` that is also the writer's file ownership. When missions share an API, schema, or type contract, freeze and integrate that contract before cutting dependent mission worktrees.

## Early Journey And Engineering Evidence

Apply this ordering during task planning. Direct work uses its existing task record; these checks do not require PLAN/RUN.

When scope introduces an unproven cross-layer dependency, the parent selects one representative core journey before expanding features that depend on it.
Link the journey to existing PRD, ARCH and TEST IDs within the approved platform order.
Use actual client, service, data and integration boundaries where applicable; headless products use caller/operator journeys.
For unchanged boundaries, reuse evidence only under existing freshness rules and record why another early journey check is unnecessary.

Build the journey through small tasks in the existing layer order, with shared contracts integrated before dependent writers start.
Keep mission cohesion, one writer per checkout, mandatory frontend ownership and approved visual quality.
The journey is an integration outcome, not permission for one task to span layers or one mission to collect unrelated work.
At its existing integration check, verify the real interfaces, state changes and required success, denial, retry and partial-failure recovery cases.
Respect the existing mock versus real-sandbox obligations; a mock result cannot satisfy required real behavior.
Only work depending on an unproven boundary waits. Continue independent work under the existing scheduler and resource rules.

Select engineering checks from approved NFRs and TEST obligations, according to actual product risk:

| Applicable risk | Required evidence from the existing acceptance criteria |
| --- | --- |
| Load, latency or paid external calls | Representative workload, measured latency, quotas, retry amplification and cost per successful operation as applicable |
| Persistent state or migration | Applicable backup restoration, version compatibility, migration failure recovery, recovery time and data-loss bounds |
| Jobs, events or external effects | Applicable duplicate/replay handling, interruption recovery and useful alert receipt by the response owner |

Keep check owners, workloads, environments and exact SHA/artifact bindings in existing task acceptance and evidence.
Record expected and observed results separately.
Keep operational setup and readback in Deployment/Activation records under their separate grants.
Plan checks before dependent work. Run them at the existing task, integration or operational checkpoint that provides their prerequisites.
Missing prerequisites block the dependent claim; planned checks and configuration alone are not observed behavior.
Use the product's accepted targets and explicit non-applicability; do not impose universal load, cost or recovery thresholds.
An uncovered product decision returns to its existing owner rather than becoming a guessed requirement.

These checks add no independent review wave, approval, schema or evidence register.
Early proof does not replace final exact-candidate verification, release readback or existing review and repair limits.

## Runtime Slice Gate

The 10-20 minute slice applies to each task: implementation plus its focused verifier should stay within roughly 10-20 minutes. Treat that range as an upper shape, not capacity to fill. A mission's worker runs its tasks in order and commits each one before the next, so one feature batch spans several slices in one worker session. Every delegated worker uses a fresh bounded context and the observed native isolation contract. Treat this as a planning SLO, not a hard process timer and not an authorization shortcut.

- Keep tasks as sequential checkpoints inside the mission. A task still needs one deliverable, scope, trace, and verifier; a list of acceptance cases is not extra work units.
- Before readiness, split a task that is expected to exceed the slice. Split a mission only for a Mission Cohesion Gate reason; then create dependency edges and freeze shared contracts first.
- Do not use a 30-minute host timeout as task decomposition. If execution shows that the slice estimate was wrong, stop before beginning the next independent mutation and return `REFINEMENT_REQUEST`; preserve the current head and evidence.
- A worker timeout is interrupted evidence, not a successful checkpoint. The parent may resume only after validating the worktree and deciding whether the remaining work still fits the same mission.
- Record the estimate and actual elapsed phase timestamps in the human PLAN/RUN view. They are telemetry, not machine authorization and do not change PLAN/RUN schema.

This slice gate shortens child contexts and failure recovery. It is not a reason to add missions: each extra mission adds a review and an integration. It does not authorize parallel writers in one mission; only independently scoped missions may enter the parallel frontier.

## UI Build Order

When the product has a design system, its primitive layers decide task order. Each layer composes only the layers above it, so a task cannot be verified before the layer it depends on exists:

```text
1. Design tokens                              (every visual, layout, and motion value)
2. Layout / surface / typography / control primitives
   + the UI contract check and the responsive check over
     design-system.json's `viewports` or `sizeClasses`
3. Product components                          (bound to their content contracts)
4. Routes                                      (one route per mission per contract-and-traceability.md)
```

Rules:

- The primitives land as one change, not one per route. A primitive that exists for one route and not the next is how a second, unofficial system starts.
- The contract checks land with the first routes, not at the end. A guardrail that first runs after every route is built reports a backlog of violations instead of stopping the first one.
- A route task may not introduce a new primitive, variant, or motion variant at all. When it needs one, it stops at a safe boundary and reports; the entry is added to `design-system.md` and `design-system.json` by the design source as a frozen delta (`design-input-updates.md`), then the route task resumes against the new revision. Three reasons this is not a task-local fix: those files are frozen contract sources, so writing them mid-task invalidates the PLAN digest and every in-flight lease including the task's own; it would make the task span two layers, which the next rule forbids; and it would put the same two files in every page mission's write scope, making all page missions conflict pairwise under `parallel-mission-selection.md`'s scope-overlap rule and serializing the per-page split this file exists to enable.
- Loading the owner-bound frontend-authoring skill does not change that route-task boundary. The Harness applies its own conformance contract around that authoring work; any proposed addition returns as a design-input delta instead of joining the route commit. Never claim the external skill defines a conformance mode absent from its pinned tree.
- Each layer is one or more tasks, never one task spanning two layers — a task that adds a token and the component consuming it cannot fail the token independently.
- A route's required states from its recipe are acceptance-matrix items inside that route's task, not separate tasks (see `What Deserves A Task` above). The same holds for every entry in the registry's responsive set.
- For an existing product, keep the same layer order but sequence it around already-shipped routes rather than building bottom-up from nothing: adopt tokens and primitives behind the current implementation first, migrate routes in the order the Open-Ended Refinement audit in `references/design-input-updates.md` establishes, and let the two coexist until the last route moves.

## Backend Build Order

Backend layers compose downward the same way UI layers do, so a task cannot be verified before the layer it depends on exists:

```text
1. Schema and migrations                      (tables, columns, indexes, constraints)
2. Data access                                 (queries, repositories, transactions, seed/fixture data)
3. API and action contracts                    (routes, inputs, outputs, error shapes)
4. Auth and permission boundaries              (identity, session, role/permission enforcement on those contracts)
5. Integrations, jobs, and events              (external systems, queues, webhooks, audit events)
```

Rules:

- Every layer above traces to the `ARCH-*` contracts in `architecture.md` — the data model rows for layers 1-2, the API and interface contract rows for layer 3, the auth and permissions section for layer 4, the integrations table for layer 5. A backend task with no `ARCH-*` trace is scope drift.
- Each `ARCH-*` trace needs a downstream task **and** a verification row. `harness_manifest.py` enforces both halves at plan validation — a planned trace whose every carrying task has an empty acceptance matrix fails — so author the verification row with the task instead of discovering the failure at validation time.
- Auth enforcement lands with or after the contract it protects, never before it. An auth layer written against routes that do not exist yet cannot be verified, and the archetype mission lists in `platform-archetypes.md` are coarse mission groupings, not this task order.
- A protected route may be scaffolded before its final UI, but it remains fail-closed until authorization, tenant/permission isolation where applicable, and denial tests are implemented and pass.
- A migration task states its classification (`additive` / `destructive`) when it is authored, not later. The classification is not a manifest field — state it in the task's objective or acceptance matrix. See `contract-and-traceability.md`'s Stop And Ask condition for a migration task reaching integration with its classification unset.
- Each layer is one or more tasks, never one task spanning two layers — a task that adds a column and the endpoint reading it cannot fail the migration independently.
- For an existing product, follow the repository's established layering when it differs; this order sequences the same layers for greenfield work.

## Refinement Limit

Execution-time refinement allows one generation only:

```text
generation 0 task -> generation 1 replacement tasks
```

When a generation-zero task is replaced:

- The parent task remains in the plan with `replaced_by` listing every child ID.
- Its RUN phase becomes `superseded`.
- Each child uses `parent_task` to point to the replaced parent.
- Children may depend on one another, but dependencies must remain acyclic.
- Existing trace coverage must be preserved or explicitly reclassified.
- Task dependencies may reference only tasks in the same mission. Cross-mission ordering belongs exclusively in the mission DAG.
- Rewrite every downstream dependency on the superseded parent to terminal replacement children. Unless the contract proves a narrower mapping, depend on every sink in the replacement subgraph. No executable task may depend on a superseded task ID.

A generation-one task may not split again. If it still cannot be implemented atomically, stop the worker and perform a mission-level replan. The result may be a revised mission, new missions, changed contracts, or a new execution run; it must not be a generation-two task.

## Worker Refinement Request

Workers never edit canonical `PLAN.md` or `RUN.md`. When scope proves insufficient, a worker emits `REFINEMENT_REQUEST` and stops at a safe task boundary:

See `worker-result-contract.md`'s Refinement Request section for the canonical payload schema. Do not restate it here.

The request is evidence, not approval. The worker keeps its branch and evidence intact and performs no further writes until the parent decides.

## Parent Decision Gate

The parent evaluates every request with this matrix:

| Check | Accept only when |
|---|---|
| Atomicity | Every proposed child has an independent deliverable and verifier |
| Scope | Child scopes are supported, contained by the mission, and collectively do not hide out-of-scope work |
| Traceability | Required upstream trace IDs still have implementation and verification coverage |
| DAG | New task dependencies exist, are acyclic, and do not change mission readiness unexpectedly |
| Generation | Parent is generation zero and every child will be generation one |
| Parallel semantics | The refinement stays inside one mission worker; it does not bypass mission conflict analysis |
| Contract | No new product, architecture, permission, data, or destructive behavior is being assumed |
| Repair lineage | Prior review attempts, unresolved findings, and the stable mission + surface + root-cause family remain visible across the revision |

The parent chooses one outcome:

1. **Acceptance-matrix update.** Keep one task and record additional cases when there is no independent deliverable.
2. **Accept refinement.** Allocate new flat IDs, supersede the parent, create generation-one tasks, increment the plan revision, recompute the plan digest, and revalidate DAG, scopes, resources, traces, and verifiers.
3. **Mission-level replan.** Stop affected execution when scope, contract, resource ownership, or another generation of splitting is required. Revise or replace the mission, then rerun readiness and conflict selection.
4. **Reject with evidence.** Resume the existing task only after explaining why the planned unit remains executable and recording any clarified acceptance criteria.

A mission-level replan does not replenish a review budget. Carry the consumed attempt count and unresolved root-cause families into the revised owner-decision source, mission stop conditions, and reviewer packet. When related edge cases expose one brittle primitive, update the acceptance matrix to cover the full failure family and change the repair strategy before resuming. If the review budget defined in `graph-orchestration.md`'s Root-Cause Repair Escalation is exhausted, a successor generation requires that section's explicit owner decision and exact additional allowance; a generic direction to continue is insufficient. Set the successor review node's `max_attempts` to that allowance only.

Any accepted change invalidates the active wave and every lease bound to the previous revision/digest, not only future proposals. Before publishing the new revision, the parent freezes launches and integration, asks all old-revision workers to stop at a safe boundary, and records the old wave as superseded. Preserve their branches/heads and evidence, but reject old-lease results for integration. After the new plan validates, an unaffected head may continue only through a new lease bound to the new revision/digest and after scope/resource revalidation; otherwise stop for mission-level replan. The parent records the decision and new static definitions before leasing work again.

## Validation Rules

A plan validator must reject:

- Duplicate or nested/derived task IDs.
- A task whose mission prefix does not match its owning mission.
- Missing or unknown task dependencies.
- A cross-mission task dependency or any dependency on a superseded task.
- Parent cycles or dependency cycles.
- `refinement_generation` outside `0..1`.
- A generation-one task with replacement children.
- A superseded parent with incomplete or unknown `replaced_by` IDs.
- A child without `parent_task`, `split_reason`, trace coverage, write scope, or verifier.
- A child write scope outside its mission scope.

Retries do not mint new task IDs. Record retries as RUN attempts against the same task and preserve each attempt's evidence.
