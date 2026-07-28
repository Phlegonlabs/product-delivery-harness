---
name: fullstack-harness-engineering
description: "Classify engineering work as small or large, then plan, execute, verify, and integrate it under explicit action authorization. This is the lightweight shared Full Stack Harness core: it owns PLAN/RUN state, traceability, scheduling contracts, local verification, and integration. Load exactly one sibling runtime adapter for Codex or Claude Code only when runtime-specific orchestration is needed, and load the GitHub landing adapter only when remote landing is requested."
---

# Full-Stack Harness Engineering

## Purpose

Keep the common delivery contract small: classify the work, freeze the necessary inputs, plan only when coordination needs it, execute under exact authorization, verify locally, and integrate safely. Runtime launch mechanics and remote landing are separate adapters so ordinary work does not load every Codex, Claude Code, GitHub, CI, review, and deployment rule.

Keep `prd-builder` as a separate upstream skill. Reuse its artifacts — `PRD.md`, `architecture.md`, `stack-decisions.md`, `wireframes.md`, and for a UI-bearing product `design-system.md` and `design-system.json` — instead of duplicating them. If product, Builder UX Direction, architecture, or design evidence is missing, route to that skill, use an explicitly authorized assumption, or record the gap as `UNVALIDATED`. An implementation agent does not invent Builder UX Direction and does not author the design system.

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
- When small work touches a frontend/UI surface, run one bounded critique-repair-recheck cycle before the final review: when a rendered view or screenshot exists, critique the product's responsive verification set against its `design-system.md` (or the anti-slop guardrails in `../prd-builder/references/design-system-guide.md` when this product has no design system), repair the single highest-impact failure, and recheck; otherwise fall back to a text-only review of the actual markup/styles against the same guardrails and record that no visual-verification claim is made. Do not retry the same failed approach more than twice; after two repair attempts, stop and report the remaining gap to the user instead of looping further.
- Small UI work obeys the UI Implementation Contract below exactly as large work does. It creates no PLAN/RUN file, so `design-system.json`, the route's screen entry in `wireframes.md`, and the exact user instruction are what bound it.
- Large work enters the workflow below. Planning does not imply parallel execution.
- Enable scheduler fan-out only when there are at least two dependency-ready, nonconflicting missions and every isolation, capacity, permission, and action gate passes.
- A ready node is executable here only when its `allowed_providers` includes the current host adapter's provider; a declared `preferred_provider` affects only which allowed provider is chosen, it does not gate executability by itself. There is no cross-host fallback: a node whose `allowed_providers` excludes the running host is simply not executable here and is reported blocked on provider mismatch.
- If small work grows large, stop at a safe checkpoint, preserve completed edits and evidence, and plan only the remainder.

## Optional External Skill Assist

This core does not bundle `frontend-design` or `feature-dev`. Both are separate Apache-2.0 plugins from the `claude-plugins-official` marketplace and require their own install (`claude plugin install frontend-design@claude-plugins-official`, `claude plugin install feature-dev@claude-plugins-official`). Before offering either, confirm it is actually loaded in the current session; if it is not installed, say so and continue on this core's own path instead of fabricating its presence.

The normal UI handoff is `prd-builder` low-fidelity wireframes -> optional product-specific preference discovery through `frontend-design` -> `prd-builder`'s design system frozen as `design-system.md` and `design-system.json` -> Harness implementation. Wireframes remain the product authority for structure and flow; the design system is the authority for the visual layer. Any exploration HTML is non-canonical evidence; implementation begins only after the design system is frozen.

- Do not use `frontend-design` to compensate for a missing or partial design system. Route that gap upstream to `prd-builder` and freeze the resolved `design-system.md` + `design-system.json` pair first.
- `frontend-design` may appear in a UI mission's `required_skills` only when the planner records the user's explicit selection for a new or high-impact visual surface. That mission runs in **frontend-design conformance mode**: it may improve the quality of execution inside the frozen wireframes and design system, but it may not choose a new aesthetic direction or invent a token, primitive, variant, component, motion pattern, or page structure at the call site.
- In conformance mode, a missing contract entry returns as a design-input delta. The worker stops at a safe boundary; the parent routes the delta through `references/design-input-updates.md`, freezes the revised package, updates the PLAN revision and digest, and only then resumes implementation. Loading `frontend-design` never turns contract drift into an allowed local exception.
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
- Read `references/graph-orchestration.md` for PLAN schema v5, RUN schema v10, older readable schemas, typed nodes, bounded review-repair-review routes, provider policy, retry, or subgraph replay.
- Read `references/execution-task-decomposition.md` for flat task IDs, one bounded execution-time split, or the UI build order a design system implies.
- Read `references/parallel-mission-selection.md` before proposing a parallel write wave.
- Read `references/design-input-updates.md`, `references/platform-archetypes.md`, or `references/existing-app-refinement.md` only when those inputs or product shapes apply.
- Read `references/worktree-thread-orchestration.md` only after the selected runtime adapter requires multiple missions, subagents, threads, or worktrees.
- Read `references/verification-gates.md` for task, integration, UI, release, and evidence gates.
- Read `references/cloudflare-deployment-lifecycle.md` only for Cloudflare delivery.
- Read `references/mobile-desktop-deployment-lifecycle.md` only for iOS/Android/Flutter/macOS/Windows delivery.
- Read `references/commit-convention.md` before a harness-managed commit.
- Read `references/orchestration-research-notes.md` for the underlying Codex/Claude Code orchestration capability facts, version gates, and GitHub review/merge mechanics behind this skill's guidance, including the Codex Cloud connection requirement and the `@codex review` manual trigger the GitHub landing adapter depends on.
- Use `assets/templates/HARNESS_PLAN.template.md` for `PLAN.md` and `assets/templates/MISSION_RUNBOOK.template.md` for `RUN.md`. Load another template only for its named expansion:
  - `assets/templates/TASKS.template.md` for `tasks.md`, a non-canonical mission/task listing view regenerated from `RUN.md` whenever a RUN.md exists.
  - `assets/templates/GOAL.template.md` for a standalone copy-ready goal prompt when a workflow needs one without creating `RUN.md`.
  - `assets/templates/WORKER_GOAL.template.md` for a mission worker's frozen launch prompt.
  - `assets/templates/PULL_REQUEST.template.md` as the PR body base when the GitHub landing adapter creates a pull request.
  - `assets/templates/E2E_VERIFICATION.template.md` only as a standalone expansion of `RUN.md`'s verification matrix when it becomes too large to scan inline.
  - `assets/templates/REFINEMENT_BACKLOG.template.md` only as a standalone expansion of `RUN.md`'s refinement backlog when it becomes too large to scan inline.
  - `assets/templates/PROJECT_CLOUDFLARE_DEPLOYMENT_GUIDE.template.md` for `docs/deployment.md`, an operational setup guide recording how this project's Cloudflare Workers are actually configured, only for Cloudflare-deploying products.

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
- A compact `RUN.md` without `PLAN.md` is sequential (one mission at a time, no leases or deterministic wave claim); its workspace default still follows the Default Runtime And Wave Policy below, not `shared_checkout`.
- Put one canonical fenced JSON manifest in each harness artifact. Markdown tables are human views; update the manifest first.
- Use an established repository planning convention instead of adding `docs/goal/` when one exists.
- On first bootstrap of a new target repository, seed a missing root `AGENTS.md` from `assets/templates/PROJECT_AGENTS.template.md` and a missing root `CLAUDE.md` from `assets/templates/PROJECT_CLAUDE.template.md`. Skip either file that already exists; never overwrite an established root `AGENTS.md` or `CLAUDE.md`.
- On that same first bootstrap, also seed a missing CI workflow from `assets/templates/PROJECT_CI.template.yml`, and, only for Cloudflare delivery, its separate CD companion `assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml` (see `references/cloudflare-deployment-lifecycle.md`). Skip either file that already exists; never overwrite established CI configuration.

## Shared Validation Tools

- `scripts/validate_harness_plan.py` validates PLAN/RUN shape, traceability, DAGs, authorization, digest consistency, closeout, RUN-v10 retained evidence, and cross-checks `integration_head_sha` against the live Git branch head.
- `scripts/upgrade_harness_schema.py` rewrites an older PLAN/RUN in place to the current schema (PLAN v5, RUN v10), adding only each version's neutral keys — never a fabricated authorization, gate, SHA, release decision, or evidence — and validates the result before writing; `--dry-run` reports the per-step additions without touching the file. Older PLAN schemas remain readable and older RUN schemas remain readable without an upgrade.
- `scripts/select_ready_nodes.py` selects the typed PLAN-v5/RUN-v10 frontier and provider-neutral launch directives; it also continues to read supported older graph schemas.
- `scripts/select_parallel_missions.py` supports older readable plans.
- `scripts/select_verifiers.py` applies `selection.mode: "changed_files"` to parent-observed changed files and never weakens integration, batch, final, release, migration, or smoke gates.
- `scripts/verifier_runtime.py` may reuse a `session_exact` PASS only when the verifier's pass signal is the literal `exit 0`, the checkout is clean, the command is cache-safe, every immutable input matches, and the explicit cache root is repository-external.
- `scripts/validate_node_result.py` and `scripts/validate_worker_result.py` validate returned identity, scope, Git facts, and verifier evidence before integration.
- `scripts/check_wrangler_binding_isolation.py` resolves a scaffolded `wrangler.jsonc`'s effective per-environment bindings and flags any D1, KV, R2, queue, or Durable Object resource identity shared between `development` and `production`.

Non-UI validation, selection, and CLI startup paths are Python-stdlib-only and deterministic. Pillow is imported lazily only when a verifier must decode binary UI evidence; if it is unavailable, report a targeted UI-evidence decoding error without preventing non-UI CLIs from starting. All but `upgrade_harness_schema.py` are read-only and never mutate Git, PLAN, RUN, tasks, or worktrees; `upgrade_harness_schema.py` is the one exception and only ever rewrites the exact PLAN/RUN files it was pointed at, never Git, tasks, or worktrees. Runtime bridges are documented only in the matching adapter.

## Default Runtime And Wave Policy

Apply this to all large plan-backed work, whether the frontier ever holds more than one ready mission or processes them one at a time:

1. Before the first production edit or launch, proactively inspect the current-session native tool surface, permission boundary, worker slots, isolation, completion channel, Git state, and runtime resources.
2. Record observed capabilities under `runtime_adapter` independently from authorization. Missing authorization must never make an available driver disappear.
3. Do not cap `max_parallel_workers` at a small fixed number. Select every dependency-ready, nonconflicting mission the current frontier contains; `references/parallel-mission-selection.md`'s effective-budget formula (`min(configured maximum, observed worker slots, isolation capacity, conflict capacity)`) is what actually bounds the wave, driven by real observed capacity and the size of the mutually nonconflicting set, not by an arbitrary starting number. Set `max_parallel_workers` generously high unless the user or observed capacity sets an explicit lower limit.
4. New plan-backed files use PLAN schema v5 and RUN schema v10. PLAN provider policy chooses providers, provider-specific model options, and reasoning effort; the selected host adapter maps those choices to its launch surface without silent substitution. Older PLAN and RUN versions remain readable, but new files do not copy their weaker acceptance, source-publication, authorization, release, continuity, or evidence shapes.
5. Immediately after Plan Readiness, validate PLAN/RUN and select every dependency-ready, nonconflicting node the effective-budget formula allows, in deterministic order. Before that first selection, record `observed.captured_at` and `observed.git` from a live `git status` / `git rev-parse`, and set `integration.batch_base_sha` to the observed integration head. The validator does not require these — a RUN that leaves them null still reports `PASS` — but the selector then has nothing to launch: every mission and lifecycle node lands in `deferred_nodes` with `parent_state_unreconciled` or `batch_base_missing`, and `dispatchable_nodes` comes back empty. Those two kinds mutate state derived from the parent's current Git position — a mission spawns writers, a lifecycle node pushes, merges, or deploys — so both are gated on it. `verifier`, `approval`, and `external_wait` nodes are not, because they change nothing the snapshot describes. Read those two keys, not `ready_frontier`: these are dispatch-time reasons, so the frontier list can still look full while nothing is dispatchable. Once `status` is `running`, the Resume Reconciliation Gate applies the same unreconciled state to every node and `ready_frontier` empties too. A green validator next to empty `dispatchable_nodes` means the observed snapshot was never filled in, not that the plan is wrong.
6. First read the target repository's instructions and existing branch/landing model. When they define implementation, integration, or protected landing branches, preserve those exact names and topology. Otherwise use persistent `development` as the default implementation and integration base. Default every mission, even when only one is ever ready at a time, to its own worktree created from the recorded current integration SHA. The primary integration checkout is a merge target, never a direct implementation surface. Before any mission head is integrated, require at least one read-only review round bound to that exact worktree head; a repair changes the head and requires a fresh review. Only review-passing heads may merge serially into the resolved integration branch. Reserve `shared_checkout` for when worktree creation itself is unavailable or unauthorized, and never run more than one writer in it.
7. Do not silently downgrade because authorization is missing. Request the exact missing execution bundle once, pause at that boundary, record the answer, then recompute the frontier.
8. Default the landing mode from the requested outcome. Under the default branch model, ordinary implementation, PRD updates, UI changes, branch, commit, and integration work uses `integration_push`: the verified integration head is pushed to `development` so the watching development deployment can build, and no PR exists. A `development -> production` promotion uses `pull_request`, prepared only after the user gives final approval and merged only by the user. Use `local_only` when the run must not touch the remote at all. When target-repository instructions define another model, record and follow that model instead. In every case, `integration.branch`, `landing.head_branch`, and `landing.base_branch` must contain the resolved repository branches rather than assumed names. Older readable schemas keep their recorded branch semantics.

## Default Development And Production Branch Policy

Apply this policy to the target repository where the skill runs only when its own instructions do not already define the implementation, integration, and landing branches. Target-repository governance wins; never create `development` or `production` merely to replace an existing authorized flow.

```text
current development SHA
-> one independent mission worktree
-> worker checks
-> at least one exact-head read-only review
-> repair and fresh review when needed
-> authorized serial integration into development
-> push development          (covered by the execution-intent instruction)
-> development deployment builds from that head

development
-> explicit final user approval to start promotion
-> harness opens the development -> production PR
-> current-head CI and review
-> STOP. the human merges.
```

The development loop runs end to end without stopping: everyone works on `development`, and the push that lets its deployment build is part of ordinary execution rather than a separate confirmation. When the repository routes work into `development` through PRs rather than direct pushes, merging those PRs — including enabling repository auto-merge on them once current-head CI and review pass — is part of the same loop and needs no separate confirmation.

The production side is the opposite — the harness prepares a verified PR and hands it over. It does not merge and does not enable auto-merge there, no matter how the promotion was approved. Only a separate explicit user instruction naming that exact PR can authorize that merge.

The production deploy is a different action from that merge and follows its own rule. `deploy` is its own ledger gate with exact `release:<target-id>` targets and is not part of the execution-intent bundle beyond the development target. The harness runs the production deploy when `deploy` is authorized for that exact production target at that exact head, and never otherwise: it does not infer the grant from the merge, from the promotion approval, or from the development loop. Where the production Worker deploys from its own Git connection instead of a harness-run command, the human's merge is the deploy trigger and that same exact `deploy` grant records the publication consequence. See `references/cloudflare-deployment-lifecycle.md`.

Under this default model, never start ordinary feature, PRD, or UI work from `production`, and never integrate a mission worktree directly into `production`. Future changes continue from the then-current `development` branch even after a production promotion. If the repository has adopted this model and either required branch is missing, report the setup gap and obtain exact branch-creation authorization rather than creating it implicitly.

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
trigger_remote_ci
manage_pr_review
merge_pr
provision_cloud_resources
deploy
archive_worker_tasks
remove_worktrees
delete_branches
```

- One user instruction may authorize several exact actions, but its source is recorded under every covered key; never replace them with blanket permission.
- Eleven of these actions carry the ordinary development loop: `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, `push` **restricted to the resolved integration branch**, `merge_pr` **restricted to a PR whose base is the resolved integration branch**, and `deploy` **restricted to the development release target**. One clear execution-intent instruction ("implement this", "build it", "ship it") covers all eleven together: record its source under each of their ledger entries in the same authorization request or checkpoint, and do not manufacture separate confirmation pauses for them. They still each get their own ledger entry with its own recorded source, and `push`, `merge_pr`, and `deploy` still carry exact targets — grouping them changes only that a single instruction suffices, not what gets recorded.
- `create_user_owned_tasks` is grouped for the same reason `spawn_subagents` is: it is the Codex host's worker-launch action. Whether worker launch needs a separate confirmation must not depend on which host the run happens to be on.
- That grouping is scoped, not general. A `push` whose target is any branch other than the resolved integration branch, a `merge_pr` whose PR base is any branch other than the resolved integration branch, and a `deploy` whose target is any release target other than the development one are not covered and need their own authorization moment. Under the default branch model this means the development loop runs without stopping — including merging a PR into `development` — while anything aimed at the protected landing branch stops.
- Record that separation in the ledger rather than leaving it to prose. Every new RUN-v10 artifact uses `action_target_contract: "action-targets/1"`; the shipped template is already marked. In a marked RUN, a `push`, `merge_pr`, or `deploy` entry carrying a target the execution-intent instruction does not reach must name the separate instruction for that exact target in `target_sources` (`references/execution-state-model.md`), and that source must differ from the entry's own. The validator fails the RUN otherwise, in every landing mode. An existing unmarked legacy RUN-v10 entry keeps its historical behavior only while it omits `target_sources`; adding `target_sources` opts that entry into the same strict provenance rules.
- The remaining actions — `create_pr`, `trigger_remote_ci`, `manage_pr_review`, `provision_cloud_resources`, `configure_repository`, `remove_worktrees`, `archive_worker_tasks`, and `delete_branches`, plus the out-of-scope `push`, `merge_pr`, and `deploy` cases above — remain independent gates. Each needs its own distinct authorization moment and is never swept in by the execution-intent statement. `trigger_remote_ci` uses exact `workflow:<identity>` targets. `provision_cloud_resources` uses exact `cloud-resource:<provider>:<environment>:<kind>:<logical-name>` targets.
- A merge whose base is the resolved integration branch may use repository auto-merge once its current-head CI and review gates pass. Enabling auto-merge on such a PR is part of the development loop, not a separate confirmation.
- A merge toward the protected landing branch is never the harness's to initiate. The harness may open the promotion PR, observe current-head CI, and request review, but it does not merge and does not enable auto-merge there — approval to prepare the promotion is not approval to land it. Hand back a verified PR and stop. The single exception is a separate, explicit user instruction naming that exact PR; that instruction is its own `merge_pr` grant bound to the exact `pr:<full-PR-URL>` target and head SHA, and it is never inferred from the execution-intent statement or from promotion approval.
- For large, plan-backed work, every RUN-v10 execution and action scope binds the current `run_id`, mission set, PLAN revision, PLAN digest, exact targets where applicable, time, and lifecycle boundary. A plan revision or digest change invalidates the grant rather than silently carrying it forward. Small work creates no RUN file (see Project Size Gate); there, each grant is bounded instead by the exact user instruction that covers that specific action and target — never inferred from an adjacent instruction or a prior small-work grant.
- `invoke_external_runtime` does not replace spawn, workspace, branch, commit, integration, landing, or deployment authorization.
- PR creation, repository configuration, review-state mutation, merge, deploy, archival, worktree removal, and branch deletion are independent boundaries.
- Workers never edit parent-owned PLAN/RUN state, expand their own scope, integrate, push, open PRs, merge, deploy, or clean up.

## UI Implementation Contract

When the product has a design system, a route's structure comes from `wireframes.md` and its visual layer comes from `design-system.md` plus `design-system.json`. The route is composed, not freely designed: the design system is a closed set the implementation picks from.

The frozen design system is the default implementation source. If the mission's explicitly planned `required_skills` includes `frontend-design`, the worker still follows every rule below in frontend-design conformance mode. The skill changes execution craft, not the contract or its precedence.

Every mission that writes UI code:

1. Reads `design-system.json` and the route's screen entry in `wireframes.md` before writing anything, and implements from them. Resolve the route by matching it against each screen's `Route(s):` line; a route no screen claims is a blocker (see `references/contract-and-traceability.md`'s Stop And Ask Conditions), and so is a route two screens claim.

    Those two files are the complete input. There is no mockup, screenshot, Figma frame, or exploration HTML in the normal path, and none is required: `wireframes.md` supplies the structure and `design-system.json` supplies every visual value the structure needs. A mission does not wait for a visual artifact, ask for one, or treat its absence as missing input. When a page UI reference does exist it is additional evidence handled through `references/design-input-updates.md`, never a precondition.
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

When an existing `RUN.md` is `running`, pass the Resume Reconciliation Gate (`references/execution-state-model.md`) before selecting or launching any ready node: a dirty checkout may hold real work an earlier, interrupted session never verified or committed, and canonical state does not know about it yet.

### 2. Plan Large Work

Freeze relevant source paths and SHA-256 digests, functional and non-functional requirements, Builder UX Direction, architecture boundaries, frontend stack, data/integration contracts, failure states, security, observability, migration/release order, acceptance criteria, and exact verification commands. Preserve stable PRD, ARCH, UI, UX, DS, and TEST trace IDs. Every task acceptance row is structured as `{test_id, trace_ids, criterion}` so each planned trace has named verification coverage.

For every UI implementation mission, default `required_skills` to `[]`. Add `frontend-design` only when the user explicitly selected it for that mission's new or high-impact visual surface, and record frontend-design conformance mode in the mission objective or stop conditions. Do not infer the skill from a frontend path, a visual review requirement, or a desire to make the page look better.

A PLAN-v5 source may record a `staged_revision`, but that is not an executable publication. The current canonical `location`, `content_sha256`, and `source_revision` stay binding until the accepted revision is published to the canonical source location, the source becomes `frozen` or `delta_accepted`, and the PLAN revision and digest change. A ready or executing RUN never points at a product staging path.

For deployable work, declare stable provider-neutral release target IDs for both `development` and `production`. When `architecture.md` has a `## Release Targets` section, reuse its target IDs verbatim instead of minting new ones, and give every expected deployable surface it lists at least one target — see `references/contract-and-traceability.md`'s Trace IDs rules. Every target names its exact stage, source, artifact kind, signing requirement, channel, data mode, trigger, migration classification, build/migrate/publish commands, prerequisites, and smoke verifiers. RUN-v10 `targets` keys exactly equal those PLAN target IDs and retain PASS artifact, channel, promotion, and availability evidence with hashes, build/version identity, and signing status.

Draw an acyclic typed graph with bounded correction handling. Before integration, send review findings back to the original mission task, thread, and worktree; after its verifier passes on a changed head, re-arm the same review node and review that head again. Bound this loop with the review node's `max_attempts`. Do not create a second repair mission from an integration branch that does not contain the reviewed head. A post-integration or batch review may route to a bounded repair node based on the reviewed integration head, then back through review; it never routes straight past the review gate. Separate independently writable frontend, backend, data, integration, review, UI evidence, and release work when their contracts and verifiers are distinct. Every runtime review is read-only and binds one exact reviewed SHA.

### 3. Pass Plan Readiness

Ready means the required inputs are frozen or explicitly `UNVALIDATED`, scope and denial boundaries are concrete, every task has a verifier, dependencies and resource conflicts are known, action authorization is recorded, and the next selected route is executable. Executability covers the whole graph, not just the next node: every `runtime_worker` node's `allowed_providers` must include a provider that will actually host part of this run. A node no available host can execute is a blocking readiness gap unless the user explicitly acknowledges it as deferred to a run on another host (see `references/graph-orchestration.md`). Builder approval proves direction conformance, not usability proof. Every must-have `UX-*` trace needs an objective check or planned evidence.

For `plan-then-stop`, stop after readiness. For execution intent, request only the missing exact execution and optional landing actions, then continue when they are authorized.

### 4. Execute And Integrate

For small work, use one parent writer and the smallest relevant checks. For large work, select the ready frontier, then follow the chosen runtime adapter. Bind every worker to an immutable base, write/deny scope, resources, tasks, verifiers, permission boundary, and completion channel. A worker writing UI code is also bound by the UI Implementation Contract above; carry it into the worker's launch prompt with the rest of its scope.

When a UI worker loads `frontend-design`, its launch prompt must state the conformance boundary and name the frozen wireframe screen, `design-system.md`, and `design-system.json` inputs. A generic instruction to "make it distinctive" is not a valid handoff.

The parent independently observes the worker head and changed files, validates the result, checks actual scope and commit ancestry, and confirms a read-only pre-integration review PASS on that exact head. An enabled task-local reviewer records its exact-head PASS in WORKER_RESULT; after validation, the parent retains that completed reviewer child in the worker's canonical `nested_review_evidence`, which must still match the mission head before integration. A disabled task-local policy, or a graph-backed direct worker with no nested policy, may validate first so its downstream review node becomes selectable, but the mission cannot transition to `integrating` until the parent records a terminal `review_workers[]` PASS covering that mission and worktree head. A review worker may bind only mission worktree or integrated SHAs declared by its own review node, plus the current integration or PR head. If the review finds a defect, repair inside the mission worktree and review the new head again. The parent then integrates passing heads serially into the resolved integration branch, runs the required post-merge integration gate, updates canonical RUN state, and recomputes the frontier. Never accept a report merely because the runtime says it completed.

### 5. Verify Local-First

Use a verification ladder:

1. Run selected task/worker checks from parent-observed changed files.
2. Before each worktree merges, complete at least one read-only review round on its exact current head. Any repair invalidates that review.
3. After real integration into the resolved integration branch, run the mission integration gate and the relevant batch and interaction gates.
4. Converge local deterministic checks and exact-SHA runtime review. A repair invalidates only affected layers.
5. After those loops close, run broad regression, browser E2E, breakpoint-by-state UI evidence, visual review, migration, and release checks that apply to the final `development` head.
6. Run `git diff --check` and review the complete final diff.

A clean, cache-safe focused task or worker verifier may reuse only an exact same-attempt `session_exact` PASS, bound to its `attempt_id` and `lease_id`, from a repository-external cache. Do not cache integration, cross-mission, UI, migration, release, or remote gates; that ban is enforced both when the PLAN declares the verifier and again at run time in `verifier_runtime.py`. RUN-v10 `verifier_executions` is append-only and parent-owned: workers return candidate results, but only the parent validates and appends the normalized verifier, execution context, key document/digests, cache decision, output hashes, metrics, and retained evidence paths. Required UI artifacts live under `docs/goal/evidence/`, record lowercase SHA-256, and bind to the exact integration head.

Automated current-head E2E may replace only an equivalent duplicate manual smoke. Record `not required - covered by current-head E2E`; deployment smoke remains separate when the tested environment differs.

Local-only work stops after its authorized worktree commits are reviewed and integrated into the resolved persistent integration branch, with local evidence recorded. It does not wait for GitHub CI or GitHub review and never changes the resolved protected landing branch. Remote final-head verification and any later approved promotion are owned by the GitHub landing adapter.

### 6. Complete

A local-only run completes when authorized local mutations are finished, all applicable local gates pass on the integration head, no blocker remains, and RUN records evidence, changed files, commits, residual risk, and explicit local landing state.

A pull-request run completes only through the GitHub landing adapter's exact-head requirements. Deployment completes only through the declared provider lifecycle. Merge or landing permission never implies deployment permission. For a native merge-triggered release, execution requires exact merge/landing authorization for the PR and release consequence plus exact deployment authorization for the target; never infer deploy from merge.

Finish by checking final Git status, reporting what changed and what was verified, and listing every intentionally unexecuted remote or lifecycle action. Never claim a push, PR, review, merge, deploy, archival, or cleanup action that did not happen.
