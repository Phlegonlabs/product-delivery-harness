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

For L full-stack, XL app, or parallel mission work, implementation starts only after the plan readiness gate passes and execution is explicitly authorized. Selecting the skill or requesting a plan does not authorize implementation. User-authorized assumptions can resolve contract gaps but do not by themselves authorize code changes.

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

## Document Folder Handoff

When the user provides a document folder path, inspect that folder before drafting harness artifacts. Treat files in the folder as upstream sources and register recognized inputs in the source map.

Recognize common upstream files and folders:

```text
PRD.md
architecture.md
wireframes.md
implementation-plan.md
design-system.md
page-ui-matrix.md
page-ui-notes.md
ui-mockups.md
visual-acceptance.md
mockups/
screenshots/
figma-refs.md
```

Rules:

- Do not require upstream files to come from a specific skill or pipeline.
- Do not write harness-owned artifacts into the upstream document folder unless the user explicitly asks for that location.
- If design-system or page UI sources are missing and UI quality matters, classify the design input state as `missing` or `partial` and stop for acceptance or assumptions before claiming a design-faithful build.
- If a page UI reference omits states or breakpoints, record the gap in the handoff readiness table and resolve it before implementation or mark the surface `UNVALIDATED`.

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

## Compact Artifact Defaults

When no repo convention exists, enforce this file budget:

```text
direct work        -> no management files
medium work        -> docs/goal/RUN.md
long/multi-mission -> docs/goal/PLAN.md + docs/goal/RUN.md
real binary proof  -> docs/goal/evidence/** only when needed
```

Keep Goal text, checkpoint, task state, verification, evidence links, blockers, and closeout together in `RUN.md`. Use temporary `docs/goal/evidence/M<n>/REPORT.md` files only for parallel worker integration, then fold their durable result into `RUN.md`.

When the repo already uses Epic artifacts, adapt to that structure rather than duplicating. Prefer one plan file and one live run file:

```text
docs/Epic{n}/SPEC.md
docs/Epic{n}/RUN.md
docs/Epic{n}/evidence/  # only when real artifacts exist
```

## Stop And Ask Conditions

Stop before implementation when:

- `RUN.md` is not `ready`, the Plan Readiness Gate has required rows that are not `PASS`, or `execution_authorized` is false.
- PRD and wireframe conflict on the primary flow.
- The design system contradicts the wireframe in a user-visible way.
- Auth, permissions, or destructive data behavior is ambiguous.
- Required secrets, services, databases, or browser tools are unavailable.
- The requested write scope would modify unrelated modules.
- The user has not approved overwrites, deletes, moves, resets, or worktree cleanup.
