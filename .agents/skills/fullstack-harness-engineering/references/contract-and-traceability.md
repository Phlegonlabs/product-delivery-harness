# Contract And Traceability

Use this reference when the work starts from a PRD, wireframe, design system, architecture note, ticket set, screenshot, or broad full-stack idea.

## Contract Freeze

Freeze only the surfaces needed for the next implementation loop. Do not freeze speculative backlog.

Required full-stack freeze fields:

```text
Product: objective, users, workflows, must-have requirements, non-goals, success criteria
Architecture: module boundaries, data model, API/action contracts, auth, permissions, side effects
UI structure: routes, screens, navigation, regions, data-to-UI mapping, states
Visual design: design system, tokens, components, spacing, typography, breakpoints, interaction states
Verification: commands, E2E journey, evidence paths, acceptance thresholds
Write scope: allowed paths, read-only paths, destructive-action approval gates
```

For L full-stack, XL app, or parallel mission work, implementation starts only after the user accepts the freeze or explicitly authorizes assumptions.

## Source Map

Record every canonical input and its status:

```text
| Source | Path / URL | Owner | Status | Notes |
|---|---|---|---|---|
| PRD | <path> | human / team | draft / frozen | <summary> |
| Wireframe | <path or URL> | human / team | draft / frozen | <screens> |
| Design system | <path or URL> | human / team | draft / frozen | <tokens/components> |
| Architecture | <path> | Codex / team | draft / frozen | <contract surfaces> |
```

If an external source is unavailable, ask for screenshots, exports, or written specs before claiming design-faithful implementation.

## Trace IDs

Use stable IDs so implementation and verification can prove coverage:

```text
PRD-001 product requirement
ARCH-001 data/API/permission contract
UI-001 screen or journey requirement
DS-001 visual/component requirement
TEST-001 verifier or acceptance evidence
```

Rules:

- Upstream contract files mint IDs.
- Mission tasks and acceptance rows reference existing IDs.
- Every must-have PRD/UI/ARCH/DS ID needs at least one downstream task and one verification row.
- A trace ID with no downstream coverage is a launch blocker unless the user accepts it as out of scope.
- A task with no upstream trace ID is scope drift unless it is harness, test, cleanup, or explicitly approved.

## Harness Artifact Defaults

When no repo convention exists, use:

```text
docs/harness/HARNESS_PLAN.md
docs/harness/MISSION_RUNBOOK.md
docs/harness/E2E_VERIFICATION.md
docs/harness/GOAL.md
docs/harness/goals/M<n>_GOAL.md
docs/harness/evidence/<mission>/
docs/harness/evidence/<mission>/REPORT.md
```

When the repo already uses Epic artifacts, adapt to that structure rather than duplicating:

```text
docs/Epic{n}/SPEC.md
docs/Epic{n}/ARCHITECTURE.md
docs/Epic{n}/WIREFRAME.md
docs/Epic{n}/DESIGN_SPEC.md
docs/Epic{n}/MISSIONS.md
docs/Epic{n}/GOAL.md
docs/Epic{n}/goals/Mission{n}_GOAL.md
docs/Epic{n}/evidence/Mission{n}/
docs/Epic{n}/evidence/Mission{n}/REPORT.md
```

## Stop And Ask Conditions

Stop before implementation when:

- PRD and wireframe conflict on the primary flow.
- The design system contradicts the wireframe in a user-visible way.
- Auth, permissions, or destructive data behavior is ambiguous.
- Required secrets, services, databases, or browser tools are unavailable.
- The requested write scope would modify unrelated modules.
- The user has not approved overwrites, deletes, moves, resets, or worktree cleanup.
