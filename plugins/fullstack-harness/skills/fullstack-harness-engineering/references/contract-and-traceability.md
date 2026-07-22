# Contract And Traceability

Use this reference when the work starts from a PRD, wireframe, design system, architecture note, ticket set, screenshot, or broad full-stack idea.

## Contract Freeze

Freeze only the surfaces needed for the next implementation loop. Do not freeze speculative backlog.

Required full-stack freeze fields:

```text
Product: objective, users, workflows, must-have requirements, non-goals, success criteria
Builder UX direction: human decision owner, experience priority, guidance/control, density, interaction/layout, confirmation/recovery, validation depth, and selected/provisional/assumed status. When the source PRD came from `prd-builder`, its `PRD.md` Builder UX Direction table (see that skill's `references/output-contract.md`) is the authority for each axis's valid values, e.g. experience priority is one of speed/clarity/guided completion/expert control/exploration/conversion/comprehension, guidance and control is guided/balanced/expert-flexible, and information density is sparse/balanced/dense. When no such upstream table exists, resolve each axis's value with the human decision owner instead of inventing terminology.
Architecture: module boundaries, data model, API/action contracts, auth, permissions, side effects
UI structure: routes, screens, navigation, regions, data-to-UI mapping, states
Visual design: design system, tokens, components, spacing, typography, breakpoints, interaction states
Verification: commands, E2E journey, evidence paths, acceptance thresholds
Write scope: allowed paths, read-only paths, destructive-action approval gates
```

For large work, including parallel mission work, implementation starts only after the plan readiness gate passes and execution is explicitly authorized. Selecting the skill or requesting a plan does not authorize implementation. User-authorized assumptions can resolve contract gaps but do not by themselves authorize code changes.

## Canonical Harness State

For long or multi-mission work, keep one versioned plan and one live run record. See `execution-state-model.md`'s "Three Authorities" table for exactly what `PLAN.md`, `RUN.md`, and observed Git/runtime facts each own; do not re-derive that split here.

The parent/coordinator is the sole writer of `PLAN.md` and `RUN.md` during execution. Workers return structured results or refinement requests and never edit either file. Every accepted plan change increments `plan_revision`; recompute the canonical plan digest, validate both DAGs, and invalidate any wave proposal bound to the previous revision or digest.

## Source Map

Record every canonical input and its status:

```text
| Source | Path / URL | Content SHA-256 / immutable revision | Owner | Status | Notes |
|---|---|---|---|---|---|
| PRD | <path> | <hash or revision> | human / team | draft / frozen | <summary> |
| Builder UX direction | <PRD section, path, or URL> | <hash or revision> | human decision owner | selected / provisional / assumed | <direction and validation needs> |
| Wireframe | <path or URL> | <hash or revision> | human / team | draft / frozen | <screens> |
| Design system | <path or URL> | <hash or revision> | human / team | draft / frozen | <tokens/components> |
| Architecture | <path> | <hash or revision> | Codex / team | draft / frozen | <contract surfaces> |
```

For plan-backed work, the PLAN JSON `sources` array is canonical; the table is its human view. Every schema-v4 source includes `content_sha256`, an immutable `source_revision`, or both. A mutable path or URL without either binding is not frozen. Recompute the PLAN digest and invalidate old attempts whenever source content or its upstream revision changes. Each trace references `source_ids` and records `priority`, `disposition`, and any disposition `rationale`. Canonical `ui_surfaces`, `risks`, mission `stop_conditions`, and verifier arrays are likewise the static source of truth; any Markdown table showing them elsewhere is a view only.

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
ui-mockups.md
visual-acceptance.md
mockups/
screenshots/
figma-refs.md
```

Rules:

- Do not require upstream files to come from a specific skill or pipeline.
- Do not write harness-owned artifacts into the upstream document folder unless the user explicitly asks for that location.
- When `implementation-plan.md` is present, read its `Harness Handoff Signals` table (dependency order, parallel candidates, shared resources, required reviews, human gates) as non-canonical planning hints before drafting the mission graph from scratch, instead of re-deriving the same analysis unassisted.
- If design-system or page UI sources are missing and UI quality matters, classify the design input state as `missing` or `partial` and stop for acceptance or assumptions before claiming a design-faithful build.
- If a page UI reference omits states or breakpoints, record the gap in the handoff readiness table and resolve it before implementation or mark the surface `UNVALIDATED`.
- For every platform (web, native iOS/Android/Flutter, macOS, Windows), `mockups/*.html` is the per-page visual and structural source of truth — a real, viewable HTML file styled to the resolved platform's own conventions, treated like a Figma export: reimplemented in the project's real framework (a web stack, SwiftUI, Jetpack Compose, a Flutter widget tree, or WinUI/.NET), never shipped as-is. `page-ui-matrix.md` is normally absent; its route/trace/test mapping lives in `ui-mockups.md`'s index instead. Do not treat a missing `page-ui-matrix.md` as a gap when `mockups/*.html` and that index are present.
- When `architecture.md`'s Frontend Technology Decision is `Selected` or `Recommended` and no matching framework/UI-library/styling stack exists in the repository yet, that decision is the scaffold mission's install target: every named layer (deployment/runtime, framework, UI library, build tool, styling/components) becomes a task in mission M1, not just the framework. See `platform-archetypes.md`'s Greenfield / Empty Repository section and `HARNESS_PLAN.template.md`'s workspace-foundation example. A layer still `Provisional` is a stop condition, not a default guess.

## Trace IDs

Use stable IDs so implementation and verification can prove coverage:

```text
PRD-001 product requirement
ARCH-001 data/API/permission contract
UI-001 screen or journey requirement
UX-001 critical task, interaction/recovery, or usability requirement
DS-001 visual/component requirement
TEST-001 verifier or acceptance evidence
```

Rules:

- Upstream contract files mint IDs.
- Mission tasks and acceptance rows reference existing IDs.
- Every must-have PRD/UI/UX/ARCH/DS ID needs at least one downstream task and one verification row.
- The archetype-specific families in `platform-archetypes.md`'s "Trace ID Families" (including the native `APPSHELL-*`, `CAP-*`, `STORE-*`, and `SIGN-*` families) get the same enforcement as the six core families: any such ID carrying a must-have requirement needs at least one downstream task and one verification row, and is a launch blocker when uncovered.
- A trace ID with no downstream coverage is a launch blocker unless the user accepts it as out of scope.
- A task with no upstream trace ID is scope drift unless it is harness, test, cleanup, or explicitly approved.
- Executable missions/tasks reference only traces with `disposition: planned`. `deferred` and `out_of_scope` traces require rationale and do not count as uncovered executable work until reclassified in a new plan revision.

## Mission And Task Identity

Use opaque, immutable IDs for references and separate aliases for readable labels:

```text
Mission ID: M1
Task ID: M1/T01
Alias: implement-session-contract
```

Rules:

- Do not encode execution order, filenames, owners, or nesting beyond the mission prefix into identity semantics.
- Keep tasks in one flat namespace. Express dependencies with `depends_on` and refinement lineage with `parent_task` / `replaced_by`.
- Preserve imported identifiers in `legacy_task_ids`; never reuse an old ID for a different outcome.
- A worker may request decomposition but cannot mint accepted tasks or change the plan revision. Follow `execution-task-decomposition.md` for the bounded refinement protocol.

## Compact Artifact Defaults

When no repo convention exists, apply `SKILL.md`'s File Budget. Use temporary `docs/goal/evidence/<mission>/REPORT.md` files only for parallel worker integration, then fold their durable result into `RUN.md`.

Do not duplicate canonical manifest fields into another state database. If the target repository already has an execution-state convention, map these ownership rules into it and document the mapping instead of creating competing truth sources.

When the repo already uses Epic artifacts, adapt to that structure rather than duplicating. Prefer one plan file and one live run file:

```text
docs/Epic{n}/SPEC.md
docs/Epic{n}/RUN.md
docs/Epic{n}/evidence/  # only when real artifacts exist
```

## Stop And Ask Conditions

Stop before implementation when:

- `RUN.md` is not `ready`, the Plan Readiness Gate has required rows that are not `PASS`, or `execution_authorized` is false.
- The requested action is false or absent in the authorization ledger. General execution permission does not imply task creation, worktree creation, commits, integration, push, PR, deploy, archival, or cleanup permission.
- PRD and wireframe conflict on the primary flow.
- Builder UX Direction is missing for UI-bearing work, its decision owner is unclear, or it conflicts with user evidence or accessibility without a recorded hypothesis and validation decision.
- The design system contradicts the wireframe in a user-visible way.
- The design source's mockup HTML is styled to a different platform than the resolved target — for example web viewport/breakpoint styling and web-family icons handed off for a native iOS/Android/Flutter/desktop mission, or the reverse. Every platform's mockup is real HTML (see `design-package-builder`'s Platform-Conditional Vocabulary), so the mismatch to catch here is the visual convention, not the file format. Do not silently implement against a mismatched-styling mockup or guess the intended platform; confirm with the user first. See `verification-gates.md`'s "Capture Mechanism By Platform" for how the resolved platform separately decides the UI evidence capture mechanism after implementation.
- Auth, permissions, or destructive data behavior is ambiguous.
- Required secrets, services, databases, or browser tools are unavailable.
- The requested write scope would modify unrelated modules.
- The user has not approved overwrites, deletes, moves, resets, or worktree cleanup.
- The canonical plan/run manifest is missing, invalid, stale, or inconsistent with the proposed wave.
- A PLAN-v4 graph does not cover every mission's write scope with at least one review-type node (`backend_code`/`frontend_code`/`visual` as applicable), regardless of `landing.mode`. `local_only` runs get no independent GitHub/Codex review at merge time, so this graph-level review is their only review gate — it is not optional there just because `pull_request` mode would add a second one.
