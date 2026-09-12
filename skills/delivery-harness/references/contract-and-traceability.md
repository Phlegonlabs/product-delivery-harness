# Contract And Traceability

Use this reference when the work starts from a PRD, design system, architecture note, ticket set, screenshot, or broad full-stack idea.

## Contract Freeze

Freeze only the surfaces needed for the next implementation loop. Do not freeze speculative backlog.

Required full-stack freeze fields:

```text
Product: objective, users, workflows, must-have requirements, non-goals, success criteria
Product Definition Approval: package revision, human owner, approved PRD/architecture/stack set, accepted assumptions, non-blocking questions, and no blocking item
Stack Decision Checkpoint: human owner, approved areas and coherent bundles, explicit delegation source if used, and no Recommended/Provisional executable layer
Builder UX direction: human decision owner, experience priority, guidance/control, density, interaction/layout, confirmation/recovery, validation depth, and selected/provisional/assumed status. When the source PRD came from `product-definition-builder`, its `PRD.md` Builder UX Direction table (see `../product-definition-builder/references/output-contract.md`) is the authority for each axis's valid values, e.g. experience priority is one of speed/clarity/guided completion/expert control/exploration/conversion/comprehension, guidance and control is guided/balanced/expert-flexible, and information density is sparse/balanced/dense. When no such upstream table exists, resolve each axis's value with the human decision owner instead of inventing terminology.
Architecture: module boundaries, data model, API/action contracts, auth, permissions, side effects
UI structure: routes, screens, navigation, regions, data-to-UI mapping, states
Visual design: design system, tokens, primitives and their closed variant sets, product components, registered motion variants, the responsive verification set, interaction states
Verification: commands, E2E journey, evidence paths, acceptance thresholds
Write scope: allowed paths, read-only paths, destructive-action approval gates
```

When a package comes from `product-definition-builder`, Harness first requires its machine-anchored Product Definition Approval and Stack Decision Checkpoint. The `PRD.md` UI surface contract remains product authority for UI structure and behavior, and approved `wireframes.html` is its projection. A headless package still needs the product and stack approvals. A wireframe-only UI package is a valid product-definition stop point but is not yet a visual implementation source.

For large work, including parallel mission work, implementation starts only after the plan readiness gate passes and execution is explicitly authorized. Selecting the skill or requesting a plan does not authorize implementation. User-authorized assumptions can resolve contract gaps but do not by themselves authorize code changes.

## Canonical Harness State

For long or multi-mission work, keep one versioned plan and one live run record. See `execution-state-model.md`'s "Three Authorities" table for exactly what `PLAN.md`, `RUN.md`, and observed Git/runtime facts each own; do not re-derive that split here.

The parent/coordinator is the sole writer of `PLAN.md` and `RUN.md` during execution. Workers return structured results or refinement requests and never edit either file. Every accepted plan change increments `plan_revision`; recompute the canonical plan digest, validate both DAGs, and invalidate any wave proposal bound to the previous revision or digest.

### Starting A New Plan vs Extending The Current One

When `docs/goal/PLAN.md`/`RUN.md` already exist, decide whether new work extends the current plan or starts a new one:

- Extend the current plan (a new `plan_revision` on the same `PLAN.md`/`RUN.md`) when the new work is incremental discovery inside the same ongoing initiative and its upstream contract sources (PRD, design system, architecture) have not materially changed.
- Start a new plan when the new work is anchored by a freshly regenerated upstream contract source — for example `product-definition-builder` published a refreshed `PRD.md`, or `design-system-compiler` published a refreshed design set, with a new `content_sha256` — signaling a distinct new initiative rather than a continuation of the prior plan's frozen contract.
- To start a new plan: first confirm the current `PLAN.md`/`RUN.md` actually reached the Closeout Bar (`verification-gates.md`). Archive the completed coordination set with `scripts/archive_run.py`: it refuses an incomplete run, lists every exact move as a dry run, and with `--apply` moves `docs/goal/PLAN.md`, `RUN.md`, `DECISIONS.md`, `REFINEMENT_BACKLOG.md`, the `evidence/` directory, and the rendered `docs/tasks.md` into `docs/goal/archived/<YYYYMMDD-HHMMSS>-<run-id>/`, recording the archived row in `docs/DOCUMENTS.md` and never deleting anything. Then create a fresh `docs/goal/PLAN.md`/`RUN.md` from the templates and freeze the new contract from the newly published upstream sources.
- Do not silently overwrite an unarchived `PLAN.md`/`RUN.md` to start the new plan — that destroys the only record of what the prior plan covered and how it was verified.
- When the owner declares the project or initiative complete, do not leave the finished state waiting for a future plan to trigger the move: once the Closeout Bar (`verification-gates.md`) is confirmed, run `scripts/archive_run.py` on the same instruction — review its dry-run move list and proceed only when the completion instruction already authorizes those exact targets or the owner explicitly approves the list. The archival bookkeeping commit lands on the run branch and reaches `main` through the same promotion path as the delivery itself; documents never stay behind on a side branch. Never move anything under `docs/product/` in this step — the current product sources stay published for future `product-definition-builder` enhancement runs. The archived set references its PRD only through the frozen `content_sha256` recorded in the archived PLAN's sources; the PRD family never enters `docs/goal/archived/` and stays at its canonical path as the living reference for later runs.

## Source Map

Record every canonical input and its status:

```text
| Source | Path / URL | Content SHA-256 / immutable revision | Owner | Status | Notes |
|---|---|---|---|---|---|
| PRD | <path> | <hash or revision> | human / team | draft / frozen / delta_accepted / revision staged | <summary> |
| Product Definition Approval | <PRD section> | <same PRD hash or revision> | human decision owner | approved / revision_requested / blocked | <package revision, accepted assumptions, blockers> |
| Builder UX direction | <PRD section, path, or URL> | <hash or revision> | human decision owner | selected / provisional / assumed | <direction and validation needs> |
| PRD UI surface contract | <path or URL> | <hash or revision> | human / team | draft / frozen / delta_accepted / revision staged | <screens> |
| Approved wireframe | <wireframes.html path> | <hash or revision> | human decision owner | draft / approved / delta_accepted / revision staged | <UI-* screens, labeled regions, states, exact responsive set, per-target layout, browser overlap/overflow check> |
| UI Design Handoff | <PRD section> | <PRD hash or revision> | human decision owner | approved / provisional / blocked | <Taste applicability, selected direction, Design System Need Gate> |
| Approved UI target | <path or immutable version> | <SHA-256 or revision> | human decision owner | approved / provisional / n/a | <routes, states, exact responsive scope, passing browser matrix, tolerance, allowed deviations> |
| Design system | <design-system.md path or n/a> | <hash or revision> | human / team | draft / frozen / delta_accepted / revision staged / n/a | <required only when the Design System Need Gate is required> |
| Design system (machine) | <design-system.json path or n/a> | <hash or revision> | human / team | draft / frozen / delta_accepted / revision staged / n/a | <the allowlist check_ui_contract.py reads when a pair exists> |
| Architecture | <path> | <hash or revision> | Codex / team | draft / frozen / delta_accepted / revision staged | <contract surfaces> |
| Stack decisions | <path> | <hash or revision> | human / team | approved / revision_requested / blocked | <Required/Selected/Approved frontend, backend/data, mobile/desktop, AI, and commercial layers> |
```

For plan-backed work, the PLAN JSON `sources` array is canonical; the table is its human view. Every current PLAN-v6 source includes `content_sha256`, an immutable `source_revision`, or both. A mutable path or URL without either binding is not frozen. Recompute the PLAN digest and invalidate old attempts whenever source content or its upstream revision changes. Each trace references `source_ids` and records `priority`, `disposition`, and any disposition `rationale`. Canonical `ui_surfaces`, `risks`, mission `stop_conditions`, and verifier arrays are likewise the static source of truth; any Markdown table showing them elsewhere is a view only.

If an external source is unavailable, ask for screenshots, exports, or written specs before claiming design-faithful implementation.

For UI-bearing work, the initial source review also checks the repository's conventional `docs/design/` folder when present, any design folder the user names, and obvious design images encountered in the normal bounded scope scan. Inventory readable candidates by repository-relative path and SHA-256, but keep them non-canonical until the PRD UI Design Pass inspects them and the owner approves a scoped target or confirmed principle. Repository presence alone never makes an image a page-faithful target. Follow `design-input-updates.md` for file types, exclusions, blocked inspection, and the handoff boundary.

## Document Folder Handoff

When the user provides a document folder path, inspect that folder before drafting harness artifacts. Treat files in the folder as upstream sources and register recognized inputs in the source map. This is commonly `docs/product/` when `product-definition-builder` published there, but the harness does not assume a fixed path — take whatever folder the user names.

Recognize common upstream files and folders:

```text
PRD.md
architecture.md
stack-decisions.md
PRD.md#ui-surface-contract
wireframes.html
implementation-plan.md
design-system.md
design-system.json
docs/design/
screenshots/
figma-refs.md
```

Rules:

- Do not require upstream files to come from a specific skill or pipeline.
- When `PRD.md` contains `<!-- product-definition-approval:start -->`, freeze `architecture.md` and `stack-decisions.md` beside it and run the sibling `check_product_package.py` join. Missing files, a non-approved checkpoint, a `Recommended`/`Provisional` layer, a blocking open question, or a blocked trust/AI gate stops implementation.
- Do not write harness-owned artifacts into the upstream document folder unless the user explicitly asks for that location.
- When `implementation-plan.md` is present, read its `Harness Handoff Signals` table (dependency order, parallel candidates, shared resources, required reviews, human gates) as non-canonical planning hints before drafting the mission graph. Its dependency/sequencing intent is mandatory input, not optional color: the planner must either adopt it in the drafted graph or record a one-line divergence reason in the PLAN. Coverage and trace-ID authority stay with `PRD.md`, `architecture.md`, and `stack-decisions.md` — the handoff table never mints traces and never substitutes for them.
- `PRD.md` is the binding structural and behavioral source for UI-bearing work; `wireframes.html` is its interactive review projection. Freeze both digests and the PRD Wireframe Approval record. A mismatch or structural change returns to `product-definition-builder` and invalidates downstream direction selection, previews, the approved UI target, design-system inputs, and implementation planning until the revised HTML is approved.
- When the Design System Need Gate is `required`, `design-system.md` and `design-system.json` are binding contract sources. Freeze both with a `content_sha256` and give each its own source row. They publish as a pair; an edit to either invalidates the PLAN digest. `design-system.json` is the sole structured authority for tokens, primitive layers and closed variants, product components, motion, and the state matrix.
- When the gate is `not_required`, the approved UI target row must carry an immutable path or version, SHA-256, routes, states, responsive scope, tolerance, and allowed deviations. Freeze it with the PRD and wireframes. No design-system pair is expected, and its absence is not `missing` or `partial`. When the target is design-reference HTML, freeze the approved all-screens HTML reference file's SHA-256 in that row, not just the folder path.
- Precedence between visual sources: product rules and the PRD UI surface contract beat approved wireframes, which beat the approved UI target, which beats a required design system's reusable choices, which beat product components, primitives, and page-specific preferences. A mission may not resolve a conflict by picking the more convenient source.
- A missing or `blocked` Design System Need Gate blocks implementation. For `required`, a missing or half-present pair is `missing` or `partial`. For `not_required`, a missing approved target or incomplete target scope is `missing` or `partial`. An in-scope route with no `UI-*` entry or matching approved wireframe is always a blocker.
- If a PRD UI surface omits its states or invariant `` `responsive` `` anchor, resolve the gap before implementation or mark the surface `UNVALIDATED`. PRD, approved `wireframes.html`, every PLAN UI surface, and — when present — `design-system.json` use the same set — at least three ascending viewports for a web package, or at least two size classes for native or desktop; historical two-target web files stay readable under the legacy wireframes/2 checker and must not be re-frozen as new packages. The target-conformance handoff records that exact set and its passing browser matrix. The harness carries no default set and never infers a missing target.
- When a design system exists for web, native iOS/Android/Flutter, macOS, or Windows, its tokens, primitive layers, and components keep their meaning and take the platform's own vocabulary. Target-conformance mode follows the named platform conventions without pretending a formal pair exists.
- When an approved Stack Decision Checkpoint names `Required`, `Selected`, or `Approved` frontend layers and no matching stack exists, those exact layers are the scaffold target: language, package manager, framework, UI library, component foundation, styling, build tool, and routing/testing as applicable. `Recommended` and `Provisional` are stop conditions, never defaults.

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
- A `DS-*` ID names an entry that exists in `design-system.json` when the Design System Need Gate is `required`. `scripts/validate_harness_plan.py --design-system <json-path> --design-system-markdown <markdown-path>` first proves the frozen pair's generated contract and compiler namespace rules, then resolves every PLAN `DS-*` trace against primitive `dsId`, product-component `dsId`, and `signatureRules` in one globally unique registry. A `not_required` route does not mint placeholder `DS-*` IDs; its visual acceptance traces to the approved UI target and the applicable `UI-*`, `UX-*`, and `TEST-*` rows.
- The PLAN's `ui_surfaces` and the PRD's `UI-*` surface contract agree exactly on IDs, each entry's one literal route, and states. A localized UI-bearing PRD keeps exactly one non-empty matched `ui-surface-contract` boundary pair around every `UI-*` heading in the document, plus exactly one backticked `route`, `states`, and `responsive` anchor per entry, while translating its human prose. When PLAN freezes PRD.md, approved wireframes.html, or design-system.json, `scripts/validate_harness_plan.py` requires the matching artifact flag and verifies its bytes against that source row's `content_sha256` before checking the semantic projection. Every frozen PRD row is parsed even when PLAN claims an empty `ui_surfaces` list, so deleting the PLAN projection cannot hide a PRD surface. The transition write path resolves the same frozen rows under `--repo-root` and runs the joins before accepting or integrating work. Frozen `wireframes.html` bytes are additionally run through `product-definition-builder`'s full wireframe checker — reviewer shell, self-containment, filled data, approved status, and the exact ID/route/state join from `PRD.md` to `wireframes.html` — so a surface that exists in only one artifact is drift, not a deliberate omission, and "approved" means the same thing in both skills.
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

When no repo convention exists, apply the File Size Limit in the project `AGENTS.md`. Use temporary `docs/goal/evidence/<mission>/REPORT.md` files only for parallel worker integration, then fold their durable result into `RUN.md`.

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
- A frozen `product-definition-builder` package carries its approval marker but fails the sibling core-package checker or omits its frozen architecture/stack sources.
- A mission's write scope has no preintegration-stage review node covering it. Enforced at execution authorization rather than plan validation, so an upgraded v3 projection stays a valid PLAN — it simply cannot execute until its review nodes are authored. On a RUN-v11 run, coverage counts only a review node whose `review.mission_ids` contains exactly that one mission and which has a direct dependency edge from that mission's node — a multi-mission or integration-stage review cannot stand in for it. After all mission heads integrate, fresh integration-stage reviewers cover the unified head. Every new code-delivery PLAN also declares one `security` review covering every mission, and its scope contains every mission write scope; older valid PLANs remain readable and are never silently rewritten.
- A planned trace has a downstream task but no verification row: a planned trace whose every carrying task has an empty `acceptance_matrix` fails plan validation. An implemented-but-unverified contract does not pass as covered.
- A mission's `required_skills` names `design-system-compiler` without `frontend-design`, a design-system-source write scope omits that pair, or a wireframe-source write scope omits `product-definition-builder`.

### Judgment Stops

Stop before implementation when:

- Static validation fails, or a readiness obligation in `execution-state-model.md` is unmet. `plan_readiness` in RUN is the single machine gate; keeping it honest is the planner's obligation.
- The requested action is false or absent in the authorization ledger. General execution permission does not imply task creation, worktree creation, commits, integration, push, archival, or cleanup permission.
- Two PRD sections conflict on the primary UI flow.
- Product Definition Approval or the Stack Decision Checkpoint is missing, blocked, revision-requested, or stale for a package produced by `product-definition-builder`.
- Builder UX Direction is missing for UI-bearing work, its decision owner is unclear, or it conflicts with user evidence or accessibility without a recorded hypothesis and validation decision.
- The wireframes contradict the PRD UI surface contract, lack human-owner approval, or the active approved UI target or required design system contradicts either source in a user-visible way.
- `design-system.md` and `design-system.json` are both present but fail `design-system-compiler`'s pair checker, run read-only from the repository root: `python skills/design-system-compiler/scripts/check_design_system_pair.py --markdown <design-system.md> --registry <design-system.json> --require-filled`. Never run it with `--write` from the harness — that edits a frozen source. A failing pair means the two files no longer agree — usually a hand edit to one after publication. Route the fix through `design-input-updates.md`; do not guess which file is right or implement against half a contract.
- `frontend-design` cannot be loaded for a design-system compilation mission. Compilation is blocked; it does not fall back.
- A UI implementation mission lists `frontend-design` without an explicit user selection for that new or high-impact visual surface, or its handoff asks the skill to choose a new direction instead of conforming to the frozen package.
- An in-scope route has no `UI-*` entry in `PRD.md`, no matching approved wireframe, or no active visual source. In system-conformance mode, a needed token, primitive, variant, component, or motion variant is absent from `design-system.json`. In target-conformance mode, the target omits the needed route, state, responsive case, or tolerance. Ask for the owning source update instead of improvising.
- The design system is written for a different platform than the resolved target — for example web pixel `viewports` and web-family icons handed off for a native iOS/Android/Flutter/desktop mission, or the reverse. Confirm with the user; do not silently implement against the mismatch or guess the intended platform. `verification-gates.md`'s "Capture Mechanism By Platform" separately decides the UI evidence capture mechanism after implementation.
- Auth, permissions, or destructive data behavior is ambiguous.
- Required secrets, services, databases, or browser tools are unavailable. A required environment variable with no `.env.example` placeholder gets its placeholder added in the task that introduces the read (see `platform-archetypes.md`'s Greenfield / Empty Repository section); then stop and ask the user for the real value instead of inventing one.
- The requested write scope would modify unrelated modules.
- The user has not approved overwrites, deletes, moves, resets, or worktree cleanup.
- A mission's covering review node's `review.type` does not fit the surface it reviews — for example a UI mission whose only review is `backend_code`, with no `visual` node. The validator counts preintegration coverage without comparing `review.type` to the write scope; choosing the applicable surface types (`backend_code`/`frontend_code`/`visual`) stays the planner's judgment. The final `security` type is separate: validation requires integration stage and complete mission coverage.
- A migration task reaches mission integration with its migration classification unset. The classification (`additive` / `destructive`) is not a manifest field — state it in the task's objective or acceptance matrix when the task is authored per `execution-task-decomposition.md`. An unclassified migration at integration may be hiding a destructive change behind a default.
- A review-type node's readiness depends on a mission outside its own `review.mission_ids`, or on a mission that completes materially later than every mission already in that set. Deferring review past the missions it covers lets a defect sit uncaught under later missions and surface as one large batch of findings instead of a few close to where each was introduced.
- The same review checkpoint is superseded before ever running (`attempts: 0`) two or more generations in a row. One superseded-before-running generation can be a legitimate scope change; repeated supersession is plan-revision churn preventing that review from ever getting a turn — the same unreviewed-accumulation end state as the deferred-readiness condition above.
- A mission's cumulative repair attempts across successive generations of the same review checkpoint (for example `N-BACKEND-REVIEW` exhausted, then `-FINAL`, `-CLOSE`, `-RETRY`, each with a fresh `max_attempts` budget) exceed a reasonable ceiling with no recorded justification. A per-node cap does not bound total rework when an exhausted node is replaced by a fresh one — track cumulative attempts per mission, and require the plan revision adding a successor review node to state why the prior cap failed.
- Implementation work continues after a mission has already `integrated`, or after the run pushed its integration head, without a new mission or task ID covering it. Open the follow-up mission via a plan revision before edits begin; an informal parallel checklist (for example a stray `tasks.md` outside the rendered `docs/tasks.md` view) duplicating the status PLAN/RUN already owns is itself the defect. When the new work is anchored by a genuinely new upstream contract source, see "Starting A New Plan vs Extending The Current One" above instead.
- A mission's write scope touches balance, payment, withdrawal, or other money-moving logic and its acceptance matrix has no idempotency, concurrency, or replay-safety item. Author these by default for any financial-transaction-adjacent mission — money-moving logic that races, double-applies, or replays under retry is a correctness defect a functional test alone will not catch.

### Review Placement Defaults

A planner MAY satisfy the mandatory review-coverage requirement above with either one review-type node per covered surface (the default) or an N-reviewer fan-out for a higher-risk surface — several independent verifier nodes of the same `review.type` bound to the same SHA, reconciled by the parent-side any-blocks rule. Both forms count as covering the surface; every planned current-head node and worker must PASS before integration, while historical or superseded evidence remains retained. See `graph-orchestration.md`'s "Multi-Reviewer Fan-Out" for the node/edge shape.

Default a review node's readiness to the completion of the same mission(s) named in its own `review.mission_ids`, not a later unrelated mission. Catching a defect close to the mission that introduced it is cheaper than discovering it after several more missions have already built on top of it, and a smaller reviewed diff is easier to judge accurately than several missions' combined changes reviewed at once. Cover more than one mission under a single review node only when reviewing them together is genuinely more meaningful than reviewing each alone — for example two missions that are tightly coupled parts of one feature where the integration between them is exactly what needs judging — not merely to reduce how many review rounds a run needs. On a RUN-v11 run such a shared node is additional context only — it does not satisfy the per-mission coverage requirement above, which counts only singleton `review.mission_ids` nodes.

The `security` review is the deliberate exception to this timing default. It runs only after serial integration, covers every mission, loads the project's `code_security_verification` Skill Binding, and evaluates cross-mission trust boundaries on the exact unified SHA. It supplements rather than replaces each mission's direct preintegration review.

This default has a mission-granularity corollary for frontend/UI work: give each page (or a small, genuinely tightly-coupled group of pages) its own frontend mission and its own `visual`-type review scoped to that mission's `mission_ids`, rather than one mission spanning every route reviewed once at the end. A single frontend mission that implements every route defeats the review-timing default above even when its own review is correctly bound to that mission's `review.mission_ids`, because that mission's completion IS the end of all frontend work — the visual conformance check still only fires once, over everything, instead of catching a page's defect as soon as that page's mission integrates. Combine pages under one mission and one review only when the same "genuinely more meaningful together" bar above is met (for example a handful of legal/utility pages sharing one trivial template), not merely to reduce the mission count. Narrowing a mission's scope to one page does not relax task-level atomicity within it — still decompose that page's build into independently verified, commit-sized tasks per `execution-task-decomposition.md` and land each with its own atomic commit per `commit-convention.md`. See `graph-orchestration.md`'s per-page repetition note, `platform-archetypes.md`'s Public Website/Marketing Site example, and `design-input-updates.md`'s New Build Flow example for this corollary applied to a worked mission list.
