# Plan: System-first Harness orchestration

This plan implements a parent-only system review stage, a real no-subagent path for managed work, optional Codex nested helpers, and an explicit serialized multi-host review contract without changing PLAN v5 or RUN v10 schemas.

## Harness Plan Manifest

```json
{
  "harness_plan": {
    "schema_version": 5,
    "plan_id": "PLAN-SYSTEM-FIRST-HARNESS",
    "revision": 2,
    "objective": "Make Harness orchestration system-first, preserve exact-head review, and keep delegated workers optional while retaining current schema compatibility.",
    "max_parallel_workers": 8,
    "required_reviews": ["backend_code"],
    "sources": [
      {
        "id": "SRC-001",
        "kind": "user instruction",
        "location": "conversation://2026-08-02/system-first-harness",
        "owner": "user",
        "status": "frozen",
        "content_sha256": null,
        "source_revision": "user-approved-system-first-multi-worker-implementation",
        "staged_revision": null,
        "notes": "Implement the agreed system-first design and use Multi Workers."
      },
      {
        "id": "SRC-002",
        "kind": "repository policy",
        "location": "AGENTS.md",
        "owner": "repository",
        "status": "frozen",
        "content_sha256": null,
        "source_revision": "42e0f0682916d14b98e7732fa3fb85cbfd367ec1",
        "staged_revision": null,
        "notes": "Canonical safety, Git flow, source-edit, sync, and verification requirements."
      }
    ],
    "traces": [
      {
        "id": "REQ-001",
        "source_ids": ["SRC-001"],
        "priority": "must",
        "requirement": "Run one parent-only read-only System Review And Route stage before managed artifacts, adapters, task-specific skills, models, or worker launches.",
        "disposition": "planned",
        "rationale": null
      },
      {
        "id": "REQ-002",
        "source_ids": ["SRC-001"],
        "priority": "must",
        "requirement": "Allow large plan-backed work to execute one mission at a time as sequential_parent in a parent-managed worktree without spawn_subagents.",
        "disposition": "planned",
        "rationale": null
      },
      {
        "id": "REQ-003",
        "source_ids": ["SRC-001"],
        "priority": "must",
        "requirement": "Make Codex nested helpers optional while keeping singleton exact-head graph review mandatory before integration.",
        "disposition": "planned",
        "rationale": null
      },
      {
        "id": "REQ-004",
        "source_ids": ["SRC-001"],
        "priority": "must",
        "requirement": "Document a serialized same-repository Codex/Claude review handoff and keep Claude workflow invocations homogeneous by tool profile.",
        "disposition": "planned",
        "rationale": null
      },
      {
        "id": "REQ-005",
        "source_ids": ["SRC-002"],
        "priority": "must",
        "requirement": "Edit canonical skills only, regenerate packaged copies, and pass the repository-required verification suite.",
        "disposition": "planned",
        "rationale": null
      }
    ],
    "ui_surfaces": [],
    "risks": [
      {
        "id": "RISK-001",
        "description": "A permissive sequential-parent mapping could dispatch more than one parent writer.",
        "impact": "high",
        "mitigation": "Cap sequential_parent runtime and write budgets at one and test a high-capacity two-root frontier.",
        "stop_condition": "Stop if more than one run_parent write mission becomes dispatchable."
      },
      {
        "id": "RISK-002",
        "description": "Making nested helpers optional could weaken pre-integration review.",
        "impact": "high",
        "mitigation": "Preserve RUN-v10 singleton review-node and exact-SHA integration gates and add focused tests.",
        "stop_condition": "Stop if an absent nested policy can integrate without a terminal exact-head graph review PASS."
      }
    ],
    "batch_verifiers": [
      {
        "id": "batch",
        "cwd": ".",
        "argv": ["python3", "scripts/sync_plugin_skills.py", "--check"],
        "pass_signal": "exit 0"
      }
    ],
    "final_gates": [
      {
        "id": "final",
        "cwd": ".",
        "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-v"],
        "pass_signal": "exit 0"
      }
    ],
    "graph": {
      "entry_nodes": ["N-M1", "N-M2", "N-M3"],
      "nodes": [
        {
          "id": "N-M1",
          "kind": "mission",
          "ref": "M1",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "codex",
            "allowed_providers": ["codex"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-terra", "reasoning_effort": "high"}
            }
          }
        },
        {
          "id": "N-REVIEW-M1",
          "kind": "verifier",
          "ref": "batch",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "fix_required", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "codex",
            "allowed_providers": ["codex"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-terra", "reasoning_effort": "medium"}
            }
          },
          "review": {
            "type": "backend_code",
            "mission_ids": ["M1"],
            "scope": [
              ".agents/skills/fullstack-harness-engineering/SKILL.md",
              ".agents/skills/fullstack-harness-engineering/agents/openai.yaml",
              ".agents/skills/fullstack-harness-engineering/references/execution-state-model.md",
              ".agents/skills/fullstack-harness-engineering/references/graph-orchestration.md",
              ".agents/skills/fullstack-harness-engineering/references/parallel-mission-selection.md",
              ".agents/skills/fullstack-harness-engineering/references/worktree-thread-orchestration.md",
              ".agents/skills/fullstack-harness-engineering/assets/templates/GOAL.template.md",
              ".agents/skills/fullstack-harness-engineering/assets/templates/MISSION_RUNBOOK.template.md",
              ".agents/skills/fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_skill_contract.py"
            ],
            "required_evidence": ["reviewed_sha", "path-and-line findings", "pass or fix_required decision"]
          }
        },
        {
          "id": "N-REVIEW-PASS-M1",
          "kind": "verifier",
          "ref": "batch",
          "executor": "local_command",
          "allowed_outcomes": ["pass", "blocked"],
          "max_attempts": 2,
          "runtime": null
        },
        {
          "id": "N-M2",
          "kind": "mission",
          "ref": "M2",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "codex",
            "allowed_providers": ["codex"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-terra", "reasoning_effort": "high"}
            }
          }
        },
        {
          "id": "N-REVIEW-M2",
          "kind": "verifier",
          "ref": "batch",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "fix_required", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "codex",
            "allowed_providers": ["codex"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-terra", "reasoning_effort": "medium"}
            }
          },
          "review": {
            "type": "backend_code",
            "mission_ids": ["M2"],
            "scope": [
              ".agents/skills/fullstack-harness-engineering/scripts/harness_manifest.py",
              ".agents/skills/fullstack-harness-engineering/scripts/select_ready_nodes.py",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_harness_manifest.py",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_select_ready_nodes.py"
            ],
            "required_evidence": ["reviewed_sha", "path-and-line findings", "pass or fix_required decision"]
          }
        },
        {
          "id": "N-REVIEW-PASS-M2",
          "kind": "verifier",
          "ref": "batch",
          "executor": "local_command",
          "allowed_outcomes": ["pass", "blocked"],
          "max_attempts": 2,
          "runtime": null
        },
        {
          "id": "N-M3",
          "kind": "mission",
          "ref": "M3",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "codex",
            "allowed_providers": ["codex"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-terra", "reasoning_effort": "high"}
            }
          }
        },
        {
          "id": "N-REVIEW-M3",
          "kind": "verifier",
          "ref": "batch",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "fix_required", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": "codex",
            "allowed_providers": ["codex"],
            "provider_options": {
              "codex": {"model": "gpt-5.6-terra", "reasoning_effort": "medium"}
            }
          },
          "review": {
            "type": "backend_code",
            "mission_ids": ["M3"],
            "scope": [
              ".agents/skills/fullstack-harness-codex/SKILL.md",
              ".agents/skills/fullstack-harness-codex/agents/openai.yaml",
              ".agents/skills/fullstack-harness-claude-code/SKILL.md",
              ".agents/skills/fullstack-harness-claude-code/agents/openai.yaml",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_adapter_contract.py",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_readme_structure.py",
              "README.md",
              "README.zh-CN.md",
              "README.zh-TW.md"
            ],
            "required_evidence": ["reviewed_sha", "path-and-line findings", "pass or fix_required decision"]
          }
        },
        {
          "id": "N-REVIEW-PASS-M3",
          "kind": "verifier",
          "ref": "batch",
          "executor": "local_command",
          "allowed_outcomes": ["pass", "blocked"],
          "max_attempts": 2,
          "runtime": null
        },
        {
          "id": "N-FINAL",
          "kind": "verifier",
          "ref": "final",
          "executor": "local_command",
          "allowed_outcomes": ["pass", "blocked"],
          "max_attempts": 2,
          "runtime": null
        }
      ],
      "edges": [
        {"id": "E-M1-REVIEW", "kind": "dependency", "from": "N-M1", "to": "N-REVIEW-M1", "on_outcomes": ["pass"], "max_traversals": null},
        {"id": "E-M1-REVIEW-PASS", "kind": "route", "from": "N-REVIEW-M1", "to": "N-REVIEW-PASS-M1", "on_outcomes": ["pass"], "max_traversals": null},
        {"id": "E-M1-FINAL", "kind": "dependency", "from": "N-REVIEW-PASS-M1", "to": "N-FINAL", "on_outcomes": ["pass"], "max_traversals": null},
        {"id": "E-M2-REVIEW", "kind": "dependency", "from": "N-M2", "to": "N-REVIEW-M2", "on_outcomes": ["pass"], "max_traversals": null},
        {"id": "E-M2-REVIEW-PASS", "kind": "route", "from": "N-REVIEW-M2", "to": "N-REVIEW-PASS-M2", "on_outcomes": ["pass"], "max_traversals": null},
        {"id": "E-M2-FINAL", "kind": "dependency", "from": "N-REVIEW-PASS-M2", "to": "N-FINAL", "on_outcomes": ["pass"], "max_traversals": null},
        {"id": "E-M3-REVIEW", "kind": "dependency", "from": "N-M3", "to": "N-REVIEW-M3", "on_outcomes": ["pass"], "max_traversals": null},
        {"id": "E-M3-REVIEW-PASS", "kind": "route", "from": "N-REVIEW-M3", "to": "N-REVIEW-PASS-M3", "on_outcomes": ["pass"], "max_traversals": null},
        {"id": "E-M3-FINAL", "kind": "dependency", "from": "N-REVIEW-PASS-M3", "to": "N-FINAL", "on_outcomes": ["pass"], "max_traversals": null}
      ]
    },
    "missions": [
      {
        "id": "M1",
        "alias": "core-contract",
        "objective": "Define the system-first orchestration contract and align shared references, templates, and contract tests.",
        "priority": 100,
        "merge_rank": 10,
        "trace_ids": ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005"],
        "write_scope": [
          ".agents/skills/fullstack-harness-engineering/SKILL.md",
          ".agents/skills/fullstack-harness-engineering/agents/openai.yaml",
          ".agents/skills/fullstack-harness-engineering/references/execution-state-model.md",
          ".agents/skills/fullstack-harness-engineering/references/graph-orchestration.md",
          ".agents/skills/fullstack-harness-engineering/references/parallel-mission-selection.md",
          ".agents/skills/fullstack-harness-engineering/references/worktree-thread-orchestration.md",
          ".agents/skills/fullstack-harness-engineering/assets/templates/GOAL.template.md",
          ".agents/skills/fullstack-harness-engineering/assets/templates/MISSION_RUNBOOK.template.md",
          ".agents/skills/fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md",
          ".agents/skills/fullstack-harness-engineering/scripts/tests/test_skill_contract.py"
        ],
        "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md", "docs/goal/tasks.md"],
        "resource_inventory_complete": true,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": true,
        "required_skills": [],
        "stop_conditions": ["Stop if the parent-only stage becomes a graph node or if legacy manifest validation is removed."],
        "worker_verifiers": [
          {"id": "m1-contract", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_skill_contract.py", "-v"], "pass_signal": "exit 0"}
        ],
        "integration_verifiers": [
          {"id": "m1-integration", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_skill_contract.py", "-v"], "pass_signal": "exit 0"}
        ],
        "tasks": [
          {
            "id": "M1/T01",
            "alias": "system-first-stage",
            "objective": "Make System Review And Route parent-only and remove new compact RUN-only authoring.",
            "acceptance_matrix": [
              {"test_id": "TEST-M1-001", "trace_ids": ["REQ-001", "REQ-005"], "criterion": "The core and tests require a parent-only pre-artifact stage and all new managed work uses PLAN plus RUN."}
            ],
            "trace_ids": ["REQ-001", "REQ-005"],
            "depends_on": [],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": [
              ".agents/skills/fullstack-harness-engineering/SKILL.md",
              ".agents/skills/fullstack-harness-engineering/agents/openai.yaml",
              ".agents/skills/fullstack-harness-engineering/references/execution-state-model.md",
              ".agents/skills/fullstack-harness-engineering/assets/templates/MISSION_RUNBOOK.template.md",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_skill_contract.py"
            ],
            "verifiers": [
              {"id": "m1-t1-contract", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_skill_contract.py", "-v"], "pass_signal": "exit 0"}
            ]
          },
          {
            "id": "M1/T02",
            "alias": "shared-orchestration-contract",
            "objective": "Document isolated sequential parent execution, optional nested helpers, serialized host handoff, and homogeneous Claude profile groups.",
            "acceptance_matrix": [
              {"test_id": "TEST-M1-002", "trace_ids": ["REQ-002", "REQ-003", "REQ-004", "REQ-005"], "criterion": "Shared contracts describe all four behaviors without a schema change and the focused contract suite passes."}
            ],
            "trace_ids": ["REQ-002", "REQ-003", "REQ-004", "REQ-005"],
            "depends_on": ["M1/T01"],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": [
              ".agents/skills/fullstack-harness-engineering/SKILL.md",
              ".agents/skills/fullstack-harness-engineering/references/execution-state-model.md",
              ".agents/skills/fullstack-harness-engineering/references/graph-orchestration.md",
              ".agents/skills/fullstack-harness-engineering/references/parallel-mission-selection.md",
              ".agents/skills/fullstack-harness-engineering/references/worktree-thread-orchestration.md",
              ".agents/skills/fullstack-harness-engineering/assets/templates/GOAL.template.md",
              ".agents/skills/fullstack-harness-engineering/assets/templates/MISSION_RUNBOOK.template.md",
              ".agents/skills/fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_skill_contract.py"
            ],
            "verifiers": [
              {"id": "m1-t2-contract", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_skill_contract.py", "-v"], "pass_signal": "exit 0"}
            ]
          }
        ]
      },
      {
        "id": "M2",
        "alias": "runtime-selection",
        "objective": "Implement and test isolated sequential_parent execution and optional Codex nested helpers.",
        "priority": 95,
        "merge_rank": 20,
        "trace_ids": ["REQ-002", "REQ-003", "REQ-005"],
        "write_scope": [
          ".agents/skills/fullstack-harness-engineering/scripts/harness_manifest.py",
          ".agents/skills/fullstack-harness-engineering/scripts/select_ready_nodes.py",
          ".agents/skills/fullstack-harness-engineering/scripts/tests/test_harness_manifest.py",
          ".agents/skills/fullstack-harness-engineering/scripts/tests/test_select_ready_nodes.py"
        ],
        "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md", "docs/goal/tasks.md"],
        "resource_inventory_complete": true,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": true,
        "required_skills": [],
        "stop_conditions": ["Stop if sequential_parent can dispatch multiple write missions or if exact-head graph review can be bypassed."],
        "worker_verifiers": [
          {"id": "m2-manifest", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_harness_manifest.py", "-v"], "pass_signal": "exit 0"},
          {"id": "m2-selector", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_select_ready_nodes.py", "-v"], "pass_signal": "exit 0"}
        ],
        "integration_verifiers": [
          {"id": "m2-integration", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_harness_manifest.py", "-v"], "pass_signal": "exit 0"}
        ],
        "tasks": [
          {
            "id": "M2/T01",
            "alias": "sequential-parent-worktree",
            "objective": "Accept parent-managed worktrees for sequential_parent and serialize its runtime budget at one.",
            "acceptance_matrix": [
              {"test_id": "TEST-M2-001", "trace_ids": ["REQ-002", "REQ-005"], "criterion": "A high-capacity frontier dispatches exactly one run_parent mission with local worktree, branch, and commit actions and no spawn action."}
            ],
            "trace_ids": ["REQ-002", "REQ-005"],
            "depends_on": [],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": [
              ".agents/skills/fullstack-harness-engineering/scripts/harness_manifest.py",
              ".agents/skills/fullstack-harness-engineering/scripts/select_ready_nodes.py",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_harness_manifest.py",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_select_ready_nodes.py"
            ],
            "verifiers": [
              {"id": "m2-t1-selector", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_select_ready_nodes.py", "-v"], "pass_signal": "exit 0"}
            ]
          },
          {
            "id": "M2/T02",
            "alias": "optional-nested-policy",
            "objective": "Stop inferring spawn_subagents from observed nested capability and allow absent app-task nested policies.",
            "acceptance_matrix": [
              {"test_id": "TEST-M2-002", "trace_ids": ["REQ-003", "REQ-005"], "criterion": "An app-thread mission launches without spawn_subagents when helpers are absent, while integration still requires exact-head graph review."}
            ],
            "trace_ids": ["REQ-003", "REQ-005"],
            "depends_on": ["M2/T01"],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": [
              ".agents/skills/fullstack-harness-engineering/scripts/harness_manifest.py",
              ".agents/skills/fullstack-harness-engineering/scripts/select_ready_nodes.py",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_harness_manifest.py",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_select_ready_nodes.py"
            ],
            "verifiers": [
              {"id": "m2-t2-manifest", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_harness_manifest.py", "-v"], "pass_signal": "exit 0"}
            ]
          }
        ]
      },
      {
        "id": "M3",
        "alias": "adapter-readme-alignment",
        "objective": "Align both adapters, default prompts, and all README languages with the system-first, optional-helper, serialized-handoff contract.",
        "priority": 90,
        "merge_rank": 30,
        "trace_ids": ["REQ-001", "REQ-003", "REQ-004", "REQ-005"],
        "write_scope": [
          ".agents/skills/fullstack-harness-codex/SKILL.md",
          ".agents/skills/fullstack-harness-codex/agents/openai.yaml",
          ".agents/skills/fullstack-harness-claude-code/SKILL.md",
          ".agents/skills/fullstack-harness-claude-code/agents/openai.yaml",
          ".agents/skills/fullstack-harness-engineering/scripts/tests/test_adapter_contract.py",
          ".agents/skills/fullstack-harness-engineering/scripts/tests/test_readme_structure.py",
          "README.md",
          "README.zh-CN.md",
          "README.zh-TW.md"
        ],
        "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md", "docs/goal/tasks.md"],
        "resource_inventory_complete": true,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": true,
        "required_skills": [],
        "stop_conditions": ["Stop if documentation claims an in-session cross-host bridge or permission-level tool removal."],
        "worker_verifiers": [
          {"id": "m3-adapters", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_adapter_contract.py", "-v"], "pass_signal": "exit 0"},
          {"id": "m3-readme", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_readme_structure.py", "-v"], "pass_signal": "exit 0"}
        ],
        "integration_verifiers": [
          {"id": "m3-integration", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_adapter_contract.py", "-v"], "pass_signal": "exit 0"}
        ],
        "tasks": [
          {
            "id": "M3/T01",
            "alias": "adapter-contracts",
            "objective": "Align Codex and Claude adapters and prompts with system-first routing, optional helpers, serialized host switching, and homogeneous Claude profile groups.",
            "acceptance_matrix": [
              {"test_id": "TEST-M3-001", "trace_ids": ["REQ-001", "REQ-003", "REQ-004", "REQ-005"], "criterion": "Adapter contract tests pass and no adapter claims automatic cross-host invocation or mixed-profile Claude calls."}
            ],
            "trace_ids": ["REQ-001", "REQ-003", "REQ-004", "REQ-005"],
            "depends_on": [],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": [
              ".agents/skills/fullstack-harness-codex/SKILL.md",
              ".agents/skills/fullstack-harness-codex/agents/openai.yaml",
              ".agents/skills/fullstack-harness-claude-code/SKILL.md",
              ".agents/skills/fullstack-harness-claude-code/agents/openai.yaml",
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_adapter_contract.py"
            ],
            "verifiers": [
              {"id": "m3-t1-adapter", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_adapter_contract.py", "-v"], "pass_signal": "exit 0"}
            ]
          },
          {
            "id": "M3/T02",
            "alias": "readme-alignment",
            "objective": "Align English, simplified Chinese, and traditional Chinese README structure and runtime claims.",
            "acceptance_matrix": [
              {"test_id": "TEST-M3-002", "trace_ids": ["REQ-001", "REQ-003", "REQ-004", "REQ-005"], "criterion": "All README languages describe the same system-first and runtime behavior and structure tests pass."}
            ],
            "trace_ids": ["REQ-001", "REQ-003", "REQ-004", "REQ-005"],
            "depends_on": ["M3/T01"],
            "parent_task": null,
            "legacy_task_ids": [],
            "replaced_by": [],
            "split_reason": null,
            "refinement_generation": 0,
            "write_scope": [
              ".agents/skills/fullstack-harness-engineering/scripts/tests/test_readme_structure.py",
              "README.md",
              "README.zh-CN.md",
              "README.zh-TW.md"
            ],
            "verifiers": [
              {"id": "m3-t2-readme", "cwd": ".", "argv": ["python3", "-m", "unittest", "discover", "-s", ".agents/skills/fullstack-harness-engineering/scripts/tests", "-p", "test_readme_structure.py", "-v"], "pass_signal": "exit 0"}
            ]
          }
        ]
      }
    ]
  }
}
```

## Plan Readiness Gate

| Readiness check | Status | Evidence / decision |
|---|---|---|
| Scope and ownership are non-overlapping | PASS | Three exact mission scopes; generated plugin copies remain parent-owned until sync. |
| Every trace maps to tasks and verifiers | PASS | REQ-001 through REQ-005 are covered in mission acceptance rows. |
| Graph and task dependencies are acyclic | PASS | Three independent mission roots; task dependencies are mission-local. |
| Runtime and isolation are executable | PASS | Codex direct workers will receive separate parent-managed worktrees. |
| UI evidence | n/a | Documentation and Python orchestration only. |
| Required authorization | PASS | User explicitly requested implementation and Multi Workers in this conversation. |

## Delivery Strategy

- Parent owns PLAN/RUN/tasks, branch/worktree allocation, integration, packaged-skill sync, full verification, and push.
- M1 owns shared core policy, references, templates, and contract tests.
- M2 owns runtime validation/selection implementation and focused tests.
- M3 owns runtime adapters, prompts, README translations, and adapter/README tests.
- Workers must not edit `plugins/fullstack-harness/skills/**`; the parent regenerates those copies after integration.

## Stop Conditions

- Stop if any Worker touches another mission's scope or the existing dirty `codex/simplify-skill-context` worktree.
- Stop if the implementation weakens exact-head review, changes PLAN/RUN schemas, or claims automatic cross-host execution.
- Stop if required canonical or packaged verification fails after two repair attempts.
