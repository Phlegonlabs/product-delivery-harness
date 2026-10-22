# Worker Result Contract

Read this reference only while rendering or validating a delegated worker's terminal payload.

Role-bound 0.58+ assignments also follow [parent-retained execution receipts](agent-execution-receipts.md). The parent records actual launch and result/failure provenance separately from child payloads.

## Contents

- [Common rules](#common-rules)
- [Verifier execution context](#verifier-execution-context)
- [Worker result](#worker-result)
- [Graph node result](#graph-node-result)
- [Contract adoption check](#contract-adoption-check)
- [Refinement request](#refinement-request)

## Common Rules

- Use exact keys. Extra or missing keys are rejected.
- Use the PLAN revision/digest, lease, base, and head supplied or observed for this attempt.
- Report `worker_passed`, never integrated.
- A passing worker result is an integration candidate, not proof of review or integration.
- RUN-v11 workers never delegate. `subagent_activity` is `not_applicable` with an empty `children` list.
- For `report_file`, write the exact fenced JSON under the heading `## Worker Result Manifest` to the parent-supplied temporary path — that heading plus one fenced `worker_result` JSON block is the exact shape `load_worker_result` parses; a report without it is unreadable to the validators.
- A passing mission returns the complete worker result below. A non-passing mission returns a graph node result with `worker_result: null`; `record-worker-result` retains that terminal outcome without pretending a partial payload passed the worker contract.
- A 0.58.0+ role-bound PASS must join the reserved assignment, attempt, worker identity, PLAN digest, and exact input SHA to the parent's persisted launch record. The parent record supplies launch/model/session evidence; a child echo does not. A mixed native/bridge result is checked against its reserved per-node axes, not the RUN's global axes.

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

In current RUN-v11, task and worker verifier commands use explicit `host` or `container` policies. Retained execution evidence must bind the declared mode, exact candidate, command, cwd, logs, exit status and live source/Git guards. Host results are fresh and do not claim sandbox confinement. Container results retain the machine-verifiable sandbox attestation and current PLAN-bound runtime/image RepoDigest observation. Missing or stale required evidence blocks dispatch or acceptance; changing modes never permits reuse of the prior mode's PASS.

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

A passing mission lists every executable, non-superseded task in `task_results`. List commits in actual Git order. Every SHA appears exactly once in the mission `commits` list and under exactly one task result; the order of each task's commit list must match that mission sequence. The final commit must equal `head_sha`.

Under an adopted runtime contract, add the `contract_adoption_check` key below.

The parent records this payload with the matching graph node result, independently observed head/diff/ancestry, and retained verifier execution files through `harness_transition.py ... record-worker-result`. The transition revalidates all of them under the RUN lock before changing canonical state.

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

## Contract Adoption Check

The narrow [rejected-ingestion recovery](agent-execution-receipts.md#rejected-ingestion-of-a-passing-result) validates an unchanged original result against its snapshot-bound adoption. It never changes ordinary current-adoption checks. A fresh reviewer must read and attest the current adopted contract.

When the directive or review packet carries `contract_adoption`, the worker or reviewer recomputes the seven-skill contract digest itself, reads the fixed contract, and returns this object as `contract_adoption_check`:

```json
{
  "digest": "<the digest you recomputed>",
  "matched": true,
  "reading_evidence": ["<what you actually read>"]
}
```

- A worker puts it at `worker_result.contract_adoption_check`. A graph review result carries it next to `reviewed_sha`, `findings`, and `evidence_summary`. A security reviewer returns it beside the security result given to `--security-result`, never inside it. For `record-review-attempt --contract-adoption-check <json file>`, the file holds this object, or `{"contract_adoption_check": <this object>}` as the reviewer returned it.
- `digest` must equal the RUN's `contract_adoption.contract_digest_sha256`, and `matched` must be `true`.
- On a mismatch, stop and keep the digest you saw. A reviewer returns `blocked` with `matched: false` and that digest (`reading_evidence` may be empty); the attempt log keeps `contract_adoption_mismatch:<digest>`. A worker, or a graph reviewer, returns a `blocked` node result and lists `contract_adoption_mismatch:<digest>` in `evidence_paths`.
- `reading_evidence` is the child's own reading. Copying the parent receipt's list is rejected.
- RUNs that require Harness 0.55.1 or later must include it for every passing worker result and every `pass` or `fix_required` review. A `blocked`, `retryable_failure`, or `contract_gap` review may omit it, because the parent can record those without child output; a supplied check is still validated. Older RUNs may omit it. It is rejected when the RUN has no adopted contract.
- The recording transitions keep the digest and reading lines in the attempt log.
- The check is the child's attestation that it recomputed the digest. The transitions compare it with the adopted digest only; `select_ready_nodes.py` compares the installed bundle with that digest at dispatch.

## Refinement Request

This is the canonical `REFINEMENT_REQUEST` schema. Every other reference points here instead of restating it.

Return this payload and stop. The parent decides whether to reject it, accept one bounded split, or replan the mission.

The runtime decides PASS from exit code 0 alone; a proposed child verifier's `pass_signal` is a label and should be `exit 0`. PLAN validation refuses `session_exact` cache reuse for a verifier with any other `pass_signal`.

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
