---
name: fullstack-harness-engineering
description: "Classify engineering work as small or large, then plan, execute, verify, and integrate it under explicit action authorization. This is the lightweight shared Full Stack Harness core: it owns PLAN/RUN state, traceability, scheduling contracts, local verification, and integration. Load exactly one sibling runtime adapter for Codex or Claude Code only when runtime-specific orchestration is needed, and load the GitHub landing adapter only when remote landing is requested."
---

# Full-Stack Harness Engineering

## Purpose

Keep the common delivery contract small: classify the work, freeze the necessary inputs, plan only when coordination needs it, execute under exact authorization, verify locally, and integrate safely. Runtime launch mechanics and remote landing are separate adapters so ordinary work does not load every Codex, Claude Code, GitHub, CI, review, and deployment rule.

Keep `prd-builder` and `design-package-builder` as separate upstream skills. Reuse their artifacts instead of duplicating them. If product, Builder UX Direction, architecture, or design evidence is missing, route to the matching skill, use an explicitly authorized assumption, or record the gap as `UNVALIDATED`. An implementation agent does not invent Builder UX Direction.

## Project Size Gate

Before invoking the planner, scheduler, worker allocator, external runtime, or PLAN/RUN workflow, perform one bounded read-only scope scan and classify the work as `small` or `large`. Planning preference can choose a stricter route, but a request to skip planning cannot override a `large` classification or a safety boundary.

Classify the work as `small` only when all of these are true:

- It has one primary outcome in one bounded component or repository area.
- One writer can finish it without parallel missions or durable handoff.
- It has no broad migration, multi-environment release, destructive data operation, or independently staged deployment.
- It does not require a frozen multi-surface contract or conditional correction graph.
- One coherent test and review pass can verify it.

Everything else is `large`. Judge size by coordination scope and blast radius, not file or line count.

```text
small -> direct inspect -> implement -> local verify -> review -> authorized Git actions
large -> planner -> readiness -> sequential execution or scheduler when parallel work is useful
```

When small work touches a frontend/UI surface, insert a bounded UI review between local verify and review:

```text
... -> local verify -> UI review -> repair highest-impact failure -> recheck -> review -> ...
```

- Small work creates no PLAN/RUN files, performs no scheduler or worker-capability scan, launches no subagent by default, and does not preflight an external runtime.
- When small work touches a frontend/UI surface, run one bounded critique-repair-recheck cycle before the final review, the same shape `design-package-builder` already uses for its own package (`references/output-contract.md`'s TEST-VIS-011/012): when a rendered view or screenshot exists, critique required breakpoints against the product's `design-package-builder` output (or the anti-slop guardrails in `../design-package-builder/references/visual-decision-guide.md` when no design package exists for this product), repair the single highest-impact failure, and recheck; otherwise fall back to a text-only review of the actual markup/styles against the same guardrails and record that no visual-verification claim is made. Do not retry the same failed approach more than twice; after two repair attempts, stop and report the remaining gap to the user instead of looping further.
- Large work enters the workflow below. Planning does not imply parallel execution.
- Enable scheduler fan-out only when there are at least two dependency-ready, nonconflicting missions and every isolation, capacity, permission, and action gate passes.
- A ready node is executable here only when its `allowed_providers` includes the current host adapter's provider; a declared `preferred_provider` affects only which allowed provider is chosen, it does not gate executability by itself. There is no cross-host fallback: a node whose `allowed_providers` excludes the running host is simply not executable here and is reported blocked on provider mismatch.
- If small work grows large, stop at a safe checkpoint, preserve completed edits and evidence, and plan only the remainder.

## Optional External Skill Assist

This core does not bundle `frontend-design` or `feature-dev`. Both are separate Apache-2.0 plugins from the `claude-plugins-official` marketplace and require their own install (`claude plugin install frontend-design@claude-plugins-official`, `claude plugin install feature-dev@claude-plugins-official`). Before offering either, confirm it is actually loaded in the current session; if it is not installed, say so and continue on this core's own path instead of fabricating its presence.

- Before writing frontend/UI code with no adequate `design-package-builder` output to follow, or when the user wants unusually distinctive visual execution beyond what an existing design package specifies, offer the `frontend-design` skill for that implementation step. Use it only after an explicit yes, and only for the visual/aesthetic execution itself; it does not replace this core's PLAN/RUN state, trace IDs, or authorization ledger.
- For `small`-classified work that is really "build one feature well inside an existing codebase," offer the `/feature-dev` command as a richer alternative to this core's minimal `direct inspect -> implement -> local verify -> review` route before defaulting to it. Treat its output as this core's implementation and verification steps, still subject to this core's own authorization gate before any Git action.
- Neither tool changes size classification, authorization, or verification requirements here. A `large` classification, an authorization boundary, or a required gate still applies regardless of which implementation path produced the change.

## Adapter Routing

The core is runtime-neutral. Do not load all adapters in one run.

1. For small sequential work, load no runtime adapter unless a runtime-specific action is actually required.
2. For large orchestration in a Codex host, read `../fullstack-harness-codex/SKILL.md`. Do not also read the Claude Code adapter; the Codex adapter is host-native only and executes exclusively nodes whose `allowed_providers` includes `codex`.
3. For large orchestration in a Claude Code host, read `../fullstack-harness-claude-code/SKILL.md`. Do not also read the Codex adapter; the Claude Code adapter is host-native only and executes exclusively nodes whose `allowed_providers` includes `claude_code`.
4. Read `../fullstack-harness-github-landing/SKILL.md` only when the requested outcome includes push, PR creation, GitHub CI, GitHub review, merge, or remote repository configuration. Local branch and commit work alone does not load it.

Explicit adapter invocation still begins with this core. The adapters may select shared scripts, templates, and references from this directory; they never create a second PLAN/RUN state model.

## Reference Routing

- Read `references/contract-and-traceability.md` for source handoff, contract freeze, trace IDs, permissions, and file placement.
- Read `references/execution-state-model.md` before creating or changing PLAN/RUN manifests, authorization, phases, runtime capability fields, landing, deployment, or integration state.
- Read `references/graph-orchestration.md` for PLAN schema v4, RUN schema v8 or v9, typed nodes, conditional routes, provider policy, retry, or subgraph replay.
- Read `references/execution-task-decomposition.md` for flat task IDs or one bounded execution-time split.
- Read `references/parallel-mission-selection.md` before proposing a parallel write wave.
- Read `references/design-input-updates.md`, `references/platform-archetypes.md`, or `references/existing-app-refinement.md` only when those inputs or product shapes apply.
- Read `references/worktree-thread-orchestration.md` only after the selected runtime adapter requires multiple missions, subagents, threads, or worktrees.
- Read `references/verification-gates.md` for task, integration, UI, release, and evidence gates.
- Read `references/cloudflare-deployment-lifecycle.md` only for Cloudflare delivery.
- Read `references/commit-convention.md` before a harness-managed commit.
- Read `references/orchestration-research-notes.md` for the underlying Codex/Claude Code orchestration capability facts, version gates, and GitHub review/merge mechanics behind this skill's guidance, including the Codex Cloud connection requirement and the `@codex review` manual trigger the GitHub landing adapter depends on.
- Use `assets/templates/HARNESS_PLAN.template.md` for `PLAN.md` and `assets/templates/MISSION_RUNBOOK.template.md` for `RUN.md`. Load another template only for its named expansion:
  - `assets/templates/TASKS.template.md` for `tasks.md`, a non-canonical mission/task listing view regenerated from `RUN.md` whenever a RUN.md exists.
  - `assets/templates/GOAL.template.md` for a standalone copy-ready goal prompt when a workflow needs one without creating `RUN.md`.
  - `assets/templates/WORKER_GOAL.template.md` for a mission worker's frozen launch prompt.
  - `assets/templates/PULL_REQUEST.template.md` as the PR body base when the GitHub landing adapter creates a pull request.
  - `assets/templates/E2E_VERIFICATION.template.md` only as a standalone expansion of `RUN.md`'s verification matrix when it becomes too large to scan inline.
  - `assets/templates/REFINEMENT_BACKLOG.template.md` only as a standalone expansion of `RUN.md`'s refinement backlog when it becomes too large to scan inline.

## File Budget

```text
small direct work      -> no management files
large sequential work -> docs/goal/RUN.md (+ optional docs/goal/tasks.md)
large multi-mission   -> docs/goal/PLAN.md + docs/goal/RUN.md (+ optional docs/goal/tasks.md)
binary UI evidence    -> docs/goal/evidence/** only when artifacts exist
worktree workers      -> temporary per-mission reports only while integration needs them
```

- Do not create empty directories, duplicate source documents, or one file per concern.
- Keep checkpoint, task state, verification, attempts, evidence, blockers, and closeout in `RUN.md`. `tasks.md`, when present, is a regenerated mission/task listing view only — it never becomes a second source of truth.
- A compact `RUN.md` without `PLAN.md` is sequential: one parent writer in `shared_checkout`, no leases, worktree fan-out, or deterministic wave claim.
- Put one canonical fenced JSON manifest in each harness artifact. Markdown tables are human views; update the manifest first.
- Use an established repository planning convention instead of adding `docs/goal/` when one exists.
- On first bootstrap of a new target repository, seed a missing root `AGENTS.md` from `assets/templates/PROJECT_AGENTS.template.md` and a missing root `CLAUDE.md` from `assets/templates/PROJECT_CLAUDE.template.md`. Skip either file that already exists; never overwrite an established root `AGENTS.md` or `CLAUDE.md`.
- On that same first bootstrap, also seed a missing CI workflow from `assets/templates/PROJECT_CI.template.yml`, and, only for Cloudflare delivery, its separate CD companion `assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml` (see `references/cloudflare-deployment-lifecycle.md`). Skip either file that already exists; never overwrite established CI configuration.

## Shared Validation Tools

- `scripts/validate_harness_plan.py` validates PLAN/RUN shape, traceability, DAGs, authorization, digest consistency, closeout, and schema-v9 UI evidence.
- `scripts/upgrade_harness_schema.py` rewrites an older PLAN/RUN in place to the current schema (PLAN v4, RUN v9), adding only each version's neutral keys — never a fabricated authorization, gate, SHA, or evidence — and validates the result before writing; `--dry-run` reports the per-step additions without touching the file.
- `scripts/select_ready_nodes.py` selects the typed PLAN-v4/RUN-v8-or-v9 frontier and provider-neutral launch directives.
- `scripts/select_parallel_missions.py` supports older readable plans.
- `scripts/select_verifiers.py` applies `selection.mode: "changed_files"` to parent-observed changed files and never weakens integration, batch, final, release, migration, or smoke gates.
- `scripts/verifier_runtime.py` may reuse a `session_exact` PASS only when the checkout is clean, the command is cache-safe, every immutable input matches, and the explicit cache root is repository-external.
- `scripts/validate_node_result.py` and `scripts/validate_worker_result.py` validate returned identity, scope, Git facts, and verifier evidence before integration.

These shared validation and selection paths are Python-stdlib-only and deterministic. All but `upgrade_harness_schema.py` are read-only and never mutate Git, PLAN, RUN, tasks, or worktrees; `upgrade_harness_schema.py` is the one exception and only ever rewrites the exact PLAN/RUN files it was pointed at, never Git, tasks, or worktrees. Runtime bridges are documented only in the matching adapter.

## Default Runtime And Wave Policy

Apply this only to large plan-backed work with multiple missions:

1. Before the first production edit or launch, proactively inspect the current-session native tool surface, permission boundary, worker slots, isolation, completion channel, Git state, and runtime resources.
2. Record observed capabilities under `runtime_adapter` independently from authorization. Missing authorization must never make an available driver disappear.
3. Use three as the configured plan-backed write-worker maximum unless the user or observed capacity sets a lower limit.
4. New plan-backed files use PLAN schema v4 and RUN schema v9. PLAN provider policy chooses providers, provider-specific model options, and reasoning effort; the selected host adapter maps those choices to its launch surface without silent substitution.
5. Immediately after Plan Readiness, validate PLAN/RUN and select up to three dependency-ready, nonconflicting nodes in deterministic order.
6. Never run more than one writer in `shared_checkout`. Parallel writes require isolated workspaces and durable authorized branch/commit handoff.
7. Do not silently downgrade because authorization is missing. Request the exact missing execution bundle once, pause at that boundary, record the answer, then recompute the frontier.
8. Default the landing mode from the requested outcome: local implementation, branch, or commit work uses `local_only`; explicit push, PR, review, merge, or deployed delivery uses `pull_request` and loads the GitHub landing adapter.

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
configure_repository
push
create_pr
manage_pr_review
merge_pr
deploy
archive_worker_tasks
remove_worktrees
delete_branches
```

- One user instruction may authorize several exact actions, but its source is recorded under every covered key; never replace them with blanket permission.
- For large, plan-backed work, every grant is bounded by the matching RUN schema scope, mission, target, time, and lifecycle boundary. Small work creates no RUN file (see Project Size Gate); there, each grant is bounded instead by the exact user instruction that covers that specific action and target — never inferred from an adjacent instruction or a prior small-work grant.
- `invoke_external_runtime` does not replace spawn, workspace, branch, commit, integration, landing, or deployment authorization.
- PR creation, repository configuration, review-state mutation, merge, deploy, archival, worktree removal, and branch deletion are independent boundaries.
- Workers never edit parent-owned PLAN/RUN state, expand their own scope, integrate, push, open PRs, merge, deploy, or clean up.

## Workflow

### 1. Intake And Route

Inspect the repository, applicable instructions, Git state, upstream product/design sources, current behavior, and requested outcome. Record concise decisions for:

```text
Project size: small | large
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Planning depth: direct | compact RUN | PLAN + RUN
Host adapter: none | codex | claude_code
Workspace: shared_checkout | parent_managed_worktree | app_managed_worktree
Landing: local_only | pull_request
Verification: focused local | integration | final local | remote final-head
```

Do not scan every optional platform or adapter. Inspect only what the selected route needs.

### 2. Plan Large Work

Freeze relevant source paths and SHA-256 digests, functional and non-functional requirements, Builder UX Direction, architecture boundaries, frontend stack, data/integration contracts, failure states, security, observability, migration/release order, acceptance criteria, and exact verification commands. Preserve stable PRD, ARCH, UI, UX, DS, and TEST trace IDs.

Draw an acyclic typed graph with bounded correction routes. Separate independently writable frontend, backend, data, integration, review, UI evidence, and release work when their contracts and verifiers are distinct. Every runtime review is read-only and binds one exact reviewed SHA.

### 3. Pass Plan Readiness

Ready means the required inputs are frozen or explicitly `UNVALIDATED`, scope and denial boundaries are concrete, every task has a verifier, dependencies and resource conflicts are known, action authorization is recorded, and the next selected route is executable. Builder approval proves direction conformance, not usability proof. Every must-have `UX-*` trace needs an objective check or planned evidence.

For `plan-then-stop`, stop after readiness. For execution intent, request only the missing exact execution and optional landing actions, then continue when they are authorized.

### 4. Execute And Integrate

For small work, use one parent writer and the smallest relevant checks. For large work, select the ready frontier, then follow the chosen runtime adapter. Bind every worker to an immutable base, write/deny scope, resources, tasks, verifiers, permission boundary, and completion channel.

The parent independently observes the worker head and changed files, validates the result, checks actual scope and commit ancestry, and integrates passing heads serially. After each integration, run the required integration gate, update canonical RUN state, and recompute the frontier. Never accept a report merely because the runtime says it completed.

### 5. Verify Local-First

Use a verification ladder:

1. Run selected task/worker checks from parent-observed changed files.
2. After real cross-mission integration, run the relevant batch and interaction gates.
3. Converge local deterministic checks and exact-SHA runtime review. A repair invalidates only affected layers.
4. After those loops close, run broad regression, browser E2E, breakpoint-by-state UI evidence, visual review, migration, and release checks that apply to the final integration head.
5. Run `git diff --check` and review the complete final diff.

A clean, cache-safe focused verifier may reuse only an exact same-session `session_exact` PASS from a repository-external cache. Do not cache integration, cross-mission, UI, migration, release, or remote gates. Required UI artifacts live under `docs/goal/evidence/`, record lowercase SHA-256, and bind to the exact integration head.

Automated current-head E2E may replace only an equivalent duplicate manual smoke. Record `not required - covered by current-head E2E`; deployment smoke remains separate when the tested environment differs.

Local-only work stops after its authorized local branch/commit/integration outcome and local evidence. It does not wait for GitHub CI or GitHub review. Remote final-head verification is owned by the GitHub landing adapter.

### 6. Complete

A local-only run completes when authorized local mutations are finished, all applicable local gates pass on the integration head, no blocker remains, and RUN records evidence, changed files, commits, residual risk, and explicit local landing state.

A pull-request run completes only through the GitHub landing adapter's exact-head requirements. Deployment completes only through the declared provider lifecycle; Cloudflare development and production remain separate targets and separate `deploy` authorizations.

Finish by checking final Git status, reporting what changed and what was verified, and listing every intentionally unexecuted remote or lifecycle action. Never claim a push, PR, review, merge, deploy, archival, or cleanup action that did not happen.
