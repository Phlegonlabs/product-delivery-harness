# Execution Task Decomposition

Use this reference when a planned task proves too broad during implementation. Execution-time refinement is bounded repair of a plan, not permission to grow an unbounded ID tree.

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

## What Deserves A Task

A refined task must have all of these properties:

- An independent deliverable that can be stated without referring to an internal step number.
- A bounded write scope contained by its mission scope.
- At least one upstream trace ID.
- An independent verifier with a pass/fail result.
- A commit-sized outcome, even when commit creation is not authorized.

Test cases, fault scenarios, browser sizes, retry attempts, and small implementation steps normally belong in the task's acceptance matrix. They are not separate tasks solely because they can be enumerated.

`acceptance_matrix` is a canonical list on the PLAN task object. Updating it is a plan revision even when the task is not split.

The parallel write unit is always a mission. Tasks within one mission run sequentially in the same worker and workspace; refining a task never creates an additional parallel worker.

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

```json
{
  "type": "REFINEMENT_REQUEST",
  "run_id": "RUN-<stable-id>",
  "plan_id": "PLAN-<stable-id>",
  "mission_id": "M1",
  "task_id": "M1/T01",
  "plan_revision": 1,
  "plan_digest_sha256": "<sha256>",
  "lease_id": "<lease-id>",
  "observed_head_sha": "<sha>",
  "reason": "<why the planned task is not atomic>",
  "proposed_children": [
    {
      "alias": "<human label>",
      "deliverable": "<independent result>",
      "trace_ids": ["<existing trace id>"],
      "write_scope": ["<repo-relative scope>"],
      "verifiers": [
        {
          "id": "<verifier id>",
          "cwd": ".",
          "argv": ["<executable>", "<argument>"],
          "pass_signal": "exit_code_0"
        }
      ]
    }
  ],
  "acceptance_matrix_items": ["<items that should stay inside one task>"],
  "scope_or_contract_gap": null,
  "evidence": ["<path or command result>"]
}
```

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

The parent chooses one outcome:

1. **Acceptance-matrix update.** Keep one task and record additional cases when there is no independent deliverable.
2. **Accept refinement.** Allocate new flat IDs, supersede the parent, create generation-one tasks, increment the plan revision, recompute the plan digest, and revalidate DAG, scopes, resources, traces, and verifiers.
3. **Mission-level replan.** Stop affected execution when scope, contract, resource ownership, or another generation of splitting is required. Revise or replace the mission, then rerun readiness and conflict selection.
4. **Reject with evidence.** Resume the existing task only after explaining why the planned unit remains executable and recording any clarified acceptance criteria.

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
