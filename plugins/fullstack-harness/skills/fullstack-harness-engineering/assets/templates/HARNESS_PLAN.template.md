# Plan: <feature or product slice>

Use this template as `docs/goal/PLAN.md` only for long, multi-mission, high-risk, or handoff-heavy work. Keep static definitions here; keep live execution state in `RUN.md`.

## Harness Plan Manifest

```json
{
  "harness_plan": {
    "schema_version": 2,
    "plan_id": "PLAN-<stable-id>",
    "revision": 1,
    "objective": "<one measurable outcome and stopping condition>",
    "max_parallel_workers": 3,
    "sources": [
      {
        "id": "SRC-001",
        "kind": "prd",
        "location": "<repo-relative path or URL>",
        "owner": "<human or team>",
        "status": "frozen",
        "notes": "<role or concise notes>"
      }
    ],
    "traces": [
      {
        "id": "REQ-001",
        "source_ids": [
          "SRC-001"
        ],
        "priority": "must",
        "requirement": "<requirement>",
        "disposition": "planned",
        "rationale": null
      }
    ],
    "ui_surfaces": [
      {
        "id": "UI-001",
        "trace_ids": [
          "REQ-001"
        ],
        "route": "<route or screen>",
        "breakpoints": [
          "mobile",
          "desktop"
        ],
        "states": [
          "ready",
          "loading",
          "empty",
          "error"
        ],
        "evidence_gate": "required"
      }
    ],
    "risks": [
      {
        "id": "RISK-001",
        "description": "<risk>",
        "impact": "high",
        "mitigation": "<mitigation>",
        "stop_condition": "<condition that stops execution>"
      }
    ],
    "batch_verifiers": [
      {
        "id": "batch-cross-mission",
        "cwd": ".",
        "argv": [
          "<runner>",
          "<batch-argument>"
        ],
        "pass_signal": "<literal pass signal>"
      }
    ],
    "final_gates": [
      {
        "id": "e2e-primary-journey",
        "cwd": ".",
        "argv": [
          "<runner>",
          "<e2e-argument>"
        ],
        "pass_signal": "<literal pass signal>"
      }
    ],
    "missions": [
      {
        "id": "M1",
        "alias": "<short stable label>",
        "objective": "<vertical mission outcome>",
        "priority": 100,
        "merge_rank": 10,
        "depends_on": [],
        "trace_ids": [
          "REQ-001"
        ],
        "write_scope": [
          "src/example/**"
        ],
        "deny_scope": [
          "docs/goal/PLAN.md",
          "docs/goal/RUN.md"
        ],
        "resource_inventory_complete": true,
        "serialized_resources": [],
        "runtime_resources": [
          {
            "key": "service:example-http",
            "access": "exclusive"
          }
        ],
        "worktree_eligible": true,
        "stop_conditions": [
          "<mission-specific stop condition>"
        ],
        "worker_verifiers": [
          {
            "id": "mission-focused",
            "cwd": ".",
            "argv": [
              "<runner>",
              "<mission-argument>"
            ],
            "pass_signal": "<literal pass signal>"
          }
        ],
        "integration_verifiers": [
          {
            "id": "mission-integration",
            "cwd": ".",
            "argv": [
              "<runner>",
              "<integration-argument>"
            ],
            "pass_signal": "<literal pass signal>"
          }
        ],
        "tasks": [
          {
            "id": "M1/T01",
            "alias": "<short stable task label>",
            "objective": "<independently verifiable outcome>",
            "acceptance_matrix": [
              "<scenario or assertion that stays inside this task>"
            ],
            "trace_ids": [
              "REQ-001"
            ],
            "depends_on": [],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": [
              "src/example/**"
            ],
            "verifiers": [
              {
                "id": "task-focused",
                "cwd": ".",
                "argv": [
                  "<runner>",
                  "<task-argument>"
                ],
                "pass_signal": "<literal pass signal>"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

The exact fenced JSON block above is the canonical plan. Scripts read this block only. Keep it valid JSON, increment `revision` after an accepted semantic plan change, and calculate the run's digest with the normalization algorithm in `references/execution-state-model.md`. Reordering set-like arrays alone does not require a revision. Markdown tables later in this document are non-canonical human views.

Use immutable, flat task IDs such as `M1/T01`. Represent lineage only with `parent_task`; use `legacy_task_ids` only for real pre-existing identifiers. A generation-0 task may be replaced by generation-1 children, but generation-1 tasks must not split again without a mission-level replan. When accepted refinement replaces a task, set its `replaced_by`, give each child `parent_task`, `split_reason`, and `refinement_generation: 1`, then increment the plan revision and revalidate the complete graph.

Task dependencies are same-mission only. Express every cross-mission ordering requirement in the mission DAG. When refinement supersedes a task, no executable task may continue to depend on the superseded ID: rewrite those edges to the terminal replacement tasks that collectively satisfy the former outcome, using all replacement sinks by default, then revalidate the task DAG.

The manifest owns source identity/status, requirement priority/disposition, UI route/state/breakpoint evidence needs, risks, and stop conditions. Trace priorities are `must`, `should`, or `could`; dispositions are `planned`, `deferred`, or `out_of_scope`, with a non-null rationale for the latter two. UI evidence gates are `required`, `optional`, or `n/a`; risk impact is `high`, `medium`, or `low`. Use empty arrays for truly non-applicable UI or risk surfaces; do not move any field used by validation, readiness, scheduling, launch, or integration into the human tables below. Tables may add explanatory narrative that does not alter execution semantics. Worker verifiers run in the mission workspace, mission integration verifiers run after that mission reaches the integration head, batch verifiers run after a selected wave integrates, and final gates close the whole run.

Scope entries must be POSIX, repository-relative exact paths or subtrees ending in `/**`. Reject absolute paths, `..`, backslashes, negation, and other wildcard syntax. Use `runtime_resources: []` when no runtime resource applies; never use a string such as `"none"`. Allowed access values are `exclusive` and `shared_read`. Treat an incomplete or unsupported resource inventory as unsafe for parallel write execution.

## Source Map

| Source | Path / URL | Status | Role / notes |
|---|---|---|---|
| Product requirements | <path> | draft / frozen / missing / n/a | <notes> |
| Architecture / API / data | <path> | draft / frozen / missing / n/a | <notes> |
| Wireframe / flow | <path> | draft / frozen / missing / n/a | <notes> |
| Design system / page UI | <path or URL> | draft / frozen / missing / n/a | <notes> |
| Existing app baseline | <path or URL> | captured / missing / n/a | <notes> |

## Delivery Context

```text
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Expected worker runtime: parent | subagent | app_task
Expected workspace mode: shared_checkout | parent_managed_worktree | app_managed_worktree
Expected completion channel: agent_result | thread_poll | report_file | user_relay
UI Evidence Gate: required | optional | n/a
Release target:
```

These are planning expectations, not authorization. Record explicit action authorization only in the `RUN.md` ledger.

## Scope And Contract Freeze

### Must Have

- `REQ-001` <requirement>

### Should / Could / Deferred

- `<TRACE-ID>` <requirement> — planned / deferred with rationale

### Non-Goals

- <explicitly out of scope>

| Surface | Canonical source | Status | Decision / gap |
|---|---|---|---|
| Product behavior | <path/section> | frozen / draft / missing | <decision> |
| Architecture / data / API | <path/section> | frozen / draft / missing / n/a | <decision> |
| Identity / permissions | <path/section> | frozen / draft / missing / n/a | <decision> |
| UI flow and states | <path/section> | frozen / draft / missing / n/a | <decision> |
| Verification | PLAN manifest | ready / partial | <decision> |

## Traceability View

| Trace | Requirement | Mission / task | Pass signal |
|---|---|---|---|
| REQ-001 | <requirement> | M1 / M1/T01 | <literal signal> |

## Delivery Dependency Strategy

```text
Shared foundations:
Backend prerequisites:
Frontend prerequisites:
Mocked / contract-first work allowed:
First end-to-end vertical slice:
Serialized code or runtime resources:
Chosen order and rationale:
```

## Mission View

| Mission | Objective | Traces | Depends on | Write / deny scope | Resources | Exit verifier |
|---|---|---|---|---|---|---|
| M1 | <objective> | REQ-001 | none | <paths> | <typed claims> | <command/action> |

## UI Surface Matrix

Include only when UI evidence is required or optional.

| Route / screen | Source | Breakpoints | Required states | Evidence |
|---|---|---|---|---|
| <route> | <source> | <sizes> | ready/loading/empty/error/... | <screenshot/trace/test> |

## Plan Readiness Gate

| Readiness check | Status | Evidence / decision |
|---|---|---|
| Every in-scope trace is planned, deferred, or out of scope | draft / PASS / BLOCKED | <note> |
| Every must-have trace maps to a task and verifier | draft / PASS / BLOCKED | <note> |
| Canonical sources, priorities, dispositions, risks, and stop conditions are complete | draft / PASS / BLOCKED | <note> |
| Mission and task dependency graphs are explicit and acyclic | draft / PASS / BLOCKED | <note> |
| Frontend/backend/data integration points are defined | draft / PASS / BLOCKED | <note> |
| Shared foundations and migrations are ordered | draft / PASS / BLOCKED | <note> |
| UI routes, breakpoints, states, and evidence are planned | draft / PASS / BLOCKED / n/a | <note> |
| Scopes use the supported grammar and resources are complete | draft / PASS / BLOCKED | <note> |
| Worker, mission-integration, batch, and final verifiers have literal signals | draft / PASS / BLOCKED | <note> |
| Blocking decisions and approval needs are surfaced | draft / PASS / BLOCKED | <note> |

Implementation may start only after static validation passes, `RUN.md` records `plan_readiness: "ready"`, and the required actions have explicit user authorization. Readiness never grants authorization by itself.

## Stop / Ask Conditions

- <condition>

## Open Risks

| Risk | Impact | Mitigation / owner |
|---|---|---|
| <risk> | <impact> | <mitigation> |
