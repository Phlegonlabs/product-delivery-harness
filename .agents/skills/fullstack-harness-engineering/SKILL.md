---
name: fullstack-harness-engineering
description: "Classify engineering work as small or large, then plan, execute, verify, and integrate it under explicit action authorization. This is the lightweight shared Full Stack Harness core: it owns PLAN/RUN state, traceability, scheduling contracts, local verification, and integration. Load exactly one sibling runtime adapter for Codex, Claude Code, or Pi only when runtime-specific orchestration is needed."
---

# Full-Stack Harness Engineering

## Purpose

Keep the common delivery contract small: classify the work, freeze the necessary inputs, plan only when coordination needs it, execute under exact authorization, verify locally, and integrate safely. Every request starts with the parent-only, read-only `System Review And Route` stage; runtime adapters are loaded only after that stage routes large work into the managed graph. A run starts `local_only` and ends after its authorized local work by default; only an explicit remote outcome moves it to `integration_push` on its own branch. Landing that branch on the default branch is the user's own step, outside this harness.

Keep `prd-builder` and `product-design-builder` as separate upstream skills. `prd-builder` owns `PRD.md`, `architecture.md`, and `stack-decisions.md`; `product-design-builder`, with mandatory `frontend-design`, owns `wireframes.md`, `design-system.md`, and `design-system.json` for a UI-bearing product. Reuse those artifacts instead of duplicating them. Route product, Builder UX Direction, or architecture gaps to `prd-builder`; route wireframe or design-system gaps to `product-design-builder`. An implementation agent invents neither Builder UX Direction nor design sources.

## Project Size Gate

Before invoking the planner, scheduler, worker allocator, external runtime, or PLAN/RUN workflow, perform one bounded read-only scope scan and classify the work as `small` or `large`. Planning preference can choose a stricter route, but a request to skip planning cannot override a `large` classification or a safety boundary.

Classify the work as `small` only when all of these are true:

- It has one primary outcome in one bounded component or repository area.
- One writer can finish it without parallel missions or durable handoff.
- It has no broad migration or destructive data operation.
- It does not require a frozen multi-surface contract or conditional correction graph.
- One coherent test and review pass can verify it.

Everything else is `large`. Judge size by coordination scope and blast radius, not file or line count.

```text
System Review And Route (parent-only, read-only; no task skill, PLAN/RUN, adapter, model, or worker)
  small -> direct inspect -> implement -> local verify -> review -> authorized Git actions
  large -> planner -> PLAN v5 + RUN v10 -> readiness -> sequential parent or scheduler when parallel work is useful
```

### System Review And Route

This is the first phase of every request and is owned by the parent coordinator. It is a bounded, read-only review of the user request, repository instructions, Git state, requested scope, and available upstream product/design inputs. It records the route decision in the conversation or parent checkpoint only; it does not create or edit `PLAN.md`, `RUN.md`, `tasks.md`, evidence, branches, worktrees, or other managed artifacts.

The parent must complete this stage before loading any task-specific skill, selecting a runtime adapter or model, preflighting a worker runtime, creating managed artifacts, or launching a worker. The stage never invokes an external runtime, spawns a worker, or performs a state-changing Git action. It returns at least:

```text
Project size: small | large
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Route: direct | plan-backed graph
Upstream inputs/skills: <what is present, missing, or must be routed upstream>
```

Only a `large` route may create the existing PLAN-v5/RUN-v10 artifacts and enter graph readiness. A `small` route stays parent-owned and direct, with no PLAN/RUN files. A large route with no usable agent capability selects real `sequential_parent` execution: the PLAN mission remains `executor: runtime_worker`, while RUN records a parent-owned executor/worker binding solely for lease/state validation (`worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, `completion_channel: agent_result`). This binding is not a delegated or spawned worker and requires no `spawn_subagents`; the parent remains the sole mission writer and runs one mission at a time. A parent-managed worktree is required; if it is unavailable or unauthorized, the route blocks rather than writing in `shared_checkout`. The graph starts after this stage; `System Review And Route` is not a PLAN/RUN node.

When small work touches a frontend/UI surface, insert a bounded UI review between local verify and review:

```text
... -> local verify -> UI review -> repair highest-impact failure -> recheck -> review -> ...
```

- Small work creates no PLAN/RUN files, performs no scheduler or worker-capability scan, launches no subagent by default, and does not preflight an external runtime.
- When small work touches a frontend/UI surface, run one bounded critique-repair-recheck cycle before the final review: when a rendered view or screenshot exists, critique the product's responsive verification set against its `design-system.md` (or the anti-slop guardrails in `../product-design-builder/references/design-system-guide.md` when this product has no design system), repair the single highest-impact failure, and recheck; otherwise fall back to a text-only review of the actual markup/styles against the same guardrails and record that no visual-verification claim is made. Do not retry the same failed approach more than twice; after two repair attempts, stop and report the remaining gap to the user instead of looping further.
- Small UI work obeys the UI Implementation Contract below exactly as large work does. It creates no PLAN/RUN file, so `design-system.json`, the route's screen entry in `wireframes.md`, and the exact user instruction are what bound it.
- Large work enters the workflow below. Planning does not imply parallel execution.
- Enable scheduler fan-out only when there are at least two dependency-ready, nonconflicting missions and every isolation, capacity, permission, and action gate passes.
- A ready node is executable here only when its `allowed_providers` includes the current host adapter's provider; a declared `preferred_provider` affects only which allowed provider is chosen, it does not gate executability by itself. There is no cross-host fallback: a node whose `allowed_providers` excludes the running host is not executable here. Unless the user explicitly acknowledged that deferral at Plan Readiness as a run on another host, a node no planned host can execute is a blocking readiness gap (see Pass Plan Readiness), not a routine deferral.
- If small work grows large, stop at a safe checkpoint, preserve completed edits and evidence, and plan only the remainder.

## Product Design Creation And Implementation Modes

This core bundles `product-design-builder`, but it does not bundle `frontend-design` or `feature-dev`. The latter are separate skills and require their own installation. Never fabricate their presence.

The normal UI handoff is `prd-builder` product inputs -> `product-design-builder` plus mandatory `frontend-design` creation mode -> frozen `wireframes.md`, `design-system.md`, and `design-system.json` -> Harness implementation. Any exploration artifact is non-canonical evidence; implementation begins only after the design set is frozen.

- A mission that creates or revises wireframes or the design-system pair lists both `product-design-builder` and `frontend-design` in `required_skills`. Missing or unloadable `frontend-design` blocks readiness and execution; creation mode has no fallback.
- Do not use implementation-mode `frontend-design` to compensate for a missing or partial design system. Route that gap upstream to `product-design-builder` and freeze the resolved three-file design set first.
- In a UI implementation mission, `frontend-design` may appear in `required_skills` only when the planner records the user's explicit selection for a new or high-impact visual surface. That mission runs in **frontend-design conformance mode**: it may improve the quality of execution inside the frozen wireframes and design system, but it may not choose a new aesthetic direction or invent a token, primitive, variant, component, motion pattern, or page structure at the call site.
- In conformance mode, a missing contract entry returns as a design-input delta. The worker stops at a safe boundary; the parent routes the delta through `references/design-input-updates.md`, freezes the revised package, updates the PLAN revision and digest, and only then resumes implementation. Loading `frontend-design` never turns contract drift into an allowed local exception.
- For `small`-classified work that is really "build one feature well inside an existing codebase," offer the `/feature-dev` command as a richer alternative to this core's minimal `direct inspect -> implement -> local verify -> review` route before defaulting to it. Treat its output as this core's implementation and verification steps, still subject to this core's own authorization gate before any Git action.
- Neither tool changes size classification, authorization, or verification requirements here. A `large` classification, an authorization boundary, or a required gate still applies regardless of which implementation path produced the change.

## Adapter Routing

The core is runtime-neutral. Do not load all adapters in one run.

1. For small sequential work, load no runtime adapter unless a runtime-specific action is actually required.
2. For large orchestration in a Codex host, read `../fullstack-harness-codex/SKILL.md`. Do not also read the Claude Code adapter; the Codex adapter is host-native only and executes exclusively nodes whose `allowed_providers` includes `codex`.
3. For large orchestration in a Claude Code host, read `../fullstack-harness-claude-code/SKILL.md`. Do not also read the Codex adapter; the Claude Code adapter is host-native only and executes exclusively nodes whose `allowed_providers` includes `claude_code`.
4. For large orchestration in a Pi host, read `../fullstack-harness-pi/SKILL.md`. Do not also read the Codex or Claude Code adapter; the Pi adapter executes exclusively nodes whose `allowed_providers` includes `pi` and preserves Pi's installed role/model routing.

Explicit adapter invocation still begins with this core. The adapters may select shared scripts, templates, and references from this directory; they never create a second PLAN/RUN state model.

If the System Review And Route stage finds no usable agent capability, do not load an adapter merely to imitate delegation. Continue the large plan-backed route with `sequential_parent`: keep each PLAN mission's `executor: runtime_worker`, record the parent-owned executor/worker binding in RUN solely for lease/state validation, and bind it to `worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result`. The binding is not a delegated or spawned worker, so the route does not request `spawn_subagents`; the parent executes one mission at a time under the same PLAN/RUN graph and review gates. If the required parent-managed worktree is unavailable or unauthorized, block the route rather than writing in `shared_checkout`. This is a runtime choice made after routing, not a new schema or a compact RUN-only mode.

## Repository Context Contract

During `System Review And Route`, discover and read the effective repository instruction chain from the target root through the selected checkout or worktree. Record both the shared project context and the active host's native overlay in the parent checkpoint; this read-only stage never creates or edits them.

- Existing context files are user-owned authority. Never overwrite, merge, normalize, or silently copy an established `AGENTS.md`, `CLAUDE.md`, or `AGENTS.override.md`.
- On an authorized first bootstrap, run `scripts/configure_project_context.py --root <target-root>`. It additively creates only a missing `AGENTS.md` from `assets/templates/PROJECT_AGENTS.template.md` and only a missing `CLAUDE.md` from `assets/templates/PROJECT_CLAUDE.template.md`. The generated files are intentionally different: `AGENTS.md` is shared Codex/Pi repository governance, while `CLAUDE.md` is a Claude Code overlay that imports `AGENTS.md`. When one or both files already exist, preserve them byte-for-byte.
- Codex workers receive the effective `AGENTS.override.md`/`AGENTS.md` chain plus the Codex adapter contract; do not inject `CLAUDE.md` as Codex worker instructions.
- Claude Code workers receive the effective `CLAUDE.md` chain plus shared `AGENTS.md` governance. A generated `CLAUDE.md` imports `AGENTS.md`; when an established `CLAUDE.md` does not, the worker handoff names both paths explicitly.
- Pi workers use Pi's native per-directory priority (`AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`) and receive the Pi adapter's role/model/subagent contract. When `AGENTS.md` exists, do not also inject `CLAUDE.md` into Pi.
- Read both established root files during planning to detect conflicts. Runtime additions may differ, but conflicting safety, branch, scope, authorization, or verification rules are a blocking input conflict; do not choose the more convenient file.
- Every delegated worker receives its runtime provider, its host-specific ordered context paths, and its adapter-specific launch contract in `WORKER_GOAL.template.md`, then reads those paths before any repository action.
- Keep automatic context discovery enabled. Do not launch a worker with `--no-context-files`, `-nc`, or an equivalent host option that suppresses repository instructions.
- A nested directory's context file or `AGENTS.override.md` may narrow the worker further. It never widens the mission write scope, action authorization, or Harness safety gates.

## Reference Routing

- Read `references/contract-and-traceability.md` for source handoff, contract freeze, trace IDs, permissions, and file placement.
- Read `references/execution-state-model.md` before creating or changing PLAN/RUN manifests, authorization, phases, runtime capability fields, or integration state.
- Read `references/graph-orchestration.md` for PLAN schema v5, RUN schema v10, typed nodes, bounded review-repair-review routes, provider policy, retry, or subgraph replay.
- Read `references/execution-task-decomposition.md` for flat task IDs, one bounded execution-time split, or the UI build order a design system implies.
- Read `references/parallel-mission-selection.md` before proposing a parallel write wave.
- Read `references/design-input-updates.md`, `references/platform-archetypes.md`, or `references/existing-app-refinement.md` only when those inputs or product shapes apply.
- Read `references/worktree-thread-orchestration.md` only after the selected runtime adapter requires multiple missions, subagents, threads, or worktrees.
- Read `references/verification-gates.md` for task, integration, UI, and evidence gates.
- Read `references/commit-convention.md` before a harness-managed commit.
- Read `references/orchestration-research-notes.md` for the underlying Codex/Claude Code orchestration capability facts and version gates behind this skill's guidance.
- Use `assets/templates/HARNESS_PLAN.template.md` for `PLAN.md` and `assets/templates/MISSION_RUNBOOK.template.md` for `RUN.md`. Load another template only for its named expansion:
  - `assets/templates/TASKS.template.md` for `tasks.md`, the human-readable mission/task listing view. Create it in the same step that creates `RUN.md` and regenerate it from `RUN.md` whenever mission or task state changes; it stays non-canonical.
  - `assets/templates/GOAL.template.md` for a standalone copy-ready goal prompt when a workflow needs one without creating `RUN.md`.
  - `assets/templates/WORKER_GOAL.template.md` for a mission worker's frozen launch prompt.
  - `assets/templates/E2E_VERIFICATION.template.md` only as a standalone expansion of `RUN.md`'s verification matrix when it becomes too large to scan inline.
  - `assets/templates/REFINEMENT_BACKLOG.template.md` only as a standalone expansion of `RUN.md`'s refinement backlog when it becomes too large to scan inline.

## File Budget

```text
small direct work       -> no management files
large sequential work  -> docs/goal/PLAN.md + docs/goal/RUN.md + docs/goal/tasks.md
large multi-mission    -> docs/goal/PLAN.md + docs/goal/RUN.md + docs/goal/tasks.md
binary UI evidence    -> docs/goal/evidence/** only when artifacts exist
worktree workers      -> temporary per-mission reports only while integration needs them
```

- Do not create empty directories, duplicate source documents, or one file per concern.
- Keep checkpoint, task state, verification, attempts, evidence, blockers, and closeout in `RUN.md`. `tasks.md` is a regenerated mission/task listing view only — it never becomes a second source of truth.
- New managed work never authors a compact RUN-only artifact. Legacy compact RUN-only `RUN.md` files without `PLAN.md` remain readable and validatable for compatibility and migration, but they cannot authorize new managed execution or enter the current graph; create a fresh PLAN-v5/RUN-v10 pair before continuing managed work.
- Put one canonical fenced JSON manifest in each harness artifact. Markdown tables are human views; update the manifest first.
- Use an established repository planning convention instead of adding `docs/goal/` when one exists.
- On first bootstrap of a new target repository, configure the missing root `AGENTS.md` and `CLAUDE.md` from their separate host-specific templates through `scripts/configure_project_context.py` under the Repository Context Contract. Never write either file during read-only review and never overwrite an established root context file.
- On that same first bootstrap, also seed a missing CI workflow from `assets/templates/PROJECT_CI.template.yml`. Skip it if it already exists; never overwrite established CI configuration.

## Shared Validation Tools

- `scripts/validate_harness_plan.py` validates PLAN/RUN shape, traceability, DAGs, authorization, digest consistency, closeout, RUN-v10 retained evidence, and cross-checks `integration_head_sha` against the live Git branch head.
- `scripts/select_ready_nodes.py` selects the typed PLAN-v5/RUN-v10 frontier and provider-neutral launch directives; it accepts no older graph schema.
- `scripts/configure_project_context.py` additively configures root `AGENTS.md` and `CLAUDE.md` from separate templates; it never overwrites an existing context file, and `--check` is read-only.
- `scripts/select_verifiers.py` applies `selection.mode: "changed_files"` to parent-observed changed files and never weakens integration, batch, or final gates.
- `scripts/verifier_runtime.py` may reuse a `session_exact` PASS only when the verifier's pass signal is the literal `exit 0`, the checkout is clean, the command is cache-safe, every immutable input matches, and the explicit cache root is repository-external.
- `scripts/validate_node_result.py` and `scripts/validate_worker_result.py` validate returned identity, scope, Git facts, and verifier evidence before integration.

Non-UI validation, selection, and CLI startup paths are Python-stdlib-only and deterministic. Pillow is imported lazily only when a verifier must decode binary UI evidence; if it is unavailable, report a targeted UI-evidence decoding error without preventing non-UI CLIs from starting. Every script is read-only and never mutates Git, PLAN, RUN, tasks, or worktrees. Runtime bridges are documented only in the matching adapter.

## Default Runtime And Wave Policy

Apply this to all large plan-backed work, whether the frontier ever holds more than one ready mission or processes them one at a time:

1. After `System Review And Route` and before the first edit or launch, proactively inspect the current-session native tool surface, permission boundary, worker slots, isolation, completion channel, Git state, and runtime resources.
2. Record observed capabilities under `runtime_adapter` independently from authorization. Missing authorization must never make an available driver disappear. RUN-v10 observed Codex readiness also requires the complete per-surface `capability_probe`; the validator derives `app_threads` and `subagents` from it and blocks any omission, unsupported claim, or `unobserved` surface before ready/running execution.
3. Do not cap `max_parallel_workers` at a small fixed number. Select every dependency-ready, nonconflicting mission the current frontier contains; `references/parallel-mission-selection.md`'s effective-budget formula (`min(configured maximum, observed worker slots, isolation capacity, conflict capacity)`) is what actually bounds the wave, driven by real observed capacity and the size of the mutually nonconflicting set, not by an arbitrary starting number. Set `max_parallel_workers` generously high unless the user or observed capacity sets an explicit lower limit.
4. New plan-backed files use PLAN schema v5 and RUN schema v10, the only pair that graph selection and node-result validation accept. PLAN provider policy chooses providers, provider-specific model options, and reasoning effort; the selected host adapter maps those choices to its launch surface without silent substitution. The manifest validator still reads older PLAN and RUN files; do not carry their weaker acceptance, source-publication, authorization, continuity, or evidence shapes forward.
5. Immediately after Plan Readiness, validate PLAN/RUN and select every dependency-ready, nonconflicting node the effective-budget formula allows, in deterministic order. Before that first selection, record `observed.captured_at` and `observed.git` from a live `git status` / `git rev-parse`, and set `integration.batch_base_sha` to the observed integration head. The validator does not require these — a RUN that leaves them null still reports `PASS` — but the selector then has nothing to launch: every mission and lifecycle node lands in `deferred_nodes` with `parent_state_unreconciled` or `batch_base_missing`, and `dispatchable_nodes` comes back empty. Those two kinds mutate state derived from the parent's current Git position — a mission spawns writers, a lifecycle node pushes or cleans up — so both are gated on it. `verifier`, `approval`, and `external_wait` nodes are not, because they change nothing the snapshot describes. Read those two keys, not `ready_frontier`: these are dispatch-time reasons, so the frontier list can still look full while nothing is dispatchable. Once `status` is `running`, the Resume Reconciliation Gate applies the same unreconciled state to every node and `ready_frontier` empties too. A green validator next to empty `dispatchable_nodes` means the observed snapshot was never filled in, not that the plan is wrong.
6. First read the target repository's instructions and existing branch model. When they define implementation or integration branches, preserve those exact names and topology. Otherwise the run's own `codex/<short-name>` branch is its integration branch, cut from the recorded current default-branch SHA. Default every mission, even when only one is ever ready at a time, to its own worktree created from the recorded current integration SHA. The primary integration checkout is a merge target, never a direct implementation surface. Before any mission head is integrated, require at least one read-only review round bound to that exact worktree head; a repair changes the head and requires a fresh review. Only review-passing heads may merge serially into the resolved integration branch. A no-agent route uses `sequential_parent` with the parent as the sole writer and no `spawn_subagents`; its PLAN mission stays `executor: runtime_worker` and its RUN parent-owned executor/worker binding uses `worker_runtime: parent`, `parent_managed_worktree`, and `agent_result` solely for lease/state validation. Parent-managed worktrees are required; if worktree creation is unavailable or unauthorized, block the route rather than writing in `shared_checkout`.
7. Do not silently downgrade because authorization is missing. Request the exact missing execution bundle once, pause at that boundary, record the answer, then recompute the frontier.
8. There are two landing modes. New runs default to `local_only`: implementation, PRD updates, UI changes, branch, commit, and local integration finish with verified local evidence. Only an explicit remote outcome, with `push` authorized for the exact resolved integration branch and current head, moves the run to `integration_push`; that push is where the remote run ends. `integration.branch` must contain the resolved repository branch rather than an assumed name; it is the only branch field, and every push target is built from it.

## Default Mission Topology

Apply this flat, parent-owned topology to every new large run:

1. Map one independently testable goal to one mission. A mission may contain several ordered tasks, but its tasks run sequentially under one writer and one file-ownership boundary. Do not split one goal across concurrent writers.
2. The parent may fan out bounded read-only exploration before implementation. Explorers report to the parent and never spawn or delegate further.
3. Give every write mission one explicit `write_scope`; that scope is the worker's file ownership. Every writer uses its own parent-allocated worktree. No two active writers share a checkout, branch, file ownership, or exclusive runtime resource.
4. Freeze shared APIs, schemas, and types before parallel implementation. When the shared contract itself needs edits, complete, review, and integrate that prerequisite mission first. Cut dependent mission worktrees from the resulting clean integration SHA.
5. Create every worktree from the exact recorded `batch_base_sha`. Before dispatch, verify the repository, branch/ref, HEAD, and `git status --porcelain` in that worktree. A wrong base, reused branch, or dirty checkout blocks launch.
6. Workers implement only their owned mission and never create another agent, task, branch, or worktree. All explorers, writers, and reviewers are parent-dispatched siblings.
7. Require the existing exact-head pre-integration review for each mission, then integrate passing mission heads serially into one integration branch. After the final mission integration, launch fresh parent-owned read-only reviewers against the exact unified integration SHA. A mission writer cannot review its own integration result. Review findings route to a repair mission and repeat the affected review cycle.
8. Use focused task, worker, and integration checks while work is changing. After the fresh integration reviewers pass and the candidate SHA is fixed, run one planned broad final validation suite against that exact SHA. If a repair changes the candidate or the suite fails, the prior result is stale; establish a new candidate before running the broad suite again.

The parent alone owns dispatch, leases, PLAN/RUN state, integration, and lifecycle actions. Workers and reviewers never delegate, even when their host exposes child-agent tools.

## Default Branch Policy

Apply this policy to the target repository where the skill runs only when its own instructions do not already define the implementation and integration branches. Target-repository governance wins; never replace an existing authorized flow with this one.

Each run cuts its own `codex/<short-name>` branch from the current default branch and does all its work there. That branch is the deliverable.

```text
current default-branch SHA
-> freeze and integrate shared contracts first, when needed
-> one independent worktree per selected mission
-> worker checks
-> at least one exact-head read-only review
-> repair and fresh review when needed
-> authorized serial integration into the run branch
-> fresh parent-dispatched reviewers on the unified integration head
-> one broad final validation on the fixed candidate SHA
-> if explicitly requested, authorize and push the run branch
-> the run is complete locally or at that push
```

The local loop runs end to end without touching the remote by default: work happens in mission worktrees cut from the recorded integration head (the default-branch SHA at run start), integrates into the run's own branch, and records verified local evidence. If the user separately requests a remote outcome, the parent records explicit remote intent plus an exact branch/head push grant and publishes that branch. A run is complete locally or at that authorized push.

Landing the pushed branch on the default branch is outside this harness. The user does it themselves. The harness opens no pull request, merges nothing, and deploys nothing, so none of that appears in PLAN, RUN, or the ledger. Report the pushed branch and its head SHA and stop there.

`push` requires explicit remote intent, exactly one target equal to the resolved integration branch, and `authorized_head_sha` equal to the current integration head. It is refused for a `branch:main` target or a run whose integration branch resolves to `main`; when `observed.git.default_branch` is available, that resolved default branch is refused too. A current RUN-v10 push fails closed when default-branch identity is unknown, without blocking unrelated local execution.

Under this default model, never make ordinary feature, PRD, or UI edits directly on the default branch, and never integrate a mission worktree into it locally. Each run starts from the then-current default branch, including immediately after a previous run landed.

## Execution Authorization Gate

Selecting this skill grants no implementation or lifecycle permission. Classify intent before any edit, stateful command, worker launch, commit, integration, external invocation, or cleanup:

```text
plan-only          -> inspect and produce the complete plan; stop at ready
plan-then-stop     -> produce PLAN.md/RUN.md and wait for explicit approval
plan-then-execute  -> plan completely, pass readiness, then execute
execute-ready-plan -> validate an existing ready plan, then execute
```

Treat planning, review, audit, explanation, and diagnosis as non-execution unless the user also requests implementation. Treat build, implement, fix, refactor, migrate, ship, continue, or finish as execution intent, but only for the actions actually stated or clearly necessary inside that scope.

Record each state-changing action separately:

```text
invoke_external_runtime
spawn_subagents
create_user_owned_tasks
create_local_worktrees
create_app_managed_worktrees
create_local_branches
create_local_commits
integrate_locally
push
archive_worker_tasks
remove_worktrees
delete_branches
```

- One user instruction may authorize several exact actions, but its source is recorded under every covered key; never replace them with blanket permission.
- Execution intent such as "implement this", "build it", "fix it", or "refactor it" covers only the applicable local route actions: runtime/workspace setup, branch creation, commits, and local integration. It does not authorize `push`. A separate explicit remote instruction such as "push" or "publish" must authorize `push` for exactly one resolved integration branch and the current head. Record every covered action under its own ledger key with its own source; preserve all 12 keys and leave unused entries false.
- `create_user_owned_tasks` is grouped for the same reason `spawn_subagents` is: it is the Codex host's worker-launch action. Whether worker launch needs a separate confirmation must not depend on which host the run happens to be on.
- Outer app-task selection uses `create_user_owned_tasks` and its outer worktree/branch/commit actions without requiring or preauthorizing `spawn_subagents`. RUN-v10 forbids enabled nested delegation; parent-dispatched sibling workers and reviewers use the parent's exact top-level launch grants.
- A large `sequential_parent` route is the explicit no-agent path: the parent remains the sole mission writer and does not request or record `spawn_subagents`, `create_user_owned_tasks`, or `create_app_managed_worktrees` for that route. RUN still records the parent-owned executor/worker binding for lease/state validation; it is not a delegated worker launch. Do not use `shared_checkout` for this route; if the required parent-managed worktree cannot be created or authorized, block it.
- That grouping is scoped, not general. A `push` whose target is any branch other than the resolved integration branch is not covered and needs its own authorization moment. A `push` is refused outright when the target or integration branch resolves to `main`, when an observed default branch resolves to the target, or when current v10 default-branch identity is unknown. Local execution remains available while that remote fact is missing.
- The remaining three actions — `archive_worker_tasks`, `remove_worktrees`, and `delete_branches` — are independent gates. Each needs its own distinct authorization moment and is never swept in by the execution-intent statement.
- For large, plan-backed work, every RUN-v10 execution and action scope binds the current `run_id`, mission set, PLAN revision, PLAN digest, exact targets where applicable, time, and lifecycle boundary. A plan revision or digest change invalidates the grant rather than silently carrying it forward. Small work creates no RUN file (see Project Size Gate); there, each grant is bounded instead by the exact user instruction that covers that specific action and target — never inferred from an adjacent instruction or a prior small-work grant.
- `invoke_external_runtime` does not replace spawn, workspace, branch, commit, or integration authorization.
- Archival, worktree removal, and branch deletion are independent boundaries.
- Workers and reviewers never delegate. They also never edit parent-owned PLAN/RUN state, expand their own scope, integrate, push, or clean up.

## UI Implementation Contract

When the product has a design system, a route's structure comes from `wireframes.md` and its visual layer comes from `design-system.md` plus `design-system.json`. The route is composed, not freely designed: the design system is a closed set the implementation picks from.

The frozen design system is the default implementation source. If the mission's explicitly planned `required_skills` includes `frontend-design`, the worker still follows every rule below in frontend-design conformance mode. The skill changes execution craft, not the contract or its precedence.

Every mission that writes UI code:

1. Reads `design-system.json` and the route's screen entry in `wireframes.md` before writing anything, and implements from them. Resolve the route by matching it against each screen's `Route(s):` line; a route no screen claims is a blocker (see `references/contract-and-traceability.md`'s Stop And Ask Conditions), and so is a route two screens claim.

    Those two files are the complete input. There is no mockup, screenshot, Figma frame, or exploration HTML in the normal path, and none is required: `wireframes.md` supplies the structure and `design-system.json` supplies every visual value the structure needs. A mission does not wait for a visual artifact, ask for one, or treat its absence as missing input. When a visual source does exist it is handled through `references/design-input-updates.md`, never a precondition: design inspiration is non-canonical evidence until `product-design-builder` freezes its accepted principles, while a page-faithful target is binding only after the user explicitly requests faithful conformance and its route, states, responsive scope, and tolerance are frozen.
2. Invents no visual value. Color, spacing, radius, font size, duration, easing, and distance come from tokens; primitive props come from the design system's closed variant sets. `gap="4"` and `size="md"`, never `gap="13px"` or an arbitrary utility class.
3. Reimplements no control or surface. A route composes the design system's primitives and product components, and references its registered motion variants only.
4. Follows the wireframe's structure: region responsibilities, section order, actions, exact wording or display contracts, and the labeled style direction for each visually important region.
5. Completes the states the wireframe's screen entry declares, using `design-system.json`'s `stateMatrix` as the checklist — ready, loading, empty, error, disabled, permission denied, stale, expired, long content, reduced motion, mobile reflow — with any inapplicable state explicitly marked `n/a`. Shipping the ready state alone does not close the task.
6. Stops and reports when the route needs a token, primitive, variant, motion variant, or component that `design-system.json` does not list. A missing entry is a contract change, not a task-local fix: it goes back to the design source as a delta, gets frozen, and returns through `references/design-input-updates.md`. An implementation mission never writes `design-system.md` or `design-system.json` — those are frozen contract sources, so editing them mid-task invalidates the PLAN digest and every in-flight lease, including its own.
7. Runs the project's UI contract check with this skill's `scripts/check_ui_contract.py`, reading `design-system.json` as the allowlist. It reports five rules: raw color and dimension values outside the declared `tokenSources`, inline layout styles, page-local control and surface styling outside the declared `primitiveSources`, and call-site motion values. Run it against the product's real source. A filtered `--rule` run reports only the rules it was given, so its exit code is not a contract-clean signal. Wiring this check and the remaining guardrails (responsive and state verification) into the project's verify command and CI is harness work.
8. Runs the visual check across the responsive verification set `design-system.json` carries — its `viewports` for a web target or its `sizeClasses` for a native or desktop target, in normal and reduced motion, and records the evidence per `references/verification-gates.md`. Read the set from the JSON; do not carry a default set in this skill, and never substitute web pixel breakpoints for a native platform's own model.

The contract check covers what a source scan can see. It does not prove a route used the right primitive, kept the wireframe's region responsibilities, or covered its states — those are review and evidence gates, not scanner rules. A clean check is a floor, not a pass.

A drift from the design system — a raw value, an unregistered variant, a page-local control, a skipped state — is a contract violation, not a style preference. Handle it exactly like any other contract violation here: stop at a safe boundary, report it, and fix the contract or the code. Do not accept the drift because the page looks acceptable, and do not let a passing functional test stand in for the contract check.

## Workflow

### 1. Intake And Route

Run `System Review And Route` first as the parent-only, read-only checkpoint described above. Do not load a task-specific skill, create PLAN/RUN, select an adapter/model, preflight worker capability, or spawn a worker while this checkpoint is in progress. Only its `large` result permits the next section's PLAN-backed workflow.

Inspect the repository, applicable instructions, Git state, upstream product/design sources, current behavior, and requested outcome. Record concise decisions for:

```text
Project size: small | large
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Planning depth: direct | PLAN + RUN
Host adapter: none | codex | claude_code
Workspace: shared_checkout | parent_managed_worktree | app_managed_worktree
Landing: local_only | integration_push
Verification: focused local | integration | final local
```

Do not scan every optional platform or adapter. Inspect only what the selected route needs.

When an existing `RUN.md` is `running`, pass the Resume Reconciliation Gate (`references/execution-state-model.md`) before selecting or launching any ready node: a dirty checkout may hold real work an earlier, interrupted session never verified or committed, and canonical state does not know about it yet.

### 2. Plan Large Work

Freeze relevant source paths and SHA-256 digests, functional and non-functional requirements, Builder UX Direction, architecture boundaries, frontend stack, data/integration contracts, failure states, security, observability, migration order, acceptance criteria, and exact verification commands. Preserve stable PRD, ARCH, UI, UX, DS, and TEST trace IDs. Every task acceptance row is structured as `{test_id, trace_ids, criterion}` so each planned trace has named verification coverage.

For every UI implementation mission, default `required_skills` to `[]`. Add `frontend-design` only when the user explicitly selected it for that mission's new or high-impact visual surface, and record frontend-design conformance mode in the mission objective or stop conditions. Do not infer the skill from a frontend path, a visual review requirement, or a desire to make the page look better. A mission that creates or revises design sources instead uses creation mode and must list both `product-design-builder` and `frontend-design`; listing `product-design-builder` alone is invalid.

A PLAN-v5 source may record a `staged_revision`, but that is not an executable publication. The current canonical `location`, `content_sha256`, and `source_revision` stay binding until the accepted revision is published to the canonical source location, the source becomes `frozen` or `delta_accepted`, and the PLAN revision and digest change. A ready or executing RUN never points at a product staging path.

Draw an acyclic typed graph with bounded correction handling. Before integration, send review findings back to the original mission task, thread, and worktree; after its verifier passes on a changed head, re-arm the same review node and review that head again. Bound this loop with the review node's `max_attempts`. Do not create a second repair mission from an integration branch that does not contain the reviewed head. A post-integration or batch review may route to a bounded repair node based on the reviewed integration head, then back through review; it never routes straight past the review gate. Separate independently writable frontend, backend, data, integration, review, and UI evidence work when their contracts and verifiers are distinct. Every runtime review is read-only and binds one exact reviewed SHA.

### 3. Pass Plan Readiness

Ready means the required inputs are frozen or explicitly `UNVALIDATED`, scope and denial boundaries are concrete, every task has a verifier, dependencies and resource conflicts are known, action authorization is recorded, and the next selected route is executable. Executability covers the whole graph, not just the next node: every `runtime_worker` node's `allowed_providers` must include a provider that will actually host part of this run. A node no available host can execute is a blocking readiness gap unless the user explicitly acknowledges it as deferred to a run on another host (see `references/graph-orchestration.md`). Builder approval proves direction conformance, not usability proof. Every must-have `UX-*` trace needs an objective check or planned evidence.

For `plan-then-stop`, stop after readiness. For execution intent, request only the missing exact execution actions, then continue when they are authorized.

### 4. Execute And Integrate

For small work, use one parent writer and the smallest relevant checks. For large work, select the ready frontier, then follow the chosen runtime adapter. Bind every worker to an immutable base, write/deny scope, resources, tasks, verifiers, permission boundary, and completion channel. A worker writing UI code is also bound by the UI Implementation Contract above; carry it into the worker's launch prompt with the rest of its scope.

When a design-source worker loads `product-design-builder` and `frontend-design`, its launch prompt must state creation mode, the frozen product inputs, the allowed design-source write scope, and the human direction gates. When a UI implementation worker loads only `frontend-design`, its launch prompt must state the conformance boundary and name the frozen wireframe screen, `design-system.md`, and `design-system.json` inputs. A generic instruction to "make it distinctive" is not a valid handoff in either mode.

The parent independently observes the worker head and changed files, validates the result, checks actual scope and commit ancestry, and dispatches a read-only pre-integration reviewer on that exact head. The mission cannot transition to `integrating` until the parent records a terminal `review_workers[]` PASS covering that mission and worktree head. A review worker may bind only mission worktree or integrated SHAs declared by its own review node, plus the current integration head. If the review finds a defect, repair inside the mission worktree and review the new head again. The parent then integrates passing heads serially into the resolved integration branch, runs the required post-merge integration gate, updates canonical RUN state, and recomputes the frontier. After the unified integration head is fixed, the parent dispatches fresh integration-stage reviewers before the one broad final validation. Never accept a report merely because the runtime says it completed.

### 5. Verify Local-First

Use a verification ladder:

1. Run selected task/worker checks from parent-observed changed files.
2. Before each worktree merges, complete at least one read-only review round on its exact current head. Any repair invalidates that review.
3. After real integration into the resolved integration branch, run the mission integration gate and the relevant batch and interaction gates.
4. Converge local deterministic checks and exact-SHA runtime review. A repair invalidates only affected layers.
5. After those loops close, run broad regression, browser E2E, breakpoint-by-state UI evidence, visual review, and migration checks that apply to the final integration head.
6. Run `git diff --check` and review the complete final diff.

A clean, cache-safe focused task or worker verifier may reuse only an exact same-attempt `session_exact` PASS, bound to its `attempt_id` and `lease_id`, from a repository-external cache. Do not cache integration, cross-mission, UI, or migration gates; that ban is enforced both when the PLAN declares the verifier and again at run time in `verifier_runtime.py`. RUN-v10 `verifier_executions` is append-only and parent-owned: workers return candidate results, but only the parent validates and appends the normalized verifier, execution context, key document/digests, cache decision, output hashes, metrics, and retained evidence paths. Required UI artifacts live under `docs/goal/evidence/`, record lowercase SHA-256, and bind to the exact integration head.

Automated current-head E2E may replace only an equivalent duplicate manual smoke. Record `not required - covered by current-head E2E`.

Local-only work stops after its authorized worktree commits are reviewed and integrated into the resolved integration branch, with local evidence recorded. It does not wait for CI and never changes the default branch.

### 6. Complete

A local-only run completes when authorized local mutations are finished, all applicable local gates pass on the integration head, no blocker remains, and RUN records evidence, changed files, commits, and residual risk.

An `integration_push` run completes when the verified integration head reaches the run's own branch and RUN records that branch, the pushed head SHA, and the local evidence behind it. The pushed head SHA is a parent-attested record: the validators check it for internal consistency and against the local branch head, but the push itself is observed by the parent, not provable by the scripts. `local_only` is the default and completes with the same verified local evidence without remote contact. Neither mode waits for a PR, for CI, or for a deploy.

Finish by checking final Git status, reporting what changed, what was verified, the branch and head SHA that were pushed, and every intentionally unexecuted lifecycle action. Never claim a push, archival, or cleanup action that did not happen.
