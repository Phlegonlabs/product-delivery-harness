# Wireframe Guide

Use this guide only after the core Product Definition package passes `python skills/product-definition-builder/scripts/check_product_package.py --prd <approved PRD.md> --architecture <approved architecture.md> --stack-decisions <approved stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved` from the repository root and records `Product Definition Approval: approved`. `ui-design-builder` owns one wireframe deliverable for every UI-bearing product: `docs/design/wireframes.html`.

Before new Wireframe authoring or repair, run `python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" --agents-md <target-AGENTS.md> --stage ui-design` with installed-command resolution. The actual writer loads the complete owner-pinned `frontend-design` skill in that same context before touching the candidate. A parent read, snapshot, role label or prior check is not invocation proof; do not backfill evidence or replace the owner binding. A missing or conflicting dependency blocks this authoring stage only and leaves prior approvals and closed historical records unchanged. This same-context rule grants no delegation; the direct parent may author. Template assemblers and reviewers provide shell construction and validation, not structural product-design judgment.

## Ownership

- `PRD.md` owns product scope, routes, screen purpose, required content and controls, actions, flows, states, implementation-bound copy and dynamic display contracts, the platform-appropriate responsive set and obligations, and `UI-*` / `UX-*` traces. UI Design Builder decides region grouping, order, layout, spans, reflow, density, and internal Wireframe Validation for schema 5.
- `ui-design.md` owns UI direction, motion and media intent, wireframe evidence, grading, and human UI decisions.
- `wireframes.html` is the interactive structural projection of that contract. It owns no new behavior and never changes product scope.
- A native mobile or desktop app is UI-bearing without a browser frontend and gets the same single `wireframes.html` deliverable: every `UI-*` screen in one file, with the product's own size classes standing in as the viewport toggle. The product ships no browser surface; the file exists purely as the review projection.
- When the HTML exposes a product gap, return it to `product-definition-builder`. A changed PRD invalidates Product Definition Approval; obtain approval for a new package revision, then regenerate only the affected `UI-*` page.
- HiFi work consumes the validated structural candidate. After delivery, routine accepted product fixes follow the current product and effective requirements; historical HTML is not regenerated solely to match them. A new product decision returns to `product-definition-builder`. A scoped UI enhancement validates its affected structure without rewriting unchanged product requirements.

## Design Translation

Apply `design-translation.md` before full authoring. Record task hierarchy, geometry, responsive/interaction rules, reading languages, motion boundaries and fixed/provisional handoff in the existing UI record. Select recipes from `composition-patterns.md`; none can add scope. Full redesign with retained PRD explicitly overrides the incremental-only authoring instructions below for its accepted scope. Product obligations remain unchanged.

## Reference Pass

Before drafting the HTML, look up how comparable products structure the same task, screen, and flow. The result is a small structural evidence set, not a mood board and not a list of fashionable products.

- Run it inline as part of wireframe drafting; it needs no separate delegation. Skip it only when the user declined it, no web search or fetch tool is available, or the package is a trivial stub, and record which reason applied.
- Inspect two to four useful sources in total. Start with first-party live products, official product documentation, or first-party case studies that expose the relevant task. Match a source to the exact screen or flow, not merely the same product category. A real reachable flow outranks a marketing screenshot or secondhand description.
- Inspect the source at the viewport and state needed to support the claim. A single desktop screenshot cannot establish mobile reflow, a still cannot establish interaction, and an isolated gallery image cannot establish a multi-screen flow. Mark those dimensions `not observable` instead of inferring them.
- Use a design gallery only as a supplemental composition source when first-party evidence does not show the needed structural alternative. Never let an isolated gallery image outrank a working product flow, and never carry its color, typography, imagery, or decorative styling into the structural wireframe.
- Record every source as a stable `WREF-*` entry under `Wireframe references consulted:` in `ui-design.md`'s `## Wireframe Validation` for schema 5, or its historical Wireframe Approval section for legacy work. Each entry names the direct URL, publisher, retrieval date, exact screen or flow, inspected viewport and state, evidence status (`observed`, `partial`, or `blocked`), structural mechanic, `Adopt / Adapt / Avoid` decision, product-fit reason, and limitation. Preserve IDs across revisions and never reuse a retired ID.
- References inform structure only. They never create scope, mint `UI-*` entries, or override the approved UI Design Intake. When a reference conflicts with `PRD.md`, `PRD.md` wins and the divergence is recorded as a revision note.
- A reference with no inspectable URL or attachment is `UNVALIDATED`. A visual source proves no market claim, and a market source becomes structural evidence only after its relevant screen is separately inspected.

## HTML Requirements

### Mid-Fidelity Completion Standard

The target is a mid-fidelity interactive structural prototype. Use exact product copy, realistic bounded data, readable type roles, intentional spacing, task-fit proportions and distinct navigation, list, table and form structures. Inspect long copy, dense data and every PRD-required alternate state at the declared responsive targets. Images remain labeled placeholders with purpose and proportions; final brand assets and animation belong to HiFi.

Walk each declared primary journey using product controls, including keyboard operation where applicable. Review-shell page/state switching is capture setup, not journey evidence. Required input, validation and recovery behavior must be represented locally from the approved PRD, with no network or real account side effects. The template's local field inputs retain edits for review, but only declared actions and flows prove a product journey; if the canonical runtime cannot express a required interaction, record the unsupported case as blocked and extend the canonical renderer and checker together before approval. Do not modify the frozen shell ad hoc, invent behavior, or call an undeclared flow complete.

### Left Sidebar And Initial Page

Keep Overview, every product page, responsive targets and state controls in the fixed left reviewer sidebar. Open the first declared product page by default; preserve explicit page and `#overview` links. Unknown hashes recover to the first page and its first state. Put the complete screen/flow summary in Overview, reached intentionally from the sidebar. Product previews keep their own task controls; reviewer navigation is not product interaction evidence.

### Historical Design System Draft View (wireframes/4 only)

For an unchanged schema-4 package, every displayed prototype value has an applied visual specimen, not just a number. Include the font family, control border/large sizes and wide/compact table insets actually used by the renderer. Show the action variants present in the product and read measured geometry from the active target.

The reviewer navigation includes `Design System` at `#design-system`, labeled `Wireframe Draft`. It is not a product surface, route or `UI-*` entry and does not join the product copy inventory. It shows prototype type sizes/weights/line heights, neutral colors, spacing, control dimensions, padding and corners, plus type, button, field, list and table specimens. Specimen wording is reviewer-only. Actual product wording remains in its approved copy records.

Use the same CSS values and renderer classes as the product canvas. Read values from those sources and computed specimens; do not hand-maintain a second value table. Keep reviewer chrome separate from the `--wf-*` prototype values. These values describe the current prototype, not approved brand tokens, a production library or native rendering proof. Record additional platform or product-specific values only when the actual renderer uses them.

Check navigation, keyboard focus, specimen behavior, wrapping and value equality alongside the existing browser matrix. W5 judges hierarchy and consistency, while W3 checks real product journeys. Static checks cannot certify either. A changed historical Draft view changes that HTML approval identity. Preserve approved legacy bytes. New schema-5 authoring has no Draft/Tokens view; formal values appear later in the compiler's separate derived preview when required.

Use `assets/templates/WIREFRAMES.template.html`. Generate one self-contained file containing every `UI-*` surface. It must open directly from disk without a server, build step, package install, network request, external font, or external asset. The checker decodes CSS escapes before evaluating `url()`, `image-set()`, and `@import`, so escaped remote schemes are rejected like literal ones.

The current template starts with four web review widths: **390, 768, 1024, and 1440 px**. Each example screen includes a layout for every width. These are review targets, not mandatory CSS breakpoints. Use the exact approved PRD targets when authoring a product; this default does not replace existing contracts or native size classes. Retain historical schema-4 templates and approvals.

For App + companion Web packages, follow `../../product-definition-builder/references/mobile-stack-selection.md#app-and-companion-web-contract`. The single wireframe includes the approved iOS, Android and Web screens, labeled by platform and bound to distinct `UI-*` entries. Use `responsiveBySurface` for every screen and omit global responsive keys. Native phone targets have their own named size classes and explicit canvas widths; Web uses its approved numeric viewports. Preserve platform navigation, safe areas, keyboard/text-scaling obligations and cross-surface journeys. Sharing a framework does not make Android behavior identical to iOS, and the showcase is not an app screen. Carry these same platform bindings into HiFi; HTML projections never substitute for native implementation tests.

New and structurally revised files use schema `wireframes/5`; the checker keeps `wireframes/2` through `wireframes/4` read compatibility for unchanged historical files. Schema 5 must provide:

1. an all-pages overview plus a page switcher showing each `UI-*` ID, page name, route or surface, and primary goal;
2. controls generated from the exact PRD responsive contract: a single-platform file uses one global set of at least three ascending positive numeric `viewports` for web/extensions or at least two ordered string `sizeClasses` for native/desktop; a hybrid file omits both global keys and uses `responsiveBySurface`, with exactly one `{kind, targets, canvasWidths}` entry for every `UI-*` screen and one positive review-canvas width per target;
3. a state selector for every required state represented by that screen;
4. annotation-mode reviewer-only section labels such as `Global Header`, `Hero Section`, `Feature Grid`, `Primary Workspace`, `Results Table`, or `CTA`, using product-fit labels rather than a fixed catalog;
5. implementation-bound product copy rendered in the canvas, with reviewer-only purpose, priority, traces, layout rules, and source notes kept in the inspector;
6. a copy inventory, visible `structureStatus`, and screen-level copy statuses; and
7. visible runtime layout QA for the selected page, responsive target, and state.

Create one screen for every `UI-*` entry in `PRD.md`; do not create an untraced screen. Every entry carries exactly one invariant `` `copy`: `` anchor whose status matches the screen's `copyStatus`. The canvas distinguishes product copy from reviewer notes:

- Static product copy uses `{kind: "static", role, text, status, source}`. `text` is the exact string the implementation must reuse. This includes navigation, headings, buttons, field labels, instructions, validation, loading announcements, empty states, errors, permission messages, confirmations, recovery, and other user-visible or assistive text.
- Dynamic content uses `{kind: "dynamic", role, example, status, source, contract}`. `example` is realistic review data, not a string to ship. `contract` states `source`, `order`, `format`, `count`, `length`, and exact `fallback` copy.
- Schema-5 actions use `{id, label, status, source}`. `id` is the stable PRD product control ID rendered as `data-control-id`; the exact label remains the flow trigger. A copied label cannot stand in for a missing control ID. Historical schema-4 actions retain `{label, status, source}`.
- A `feedback` flow also carries one structured `feedback` copy item. The reviewer shows that approved text directly; it never invents `Result:` or another runtime message from the flow target.
- The first state is `ready`, the schema-4 baseline. Alternate-state treatments use `{layout, copy}`. `layout` is reviewer-only; every alternate state supplies at least one exact visible or assistive copy item, even when its visible treatment is primarily a skeleton or other non-text state.

Schema 5's top-level `structureStatus` is `draft`, `validated`, or `blocked`. Its `copyInventory` has exactly `locale`, a BCP 47-style tag. Schema 5 has no root `approvalStatus` or `copyFreeze`; `--require-structure-validated` checks a validated structure and its canonical shell, but never mints a human approval. Screen and copy-item `draft`/`approved` statuses remain source facts for PRD joins.

The schema-5 reviewer persists selected responsive target and state in session storage under `wireframe-review:<data fingerprint>:<platform>:<screen>`. The fingerprint comes from the embedded wireframe data; the platform and screen keys keep each canvas independent. A changed package or unknown stored selection falls back to that screen's first valid target and state. This is reviewer convenience, not product state or approval evidence.

Schema 4 remains a historical authoring contract. Its top-level `copyFreeze` records `status`, human `owner`, primary BCP 47 `locale`, and `approvedOn`. An approved Copy Freeze requires an ISO `YYYY-MM-DD` date, every screen `copyStatus: approved`, and every static, dynamic-contract, action, feedback, and alternate-state copy item `status: approved`. No placeholder or draft product copy survives `--require-filled --require-approved`. The approved HTML hash freezes the words together with structure; no separate hand-maintained copy digest is needed.

Use the template's embedded data block as the only product-specific input. Replace its example screens with the complete surface set and escape `<`, `>`, `&`, U+2028, and U+2029 inside JSON string values before embedding untrusted or user-supplied text. Render values through `textContent`, not `innerHTML`.

Project the PRD's flows and traces through the same block. In schema 5, each flow keeps `{from, trigger, to, presentation}` and adds `sourceState`, `control`, and `destination:{surface,state}`. `control` equals the rendered action `id`; `sourceState` and destination identify declared PRD states. For `page` and `overlay` flows, `to` matches the destination surface; for `feedback`, it matches the exact feedback copy. Route by source state and control, then apply the destination state. `trigger` matches that action's exact `label`. `presentation` is `page`, `overlay`, or `feedback`; feedback also carries structured copy and never performs a network request. Product buttons switch screens, open an accessible local dialog, or show exact approved local feedback. A label may repeat across distinct regions only when the source-state/control binding remains unambiguous; repeating it within one region fails, and at least one copy remains visible per responsive target. Per-screen or per-region `traces` list the `UX-*` IDs the surface traces to. Historical schema-4 flows retain `{from, trigger, to, presentation}` and their original behavior.

An optional `mediaIntent` object on a screen or region records the approved Motion and Media Intent decision. It carries a stable `id` equal to its `MM-*` row plus `treatment` — `none`, `image`, `motion`, or `image + motion` — plus non-empty `purpose`, `trigger`, `draftPrompt`, `source`, `reducedMotionFallback`, and `generationRoute`, with `generationStatus: deferred`. Add one only where a decision exists. A blocked region returns to the owning product or design decision before validation. The reviewer shell renders the record as a visible note. The wireframe implements no final image or animation and invokes no provider. Deterministic UI motion and generated assets are routed only after structure validation under `motion-and-media-routing.md`.

Every PRD `UI-*` entry carries one invariant `` `responsive`: `` anchor. Its kind and values match either the HTML's single global set or that screen's exact `responsiveBySurface` entry. A hybrid entry also preserves the PRD `releaseSurface`, `surfaceClass`, and `captureMode`; one platform's targets never stand in for another's. Every screen carries a non-empty `neverDrop` list and a `responsiveLayouts` object keyed by its own targets. Each target entry declares `order`, `hidden`, `columns`, a `spans` value for every region, plus filled `reflow` and `interaction` rules. `order` contains every region exactly once. `hidden` may omit secondary material only; it cannot contain a never-drop region, and every primary region belongs to `neverDrop`. These fields make responsive behavior inspectable instead of treating a generic compact stack as proof.

Schema-4 may add a bounded `composition` object to a target layout when relative geometry needs to be explicit. Its shape is `{ "canvas": { "padding": number, "gap": number }, "regions": { "region-id": { "padding"?: number, "gap"?: number, "maxWidth"?: number, "actionsPlacement"?: "before" | "after" | "inline", "itemColumns"?: integer, "mediaAspectRatio"?: number } } }`. `canvas.padding` and `canvas.gap` are 0–128; region padding and gap are 0–128; `maxWidth` is 1–2400; `itemColumns` is 1–12; and `mediaAspectRatio` is 0.25–4. Unknown keys or region IDs fail validation. The template applies these values to the review canvas, region spacing and measure, action position, list columns and media placeholder ratio; they are not arbitrary CSS or product behavior.

Inline CSS and JavaScript implement the reviewer studio, page switching, working PRD actions, local overlays and feedback, viewport switching, state switching, copy inventory, reviewer-only inspector, and printing. They are not product implementation. Keep the canvas grayscale and structural: use typography, spacing, content silhouettes, and contrast only to make hierarchy legible. Add no brand palette, decorative imagery, generated media, final animation, production component library, polished marketing treatment, or formal design-system token decision. Shared prototype values may style the structural canvas, but schema 5 has no Draft view.

## Composition Before Coverage

Use the W5 composition criteria in `ui-grading-rubric.md` while authoring, before final structure validation. Start with a frequent task and a dense or alternate-state case at wide and compact targets; inspect their hierarchy, spacing, content form, and reflow before expanding the full surface matrix. This is an authoring checkpoint, not another human approval. Do not alter the approved product scope or wording to make a composition easier.

The formal wireframe opens with annotations visible over a composed neutral-grayscale interface. Hide annotations provides an optional clean view; it never substitutes for designing the page. Show each region's name, purpose, column allocation and measured width/padding, plus the canvas's measured insets and row/column gaps. Keep detailed notes outside product copy and provide a keyboard-accessible way to locate the corresponding region. Product actions, content and destinations remain unchanged when toggling notes. Do not use inherited brand color, identical card wrappers, or fixed empty region heights as a substitute for hierarchy.

Describe each action in plain language with the destination page name and ID: go to a page, open a dialog over the current page, or stay here and show the recorded result. Display both incoming and outgoing connections. Local search and reset notes describe their actual local behavior. Missing destinations stay visibly unresolved; never invent a return path, state-preservation promise or backend effect. Product controls demonstrate the journey; annotation links only inspect its target.

A region may declare `presentation`: `content` (default), `navigation`, `editorial`, `list`, `form`, or `table`. These are structural treatments, not product component or stack choices. Preserve the existing copy records and sources:

- `list` uses exact `list item` roles for rows; other copy precedes the list.
- `table` uses exact `table header` roles followed by `table cell` records in row-major order. At least one header and one complete row are required. Introductory copy precedes the headers; interleaved copy is rejected rather than reordered. Preserve readable column relationships at compact targets; wide tables need a product-approved reflow design, not tiny text.
- `form` uses exact `field label` roles and an optional immediately following `field value` record. The template renders labeled local text inputs that can be edited in the review file and retain their values across page, target and reviewer-panel switches. Submission, validation and recovery still require declared PRD actions and flows; editable placement alone never invents a product journey or side effect.
- `navigation` groups orientation and existing actions; `editorial` provides a leading text hierarchy. Neither infers routes, action priority, or product behavior.

A region may set `primaryAction` to exactly one existing action label to give that control primary emphasis. Derive it from the approved task hierarchy; array order never implies priority. Alternate-state copy replaces the baseline region content and deferred media rather than displaying stale data underneath it; existing actions retain their declared destinations.

Existing files without `presentation` remain readable. New authoring must choose the content form that fits the actual task rather than leaving every region as generic content. Extend the local renderer within the approved contract when these treatments cannot express the product; never pass an inaccurate projection merely because the template can render it.

### Local Search Projection

Schema-4 screens may declare one bounded, local-only search projection when the approved product flow needs an editable query and language filter. It is optional and adds no product scope or network behavior. The exact shape is:

```json
{
  "localSearch": {
    "formRegion": "search-form",
    "resultsRegion": "search-results",
    "queryLabel": {"kind": "static", "role": "field label", "text": "Search", "status": "approved", "source": "..."},
    "languageLabel": {"kind": "static", "role": "field label", "text": "Language", "status": "approved", "source": "..."},
    "languageOptions": [
      {"value": "all", "copy": {"kind": "static", "role": "select option", "text": "All languages", "status": "approved", "source": "..."}}
    ],
    "submitAction": "Search",
    "clearAction": "Clear",
    "states": {"initial": "ready", "results": "results", "empty": "no-results"},
    "items": [
      {
        "language": "en",
        "copy": {"kind": "dynamic", "role": "list item", "example": "Example result", "status": "approved", "source": "...", "contract": {"source": "...", "order": "...", "format": "...", "count": "...", "length": "...", "fallback": "..."}},
        "searchText": "Example result"
      }
    ]
  }
}
```

`formRegion` and `resultsRegion` reference existing regions; the results region uses the `list` presentation. The first language option is the unfiltered option used by Clear. Labels and options are static copy, while item copy is dynamic copy with the normal source/order/format/count/length/fallback contract. `items` is local bounded review data (at most 10,000 items and 4,096 search characters per item); it is not a network-backed result set. `states` references three existing screen states, and their results/empty treatments provide the approved count or empty copy. Search, Enter, language changes, and Clear operate only on this local item set; Search and Clear still map to the screen's declared flows for contract coverage, but the reviewer intercepts them locally. Results always render the matching rows as well as any approved results treatment, and Clear restores the first option, the initial state, and query focus.

## Reading, Control And Motion Fields

Schema-4 copy items may declare `locale` (BCP 47-style tag), `direction` (`ltr`, `rtl`, `auto`) and `parallel` (one to three complete copy items). Parallel items have distinct explicit locales, the same role/kind as the primary item, their own status/source and dynamic contract when needed, and no nested parallel items. The primary locale is also required. The renderer stacks each language as a naturally wrapping block in the same semantic heading/paragraph. All parallel shipping text participates in sourced copy validation; stress-only translations remain separate review evidence, never accepted by implication. Input values and select options reject stacked pairs; action labels keep their existing single-language semantics; use the content pair for explanations rather than inventing bilingual control names.

A navigation region may declare `disclosure: {targets: ["390"], label: <static copy item>}` using only its declared responsive target keys. The native HTML details/summary control opens inline, supports keyboard activation and Escape with focus return, and becomes expanded navigation at other targets. It adds no new route or destination. Its exact toggle label is part of sourced copy and the copy inventory. A modal drawer instead uses an approved overlay flow with separate focus/backdrop/dismissal checks; do not count an inline disclosure as drawer evidence.

Schema 5 navigation regions may add bounded `controls`. A menu is `{id, label, items, targets, defaultOpen}`: `items` are distinct action labels already declared in that region and `targets` are declared responsive targets. The renderer keeps the real action buttons, toggles `aria-expanded`, supports Arrow Up/Down, and returns focus on Escape. A tab is `{id, label, state}` and must name a declared screen state. Tab buttons use ARIA tab semantics, Arrow Left/Right/Home/End, and change the rendered state rather than only their highlight. No control configuration invents a route, action, state, disabled treatment, or product copy.

Actions may declare `variant: secondary|tertiary|destructive`, `size: regular|large` and boolean `fullWidth`. The existing `primaryAction` remains the only primary-emphasis selector and overrides a variant. Destructive styling is structural grayscale, not a substitute for an explicit action label and confirmation flow. These fields change no destinations and do not invent disabled/loading behavior: use approved state/flow treatments for those cases and verify them in the browser. Fine dimensions remain provisional for HiFi.

Motion-bearing `mediaIntent` may carry the bounded `motionSpec` from `motion-and-media-routing.md`; new motion authoring supplies it. Strict schema-4 region checks (`--require-filled` or `--require-approved`) reject motion treatments without it; non-strict inspection keeps legacy records readable. The renderer outlines and labels the region in annotation mode, including trigger, behavior, layout reservation, phone treatment, playback/cost and reduced-motion fallback. Old records without this extension remain readable and require semantic migration review rather than fabricated metadata. Same source identity does not prove old records meet new authoring guidance.

## Wireframe Validation Gate (wireframes/5)

Load and use `frontend-design` for actual structural hierarchy, composition and interactions. Complete every sourced static and dynamic copy item and the BCP 47 `copyInventory.locale`; keep reviewer notes outside product copy. Record the exact candidate and concrete authoring choices under `## Wireframe Validation` → `### Frontend Design Usage` in `ui-design.md`.

Run the package and PRD checks on the candidate, then W1–W5 grading against the approved product scope. Use one complete diagnostic wave, one consolidated repair batch and one re-review; a second failure needs the owner's changed strategy and acceptance matrix. Require overall and W5 at least 80, every dimension at least 60, and no block. Grade actual task hierarchy, responsive composition and real journeys; a score cannot excuse a missing control or PRD contradiction.

Open the file in a real browser and exercise every `UI-*` × responsive target × applicable state. Check the exact canvas width, legible content, layout QA, keyboard, focus, dialogs, disclosure, menus, tabs and PRD operation destinations. No reviewer-shell or canvas element may be unintentionally overlapped, clipped, occluded, or cause horizontal page scrolling. Intended overlays need declared stacking, focus and dismissal. Record actual `ui-output/3` observations and `ui-evidence/3` receipts under `Responsive surface check` and `UI grading`; static validation alone cannot claim browser PASS.

Set `structureStatus: validated` only after the full structure, sourced copy, responsive and interaction checks pass. Record `Structure validation: validated` and the current candidate hash in `ui-design.md`. Run from the target repository root with the observed installed skill path:

```text
python "<ui-design-builder-skill-root>/scripts/check_wireframe_html.py" --html <wireframes.html> --prd <approved PRD.md> --require-filled --require-structure-validated
python "<ui-design-builder-skill-root>/scripts/check_ui_design_contract.py" --repo-root <repository-root> --ui-design <ui-design.md> --prd <approved PRD.md> --wireframes <wireframes.html> --require-filled --require-structure-validated
```

This is internal validation. Schema 5 has no human Copy Freeze or Wireframe Approval. The owner reviews copy and structure with the complete HiFi at the later consolidated Visual Approval. A failed check remains blocked; no machine result grants human approval.

## Historical Wireframe Approval (wireframes/4 and earlier)

Unchanged schema-4 packages keep their original Copy Freeze and human Wireframe Approval meaning. Their `copyFreeze`, `approvalStatus`, `--require-copy-approved` and `--require-approved` checks remain available for reading or explicitly scoped legacy recovery. Preserve actual owner, dates and receipts; never relabel them as schema 5 or fabricate approval. A new enhancement package uses schema 5 and validates its affected scope without rewriting older approvals.
## Enhancement Revisions

An enhancement run first classifies the delta's UI impact with the owner — `none`, `structure`, `style`, or `both`. Never assume `none` because the request reads backend- or data-side.

Apply `enhancement-recommendations.md`'s Incremental UI Scope before authoring. Append a new screen or patch named regions in the existing data; retain all other screen objects, copy, composition and flow bindings. Necessary entry links are a named change, not permission to redesign their entire page. Re-serializing the container HTML does not authorize new product content or geometry. Review the full package without re-authoring the preserved scope.

- `none`: preserve `wireframes.html` and any approved UI target verbatim.
- `structure` or `both`: update the affected `UI-*` entries in `PRD.md` first, then regenerate the affected pages in `wireframes.html`, then re-run Wireframe Validation on the changed scope and refresh `## Wireframe Validation`. A changed PRD UI contract with a stale wireframe artifact is not a complete package.
- `style` or `both`: re-run `references/ui-design-pass.md` for the affected scope. Reuse the recorded approved direction unless the accepted delta changes it; do not seek a fresh style selection merely because a page was added. Refresh affected target and source bindings, and renew applicable approval/evidence. A stale visual contract never publishes silently.

A user-visible wording change is a copy delta and uses `structure` (or `both` when style also changes) under the existing four-value UI-impact classifier. Update the affected PRD `` `copy` `` anchors and schema-4 items, return affected schema-5 copy items and screen `copyStatus` to `draft`, inspect every impacted viewport and state for reflow, and renew Wireframe Validation plus the affected Visual Approval when this is an active design enhancement. A dynamic source/order/format/count/length/fallback change follows the same route even when its representative example stays unchanged.

## Quality Check

- Every `UI-*` entry appears exactly once and every route remains owned by exactly one PRD surface.
- Region order and actions agree with `PRD.md`; every visible action works from the local file.
- Every `flows` entry starts from a known screen ID, names `page`, `overlay`, or `feedback`, and matches exactly one visible action plus one PRD flow; `page` and `overlay` target known screens, and `traces` match the `UX-*` records in `PRD.md`.
- Every static string, action label, feedback message, and alternate-state message is exact implementation-bound copy with status and source; every dynamic item has a realistic example and complete source/order/format/count/length/fallback contract.
- The canvas shows product copy while reviewer-only purpose, priority, traces, responsive rules, and source notes stay visually separate in the inspector.
- Every required state is represented or explicitly `n/a` in the PRD.
- Every responsive layout contains every region exactly once, hides no never-drop region, and preserves all never-drop content and actions.
- Every schema-4 `mediaIntent` annotation names a valid treatment (`none`, `image`, `motion`, or `image + motion`), purpose, trigger, dedicated prompt, source, reduced-motion fallback, generation route, and `generationStatus: deferred`.
- Every page-target-state combination renders without unintended overlap, clipping, occlusion, or horizontal overflow; intended overlays have documented stacking, focus, and dismissal behavior.
- The page switcher, overview, responsive-target control, state control, copy inventory, reviewer-only inspector, runtime layout QA, and visible section labels work from a local file.
- No design-reference styling, generated imagery, formal design-system token contract, or product implementation code appears. Schema 5 has no Draft or Tokens view.
- `check_wireframe_html.py` passes with `--prd <approved PRD.md> --require-filled --require-structure-validated` after the full browser matrix and structure checks.
- The PRD-bound diagnostic stage ran as one complete diagnostic wave with its scores, consolidated defect ledger, and bounded repair/re-review outcome recorded; an unavailable capability is a blocking outcome, not a skipped PASS.
- `ui-design.md` records the validated `UI-*` scope, source identities, primary locale, actual evidence, grading and unresolved items under Wireframe Validation. New product wording returns to Product Definition; routine maintenance keeps historical design records intact.

If any check fails, keep the package staged and repair the PRD or HTML before approval.
