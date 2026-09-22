---
name: delivery-harness
description: "Route engineering work to the lightest safe delivery path, then plan, authorize, execute, verify, and integrate it. Use direct parent-owned delivery when one writer and one coherent verification pass are enough. Use PLAN-v6/RUN-v11 only for work that needs durable coordination, isolated mission integration, or a bounded correction graph. Apply the general runtime adapter contract only when that managed route needs native orchestration."
---

# Delivery Harness

For scripts and bindings, read `references/installed-commands.md`.

Every invocation uses `references/document-sync-contract.md`. Accepted enhancements follow `references/bounded-enhancement.md`; acceptance follows `references/delivery-acceptance-contract.md`.

Project `AGENTS.md` also requires Repository Change Checkpoints at task start, significant change boundaries and completion/handoff, even outside Harness. Record meaningful local Git and working-tree changes in the relevant Epic without creating PLAN/RUN or a background watcher. Read-only tasks report proposed records without writing. Implement from canonical English PRD/architecture; Chinese review copies are not implementation sources.

## Purpose

Keep direct work simple; add PLAN/RUN orchestration only when coordination requires it.

Keep upstream ownership separate:

- `product-definition-builder` owns the approved Product Definition revision across `PRD.md`, `architecture.md`, and `stack-decisions.md`, including complete frontend and backend architecture and technology decisions.
- `ui-design-builder` owns `docs/design/ui-design.md`, UI Design Intake, approved `wireframes.html`, Style Integration, Impeccable review, PRD-bound scores, Visual Approval, and the HiFi target. `design-system-compiler`, with `frontend-design`, owns the design-system pair only when the Design System Need Gate is `required`.
- This skill implements approved product/stack sources, `ui-design.md`, copy-frozen `wireframes.html`, and the active visual source. It preserves approved copy and dynamic display contracts. UI approval proves direction conformance, not representative-user usability; every must-have `UX-*` trace still needs objective evidence. `Recommended` and `Provisional` technology rows are proposals, not scaffold authority. This skill invents no product, copy, stack, or design decisions.
- `code-security-review` owns read-only review of the fixed integrated SHA; it neither remediates nor probes live targets.

## Project Size Gate

Before loading task-specific tooling, run one bounded parent-only scope scan.

Classify work as `small` when one parent writer can own one bounded outcome in one checkout and verify it with one coherent local sequence. A high file count, language count, test duration, or reasoning difficulty does not make work `large` by itself.

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

Small work creates no PLAN/RUN files, scheduler state, worker-capability inventory, or delegated worker by default. Load no runtime adapter unless the direct task actually needs native delegation. If small work grows large, preserve the current diff and evidence, then plan only the remainder.

### System Review And Route

Complete this checkpoint before loading any task-specific skill. Read the request, repository instructions, Git state, requested scope, and relevant frozen product/design inputs. Do not create or edit `PLAN.md`, `RUN.md`, `tasks.md`, branches, worktrees, evidence, or implementation files during this checkpoint.

Record:

```text
Project size: small | large
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Route: direct | plan-backed graph
Host adapter: none | general (observed host identity or generic)
RUN landing: local_only
Post-archive publication: none | exact candidate branch
Upstream inputs: present | missing | needs owner decision
Gitignore impact: none | update | needs owner decision
```

For UI work, inspect only `docs/design/`, a user-named design folder, and obvious in-scope images from the normal scan. Record candidate paths and hashes, then apply `references/design-input-updates.md`; only PRD-approved consequences and any required compiled design-system pair influence implementation.

Classify each task's Gitignore impact with `references/gitignore-contract.md`; it applies to both direct and managed routes.

When an existing RUN is `running`, perform the Resume Reconciliation Gate in `references/execution-state-model.md` before selecting work. Start with `python "<delivery-harness-skill-root>/scripts/inspect_harness_run.py" --repo-root <target-root>` for a concise manifest-versus-worktree summary, then inspect host process/session evidence separately. Canonical state, live process state, Git heads, and dirty worktrees are separate evidence; never assume `worker_running` proves a live worker.

After capability detection, apply `references/runtime-upgrades.md`. Only an old compatible runtime's active wave may finish. An incompatible or restarted runtime waits for a fresh probe, then re-orchestrates every remaining task onto the new runtime through new attempts. Provider changes require explicit replanning; never hot-upgrade a worker or silently mutate installed runtime software.

## Non-Negotiable Boundaries

These rules apply to both routes:

- Selecting this skill grants no mutation permission. Bind each state-changing action to the user's exact instruction and target.
- Preserve all 12 managed action keys: `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `archive_worker_tasks`, `remove_worktrees`, and `delete_branches`.
- Execution intent covers only applicable local setup, branch, commit, and integration actions; it does not authorize `push`. Harness 0.38 RUNs stay `local_only` with `push` false. Publishing A to the run branch and promoting A to `main` are separate post-RUN actions with separate authorization.
- This workflow is main-only. Never implement directly on the default branch, and never use the retired `development` name as a run or release branch. Promote only through `references/branch-promotion-contract.md`; never force-push. If no exact run-branch name exists, ask before branch creation; never add a fixed prefix.
- Archival, worktree removal, and branch deletion are separate actions and are never implied by completion.
- The parent owns routing, authorization, PLAN/RUN, dispatch, leases, integration, and lifecycle actions. Workers and reviewers never delegate, edit PLAN/RUN, integrate, push, or clean up.
- A managed runtime review launches only from a persisted `reserve-review-dispatch` receipt for the selector's current directive. A raw runtime spawn is unplanned work; do not accept its result or reconstruct a receipt afterward.
- Non-mission nodes reserve with `reserve-node-attempt`, execute outside the RUN lock, then record evidence with `record-node-result`; interrupted attempts become `blocked`.
- A review PASS binds one exact SHA. Any repair invalidates it.
- Preserve failed, interrupted, cancelled, dirty, and partial worktree evidence. Never reset or remove it automatically.

## Direct Route

For small work:

1. Inspect the bounded component and relevant instructions.
2. When work consumes a package produced by `product-definition-builder`, verify its Product Definition Approval and Stack Decision Checkpoint; then implement with one parent writer.
3. Run the smallest focused checks, including security tests, that prove the change.
4. Review the complete diff and run `git diff --check`.
5. Create an authorized local commit when requested.
6. For code work, load `code-security-review` on that SHA; without one, report `UNVALIDATED`, not PASS.
7. Perform only remaining authorized Git actions.

For small UI work, add one critique-repair-recheck cycle before final review. Use rendered evidence when available; otherwise perform a text-only markup/style review and state that no visual claim was made. Obey `references/ui-implementation-contract.md`, including rule-8 UI-impact classification and same-change doc updates. Stop after two failed repair attempts and report the remaining gap.

Optional `/feature-dev` exploration does not change authorization, ownership or verification.

## Managed Route

New managed work uses PLAN schema v6 and RUN schema v11. New managed work never authors a compact RUN-only artifact. Legacy compact RUN-only files remain readable for recovery, but cannot authorize new execution.

Author PLAN from `assets/templates/HARNESS_PLAN.template.md`. Generate RUN with `scripts/new_run.py`; it derives initial state and grants nothing. RUN owns checkpoints, tasks, attempts, evidence, and closeout. With `--repo-root`, `new_run.py --out` and guarded checkpoint transitions automatically render `docs/tasks.md` from its declared coordination path. This non-canonical view preserves its Update Log. A refresh failure leaves successful RUN state intact; use `scripts/render_tasks_view.py` to repair or `--check` it. Read `references/execution-state-model.md` for the checkpoint set, source guards, and formal revision procedure.

### Reference Routing

Read only what the current decision needs:

- `references/contract-and-traceability.md`: frozen sources, traces, permissions, and file placement.
- `references/execution-state-model.md`: PLAN/RUN creation, resume reconciliation, authorization, state transitions, and host handoff.
- `references/graph-orchestration.md`: typed graph, provider policy, retries, and correction loops.
- `references/execution-task-decomposition.md`: mission/task split rules.
- `references/parallel-mission-selection.md`: parallel write-wave selection.
- `references/runtime-adapters.md`: the general capability and dispatch contract, applied only when managed execution needs it.
- `references/deployment-contract.md` and `references/branch-promotion-contract.md`: candidate-environment verification and post-RUN exact-SHA promotion to `main`.
- `references/worktree-thread-orchestration.md`: only after the selected adapter needs workers, threads, or worktrees.
- `references/verification-gates.md`: task, integration, UI, and evidence gates.
- `references/runtime-performance.md`: bounded context, event waits, streaming review, verifier batches, and machine telemetry.
- `references/runtime-upgrades.md`: host/Harness version observation, old-runtime wave boundaries, updater/restart handling, and fresh-session recovery.
- Runtime trust/publication: see `references/runtime-trust.md` and `trusted-host-publication.md`.
- `references/ui-implementation-contract.md`: every UI implementation or UI review.
- `references/gitignore-contract.md`: task-specific ignore classification and checks.
- `references/commit-convention.md`: before a Harness-managed commit.
- `references/design-input-updates.md` and `references/platform-archetypes.md`: only when those shapes apply.
- `references/orchestration-research-notes.md`: capability/version evidence, not routine execution.
- `references/worker-result-contract.md`: only while rendering or validating a delegated worker payload.

## Adapter Routing

Load no adapter for direct work. For managed execution, apply `references/runtime-adapters.md`: one capability contract for every host. The agent maps current native tools to that contract automatically, records observed capabilities and the actual host identity (or `generic` when unknown), and never probes another runtime as a substitute.

The adapter layer owns no shared state, authorization, review, integration, handoff or cleanup. Adding a host needs no provider section, fixed model defaults, launch script or schema change.

## Repository Context Contract

Discover the effective instruction chain from repository root to the selected checkout.

- Existing `AGENTS.md`, `AGENTS.override.md`, and `CLAUDE.md` files are user-owned authority. Never overwrite, merge, normalize, or silently copy them.
- On an authorized first bootstrap, run `scripts/configure_project_context.py --root <target-root>`. It creates only missing root files from `PROJECT_AGENTS.template.md` and `PROJECT_CLAUDE.template.md`; the generated files are intentionally different. Resolve new Skill Bindings from observed skills with owner confirmation; preserve established context files.
- Follow the current host's effective instruction precedence; do not guess it from a provider name or inject another host's instructions.
- Keep automatic context discovery enabled. A nested instruction may narrow a mission but never widen write scope or authorization.

## Default Runtime And Wave Policy

Apply this only to large plan-backed work:

1. Proactively inspect the current-session native tool surface, permission boundary, completion channel, worker slots, isolation, Git state, shared resources, host version, and loaded Harness version before the first launch.
2. Record observed capability independently from authorization. Missing authorization must never make an available driver disappear. Every advertised delegated driver needs observed `capability_probe` facts; unrelated surfaces need no inventory. For a web review that must inspect the live page, add `review.required_tools: ["chrome_devtools"]` in PLAN and record the exact selected driver's fresh reviewer-session probe under `runtime_capabilities.reviewer_tools.chrome_devtools`. Parent-session access, an installed package, or a CLI flag alone is not enough. A capability-probe child is read-only discovery, never review evidence, and still needs the matching launch authorization; its result cannot update review state.
3. Do not cap `max_parallel_workers` at a small fixed number. The effective budget is the minimum of configured maximum, observed slots, isolation capacity, and the dependency-ready conflict-free frontier.
4. Before selection, record `observed.captured_at`, live Git facts, and `integration.batch_base_sha`. A green validator with empty `dispatchable_nodes` and `deferred_nodes` reasons `parent_state_unreconciled` or `batch_base_missing` means the live snapshot is incomplete; these are dispatch-time reasons, not an empty graph.
5. Enable scheduler fan-out only when at least two dependency-ready, nonconflicting write missions have isolated workspaces and exact authorization. Never run parallel writers in `shared_checkout`.
6. If no delegated driver is usable, select real `sequential_parent` per `references/execution-state-model.md`'s Sequential Parent Route and execute one mission at a time. An independent runtime-review node stays blocked until a fresh eligible reviewer driver, a same-repository host handoff, or another allowed host is available.

## Default Mission Topology

1. Map one independently testable goal to one mission: specifically, one product or contract outcome. A mission is not a phase label, subsystem backlog, or catch-all for everything touching one router. Blog, Settings, and user administration are separate missions when each can be reviewed and verified independently, even when they share auth, schema, navigation, or migration work.
2. Pass the Mission Cohesion Gate in `references/execution-task-decomposition.md` before readiness. Split a mission when its objective joins independently valuable outcomes, spans separate product surfaces or domain capabilities, needs unrelated verifier families, or hides more than one commit-sized outcome inside a task. Shared files, likely merge conflicts, or serialized resources are not reasons to bundle independent outcomes: freeze a shared foundation first, then represent ordering and conflicts with dependency and resource edges. Combine work only when separating it would create an unverifiable or nonfunctional half-state.
3. Plan tasks as ordered atomic commit boundaries. Complete one task's implementation and focused verifier, create its authorized task commit, and only then begin the next task. One commit cannot satisfy multiple tasks. A review repair is a separate atomic follow-up commit attributed to exactly one task; it does not make the original task broader.
4. Size each mission so its fixed per-mission overhead stays small against its useful work. Every mission pays for a worktree, a rendered handoff, result validation, an exact-head review, a serial integration, and an integration verifier rerun, so slicing past that point makes a run slower, not safer. Roughly 10-20 minutes of implementation plus focused verification is the upper shape of a normal bounded slice, not a target to fill; prefer the smaller cohesive mission when two candidate splits both preserve independent verification. If the frozen scope cannot fit one bounded worker slice, split independently testable outcomes into additional missions before readiness instead of relying on a long-running child or a timeout-driven repair.
5. The parent may fan out bounded read-only exploration. Explorers report to the parent and never delegate.
6. Give every writer one explicit `write_scope` and one isolated exact-base worktree. No active writers share a branch, file ownership, or exclusive runtime resource.
7. Freeze shared APIs, schemas, and types before dependent missions launch.
8. Verify repository, branch, base HEAD, and empty `git status --porcelain` before dispatch.
9. Render `WORKER_GOAL.template.md`; attach only the host contract and result fields that mission needs.
10. Validate returned identity, changed files, scope, verifier evidence, atomic task-commit attribution, commit order, and ancestry against live Git.
11. Require one exact-head pre-integration reviewer per applicable surface for every mission. Render its bounded packet with `scripts/render_review_packet.py`; do not attach the full PLAN/RUN when that slice is sufficient. Each review returns all blocking findings in one pass and allows at most one repair-and-re-review cycle. Group related findings into one root-cause failure family before repair. If another variant of that family appears after repair, stop example-by-example patching and require one structural repair with a complete acceptance matrix or return `REFINEMENT_REQUEST` / `contract_gap`. Add same-surface reviewer fan-out only when the user requests it or a recorded high-impact risk justifies it. A web `visual` review declares `required_tools: ["chrome_devtools"]`. A `frontend_code` review declares it when DOM state, console, network, runtime JavaScript, accessibility, or rendered behavior is part of its evidence. Backend-only and source-only reviews do not acquire a browser requirement. The selector defers a required tool as `reviewer_tool_unobserved:<tool>` or `reviewer_tool_unavailable:<tool>`; never replace the missing reviewer tool with the parent's browser session.
12. Dispatch one planned parent-owned read-only reviewer per integration surface on the unified SHA. Every new code-delivery PLAN adds a fresh sibling `security` review over all missions with the `code_security_verification` binding; it never uses the tree-identity skip. For other review, do not dispatch another same-scope review on an unchanged SHA; a byte-identical skip records both tree SHAs.
13. After those reviews pass, run one planned broad final validation suite. A security repair changes the SHA and invalidates its review and downstream gates.

Managed runs carry no wall-time percentage target. The objective is to stop paying for the same work twice. Follow `references/runtime-performance.md`; removing repetition never weakens authorization, exact-head review, evidence, or final validation.

## UI Implementation Contract

Read `references/ui-implementation-contract.md` before UI implementation or review.

- `design-system-compiler` owns compilation after approved Product Definition, UI design, Copy Freeze, wireframes, HiFi, and a `required` Design System Need Gate. Do not claim another skill exposes compilation mode.
- UI implementation runs the bound frontend author under this Harness's conformance contract. Do not claim that skill defines conformance mode or reopen Style Integration.
- System-conformance mode obeys the frozen PRD UI Surface Contract, approved `ui-design.md`, `wireframes.html`, `design-system.md`, and `design-system.json`; their responsive sets must agree and meet the declared platform minimum. Target-conformance mode is allowed only when the UI design gate is `not_required`; it obeys the approved target's scope, states, exact PRD/wireframe responsive coverage, browser evidence, and tolerance in `ui-design.md`. A missing required input is a design-input delta, not local invention.
- A page-faithful target binds implementation only after the user explicitly requests faithful conformance.
- After the Final Visual Parity Loop, one read-only page-quality pass (`references/verification-gates.md`) runs on the exact head. Impeccable is not the default; a separately authorized run may add UI evidence, with its subagents, browser/server, snapshot, and download side effects disclosed. It never fills a Harness read-only reviewer node.
- Bundled defaults exist only for bundled skills. A project's owner-confirmed Skill Bindings table may bind installed external visual-direction, frontend-authoring, or UI-quality tools after their full trees and side effects are checked; an unresolved or incompatible slot blocks its dependent node.

## Workflow

### 1. Intake And Route

Run System Review And Route. For a running RUN, reconcile canonical state with live Git and runtime evidence before selecting a node.

If the user pauses or cancels a managed run, apply the durable control transition subcommand of `scripts/harness_transition.py` — `pause`, `resume`, or `cancel`, each requiring `--source`. A conversational stop is not scheduler state. Preserve active and dirty worktrees, then reconcile interrupted mission workers with `reconcile-interrupted` and stopped review workers together with `reconcile-interrupted-reviews` before any resume. Review reconciliation preserves the attempt evidence, restores lineage counters, removes ungrounded edge traversals, and leaves the run paused.

### 2. Plan Large Work

Freeze only approved inputs needed by the graph: Product Definition revision, Stack Decision Checkpoint, source paths and digests, scope, architecture and design boundaries, acceptance criteria, trace IDs, write/deny scopes, dependencies, resources, stop conditions, and exact verifiers. Harness 0.38 requires one canonical frozen PRD, architecture, and stack source for every plan and always runs the full sibling Product package checker with `--repo-root`; UI plans also require the approved UI, wireframe, HiFi target, and conditional design-system authority. Use the bounded review-repair graph and owner-attempt rules. A generic instruction to continue grants no new attempt.

### 3. Pass Plan Readiness

Require frozen or explicitly `UNVALIDATED` inputs, concrete scope, a passed Mission Cohesion Gate, one bounded worker slice per mission whose fixed overhead stays small against its useful work, one atomic commit boundary per executable task, a verifier for every mission, known conflicts, exact action authorization, and an executable provider for every runtime-worker node. Reject readiness when independent outcomes are bundled only because they share files or resources, or when one task would need a catch-all commit. Executability covers the whole graph, not just the next node; each node's `allowed_providers` must include a host this delivery will actually use. An unavailable provider is a blocking readiness gap unless the user explicitly accepts deferral to another host. See `references/graph-orchestration.md`.

Apply `references/gitignore-contract.md`'s task ownership and `write_scope` gate when applicable.

### 4. Execute And Integrate

Full-stack slices and reproducible E2E follow `references/delivery-acceptance-contract.md`.

After the version gate, run `python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan docs/goal/PLAN.md --run docs/goal/RUN.md --repo-root <absolute-root> record-observation`. Global flags precede the subcommand. It binds the host, PLAN revision, and digest, plus runtime and RepoDigest for explicitly selected containers; `--probe-sandboxes` is diagnostic only. `lease-worker` copies selector bindings and materializes exact targets only from active wildcard grants. Record through guarded transitions, review exact heads, integrate serially, and close the wave.

### 5. Verify Local-First

New PLANs explicitly select `execution.isolation: "host"` for local build/lint/test. Host commands use current user permissions, not sandbox confinement. Containers remain optional with no fallback. See `references/verification-gates.md` for mode, source/Git guards, and evidence requirements.

Use the verification ladder:

1. focused task and worker checks selected from parent-observed changed files using `selection.mode: "changed_files"`;
2. exact-head mission review;
3. mission integration and interaction checks;
4. fresh exact-SHA unified review; only non-security review may reuse byte-identical-tree evidence;
5. `code-security-review`, repair when required, and fresh review of the new SHA;
6. final broad regression, browser E2E, breakpoint-by-state UI evidence, element overlap/clipping/overflow checks, visual, and migration checks; UI-surface runs also close the Final Visual Parity Loop from `references/verification-gates.md`;
7. applicable `references/gitignore-contract.md` checks, then `git diff --check` and complete final-diff review.

Host verifiers run fresh and serially per runner. Container `session_exact` reuse requires `exit 0`, clean matching inputs, read-only task/worker declarations, and `cache.deterministic_local: true` within one runner batch. Every consumer rechecks guards and runtime/image identity and retains its reservation, evidence, and origin. Keep request/result artifacts repository-external; no disk cache is used. Integration, cross-mission, final, browser, migration, mutable-environment, and network checks execute fresh. UI artifacts under `docs/goal/evidence/` use lowercase SHA-256 and bind to the integration head.

### 6. Complete

Harness 0.38 RUNs close `local_only` at C after all gates and security pass. `archive_run.py --anchor-out <external path>` moves coordination, writes `ARCHIVE_RECEIPT.json` plus its immutable external anchor, and rolls back failure; commit only bookkeeping as A and reverify it. A current RUN never pushes. Under a new instruction, `push_archived_candidate.py --archive-anchor <path>` keeps request, attempt, receipt, and trusted-host evidence external, binds the canonical URL plus machine-policy ID/hash/principal and OS-managed verifier digest, returns a URL-only no-force argv, and never invokes `git push`; a trusted host reloads and revalidates the request with sanitized config, signs evidence, publishes, and recovery verifies it before reading A back. Candidate gates and separately authorized exact-A `main` promotion follow.

`product-activation` preparation requires a fixed SHA and separate authorization. Readiness, measurement handoff, outcome review, and SEO require promotion and production verification; no RUN grant authorizes them.
