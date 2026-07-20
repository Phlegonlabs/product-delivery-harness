# Plan: <feature or product slice>

Use this template as `docs/goal/PLAN.md` only for long, multi-mission, high-risk, or handoff-heavy work. Keep static definitions here; keep live execution state in `RUN.md`.

## Harness Plan Manifest

```json
{
  "harness_plan": {
    "schema_version": 4,
    "plan_id": "PLAN-<stable-id>",
    "revision": 1,
    "objective": "<one measurable outcome and stopping condition>",
    "max_parallel_workers": 3,
    "required_reviews": [
      "frontend_code",
      "visual"
    ],
    "sources": [
      {
        "id": "SRC-001",
        "kind": "prd",
        "location": "<repo-relative path or URL>",
        "owner": "<human or team>",
        "status": "frozen",
        "content_sha256": "<lowercase SHA-256 of the frozen content, or null>",
        "source_revision": "<immutable upstream revision, or null>",
        "notes": "<role or concise notes>"
      }
    ],
    "traces": [
      {
        "id": "PRD-001",
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
          "PRD-001"
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
    "release": {
      "provider": "cloudflare",
      "targets": [
        {
          "id": "development",
          "source": "pr_head",
          "worker_name": "<app-name>-development",
          "wrangler_config_path": "<app-directory>/wrangler.jsonc",
          "wrangler_environment": "development",
          "data_mode": "isolated_non_production",
          "payment_mode": "sandbox",
          "auth_mode": "development",
          "prerequisites": [
            "current_head_ci"
          ],
          "migration_command": null,
          "deploy_command": {
            "id": "deploy-development",
            "cwd": "<app-directory>",
            "argv": [
              "npx",
              "wrangler",
              "deploy",
              "--env",
              "development"
            ],
            "pass_signal": "Wrangler reports a successful development deployment"
          },
          "smoke_verifiers": [
            {
              "id": "smoke-development",
              "cwd": ".",
              "argv": [
                "<smoke-runner>",
                "<development-smoke-argument>"
              ],
              "pass_signal": "Development login, sandbox payment, and primary journey pass"
            }
          ]
        },
        {
          "id": "production",
          "source": "merged_main",
          "worker_name": "<app-name>-production",
          "wrangler_config_path": "<app-directory>/wrangler.jsonc",
          "wrangler_environment": "production",
          "data_mode": "production",
          "payment_mode": "live",
          "auth_mode": "production",
          "prerequisites": [
            "development_pass",
            "merged_main"
          ],
          "migration_command": null,
          "deploy_command": {
            "id": "deploy-production",
            "cwd": "<app-directory>",
            "argv": [
              "npx",
              "wrangler",
              "deploy",
              "--env",
              "production"
            ],
            "pass_signal": "Wrangler reports a successful production deployment"
          },
          "smoke_verifiers": [
            {
              "id": "smoke-production",
              "cwd": ".",
              "argv": [
                "<smoke-runner>",
                "<production-smoke-argument>"
              ],
              "pass_signal": "Production critical routes and primary journey pass"
            }
          ]
        }
      ]
    },
    "graph": {
      "entry_nodes": [
        "N-M1"
      ],
      "nodes": [
        {
          "id": "N-M1",
          "kind": "mission",
          "ref": "M1",
          "executor": "runtime_worker",
          "allowed_outcomes": [
            "pass",
            "retryable_failure",
            "blocked",
            "contract_gap"
          ],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "claude_code",
            "allowed_providers": [
              "codex",
              "claude_code"
            ],
            "provider_options": {
              "codex": {
                "model": "gpt-5.6-sol",
                "reasoning_effort": "xhigh"
              },
              "claude_code": {
                "model": "claude-fable-5",
                "reasoning_effort": "high"
              }
            }
          }
        },
        {
          "id": "N-FRONTEND-REVIEW",
          "kind": "verifier",
          "ref": "batch-cross-mission",
          "executor": "runtime_worker",
          "allowed_outcomes": [
            "pass",
            "fix_required",
            "blocked",
            "contract_gap"
          ],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "claude_code",
            "allowed_providers": [
              "codex",
              "claude_code"
            ],
            "provider_options": {
              "codex": {
                "model": "gpt-5.6-sol",
                "reasoning_effort": "medium"
              },
              "claude_code": {
                "model": "claude-fable-5",
                "reasoning_effort": "medium"
              }
            }
          },
          "review": {
            "type": "frontend_code",
            "mission_ids": [
              "M1"
            ],
            "scope": [
              "src/example/**"
            ],
            "required_evidence": [
              "reviewed_sha",
              "path-and-line findings",
              "pass or fix_required decision"
            ]
          }
        },
        {
          "id": "N-VISUAL-REVIEW",
          "kind": "verifier",
          "ref": "e2e-primary-journey",
          "executor": "runtime_worker",
          "allowed_outcomes": [
            "pass",
            "fix_required",
            "blocked",
            "contract_gap"
          ],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "claude_code",
            "allowed_providers": [
              "codex",
              "claude_code"
            ],
            "provider_options": {
              "codex": {
                "model": "gpt-5.6-sol",
                "reasoning_effort": "medium"
              },
              "claude_code": {
                "model": "claude-fable-5",
                "reasoning_effort": "medium"
              }
            }
          },
          "review": {
            "type": "visual",
            "mission_ids": [
              "M1"
            ],
            "scope": [
              "src/example/**"
            ],
            "required_evidence": [
              "reviewed_sha",
              "required-breakpoint screenshots",
              "visual findings and decision"
            ]
          }
        }
      ],
      "edges": [
        {
          "id": "E-M1-FRONTEND-REVIEW",
          "kind": "dependency",
          "from": "N-M1",
          "to": "N-FRONTEND-REVIEW",
          "on_outcomes": [
            "pass"
          ],
          "max_traversals": null
        },
        {
          "id": "E-FRONTEND-VISUAL-REVIEW",
          "kind": "dependency",
          "from": "N-FRONTEND-REVIEW",
          "to": "N-VISUAL-REVIEW",
          "on_outcomes": [
            "pass"
          ],
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
        "trace_ids": [
          "PRD-001"
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
            "pass_signal": "exit 0",
            "selection": {
              "mode": "changed_files",
              "scopes": [
                "src/example/**"
              ]
            },
            "cache": {
              "mode": "session_exact",
              "environment_keys": [
                "CI"
              ]
            }
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
              "PRD-001"
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
                "pass_signal": "exit 0",
                "selection": {
                  "mode": "changed_files",
                  "scopes": [
                    "src/example/**"
                  ]
                },
                "cache": {
                  "mode": "session_exact",
                  "environment_keys": [
                    "CI"
                  ]
                }
              }
            ]
          }
        ]
      }
    ]
  }
}
```

The exact fenced JSON block above is the canonical plan. Scripts read this block only. New plans use schema v4. The graph is the canonical source for mission dependencies and routing; existing schema-v2 and schema-v3 plans remain readable. Keep the displayed `release` object only for a deployable Cloudflare plan; remove the whole object for non-Cloudflare or non-deployable work. Schema version exposes the field but does not enable it by itself. Keep the JSON valid, increment `revision` after an accepted semantic plan or graph change, and calculate the run's digest with the normalization algorithm in `references/execution-state-model.md`. Reordering set-like arrays alone does not require a revision. Markdown tables later in this document are non-canonical human views.

For each `runtime_worker` node, Plan Mode chooses the allowed and preferred provider first, then may set provider-specific launch options under `provider_options`. For general-purpose nodes and backend implementation, prefer Codex `gpt-5.6-terra` with `xhigh` reasoning and keep Claude Code `sonnet` as the availability fallback. Choose review effort by risk: routine deterministic `backend_code`, `frontend_code`, and visual reviews use `medium`; reserve `high` or `xhigh` for security, migration, difficult correctness, broad architecture, or genuinely ambiguous visual judgment. This UI-bearing example applies the frontend model override below. Plan Mode may replace either option per node using the mission-selection policy. Codex and Claude Code accept a model plus a runtime-supported reasoning effort; the destination runtime still validates the exact pair at launch. Keep effort `null` when the provider default is intentional. Omit `provider_options` to use runtime defaults. Options may name only providers listed in `allowed_providers`; changing them is a semantic plan revision.

Every schema-v4 source must bind the frozen input with `content_sha256`, `source_revision`, or both. A path or URL alone is not a freeze. Recompute the PLAN digest whenever source content or its immutable upstream revision changes.

For frontend/UI implementation, set Claude to the pinned `claude-fable-5` ID with `high` reasoning and use Codex `gpt-5.6-sol` with `xhigh` reasoning as the availability fallback. Routine `frontend_code` and visual-review nodes use the same models with `medium` reasoning unless the recorded review risk justifies a higher effort. These role-specific options replace the generic fallback on those nodes.

For full-stack work, plan separate `frontend_code` and `backend_code` runtime-worker verifier nodes after their matching missions. If UI is present, place a `visual` review after integration or preview. Each review node must name the missions and repository scope it reviews, bind to one exact reviewed SHA in RUN, and route `fix_required` back to the matching bounded repair path. Combine reviews only when the scope is genuinely single-surface and record why.

List every applicable review type in `required_reviews`. PLAN validation rejects a required type without a matching runtime-worker verifier node. Use an empty list only when the work has no frontend, backend, or visual review surface; explain that applicability decision in the human review map.

Use immutable, flat task IDs such as `M1/T01`. Represent lineage only with `parent_task`; use `legacy_task_ids` only for real pre-existing identifiers. A generation-0 task may be replaced by generation-1 children, but generation-1 tasks must not split again without a mission-level replan. When accepted refinement replaces a task, set its `replaced_by`, give each child `parent_task`, `split_reason`, and `refinement_generation: 1`, then increment the plan revision and revalidate the complete graph.

Task dependencies are same-mission only. In schema v4, express every cross-mission ordering requirement with `graph.edges` of kind `dependency`; do not retain a second `missions[].depends_on` source. Dependency edges must stay acyclic. Conditional `route` edges may form a correction loop only when every cyclic route has `max_traversals` and the cycle has an exit edge. When refinement supersedes a task, no executable task may continue to depend on the superseded ID: rewrite those edges to the terminal replacement tasks that collectively satisfy the former outcome, using all replacement sinks by default, then revalidate the task DAG.

The manifest owns source identity/status, requirement priority/disposition, UI route/state/breakpoint evidence needs, risks, and stop conditions. Trace priorities are `must`, `should`, or `could`; dispositions are `planned`, `deferred`, or `out_of_scope`, with a non-null rationale for the latter two. UI evidence gates are `required`, `optional`, or `n/a`; risk impact is `high`, `medium`, or `low`. Use empty arrays for truly non-applicable UI or risk surfaces; do not move any field used by validation, readiness, scheduling, launch, or integration into the human tables below. Tables may add explanatory narrative that does not alter execution semantics. Worker verifiers run in the mission workspace, mission integration verifiers run after that mission reaches the integration head, batch verifiers run after a selected wave integrates, and final gates close the whole run.

Task and worker verifiers may declare `selection.mode: "changed_files"`; keep every selection scope inside the owning task or mission write scope. The parent-observed changed files decide applicability. Integration, batch, and final verifiers remain `always`. Omit `selection` for the existing always-run behavior. `cache.mode: "session_exact"` is only for deterministic local `exit 0` commands. List every environment key that can affect the result, and use a repository-external session cache root. Omit `cache` or use `disabled` for network, shared database, time/random, browser, review, migration, deployment, smoke, or other mutable checks.

Plan focused checks at task/worker level, the mission's integration surface at integration level, true cross-mission checks at batch level, and broad regression/browser/UI/release proof at final level. Place expensive final browser and screenshot work after exact-SHA code review and repair loops converge.

Scope entries must be POSIX, repository-relative exact paths or subtrees ending in `/**`. Reject absolute paths, `..`, backslashes, negation, and other wildcard syntax. Use `runtime_resources: []` when no runtime resource applies; never use a string such as `"none"`. Allowed access values are `exclusive` and `shared_read`. Treat an incomplete or unsupported resource inventory as unsafe for parallel write execution.

## Source Map

| Source | Path / URL | Content SHA-256 / immutable revision | Status | Role / notes |
|---|---|---|---|---|
| Product requirements | <path> | <hash or revision> | draft / frozen / missing / n/a | <notes> |
| Builder UX Direction | <PRD section, path, or URL> | <hash or revision> | selected / provisional / assumed / conflicting / missing / n/a | <human owner, direction, validation need> |
| Architecture / API / data | <path> | <hash or revision> | draft / frozen / missing / n/a | <notes> |
| Wireframe / flow | <path> | <hash or revision> | draft / frozen / missing / n/a | <notes> |
| Design system / page UI | <path or URL> | <hash or revision> | draft / frozen / missing / n/a | <notes> |
| Existing app baseline | <path or URL> | <hash or revision> | captured / missing / n/a | <notes> |

## Delivery Context

```text
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Expected worker runtime: parent | subagent | app_task
Expected workspace mode: shared_checkout | parent_managed_worktree | app_managed_worktree
Expected completion channel: agent_result | thread_poll | report_file | user_relay
UI Evidence Gate: required | optional | n/a
UX Validation Gate: required | optional | n/a
Release target:
```

For deployable Cloudflare applications, the canonical `release` object owns the development and production Worker names, Wrangler environments, isolated data/auth/payment modes, exact deployment commands, smoke verifiers, and promotion prerequisites. Use `migration_command: null` only when the target has no remote migration step. The development target binds to the current PR head after CI; production binds to the merged `main` SHA only after development passes.

These are planning expectations, not authorization. Record explicit action authorization only in the `RUN.md` ledger.

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
| <route> | <source> | <sizes> | ready/loading/empty/error/... | <screenshot/trace/test> |

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
| Builder UX Direction owner, decision statuses, conflicts, and UX validation depth are explicit | draft / PASS / BLOCKED / n/a | <note> |
| Scopes use the supported grammar and resources are complete | draft / PASS / BLOCKED | <note> |
| Worker, mission-integration, batch, and final verifiers have literal signals | draft / PASS / BLOCKED | <note> |
| Blocking decisions and approval needs are surfaced | draft / PASS / BLOCKED | <note> |
| Cloudflare development and production targets, isolated resources, migration order, promotion prerequisites, and smoke verifiers are complete | draft / PASS / BLOCKED / n/a | <note> |

Implementation may start only after static validation passes, `RUN.md` records `plan_readiness: "ready"`, and the required actions have explicit user authorization. Readiness never grants authorization by itself.

## Stop / Ask Conditions

- <condition>

## Open Risks

| Risk | Impact | Mitigation / owner |
|---|---|---|
| <risk> | <impact> | <mitigation> |
