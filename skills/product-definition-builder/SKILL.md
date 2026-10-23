---
name: product-definition-builder
description: Create or refine owner-approved Product Definition packages from user needs, including discovery, measurable requirements, UI surface behavior, data/trust and AI gates, implementation-ready backend and frontend architecture, coherent owner-approved technology and commercial stack decisions, release targets, tests, and sourced market reconciliation. Use for PRDs, product specs, architecture, backend/data/auth/deployment choices, frontend stack choices, and product research. It stops at Product Definition Approval and hands UI-bearing products to ui-design-builder; it does not create wireframes or visual design.
---

# Product Definition Builder

## Installed Commands

Resolve `<product-definition-builder-skill-root>` and logical script paths as [Installed Commands](../delivery-harness/references/installed-commands.md) states.

## Overview

At every invocation, run the [entry checklist](../delivery-harness/references/governance/task-and-handoff.md#project-entry-and-current-work).

For a UI enhancement, hand off the added/changed UI IDs and necessary entry or return paths, with all other surfaces explicitly preserved. Follow `../ui-design-builder/references/enhancement-recommendations.md`'s Incremental UI Scope for the downstream boundary; do not request a fresh all-screen design package or reset unaffected approvals.

Before approval, define test personas (role, tenant, account/data state), applicable Web/native/agent journeys, observable success and denial/no-side-effect assertions, and mock versus real-sandbox obligations in the existing TEST rows and architecture testing section. Record non-applicability rather than inventing login for a headless or unauthenticated product. The downstream Harness freezes the executable matrix and owns fixtures and evidence through `../delivery-harness/references/delivery-acceptance-contract.md`; this skill creates no accounts or evidence register.

Use this skill to turn a product idea into a decision-ready package, not an agent-selected implementation guess. Define product scope, journeys, UI surface responsibilities, routes, actions, states, data, trust, and security boundaries, acceptance signals, implementation architecture, release targets, and technology constraints. Draft and reconcile `PRD.md`, `architecture.md`, and `stack-decisions.md`; present coherent frontend, backend/data/auth, mobile/desktop, AI, deployment, and commercial technology options; then obtain an explicit Stack Decision Checkpoint and Product Definition Approval. Stop there. A later explicit UI request invokes `ui-design-builder`; a later implementation request invokes `delivery-harness` against approved inputs.

## Stage Routing

Read the owning section before its matching action. Domain guides stay conditional.

- Before a definition or enhancement starts, read [Workflow](references/stages/product-definition.md#workflow) and [Interview Rules](references/stages/product-definition.md#interview-rules). Enhancement mode first uses its scoped delta branch and does not force an initial interview.
- Before Product Definition Approval is requested, read [Self-Review Before Product Definition Approval](references/stages/product-definition.md#self-review-before-product-definition-approval).
- Before a UI handoff is prepared, read [Current UI Preflight](references/stages/product-definition.md#current-ui-preflight).
- Before applicable domain decisions are resolved, read the guides that Workflow step 9 names.
- Actual initial drafting follows the complete required procedure in [Workflow](references/stages/product-definition.md#workflow).

## Entry Boundary

- `PRD.md` and `architecture.md` remain the canonical English implementation sources; complete Chinese review copies remain required.
- Product Definition Approval and the Stack Decision Checkpoint are explicit owner gates.
- Enhancement preserves the same current PRD and stable IDs.
- No UI design, implementation, PLAN/RUN, or E2E evidence register starts here.
- A completed package does not launch downstream work automatically. The package creates no wireframe, design system, production component, or Harness mission map.
