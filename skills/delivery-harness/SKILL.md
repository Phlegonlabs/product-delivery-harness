---
name: delivery-harness
description: "Use only when the user explicitly requests delivery-harness or a requested skill workflow requires it. Route engineering work through planning, authorization, execution, verification and integration. Use direct delivery for one writer or a Direct Fan-Out with one verification sequence; use PLAN-v6/RUN-v11 for durable coordination, isolated integration or a bounded correction graph. Use agent-configured executors through observed tools or explicitly bound bridges."
---

# Delivery Harness

Run only on the user's explicit request, continuation, or a required dependency of that requested skill workflow.
A matching task, installation, discussion, source edit or existing project artifact does not activate it.
Required checks and dependencies stay within the requested outcome; a new top-level stage needs an explicit request.

Commands: `references/installed-commands.md`; direct cards: `references/stages/direct-cards.md`; stage cards: `references/stages/stage-cards.md`; launch brief: `assets/templates/HARNESS_GOAL.template.md`.

At every invocation, run the [entry checklist](references/governance/task-and-handoff.md#project-entry-and-current-work). For new delivery work, direct or managed, acceptance follows `references/delivery-acceptance-contract.md`. English PRD/architecture remain implementation authority, not Chinese review copies.

## Design And Maintenance Routing

Before Product-package execution, apply `references/pre-delivery-self-review.md#harness-entry`; missing or stale evidence blocks execution, not inspection or planning. Classify UI work under [Product Contracts](references/governance/product-contracts.md#consumer-keep-product-contracts-current).

Optional context: `references/reference-selection.md` (`references/option-library/`).

## Purpose

Use PLAN/RUN only when coordination requires it. Preserve upstream ownership:

- `product-definition-builder` owns approved `PRD.md`, `architecture.md`, and `stack-decisions.md`, including complete frontend/backend architecture and technology decisions.
- `ui-design-builder` owns UI Design Intake, PRD-led direction studies, HiFi checks, Visual Approval and the HiFi target. `design-system-compiler` owns a required design-system pair.
- Implement current approved product/stack and applicable UI sources. Every must-have `UX-*` trace still needs objective evidence. `Recommended` and `Provisional` stack rows are proposals. Do not invent product, copy, stack or design decisions.
- The security lens in `references/security-review.md` owns read-only review of the fixed integrated SHA; it neither remediates nor probes live targets.

## Project Size Gate

Classify work as `small` when one writer can own one bounded outcome in one checkout and verify it with one coherent local sequence; that writer may be the required delegated specialist. `small` also covers a few independent outcomes in different files ([Direct Fan-Out](references/direct-fan-out.md)). A high file count, language count, test duration, or reasoning difficulty does not make work `large` by itself.

Classify work as `large` only when at least one condition is true:

- a mission needs another mission's integrated output;
- a shared contract must be frozen, reviewed and integrated before dependents start;
- execution needs durable cross-session or cross-host handoff;
- a migration, destructive operation, or correction loop needs a durable bounded graph; or
- the user explicitly requests managed Harness orchestration.

Planning preference may choose the stricter route, but cannot override a `large` classification or any safety boundary.

```text
System Review And Route (parent-only, read-only)
  small -> direct inspect -> implement -> local verify -> review -> authorized Git actions
  large -> planner -> PLAN v6 + RUN v11 -> readiness -> managed execution
```

Small work creates no PLAN/RUN files. If scope grows, preserve evidence and plan the remainder. The Sequential Parent Route runs one mission at a time (`execution-state-model.md`). Preserve required independent reviews.

### System Review And Route

Within an explicitly requested `delivery-harness` workflow, complete this checkpoint before loading any task-specific skill. Read the request, repository instructions, Git state, requested scope, and relevant frozen product/design inputs. Do not create or edit `PLAN.md`, `RUN.md`, `tasks.md`, branches, worktrees, evidence, or implementation files during this checkpoint.

Record:

```text
Project size: small | large
Delivery profile: standard | mvp | program
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Route: direct | plan-backed graph
Host adapter: none | general (observed host identity or generic)
RUN landing: local_only
Post-archive publication: none | exact candidate branch
Upstream inputs: present | missing | needs owner decision
Gitignore impact: none | update | needs owner decision
Planned review points: <n> (<reasons>)
```

For UI work, inspect only `docs/design/`, a user-named design folder, and obvious in-scope images from the normal scan, record candidate paths and hashes, then apply `references/design-input-updates.md`; only PRD-approved consequences and any required compiled design-system pair influence implementation.

Record `Gitignore impact: none` unless the task introduces or retires a local-only file class; only then classify it with `references/gitignore-contract.md`. This applies to both direct and managed routes.

When an existing RUN is `running`, perform the Resume Reconciliation Gate in `references/execution-state-model.md` before selecting work. Start with `python "<delivery-harness-skill-root>/scripts/inspect_harness_run.py" --repo-root <target-root> --session-id <id>`; its `Next` block names the state and one recommended command, and a `running` RUN with no lock needs one owner decision before selection. Inspect host process/session evidence separately. Canonical state, live process state, Git heads, and dirty worktrees are separate evidence; never assume `worker_running` proves a live worker. For a package pinned to an earlier Harness version, also read [Legacy Pins](references/legacy/legacy-pins.md).

For a managed RUN, after capability detection, apply `references/runtime-upgrades.md`. Only an old compatible runtime's active wave may finish. An incompatible or restarted runtime waits for a fresh probe, then re-orchestrates every remaining task onto the new runtime through new attempts using that RUN's exact pinned bundle. Provider changes require explicit replanning; never hot-upgrade a worker or silently mutate installed runtime software.

### MVP Week

The owner-selected `mvp` profile targets one week from approved PRD to a verified release candidate for a small project or an MVP. It runs one combined review plus one re-check, folds Final UI Acceptance into that review, isolates every post-re-check defect, runs the broad suite once, and keeps at most four owner gates. Speed changes nothing else: the authorization ledger, the security lens on executable diffs, data safety, and exact-SHA binding still apply.

## Non-Negotiable Boundaries

These rules apply to both routes:

- Selecting this skill grants no mutation permission. Bind each state-changing action to the user's exact instruction and target.
- Preserve all 12 managed action keys in the [Authorization Action Ledger](references/execution-state-model.md#authorization-action-ledger).
- Execution intent covers only applicable local setup, branch, commit, and integration actions; it does not authorize `push`. Harness 0.38+ RUNs stay `local_only` with `push` false; after close, archive, publication and promotion follow stage Card 8. When the owner has recorded an Epic landing grant, a passing `scripts/landing_gate.py check` is the authorization for each action the grant names (`references/branch-promotion-contract.md#epic-landing-grant`).
- Freeze the remote `main` base in PLAN `branch_policy`; retain historical RUN pins. Never edit/commit on a protected branch or recreate one as a run branch. Follow `references/branch-promotion-contract.md#delivery-kind-and-base` and `references/branch-promotion-contract.md#protected-branches`; never force-push. Ask before creating that branch unless a signed launch brief names it; never add a fixed prefix.
- Archival, worktree removal, and branch deletion are separate actions, never implied by completion. A grant's `cleanup` action covers only the commands `scripts/landing_gate.py cleanup-plan` prints.
- The parent owns routing, authorization, PLAN/RUN, dispatch, leases, integration, and lifecycle actions. Workers and reviewers receive only their assigned actions. Pinned managed protocols retain parent-owned PLAN/RUN, integration and lifecycle transitions.
- A managed runtime review launches only from a persisted `reserve-review-dispatch` receipt for the selector's current directive. A raw runtime spawn is unplanned work; do not accept its result or reconstruct a receipt afterward.
- Non-mission nodes reserve with `reserve-node-attempt`, execute outside the RUN lock, then record evidence with `record-node-result`; interrupted attempts become `blocked`.
- A review PASS binds one exact SHA. Any repair invalidates it for the paths the repair touches; on the direct route, scope-disjoint bookkeeping commits carry it forward, and a scoped repair PASS re-binds the repaired paths (`references/verification-gates.md#review-topology`).
- Preserve failed, interrupted, cancelled, dirty, and partial worktree evidence. Never reset or remove it automatically.

## Direct Route

Run `references/stages/direct-cards.md#card-d1-direct-delivery` for every `small` task; only for an `initial_delivery`, add `references/stages/direct-cards.md#card-d2-initial-product`; only when the task changes UI, add `references/stages/direct-cards.md#card-d3-ui-change`. For direct work, do not read the managed stage files.

## Managed Stage Routing

Use this routing only when the size gate classifies work as `large`; then start each stage from its card in `references/stages/stage-cards.md`, and read the sections below when the card names them or a command fails. For direct work, do not read the managed stage file.

- When authoring PLAN, first read [Managed Route](references/stages/managed-delivery.md#managed-route), [Reference Routing](references/stages/managed-delivery.md#reference-routing), and [Plan Large Work](references/stages/managed-delivery.md#2-plan-large-work).
- When preparing readiness and dispatch, first read [Default Runtime And Wave Policy](references/stages/managed-delivery.md#default-runtime-and-wave-policy), [Default Mission Topology](references/stages/managed-delivery.md#default-mission-topology), and [Pass Plan Readiness](references/stages/managed-delivery.md#3-pass-plan-readiness).
- When using a managed runtime, first read [Adapter Routing](references/stages/managed-delivery.md#adapter-routing).
- When executing, first read [Execute And Integrate](references/stages/managed-delivery.md#4-execute-and-integrate).
- When verifying, first read [Verify Local-First](references/stages/managed-delivery.md#5-verify-local-first).
- When closing out, first read [Complete](references/stages/managed-delivery.md#6-complete).

## Repository Context Contract

Discover the effective instruction chain from repository root to the selected checkout.

- Existing `AGENTS.md`/`AGENTS.override.md`/`CLAUDE.md` are user-owned; never overwrite, normalize, silently copy.
- Entry runs `scripts/configure_project_context.py --root <target-root> --check --merge-agents`; without `--check`, only an authorized bootstrap creates missing files from `PROJECT_AGENTS.template.md` and `PROJECT_CLAUDE.template.md`; generated files differ. Existing AGENTS stays proposal-only until a reviewed plan binds original/template hashes, selected headings and acknowledged conflicts. Same-heading differences are unresolved semantic divergences. Resolve new Skill Bindings from observed skills with owner confirmation.
- Follow the current host's effective instruction precedence; never guess it from a provider name or inject another host's instructions.
- Keep automatic context discovery enabled. A nested instruction may narrow a mission, never widen write scope or authorization.

## UI Implementation Contract

When the task changes UI, read `references/ui-implementation-contract.md` before UI implementation or review.

- `design-system-compiler` alone owns compilation when the Design System Need Gate is `required`.
- UI implementation runs the bound frontend author under this Harness's conformance contract. Do not claim that skill defines conformance mode or reopen Style Integration.
- Initial/enhancement system-conformance uses current approved PRD, UI design, HiFi and pair; their responsive sets must agree. Target-conformance uses the approved target when the gate is `not_required`. For routine maintenance, follow `references/ui-implementation-contract.md`; a missing required input is a design-input delta.
- A page-faithful target binds implementation only after the user explicitly requests faithful conformance.
- When UI changed, Final UI Acceptance runs the Final Visual Parity Loop and the page-quality pass once, on the exact head, in the one review (`references/verification-gates.md#final-ui-acceptance`). Impeccable is not the default reviewer.
- Bundled defaults exist only for bundled skills. A project's owner-confirmed Skill Bindings table may bind installed external visual-direction, frontend-authoring, or UI-quality tools after their full trees and side effects are checked; an unresolved or incompatible slot blocks its dependent node.

## Workflow

### 1. Intake And Route

Run System Review And Route; the Resume Reconciliation Gate above covers a running RUN.

If the user pauses or cancels a managed run, apply the durable control transition subcommand of `scripts/harness_transition.py` — `pause`, `resume`, or `cancel`, each requiring `--source`. A conversational stop is not scheduler state. Preserve active and dirty worktrees, then reconcile interrupted mission workers with `reconcile-interrupted` and stopped review workers together with `reconcile-interrupted-reviews` before any resume.
