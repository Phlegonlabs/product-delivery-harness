# PRD, Direction, And HiFi Pass

Run this pass only inside an active `ui-design-builder` flow after Product Definition Approval. It turns the approved PRD UI Surface Contract into direction studies and then a human-approved visual target; it does not create a gray structural wireframe first. `frontend-design` is the single design author. `impeccable` and rubric graders provide review evidence; they do not publish or approve the target.

Before direction studies and before connected HiFi, run `python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" --agents-md <target-AGENTS.md> --stage ui-design` with installed-command resolution. Repairs and the `frontend-design` read follow [Required Skills And Inputs](stages/ui-design.md#required-skills-and-inputs): the actual writer loads the complete owner-pinned skill in its own context, and nobody may silently replace the binding. Agent configuration designates the UI authoring executor. Reviewer and assembler helpers construct the shell or validate; they do not choose or repair the product design.

## Rebuild And Reading Scope

Apply `design-translation.md` and `design-freshness.md`. An explicit full rebuild retains product/stack constraints but starts from fresh directions built from the PRD UI Surface Contract, not from prior design authority. Refine provisional type, optical spacing and fine proportions without changing the approved behavior or hierarchy of responsibilities. Inspect repeated controls across pages, real CJK/Latin copy, stacked bilingual reading where required, text enlargement and dense/alternate states. Use source-bound before/after findings; numerical grades alone prove no improvement. New iOS scope defaults to iPhone; iPad remains conditional on Product Definition, never silently dropped from an existing PRD.

Apply `ui-grading-rubric.md#layout-integrity-and-anti-slop-review` while authoring and before presenting HiFi. Inspect control compression, alignment, open layers, long content and intermediate Web widths; record measured failures and product-specific visual findings in the existing evidence and defect ledger. Fix shared causes rather than hiding overflow.

Apply `page-design-profiles.md` to each affected surface. Inspect the selected font roles, desktop headline target and motion commitment with actual copy; page-specific exceptions remain visible in the existing brief and grading evidence.

## Frozen Inputs

For a current round, the Product Definition preflight uses the exact approved-package check with `--ui-contract ui-design/3` (or `ui-design/2` for an existing ui-design/2 package). A failed or unapproved product/stack identity blocks direction work; a missing UI-contract argument must not be treated as a current-package preflight.

For enhancements, apply `enhancement-recommendations.md#incremental-ui-scope` first. Reuse the approved direction and intake unless the accepted delta changes them. The complete matrix remains covered, but only added or changed screens and necessary entry/return controls are authored again. Keep unaffected product DOM, copy, layout, style, IDs and behavior; reviewer-shell migration alone is not a product redesign. Direction studies below apply to a new or changed direction, not automatically to every added feature.

Every direction and HiFi candidate uses the same:

- approved `PRD.md`, `architecture.md`, and `stack-decisions.md` identities;
- complete `UI-* × responsive target × non-n/a state` matrix;
- the PRD UI Surface Contract's page purposes, element/content responsibilities, operations, flows, states, copy contracts, data/charting and integration boundaries when declared;
- UI Design Intake and Visual Preference Brief, including the Design Brief for new or changed design scope;
- Motion and Media Intent rows;
- exact copy or bounded display contracts;
- brand, accessibility, platform, performance, component-foundation, and styling constraints; and
- applicable `MR-*` market evidence plus inspected `REF-*` visual evidence.

The pass may choose hierarchy, grouping, section rhythm, composition, typography, density and visual treatment. It cannot add, remove, reorder, or reinterpret product scope, content responsibility, routes, actions, flows, states, trace IDs, responsive targets, or approved stack constraints. A structural finding returns to `product-definition-builder`. A visual direction that needs a different framework, component foundation, styling method, runtime, or provider returns to the Stack Decision Checkpoint and Product Definition Approval.

## Direction Authoring Prompt

Use this prompt with the approved source paths and the existing Design Brief. Read requirements from those sources; do not copy per-page contracts into another table.

```text
Read the approved PRD UI Surface Contract, architecture, stack decisions and UI Design Brief at [source paths]. Derive the exact page/surface count and affected UI IDs from the PRD. For each page, satisfy its purpose, content and data responsibilities, required controls and operations, routes, states, responsive targets and sourced copy. Preserve unaffected pages in an enhancement.

For administration, include the required work areas and their responsibilities, data fields, filters, actions and permissions. For charts, honor the declared metric, source, units, time range and loading/empty/error behavior. For agent workflows, show the required inputs, execution progress, human decisions, results, failures and recovery. Use the approved frontend/backend and service boundaries; do not invent endpoints or product capabilities. Report missing product decisions upstream.

Choose composition, hierarchy, grouping, typography, imagery and motion freely within the approved constraints. A hero, introduction, feature group or CTA is a design choice when it serves the page purpose; do not impose a universal section sequence. Use the existing Page-purpose mapping to distinguish fixed requirements from design freedom.

Produce three materially different visual directions by default, with inspected reference lessons and the same representative primary and stress cases. Show applicable motion and reduced-motion treatment. If the owner explicitly requested one direction, produce one. Present comparable studies and wait for the owner's selection before creating the full connected HiFi HTML package.
```

## Cheap Completeness Check

Before HiFi author self-review and Impeccable, run:

```text
python "<ui-design-builder-skill-root>/scripts/check_ui_design_contract.py" --ui-design docs/design/ui-design.md --repo-root <root> --prd docs/product/PRD.md --hifi docs/design/ui-references/<run>/index.html --require-hifi-preflight
```

This checks source identities, the approved Product package, manifest closure, UI IDs, routes, states, responsive sets, operation/control destinations and copy provenance against actual product DOM. Repair failures and rerun before expensive review. Keep the command result with existing task evidence; no extra approval or duplicated requirements table is needed. Structured coverage does not prove chart meaning, data integration, aesthetics or runtime behavior. The author and reviewer check those responsibilities against the PRD; browser evidence still verifies interactions.

For `ui-design/3`, the CLI also reports advisory `compiler-source` diagnostics from the hash-checked HiFi package.
Inspect unresolved animation provenance before owner review. The author can clarify intended triggers or repair approved-scope source limitations early.
Static controls need no animation. A diagnostic never proves a design defect or a failed approval gate by itself.
Registry trigger feasibility and variant/state coverage remain deferred until the compiler has the actual registry.
The report creates no registry, changes no HiFi bytes and grants no compile-readiness PASS.

## Style Intake Gate

The intake must already be complete before `frontend-design` proposes a theme or Design Read. If it is missing, read `ui-design-intake.md`, ask the human owner the product-specific questions, end the turn, and wait. Reuse supplied answers; wait only on missing decisions.

If the owner supplies a reference, read `design-reference-guide.md` and inspect it through the matching source route. Record `REF-*` sources and proposed `Adopt / Adapt / Avoid` `RP-*` principles, then end the turn for confirmation before creating a direction.

Use the existing Design Brief to connect the page-purpose/profile mapping, typography/density/headline constraints, motion intent, owner answer, reference lessons and visual constraints to Style Integration and MM records as decisions mature. An explicit `no references` answer permits relevant research and recommendations under `design-reference-guide.md`; it is not direction approval. Unanswered optional references stay `not supplied`, and inaccessible material stays uninspected. Continue independent work and wait only for work that depends on the missing input. Preserve answered preferences and unchanged enhancement directions.

When the owner explicitly instructs a single recommendation, produce one product-specific direction and record it as the intake's `Direction mode: one recommended direction` with that owner's `Decision owner` and `Decided on`; this applies to `ui-design/3` and `ui-design/2` alike. Otherwise a new package gets exactly three materially different directions over the same approved surfaces, states and responsive targets. Continuing uncertainty or silence never converts into that instruction. An enhancement keeps its package's contract and retains the accepted direction for unchanged scope: a `ui-design/3` package keeps its approved round's hash-bound studies and selection, and no enhancement restarts direction selection. Never substitute a fixed catalog of style names.

Present the complete direction set to the human owner. End the turn and wait for `approve`, `select`, `mix`, or `reject`; even a one-direction set needs explicit approval. A mix or modification produces one revised study of the selected direction, with any requested variants inside it, and one more owner decision. A rejection starts a complete new set. Do not create the connected HiFi reference or invoke a generation provider before a direction is selected.

Before this selection, render bounded representative studies for every direction: a frequent primary task and a stress case using dense data, long content, or an approved alternate state. A one-screen product may show two content scenarios in the same approved state; do not invent a state or rewrite frozen copy. Use the same surface, state, target, scenario, and content basis across directions. Cover each in-scope platform. Compare composition, hierarchy, density, typography, and control treatment; changing only an accent color is not a distinct direction.

Where useful, a study may play a bounded local deterministic motion option within the existing MM scope, and with its normal/reduced-motion behavior visible. This makes a design choice easier to judge; it is not Required motion evidence, native proof, or permission to call a generation provider. Full connected HiFi remains the source of final motion evidence on the selected route, and provider calls remain after direction selection with exact authorization. For a landing or portfolio region with a proposed or selected `expressive` row, at least one direction plays that motion live; a static frame cannot stand in for it.

If proactive reference research introduces a structural option, route the product-side scope back to `product-definition-builder` before HiFi cosmetic work. Do not use an unreviewed reference study to add a route, control, state, or responsive destination.

Record the studies in `### Direction comparison` under Style Integration using the output contract's table, with inspected screenshot paths/hashes and a concrete rationale for each row. Tie each rationale to the Design Brief's page-purpose/profile, type/density/headline, motion and reference lessons; do not substitute generic style labels. Keep their authorized files under `docs/design/directions/<round>/`. These studies are selection evidence, not the connected HiFi target or production UI. The owner selects from the recorded direction IDs. This uses the existing direction gate, not another approval step. Screenshot hashes prove identity, not aesthetic quality or honest inspection.

Before asking the owner to select a direction, the author completes the UI structure/direction self-review in `../../delivery-harness/references/pre-delivery-self-review.md`. Inspect the representative studies, their required operations and primary/stress cases, repair defects and retain the result against the current candidate identities in the existing task record. An owner-selected mix or changed study needs an affected recheck.

## Frontend Design Style Integration

Load `frontend-design` and use its brief-first, subject-grounded design process. It owns the direction, page theme, and connected HiFi design-reference HTML across every surface. Taste skills such as `design-taste-frontend` or `gpt-taste` may supplement an approved direction; they never replace `frontend-design` as the author or select a competing direction. Do not run Impeccable build/refine commands or another visual author in parallel.

For each direction, record:

- a versioned `VD-*` ID and concise design intent;
- product and audience fit, including the accepted Design Brief page-purpose/profile and type/density/headline constraints;
- confirmed `REF-*` and `RP-*` evidence, including useful composition/typography/motion roles and avoid rationale;
- layout, composition, typography, color, surface, shape, icon, imagery, and motion rules;
- tradeoffs and an avoid list; and
- how it respects the approved component foundation and styling approach.

Choose iconography through current official-source lookup for the approved platform. For Web icons, compare Lucide, Phosphor, Heroicons, and Tabler, select one primary and one named fallback, and record license, framework support, maintenance evidence, URLs, and retrieval dates. For iOS, assess SF Symbols first against the approved OS range, text styles, symbol meaning, and brand needs; record the selected system or custom treatment and its reason. Other platforms use their own conventions and approved component foundation. Never require a Web icon library on a native surface. Record `UNVALIDATED` when evidence is unavailable; never silently choose from memory.

Choose typography with the same evidence discipline. Record display/body roles, required weights, Latin and CJK coverage, fallback order, loading strategy, source URLs, and retrieval dates. Record the palette derivation, contrast intent, and whether dark mode is in scope. These candidate theme values render the HiFi target but are not yet a frozen design-system contract.

## Platform Rules

Use `modern-design-sources.md` to select current source-backed platform and accessibility checks. Record adopted rules in the existing handoff; preserve the approved stack and responsive targets.

Record one row per approved `stackSemantics.platform` in `### Platform rules` under Style Integration. Shared brand color roles, content hierarchy, and voice may span platforms; navigation, control geometry, type metrics, density, and feedback must follow the platform and task. The table does not select a framework or reopen the approved stack.

- Web App: design the frequent working screen first. Set navigation, keyboard/focus/hover behavior, content width, table/list/detail density, responsive composition, font loading, and CJK fallback. A hero treatment belongs only to a product-approved surface that needs it.
- iOS: explain system text styles and Dynamic Type, SF Symbols or a reasoned custom alternative, navigation/back behavior, sheets, safe areas, touch targets, keyboard avoidance, native list density, system feedback, and reduced motion. Check supported OS versions. Assess dark mode and haptics only within approved scope. Custom fonts may express the brand when they preserve scaling, readability, and language coverage.
- Other native/desktop platforms: record the corresponding typography, controls, input methods, layout, and feedback conventions with current official evidence. A Web projection cannot substitute for these decisions.

Use current [Apple iOS guidance](https://developer.apple.com/design/human-interface-guidelines/designing-for-ios), [typography guidance](https://developer.apple.com/design/human-interface-guidelines/typography), and [SF Symbols](https://developer.apple.com/sf-symbols/) for iOS, recording the inspected source and date. Their names alone are not design reasoning.

Set `Review medium: HTML projection only`. Studies and HiFi review native appearance approximately; they do not prove native typography, gestures, keyboard behavior, scrolling, haptics, or accessibility. `Native proof` is `not_applicable` for Web and `required before expansion` for native/desktop platforms. After Visual Approval, the first implementation slice verifies representative primary and stress cases using the approved stack and actual platform tooling before expanding to other screens. Record this in the existing Harness UI evidence and repair through the same ownership boundaries; HTML cannot clear it. No production UI is authored during this design pass.

## Motion And Generated Media

Consume the approved Motion and Media Intent rows without re-asking them. Use `motion-and-media-routing.md` to select the lowest applicable route (CSS/WAAPI, Motion, GSAP or Three.js) for the selected direction and final HiFi.

After direction selection, an installed Higgsfield MCP or another owner-approved generation provider may create an approved generated or curated motion asset only after exact provider/action authorization. Record provider capability, prompt, output identity, usage constraints, placement, fallback, and review result. When intake authorized a provider for an MM row, generate its asset after direction selection so the HiFi shows the actual result. Without that authorization, keep the typed static placeholder and name the gap in the handoff. Generated output cannot add copy, controls, states, routes, or claims.

Required deterministic functional UI motion may run locally in the HiFi HTML with its normal and reduced-motion behavior. A generated video or cinematic asset has a static poster/fallback even when the generated output is present.

Every `motion` or `image + motion` intent records its design-projection effect evidence under `### Required motion evidence` before Visual Approval. Intent approval and effect completion are distinct; changing its status to `deferred` cannot waive required evidence. Preserve the intent record's approved source and frozen identity. Native studies demonstrate the visual intent in HTML; actual native normal/reduced-motion, gesture and haptic results belong to the first implementation slice and final full matrix. The design table never proves native implementation.

## Connected HiFi Reference

Produce a connected `ui-hifi/2` HTML package with `index.html` as its entry and sibling HTML files for separate pages. Cover every in-scope `UI-*` screen, responsive target, and non-`n/a` state. Each page embeds its CSS, scripts, fonts, and media. Keep the entry's `ui-hifi/2` manifest and `ui-hifi-copy/1` provenance JSON; tag rendered product copy with matching `data-copy-id` and `data-copy-locale`, including paired-language variants. Keep the fixed left version-3 review sidebar, product screen navigation, Overview, Design Tokens, and responsive controls. A product tab or page link uses a real anchor to its declared HTML destination. Buttons change a declared local state, including overlays and feedback. Reviewer sidebar navigation never substitutes for product-control interaction coverage. Every current Visual Approval requires schema 2; schema-1 single-file references remain inspection-only.

Use `skills/ui-design-builder/assets/templates/HIFI_REVIEWER.template.html` as the reusable inline fragment. Keep the exact CSP first. Inline its marked CSS in each page's head; wrap the sole product surface in `main[data-hifi-reviewer-main] > [data-hifi-canvas]`; inline a version-3 shell whose page links and real target buttons match that page's manifest targets; add Overview and Design Tokens panels only to `index.html`; inline the marked runtime and call `connectHifiReviewer()` last. A hybrid bundle keeps each page's target family separate (for example, web viewports do not acquire native size classes). Pass `targetsByPage` to `createHifiReviewerRuntime`, or put space-separated `data-hifi-page-targets` on each page-navigation link, so navigation falls back to the destination page's first valid target when the retained target is unavailable. Mark one actual product input/textarea `data-retention-input` and one actual `select` or selected control with `aria-selected`, `aria-pressed`, or checked semantics as `data-retention-selected` only when those controls exist on the product page; a marked text input is ignored. The runtime exposes `window.createHifiReviewerRuntime({storage, pages, surfaces, targets, targetsByPage, page, defaultSurface})` and `window.connectHifiReviewer()`, with `selectTarget`, `setPage`, `openView`, `showProduct`, `selectSurface`, and `snapshot` methods. It stores only reviewer target/surface selection and toggles panel, canvas, and selected-surface visibility; it never rebuilds product DOM, fetches, or uses an iframe. Product responsive rules must use container queries on the exact-width canvas.

The HTML contains exactly one canonical restrictive CSP meta:

`default-src 'none'; base-uri 'none'; connect-src 'none'; form-action 'none'; frame-src 'none'; object-src 'none'; navigate-to 'self'; img-src data:; media-src data:; font-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'`

The offline browser additionally allows only the declared package pages. CSP alone does not enforce the page allowlist and cannot prove arbitrary JavaScript safe. Follow the manifest and interaction-output schemas in `output-contract.md`.

The file calls no live backend, credential, identity provider, or unapproved generation provider. Login, registration, recovery, and authentication-error preview scenes may be marked `n/a` for this visual review without removing their production requirements. Native chrome may use a labeled HTML placeholder.

## HiFi Author Self-Review

After the connected package passes the cheap completeness check, apply `../../delivery-harness/references/pre-delivery-self-review.md#hifi-self-review`. The same `frontend-design` author inspects actual renders and interactions under the Browser And Human Visual Approval restrictions below, checks the full contract and fixes in-scope defects before the independent review. Link existing browser, copy, motion and grading evidence rather than creating a second specification. Missing visual evidence stays blocked or unvalidated. This self-review does not replace or reset the following independent diagnostic and repair budget.

## Impeccable Quality Review And PRD-Bound Grading

Browser, Impeccable and rubric checks below form one diagnostic wave on the same frozen candidate.
The lead uses current shared evidence and returns one consolidated assessment, not sequential independent review waves.
Keep Impeccable's required internal workflow and both PASS records; its native totals never replace H1-H9.

Before human visual approval:

1. Freeze the PRD, `ui-design.md`, and HiFi candidate paths and SHA-256 values.
2. Run the cheap machine completeness preflight on the exact `ui-hifi/2` entry, manifest and sibling hashes against the PRD UI Surface Contract and current UI decisions. Repair missing coverage on the candidate and rerun it before formal review.
3. Run `impeccable critique` and `impeccable audit` against the exact connected candidate only with explicit workflow authorization. Impeccable may have side effects, so it needs that authorization, but it is required: Visual Approval and publication need both PASS records, and a declined authorization leaves the stage `blocked`. Its Nielsen, detector, accessibility, responsive, performance, theming, and implementation-integrity scores are diagnostic evidence. Record exact `PASS` when the run covered its required scope and every finding is in the ledger as closed, an advisory or a block.
4. Run `ui-grading-rubric.md`'s Technical Hard Gate and complete `H1`–`H9` scoring. These scores, not Impeccable's native totals, decide readiness.
5. Consolidate every Impeccable and rubric finding into one root-cause defect ledger before editing.
6. Let `frontend-design` make one repair batch. Re-review the new SHA-256 under [Repair Re-review Scope](ui-grading-rubric.md#repair-re-review-scope).

Readiness requires an overall score of at least 85 and every H1-H9 dimension at least 80.
No block or disputed dimension may remain. Record the actual scores, even when they fail these thresholds.
After all readiness checks pass, do not repair merely to raise the overall score.
A second failed review stops at `blocked` unless the owner explicitly approves one changed strategy and acceptance matrix.

## Browser And Human Visual Approval

Use a fresh local browser context; Docker and Podman are optional, not UI prerequisites. The `sandboxed-offline-browser` method names the browser restrictions below, not a container runtime. Agent Browser can drive the review only when its actual browser setup enforces those restrictions and retains the required evidence; screenshots alone are insufficient. Record the supported underlying browser tool accurately rather than relabeling an unsupported tool.

Enable direct CDP `Log` and `Runtime` channels before the first page load. Keep those channels on through capture completion, and never clear their buffers. Action-navigation setup may occur after trusted source setup; native console capture does not begin with that action transcript.

Render every page-target-state and overlay in a real browser inside a closed offline browser context and record the actual PASS, FAIL, MISSING or BLOCKED verdict; never fill a success by default. For schema 2, load the hash-checked pages into an isolated same-origin browser context using intercepted, locally fulfilled document requests; disable external network, service workers, popups, downloads, and forms. Allow only the exact declared HTML documents and block redirects or other destinations. Reset to the declared source page/state before each test. Click each product control and activate it by keyboard at every source responsive target; wait for the destination, then verify its visible surface/state and correct focus or selected-tab behavior. Begin the action transcript after trusted source-page/state setup completes. During each tested action, capture every attempted document navigation, including blocked ones, rather than filtering failures from the transcript. The review sidebar may set up a test but cannot be the tested control.

For the reviewer object, measure the product canvas's actual bounding width after each target change; never copy `data-hifi-target`. Traverse product and reviewer routes and record the selected target after each transition. Before and after target and Overview/Tokens switches, read the actual input value and selected option/value and record those observations. Verify Overview and Tokens hide every product surface, product navigation exposes exactly the destination surface, and recovery restores the originating surface. Compute each specimen from its bound source page, real specimen element and displayed value in that browser context. Static validator success never converts these fields into visual, aesthetic, or interaction PASS evidence.

HiFi surface evidence keeps method `sandboxed-offline-browser`. New packages require `ui-output/3` with the exact interaction results and local-navigation transcript described in `output-contract.md`. A missing result, wrong destination, invisible destination, bad focus, undeclared navigation, external request, popup, form attempt, or console error fails. Schema-1 references retain their existing `ui-output/1` no-navigation policy. Also reject unintended overlap, clipping, occlusion, broken wrapping, off-container content, or horizontal overflow. Verify long and localized content, normal/reduced motion, and intentional-overlay stacking and dismissal.

Proactively send one user-visible response with verified absolute Markdown links to the complete current schema-2 HiFi entrypoint, every manifest-listed sibling page, and the affected `ui-design.md` design handoff. Use the final logical paths in the authorized publication checkout for approval; after publication, link canonical files in the source checkout. Do not collect approval on `.ui-staging` paths. Say that the full approved scope is included, name what the owner should review, and ask explicitly for Visual Approval. A preview or panel open is convenience only and cannot replace the response or links; if any page or preview cannot be verified or opened, report that blockage instead of approval readiness.

Wait for the owner's explicit decision. Record it as `approved`, `revision_requested`, or `blocked` in `ui-design.md`, with the decision owner and date. The checker rejects an approval dated before the newest HiFi, Impeccable, grading or motion receipt; a repaired candidate needs a new owner decision. When the owner already reviewed the earlier candidate, present the repair diff and its changed pages; the owner may decide on that diff. Approval proves visual-direction conformance, not representative-user usability or production readiness.

## Retention And Design System Need Gate

Retain an approved all-screens target under `docs/design/ui-references/<run-id>/index.html` only with exact write approval. Record its SHA-256, routes, states, responsive scope, browser evidence, tolerance, and allowed deviations. Archive superseded references; never delete them or leave live pointers to archived paths.

After Visual Approval, record exactly one Design System Need result:

- `required`: a formal reusable token/component contract is needed or requested;
- `not_required`: the approved target, `ui-design.md`, and PRD are sufficient; or
- `blocked`: a required decision or source is missing.

When `required`, write `Compiled design system pair: pending — design-system-compiler` as the exact handoff marker, run the compiler preflight against the approved PRD/architecture/stack/UI/HiFi bytes, compile both files (`design-system/4` plus its derived HTML for `ui-design/3`, `design-system/3` for `ui-design/2`), and then replace the marker with both pair paths and hashes. The ordinary UI checker rejects a pending marker. When `not_required`, publish no placeholder pair and record the machine-bound existing-pair disposition.

A `ui-design/3` package never records `not_required`: it adds `Package action: compile|update|reuse` under the output contract. Its HiFi must carry `data-specimen-variant`/`data-specimen-state` on every product element the design system will display, because the compiled HTML derives component specimens only from those approved source elements.
