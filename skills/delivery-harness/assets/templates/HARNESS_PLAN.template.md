# Plan: <feature or product slice>

Use this template as `docs/goal/PLAN.md` for managed work that needs durable coordination, even when the selected execution route is sequential. Direct small work creates no PLAN/RUN artifacts. This example intentionally shows one neutral mission, one isolated writer, one exact-head pre-integration review, one fresh unified security review, and local final gates; it is not a UI repair graph or a promise of parallel fan-out. UI Design Intake remains an upstream contract when a product has UI; this neutral example has no UI surface. A web visual review adds `"required_tools": ["chrome_devtools"]` inside its `review` object; a frontend-code review adds it only when live browser state is part of the required evidence.

For new consolidated UI acceptance, add `ui_acceptance` to the `visual` node's existing `required_evidence` list.
Use the same marker on earlier visual reviews only when they cover parity and page quality for their complete declared scope.
Keep comparison and quality-report anchors in that review attempt's evidence, as required by `references/verification-gates.md`.
This neutral headless example remains unmarked. Do not rewrite frozen RUNs or earlier review results to adopt the marker.

## Harness Plan Manifest

```json
{
  "harness_plan": {
    "schema_version": 6,
    "plan_id": "PLAN-<stable-id>",
    "revision": 1,
    "objective": "<one measurable outcome and stopping condition>",
    "max_parallel_workers": 1,
    "branch_policy": {
      "protocol": "main-preview/1",
      "kind": "ordinary",
      "base_ref": "refs/remotes/origin/main",
      "base_sha": "0000000000000000000000000000000000000000"
    },
    "sources": [
      {
        "id": "SRC-001",
        "kind": "prd",
        "location": "docs/product/PRD.md",
        "owner": "<human or team>",
        "status": "frozen",
        "content_sha256": null,
        "source_revision": "0000000000000000000000000000000000000000",
        "staged_revision": null,
        "notes": "approved product authority"
      },
      {
        "id": "SRC-002",
        "kind": "architecture",
        "location": "docs/product/architecture.md",
        "owner": "<human or team>",
        "status": "frozen",
        "content_sha256": null,
        "source_revision": "0000000000000000000000000000000000000000",
        "staged_revision": null,
        "notes": "approved architecture authority"
      },
      {
        "id": "SRC-003",
        "kind": "stack decisions",
        "location": "docs/product/stack-decisions.md",
        "owner": "<human or team>",
        "status": "frozen",
        "content_sha256": null,
        "source_revision": "0000000000000000000000000000000000000000",
        "staged_revision": null,
        "notes": "approved stack authority"
      },
      {
        "id": "SRC-004",
        "kind": "delivery acceptance",
        "location": "docs/verification/delivery-acceptance.json",
        "owner": "<human or team>",
        "status": "frozen",
        "content_sha256": null,
        "source_revision": "0000000000000000000000000000000000000000",
        "staged_revision": null,
        "notes": "frozen delivery-acceptance scenario contract"
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
    "security_review": {
      "status": "required",
      "skill_slot": "code_security_verification",
      "reason": null
    },
    "required_reviews": ["security"],
    "batch_verifiers": [],
    "final_gates": [
      {
        "id": "final-check",
        "cwd": ".",
        "argv": ["<runner>", "<final-argument>"],
        "pass_signal": "exit 0",
        "execution": {
          "parallel_safe": false,
          "resources": [],
          "isolation": "host"
        }
      },
      {
        "id": "delivery-acceptance",
        "cwd": ".",
        "argv": [
          "<absolute-observed-python-executable>",
          "<installed-delivery-harness>/scripts/check_delivery_acceptance.py",
          "--repo-root", ".",
          "--prd", "docs/product/PRD.md",
          "--contract", "docs/verification/delivery-acceptance.json",
          "--contract-sha256", "<parent-frozen-hash>",
          "--results", "docs/verification/delivery-results.json",
          "--candidate-from-head"
        ],
        "pass_signal": "exit 0",
        "execution": {
          "parallel_safe": false,
          "resources": [],
          "isolation": "host"
        }
      },
      {
        "id": "final-closeout",
        "cwd": ".",
        "argv": ["<runner>", "<closeout-argument>"],
        "pass_signal": "exit 0",
        "execution": {
          "parallel_safe": false,
          "resources": [],
          "isolation": "host"
        }
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
            "allowed_providers": ["generic"],
            "worker_role": "implementer",
            "provider_options": {
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
            "allowed_providers": ["generic"],
            "provider_options": {
              "generic": {"model": null, "reasoning_effort": null}
            }
          },
          "review": {
            "stage": "preintegration",
            "type": "backend_code",
            "lineage_id": "REVIEW-M1",
            "mission_ids": ["M1"],
            "scope": ["src/example/**"],
            "required_evidence": ["reviewed_sha", "path-and-line findings", "root-cause-grouped finding set", "pass or fix_required decision"]
          }
        },
        {
          "id": "N-SECURITY-REVIEW",
          "kind": "verifier",
          "ref": "mission-focused",
          "executor": "runtime_worker",
          "allowed_outcomes": ["pass", "retryable_failure", "blocked", "contract_gap"],
          "max_attempts": 2,
          "runtime": {
            "preferred_provider": null,
            "allowed_providers": ["generic"],
            "provider_options": {
              "generic": {"model": null, "reasoning_effort": null}
            }
          },
          "review": {
            "stage": "integration",
            "type": "security",
            "lineage_id": "REVIEW-SECURITY",
            "mission_ids": ["M1"],
            "scope": [
              "src/example/**",
              "docs/verification/delivery-results.json",
              "docs/verification/evidence/**"
            ],
            "required_evidence": ["reviewed_sha", "trust-boundary coverage", "source-to-sink findings", "tool coverage and gaps", "pass or blocked decision"]
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
          "id": "N-ACCEPTANCE-GATE",
          "kind": "verifier",
          "ref": "delivery-acceptance",
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
          "id": "E-M1-REVIEW-SECURITY",
          "kind": "route",
          "from": "N-M1-REVIEW",
          "to": "N-SECURITY-REVIEW",
          "on_outcomes": ["pass"],
          "max_traversals": 2
        },
        {
          "id": "E-SECURITY-FINAL",
          "kind": "route",
          "from": "N-SECURITY-REVIEW",
          "to": "N-FINAL-GATE",
          "on_outcomes": ["pass"],
          "max_traversals": null
        },
        {
          "id": "E-FINAL-ACCEPTANCE",
          "kind": "dependency",
          "from": "N-FINAL-GATE",
          "to": "N-ACCEPTANCE-GATE",
          "on_outcomes": ["pass"],
          "max_traversals": null
        },
        {
          "id": "E-ACCEPTANCE-CLOSEOUT",
          "kind": "dependency",
          "from": "N-ACCEPTANCE-GATE",
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
        "write_scope": [
          "src/example/**",
          "docs/verification/delivery-results.json",
          "docs/verification/evidence/**"
        ],
        "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md"],
        "resource_inventory_complete": true,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": true,
        "required_skills": [],
        "worker_verifiers": [
          {
            "id": "mission-focused",
            "cwd": ".",
            "argv": ["<runner>", "<mission-argument>"],
            "pass_signal": "exit 0",
            "read_only": true,
            "execution": {
              "parallel_safe": false,
              "resources": [],
              "isolation": "host"
            },
            "selection": {"mode": "changed_files", "scopes": ["src/example/**"]},
            "cache": {"mode": "disabled", "environment_keys": []}
          }
        ],
        "integration_verifiers": [
          {
            "id": "mission-integration",
            "cwd": ".",
            "argv": ["<runner>", "<integration-argument>"],
            "pass_signal": "exit 0",
            "execution": {
              "parallel_safe": false,
              "resources": [],
              "isolation": "host"
            }
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
                "criterion": "<observable scenario or assertion that stays inside this task; for a security boundary, include denial and no unauthorized side effects>"
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
                "read_only": true,
                "execution": {
                  "parallel_safe": false,
                  "resources": [],
                  "isolation": "host"
                },
                "selection": {"mode": "changed_files", "scopes": ["src/example/**"]},
                "cache": {"mode": "disabled", "environment_keys": []}
              }
            ]
          }
        ]
      }
    ]
  }
}
```

The exact fenced JSON block is the canonical plan. New plans use PLAN schema v6. Older PLAN schemas remain readable; their recorded schema decides which fields apply. Every runtime review has a stable `lineage_id` that survives node replacement and PLAN revision. The graph is the canonical source for mission dependencies and routing. Keep the JSON valid, increment `revision` after an accepted semantic plan or graph change, and calculate the run's digest with the normalization algorithm in `references/execution-state-model.md`. There is no `execution_route` PLAN field: the selector derives it from the chosen route and actually selected safe write missions.

`branch_policy` freezes the observed remote main head for both `ordinary` work and `hotfix`. Replace the zero SHA with that full SHA; waves never advance it. Harness 0.63+ requires `main-preview/1` and the active architecture marker `Release source policy: main-preview/1`. Pinned 0.59–0.62 RUNs retain `dual-branch/1`; older pins retain their recorded contract. The exact-A correction exception retains its original policy and runtime pin. `new_run.py --branch` names the owner-resolved temporary integration branch; the generator never invents or mutates the base. PR/branch Preview acceptance precedes separately authorized main landing.

Every new RUN records an explicit `security_review` policy. Use `required` for code delivery and include `security` in `required_reviews`; use `not_applicable` only with a concrete reason for a non-code delivery. `new_run.py` refuses an omitted policy. A required policy may add `required_checks`: batch or final verifier IDs whose single parent-run graph node must precede every security node and pass at the reviewed head before reservation; the review packet carries each with its `execution_key`. Existing PLAN-v6/RUN-v11 pairs remain readable and are never silently rewritten.

When the frozen architecture declares `platform-delivery/1`, add optional `platform_delivery`. Its stages use `{id, mission_ids, completion_mission_id, integration_verifier_ids}`. Derive order from the architecture, not list order. Use pass-only dependencies to completion and the next stage. Completion integration verifiers disable reuse and annotate every upstream platform TEST ID. Fresh final gates cover the platform TEST set. In this marked flow, including `not_required`, every planned `PRD-*` must trace names its existing gates in `acceptance_gate_ids`; unmarked legacy PLANs keep their old optional behavior.

Planned security requirements reuse upstream `PRD-*` traces and required `TEST-*` acceptance IDs. Give each trace an existing disposition (`planned`, `deferred`, or `out_of_scope`) under the current trace rules; an executable touched boundary must be `planned`. This template adds no security-specific schema or risk document.

The single-mission example deliberately leaves `batch_verifiers` empty: a one-mission managed route has no true cross-mission batch gate. It still proves the selected runtime driver, allocates an isolated writer, checks exact authorization and scope/head bindings, runs the direct singleton pre-integration review, integrates the candidate, dispatches a fresh `security` reviewer with the project's `code_security_verification` binding, and closes through final gates. The neutral example has no predeclared security-repair mission, so a validated finding returns `blocked` and requires an explicit PLAN refinement before any write; a project that declares `fix_required` must also declare the bounded repair and re-review route. If two or more safe write missions are selected, the selector reports `parallel_graph` and the plan may declare real cross-mission checks.

For each `runtime_worker` node, record the actually allowed host identities in `allowed_providers`, with `preferred_provider` null unless explicitly chosen. The `generic` example is a placeholder for an unknown host, not a wildcard. Leave model and effort null to preserve installed defaults. Set explicit supported options only when selected; the agent observes native capability rather than applying provider-specific rules.

Add logical `runtime.worker_role` when host policy binds a specialist or reviewer. UI authoring or implementation uses `frontend_worker`; independent review uses `reviewer`. Other portable or host-defined role IDs are allowed. The RUN maps the role to actual native or bridge execution and per-node axes; a missing mandatory binding defers the node instead of substituting the parent or another implementer.

Harness 0.38+ always freezes the three exact rows shown above with current `content_sha256`; if `source_revision` is present, that full-SHA Git blob and current bytes must both match. Contract joins consume those immutable bytes. Harness 0.59+ new full-UI work adds exact `ui design` (`ui-design/3`) and `approved ui target` rows; the target entry embeds the manifest and binds every sibling hash. A retained `ui-design/2` package uses its original contract; pins 0.56–0.58 require `ui-design/2`. Older pinned RUNs, and maintenance rounds on a legacy UI contract, retain their wireframe row. Current rows stay at their canonical `docs/design/` paths. A `required` Design System Need gate adds exact `design system` and `design system json` rows; `ui-design/3` also adds the frozen `design system preview` row. `not_required` adds neither and permits no `DS-*` trace. Every UI surface records `capture_mode: hosted-browser | browser-extension | native | desktop`. URLs are never fetched or joined as authority. A `staged_revision` is not an executable publication. Publish the accepted revision to the canonical source location, clear staging, and increment PLAN revision/digest.

Every executable verifier declaration uses an explicit isolation mode. New templates default to `isolation: "host"`, `parallel_safe: false`, and disabled cache: the command runs in the exact checkout cwd with the project's local tools and environment, and host builds may create ignored artifacts but tracked source and protected Git state must remain unchanged. Host mode is not OS isolation and never reuses results. To use the legacy pinned container route instead, declare the full container policy explicitly and replace the example image reference with a locally observed immutable RepoDigest before readiness; zero or fabricated template digests are rejected, and omission never downgrades to host. External, network, browser, and mutable-environment checks use an external-wait, lifecycle, or browser route instead of a local candidate subprocess. Task and worker declarations may use the exact `selection.mode: "changed_files"` form shown by the machine manifest's `"mode": "changed_files"` value; targeted checks follow parent-observed changed files.

Before readiness, apply `references/execution-task-decomposition.md`'s Mission Cohesion Gate to every mission. Split independent product surfaces or domain capabilities even when they share router, auth, schema, migration, or serialized resources; model the shared foundation and ordering explicitly instead of creating a catch-all mission. Plan each mission as one bounded fresh-child worker slice that normally stays within 10-20 minutes of implementation plus focused verification, treating that range as an upper shape rather than capacity to fill. Make every executable task one atomic initial commit boundary: verify and commit it before the next task begins; keep later repair commits separate and attributed to that task.

Before implementation, every touched security boundary has a control, denial/no-side-effect acceptance row, existing verifier, and evidence plan. Required evidence or tooling that is unavailable blocks readiness or execution; no scanner is installed automatically.

For each required security TEST, its acceptance `criterion` uses `denial: rejected (<observable rejection signal>); no unauthorized side effects: unchanged (<observable state evidence>)`. Each observation needs at least 12 characters and no placeholders. The canonical Product checker validates this same format in the TEST Expected signal; matching IDs or a generic scan result alone cannot satisfy the join.

Plan one runtime reviewer per applicable surface, set `max_attempts` to at most 2, and add same-surface fan-out only for an explicit user request or a recorded high-impact risk. Every new code-delivery plan includes one integration-stage `security` review covering all missions and loads the skill bound to `code_security_verification`; it always runs fresh on the unified candidate and cannot use the byte-identical-tree skip. Group repair findings by root-cause failure family, freeze the family's acceptance matrix before another write, and carry consumed review attempts across PLAN revisions in the owner-decision source, mission stop conditions, and reviewer packet. A replan does not grant a fresh review budget. After exhaustion, only an explicit owner decision naming the structural strategy, failure-family matrix, and exact additional allowance may create one successor review node; set its `max_attempts` to that allowance, never the default two. Model and effort choices remain per-node and explicit. Null preserves the host defaults. The agent checks current support and preserves installed role/fallback policy; no provider-specific catalog or default applies. A non-null preferred provider records an explicit host preference and never authorizes a bridge. Keep final review tied to the unified SHA and do not add another same-scope review on an unchanged head.

For UI work, load `references/ui-implementation-contract.md`. Freeze the approved UI contract, HiFi target, capture mode, and exactly one visual route. `design-system-compiler` owns the required `design-system/4` package and frozen derived HTML for `ui-design/3`; a retained `ui-design/2` package owns its conditional schema-3 pair; otherwise use the exact `not_required` replacement. UI implementation uses the owner-bound frontend-authoring skill under Harness conformance. A missing source is a design-input delta. Run platform-correct evidence after exact-SHA review and repair converge.

Use immutable flat task IDs such as `M1/T01`. Each task has a structured acceptance row exactly `{test_id, trace_ids, criterion}` and a verifier. Task dependencies are same-mission only; cross-mission ordering belongs in typed graph dependency edges. Scope entries are POSIX repository-relative paths or terminal `/**` subtrees. Workers never edit PLAN/RUN or frozen contract sources.

## Source Map

| Source | Path / URL | Content SHA-256 / immutable revision | Status | Role / notes |
|---|---|---|---|---|
| Product requirements | <path> | <hash or revision> | draft / frozen / delta_accepted / missing / n/a | <notes> |
| Product Definition Approval | <PRD section> | <same hash or revision> | approved / revision_requested / blocked / n/a | <package revision, owner, blockers> |
| UI design contract | <ui-design.md path> | <hash or revision> | approved / provisional / blocked / n/a | <intake, motion/media, PRD-to-HiFi completeness, Visual Approval, Impeccable and H1-H9 evidence; historical approvals retain their meaning> |
| Approved HiFi target | <target path/version> | <hash or revision> | approved / provisional / blocked / n/a | <Design System Need Gate, scope, states, responsive matrix, tolerance> |
| Architecture / API / data | <path> | <hash or revision> | draft / frozen / missing / n/a | <notes> |
| Stack decisions | <stack-decisions.md path> | <hash or revision> | approved / revision_requested / blocked / n/a | <Required/Selected/Approved layers; delegation source if used> |
| Design system pair | <path> | <hash or revision> | draft / frozen / missing / n/a | <required only when the Design System Need Gate is required> |
| Design system preview (derived) | <design-system-preview.html path or n/a> | <hash or n/a> | frozen / missing / n/a | <required with `design-system/4`; derive from the frozen pair and bound HiFi> |

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

These are planning expectations, not authorization. Record explicit action authorization only in RUN schema v11. `tasks.md` is an optional on-demand human view, not a second state source.

## Scope And Contract Freeze

### Must Have

- `PRD-001` <requirement>

### Non-Goals

- Parallel fan-out when fewer than two safe write missions are selected.
- UI repair graphs or unplanned design changes.

## Plan Readiness Gate

For RUN pins >=0.60.0, require the PRD's explicit `eval-policy/1` applicability;
older pins keep their checks unless a marker opts in. Applicable plans also
freeze `SRC-EVAL` of kind `eval contract` at `docs/verification/eval-contract.json`.
Follow `references/eval-acceptance-contract.md`: add the always-run final gate
`eval-acceptance` invoking installed `check_eval_acceptance.py` with independently
frozen PRD/eval/delivery hashes and default register. Both eval and delivery
acceptance gates declare `execution.isolation: host` and absolute installed
checker paths with the observed absolute Python executable; PATH or a project
executable cannot substitute it. Containers cannot substitute their filesystem. Add its local-command node
between every broad final check and delivery acceptance, using pass-only
dependency edges. Keep `final-closeout` after delivery acceptance. Missing or
substituted sources, checker argv, hashes or graph paths fail the common join.
Declare runner/grader/lockfile/runbook task scope and two independent full-run
reports before execution. PLAN/RUN store no duplicate eval state.

For newly authored delivery work, also follow `references/delivery-acceptance-contract.md`. The example manifest above shows these entries; keep all of them before readiness:

- a source `SRC-004` of kind `delivery acceptance` at `docs/verification/delivery-acceptance.json`, frozen like the other rows;
- a final gate `delivery-acceptance` with no `selection` (so it always runs) whose argv runs `check_delivery_acceptance.py` with `--repo-root`, `--prd`, `--contract`, `--contract-sha256`, `--results` and `--candidate-from-head`;
- a `local_command` verifier node `N-ACCEPTANCE-GATE` with `ref: "delivery-acceptance"`;
- `dependency` edges from `N-FINAL-GATE` to `N-ACCEPTANCE-GATE` and from `N-ACCEPTANCE-GATE` to `N-CLOSEOUT-GATE`.

Use the parent's frozen contract hash, never a value derived from result writers. The PLAN cannot name the candidate H1, because H1 exists only after the last merge; `--candidate-from-head` takes H1 from the register and fails unless Git shows H1 is an ancestor of the checked-out head and every later commit changes only the register, the evidence files it lists under `docs/verification/evidence/` (the `evidence/` directory next to the register) and run coordination files. The register commit gets its RUN slot through `record-integration`, in one order:

1. Merge the last mission by `merge_rank`, giving H1. Do not record it yet.
2. Run the scenarios at H1 and write `candidate_sha: H1` in the register.
3. Commit only the register and the evidence files it lists on top of H1, giving H2.
4. Run `record-integration --integrated-sha H2` for that mission, so H2 is the recorded integration head.
5. Run every unified review and final gate, including `N-ACCEPTANCE-GATE`, at H2.

For this, the last mission's `write_scope` lists `docs/verification/delivery-results.json` and `docs/verification/evidence/**`, as M1 shows, and so does the security review's `scope` (the validator requires it to cover every mission scope). Readiness review checks that the base already has byte-preserving `-text -filter` attributes for these paths; if not, put `.gitattributes` in an authorized pre-H1 task's `write_scope` and the security review scope, and commit it before H1. `record-integration` checks only that mission scope, so `N-ACCEPTANCE-GATE` is what refuses a product file committed with the register. Only the parent writes these paths, and every evidence file the register lists comes from its own run at H1. When the PLAN declares the acceptance gate, worker-result validation refuses a worker change to the register the gate names with `--results` or anything under its `evidence/` directory, whatever the task `write_scope` says. It also refuses any change no task `write_scope` covers, even when the register path cannot be read from the gate argv. Both checks run in every workspace mode, shared checkout included. They are not coordination paths, so a register commit after the recorded head leaves RUN stale. Any candidate repair after H2 changes files outside the register, so `N-ACCEPTANCE-GATE` fails at the repaired head. `reconcile-candidate-head` accepts only paths in the repair task's `write_scope`, which never lists the register, so rerunning acceptance after H2 needs a formal PLAN revision with fresh owner authorization: the new digest stops the old execution grants from covering anything. The revision adds a repair task whose `write_scope` lists only the register and evidence paths; that is safe then because the mission is already integrated. The parent commits that repair and records it with `reconcile-candidate-head`; a worker result cannot carry it. The template's neutral command placeholders must be replaced before execution.

Applicable eval policies require these entries through the common source join.
For older plans without an eval marker, the parent's readiness review still
confirms them; schema validation alone is insufficient. Do not retrofit or
silently migrate a running legacy PLAN/RUN. Direct work runs the acceptance CLI
without these artifacts.

Implementation may start only after static validation passes, RUN records `plan_readiness: "ready"`, and required actions have explicit user authorization. Readiness never grants authorization.

Before marking readiness, reject any mission whose objective contains independently shippable or reviewable outcomes, whose tasks hide multiple commit-sized deliverables, or whose only cohesion is a shared file or serialized resource. Every executable task must map to its own authorized atomic commit before the next task begins.

`plan_readiness` in RUN is the single machine gate; do not restate the checks as a hand-filled table here.

## Stop / Ask Conditions

- <condition>
- A touched security boundary lacks an upstream PRD/TEST contract, control, negative test, required evidence, or tooling.
- A UI route has no frozen screen/design-system entry; load `ui-implementation-contract.md` and route a design-input delta instead of inventing a value.
- A required worktree, authorization, scope/head binding, or exact-head review cannot be proved.
