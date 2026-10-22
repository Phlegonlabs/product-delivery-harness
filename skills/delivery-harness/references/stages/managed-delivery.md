# Managed Delivery

Apply this file only after the entry routes work as `large`.
Literal `references/...`, `assets/...`, and `scripts/...` paths resolve from the delivery-harness skill root.

## Managed Route

Recover existing RUNs before replacement; see `references/execution-state-model.md`.

New managed work uses PLAN schema v6 and RUN schema v11. New managed work never authors a compact RUN-only artifact. Legacy compact RUN-only files remain readable for recovery, but cannot authorize new execution.

Author PLAN from `assets/templates/HARNESS_PLAN.template.md`. Generate RUN with `scripts/new_run.py`; it derives initial state and grants nothing. RUN owns checkpoints, tasks, attempts, evidence, and closeout. With `--repo-root`, `new_run.py --out` and guarded checkpoint transitions automatically render `docs/tasks.md` from its declared coordination path; this non-canonical view preserves its Update Log. A refresh failure leaves successful RUN state intact; use `scripts/render_tasks_view.py` to repair or `--check` it. Read `references/execution-state-model.md` for the checkpoint set, source guards, and formal revision procedure.

### Reference Routing

Read only what the current decision needs:

- `references/contract-and-traceability.md`: frozen sources, traces, permissions, and file placement.
- `references/execution-state-model.md`: PLAN/RUN creation, resume reconciliation, authorization, state transitions, and host handoff.
- `references/graph-orchestration.md`: typed graph, provider policy, bounded experiments, retries and correction loops.
- `references/execution-task-decomposition.md`: mission/task split rules.
- `references/parallel-mission-selection.md`: parallel write-wave selection.
- `references/runtime-adapters.md`: the general capability and dispatch contract, applied only when managed execution needs it.
- `references/deployment-contract.md` and `references/branch-promotion-contract.md`: candidate-environment verification and post-RUN exact-SHA promotion to `main`.
- `references/worktree-thread-orchestration.md`: only after the selected adapter needs workers, threads, or worktrees.
- `references/verification-gates.md`: task, integration, UI, and evidence gates.
- `references/runtime-performance.md`: bounded context, event waits, and verifier batches.
- `references/runtime-upgrades.md`: host/Harness version observation, old-runtime wave boundaries, updater/restart handling, and fresh-session recovery.
- Runtime trust/publication: see `references/runtime-trust.md` and `trusted-host-publication.md`.
- `references/ui-implementation-contract.md`: every UI implementation or UI review.
- `references/gitignore-contract.md`: task-specific ignore classification and checks.
- `references/commit-convention.md`: before a Harness-managed commit.
- `references/design-input-updates.md` and `references/platform-archetypes.md`: only when those shapes apply.
- `references/orchestration-research-notes.md`: capability/version evidence, not routine execution.
- `references/worker-result-contract.md`: only while rendering or validating a delegated worker payload.

## Adapter Routing

Direct delegation uses `references/delegation-contract.md`; managed execution also uses `references/runtime-adapters.md`. Record observed capabilities and host identity (`generic` when unknown). Bridges need explicit bindings and authorization.

The adapter layer owns no shared state, authorization, review, integration, handoff or cleanup. Adding a host needs no provider section, fixed model defaults, launch script or schema change.

## Default Runtime And Wave Policy

Apply this only to large plan-backed work:

1. Proactively inspect the current-session native tool surface, permission boundary, completion channel, worker slots, isolation, Git state, shared resources, host version, and loaded Harness version before the first launch.
2. Record observed capability independently from authorization. Missing authorization must never make an available driver disappear. Every advertised delegated driver needs observed `capability_probe` facts; unrelated surfaces need no inventory. For a web review that must inspect the live page, add `review.required_tools: ["chrome_devtools"]` in PLAN and record the selected driver's fresh reviewer-session probe under `runtime_capabilities.reviewer_tools.chrome_devtools`. Parent-session access, an installed package, or a CLI flag alone is not enough. A capability-probe child is read-only discovery, never review evidence, and still needs matching launch authorization; its result cannot update review state.
3. Do not cap `max_parallel_workers` at a small fixed number. The effective budget is the minimum of configured maximum, observed slots, isolation capacity, and the dependency-ready conflict-free frontier.
4. Before selection, record `observed.captured_at`, live Git facts, and `integration.batch_base_sha`. A green validator with empty `dispatchable_nodes` and `deferred_nodes` reasons `parent_state_unreconciled` or `batch_base_missing` means the live snapshot is incomplete; these are dispatch-time reasons, not an empty graph.
5. Enable scheduler fan-out only when at least two dependency-ready, nonconflicting write missions have isolated workspaces and exact authorization. Never run parallel writers in `shared_checkout`.
6. If no delegated driver is usable, only nodes without a mandatory delegate may use `sequential_parent` under `references/execution-state-model.md`. Required frontend and independent review nodes stay blocked until an eligible bound executor is available.

## Default Mission Topology

1. Map one feature batch to one mission: one user-visible feature or one shared foundation, owned by one writer role. A mission is not a phase label, subsystem backlog, or catch-all for everything touching one router. Blog, Settings, and user administration are separate features; the pages and endpoints of one feature are tasks inside its mission.
2. Pass the Mission Cohesion Gate in `references/execution-task-decomposition.md` before readiness. Split a mission only when parts need different writer roles, a shared contract must be frozen first, parallel work saves more than one more review costs, or the batch will not fit one worker session. Every mission adds an integration; under `per_mission` it also adds a review, so count planned review nodes and merge single-task missions into feature batches. Shared files, likely merge conflicts, or serialized resources are not reasons to bundle unrelated features: freeze a shared foundation first, then represent ordering and conflicts with dependency and resource edges.
3. Plan tasks as ordered atomic commit boundaries. Complete one task's implementation and focused verifier, create its authorized task commit, and only then begin the next task. One commit cannot satisfy multiple tasks. A review repair is a separate atomic follow-up commit attributed to exactly one task; it does not make the original task broader.
4. Size each mission so its fixed worktree, handoff, validation, serial integration, and rerun overhead stays small against useful work; overslicing slows delivery and multiplies reviews. Treat 10-20 minutes of implementation plus focused verification as each task's upper shape, not a target. The mission's worker runs its tasks in order, one bounded worker slice per task, in one session. If a task cannot fit one bounded worker slice, split the task before readiness rather than rely on a long-running child or timeout-driven repair.
5. For bounded read-only exploration, split independent substantive questions into distinct authorized sibling assignments under `references/delegation-contract.md`. Explorers report to the parent, never delegate; capacity limits waves, not assignment identity.
6. Give every writer one explicit `write_scope` and one isolated exact-base worktree. No active writers share a branch, file ownership, or exclusive runtime resource.
7. Freeze shared APIs, schemas, and types before dependent missions launch.
8. Verify repository, branch, base HEAD, and empty `git status --porcelain` before dispatch.
9. Render `WORKER_GOAL.template.md`; attach only the host contract and result fields that mission needs.
10. Validate returned identity, changed files, scope, verifier evidence, atomic task-commit attribution, commit order, and ancestry against live Git.
11. Dispatch one planned parent-owned read-only reviewer on the unified SHA with the union of lenses the mission's write scope needs, across every mission, per `verification-gates.md#review-topology`. Its `review.type` names the widest lens and the human plan view lists its lenses. A `visual` lens declares `required_tools: ["chrome_devtools"]`; a `frontend_code` lens declares it when DOM state, console, network, runtime JavaScript or rendered behavior is evidence. The selector defers a missing tool as `reviewer_tool_unobserved:<tool>` or `reviewer_tool_unavailable:<tool>`; never replace it with the parent's browser session. Render its bounded packet with `scripts/render_review_packet.py`; do not attach the full PLAN/RUN. The review returns all blocking findings in one pass and allows at most one repair-and-re-review cycle; do not dispatch another same-scope review on an unchanged SHA. Collect every required review result for the same candidate before repair, then group related findings into one root-cause failure family and send one consolidated repair. The re-check covers the original findings, the changed code and its direct consumers; it is not a fresh full review. Root-cause repair follows `graph-orchestration.md#root-cause-repair-escalation`. Non-blocking suggestions go to the Epic backlog. Under `per_mission`, each mission also gets its own exact-head review before it integrates.
12. Run one planned broad final validation suite after it passes.

Managed runs carry no wall-time percentage target. The objective is to stop paying for the same work twice. Follow `references/runtime-performance.md`; removing repetition never weakens authorization, exact-head review, evidence, or final validation.

## Workflow

### 2. Plan Large Work

Freeze only approved inputs needed by the graph: Product Definition revision, Stack Decision Checkpoint, source paths and digests, scope, architecture and design boundaries, acceptance criteria, trace IDs, write/deny scopes, dependencies, resources, stop conditions, and exact verifiers. Every plan freezes one canonical PRD, architecture, and stack source and always runs the full sibling Product package checker with `--repo-root`. New full-UI plans freeze `ui-design/3`, complete HiFi, `design-system/4` and one frozen derived HTML source, without wireframes; retained and older pins follow `legacy-pins.md#legacy-ui-contracts-before-059`. Use the bounded review-repair graph and owner-attempt rules. A generic instruction to continue grants no new attempt.

Map active `platform-delivery/1` stages in architecture order. Use pass-only dependencies to completions and next stages. Shared foundations start first. Completion verifiers carry upstream platform TESTs. Marked contracts, including `not_required`, require fresh gates for planned features.

For initial website/app work, read [Initial Product Foundations](../initial-product-foundations.md).
Order approved discovery, deployment and measurement prerequisites before their dependent features using existing dependencies and TEST obligations.
Keep code tasks separate from parent-coordinated, separately authorized external setup; neither workers nor RUN gain deployment or console-write authority.
Use evidence for each prerequisite, not global Activation readiness, to unblock its dependent work. Preserve independent work during external blockers.

### 3. Pass Plan Readiness

Apply the direct route's self-review handoff before managed readiness.

Require frozen or explicitly `UNVALIDATED` inputs, concrete scope, a passed Mission Cohesion Gate, feature-batch missions with small fixed overhead and one bounded worker slice per task, one atomic commit boundary per executable task, a verifier for every mission, known conflicts, exact action authorization, and an executable provider for every runtime-worker node. Reject readiness when unrelated features are bundled only because they share files/resources, one task needs a catch-all commit, or a single-task mission has no Mission Cohesion Gate reason. Executability covers the whole graph, not just the next node; each node's `allowed_providers` must include a host this delivery actually uses. An unavailable provider is a blocking readiness gap unless the user explicitly accepts deferral to another host. See `references/graph-orchestration.md`.

Apply `references/gitignore-contract.md`'s task ownership and `write_scope` gate when applicable.

### 4. Execute And Integrate

Acceptance/eval gates: `references/delivery-acceptance-contract.md`, `references/eval-acceptance-contract.md`.

After the version gate, run `python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan docs/goal/PLAN.md --run docs/goal/RUN.md --repo-root <absolute-root> record-observation`. Global flags precede the subcommand. It binds the host, PLAN revision, and digest, plus runtime and RepoDigest for explicitly selected containers; `--probe-sandboxes` is diagnostic only. `lease-worker` copies selector bindings and materializes exact targets only from active wildcard grants. Record through guarded transitions, review exact heads, integrate serially, and close the wave.

### 5. Verify Local-First

New PLANs explicitly select `execution.isolation: "host"` for local build/lint/test. Host commands use current user permissions, not sandbox confinement. Containers remain optional with no fallback. See `references/verification-gates.md` for mode, source/Git guards, and evidence requirements.

Follow the verification ladder and Review Topology in `references/verification-gates.md`. Retain Final UI Acceptance from it on the unchanged candidate without another reviewer dispatch. Finish with the applicable `references/gitignore-contract.md` checks, `git diff --check` and a complete final-diff review.

Host verifiers run fresh and serially per runner. Container `session_exact` reuse requires `exit 0`, clean matching inputs, read-only task/worker declarations, and `cache.deterministic_local: true` within one runner batch. Every consumer rechecks guards and runtime/image identity and retains its reservation, evidence, and origin. Keep request/result artifacts repository-external; no disk cache is used. Integration, cross-mission, final, browser, migration, mutable-environment, and network checks execute fresh. UI artifacts under `docs/goal/evidence/` use lowercase SHA-256 and bind to the integration head.

### 6. Complete

RUNs close `local_only` at C after all gates and security pass, and a current RUN never pushes. Archive, publication, Preview gates and exact-SHA `main` promotion follow `references/branch-promotion-contract.md#managed-run-archive-before-promotion`.

`product-activation` preparation may start at a fixed initial build before dependent features, under separate authorization.
Final readiness, measurement handoff, outcome review and live SEO review retain their applicable release and production verification; no RUN grant authorizes them.
