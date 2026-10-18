---
name: delivery-harness
description: "Route engineering work through planning, authorization, execution, verification and integration. Use direct delivery for one writer and one verification sequence; use PLAN-v6/RUN-v11 for durable coordination, isolated integration or a bounded correction graph. Resolve required delegates through observed native tools or explicitly bound external bridges."
---

# Delivery Harness

Commands: `references/installed-commands.md`.

Before direct or managed routing, apply `references/delegation-contract.md`: distinct sibling assignments, required roles and actual execution identity. Delegation grants no actions and requires no managed run.

Every invocation uses `references/document-sync-contract.md`. Accepted enhancements follow `references/bounded-enhancement.md`; acceptance follows `references/delivery-acceptance-contract.md`.

[Generate, Verify, Correct](references/gen-verify-correct.md)

At implementation/integration/acceptance checkpoints, apply `../product-definition-builder/references/prd-refinement.md`: record evidenced PRD gaps, repair requirement violations and preserve frozen inputs.

Follow `AGENTS.md` Repository Change Checkpoints at entry, significant changes and handoff, even outside Harness. Record meaningful Git/working-tree changes in the Epic, without PLAN/RUN or watchers. Read-only tasks propose records. English PRD/architecture remain implementation authority, not Chinese review copies.

## Design And Maintenance Routing

Before Product-package execution, apply `references/pre-delivery-self-review.md#harness-entry`: author reviews, catch-up rules, scoped routes and evidence. Missing/stale evidence blocks execution, not inspection/planning.

Classify UI work with `ui-design-builder/references/review-workflow.md`. Initial design, enhancements and `structure`/`both` changes use the affected design gates. Routine maintenance (UI impact `none` or `style`) updates current product and requirements and keeps historical design artifacts. Product or stack decisions return upstream. Frozen RUNs keep pinned contracts until a task boundary.

Optional context: `references/reference-selection.md` (`references/option-library/`).

## Purpose

Use PLAN/RUN only when coordination requires it. Preserve upstream ownership:

- `product-definition-builder` owns approved `PRD.md`, `architecture.md`, and `stack-decisions.md`, including complete frontend/backend architecture and technology decisions.
- `ui-design-builder` owns UI Design Intake, PRD-led direction studies, HiFi checks, Visual Approval and the HiFi target. `design-system-compiler` owns a required design-system pair.
- Implement current approved product/stack and applicable UI sources. Every must-have `UX-*` trace still needs objective evidence. `Recommended` and `Provisional` stack rows are proposals. Do not invent product, copy, stack or design decisions.
- `code-security-review` owns read-only review of the fixed integrated SHA; it neither remediates nor probes live targets.

## Project Size Gate

Before loading task-specific tooling, run one bounded parent-only scope scan.

Classify work as `small` when one writer can own one bounded outcome in one checkout and verify it with one coherent local sequence. That writer may be the required delegated specialist. A high file count, language count, test duration, or reasoning difficulty does not make work `large` by itself.

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

Small work creates no PLAN/RUN files. Resolve required delegates. If scope grows, preserve evidence and plan the remainder. The Sequential Parent Route in `execution-state-model.md` handles eligible generic work one mission at a time, never mandatory roles.

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
- Execution intent covers only applicable local setup, branch, commit, and integration actions; it does not authorize `push`. Harness 0.38+ RUNs stay `local_only` with `push` false. Publishing A to the run branch and promoting A to `main` are separate post-RUN actions with separate authorization.
- Use PLAN `branch_policy` to freeze the remote `main` base for ordinary work and hotfixes under `main-preview/1`; retain historical RUN pins. Never edit/commit on a protected branch or recreate one as a run branch. Follow `references/branch-promotion-contract.md`; never force-push. Ask before branch creation; never add a fixed prefix.
- Archival, worktree removal, and branch deletion are separate actions and are never implied by completion.
- The parent owns routing, authorization, PLAN/RUN, dispatch, leases, integration, and lifecycle actions. Workers and reviewers never delegate, edit PLAN/RUN, integrate, push, or clean up.
- A managed runtime review launches only from a persisted `reserve-review-dispatch` receipt for the selector's current directive. A raw runtime spawn is unplanned work; do not accept its result or reconstruct a receipt afterward.
- Non-mission nodes reserve with `reserve-node-attempt`, execute outside the RUN lock, then record evidence with `record-node-result`; interrupted attempts become `blocked`.
- A review PASS binds one exact SHA. Any repair invalidates it.
- Preserve failed, interrupted, cancelled, dirty, and partial worktree evidence. Never reset or remove it automatically.

## Direct Route

For small work:

For initial website/app implementation, read [Initial Product Foundations](references/initial-product-foundations.md) and order prerequisites before dependent features.
Implement local hooks first; route fixed-build external setup to separately authorized Activation preparation and deployment operations.

1. Inspect the bounded component and relevant instructions.
2. When work consumes a package produced by `product-definition-builder`, verify its Product Definition Approval and Stack Decision Checkpoint plus the applicable self-review and UI handoff under `references/pre-delivery-self-review.md`; then implement with one writer resolved under `references/delegation-contract.md`. UI work requires the host frontend worker; the parent retains coordination and acceptance.
3. Run the smallest focused checks, including security tests, that prove the change.
4. Review the complete diff and run `git diff --check`.
5. Create an authorized local commit when requested.
6. For code work, load `code-security-review` on that SHA; without one, report `UNVALIDATED`, not PASS.
7. Perform only remaining authorized Git actions.

For small UI work, add one critique-repair-recheck cycle before final review. Use rendered evidence when available; otherwise perform a text-only markup/style review and state that no visual claim was made. Obey `references/ui-implementation-contract.md`, including rule-8 UI-impact classification and same-change doc updates. Stop after two failed repair attempts and report the remaining gap.

Optional `/feature-dev` exploration does not change authorization, ownership or verification.

## Managed Stage Routing

Use this routing only when the size gate classifies work as `large`. For direct work, do not read the managed stage file.

- Before authoring PLAN, read [Managed Route](references/stages/managed-delivery.md#managed-route), [Reference Routing](references/stages/managed-delivery.md#reference-routing), and [Plan Large Work](references/stages/managed-delivery.md#2-plan-large-work).
- Before readiness and dispatch, read [Default Runtime And Wave Policy](references/stages/managed-delivery.md#default-runtime-and-wave-policy), [Default Mission Topology](references/stages/managed-delivery.md#default-mission-topology), and [Pass Plan Readiness](references/stages/managed-delivery.md#3-pass-plan-readiness).
- Before managed runtime use, read [Adapter Routing](references/stages/managed-delivery.md#adapter-routing).
- Before execution, read [Execute And Integrate](references/stages/managed-delivery.md#4-execute-and-integrate).
- Before verification, read [Verify Local-First](references/stages/managed-delivery.md#5-verify-local-first).
- Before closeout, read [Complete](references/stages/managed-delivery.md#6-complete).

## Repository Context Contract

Discover the effective instruction chain from repository root to the selected checkout.

- Existing `AGENTS.md`/`AGENTS.override.md`/`CLAUDE.md` are user-owned; never overwrite, normalize, silently copy.
- Entry runs `scripts/configure_project_context.py --root <target-root> --merge-agents`; missing files use `PROJECT_AGENTS.template.md` and distinct `PROJECT_CLAUDE.template.md`; generated files differ. Existing AGENTS stays proposal-only until a reviewed plan binds original/template hashes, selected headings and acknowledged conflicts. Same-heading differences are unresolved semantic divergences. Resolve new Skill Bindings from observed skills with owner confirmation.
- Follow the current host's effective instruction precedence; do not guess it from a provider name or inject another host's instructions.
- Keep automatic context discovery enabled. A nested instruction may narrow a mission but never widen write scope or authorization.

## UI Implementation Contract

Read `references/ui-implementation-contract.md` before UI implementation or review.

- `design-system-compiler` alone owns compilation when the Design System Need Gate is `required`.
- UI implementation runs the bound frontend author under this Harness's conformance contract. Do not claim that skill defines conformance mode or reopen Style Integration.
- Initial/enhancement system-conformance uses current approved PRD, UI design, HiFi and pair; their responsive sets must agree. Target-conformance uses the approved target when the gate is `not_required`. Routine maintenance follows `references/ui-implementation-contract.md`; a missing required input is a design-input delta.
- A page-faithful target binds implementation only after the user explicitly requests faithful conformance.
- After the Final Visual Parity Loop, one read-only page-quality pass (`references/verification-gates.md`) runs on the exact head. Impeccable is not the default; a separately authorized run may add UI evidence, with its subagents, browser/server, snapshot, and download side effects disclosed. It never fills a Harness read-only reviewer node.
- Bundled defaults exist only for bundled skills. A project's owner-confirmed Skill Bindings table may bind installed external visual-direction, frontend-authoring, or UI-quality tools after their full trees and side effects are checked; an unresolved or incompatible slot blocks its dependent node.

## Workflow

### 1. Intake And Route

Run System Review And Route; the Resume Reconciliation Gate above covers a running RUN.

If the user pauses or cancels a managed run, apply the durable control transition subcommand of `scripts/harness_transition.py` — `pause`, `resume`, or `cancel`, each requiring `--source`. A conversational stop is not scheduler state. Preserve active and dirty worktrees, then reconcile interrupted mission workers with `reconcile-interrupted` and stopped review workers together with `reconcile-interrupted-reviews` before any resume. Review reconciliation preserves the attempt evidence, restores lineage counters, removes ungrounded edge traversals, and leaves the run paused.
