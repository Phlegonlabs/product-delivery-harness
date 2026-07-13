# Worker Goal: <mission ID> — <objective>

Use this prompt only after the parent validates the canonical PLAN/RUN state, leases one mission, fixes its base SHA, and confirms every required authorization. A worker owns mission implementation only; the parent owns planning, live state, integration, and landing.

```text
/goal Complete <mission ID> (<objective>) only.

Frozen inputs:
- PLAN: <path>, plan ID <id>, revision <revision>, digest <sha256>
- RUN snapshot supplied by parent: <path or payload>
- Mission/task IDs: <mission and task IDs>
- Lease ID: <lease-id>
- Batch base SHA: <full SHA>

Coordination:
- worker_runtime: parent | subagent | app_task
- workspace_mode: shared_checkout | parent_managed_worktree | app_managed_worktree
- completion_channel: agent_result | thread_poll | report_file | user_relay
- Worktree: <path or n/a>
- Branch/ref: <branch, ref, or pending-authorized creation>
- Resource claims: <typed resource keys and access>

Write only within: <mission write_scope>.
Deny: <mission deny_scope>, parent-owned PLAN.md and RUN.md, frozen contracts, and unrelated files.

Before editing, verify the supplied plan revision/digest, lease, base SHA, workspace, resource claims, and action authorizations are current. Stop if any value is missing, stale, contradictory, or outside the supported scope grammar.

For each ready task: make the smallest coherent change, run its declared verifier, and return evidence. Create a commit only when create_local_commits is explicitly authorized. Do not spawn another worker or create another task. Do not pull, rebase, merge, integrate, push, open a PR, deploy, remove a worktree, delete a branch, or archive a task; those remain parent/user-owned actions unless separately and explicitly assigned.

Never edit PLAN.md or RUN.md. If the task is too large or its scope is insufficient, emit REFINEMENT_REQUEST with the contract below and stop before further task work. Do not invent child IDs or rewrite the plan.

When assigned work passes, return WORKER_RESULT through the configured completion channel and stop. Report worker_passed, never integrated: only the parent may validate actual diffs, integrate the branch/head, run integration gates, verify ancestry, and mark the mission integrated.

Guardrails: stop on requirements conflict, unavailable verifier, scope escape, unexpected parent-head movement, destructive action, or three consecutive no-progress iterations. Do not retry the same failed approach more than twice.
```

## Workspace Launch Rules

### Shared checkout

Use only when the parent is the sole writer or otherwise guarantees one write lease. Do not run parallel writers in one checkout.

### Parent-managed worktree

The parent creates and records the worktree, branch, and fixed base before launch. The worker must not change upstream synchronization or reuse a different base.

### App-managed worktree

The app may start the task detached and may apply platform retention independently of the ledger. When `create_local_branches` is explicitly authorized, create or attach the recorded durable branch/ref before unique work. Never claim that `remove_worktrees: false` disables platform-managed retention. Completion may require `thread_poll` or `user_relay`; do not assume an automatic cross-task callback.

## Refinement Request Contract

Return this payload and stop. The parent decides whether to reject it, accept a bounded generation-1 split, or perform a mission-level replan.

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
  "reason": "<why the current task cannot remain one independently verifiable unit>",
  "proposed_children": [
    {
      "alias": "<short label>",
      "deliverable": "<independent bounded outcome>",
      "trace_ids": [
        "REQ-001"
      ],
      "write_scope": [
        "src/example/**"
      ],
      "verifiers": [
        {
          "id": "<verifier id>",
          "cwd": ".",
          "argv": [
            "<runner>",
            "<argument>"
          ],
          "pass_signal": "<literal pass signal>"
        }
      ]
    }
  ],
  "acceptance_matrix_items": [],
  "scope_or_contract_gap": null,
  "evidence": [
    "<path, command result, or concise fact>"
  ]
}
```

## Worker Result Manifest

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
    "diff_summary": "<concise observed change summary>",
    "changed_files": [],
    "task_results": [
      {
        "task_id": "M1/T01",
        "status": "worker_passed",
        "head_sha": "<full SHA containing this task result>",
        "verifier_ids": [
          "task-focused"
        ],
        "commits": [],
        "evidence_paths": []
      }
    ],
    "verifiers": [
      {
        "id": "<verifier id>",
        "status": "PASS",
        "evidence": "<command result or artifact>"
      }
    ],
    "commits": [],
    "evidence_paths": [],
    "blockers": [],
    "residual_risks": [],
    "integration_notes": "<notes for parent>"
  }
}
```

Use the same payload for `agent_result`, `thread_poll`, `report_file`, or `user_relay`. For `report_file`, place this exact heading and fenced JSON in the parent-supplied temporary report path; Markdown prose outside the manifest is non-canonical.

Worker and task-result statuses are `worker_passed`, `blocked`, and `worker_failed`. A mission-level `worker_passed` result lists every executable non-superseded task in `task_results`; after validating reachability and evidence, the parent advances those task states to `mission_recorded`. A blocked/failed result sets `current_task_id` and preserves completed task results. A passing result is an integration candidate only; it is not proof of scope compliance, conflict freedom, integration-gate success, or completion.

## Launch Checklist

- [ ] Canonical PLAN validates; supplied ID, revision, and digest match RUN.
- [ ] RUN records `plan_readiness: "ready"` and overall execution authorization.
- [ ] Mission is `leased` at the fixed base SHA and its dependencies are already integrated.
- [ ] The selected runtime, workspace, completion channel, and required authorizations match the launch method.
- [ ] Any isolated write handoff has authorized branch and commit creation; otherwise this mission uses sequential parent execution.
- [ ] Write/deny scopes and typed resource inventory are complete and non-conflicting.
- [ ] Worktree/branch behavior follows the selected workspace rule.
- [ ] Worker and integration verifiers have literal pass signals.
- [ ] Parent-owned files and temporary report location are explicit.
