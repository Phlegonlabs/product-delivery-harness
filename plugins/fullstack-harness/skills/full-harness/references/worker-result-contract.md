# Worker Result Contract

Read this reference only while rendering or validating a delegated worker's terminal payload.

## Contents

- [Common rules](#common-rules)
- [Verifier execution context](#verifier-execution-context)
- [Worker result](#worker-result)
- [Graph node result](#graph-node-result)
- [Refinement request](#refinement-request)

## Common Rules

- Use exact keys. Extra or missing keys are rejected.
- Use the PLAN revision/digest, lease, base, and head supplied or observed for this attempt.
- Report `worker_passed`, never integrated.
- A passing worker result is an integration candidate, not proof of review or integration.
- RUN-v11 workers never delegate. `subagent_activity` is `not_applicable` with an empty `children` list.
- For `report_file`, write the exact fenced JSON to the parent-supplied temporary path.
- Worker and task states are `worker_passed`, `blocked`, or `worker_failed`.

## Verifier Execution Context

`trust_domain` is always `parent_local`; `checkout_role` is always `worker`.

```json
{
  "run_id": "RUN-<stable-id>",
  "plan_revision": 1,
  "plan_digest_sha256": "<lowercase SHA-256>",
  "graph_revision": 1,
  "batch_base_sha": "<full SHA>",
  "head_sha": "<full SHA>",
  "changed_files": ["<repo-relative path>"],
  "trust_domain": "parent_local",
  "checkout_role": "worker",
  "checkout_dirty": false,
  "cache_safe": true,
  "layer": "task",
  "mission_id": "M1",
  "task_id": "M1/T01",
  "attempt_id": "<attempt-id>",
  "lease_id": "<lease-id>"
}
```
For a worker-level verifier, use `"layer": "worker"` and `"task_id": null`. Use `"graph_revision": null` outside a graph run.

## Worker Result

```json
{
  "worker_result": {
    "type": "WORKER_RESULT",
    "run_id": "RUN-<stable-id>",
    "plan_id": "PLAN-<stable-id>",
    "mission_id": "M1",
    "lease_id": "<lease-id>",
    "status": "worker_passed",
    "current_task_id": null,
    "plan_revision": 1,
    "plan_digest_sha256": "<sha256>",
    "base_sha": "<full SHA>",
    "head_sha": "<full SHA>",
    "diff_summary": "<concise summary>",
    "changed_files": ["<repo-relative path>"],
    "task_results": [
      {
        "task_id": "M1/T01",
        "status": "worker_passed",
        "head_sha": "<full SHA containing this task>",
        "verifier_ids": ["task-focused"],
        "commits": ["<full task commit SHA>"],
        "evidence_paths": []
      }
    ],
    "verifiers": [
      {
        "id": "<verifier id>",
        "status": "PASS",
        "evidence": "<execution_key from verifier_runtime.py>"
      }
    ],
    "commits": ["<every task commit in order>"],
    "evidence_paths": [],
    "subagent_activity": {
      "status": "not_applicable",
      "skip_reason": "flat parent-owned topology; child agents are not applicable",
      "children": []
    },
    "blockers": [],
    "residual_risks": [],
    "integration_notes": "<notes for parent>"
  }
}
```

A passing mission lists every executable, non-superseded task in `task_results`. A blocked or failed result sets `current_task_id` and preserves completed task results. The final commit must equal `head_sha`.

## Graph Node Result

Return this wrapper alongside the worker result for a graph-backed run.

```json
{
  "run_id": "RUN-<stable-id>",
  "node_id": "N-M1",
  "attempt_id": "<attempt-id>",
  "plan_id": "PLAN-<stable-id>",
  "plan_revision": 1,
  "plan_digest_sha256": "<lowercase SHA-256>",
  "graph_revision": 1,
  "batch_base_sha": "<full SHA>",
  "status": "succeeded",
  "outcome": "pass",
  "worker_result": { "<the worker_result object>": "..." },
  "refinement_request": null,
  "evidence_paths": []
}
```

Allowed status/outcome pairs:

- `succeeded`: `pass` or `fix_required`
- `failed`: `retryable_failure`
- `blocked`: `blocked` or `contract_gap`

## Refinement Request

This is the canonical `REFINEMENT_REQUEST` schema. Every other reference points here instead of restating it.

Return this payload and stop. The parent decides whether to reject it, accept one bounded split, or replan the mission.

`pass_signal` must be the literal `exit 0` for a proposed child verifier to be eligible for `session_exact` cache reuse; any other spelling silently disables reuse for that verifier.

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
  "observed_head_sha": "<full SHA>",
  "reason": "<why the task cannot remain one independently verifiable unit>",
  "proposed_children": [
    {
      "alias": "<short label>",
      "deliverable": "<bounded outcome>",
      "trace_ids": ["REQ-001"],
      "write_scope": ["src/example/**"],
      "verifiers": [
        {
          "id": "<verifier id>",
          "cwd": ".",
          "argv": ["<runner>", "<argument>"],
          "pass_signal": "exit 0"
        }
      ]
    }
  ],
  "acceptance_matrix_items": [],
  "scope_or_contract_gap": null,
  "evidence": ["<path, command result, or concise fact>"]
}
```
