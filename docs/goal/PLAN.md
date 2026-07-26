# Plan: Frontend design wireframe flow

This plan adds one stable visual-direction step between product wireframes and the frozen UI architecture package. The product wireframe remains the source of structure and scope.

## Harness Plan Manifest

```json
{
  "harness_plan": {
    "schema_version": 5,
    "plan_id": "PLAN-FRONTEND-DESIGN-WIREFRAME",
    "revision": 1,
    "objective": "Define and verify one cross-skill flow where structural wireframes stay canonical, frontend-design produces a bounded visual direction, UI architecture freezes the selected direction, and implementation missions conform to the frozen package.",
    "max_parallel_workers": 3,
    "required_reviews": [
      "frontend_code"
    ],
    "sources": [
      {
        "id": "SRC-USER-DIRECTION",
        "kind": "user_instruction",
        "location": "conversation:frontend-design-wireframe-flow",
        "owner": "user",
        "status": "frozen",
        "content_sha256": null,
        "source_revision": "2026-07-25:user-approved-multi-agent-implementation",
        "staged_revision": null,
        "notes": "Use frontend-design to improve visual direction without replacing structural wireframes, and implement the change with multiple agents."
      }
    ],
    "traces": [
      {
        "id": "REQ-PRD-HANDOFF",
        "source_ids": [
          "SRC-USER-DIRECTION"
        ],
        "priority": "must",
        "requirement": "PRD guidance must keep low-fidelity wireframes canonical while defining an optional visual-direction handoff.",
        "disposition": "planned",
        "rationale": null
      },
      {
        "id": "REQ-DESIGN-FREEZE",
        "source_ids": [
          "SRC-USER-DIRECTION"
        ],
        "priority": "must",
        "requirement": "UI architecture guidance must use frontend-design as a bounded candidate pass before freezing tokens, primitives, recipes, and mockups.",
        "disposition": "planned",
        "rationale": null
      },
      {
        "id": "REQ-HARNESS-CONFORMANCE",
        "source_ids": [
          "SRC-USER-DIRECTION"
        ],
        "priority": "must",
        "requirement": "Harness implementation guidance must consume the frozen UI package and use frontend-design only in explicit conformance mode for eligible visual missions.",
        "disposition": "planned",
        "rationale": null
      }
    ],
    "ui_surfaces": [],
    "risks": [
      {
        "id": "RISK-DESIGN-DRIFT",
        "description": "Calling frontend-design independently for each page can create incompatible visual directions and bypass the frozen design package.",
        "impact": "high",
        "mitigation": "Run one bounded representative-screen pass, select one direction, and normalize it through UI architecture before implementation.",
        "stop_condition": "Stop if a proposed change lets a worker alter product scope, canonical wireframes, or frozen UI registry files from an implementation mission."
      }
    ],
    "batch_verifiers": [
      {
        "id": "batch-cross-skill-contract",
        "cwd": ".",
        "argv": [
          "python",
          "-m",
          "unittest",
          ".agents.skills.fullstack-harness-engineering.scripts.tests.test_cross_skill_pipeline",
          "-v"
        ],
        "pass_signal": "exit 0"
      }
    ],
    "final_gates": [
      {
        "id": "final-harness-suite",
        "cwd": ".",
        "argv": [
          "python",
          "-m",
          "unittest",
          "discover",
          "-s",
          ".agents/skills/fullstack-harness-engineering/scripts/tests",
          "-v"
        ],
        "pass_signal": "exit 0"
      }
    ],
    "graph": {
      "entry_nodes": [
        "N-M1",
        "N-M2",
        "N-M3"
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
            "preferred_provider": "codex",
            "allowed_providers": [
              "codex"
            ],
            "provider_options": {
              "codex": {
                "model": null,
                "reasoning_effort": null
              }
            }
          }
        },
        {
          "id": "N-M2",
          "kind": "mission",
          "ref": "M2",
          "executor": "runtime_worker",
          "allowed_outcomes": [
            "pass",
            "retryable_failure",
            "blocked",
            "contract_gap"
          ],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "codex",
            "allowed_providers": [
              "codex"
            ],
            "provider_options": {
              "codex": {
                "model": null,
                "reasoning_effort": null
              }
            }
          }
        },
        {
          "id": "N-M3",
          "kind": "mission",
          "ref": "M3",
          "executor": "runtime_worker",
          "allowed_outcomes": [
            "pass",
            "retryable_failure",
            "blocked",
            "contract_gap"
          ],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "codex",
            "allowed_providers": [
              "codex"
            ],
            "provider_options": {
              "codex": {
                "model": null,
                "reasoning_effort": null
              }
            }
          }
        },
        {
          "id": "N-CONTRACT-REVIEW",
          "kind": "verifier",
          "ref": "batch-cross-skill-contract",
          "executor": "runtime_worker",
          "allowed_outcomes": [
            "pass",
            "retryable_failure",
            "blocked",
            "contract_gap"
          ],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "codex",
            "allowed_providers": [
              "codex"
            ],
            "provider_options": {
              "codex": {
                "model": null,
                "reasoning_effort": null
              }
            }
          },
          "review": {
            "type": "frontend_code",
            "mission_ids": [
              "M1",
              "M2",
              "M3"
            ],
            "scope": [
              ".agents/skills/prd-builder/**",
              ".agents/skills/ui-architecture-builder/**",
              ".agents/skills/fullstack-harness-engineering/**",
              ".agents/skills/fullstack-harness-codex/**"
            ],
            "required_evidence": [
              "reviewed_sha",
              "path-and-line findings",
              "pass or blocked decision"
            ]
          }
        },
        {
          "id": "N-FINAL-GATE",
          "kind": "verifier",
          "ref": "final-harness-suite",
          "executor": "local_command",
          "allowed_outcomes": [
            "pass",
            "retryable_failure",
            "blocked",
            "contract_gap"
          ],
          "max_attempts": 2,
          "runtime": null
        }
      ],
      "edges": [
        {
          "id": "E-M1-REVIEW",
          "kind": "dependency",
          "from": "N-M1",
          "to": "N-CONTRACT-REVIEW",
          "on_outcomes": [
            "pass"
          ],
          "max_traversals": null
        },
        {
          "id": "E-M2-REVIEW",
          "kind": "dependency",
          "from": "N-M2",
          "to": "N-CONTRACT-REVIEW",
          "on_outcomes": [
            "pass"
          ],
          "max_traversals": null
        },
        {
          "id": "E-M3-REVIEW",
          "kind": "dependency",
          "from": "N-M3",
          "to": "N-CONTRACT-REVIEW",
          "on_outcomes": [
            "pass"
          ],
          "max_traversals": null
        },
        {
          "id": "E-REVIEW-FINAL",
          "kind": "route",
          "from": "N-CONTRACT-REVIEW",
          "to": "N-FINAL-GATE",
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
        "alias": "prd-visual-handoff",
        "objective": "Define the optional frontend-design handoff while keeping PRD wireframes structural and canonical.",
        "priority": 100,
        "merge_rank": 10,
        "trace_ids": [
          "REQ-PRD-HANDOFF"
        ],
        "write_scope": [
          ".agents/skills/prd-builder/**"
        ],
        "deny_scope": [
          "docs/goal/PLAN.md",
          "docs/goal/RUN.md",
          "plugins/**"
        ],
        "resource_inventory_complete": true,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": true,
        "required_skills": [
          "prd-builder",
          "frontend-design"
        ],
        "stop_conditions": [
          "Stop if the change makes a visual prototype part of the canonical PRD package or lets it change product scope."
        ],
        "worker_verifiers": [
          {
            "id": "m1-cross-skill-focused",
            "cwd": ".",
            "argv": [
              "python",
              "-m",
              "unittest",
              ".agents.skills.fullstack-harness-engineering.scripts.tests.test_cross_skill_pipeline",
              "-v"
            ],
            "pass_signal": "exit 0",
            "selection": {
              "mode": "changed_files",
              "scopes": [
                ".agents/skills/prd-builder/**"
              ]
            },
            "cache": {
              "mode": "session_exact",
              "environment_keys": []
            }
          }
        ],
        "integration_verifiers": [
          {
            "id": "m1-integration-contract",
            "cwd": ".",
            "argv": [
              "python",
              "-m",
              "unittest",
              ".agents.skills.fullstack-harness-engineering.scripts.tests.test_cross_skill_pipeline",
              "-v"
            ],
            "pass_signal": "exit 0"
          }
        ],
        "tasks": [
          {
            "id": "M1/T01",
            "alias": "document-prd-handoff",
            "objective": "Update PRD workflow and output guidance with a bounded visual-direction handoff.",
            "acceptance_matrix": [
              {
                "test_id": "TEST-M1-T01-001",
                "trace_ids": [
                  "REQ-PRD-HANDOFF"
                ],
                "criterion": "PRD guidance states that low-fidelity wireframes remain canonical and frontend-design output is an optional non-canonical downstream input."
              }
            ],
            "trace_ids": [
              "REQ-PRD-HANDOFF"
            ],
            "depends_on": [],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": [
              ".agents/skills/prd-builder/**"
            ],
            "verifiers": [
              {
                "id": "m1-task-contract",
                "cwd": ".",
                "argv": [
                  "python",
                  "-m",
                  "unittest",
                  ".agents.skills.fullstack-harness-engineering.scripts.tests.test_cross_skill_pipeline",
                  "-v"
                ],
                "pass_signal": "exit 0",
                "selection": {
                  "mode": "changed_files",
                  "scopes": [
                    ".agents/skills/prd-builder/**"
                  ]
                },
                "cache": {
                  "mode": "session_exact",
                  "environment_keys": []
                }
              }
            ]
          }
        ]
      },
      {
        "id": "M2",
        "alias": "ui-visual-direction",
        "objective": "Define one bounded frontend-design candidate pass and the normalization step that freezes the UI architecture package.",
        "priority": 100,
        "merge_rank": 20,
        "trace_ids": [
          "REQ-DESIGN-FREEZE"
        ],
        "write_scope": [
          ".agents/skills/ui-architecture-builder/**"
        ],
        "deny_scope": [
          "docs/goal/PLAN.md",
          "docs/goal/RUN.md",
          "plugins/**"
        ],
        "resource_inventory_complete": true,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": true,
        "required_skills": [
          "ui-architecture-builder",
          "frontend-design"
        ],
        "stop_conditions": [
          "Stop if frontend-design is called independently per route or its candidate output becomes canonical without normalization."
        ],
        "worker_verifiers": [
          {
            "id": "m2-cross-skill-focused",
            "cwd": ".",
            "argv": [
              "python",
              "-m",
              "unittest",
              ".agents.skills.fullstack-harness-engineering.scripts.tests.test_cross_skill_pipeline",
              "-v"
            ],
            "pass_signal": "exit 0",
            "selection": {
              "mode": "changed_files",
              "scopes": [
                ".agents/skills/ui-architecture-builder/**"
              ]
            },
            "cache": {
              "mode": "session_exact",
              "environment_keys": []
            }
          }
        ],
        "integration_verifiers": [
          {
            "id": "m2-integration-contract",
            "cwd": ".",
            "argv": [
              "python",
              "-m",
              "unittest",
              ".agents.skills.fullstack-harness-engineering.scripts.tests.test_cross_skill_pipeline",
              "-v"
            ],
            "pass_signal": "exit 0"
          }
        ],
        "tasks": [
          {
            "id": "M2/T01",
            "alias": "document-design-pass",
            "objective": "Update UI architecture workflow and package guidance for the visual-direction candidate lifecycle.",
            "acceptance_matrix": [
              {
                "test_id": "TEST-M2-T01-001",
                "trace_ids": [
                  "REQ-DESIGN-FREEZE"
                ],
                "criterion": "UI architecture guidance runs frontend-design once on representative screens, treats candidates as non-canonical, and freezes the selected direction into normal package artifacts."
              }
            ],
            "trace_ids": [
              "REQ-DESIGN-FREEZE"
            ],
            "depends_on": [],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": [
              ".agents/skills/ui-architecture-builder/**"
            ],
            "verifiers": [
              {
                "id": "m2-task-contract",
                "cwd": ".",
                "argv": [
                  "python",
                  "-m",
                  "unittest",
                  ".agents.skills.fullstack-harness-engineering.scripts.tests.test_cross_skill_pipeline",
                  "-v"
                ],
                "pass_signal": "exit 0",
                "selection": {
                  "mode": "changed_files",
                  "scopes": [
                    ".agents/skills/ui-architecture-builder/**"
                  ]
                },
                "cache": {
                  "mode": "session_exact",
                  "environment_keys": []
                }
              }
            ]
          }
        ]
      },
      {
        "id": "M3",
        "alias": "harness-ui-conformance",
        "objective": "Define how implementation missions consume the frozen UI package and constrain optional frontend-design use.",
        "priority": 100,
        "merge_rank": 30,
        "trace_ids": [
          "REQ-HARNESS-CONFORMANCE"
        ],
        "write_scope": [
          ".agents/skills/fullstack-harness-engineering/**",
          ".agents/skills/fullstack-harness-codex/**"
        ],
        "deny_scope": [
          "docs/goal/PLAN.md",
          "docs/goal/RUN.md",
          "plugins/**"
        ],
        "resource_inventory_complete": true,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": true,
        "required_skills": [
          "fullstack-harness-engineering",
          "fullstack-harness-codex",
          "frontend-design"
        ],
        "stop_conditions": [
          "Stop if an implementation worker can invent a new design direction, token, primitive, or component outside the frozen UI package."
        ],
        "worker_verifiers": [
          {
            "id": "m3-harness-focused",
            "cwd": ".",
            "argv": [
              "python",
              "-m",
              "unittest",
              ".agents.skills.fullstack-harness-engineering.scripts.tests.test_cross_skill_pipeline",
              "-v"
            ],
            "pass_signal": "exit 0",
            "selection": {
              "mode": "changed_files",
              "scopes": [
                ".agents/skills/fullstack-harness-engineering/**",
                ".agents/skills/fullstack-harness-codex/**"
              ]
            },
            "cache": {
              "mode": "session_exact",
              "environment_keys": []
            }
          }
        ],
        "integration_verifiers": [
          {
            "id": "m3-integration-contract",
            "cwd": ".",
            "argv": [
              "python",
              "-m",
              "unittest",
              ".agents.skills.fullstack-harness-engineering.scripts.tests.test_cross_skill_pipeline",
              "-v"
            ],
            "pass_signal": "exit 0"
          }
        ],
        "tasks": [
          {
            "id": "M3/T01",
            "alias": "document-conformance-mode",
            "objective": "Update Harness contracts and cross-skill tests for frozen-package conformance.",
            "acceptance_matrix": [
              {
                "test_id": "TEST-M3-T01-001",
                "trace_ids": [
                  "REQ-HARNESS-CONFORMANCE"
                ],
                "criterion": "Harness guidance limits frontend-design to explicit eligible missions and forbids implementation-time design-system drift."
              }
            ],
            "trace_ids": [
              "REQ-HARNESS-CONFORMANCE"
            ],
            "depends_on": [],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": [
              ".agents/skills/fullstack-harness-engineering/**",
              ".agents/skills/fullstack-harness-codex/**"
            ],
            "verifiers": [
              {
                "id": "m3-task-contract",
                "cwd": ".",
                "argv": [
                  "python",
                  "-m",
                  "unittest",
                  ".agents.skills.fullstack-harness-engineering.scripts.tests.test_cross_skill_pipeline",
                  "-v"
                ],
                "pass_signal": "exit 0",
                "selection": {
                  "mode": "changed_files",
                  "scopes": [
                    ".agents/skills/fullstack-harness-engineering/**",
                    ".agents/skills/fullstack-harness-codex/**"
                  ]
                },
                "cache": {
                  "mode": "session_exact",
                  "environment_keys": []
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

## Execution Boundary

- Local implementation, isolated worker branches/worktrees, local commits, and local integration are authorized by the user's instruction to implement this with multiple agents.
- Push, pull request, merge, deployment, cleanup, worktree removal, and branch deletion are not authorized.
- Plugin mirror updates are parent-owned mechanical synchronization after canonical skill changes integrate.
