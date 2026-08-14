# Contract And Traceability

Use this reference when the work starts from a PRD, wireframe, design system, architecture note, ticket set, screenshot, or broad full-stack idea.

## Contract Freeze

Freeze only the surfaces needed for the next implementation loop. Do not freeze speculative backlog.

Required full-stack freeze fields:

```text
Product: objective, users, workflows, must-have requirements, non-goals, success criteria
Builder UX direction: human decision owner, experience priority, guidance/control, density, interaction/layout, confirmation/recovery, validation depth, and selected/provisional/assumed status. When the source PRD came from `prd-builder`, its `PRD.md` Builder UX Direction table (see `../prd-builder/references/output-contract.md`) is the authority for each axis's valid values, e.g. experience priority is one of speed/clarity/guided completion/expert control/exploration/conversion/comprehension, guidance and control is guided/balanced/expert-flexible, and information density is sparse/balanced/dense. When no such upstream table exists, resolve each axis's value with the human decision owner instead of inventing terminology.
Architecture: module boundaries, data model, API/action contracts, auth, permissions, side effects
UI structure: routes, screens, navigation, regions, data-to-UI mapping, states
Visual design: design system, tokens, primitives and their closed variant sets, product components, registered motion variants, the responsive verification set, interaction states
Verification: commands, E2E journey, evidence paths, acceptance thresholds
Write scope: allowed paths, read-only paths, destructive-action approval gates
```

Low-fidelity wireframes remain the product authority for structure and flow. An upstream `frontend-design` visual-direction candidate is non-canonical until `product-design-builder` normalizes it into the frozen design set above. Harness implementation consumes those frozen sources, not the candidate prototype.

For large work, including parallel mission work, implementation starts only after the plan readiness gate passes and execution is explicitly authorized. Selecting the skill or requesting a plan does not authorize implementation. User-authorized assumptions can resolve contract gaps but do not by themselves authorize code changes.

## Canonical Harness State

For long or multi-mission work, keep one versioned plan and one live run record. See `execution-state-model.md`'s "Three Authorities" table for exactly what `PLAN.md`, `RUN.md`, and observed Git/runtime facts each own; do not re-derive that split here.

The parent/coordinator is the sole writer of `PLAN.md` and `RUN.md` during execution. Workers return structured results or refinement requests and never edit either file. Every accepted plan change increments `plan_revision`; recompute the canonical plan digest, validate both DAGs, and invalidate any wave proposal bound to the previous revision or digest.

### Starting A New Plan vs Extending The Current One

When `docs/goal/PLAN.md`/`RUN.md` already exist, decide whether new work extends the current plan or starts a new one:

- Extend the current plan (a new `plan_revision` on the same `PLAN.md`/`RUN.md`) when the new work is incremental discovery inside the same ongoing initiative and its upstream contract sources (PRD, design system, architecture) have not materially changed.
- Start a new plan when the new work is anchored by a freshly regenerated upstream contract source — for example `prd-builder` published a refreshed `PRD.md`, or `product-design-builder` published a refreshed design set, with a new `content_sha256` — signaling a distinct new initiative rather than a continuation of the prior plan's frozen contract.
- To start a new plan: first confirm the current `PLAN.md`/`RUN.md` actually reached the Closeout Bar (`verification-gates.md`). Archive the completed `PLAN.md` and `RUN.md`, plus their `docs/goal/evidence/` directory, into `docs/goal/archived/<YYYYMMDD-HHMMSS>-<initiative-slug>/`, mirroring the same archival convention `prd-builder` already uses for its own superseded documents. Then create a fresh `docs/goal/PLAN.md`/`RUN.md` from the templates and freeze the new contract from the newly published upstream sources.
- Do not silently overwrite an unarchived `PLAN.md`/`RUN.md` to start the new plan — that destroys the only record of what the prior plan covered and how it was verified.

## Source Map

Record every canonical input and its status:

```text
| Source | Path / URL | Content SHA-256 / immutable revision | Owner | Status | Notes |
|---|---|---|---|---|---|
| PRD | <path> | <hash or revision> | human / team | draft / frozen / delta_accepted / revision staged | <summary> |
| Builder UX direction | <PRD section, path, or URL> | <hash or revision> | human decision owner | selected / provisional / assumed | <direction and validation needs> |
| Wireframe | <path or URL> | <hash or revision> | human / team | draft / frozen / delta_accepted / revision staged | <screens> |
| Design system | <design-system.md path> | <hash or revision> | human / team | draft / frozen / delta_accepted / revision staged | <tokens, primitive layers, components, state matrix, guardrails> |
| Design system (machine) | <design-system.json path> | <hash or revision> | human / team | draft / frozen / delta_accepted / revision staged | <the allowlist check_ui_contract.py reads; publishes with the Markdown> |
| Architecture | <path> | <hash or revision> | Codex / team | draft / frozen / delta_accepted / revision staged | <contract surfaces> |
| Stack decisions | <path> | <hash or revision> | human / team | required / selected / recommended / provisional | <resolved frontend, backend/data, mobile/desktop layers> |
```

For plan-backed work, the PLAN JSON `sources` array is canonical; the table is its human view. Every current PLAN-v5 source includes `content_sha256`, an immutable `source_revision`, or both. A mutable path or URL without either binding is not frozen. Recompute the PLAN digest and invalidate old attempts whenever source content or its upstream revision changes. Each trace references `source_ids` and records `priority`, `disposition`, and any disposition `rationale`. Canonical `ui_surfaces`, `risks`, mission `stop_conditions`, and verifier arrays are likewise the static source of truth; any Markdown table showing them elsewhere is a view only.

If an external source is unavailable, ask for screenshots, exports, or written specs before claiming design-faithful implementation.

## Document Folder Handoff

When the user provides a document folder path, inspect that folder before drafting harness artifacts. Treat files in the folder as upstream sources and register recognized inputs in the source map. This is commonly `docs/product/` when `prd-builder` published there, but the harness does not assume a fixed path — take whatever folder the user names.

Recognize common upstream files and folders:

```text
PRD.md
architecture.md
stack-decisions.md
wireframes.md
implementation-plan.md
design-system.md
design-system.json
screenshots/
figma-refs.md
```

Rules:

- Do not require upstream files to come from a specific skill or pipeline.
- Do not write harness-owned artifacts into the upstream document folder unless the user explicitly asks for that location.
- When `implementation-plan.md` is present, read its `Harness Handoff Signals` table (dependency order, parallel candidates, shared resources, required reviews, human gates) as non-canonical planning hints before drafting the mission graph from scratch, instead of re-deriving the same analysis unassisted.
- `design-system.md` and `design-system.json` are binding contract sources, not advisory notes. Freeze both with a `content_sha256` and give each its own source row. They publish as a pair, so an edit to either invalidates the PLAN digest and reaches implementation through `design-input-updates.md`, not by a mission quietly following the newer file. `design-system.md` owns visual reasoning, ratios, and taste guardrails. `design-system.json` is the sole structured authority for tokens, primitive layers and closed variants, product components, motion, and the state matrix; Markdown's machine-contract block is generated from it. `../product-design-builder/references/design-system-guide.md` holds the design method itself — read it there rather than restating it in harness artifacts.
- Precedence between design sources: product rules beat the wireframes' structure, which beats the design system's visual choices, which beat product components, which beat primitives, which beat any page-specific preference. A mission may not resolve such a conflict by picking the more convenient source.
- If `design-system.md` or `design-system.json` is missing and UI quality matters, classify the design input state as `missing` or `partial` and stop for acceptance or assumptions before claiming a design-faithful build. One of the pair present without the other is `partial`, never `frozen`. An in-scope route with no screen entry in `wireframes.md` is a blocker for that route, not an invitation to improvise it.
- If a wireframe screen omits its states, record the gap in the handoff readiness table and resolve it before implementation or mark the surface `UNVALIDATED`. The required responsive set comes from `design-system.json`: `viewports` for a web target or `sizeClasses` for a native or desktop target, exactly one of the two. The harness does not carry its own default set — an absent or empty set is a `partial` design input, not a cue to assume common breakpoints.
- For every platform (web, native iOS/Android/Flutter, macOS, Windows), the design system's tokens, primitive layers, and components keep their meaning and take the platform's own vocabulary: tokens become theme values, layout primitives become the platform's layout containers, and control primitives wrap its native controls. Wrapping a platform's own component in a design-system primitive is what keeps the closed variant sets — do not drop the primitive layer because the platform ships a component library.
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

- Upstream contract files mint IDs. A harness planner never mints a new one.
- Mission tasks and acceptance rows reference existing IDs.
- Every must-have PRD/UI/UX/ARCH/DS ID needs at least one downstream task and one verification row.
- The archetype-specific families in `platform-archetypes.md`'s "Trace ID Families" (including the native `APPSHELL-*`, `CAP-*`, `STORE-*`, and `SIGN-*` families) are not a separate upstream ID space and are not an exception to the minting rule above. They are lenses: each one re-tags a requirement that already carries a core ID, so a tenant-isolation rule frozen as `ARCH-004` is also `TENANT-001`. A planner may apply a tag because applying it mints nothing. The tag inherits its requirement's coverage obligation and gets the same enforcement as the six core families: any such ID carrying a must-have requirement needs at least one downstream task and one verification row, and is a launch blocker when uncovered. The same task and verification row can prove both the core ID and the tag.
- A `DS-*` ID names an entry that exists in `design-system.json` — a token, a primitive with its closed variant set, a product component, or a registered motion variant. Resolve every `DS-*` trace against that file. An implementation that satisfies a `DS-*` trace with a value or component the design system does not list has not covered it; that is a contract violation, not a stylistic difference.
- The planner authors a verification row for every visual `TEST-*` obligation `PRD.md` marks required. `verification-gates.md`'s Full-Stack E2E matrix ships named rows only for the checks a script or a standard capture already covers; the rest — taste, container purpose, icon and motion conformance, and the others — have no prebuilt row and must be added to the plan's acceptance matrix at authoring time, each with its own comparison method and tolerance. A required row with no authored counterpart is an uncovered must-have trace at closeout, not an optional extra.
- A visual `TEST-*` obligation in `PRD.md` is an acceptance contract for the implementation, not design-review bookkeeping: each one marked required for an in-scope surface must map to at least one harness verification row (a task acceptance row, a visual review's scope, or a UI-evidence/E2E gate) or be explicitly recorded as descoped with a reason. Do not let the harness's own generically named visual gates silently stand in for a specific obligation (for example the anti-slop review or container-and-border purpose check) that nothing actually maps to.
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

Two kinds of stop exist. Validator-enforced stops surface mechanically — `harness_manifest.py` blocks them when it validates the plan or run, and `select_ready_nodes.py` blocks them at wave selection. They are listed so a planner understands why validation, authorization, or selection fails, not because an agent must catch them by reading. Judgment stops have no validator; the agent must notice them itself and stop.

### Validator-Enforced Stops

The validators block these. Fix the plan or run state; do not work around them:

- `RUN.md` is not `ready` or `execution_authorized` is false: `select_ready_nodes.py` refuses to select a wave.
- The canonical plan/run manifest is missing, invalid, stale, or inconsistent with the proposed wave.
- A mission's write scope has no preintegration-stage review node covering it. Enforced at execution authorization rather than plan validation, so an upgraded v3 projection stays a valid PLAN — it simply cannot execute until its review nodes are authored. On a RUN-v10 run, coverage counts only a review node whose `review.mission_ids` contains exactly that one mission and which has a direct dependency edge from that mission's node — a multi-mission or integration-stage review cannot stand in for it. After all mission heads integrate, fresh integration-stage reviewers cover the unified head; `required_reviews` staying empty never means the run ships without review.
- A planned trace has a downstream task but no verification row: a planned trace whose every carrying task has an empty `acceptance_matrix` fails plan validation. An implemented-but-unverified contract does not pass as covered.
- A mission's `required_skills` names `product-design-builder` without `frontend-design`, or a design-source write scope omits that skill pair.

### Judgment Stops

Stop before implementation when:

- The Plan Readiness Gate has required rows that are not `PASS`. No script parses that table; keeping it honest is the planner's obligation.
- The requested action is false or absent in the authorization ledger. General execution permission does not imply task creation, worktree creation, commits, integration, push, archival, or cleanup permission.
- PRD and wireframe conflict on the primary flow.
- Builder UX Direction is missing for UI-bearing work, its decision owner is unclear, or it conflicts with user evidence or accessibility without a recorded hypothesis and validation decision.
- The design system contradicts the wireframe in a user-visible way.
- `design-system.md` and `design-system.json` are both present but fail `product-design-builder`'s pair checker, run read-only from the repository root: `scripts/check_design_system_pair.py --markdown <design-system.md> --registry <design-system.json> --require-filled`. Never run it with `--write` from the harness — that edits a frozen source. A failing pair means the two files no longer agree — usually a hand edit to one after publication. Route the fix through `design-input-updates.md`; do not guess which file is right or implement against half a contract.
- `frontend-design` cannot be loaded for a mission that requires it. Creation mode is blocked; it does not fall back.
- A UI implementation mission lists `frontend-design` without an explicit user selection for that new or high-impact visual surface, or its handoff asks the skill to choose a new direction instead of conforming to the frozen package.
- An in-scope route has no screen entry in `wireframes.md`, or a route needs a token, primitive, variant, component, or motion variant that `design-system.json` does not list. Ask for the missing screen or design-system entry; do not improvise the route or pass a raw value at the call site.
- The design system is written for a different platform than the resolved target — for example web pixel `viewports` and web-family icons handed off for a native iOS/Android/Flutter/desktop mission, or the reverse. Confirm with the user; do not silently implement against the mismatch or guess the intended platform. `verification-gates.md`'s "Capture Mechanism By Platform" separately decides the UI evidence capture mechanism after implementation.
- Auth, permissions, or destructive data behavior is ambiguous.
- Required secrets, services, databases, or browser tools are unavailable. A required environment variable with no `.env.example` placeholder gets its placeholder added in the task that introduces the read (see `platform-archetypes.md`'s Greenfield / Empty Repository section); then stop and ask the user for the real value instead of inventing one.
- The requested write scope would modify unrelated modules.
- The user has not approved overwrites, deletes, moves, resets, or worktree cleanup.
- A mission's covering review node's `review.type` does not fit the surface it reviews — for example a UI mission whose only review is `backend_code`, with no `visual` node. The validator counts coverage without comparing `review.type` to the write scope; choosing the applicable types (`backend_code`/`frontend_code`/`visual`) stays the planner's judgment.
- A migration task reaches mission integration with its migration classification unset. The classification (`additive` / `destructive`) is not a manifest field — state it in the task's objective or acceptance matrix when the task is authored per `execution-task-decomposition.md`. An unclassified migration at integration may be hiding a destructive change behind a default.
- A review-type node's readiness depends on a mission outside its own `review.mission_ids`, or on a mission that completes materially later than every mission already in that set. Deferring review past the missions it covers lets a defect sit uncaught under later missions and surface as one large batch of findings instead of a few close to where each was introduced.
- The same review checkpoint is superseded before ever running (`attempts: 0`) two or more generations in a row. One superseded-before-running generation can be a legitimate scope change; repeated supersession is plan-revision churn preventing that review from ever getting a turn — the same unreviewed-accumulation end state as the deferred-readiness condition above.
- A mission's cumulative repair attempts across successive generations of the same review checkpoint (for example `N-BACKEND-REVIEW` exhausted, then `-FINAL`, `-CLOSE`, `-RETRY`, each with a fresh `max_attempts` budget) exceed a reasonable ceiling with no recorded justification. A per-node cap does not bound total rework when an exhausted node is replaced by a fresh one — track cumulative attempts per mission, and require the plan revision adding a successor review node to state why the prior cap failed.
- Implementation work continues after a mission has already `integrated`, or after the run pushed its integration head, without a new mission or task ID covering it. Open the follow-up mission via a plan revision before edits begin; an informal parallel checklist (for example a stray `tasks.md` outside `docs/goal/`) duplicating the status PLAN/RUN already owns is itself the defect. When the new work is anchored by a genuinely new upstream contract source, see "Starting A New Plan vs Extending The Current One" above instead.
- A mission's write scope touches balance, payment, withdrawal, or other money-moving logic and its acceptance matrix has no idempotency, concurrency, or replay-safety item. Author these by default for any financial-transaction-adjacent mission — money-moving logic that races, double-applies, or replays under retry is a correctness defect a functional test alone will not catch.

### Review Placement Defaults

A planner MAY satisfy the mandatory review-coverage requirement above with either one review-type node per covered surface (the default) or an N-reviewer fan-out for a higher-risk surface — several independent verifier nodes of the same `review.type` bound to the same SHA, reconciled by a parent-side rule. Both forms count as covering the surface; see `graph-orchestration.md`'s "Multi-Reviewer Fan-Out" for the node/edge shape and the any-blocks vs majority-pass reconciliation patterns.

Default a review node's readiness to the completion of the same mission(s) named in its own `review.mission_ids`, not a later unrelated mission. Catching a defect close to the mission that introduced it is cheaper than discovering it after several more missions have already built on top of it, and a smaller reviewed diff is easier to judge accurately than several missions' combined changes reviewed at once. Cover more than one mission under a single review node only when reviewing them together is genuinely more meaningful than reviewing each alone — for example two missions that are tightly coupled parts of one feature where the integration between them is exactly what needs judging — not merely to reduce how many review rounds a run needs. On a RUN-v10 run such a shared node is additional context only — it does not satisfy the per-mission coverage requirement above, which counts only singleton `review.mission_ids` nodes.

This default has a mission-granularity corollary for frontend/UI work: give each page (or a small, genuinely tightly-coupled group of pages) its own frontend mission and its own `visual`-type review scoped to that mission's `mission_ids`, rather than one mission spanning every route reviewed once at the end. A single frontend mission that implements every route defeats the review-timing default above even when its own review is correctly bound to that mission's `review.mission_ids`, because that mission's completion IS the end of all frontend work — the visual conformance check still only fires once, over everything, instead of catching a page's defect as soon as that page's mission integrates. Combine pages under one mission and one review only when the same "genuinely more meaningful together" bar above is met (for example a handful of legal/utility pages sharing one trivial template), not merely to reduce the mission count. Narrowing a mission's scope to one page does not relax task-level atomicity within it — still decompose that page's build into independently verified, commit-sized tasks per `execution-task-decomposition.md` and land each with its own atomic commit per `commit-convention.md`. See `graph-orchestration.md`'s per-page repetition note, `platform-archetypes.md`'s Public Website/Marketing Site example, and `design-input-updates.md`'s New Build Flow example for this corollary applied to a worked mission list.
