---
name: fullstack-harness-engineering
description: "Route engineering work to the lightest safe delivery path, then plan, authorize, execute, verify, and integrate it. Use direct parent-owned delivery when one writer and one coherent verification pass are enough. Use PLAN-v6/RUN-v11 only for work that needs durable coordination, isolated mission integration, or a bounded correction graph. Load exactly one Codex, Claude Code, or Pi adapter only when that managed route needs host-specific orchestration."
---

# Full-Stack Harness Engineering

## Purpose

Use the least ceremony that preserves the real safety boundary. Keep routine work direct. Add PLAN/RUN state, runtime probing, workers, worktrees, and graph scheduling only when coordination requires them.

Keep upstream ownership separate:

- `prd-builder` owns `PRD.md`, approved low-fidelity `wireframes.html`, `architecture.md`, and `stack-decisions.md`.
- `PRD.md` owns UI structure, behavior, and the approved UI Design Handoff; `wireframes.html` makes its low-fidelity page, section, state, and responsive map inspectable. `product-design-builder`, with `frontend-design`, owns `design-system.md` and `design-system.json` only when the Design System Need Gate is `required`.
- This skill implements frozen inputs, including the Builder UX Direction and either the formal design-system pair or the approved page-faithful UI target recorded when the pair is `not_required`. It invents neither product direction nor design sources. Builder approval proves direction conformance, not usability proof; every must-have `UX-*` trace still needs objective evidence.

## Project Size Gate

Before loading a task skill, adapter, planner, scheduler, or worker, run one bounded parent-only, read-only scope scan.

Classify work as `small` when one parent writer can own one bounded outcome, work in one implementation branch or checkout, and verify it with one coherent local sequence. A high file count, several languages, a long test command, or difficult reasoning does not make work `large` by itself.

Classify work as `large` only when at least one condition is true:

- two or more independently writable missions need separate ownership or integration;
- execution needs durable cross-session or cross-host handoff;
- independently reviewed mission heads must integrate into one candidate;
- a migration, destructive operation, or correction loop needs a durable bounded graph; or
- the user explicitly requests managed Harness orchestration.

Planning preference may choose the stricter route, but it cannot override a `large` classification or any safety boundary.

```text
System Review And Route (parent-only, read-only)
  small -> direct inspect -> implement -> local verify -> review -> authorized Git actions
  large -> planner -> PLAN v6 + RUN v11 -> readiness -> managed execution
```

Small work creates no PLAN/RUN files, scheduler state, worker-capability inventory, or delegated worker by default. Load no runtime adapter unless the direct task actually needs a host-specific action. If small work grows large, preserve the current diff and evidence, then plan only the remainder.

### System Review And Route

Complete this checkpoint before loading any task-specific skill. Read the request, repository instructions, Git state, requested scope, and relevant frozen product/design inputs. Do not create or edit `PLAN.md`, `RUN.md`, `tasks.md`, branches, worktrees, evidence, or implementation files during this checkpoint.

Record:

```text
Project size: small | large
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Route: direct | plan-backed graph
Host adapter: none | codex | claude_code | pi | generic
Landing: local_only | integration_push
Upstream inputs: present | missing | needs owner decision
```

For UI work, inspect only `docs/design/`, a user-named design folder, and obvious in-scope images encountered during the normal scan. Treat each image as a candidate reference, record its relative path and hash, and route it through `references/design-input-updates.md`. It influences implementation only after the PRD UI Design Pass records owner-approved consequences; when the Design System Need Gate is `required`, `product-design-builder` also compiles those consequences into the frozen pair.

When an existing RUN is `running`, perform the Resume Reconciliation Gate in `references/execution-state-model.md` before selecting work. Start with `python .agents/skills/fullstack-harness-engineering/scripts/inspect_harness_run.py --repo-root <target-root>` for a concise manifest-versus-worktree summary, then inspect host process/session evidence separately. Canonical state, live process state, Git heads, and dirty worktrees are separate evidence; never assume `worker_running` proves a live worker.

After capability detection, apply `references/runtime-upgrades.md`. An old compatible runtime may finish only its already-active wave; an incompatible or restarted runtime dispatches nothing until a fresh session re-probes successfully. Never hot-upgrade a live worker or silently mutate installed runtime software.

## Non-Negotiable Boundaries

These rules apply to both routes:

- Selecting this skill grants no mutation permission. Bind each state-changing action to the user's exact instruction and target.
- Preserve all 12 managed action keys: `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `archive_worker_tasks`, `remove_worktrees`, and `delete_branches`.
- Execution intent covers only applicable local setup, branch, commit, and integration actions. It does not authorize `push`. Push needs a separate explicit remote instruction for the resolved non-default integration branch and current exact head.
- Never push to the default branch. Never add a fixed prefix to a run branch. Follow repository governance or the user's exact branch; if neither names it, ask before branch creation.
- Archival, worktree removal, and branch deletion are separate actions and are never implied by completion.
- The parent owns routing, authorization, PLAN/RUN, dispatch, leases, integration, and lifecycle actions. Workers and reviewers never delegate, edit PLAN/RUN, integrate, push, or clean up.
- A review PASS binds one exact SHA. Any repair invalidates it.
- Preserve failed, interrupted, cancelled, dirty, and partial worktree evidence. Never reset or remove it automatically.

## Direct Route

For small work:

1. Inspect the bounded component and relevant instructions.
2. Implement with one parent writer.
3. Run the smallest focused checks that prove the change.
4. Review the complete diff and run `git diff --check`.
5. Perform only authorized Git actions.

For small UI work, add one critique-repair-recheck cycle before final review. Use rendered evidence when available; otherwise perform a text-only markup/style review and state that no visual claim was made. Obey `references/ui-implementation-contract.md`. Stop after two failed repair attempts and report the remaining gap.

For a self-contained feature inside an existing codebase, offer `/feature-dev` as an optional richer implementation loop. It does not change authorization, ownership, or verification rules.

## Managed Route

New managed work uses PLAN schema v6 and RUN schema v11. New managed work never authors a compact RUN-only artifact. Legacy compact RUN-only files remain readable for recovery, but cannot authorize new execution.

Author PLAN from `assets/templates/HARNESS_PLAN.template.md`. Generate RUN with `scripts/new_run.py` rather than hand-copying `assets/templates/MISSION_RUNBOOK.template.md`; nearly every field of a new RUN is derivable from PLAN, and the generator grants nothing. Keep one canonical fenced JSON manifest in each file. Keep checkpoints, tasks, attempts, evidence, and closeout in RUN; create `tasks.md` only when a human listing is useful.

### Reference Routing

Read only what the current decision needs:

- `references/contract-and-traceability.md`: frozen sources, traces, permissions, and file placement.
- `references/execution-state-model.md`: PLAN/RUN creation, resume reconciliation, authorization, state transitions, and host handoff.
- `references/graph-orchestration.md`: typed graph, provider policy, retries, and correction loops.
- `references/execution-task-decomposition.md`: mission/task split rules.
- `references/parallel-mission-selection.md`: parallel write-wave selection.
- `references/worktree-thread-orchestration.md`: only after the selected adapter needs workers, threads, or worktrees.
- `references/verification-gates.md`: task, integration, UI, and evidence gates.
- `references/runtime-performance.md`: bounded context, event waits, streaming review, verifier batches, and machine telemetry.
- `references/runtime-upgrades.md`: host/Harness version observation, old-runtime wave boundaries, updater/restart handling, and fresh-session recovery.
- `references/ui-implementation-contract.md`: every UI implementation or UI review.
- `references/commit-convention.md`: before a Harness-managed commit.
- `references/design-input-updates.md` and `references/platform-archetypes.md`: only when those shapes apply.
- `references/orchestration-research-notes.md`: capability/version evidence, not routine execution.
- `references/worker-result-contract.md`: only while rendering or validating a delegated worker payload.

## Adapter Routing

Load no adapter for direct work. For a large managed run, load exactly one adapter after System Review And Route:

- Codex: `../fullstack-harness-codex/SKILL.md`
- Claude Code: `../fullstack-harness-claude-code/SKILL.md`
- Pi: `../fullstack-harness-pi/SKILL.md`

Adapters select launch mechanics and provider-specific model options. They grant no authorization and do not redefine shared state, review, integration, handoff, or cleanup rules.

## Repository Context Contract

Discover the effective instruction chain from repository root to the selected checkout.

- Existing `AGENTS.md`, `AGENTS.override.md`, and `CLAUDE.md` files are user-owned authority. Never overwrite, merge, normalize, or silently copy them.
- On an authorized first bootstrap, run `scripts/configure_project_context.py --root <target-root>`. It creates only missing root files from `PROJECT_AGENTS.template.md` and `PROJECT_CLAUDE.template.md`; the generated files are intentionally different.
- Codex receives the effective `AGENTS.override.md` / `AGENTS.md` chain and never receives `CLAUDE.md` as Codex instructions.
- Claude Code receives its effective `CLAUDE.md` chain plus shared `AGENTS.md` governance.
- Pi uses Pi's native per-directory priority: `AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`.
- Keep automatic context discovery enabled. A nested instruction may narrow a mission but never widen write scope or authorization.

## Default Runtime And Wave Policy

Apply this only to large plan-backed work:

1. Proactively inspect the current-session native tool surface, permission boundary, completion channel, worker slots, isolation, Git state, shared resources, host version, and loaded Harness version before the first launch.
2. Record observed capability independently from authorization. Missing authorization must never make an available driver disappear. A Codex route that may select two writers needs the complete per-surface `capability_probe`; a provably sequential route records only the selected driver facts.
3. Do not cap `max_parallel_workers` at a small fixed number. The effective budget is the minimum of configured maximum, observed slots, isolation capacity, and the dependency-ready conflict-free frontier.
4. Before selection, record `observed.captured_at`, live Git facts, and `integration.batch_base_sha`. A green validator with empty `dispatchable_nodes` and `deferred_nodes` reasons `parent_state_unreconciled` or `batch_base_missing` means the live snapshot is incomplete; these are dispatch-time reasons, not an empty graph.
5. Enable scheduler fan-out only when at least two dependency-ready, nonconflicting write missions have isolated workspaces and exact authorization. Never run parallel writers in `shared_checkout`.
6. If no delegated driver is usable, select real `sequential_parent`: keep PLAN missions as `executor: runtime_worker`, record the parent-owned binding with `worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result`, and execute one mission at a time. This route uses no `spawn_subagents`; the route blocks rather than writing in `shared_checkout` when its worktree is unavailable or unauthorized.

## Default Mission Topology

1. Map one independently testable goal to one mission. Tasks inside one mission run sequentially under one writer.
2. Size each mission so its fixed per-mission overhead stays small against its useful work. Every mission pays for a worktree, a rendered handoff, result validation, an exact-head review, a serial integration, and an integration verifier rerun, so slicing past that point makes a run slower, not safer. Roughly 10-20 minutes of implementation plus focused verification is the usual landing zone, but treat it as a consequence of the overhead ratio rather than a target to hit. If the frozen scope cannot fit one bounded worker slice, split independently testable outcomes into additional missions before readiness instead of relying on a long-running child or a timeout-driven repair.
3. The parent may fan out bounded read-only exploration. Explorers report to the parent and never delegate.
4. Give every writer one explicit `write_scope` and one isolated exact-base worktree. No active writers share a branch, file ownership, or exclusive runtime resource.
5. Freeze shared APIs, schemas, and types before dependent missions launch.
6. Verify repository, branch, base HEAD, and empty `git status --porcelain` before dispatch.
7. Render `WORKER_GOAL.template.md`; attach only the host contract and result fields that mission needs.
8. Validate returned identity, changed files, scope, verifier evidence, commits, and ancestry against live Git.
9. Require one exact-head pre-integration reviewer per applicable surface for every mission. Render its bounded packet with `scripts/render_review_packet.py`; do not attach the full PLAN/RUN when that slice is sufficient. Each review returns all blocking findings in one pass and allows at most one repair-and-re-review cycle. Group related findings into one root-cause failure family before repair. If another variant of that family appears after repair, stop example-by-example patching and require one structural repair with a complete acceptance matrix or return `REFINEMENT_REQUEST` / `contract_gap`. Add same-surface reviewer fan-out only when the user requests it or a recorded high-impact risk justifies it.
10. Dispatch one planned parent-owned read-only reviewer per applicable integration surface against the exact unified integration SHA, then run one planned broad final validation suite on the fixed candidate. The unified-head review is the final synthesis; do not dispatch another same-scope review while the SHA is unchanged.

Managed runs carry no wall-time percentage target. The objective is to stop paying for the same work twice: repeated reviewer dispatches, repeated deterministic verifier runs, needless serialization, and finished work waiting on a slower sibling. Follow `references/runtime-performance.md`. Removing repetition never licenses weakening authorization, exact-head review, evidence, or final validation, and no reduction may be claimed without a comparable measured baseline.

## UI Implementation Contract

Read `references/ui-implementation-contract.md` before UI implementation or review.

- Design-system compilation mode requires `product-design-builder` and `frontend-design` together, after approved wireframes, an approved UI Design Handoff, and `Design System Need Gate: required`. It does not reopen Taste or concept generation by default.
- UI implementation may use frontend-design conformance mode only when the user explicitly selected it for a new or high-impact visual surface.
- System-conformance mode obeys the frozen PRD UI surface contract, approved `wireframes.html`, `design-system.md`, and `design-system.json`. Target-conformance mode is allowed only when the PRD gate is `not_required`; it obeys the approved immutable UI target, scope, states, responsive coverage, and tolerance recorded in the UI Design Handoff. A missing required input is a design-input delta, not local invention.
- A page-faithful target binds implementation only after the user explicitly requests faithful conformance.

## Workflow

### 1. Intake And Route

Run System Review And Route. For a running RUN, reconcile canonical state with live Git and runtime evidence before selecting a node.

If the user pauses or cancels a managed run, apply the durable control transition with `scripts/harness_transition.py`. A conversational stop is not scheduler state. Preserve active and dirty worktrees, then reconcile interrupted mission workers with `reconcile-interrupted` and stopped review workers together with `reconcile-interrupted-reviews` before any resume. Review reconciliation preserves the attempt evidence, restores lineage counters, removes ungrounded edge traversals, and leaves the run paused.

### 2. Plan Large Work

Freeze only the inputs needed by the graph: source paths and digests, scope, architecture and design boundaries, acceptance criteria, trace IDs, write/deny scopes, dependencies, resources, stop conditions, and exact verifiers. Use a bounded acyclic review-repair-review graph. Every runtime review is read-only, names one SHA, reports all blocking findings in one attempt, and has at most two total attempts: the initial review plus one repair re-review. That budget follows the mission, review surface, and root-cause lineage across PLAN revisions; a replan preserves consumed attempts instead of silently granting two more. After exhaustion, only an explicit owner decision that names the structural strategy, failure-family matrix, and exact additional review allowance may authorize one successor generation. A generic instruction to continue or finish the run is not that decision.

### 3. Pass Plan Readiness

Require frozen or explicitly `UNVALIDATED` inputs, concrete scope, one bounded worker slice per mission whose fixed overhead stays small against its useful work, a verifier for every mission, known conflicts, exact action authorization, and an executable provider for every runtime-worker node. Executability covers the whole graph, not just the next node; each node's `allowed_providers` must include a host this delivery will actually use. An unavailable provider is a blocking readiness gap unless the user explicitly accepts deferral to another host. See `references/graph-orchestration.md`.

### 4. Execute And Integrate

Select the ready frontier only after the runtime version gate is `current` or an already-active `compatible_old` wave is reaching its boundary. Follow the active adapter and bind each worker to the exact plan digest, lease, base, worktree, write scope, resources, skills, verifier, permission boundary, and completion channel. Validate results from live facts, review the exact head, repair in the original mission worktree, re-review a changed head, and integrate passing heads serially. Use `scripts/harness_step.py` to re-observe and select in one read-only call, and `scripts/validate_result.py` to validate a graph-backed payload in one; see `references/runtime-performance.md`'s Parent Turn Boundaries for what batches and what stays its own stop.

### 5. Verify Local-First

Use the verification ladder:

1. focused task and worker checks selected from parent-observed changed files using `selection.mode: "changed_files"`;
2. exact-head mission review;
3. mission integration and interaction checks;
4. fresh exact-SHA unified review;
5. one final applicable set of broad regression, browser E2E, breakpoint-by-state UI evidence, visual, and migration checks;
6. `git diff --check` and complete final-diff review.

Reuse a `session_exact` PASS only when the verifier's pass signal is the literal `exit 0`, the checkout is clean, inputs match, the command is cache-safe, and the cache is repository-external. Equivalent opted-in task and worker declarations reuse one execution even when their verifier IDs and gate attribution differ; each gate still retains its own PASS record. Integration, cross-mission, UI, and migration gates refuse reuse by default; one may opt in with `cache.deterministic_local: true` only when it is a pure local deterministic command, never for a browser capture, migration, mutable-environment smoke, or network check. Required UI artifacts live under `docs/goal/evidence/`, use lowercase SHA-256, and bind to the integration head.

### 6. Complete

New runs default to `local_only`, which completes after authorized local work, required gates, recorded evidence, and no blocker. `integration_push` additionally requires an explicitly authorized push of the verified integration head to the run branch. Landing on the default branch, PR creation, merging, deployment, archival, worktree removal, and branch deletion remain unexecuted unless separately requested.
