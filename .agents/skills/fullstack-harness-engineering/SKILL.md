---
name: fullstack-harness-engineering
description: Build full-stack Codex harness plans from new or updated PRDs, wireframes, design systems, page-specific UI references, architecture notes, broad app ideas, or already-built apps that need refinement. Use when the user asks for end-to-end implementation workflow, Codex /goal planning, worktree or thread orchestration, mission decomposition, verification gates, UI evidence, full-stack acceptance, product/app refinement, UX polish, performance/accessibility/SEO improvement, design-input updates, page UI implementation, or a complete harness engineering process for frontend/backend/data/API work. Do not use for small bounded code edits, simple reviews, or one-off questions that do not need a durable implementation loop.
---

# Full-Stack Harness Engineering

## Purpose

Use this skill to turn product, design, and architecture inputs into a full-stack implementation harness: frozen contracts, mission slices, worktree/thread orchestration, an execution loop, and end-to-end verification evidence.

Keep the main prompt short. Put durable context, traceability, mission state, and verification evidence in files when the work is large enough to survive compaction, handoff, or parallel execution.

## Terminology

Use `app` as the umbrella product term. In this skill, an app can be a public website, marketing site, docs/content site, ecommerce/catalog experience, conversion landing page, authenticated web app, SaaS platform, dashboard, internal tool, backend-backed workflow, or a hybrid of these.

## Reference Routing

- Read `references/contract-and-traceability.md` when PRDs, wireframes, design systems, data/API contracts, permissions, or freeze rules matter.
- Read `references/design-input-updates.md` when the user provides new or updated PRDs, wireframes, design-system changes, screenshots, Figma/page UI references, or page-specific UI targets for a new build or existing-app refinement.
- Read `references/platform-archetypes.md` when adapting the harness to authenticated apps, SaaS, internal tools, public websites, marketing sites, docs/content sites, ecommerce/catalog, or conversion landing pages.
- Read `references/existing-app-refinement.md` when the app already exists and the user wants polish, UX refinement, performance, accessibility, SEO, conversion, reliability, cleanup, or evidence-backed improvement.
- Read `references/worktree-thread-orchestration.md` when the work uses multiple missions, worktrees, subagents, worker threads, or parent-thread integration.
- Read `references/verification-gates.md` when defining deterministic checks, UI evidence, backend/data checks, end-to-end tests, release gates, or evidence schemas.
- Use `assets/templates/HARNESS_PLAN.template.md`, `MISSION_RUNBOOK.template.md`, `E2E_VERIFICATION.template.md`, and `GOAL.template.md` when creating durable harness artifacts.

## Core Rules

- Use Direct Work for small bounded edits. Do not create harness files, worktrees, or goals for one-file fixes unless the user explicitly asks.
- Select a product archetype before drafting contracts. `App` is broad; choose the concrete shape: authenticated app, SaaS platform, internal tool, public website, marketing site, docs/content site, ecommerce/catalog, conversion landing page, or hybrid.
- Treat updated PRDs, wireframes, design systems, and page UI references as contract deltas. Compare them against the current contract or app baseline before implementation.
- For existing-app refinement, capture the current baseline before proposing changes. Do not replace working behavior or redesign scope without an accepted refinement target.
- For full-stack or long-running work, freeze the contract before implementation: product scope, architecture/data/API, UI flow, and visual design.
- Every requirement that matters to acceptance needs a trace ID. Mission tasks and verification rows reference existing IDs; they do not invent new product scope.
- Treat deterministic verification as the hard gate. LLM review is useful critique, not final proof.
- A loop iteration counts as progress only when a verifier improves, an acceptance row becomes PASS with evidence, a task is committed after verification, or a blocker is narrowed with new reproducible evidence.
- Do not claim completion without recorded evidence: command, exit code, browser trace/screenshot path, metric, log, commit hash, or explicit human approval.
- Use worktrees only when isolation helps: parallel missions, high-risk changes, full-stack slices, UI/API/data work that can conflict, or long-running background work.
- Parent thread owns planning, mission state, merge order, integration verification, and shared harness docs. Worker threads own exactly one mission and report evidence; they do not edit shared state files directly during parallel execution.
- Before deleting, overwriting, moving, resetting, or cleaning worktrees, ask the user.
- Recommend Extra High reasoning when the runtime exposes it for long, agentic, high-ambiguity harness planning; do not encode model-specific assumptions into artifacts unless the user asks.

## Workflow

### 1. Intake And Route

Classify before creating files:

```text
Mode: direct-work | harness-plan | refinement-audit | refinement-loop | create-goal | execute-loop | audit-harness
Objective:
Existing inputs: PRD | updated PRD | wireframe | updated wireframe | design system | updated design system | page UI reference | architecture | tickets | screenshots | codebase
Input change type: new build | spec update | page UI update | design-system update | refinement delta | hybrid
Existing app state: greenfield | built app | deployed app | legacy app | partially implemented
Product archetype: authenticated app | SaaS platform | internal tool | public website | marketing site | docs/content site | ecommerce/catalog | conversion landing page | hybrid
Critical surfaces: auth | tenant | roles | billing | admin | content/CMS | SEO | analytics | catalog | checkout | integrations | compliance
Scale: small | single-mission | multi-mission | full-stack | program
Contract state: missing | draft | frozen | update proposed | delta accepted
Design input state: missing | provided | partial | conflicting | frozen | updated
Refinement lenses: UX | visual polish | performance | accessibility | SEO | conversion | reliability | test coverage | code quality | security | release readiness
UI Evidence Gate: required | optional | n/a
Worktree strategy: none | single worktree | mission worktrees | Codex-managed app worktrees
Verification surface: build | lint | typecheck | unit | integration | api | db | e2e | browser | accessibility | performance | release
Allowed actions: answer-only | create-docs | edit-code | run-verifiers | create-commits | spawn-subagents | create-worktrees
Stop or ask when:
```

If the answer is Direct Work, do the bounded task and stop. If the request asks to improve an existing app without a concrete target, use `refinement-audit` first and produce a ranked backlog rather than editing immediately. If the request needs a reusable plan, create or update durable harness docs.

### 2. Build The Contract

For full-stack work, produce or update the smallest durable contract set:

- `docs/harness/HARNESS_PLAN.md`: source map, product contract, architecture/data/API summary, UI/design contract, traceability matrix, mission map, worktree plan, risk gates.
- `docs/harness/MISSION_RUNBOOK.md`: mission sections, task queue, acceptance rows, attempt log, worktree/thread assignments, checkpoint, changed files, commits, blockers.
- `docs/harness/E2E_VERIFICATION.md`: final verification matrix and evidence register.
- `docs/harness/GOAL.md`: copy-ready `/goal` prompt when the user wants a long-running Codex goal.

When updated PRDs, wireframes, design systems, or page UI references are provided, record the delta: source version, changed requirements, affected pages/components, new acceptance gates, superseded assumptions, and unresolved conflicts. For existing apps, map the delta to both current baseline and target state.

For existing-app refinement, add a baseline and backlog section to the harness plan, or create `docs/harness/REFINEMENT_BACKLOG.md` from `assets/templates/REFINEMENT_BACKLOG.template.md` when the audit produces multiple candidate improvements.

If the target repo already has established Epic artifacts such as `docs/Epic{n}/SPEC.md`, `MISSIONS.md`, and `GOAL.md`, use that shape instead of creating a separate `docs/harness/` folder. Preserve local conventions.

Read an existing target file before changing it. Prefer gap-fill edits. If a file is not template-produced and needs a major rewrite, stop and ask.

### 3. Decompose Missions

Use vertical slices when possible. A common full-stack sequence is:

```text
Mission 1: foundation, environment, schema, auth, seed data
Mission 2: backend API, services, validation, permissions
Mission 3: frontend routes, screens, state/data wiring
Mission 4: design system implementation, responsive and interaction states
Mission 5: integration and end-to-end verification
Mission 6: release notes, docs, cleanup, if user/operator impact exists
```

Load the matching platform profile and add only relevant missions. Examples:

- SaaS/authenticated app: tenant/account model, auth lifecycle, roles/admin, billing/entitlements, audit/observability, webhook/job integrations.
- Public/content site: content/CMS foundation, page templates, SEO/metadata, analytics/conversion, responsive/visual QA, crawl/deployment validation.
- Ecommerce/catalog: catalog data, PDP/PLP/search/filtering, pricing/inventory, cart/checkout boundary if in scope, schema markup and analytics.
- Existing app refinement: baseline capture, issue ranking, smallest accepted improvement, regression protection, targeted implementation, before/after verification.
- Spec/design update: delta audit, contract update, page/component ownership, implementation, conformance verification, regression protection.

Parallelize only missions with disjoint write scopes and satisfied dependencies. Serialize migrations, shared clients, design tokens, global config, and any file touched by multiple missions.

### 4. Define The Loop

Each mission uses this loop:

```text
observe -> choose the smallest ready task -> implement only that task -> run its verifier -> record evidence -> commit if allowed -> update mission state -> choose next task or report blocker
```

Guardrails:

- One task per iteration.
- Commit only after task-specific verification passes.
- Stop after 3 consecutive no-progress iterations.
- Do not retry the same failed approach more than twice.
- If a verifier is missing, create or define the verifier first, or mark the surface `UNVALIDATED`.
- If verification cannot run, record why and name residual risk.

### 5. Orchestrate Worktrees And Threads

For multi-mission work, the parent thread creates the mission table and worktree plan before workers start. Use one worktree per independent mission when running in parallel.

Worker thread contract:

```text
Read: frozen contract files and only this mission's section.
Write: only the mission write scope.
Do not edit: shared harness docs, frozen contracts, unrelated files.
Verify: run the mission verifier and record literal pass/fail evidence.
Report: changed files, commands, exit codes, evidence paths, commit hash, blockers, residual risk.
```

The parent thread integrates in dependency and merge order, reruns each mission's verifier after merge, then runs the final E2E gate.

### 6. Verify And Close

End-to-end completion requires:

- Contract coverage: every must-have trace ID has downstream task and verification coverage.
- Code health: build/lint/typecheck/unit checks pass or skipped checks are justified.
- Backend/data: API, validation, permission, migration, seed/reset, and failure paths pass.
- Platform gates: archetype-specific auth/tenant/billing/content/SEO/analytics/catalog/deployment gates pass or are explicitly marked `UNVALIDATED`.
- Refinement gates: before/after evidence proves the accepted target improved or did not regress.
- Design-input gates: implemented pages/components match the accepted PRD/wireframe/design-system/page UI delta, and superseded behavior is intentionally handled.
- UI: primary journey, responsive breakpoints, loading/empty/error/disabled states, console/network health, accessibility, and design comparison pass when applicable.
- Integration: merged branch passes the E2E matrix.
- Evidence: commands, exit codes, artifacts, screenshots/traces, metrics, and commit hashes are recorded.
- Residual risk: every `UNVALIDATED` surface is named.

## Output Shape

For planning:

```text
Harness route:
Contract files:
Mission map:
Worktree/thread plan:
Verification gates:
Goal prompt:
Stop/ask conditions:
Next action:
```

For execution closeout:

```text
Outcome:
Evidence:
Changed files:
Commits:
Unvalidated surfaces:
Residual risk:
Next loop:
```
