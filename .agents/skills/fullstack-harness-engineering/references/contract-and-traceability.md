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
Visual design: design system, tokens, primitives and their closed variant sets, product components, registered motion variants, page recipes, breakpoints, interaction states
Verification: commands, E2E journey, evidence paths, acceptance thresholds
Write scope: allowed paths, read-only paths, destructive-action approval gates
```

For large work, including parallel mission work, implementation starts only after the plan readiness gate passes and execution is explicitly authorized. Selecting the skill or requesting a plan does not authorize implementation. User-authorized assumptions can resolve contract gaps but do not by themselves authorize code changes.

## Canonical Harness State

For long or multi-mission work, keep one versioned plan and one live run record. See `execution-state-model.md`'s "Three Authorities" table for exactly what `PLAN.md`, `RUN.md`, and observed Git/runtime facts each own; do not re-derive that split here.

The parent/coordinator is the sole writer of `PLAN.md` and `RUN.md` during execution. Workers return structured results or refinement requests and never edit either file. Every accepted plan change increments `plan_revision`; recompute the canonical plan digest, validate both DAGs, and invalidate any wave proposal bound to the previous revision or digest.

### Starting A New Plan vs Extending The Current One

When `docs/goal/PLAN.md`/`RUN.md` already exist, decide whether new work extends the current plan or starts a new one:

- Extend the current plan (a new `plan_revision` on the same `PLAN.md`/`RUN.md`) when the new work is incremental discovery inside the same ongoing initiative and its upstream contract sources (PRD, design system, architecture) have not materially changed.
- Start a new plan when the new work is anchored by a freshly regenerated upstream contract source — for example `prd-builder` or `ui-architecture-builder` just published a new or refreshed `PRD.md`/`design-system.md` with a new `content_sha256` — signaling a distinct new initiative rather than a continuation of the prior plan's frozen contract.
- To start a new plan: first confirm the current `PLAN.md`/`RUN.md` actually reached the Closeout Bar (`verification-gates.md`). Archive the completed `PLAN.md` and `RUN.md`, plus their `docs/goal/evidence/` directory, into `docs/goal/archived/<YYYYMMDD-HHMMSS>-<initiative-slug>/`, mirroring the same archival convention `prd-builder` and `ui-architecture-builder` already use for their own superseded documents. Then create a fresh `docs/goal/PLAN.md`/`RUN.md` from the templates and freeze the new contract from the newly published upstream sources.
- Do not silently overwrite an unarchived `PLAN.md`/`RUN.md` to start the new plan — that destroys the only record of what the prior plan covered and how it was verified.

## Source Map

Record every canonical input and its status:

```text
| Source | Path / URL | Content SHA-256 / immutable revision | Owner | Status | Notes |
|---|---|---|---|---|---|
| PRD | <path> | <hash or revision> | human / team | draft / frozen | <summary> |
| Builder UX direction | <PRD section, path, or URL> | <hash or revision> | human decision owner | selected / provisional / assumed | <direction and validation needs> |
| Wireframe | <path or URL> | <hash or revision> | human / team | draft / frozen | <screens> |
| Design system | <path or URL> | <hash or revision> | human / team | draft / frozen | <tokens/components> |
| UI architecture | <path> | <hash or revision> | human / team | draft / frozen | <layers, precedence, state matrix, definition of done> |
| UI registry | <path> | <hash or revision> | human / team | draft / frozen | <primitives, closed variant sets, motion variants, components, recipes> |
| Page recipes | <path> | <hash or revision> | human / team | draft / frozen | <routes covered, route → mockup → trace → test index> |
| Architecture | <path> | <hash or revision> | Codex / team | draft / frozen | <contract surfaces> |
| Stack decisions | <path> | <hash or revision> | human / team | required / selected / recommended / provisional | <resolved frontend, backend/data, mobile/desktop layers> |
| Page mockups + catalog | <mockups/ path> | <hash or revision> | human / team | draft / frozen | <one HTML file per route, plus catalog.html> |
| Visual acceptance | <path> | <hash or revision> | human / team | draft / frozen | <TEST-VIS-* gates required for the in-scope surfaces> |
```

For plan-backed work, the PLAN JSON `sources` array is canonical; the table is its human view. Every current PLAN-v5 source includes `content_sha256`, an immutable `source_revision`, or both. A mutable path or URL without either binding is not frozen. Recompute the PLAN digest and invalidate old attempts whenever source content or its upstream revision changes. Each trace references `source_ids` and records `priority`, `disposition`, and any disposition `rationale`. Canonical `ui_surfaces`, `risks`, mission `stop_conditions`, and verifier arrays are likewise the static source of truth; any Markdown table showing them elsewhere is a view only.

If an external source is unavailable, ask for screenshots, exports, or written specs before claiming design-faithful implementation.

## Document Folder Handoff

When the user provides a document folder path, inspect that folder before drafting harness artifacts. Treat files in the folder as upstream sources and register recognized inputs in the source map. This is commonly `docs/product/` when `prd-builder` and `ui-architecture-builder` published there, but the harness does not assume a fixed path — take whatever folder the user names.

Recognize common upstream files and folders:

```text
PRD.md
architecture.md
stack-decisions.md
wireframes.md
implementation-plan.md
ui-architecture.md
ui-registry.json
page-recipes.md
design-system.md
visual-acceptance.md
mockups/
screenshots/
figma-refs.md
```

Rules:

- Do not require upstream files to come from a specific skill or pipeline.
- Do not write harness-owned artifacts into the upstream document folder unless the user explicitly asks for that location.
- When `implementation-plan.md` is present, read its `Harness Handoff Signals` table (dependency order, parallel candidates, shared resources, required reviews, human gates) as non-canonical planning hints before drafting the mission graph from scratch, instead of re-deriving the same analysis unassisted.
- `ui-architecture.md`, `ui-registry.json`, and `page-recipes.md` are binding contract sources, not advisory notes. Freeze all three with a `content_sha256` alongside `design-system.md`, and give each its own source row. Freeze `mockups/` the same way — one row covering the per-route files and `catalog.html`, as `HARNESS_PLAN.template.md`'s Source Map expects — because a changed mockup changes the visual source of truth a page mission implements against. A mockup edit invalidates the PLAN digest exactly like an edit to the other four, and reaches implementation through `design-input-updates.md`, not by a mission quietly following the newer file. `ui-architecture.md` fixes the layer model, source-of-truth precedence, content contracts, primitive contracts with closed variant sets, product components, motion architecture, state matrix, guardrail requirements, definition of done, and adoption sequence; `ui-registry.json` is the machine-readable allowlist an implementation agent and a contract check both read; `page-recipes.md` fixes each route's recipe and carries the route → mockup file → upstream trace IDs → DS IDs → TEST IDs index. `ui-architecture-builder`'s `references/ui-architecture-guide.md` holds the architecture itself — read it there rather than restating it in harness artifacts.
- The precedence in `ui-architecture.md` decides every conflict between design sources: product rules beat content contracts, which beat page recipes, which beat product components, which beat primitive contracts, which beat design tokens, which beat any page-specific preference. A mission may not resolve such a conflict by picking the more convenient source.
- If design-system, `ui-architecture.md`, `ui-registry.json`, `page-recipes.md`, or the `mockups/` set is missing and UI quality matters, classify the design input state as `missing` or `partial` and stop for acceptance or assumptions before claiming a design-faithful build. An in-scope route with no mockup file is `partial`, not a route to implement from the recipe alone. A route with no recipe in `page-recipes.md` is a blocker for that route, not an invitation to improvise it.
- If a page recipe omits states or breakpoints, record the gap in the handoff readiness table and resolve it before implementation or mark the surface `UNVALIDATED`. The required responsive set comes from `ui-registry.json`: `viewports` for a web target or `sizeClasses` for a native or desktop target, exactly one of the two. The harness does not carry its own default set — an absent or empty set is a `partial` design input, not a cue to assume common breakpoints.
- For every platform (web, native iOS/Android/Flutter, macOS, Windows), `mockups/*.html` is the per-page visual and structural source of truth — a real, viewable HTML file styled to the resolved platform's own conventions, treated like a Figma export: reimplemented in the project's real framework (a web stack, SwiftUI, Jetpack Compose, a Flutter widget tree, or WinUI/.NET), never shipped as-is. `mockups/catalog.html` is the component catalog: every token, primitive variant, and component state under realistic content, and the reference a visual review opens instead of hunting through routes. `page-ui-matrix.md` is retired and normally absent; its route/trace/test mapping lives in `page-recipes.md`'s index instead. Do not treat a missing `page-ui-matrix.md` as a gap when `mockups/*.html` and that index are present.
- When `stack-decisions.md`'s Frontend Technology Decision is `Selected` or `Recommended` and no matching framework/UI-library/styling stack exists in the repository yet, that decision is the scaffold mission's install target: every named layer (deployment/runtime, framework, UI library, build tool, styling/components) becomes a task in mission M1, not just the framework. See `platform-archetypes.md`'s Greenfield / Empty Repository section and `HARNESS_PLAN.template.md`'s workspace-foundation example. A layer still `Provisional` is a stop condition, not a default guess.

## Trace IDs

Use stable IDs so implementation and verification can prove coverage:

```text
PRD-001 product requirement
ARCH-001 data/API/permission contract
UI-001 screen or journey requirement
UX-001 critical task, interaction/recovery, or usability requirement
DS-001 visual/component requirement (token, primitive variant, product component, motion variant, or page recipe)
TEST-001 verifier or acceptance evidence
```

Rules:

- Upstream contract files mint IDs.
- Mission tasks and acceptance rows reference existing IDs.
- Every must-have PRD/UI/UX/ARCH/DS ID needs at least one downstream task and one verification row.
- The archetype-specific families in `platform-archetypes.md`'s "Trace ID Families" (including the native `APPSHELL-*`, `CAP-*`, `STORE-*`, and `SIGN-*` families) get the same enforcement as the six core families: any such ID carrying a must-have requirement needs at least one downstream task and one verification row, and is a launch blocker when uncovered.
- When the design source is a `ui-architecture-builder` package, a `DS-*` ID names an entry that exists in `ui-registry.json` — a token, a primitive with its closed variant set, a product component, a registered motion variant, or a page recipe. Resolve every `DS-*` trace against that registry, and against the route's row in `page-recipes.md` for a route-scoped one. An implementation that satisfies a `DS-*` trace with a value or component the registry does not list has not covered it; that is a contract violation, not a stylistic difference.
- The planner authors a verification row for every `TEST-VIS-*` the package marks required. `verification-gates.md`'s Full-Stack E2E matrix ships named rows only for the checks a script or a standard capture already covers; the rest — page-to-mockup conformance, taste, container purpose, icon and motion conformance, and the others — have no prebuilt row and must be added to the plan's acceptance matrix at authoring time, each with its own comparison method and tolerance. A required row with no authored counterpart is an uncovered must-have trace at closeout, not an optional extra.
- When the design source is a `ui-architecture-builder` package, its `visual-acceptance.md` `TEST-VIS-*` rows are that package's acceptance contract for the implementation, not just internal design-review bookkeeping: each `TEST-VIS-*` row marked required for an in-scope surface must map to at least one harness verification row (a task acceptance row, a visual review's scope, or a UI-evidence/E2E gate) or be explicitly recorded as descoped with a reason. Do not let the harness's own generically named visual gates silently stand in for a specific `TEST-VIS-*` obligation (for example the anti-slop review or container-and-border purpose check) that nothing actually maps to.
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
- An in-scope route has no recipe in `page-recipes.md`, or a route's recipe requires a primitive, variant, component, or motion variant that `ui-registry.json` does not list. Ask for the missing recipe or registry entry; do not improvise the route or pass a raw value at the call site.
- The design source's mockup HTML is styled to a different platform than the resolved target — for example web viewport/breakpoint styling and web-family icons handed off for a native iOS/Android/Flutter/desktop mission, or the reverse. Every platform's mockup is real HTML (see `ui-architecture-builder`'s Platform-Conditional Vocabulary), so the mismatch to catch here is the visual convention, not the file format. Do not silently implement against a mismatched-styling mockup or guess the intended platform; confirm with the user first. See `verification-gates.md`'s "Capture Mechanism By Platform" for how the resolved platform separately decides the UI evidence capture mechanism after implementation.
- Auth, permissions, or destructive data behavior is ambiguous.
- Required secrets, services, databases, or browser tools are unavailable. When a required environment variable has no placeholder yet in the project's `.env.example` (see `platform-archetypes.md`'s Greenfield / Empty Repository section), add the placeholder entry as part of the task that introduces the read, then stop and ask the user for the real value instead of inventing or guessing one.
- The requested write scope would modify unrelated modules.
- The user has not approved overwrites, deletes, moves, resets, or worktree cleanup.
- The canonical plan/run manifest is missing, invalid, stale, or inconsistent with the proposed wave.
- The PLAN declares a `release` section while `landing.mode` is `local_only`. The production target's PASS requires a merged PR (`harness_release.py`), and `local_only` can never record one, so the run could not reach `complete`. `harness_manifest.py` now rejects this at execution authorization rather than at closeout: either move the run to `pull_request` mode or drop the release section before authorizing.
- A mission's write scope has no review-type node covering it. `harness_manifest.py` enforces this at execution authorization: a run cannot set `execution_authorized: true` while any mission with a write scope is absent from every review node's `mission_ids`. The check fires at authorization rather than plan validation, so an upgraded v3 projection stays a valid PLAN — it simply cannot execute until its review nodes are authored. `required_reviews` staying empty no longer means the run ships without review.
- A planned trace has a downstream task but no verification row. `harness_manifest.py` enforces both halves: a planned trace whose every carrying task has an empty `acceptance_matrix` fails plan validation. An implemented-but-unverified contract no longer passes as covered.
- A current PLAN-v5 graph does not cover every mission's write scope with at least one review-type node (`backend_code`/`frontend_code`/`visual` as applicable), regardless of `landing.mode`. `local_only` runs get no independent GitHub/Codex review at merge time, so this graph-level review is their only review gate — it is not optional there just because `pull_request` mode would add a second one.
- A review-type node's dependency edge sources from a mission outside its own `review.mission_ids`, or from a mission that completes materially later than every mission already in that set — review readiness deferred to an unrelated downstream mission's completion instead of becoming ready as soon as every mission in `review.mission_ids` has itself integrated. This defeats incremental review even when write-scope coverage is technically satisfied: a defect in an earlier-listed mission can sit uncaught through every mission built on top of it before review ever runs, and surfaces as one large concentrated batch of findings instead of a few close to where each was introduced.
- A review-type node is superseded by a plan revision before it ever executes (`attempts: 0`), and its successor generation of the same review checkpoint is then also superseded before running. One superseded-before-running generation can be an ordinary consequence of a legitimate scope change; two or more in a row against the same checkpoint means plan-revision churn is preventing that review from ever getting a turn to run, letting unreviewed work accumulate across every mission named in its `review.mission_ids` until a much-later generation finally executes and surfaces a large batch of findings at once — the same end state as the deferred-edge condition above, reached by repeated supersession instead of a wrong dependency source.
- A mission's cumulative repair attempts across successive generations of the same review checkpoint (for example `N-BACKEND-REVIEW` exhausted then replaced by `-FINAL`, `-CLOSE`, `-RETRY`, each with its own fresh `max_attempts` budget) exceed a reasonable ceiling with no recorded justification for why the prior generation's cap was insufficient. A per-node attempt cap does not bound total rework when an exhausted node can simply be superseded by a fresh one with its own budget — track cumulative attempts per mission, not only per node, and require the plan revision that adds a successor review node to state why the previous node's cap failed to resolve the issue.
- Implementation work continues after a mission has already `integrated`, or after the whole run's `landing` already reached `merged`, and no new mission or task ID has been opened to cover it. Discovered post-merge work needs its own mission (a plan revision on the same PLAN/RUN) opened before edits begin, not an informal parallel checklist (for example a stray `tasks.md` outside `docs/goal/`) that duplicates the status PLAN/RUN already owns — two systems both claiming to be the record of what is done is itself the defect. When the new work is bigger than an isolated follow-up — anchored by a genuinely new upstream contract source rather than incremental discovery — see "Starting A New Plan vs Extending The Current One" above instead of opening just another mission on the old plan.
- A mission whose write scope includes a database or schema migration reaches its integration gate while the applicable PLAN-v5 release target's `migration_classification` is null. Null means unresolved and blocks execution. Revise the parent-owned PLAN to classify it as `not_applicable`, `additive`, or `destructive`, increment the revision/digest, and reauthorize the changed plan before continuing.
- A mission's write scope touches balance, payment, withdrawal, or other money-moving logic and its acceptance matrix has no idempotency, concurrency, or replay-safety item. Add these to the acceptance matrix by default at authoring time for any financial-transaction-adjacent mission, not only after a review or incident finds the gap — money-moving logic that races, double-applies, or replays under retry is a correctness defect a functional test alone will not catch.
- An autonomous production deploy is about to fire whose target SHA differs from the exact candidate head recorded by `deploy` authorization for `release:<target-id>`, or whose in-scope migration is classified potentially destructive.

A planner MAY satisfy the mandatory review-coverage requirement above with either one review-type node per covered surface (the default) or an N-reviewer fan-out for a higher-risk surface — several independent verifier nodes of the same `review.type` bound to the same SHA, reconciled by a parent-side rule. Both forms count as covering the surface; see `graph-orchestration.md`'s "Multi-Reviewer Fan-Out" for the node/edge shape and the any-blocks vs majority-pass reconciliation patterns.

Default a review node's readiness to the completion of the same mission(s) named in its own `review.mission_ids`, not a later unrelated mission. Catching a defect close to the mission that introduced it is cheaper than discovering it after several more missions have already built on top of it, and a smaller reviewed diff is easier to judge accurately than several missions' combined changes reviewed at once. Cover more than one mission under a single review node only when reviewing them together is genuinely more meaningful than reviewing each alone — for example two missions that are tightly coupled parts of one feature where the integration between them is exactly what needs judging — not merely to reduce how many review rounds a run needs.

This default has a mission-granularity corollary for frontend/UI work bound to `mockups/*.html`: give each page (or a small, genuinely tightly-coupled group of pages) its own frontend mission and its own `visual`-type review scoped to that mission's `mission_ids`, rather than one mission spanning every route in `page-recipes.md` reviewed once at the end. A single frontend mission that implements every route defeats the review-timing default above even when its own review is correctly bound to that mission's `review.mission_ids`, because that mission's completion IS the end of all frontend work — the visual conformance check against `mockups/*.html` still only fires once, over everything, instead of catching a page's defect as soon as that page's mission integrates. Combine pages under one mission and one review only when the same "genuinely more meaningful together" bar above is met (for example a handful of legal/utility pages sharing one trivial template), not merely to reduce the mission count. Narrowing a mission's scope to one page does not relax task-level atomicity within it — still decompose that page's build into independently verified, commit-sized tasks per `execution-task-decomposition.md` and land each with its own atomic commit per `commit-convention.md`. See `graph-orchestration.md`'s per-page repetition note, `platform-archetypes.md`'s Public Website/Marketing Site example, and `design-input-updates.md`'s New Build Flow example for this corollary applied to a worked mission list.
