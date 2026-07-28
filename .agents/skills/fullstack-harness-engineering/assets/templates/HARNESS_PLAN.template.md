# Plan: <feature or product slice>

Use this template as `docs/goal/PLAN.md` only for long, multi-mission, high-risk, or handoff-heavy work. Keep static definitions here; keep live execution state in `RUN.md`. Resolve the target repository's existing branch model before filling branch fields; the template's `codex/<short-name>` run branch and `main` default branch are fallbacks, not overrides.

## Harness Plan Manifest

```json
{
  "harness_plan": {
    "schema_version": 5,
    "plan_id": "PLAN-<stable-id>",
    "revision": 1,
    "objective": "<one measurable outcome and stopping condition>",
    "max_parallel_workers": 8,
    "required_reviews": ["frontend_code", "visual"],
    "sources": [
      {
        "id": "SRC-001",
        "kind": "prd",
        "location": "<repo-relative path or URL>",
        "owner": "<human or team>",
        "status": "frozen",
        "content_sha256": null,
        "source_revision": "<immutable published upstream revision, or null>",
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
    "ui_surfaces": [
      {
        "id": "UI-001",
        "trace_ids": ["PRD-001"],
        "route": "<route or screen>",
        "breakpoints": ["<copy the complete viewports or sizeClasses set from design-system.json>"],
        "states": ["<copy the complete stateMatrix from design-system.json, preserving order>"],
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
        "argv": ["<runner>", "<batch-argument>"],
        "pass_signal": "<literal pass signal>"
      }
    ],
    "final_gates": [
      {
        "id": "e2e-primary-journey",
        "cwd": ".",
        "argv": ["<runner>", "<e2e-argument>"],
        "pass_signal": "<literal pass signal>"
      },
      {
        "id": "final-closeout",
        "cwd": ".",
        "argv": ["<runner>", "<final-closeout-argument>"],
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
            "preferred_provider": "claude_code",
            "allowed_providers": ["codex", "claude_code"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-sol", "reasoning_effort": "high"},
              "claude_code": {"model": "sonnet", "reasoning_effort": "high"}
            }
          }
        },
        {
          "id": "N-FRONTEND-REVIEW",
          "kind": "verifier",
          "ref": "batch-cross-mission",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "fix_required", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "claude_code",
            "allowed_providers": ["codex", "claude_code"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-sol", "reasoning_effort": "medium"},
              "claude_code": {"model": "sonnet", "reasoning_effort": "medium"}
            }
          },
          "review": {
            "type": "frontend_code",
            "mission_ids": ["M1"],
            "scope": ["src/example/**"],
            "required_evidence": ["reviewed_sha", "path-and-line findings", "pass or fix_required decision"]
          }
        },
        {
          "id": "N-FINAL-GATE",
          "kind": "verifier",
          "ref": "e2e-primary-journey",
          "executor": "local_command",
          "allowed_outcomes": ["pass", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": null
        },
        {
          "id": "N-VISUAL-REVIEW",
          "kind": "verifier",
          "ref": "e2e-primary-journey",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "fix_required", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "claude_code",
            "allowed_providers": ["codex", "claude_code"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-sol", "reasoning_effort": "medium"},
              "claude_code": {"model": "sonnet", "reasoning_effort": "medium"}
            }
          },
          "review": {
            "type": "visual",
            "mission_ids": ["M1", "M3"],
            "scope": ["src/example/**"],
            "required_evidence": ["reviewed_sha", "required-breakpoint screenshots", "visual findings and decision"]
          }
        },
        {
          "id": "N-VISUAL-REPAIR",
          "kind": "mission",
          "ref": "M3",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "claude_code",
            "allowed_providers": ["codex", "claude_code"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-sol", "reasoning_effort": "high"},
              "claude_code": {"model": "sonnet", "reasoning_effort": "high"}
            }
          }
        },
        {
          "id": "N-VISUAL-REPAIR-CODE-REVIEW",
          "kind": "verifier",
          "ref": "batch-cross-mission",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "fix_required", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "claude_code",
            "allowed_providers": ["codex", "claude_code"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-sol", "reasoning_effort": "medium"},
              "claude_code": {"model": "sonnet", "reasoning_effort": "medium"}
            }
          },
          "review": {
            "type": "frontend_code",
            "mission_ids": ["M3"],
            "scope": ["src/example/**"],
            "required_evidence": ["reviewed_sha", "path-and-line findings", "pass or fix_required decision"]
          }
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
          "id": "E-M1-FRONTEND-REVIEW",
          "kind": "dependency",
          "from": "N-M1",
          "to": "N-FRONTEND-REVIEW",
          "on_outcomes": ["pass"],
          "max_traversals": null
        },
        {
          "id": "E-FRONTEND-FINAL-GATE",
          "kind": "route",
          "from": "N-FRONTEND-REVIEW",
          "to": "N-FINAL-GATE",
          "on_outcomes": ["pass"],
          "max_traversals": null
        },
        {
          "id": "E-FINAL-VISUAL-REVIEW",
          "kind": "dependency",
          "from": "N-FINAL-GATE",
          "to": "N-VISUAL-REVIEW",
          "on_outcomes": ["pass"],
          "max_traversals": null
        },
        {
          "id": "E-VISUAL-REVIEW-REPAIR",
          "kind": "route",
          "from": "N-VISUAL-REVIEW",
          "to": "N-VISUAL-REPAIR",
          "on_outcomes": ["fix_required"],
          "max_traversals": 2
        },
        {
          "id": "E-VISUAL-REPAIR-CODE-REVIEW",
          "kind": "dependency",
          "from": "N-VISUAL-REPAIR",
          "to": "N-VISUAL-REPAIR-CODE-REVIEW",
          "on_outcomes": ["pass"],
          "max_traversals": null
        },
        {
          "id": "E-VISUAL-REPAIR-REREVIEW",
          "kind": "route",
          "from": "N-VISUAL-REPAIR-CODE-REVIEW",
          "to": "N-VISUAL-REVIEW",
          "on_outcomes": ["pass"],
          "max_traversals": 2
        },
        {
          "id": "E-VISUAL-CLOSEOUT",
          "kind": "route",
          "from": "N-VISUAL-REVIEW",
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
        "runtime_resources": [{"key": "service:example-http", "access": "exclusive"}],
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
      },
      {
        "id": "M3",
        "alias": "visual-review-repair",
        "objective": "Apply only accepted visual review findings, regenerate affected evidence, and return the changed head through the same visual review.",
        "priority": 80,
        "merge_rank": 30,
        "trace_ids": ["PRD-001"],
        "write_scope": ["src/example/**", "docs/goal/evidence/**"],
        "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md"],
        "resource_inventory_complete": true,
        "serialized_resources": [],
        "runtime_resources": [{"key": "service:example-http", "access": "exclusive"}],
        "worktree_eligible": true,
        "required_skills": [],
        "stop_conditions": [
          "Stop if a visual finding requires a design-contract change instead of an in-scope implementation repair."
        ],
        "worker_verifiers": [
          {
            "id": "visual-repair-focused",
            "cwd": ".",
            "argv": ["<runner>", "<visual-repair-argument>"],
            "pass_signal": "exit 0",
            "selection": {"mode": "changed_files", "scopes": ["src/example/**", "docs/goal/evidence/**"]},
            "cache": {"mode": "session_exact", "environment_keys": ["CI"]}
          }
        ],
        "integration_verifiers": [
          {
            "id": "visual-repair-integration",
            "cwd": ".",
            "argv": ["<runner>", "<visual-repair-integration-argument>"],
            "pass_signal": "<literal pass signal>"
          }
        ],
        "tasks": [
          {
            "id": "M3/T01",
            "alias": "apply-visual-review-findings",
            "objective": "Repair the accepted in-scope visual findings and refresh every affected screenshot artifact.",
            "acceptance_matrix": [
              {
                "test_id": "TEST-M3-T01-001",
                "trace_ids": ["PRD-001"],
                "criterion": "Every accepted blocking visual finding is resolved and affected evidence is recaptured for the repaired head."
              }
            ],
            "trace_ids": ["PRD-001"],
            "depends_on": [],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": ["src/example/**", "docs/goal/evidence/**"],
            "verifiers": [
              {
                "id": "visual-repair-task",
                "cwd": ".",
                "argv": ["<runner>", "<visual-repair-task-argument>"],
                "pass_signal": "exit 0",
                "selection": {"mode": "changed_files", "scopes": ["src/example/**", "docs/goal/evidence/**"]},
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

The exact fenced JSON block above is the canonical plan. Scripts read this block only. New plans use PLAN schema v5. The graph is the canonical source for mission dependencies and routing. Older PLAN schemas remain readable; their recorded schema decides which fields apply. Keep the JSON valid, increment `revision` after an accepted semantic plan or graph change, and calculate the run's digest with the normalization algorithm in `references/execution-state-model.md`. Reordering set-like arrays alone does not require a revision. Markdown tables later in this document are non-canonical human views.

For each `runtime_worker` node, Plan Mode chooses the allowed and preferred provider first, then may set provider-specific launch options under `provider_options`. For general-purpose nodes and backend implementation, prefer Codex `gpt-5.6-terra` with `high` reasoning and keep Claude Code `sonnet` with `high` reasoning as the availability fallback. Choose review effort by risk: routine deterministic `backend_code`, `frontend_code`, and visual reviews use `medium`; reserve `xhigh` for security, migration, difficult correctness, broad architecture, or genuinely ambiguous visual judgment. This UI-bearing example applies the frontend model override below. Plan Mode may replace either option per node using the mission-selection policy. Codex and Claude Code accept a model plus a runtime-supported reasoning effort; the destination runtime still validates the exact pair at launch. Keep effort `null` when the provider default is intentional. Omit `provider_options` to use runtime defaults. Options may name only providers listed in `allowed_providers`; changing them is a semantic plan revision.

Every PLAN-v5 source binds the published input with `content_sha256`, `source_revision`, or both. A path or URL alone is not a freeze. `staged_revision` records a proposed accepted delta while the published source fields remain canonical; it is not an executable publication. A ready or executable RUN requires every source to be `frozen` or `delta_accepted` and forbids product staging locations. Publish the accepted revision to the canonical source location, move its hash/revision into the published fields, clear `staged_revision`, then increment the PLAN revision and recompute the digest.

For frontend/UI implementation, use Codex `gpt-5.6-sol` with `high` reasoning; a delegated Claude Code node still defaults to `sonnet`, with `high` reasoning for the implementation node and `medium` for routine `frontend_code`/visual-review nodes unless the recorded review risk justifies a higher effort. Reserve any stronger pinned Claude model — whichever premium model opened the current session — for the parent's own coordination and planning, never for a delegated node by default. These role-specific options replace the generic fallback on those nodes.

For full-stack work, plan separate `frontend_code` and `backend_code` runtime-worker verifier nodes after their matching missions. If UI is present, place a `visual` review after integration. Each review node must name the missions and repository scope it reviews and bind to one exact reviewed SHA in RUN. A pre-integration review covers one mission; `fix_required` returns to that mission's original task, thread, and worktree, and `max_attempts` bounds review of each changed head. A post-integration or batch review may route `fix_required` to a bounded repair node based on the reviewed integration head. Combine reviews only when the scope is genuinely single-surface and record why.

List every applicable review type in `required_reviews`. PLAN validation rejects a required type without a matching runtime-worker verifier node. Use an empty list only when the work has no frontend, backend, or visual review surface; explain that applicability decision in the human review map.

Use immutable, flat task IDs such as `M1/T01`. Represent lineage only with `parent_task`; use `legacy_task_ids` only for real pre-existing identifiers. A generation-0 task may be replaced by generation-1 children, but generation-1 tasks must not split again without a mission-level replan. When accepted refinement replaces a task, set its `replaced_by`, give each child `parent_task`, `split_reason`, and `refinement_generation: 1`, then increment the plan revision and revalidate the complete graph.

Task dependencies are same-mission only. In PLAN schema v5, express every cross-mission ordering requirement with `graph.edges` of kind `dependency`; do not retain a second `missions[].depends_on` source. Dependency edges must stay acyclic. Conditional `route` edges may form a correction loop only when every cyclic route has `max_traversals` and the cycle has an exit edge. A pre-integration runtime review that can return `fix_required` may use direct mission dependency plus `max_attempts`: the parent sends findings to the original mission task/worktree and re-arms review only after a changed head passes its focused verifier. Post-integration review uses a bounded repair route and returns the repair through the same review before any deterministic final gate. When refinement supersedes a task, no executable task may continue to depend on the superseded ID: rewrite those edges to the terminal replacement tasks that collectively satisfy the former outcome, using all replacement sinks by default, then revalidate the task DAG.

Each PLAN-v5 `acceptance_matrix` row is exactly `{test_id, trace_ids, criterion}`. Use a stable `TEST-*` ID, bind only traces declared by that task, and write one observable criterion. Every planned task trace must appear in at least one acceptance row; prose-only arrays from older schemas are readable but are not the current authoring contract.

The manifest owns source identity/status, requirement priority/disposition, UI route/state/breakpoint evidence needs, risks, and stop conditions. Trace priorities are `must`, `should`, or `could`; dispositions are `planned`, `deferred`, or `out_of_scope`, with a non-null rationale for the latter two. UI evidence gates are `required`, `optional`, or `n/a`; risk impact is `high`, `medium`, or `low`. Use empty arrays for truly non-applicable UI or risk surfaces; do not move any field used by validation, readiness, scheduling, launch, or integration into the human tables below. Tables may add explanatory narrative that does not alter execution semantics. Worker verifiers run in the mission workspace, mission integration verifiers run after that mission reaches the integration head, batch verifiers run after a selected wave integrates, and final gates close the whole run.

Task and worker verifiers may declare `selection.mode: "changed_files"`; keep every selection scope inside the owning task or mission write scope. The parent-observed changed files decide applicability. Integration, batch, and final verifiers remain `always`. Omit `selection` for the existing always-run behavior. `cache.mode: "session_exact"` is only for deterministic local `exit 0` commands. List every environment key that can affect the result, and use a repository-external session cache root. Omit `cache` or use `disabled` for network, shared database, time/random, browser, review, migration, smoke, or other mutable checks.

Plan focused checks at task/worker level, the mission's integration surface at integration level, true cross-mission checks at batch level, and broad regression/browser/UI proof at final level. Place expensive final browser and screenshot work after exact-SHA code review and repair loops converge.

Scope entries must be POSIX, repository-relative exact paths or subtrees ending in `/**`. Reject absolute paths, `..`, backslashes, negation, and other wildcard syntax. Use `runtime_resources: []` when no runtime resource applies; never use a string such as `"none"`. Allowed access values are `exclusive` and `shared_read`. Treat an incomplete or unsupported resource inventory as unsafe for parallel write execution.

`required_skills` names every installed skill (by its `name:` frontmatter, e.g. `frontend-design`) that mission's worker must load before implementing, beyond this harness core itself. Use `[]` when the mission needs no additional skill. Record the planner's explicit choice here; do not have a worker infer a skill from its `write_scope` glob pattern. Every launch path (`WORKER_GOAL.template.md`, a Codex app-task prompt, or a Claude Dynamic Workflow agent prompt) must carry this list verbatim so a spawned worker actually learns to load it — see `references/worktree-thread-orchestration.md`'s Worker Handoff.

For UI implementation, `[]` remains the default. Add `frontend-design` only when the user explicitly selected it for a new or high-impact visual surface. Then state `frontend-design conformance mode` in the mission objective or stop conditions: the worker follows the frozen wireframe, design system, registry, route recipe, and mockup; it does not invent a direction, token, primitive, variant, component, motion pattern, or structure. A missing entry returns as a design-input delta and blocks the mission until the package and PLAN digest are revised.

On a greenfield repository, mission M1 scaffolds the workspace and every layer the frozen `stack-decisions.md` Frontend Technology Decision names, before any archetype-specific mission runs. See `references/platform-archetypes.md`'s Greenfield / Empty Repository section for the per-toolchain detection table and a complete, copy-paste-ready `M1 workspace-foundation` mission object.

## Source Map

| Source | Path / URL | Content SHA-256 / immutable revision | Status | Role / notes |
|---|---|---|---|---|
| Product requirements | <path> | <hash or revision> | draft / frozen / missing / n/a | <notes> |
| Builder UX Direction | <PRD section, path, or URL> | <hash or revision> | selected / provisional / assumed / conflicting / missing / n/a | <human owner, direction, validation need> |
| Architecture / API / data | <path> | <hash or revision> | draft / frozen / missing / n/a | <notes> |
| Stack decisions (frontend, backend/data, mobile/desktop) | <path> | <hash or revision> | required / selected / recommended / provisional / missing / n/a | <resolved layers; a still-provisional layer is a stop condition> |
| Wireframe / flow | <path> | <hash or revision> | draft / frozen / missing / n/a | <notes> |
| Design system | <design-system.md path> | <hash or revision> | draft / frozen / missing / n/a | <tokens, primitive layers, components, state matrix, guardrails> |
| Design system (machine) | <design-system.json path> | <hash or revision> | draft / frozen / missing / n/a | <the allowlist check_ui_contract.py reads; freezes with the Markdown> |
| Existing app baseline | <path or URL> | <hash or revision> | captured / missing / n/a | <notes> |

## Delivery Context

```text
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Expected worker runtime: parent | subagent | app_task
Expected workspace mode: shared_checkout | parent_managed_worktree | app_managed_worktree
Expected completion channel: agent_result | thread_poll | report_file | user_relay
UI Evidence Gate: required | optional | n/a
UX Validation Gate: required | optional | n/a
```

These are planning expectations, not authorization. Record explicit action authorization only in RUN schema v10.

## Scope And Contract Freeze

### Must Have

- `PRD-001` <requirement>

### Should / Could / Deferred

- `<TRACE-ID>` <requirement> — planned / deferred with rationale

### Non-Goals

- <explicitly out of scope>

| Surface | Canonical source | Status | Decision / gap |
|---|---|---|---|
| Product behavior | <path/section> | frozen / draft / missing | <decision> |
| Architecture / data / API | <path/section> | frozen / draft / missing / n/a | <decision> |
| Identity / permissions | <path/section> | frozen / draft / missing / n/a | <decision> |
| Builder UX Direction | <path/section> | selected / provisional / assumed / conflicting / missing / n/a | <human owner, controlling decisions, validation need> |
| UI flow and states | <path/section> | frozen / draft / missing / n/a | <decision> |
| Design system pair | <path/section> | frozen / draft / missing / n/a | <decision; one file without the other is `partial`, and a route with no wireframe screen is a blocker> |
| Verification | PLAN manifest | ready / partial | <decision> |

## Traceability View

| Trace | Requirement | Mission / task | Pass signal |
|---|---|---|---|
| PRD-001 | <requirement> | M1 / M1/T01 | <literal signal> |
| UX-001 | <critical task, interaction/recovery, or usability requirement> | M1 / M1/T02 | <direction, behavior, or usability signal> |

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
| M1 | <objective> | PRD-001 | none | <paths> | <typed claims> | <command/action> |

## UI Surface Matrix

Include only when UI evidence is required or optional.

| Route / screen | Source | Breakpoints | Required states | Evidence |
|---|---|---|---|---|
| <route> | <wireframes.md screen entry> | <copied from design-system.json: viewports or sizeClasses> | ready/loading/empty/error/... | <screenshot/trace/test> |

Each `ui_surfaces[].route` is copied verbatim from the `Route(s):` line of that screen's entry in `wireframes.md` — that field is what makes a route resolvable to a screen, and inventing a route string here breaks the lookup implementation depends on. A screen serving several routes contributes one `ui_surfaces` entry per route, all sharing the screen's `UI-*` id. A wireframe screen whose `Route(s):` is `n/a` has no addressable route and gets no `ui_surfaces` entry; cover it through the parent route that reaches it.

When the product has a design system, `design-system.json`'s `stateMatrix` is the state checklist for every surface and its `viewports` or `sizeClasses` is the required responsive set — take them from there, do not restate a default here. `viewports` is a numeric pixel-width array, while a PLAN `breakpoints` entry is a label that ends in one of those widths (`mobile-390` covers `390`); `sizeClasses` is a string array matched verbatim. Putting the labels into `design-system.json` fails the responsive-set check, which reports the design system rather than the type mismatch. A state a surface genuinely cannot have is listed as `<state>:n/a`, not omitted, so `validate_harness_plan.py --design-system` can tell a deliberate exclusion from an oversight. Mirror those values into the canonical `ui_surfaces` object above — the table is a view.

## Plan Readiness Gate

| Readiness check | Status | Evidence / decision |
|---|---|---|
| Every in-scope trace is planned, deferred, or out of scope | draft / PASS / BLOCKED | <note> |
| Every must-have trace maps to a task and verifier | draft / PASS / BLOCKED | <note> |
| Canonical sources, priorities, dispositions, risks, and stop conditions are complete | draft / PASS / BLOCKED | <note> |
| Typed graph dependency edges and task dependencies are explicit and acyclic; route loops are bounded with exits | draft / PASS / BLOCKED | <note> |
| Frontend/backend/data integration points are defined | draft / PASS / BLOCKED | <note> |
| Shared foundations and migrations are ordered | draft / PASS / BLOCKED | <note> |
| UI routes, breakpoints, states, and evidence are planned | draft / PASS / BLOCKED / n/a | <note> |
| Every in-scope route has a `wireframes.md` screen entry, every `DS-*` trace resolves to a `design-system.json` entry, and the UI contract check is a planned verifier | draft / PASS / BLOCKED / n/a | <note> |
| Builder UX Direction owner, decision statuses, conflicts, and UX validation depth are explicit | draft / PASS / BLOCKED / n/a | <note> |
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
