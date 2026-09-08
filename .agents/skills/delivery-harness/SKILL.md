---
name: delivery-harness
description: "Route engineering work to the lightest safe delivery path, then plan, authorize, execute, verify, and integrate it. Use direct parent-owned delivery when one writer and one coherent verification pass are enough. Use PLAN-v6/RUN-v11 only for work that needs durable coordination, isolated mission integration, or a bounded correction graph. Apply the runtime adapter reference for the detected host only when that managed route needs host-specific orchestration."
---

# Delivery Harness

## Purpose

Use the least ceremony that preserves safety. Keep work direct. Add PLAN/RUN state, runtime probing, workers, worktrees, and graph scheduling only when coordination requires them.

Keep upstream ownership separate:

- `product-definition-builder` owns `PRD.md`, approved low-fidelity `wireframes.html`, `architecture.md`, and `stack-decisions.md`.
- `PRD.md` owns UI structure, behavior, the exact responsive set, and the approved UI Design Handoff; `wireframes.html` makes its low-fidelity page, section, state, and per-target map inspectable, with browser layout status. `design-system-compiler`, with `frontend-design`, owns `design-system.md` and `design-system.json` only when the Design System Need Gate is `required`.
- This skill implements frozen inputs, including the Builder UX Direction and either the formal design-system pair or the approved page-faithful UI target recorded when the pair is `not_required`. It invents neither product direction nor design sources. Builder approval proves direction conformance, not usability proof; every must-have `UX-*` trace still needs objective evidence.
- `code-security-review` owns read-only review of the fixed integrated SHA; it neither remediates nor probes live targets.

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
Gitignore impact: none | update | needs owner decision
```

For UI work, inspect only `docs/design/`, a user-named design folder, and obvious in-scope images from the normal scan. Record candidate paths and hashes, then apply `references/design-input-updates.md`; only PRD-approved consequences and any required compiled design-system pair influence implementation.

Classify each task's Gitignore impact with `references/gitignore-contract.md`; it applies to both direct and managed routes.

When an existing RUN is `running`, perform the Resume Reconciliation Gate in `references/execution-state-model.md` before selecting work. Start with `python .agents/skills/delivery-harness/scripts/inspect_harness_run.py --repo-root <target-root>` for a concise manifest-versus-worktree summary, then inspect host process/session evidence separately. Canonical state, live process state, Git heads, and dirty worktrees are separate evidence; never assume `worker_running` proves a live worker.

After capability detection, apply `references/runtime-upgrades.md`. Only an old compatible runtime's active wave may finish. An incompatible or restarted runtime waits for a fresh probe, then re-orchestrates every remaining task onto the new runtime through new attempts. Provider changes require explicit replanning; never hot-upgrade a worker or silently mutate installed runtime software.

## Non-Negotiable Boundaries

These rules apply to both routes:

- Selecting this skill grants no mutation permission. Bind each state-changing action to the user's exact instruction and target.
- Preserve all 12 managed action keys: `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `archive_worker_tasks`, `remove_worktrees`, and `delete_branches`.
- Execution intent covers only applicable local setup, branch, commit, and integration actions. It does not authorize `push`. A RUN push needs explicit remote intent for its own integration branch and exact head; later `development` and `main` promotions require separate action-time authorizations.
- Never implement directly on `development` or the default branch. Promote only through `references/branch-promotion-contract.md`; never force-push. If no exact run-branch name exists, ask before branch creation; never add a fixed prefix.
- Archival, worktree removal, and branch deletion are separate actions and are never implied by completion.
- The parent owns routing, authorization, PLAN/RUN, dispatch, leases, integration, and lifecycle actions. Workers and reviewers never delegate, edit PLAN/RUN, integrate, push, or clean up.
- A managed runtime review launches only from a persisted `reserve-review-dispatch` receipt for the selector's current directive. A raw runtime spawn is unplanned work; do not accept its result or reconstruct a receipt afterward.
- Non-mission nodes reserve with `reserve-node-attempt`, execute outside the RUN lock, then record evidence with `record-node-result`; interrupted attempts become `blocked`.
- A review PASS binds one exact SHA. Any repair invalidates it.
- Preserve failed, interrupted, cancelled, dirty, and partial worktree evidence. Never reset or remove it automatically.

## Direct Route

For small work:

1. Inspect the bounded component and relevant instructions.
2. Implement with one parent writer.
3. Run the smallest focused checks that prove the change.
4. Review the complete diff and run `git diff --check`.
5. Create an authorized local commit when requested.
6. For code work, load `code-security-review` on that SHA; without one, report `UNVALIDATED`, not PASS.
7. Perform only remaining authorized Git actions.

For small UI work, add one critique-repair-recheck cycle before final review. Use rendered evidence when available; otherwise perform a text-only markup/style review and state that no visual claim was made. Obey `references/ui-implementation-contract.md`. Stop after two failed repair attempts and report the remaining gap.

For a self-contained feature inside an existing codebase, offer `/feature-dev` as an optional richer implementation loop. It does not change authorization, ownership, or verification rules.

## Managed Route

New managed work uses PLAN schema v6 and RUN schema v11. New managed work never authors a compact RUN-only artifact. Legacy compact RUN-only files remain readable for recovery, but cannot authorize new execution.

Author PLAN from `assets/templates/HARNESS_PLAN.template.md`. Generate RUN with `scripts/new_run.py` rather than hand-copying `assets/templates/MISSION_RUNBOOK.template.md`; nearly every field of a new RUN is derivable from PLAN, and the generator grants nothing. Keep checkpoints, tasks, attempts, evidence, and closeout in RUN; render `docs/tasks.md` with `scripts/render_tasks_view.py` when the run starts, after each accepted wave, and after recording a mid-run modification — each becomes its own mission (`references/execution-state-model.md`); the view is non-canonical, never edited to change state, and `--check` detects a stale view by its state fingerprint.

### Reference Routing

Read only what the current decision needs:

- `references/contract-and-traceability.md`: frozen sources, traces, permissions, and file placement.
- `references/execution-state-model.md`: PLAN/RUN creation, resume reconciliation, authorization, state transitions, and host handoff.
- `references/graph-orchestration.md`: typed graph, provider policy, retries, and correction loops.
- `references/execution-task-decomposition.md`: mission/task split rules.
- `references/parallel-mission-selection.md`: parallel write-wave selection.
- `references/runtime-adapters.md`: the shared adapter contract and per-provider launch mechanics, applied only for a large managed run after host detection.
- `references/deployment-contract.md` and `references/branch-promotion-contract.md`: post-RUN deployment and `development`-to-`main` promotion.
- `references/worktree-thread-orchestration.md`: only after the selected adapter needs workers, threads, or worktrees.
- `references/verification-gates.md`: task, integration, UI, and evidence gates.
- `references/runtime-performance.md`: bounded context, event waits, streaming review, verifier batches, and machine telemetry.
- `references/runtime-upgrades.md`: host/Harness version observation, old-runtime wave boundaries, updater/restart handling, and fresh-session recovery.
- `references/ui-implementation-contract.md`: every UI implementation or UI review.
- `references/gitignore-contract.md`: task-specific ignore classification and checks.
- `references/commit-convention.md`: before a Harness-managed commit.
- `references/design-input-updates.md` and `references/platform-archetypes.md`: only when those shapes apply.
- `references/orchestration-research-notes.md`: capability/version evidence, not routine execution.
- `references/worker-result-contract.md`: only while rendering or validating a delegated worker payload.

## Adapter Routing

Load no adapter for direct work. For a large managed run, apply `references/runtime-adapters.md` after System Review And Route: its shared adapter contract plus the one provider section for the detected host. A session not evidently Codex, Claude Code, or Pi is `generic` outright — no detection pass, no probing another runtime's CLI.

The adapter layer selects launch mechanics and provider-specific model options. It grants no authorization and does not redefine shared state, review, integration, handoff, or cleanup rules. Adding a host adds one provider section to that reference, not a new skill.

## Repository Context Contract

Discover the effective instruction chain from repository root to the selected checkout.

- Existing `AGENTS.md`, `AGENTS.override.md`, and `CLAUDE.md` files are user-owned authority. Never overwrite, merge, normalize, or silently copy them.
- On an authorized first bootstrap, run `scripts/configure_project_context.py --root <target-root>`. It creates only missing root files from `PROJECT_AGENTS.template.md` and `PROJECT_CLAUDE.template.md`; the generated files are intentionally different. The seeding flow fills the new `AGENTS.md`'s Skill Bindings table from locally observed skills with the owner's confirmation; an established file is never reopened for it.
- Codex receives the effective `AGENTS.override.md` / `AGENTS.md` chain and never receives `CLAUDE.md` as Codex instructions.
- Claude Code receives its effective `CLAUDE.md` chain plus shared `AGENTS.md` governance.
- Pi uses Pi's native per-directory priority: `AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`.
- Keep automatic context discovery enabled. A nested instruction may narrow a mission but never widen write scope or authorization.

## Default Runtime And Wave Policy

Apply this only to large plan-backed work:

1. Proactively inspect the current-session native tool surface, permission boundary, completion channel, worker slots, isolation, Git state, shared resources, host version, and loaded Harness version before the first launch.
2. Record observed capability independently from authorization. Missing authorization must never make an available driver disappear. A Codex route that may select two writers needs the complete per-surface `capability_probe`; a provably sequential route records only the selected driver facts. For a web review that must inspect the live page, add `review.required_tools: ["chrome_devtools"]` in PLAN and record the exact selected driver's fresh reviewer-session probe under `runtime_capabilities.reviewer_tools.chrome_devtools`. Parent-session access, an installed package, or a CLI flag alone is not enough. A capability-probe child is read-only discovery, never review evidence, and still needs the matching launch authorization; its result cannot update review state.
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

- Design-system compilation mode requires `design-system-compiler` and `frontend-design` together, after approved wireframes, an approved UI Design Handoff, and `Design System Need Gate: required`. It does not reopen Taste or concept generation by default.
- UI implementation may use frontend-design conformance mode only when the user explicitly selected it for a new or high-impact visual surface.
- System-conformance mode obeys the frozen PRD UI surface contract, approved `wireframes.html`, `design-system.md`, and `design-system.json`; their responsive sets must agree and contain at least two targets. Target-conformance mode is allowed only when the PRD gate is `not_required`; it obeys the approved target's scope, states, exact PRD/wireframe responsive coverage, browser layout evidence, and tolerance in the UI Design Handoff. A missing required input is a design-input delta, not local invention.
- A page-faithful target binds implementation only after the user explicitly requests faithful conformance.
- After the Final Visual Parity Loop closes, the final gate adds one page-quality pass (`references/verification-gates.md`): the skill bound to the `ui_quality_verification` slot — `impeccable` by default — runs one critique and one audit per delivered page on the exact integration head. Blocking findings enter the ordinary repair budget and never override the frozen design sources.
- These are bundled defaults. A project's Skill Bindings table in its `AGENTS.md` may bind other skills to the design, implementation, and page-quality-verification slots, plus the code-security-verification slot; the same modes, sources, and gates apply.

## Workflow

### 1. Intake And Route

Run System Review And Route. For a running RUN, reconcile canonical state with live Git and runtime evidence before selecting a node.

If the user pauses or cancels a managed run, apply the durable control transition subcommand of `scripts/harness_transition.py` — `pause`, `resume`, or `cancel`, each requiring `--source`. A conversational stop is not scheduler state. Preserve active and dirty worktrees, then reconcile interrupted mission workers with `reconcile-interrupted` and stopped review workers together with `reconcile-interrupted-reviews` before any resume. Review reconciliation preserves the attempt evidence, restores lineage counters, removes ungrounded edge traversals, and leaves the run paused.

### 2. Plan Large Work

Freeze only the inputs needed by the graph: source paths and digests, scope, architecture and design boundaries, acceptance criteria, trace IDs, write/deny scopes, dependencies, resources, stop conditions, and exact verifiers. Use a bounded acyclic review-repair-review graph. Every runtime review is read-only, names one SHA, and reports all blocking findings in one attempt. Its attempt budget and owner gate are defined in `references/graph-orchestration.md`'s Root-Cause Repair Escalation: at most the initial review plus one repair re-review, counted across the mission, review surface, and root-cause lineage over PLAN revisions, with one extra successor attempt only through `grant-review-attempts` under that section's conditions. A generic instruction to continue or finish the run is not that decision.

### 3. Pass Plan Readiness

Require frozen or explicitly `UNVALIDATED` inputs, concrete scope, a passed Mission Cohesion Gate, one bounded worker slice per mission whose fixed overhead stays small against its useful work, one atomic commit boundary per executable task, a verifier for every mission, known conflicts, exact action authorization, and an executable provider for every runtime-worker node. Reject readiness when independent outcomes are bundled only because they share files or resources, or when one task would need a catch-all commit. Executability covers the whole graph, not just the next node; each node's `allowed_providers` must include a host this delivery will actually use. An unavailable provider is a blocking readiness gap unless the user explicitly accepts deferral to another host. See `references/graph-orchestration.md`.

Apply `references/gitignore-contract.md`'s task ownership and `write_scope` gate when applicable.

### 4. Execute And Integrate

Select only after the runtime version gate. `lease-worker` copies selector-derived runtime/portable bindings, validates compatibility flags, accepts `--task-thread-id` only for `app_task`, accepts existing exact targets, and materializes new exact targets only from active wildcard grants without widening authority. Record missions with `record-worker-result` under the RUN lock; use `reject-worker-result` for stale candidates and `validate_result.py` for preflight. For non-mission nodes, reserve with `reserve-node-attempt`, execute outside the lock, then finish with `record-node-result` and evidence. Persist `reserve-review-dispatch` before launch, finish with `record-review-attempt`, review exact heads, integrate serially, and close-wave.

### 5. Verify Local-First

Use the verification ladder:

1. focused task and worker checks selected from parent-observed changed files using `selection.mode: "changed_files"`;
2. exact-head mission review;
3. mission integration and interaction checks;
4. fresh exact-SHA unified review; only non-security review may reuse byte-identical-tree evidence;
5. `code-security-review`, repair when required, and fresh review of the new SHA;
6. final broad regression, browser E2E, breakpoint-by-state UI evidence, element overlap/clipping/overflow checks, visual, and migration checks; UI-surface runs also close the Final Visual Parity Loop from `references/verification-gates.md`;
7. applicable `references/gitignore-contract.md` checks, then `git diff --check` and complete final-diff review.

Reuse a `session_exact` PASS only when the verifier's pass signal is the literal `exit 0`, the checkout is clean, inputs match, the command is cache-safe, and the cache is repository-external. Equivalent opted-in task and worker declarations reuse one execution even when their verifier IDs and gate attribution differ; each gate still retains its own PASS record. Integration, cross-mission, UI, and migration gates refuse reuse by default; one may opt in with `cache.deterministic_local: true` only when it is a pure local deterministic command, never for a browser capture, migration, mutable-environment smoke, or network check. Required UI artifacts live under `docs/goal/evidence/`, use lowercase SHA-256, and bind to the integration head.

### 6. Complete

New runs default to `local_only`, which completes after authorized local work, required gates, a fresh exact-SHA `security` review for code delivery, recorded evidence, and no blocker. `integration_push` additionally requires an authorized exact-head push to the run branch. After RUN close, apply `references/branch-promotion-contract.md`: initial delivery and later enhancements promote to `development`, pass internal exact-SHA tests there, then fast-forward the same SHA to `main` under separate authorizations and read-backs. Deployment, archival, cleanup, and activation keep their own gates.

`product-activation` follows required promotion and deployment verification; RUN grants no authority.
