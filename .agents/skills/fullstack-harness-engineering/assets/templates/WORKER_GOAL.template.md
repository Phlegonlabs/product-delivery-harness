# Worker Goal: <mission ID> — <objective>

Use this prompt only after the parent completes the parent-only, read-only `System Review And Route`, validates the canonical PLAN/RUN state, leases one delegated mission, fixes its base SHA, and confirms every required authorization. A worker owns mission implementation only; the parent owns routing, planning, live state, integration, and landing. A large no-agent route does not render or launch this prompt: it uses real `sequential_parent` execution, with the parent as sole mission writer and no `spawn_subagents` action.

```text
Complete <mission ID> (<objective>) only.

Frozen inputs:
- PLAN: <path>, plan ID <id>, revision <revision>, digest <sha256>
- RUN snapshot supplied by parent: <path or payload>
- Mission/task IDs: <mission and task IDs>
- Lease ID: <lease-id>
- Batch base SHA: <full SHA>

Coordination:
- Skills to load: <mission's required_skills, or "none">
- runtime_provider: codex | claude_code | pi | generic
- Host-specific repository context: <Codex: effective AGENTS chain; Claude: shared AGENTS plus effective CLAUDE chain; Pi: the one file selected per directory by Pi priority>
- Runtime-specific worker contract: <matching Codex, Claude Code, or Pi adapter instructions>
- execution_route (selector-derived): direct | managed_sequential | parallel_graph
- runtime_driver (transport): app_threads | dynamic_workflow | subagents | sequential_parent
- worker_runtime: parent | subagent | app_task
- workspace_mode: shared_checkout | parent_managed_worktree | app_managed_worktree
- completion_channel: agent_result | thread_poll | report_file | user_relay
- permission_boundary: selected mode/profile, approval policy, filesystem/network/local-binding scope, inheritance, ready status
- nested_subagent_policy: disabled; RUN-v10 forbids worker-owned child agents
- Worktree: <path or n/a>
- Branch/ref: <branch, ref, or pending-authorized creation>
- Resource claims: <typed resource keys and access>

Write only within: <mission write_scope>.
Deny: <mission deny_scope>, parent-owned PLAN.md and RUN.md, frozen contracts, and unrelated files.

The parent must have completed `System Review And Route` before this delegated handoff exists. A `managed_sequential` route is not a fan-out claim; it still carries the isolated writer, authorization, scope/head, and review gates. Enter the assigned worktree and read every ordered path in "Host-specific repository context" before any repository action. Apply only the matching "Runtime-specific worker contract"; never borrow another host's model, role, context, or launch mechanics. Do not disable automatic context discovery. Load exactly the skills named in "Skills to load" above — no more, no fewer — before the Launch Checklist below, then verify the supplied plan revision/digest, lease, base SHA, workspace, resource claims, permission boundary, and action authorizations are current. Confirm linked-worktree Git metadata, temp/cache paths, outbound network, local/private bindings, and required sockets fit the inherited boundary. Stop if any value is missing, stale, contradictory, outside the supported scope grammar, or would require an unresolved approval during unattended execution.

When "Skills to load" includes both `product-design-builder` and `frontend-design`, run design creation mode. Use `frontend-design` through `product-design-builder`'s workflow to create or revise only the canonical wireframes and design-system sources in scope, starting from the frozen product inputs and stopping at every required human direction gate. If `frontend-design` is unavailable, stop; do not simulate it or fall back.

When "Skills to load" includes `frontend-design` without `product-design-builder` for a UI implementation mission, use it only in frontend-design conformance mode. Read the frozen wireframe screen, `design-system.md`, and `design-system.json` named by the parent before coding. Do not choose a new aesthetic direction or invent a token, primitive, variant, component, motion pattern, or page structure. Return a missing entry as a design-input delta and stop; do not add it locally.

For each ready task: make the smallest coherent change, use the local diff for provisional `selection.mode: "changed_files"` matching, run every applicable declared verifier, and return literal evidence. Execute every declared verifier through `scripts/verifier_runtime.py`'s `run_verifier()` — passing `cache_root=None`, or omitting it, whenever the parent supplied no cache root — so its returned `execution_key` is available to report as `evidence`; this applies unconditionally, not only when caching applies. Never run a verifier command through a separate direct shell invocation whose result carries no `execution_key`; a worker result reporting free-form text or a command transcript as `evidence` is rejected. Omitted selection metadata means always run. A targeted verifier may be absent only when no changed path matches its declared scope; the parent recomputes applicability from parent-observed changed files and may require a fresh check. If the parent supplied a repository-external verifier cache root, reuse is allowed only through `verifier_runtime.py` for an opted-in deterministic local `exit 0` command with exact immutable inputs; never claim a cache hit from memory or prose. Create a commit only when create_local_commits is explicitly authorized. Every isolated successful handoff needs durable task commits, each attributed to exactly one task, with the final commit equal to the reported head. Do not create another agent, app task, mission worker, branch, worktree, or harness lease. All explorers, writers, and reviewers are parent-dispatched siblings. Do not switch branches, pull, rebase, merge, integrate, push, remove a worktree, delete a branch, or archive a task; those remain parent/user-owned actions unless separately and explicitly assigned.

Never edit PLAN.md or RUN.md. If the task is too large or its scope is insufficient, emit REFINEMENT_REQUEST with the contract below and stop before further task work. Do not invent child IDs or rewrite the plan.

When assigned work passes, return WORKER_RESULT through the configured completion channel and stop. Report worker_passed, never integrated: only the parent may validate actual diffs, integrate the branch/head, run integration gates, verify ancestry, and mark the mission integrated.

Guardrails: stop on requirements conflict, unavailable verifier, scope escape, unexpected parent-head movement, destructive action, or three consecutive no-progress iterations. Do not retry the same failed approach more than twice.
```

## No Nested Delegation

Do not spawn, create, or delegate to another agent, even when the host exposes child-agent tools. Complete only the assigned mission. Ask the parent for a sibling explorer or reviewer when independent read-only work is useful. RUN-v10 accepts only an omitted or disabled `nested_subagent_policy`; report `subagent_activity.status: "not_applicable"`, an empty `children` list, and a concrete skip reason such as `flat parent-owned topology`. The parent supplies every exact-head pre-integration review and every fresh unified-head review.

## Claude Dynamic Workflow Rules

When `runtime_driver` is `dynamic_workflow`, the accepted wave is one parent-owned flat workflow. This mission worker must not spawn or delegate. Explorer, writer, and reviewer agents are workflow-controlled siblings, not nested children, and `subagent_activity` remains `not_applicable` for the mission worker. Work only in the exact parent-allocated worktree and branch supplied above.

Claude Dynamic Workflow cannot wait for human sign-off between stages. If implementation needs a contract choice, new authorization, secret, destructive action, scope expansion, or generation-1 refinement decision, return `REFINEMENT_REQUEST` and stop. Never guess the decision or keep writing while waiting for an interactive reply.

## Workspace Launch Rules

### Shared checkout

Use only when the parent is the sole writer or otherwise guarantees one write lease. Do not run parallel writers in one checkout.

### Parent-managed worktree

The parent creates and records the worktree, branch, and fixed base before launch. The worker must not change upstream synchronization or reuse a different base.

### App-managed worktree

The app may start the task detached and may apply platform retention independently of the ledger. When `create_local_branches` is explicitly authorized, create or attach the recorded durable branch/ref before unique work unless the runtime has already assigned it; never switch away from that assigned ref. Remember that branch/commit commands may write the original repository's Git common directory outside this worktree. Never claim that `remove_worktrees: false` disables platform-managed retention. Completion may use `agent_result`, `thread_poll`, or `user_relay`; do not assume an automatic callback outside the declared channel.

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

## Verifier Execution Context

`run_verifier()` takes a `context` object with all of these keys. Two are fixed constants and are the usual thing to get wrong: `trust_domain` is always `"parent_local"` and `checkout_role` is always `"worker"` — they describe the domain the parent will validate the evidence in, not the process running the command. A wrong guess still runs green here and is rejected much later as `retained_verifier_context_mismatch`.

```json
{
  "run_id": "RUN-<stable-id>",
  "plan_revision": 1,
  "plan_digest_sha256": "<lowercase SHA-256 of the current semantic PLAN>",
  "graph_revision": 1,
  "batch_base_sha": "<full SHA the worktree was created from>",
  "head_sha": "<full SHA of the worker head>",
  "changed_files": ["<repo-relative path>", "..."],
  "trust_domain": "parent_local",
  "checkout_role": "worker",
  "checkout_dirty": false,
  "cache_safe": true,
  "layer": "task",
  "mission_id": "M1",
  "task_id": "M1/T01",
  "attempt_id": "<attempt id for this execution>",
  "lease_id": "<the lease supplied at launch>"
}
```

For a worker-level verifier use `"layer": "worker"` and `"task_id": null`; everything else is identical. `graph_revision` is `null` for a non-graph run.

## Node Result Manifest

A graph-backed run returns this alongside WORKER_RESULT. The key set is exact — extra or missing keys are rejected outright.

```json
{
  "run_id": "RUN-<stable-id>",
  "node_id": "N-M1",
  "attempt_id": "<attempt id>",
  "plan_id": "PLAN-<stable-id>",
  "plan_revision": 1,
  "plan_digest_sha256": "<lowercase SHA-256 of the current semantic PLAN>",
  "graph_revision": 1,
  "batch_base_sha": "<full SHA the attempt was based on>",
  "status": "succeeded",
  "outcome": "pass",
  "worker_result": { "<the WORKER_RESULT object below>": "..." },
  "refinement_request": null,
  "evidence_paths": []
}
```

`status` and `outcome` are paired: `succeeded` takes `pass` or `fix_required`, `failed` takes `retryable_failure`, and `blocked` takes `blocked` or `contract_gap`.

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
        "commits": ["<full SHA of this task's commit>"],
        "evidence_paths": []
      }
    ],
    "verifiers": [
      {
        "id": "<verifier id>",
        "status": "PASS",
        "evidence": "<execution_key from verifier_runtime.py's run_verifier() output>"
      }
    ],
    "commits": ["<every task commit, in order; the last equals head_sha>"],
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

Use the same worker-result payload for `agent_result`, `thread_poll`, `report_file`, or `user_relay`. For `report_file`, place this exact heading and fenced JSON in the parent-supplied temporary report path; Markdown prose outside the manifest is non-canonical.

For current RUN-v10, `subagent_activity` is always `status: "not_applicable"`, a concrete `skip_reason`, and an empty `children` list. Workers and reviewers never create child agents; the parent dispatches every explorer and reviewer as a sibling graph node. Legacy RUN-v6 through v9 results retain their historical nested-policy validation only, and must not be copied into a new RUN-v10 handoff.

Worker and task-result statuses are `worker_passed`, `blocked`, and `worker_failed`. A mission-level `worker_passed` result lists every executable non-superseded task in `task_results`; after validating reachability and evidence, the parent advances those task states to `mission_recorded`. A blocked/failed result sets `current_task_id` and preserves completed task results. A passing result is an integration candidate only; it is not proof of scope compliance, conflict freedom, integration-gate success, or completion.

## Launch Checklist

- [ ] Parent-only `System Review And Route` completed before this delegated handoff; current managed work uses PLAN-v5/RUN-v10.
- [ ] Every skill in "Skills to load" is loaded before the first production edit; "none" needs no action.
- [ ] No nested delegation is permitted; any needed explorer or reviewer is requested from the parent as a sibling.
- [ ] The runtime provider, its matching adapter contract, and only its host-specific ordered context paths are supplied and read from the assigned checkout before any repository action; automatic context discovery remains enabled.
- [ ] Canonical PLAN validates; supplied ID, revision, and digest match RUN.
- [ ] RUN records `plan_readiness: "ready"` and overall execution authorization.
- [ ] Mission is `leased` at the fixed base SHA and its dependencies are already integrated.
- [ ] The selected runtime, workspace, completion channel, and required authorizations match the launch method.
- [ ] The recorded provider capability snapshot routes to the declared driver; Claude Dynamic Workflow workers use flat orchestration and do not delegate.
- [ ] RUN-v10 `subagent_activity` is `not_applicable` with a concrete flat-topology reason and empty `children`; any explorer or reviewer is parent-dispatched as a sibling.
- [ ] Any isolated write handoff has authorized branch and commit creation; otherwise this mission uses sequential parent execution.
- [ ] Write/deny scopes and typed resource inventory are complete and non-conflicting.
- [ ] Worktree/branch behavior follows the selected workspace rule.
- [ ] Worker and integration verifiers have literal pass signals.
- [ ] Parent-owned files and temporary report location are explicit.
