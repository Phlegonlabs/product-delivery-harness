# Plan: <feature or product slice>

Use this template as `docs/goal/PLAN.md` for managed work that needs durable coordination, even when the selected execution route is sequential. Direct small work creates no PLAN/RUN artifacts. This example intentionally shows one neutral mission, one isolated writer, one exact-head pre-integration review, and local final gates; it is not a UI repair graph or a promise of parallel fan-out. Builder UX Direction remains an upstream contract when a product has one; this neutral example has no UI surface.

## Harness Plan Manifest

```json
{
  "harness_plan": {
    "schema_version": 5,
    "plan_id": "PLAN-<stable-id>",
    "revision": 1,
    "objective": "<one measurable outcome and stopping condition>",
    "max_parallel_workers": 1,
    "required_reviews": ["backend_code"],
    "sources": [
      {
        "id": "SRC-001",
        "kind": "prd",
        "location": "<repo-relative path or URL>",
        "owner": "<human or team>",
        "status": "frozen",
        "content_sha256": null,
        "source_revision": "0000000000000000000000000000000000000000",
        "staged_revision": null,
        "notes": "<role or concise notes>"
      }
    ],
    "traces": [
      {
        "id": "PRD-001",
        "source_ids": ["SRC-001"],
        "priority": "must",
        "requirement": "<requirement>",
        "disposition": "planned",
        "rationale": null
      }
    ],
    "ui_surfaces": [],
    "risks": [
      {
        "id": "RISK-001",
        "description": "<risk>",
        "impact": "medium",
        "mitigation": "<mitigation>",
        "stop_condition": "<condition that stops execution>"
      }
    ],
    "batch_verifiers": [],
    "final_gates": [
      {
        "id": "final-check",
        "cwd": ".",
        "argv": ["<runner>", "<final-argument>"],
        "pass_signal": "<literal pass signal>"
      },
      {
        "id": "final-closeout",
        "cwd": ".",
        "argv": ["<runner>", "<closeout-argument>"],
        "pass_signal": "<literal pass signal>"
      }
    ],
    "graph": {
      "entry_nodes": ["N-M1"],
      "nodes": [
        {
          "id": "N-M1",
          "kind": "mission",
          "ref": "M1",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": null,
            "allowed_providers": ["codex", "claude_code", "pi", "generic"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-sol", "reasoning_effort": "high"},
              "claude_code": {"model": "sonnet", "reasoning_effort": "high"},
              "pi": {"model": null, "reasoning_effort": null},
              "generic": {"model": null, "reasoning_effort": null}
            }
          }
        },
        {
          "id": "N-M1-REVIEW",
          "kind": "verifier",
          "ref": "mission-focused",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "fix_required", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": null,
            "allowed_providers": ["codex", "claude_code", "pi", "generic"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-sol", "reasoning_effort": "medium"},
              "claude_code": {"model": "sonnet", "reasoning_effort": "medium"},
              "pi": {"model": null, "reasoning_effort": null},
              "generic": {"model": null, "reasoning_effort": null}
            }
          },
          "review": {
            "stage": "preintegration",
            "type": "backend_code",
            "mission_ids": ["M1"],
            "scope": ["src/example/**"],
            "required_evidence": ["reviewed_sha", "path-and-line findings", "pass or fix_required decision"]
          }
        },
        {
          "id": "N-FINAL-GATE",
          "kind": "verifier",
          "ref": "final-check",
          "executor": "local_command",
          "allowed_outcomes": ["pass", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": null
        },
        {
          "id": "N-CLOSEOUT-GATE",
          "kind": "verifier",
          "ref": "final-closeout",
          "executor": "local_command",
          "allowed_outcomes": ["pass", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": null
        }
      ],
      "edges": [
        {
          "id": "E-M1-REVIEW",
          "kind": "dependency",
          "from": "N-M1",
          "to": "N-M1-REVIEW",
          "on_outcomes": ["pass"],
          "max_traversals": null
        },
        {
          "id": "E-M1-REVIEW-FINAL",
          "kind": "route",
          "from": "N-M1-REVIEW",
          "to": "N-FINAL-GATE",
          "on_outcomes": ["pass"],
          "max_traversals": null
        },
        {
          "id": "E-FINAL-CLOSEOUT",
          "kind": "dependency",
          "from": "N-FINAL-GATE",
          "to": "N-CLOSEOUT-GATE",
          "on_outcomes": ["pass"],
          "max_traversals": null
        }
      ]
    },
    "missions": [
      {
        "id": "M1",
        "alias": "<short stable label>",
        "objective": "<vertical mission outcome>",
        "priority": 100,
        "merge_rank": 10,
        "trace_ids": ["PRD-001"],
        "write_scope": ["src/example/**"],
        "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md"],
        "resource_inventory_complete": true,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": true,
        "required_skills": [],
        "stop_conditions": ["<mission-specific stop condition>"],
        "worker_verifiers": [
          {
            "id": "mission-focused",
            "cwd": ".",
            "argv": ["<runner>", "<mission-argument>"],
            "pass_signal": "exit 0",
            "selection": {"mode": "changed_files", "scopes": ["src/example/**"]},
            "cache": {"mode": "session_exact", "environment_keys": ["CI"]}
          }
        ],
        "integration_verifiers": [
          {
            "id": "mission-integration",
            "cwd": ".",
            "argv": ["<runner>", "<integration-argument>"],
            "pass_signal": "<literal pass signal>"
          }
        ],
        "tasks": [
          {
            "id": "M1/T01",
            "alias": "<short stable task label>",
            "objective": "<independently verifiable outcome>",
            "acceptance_matrix": [
              {
                "test_id": "TEST-M1-T01-001",
                "trace_ids": ["PRD-001"],
                "criterion": "<observable scenario or assertion that stays inside this task>"
              }
            ],
            "trace_ids": ["PRD-001"],
            "depends_on": [],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": ["src/example/**"],
            "verifiers": [
              {
                "id": "task-focused",
                "cwd": ".",
                "argv": ["<runner>", "<task-argument>"],
                "pass_signal": "exit 0",
                "selection": {"mode": "changed_files", "scopes": ["src/example/**"]},
                "cache": {"mode": "session_exact", "environment_keys": ["CI"]}
              }
            ]
          }
        ]
      }
    ]
  }
}
```

The exact fenced JSON block is the canonical plan. New plans use PLAN schema v5. Older PLAN schemas remain readable; their recorded schema decides which fields apply. The graph is the canonical source for mission dependencies and routing. Keep the JSON valid, increment `revision` after an accepted semantic plan or graph change, and calculate the run's digest with the normalization algorithm in `references/execution-state-model.md`. There is no `execution_route` PLAN field: the selector derives it from the chosen route and actually selected safe write missions.

The single-mission example deliberately leaves `batch_verifiers` empty: a one-mission managed route has no true cross-mission batch gate. It still proves the selected runtime driver, allocates an isolated writer, checks exact authorization and scope/head bindings, runs the direct singleton pre-integration review, and closes through final gates. If two or more safe write missions are selected, the selector reports `parallel_graph` and the plan may declare real cross-mission checks.

For each `runtime_worker` node, Plan Mode may leave `preferred_provider` null and list every supported host (`codex`, `claude_code`, `pi`, and `generic`) under `allowed_providers`; provider-specific launch options remain under `provider_options`. The selected runtime adapter remains host-native and separate from the selector's `execution_route`. A large route with no usable agent capability uses `sequential_parent`: the PLAN mission stays `executor: runtime_worker`, while RUN records a parent-owned binding with `worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result` solely for lease/state validation.

Every PLAN-v5 source binds the published input with `content_sha256`, `source_revision`, or both. When `validate_harness_plan.py --repo-root` is supplied, repo-relative sources must resolve inside that root and their `content_sha256` is checked against immutable bytes; `source_revision` makes the checker read the Git blob at that revision. URLs are never fetched, so an external source needs an immutable revision or a local frozen snapshot. `staged_revision` records a proposed accepted delta while the published source fields remain canonical; it is not an executable publication. A ready or executable RUN requires every source to be `frozen` or `delta_accepted` and forbids product staging locations. Publish the accepted revision to the canonical source location, move its hash/revision into the published fields, clear `staged_revision`, then increment the PLAN revision and recompute the digest.

Task and worker declarations may use the exact `selection.mode: "changed_files"` form shown by the machine manifest's `"mode": "changed_files"` value; targeted checks follow parent-observed changed files and cache roots stay repository-external. For broad implementation plans, prefer Codex `gpt-5.6-terra` with `high` reasoning, while routine deterministic `backend_code` review uses `gpt-5.6-terra` with `medium`; provider-specific options remain per-node and the selected runtime adapter remains authoritative. A plan may set a non-null `preferred_provider` only when an explicit host preference is part of the plan; otherwise keep it null so the same canonical graph routes on every supported host. Provider examples may repeat delegated `"model": "sonnet"` and `"model": "gpt-5.6-sol"` for each matching node; Pi and generic providers keep model and reasoning values null, and stronger models remain reserved for the parent's own coordination and planning. Raise the final review to `xhigh` only when its gate warrants it.

For UI work, load `references/ui-implementation-contract.md` only when the mission writes UI or a UI review needs the detailed contract. Creation mode requires `product-design-builder` and `frontend-design`; implementation-mode `frontend-design` is used only when the user explicitly selected it for the new or high-impact visual surface and then runs in frontend-design conformance mode. A missing entry is a proposed design-input delta, not a local exception. The creation mode and conformance mode are distinct; do not bypass the frozen source pair. Run the broad final regression and browser/UI checks after exact-SHA code review and repair loops converge.

Use immutable flat task IDs such as `M1/T01`. Each task has a structured acceptance row exactly `{test_id, trace_ids, criterion}` and a verifier. Task dependencies are same-mission only; cross-mission ordering belongs in typed graph dependency edges. Scope entries are POSIX repository-relative paths or terminal `/**` subtrees. Workers never edit PLAN/RUN or frozen contract sources.

## Source Map

| Source | Path / URL | Content SHA-256 / immutable revision | Status | Role / notes |
|---|---|---|---|---|
| Product requirements | <path> | <hash or revision> | draft / frozen / delta_accepted / missing / n/a | <notes> |
| Architecture / API / data | <path> | <hash or revision> | draft / frozen / missing / n/a | <notes> |
| Design system pair | <path> | <hash or revision> | draft / frozen / missing / n/a | <load the UI reference only when applicable> |

## Delivery Context

```text
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Route: direct | plan-backed graph
Execution route (derived after selection): direct | managed_sequential | parallel_graph
Expected worker runtime: parent | subagent | app_task
Expected workspace mode: shared_checkout | parent_managed_worktree | app_managed_worktree
Expected completion channel: agent_result | thread_poll | report_file | user_relay
UI Evidence Gate: required | optional | n/a
```

These are planning expectations, not authorization. Record explicit action authorization only in RUN schema v10. `tasks.md` is an optional on-demand human view, not a second state source.

## Scope And Contract Freeze

### Must Have

- `PRD-001` <requirement>

### Non-Goals

- Parallel fan-out when fewer than two safe write missions are selected.
- UI repair graphs or unplanned design changes.

## Mission View

| Mission | Objective | Traces | Depends on | Write / deny scope | Resources | Exit verifier |
|---|---|---|---|---|---|---|
| M1 | <objective> | PRD-001 | none | src/example/** / PLAN,RUN denied | none | mission-focused |

## Plan Readiness Gate

| Readiness check | Status | Evidence / decision |
|---|---|---|
| Every in-scope trace is planned, deferred, or out of scope | draft / PASS / BLOCKED | <note> |
| Every must-have trace maps to a task and verifier | draft / PASS / BLOCKED | <note> |
| Typed graph dependency edges and task dependencies are explicit and acyclic | draft / PASS / BLOCKED | <note> |
| Scopes and typed resource inventories are complete | draft / PASS / BLOCKED | <note> |
| Worker, exact-head review, integration, and final verifiers have literal signals | draft / PASS / BLOCKED | <note> |
| Blocking decisions and approval needs are surfaced | draft / PASS / BLOCKED | <note> |

Implementation may start only after static validation passes, RUN records `plan_readiness: "ready"`, and required actions have explicit user authorization. Readiness never grants authorization.

## Stop / Ask Conditions

- <condition>
- A UI route has no frozen screen/design-system entry; load `ui-implementation-contract.md` and route a design-input delta instead of inventing a value.
- A required worktree, authorization, scope/head binding, or exact-head review cannot be proved.

## Open Risks

| Risk | Impact | Mitigation / owner |
|---|---|---|
| <risk> | <impact> | <mitigation> |
