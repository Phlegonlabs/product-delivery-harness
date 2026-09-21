# Wireframe Guide

Use this guide only after the core Product Definition package passes `python skills/product-definition-builder/scripts/check_product_package.py --prd <approved PRD.md> --architecture <approved architecture.md> --stack-decisions <approved stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved` from the repository root and records `Product Definition Approval: approved`. `ui-design-builder` owns one wireframe deliverable for every UI-bearing product: `docs/design/wireframes.html`.

## Ownership

- `PRD.md` owns product scope, routes, screen purpose, required content and controls, actions, flows, states, implementation-bound copy and dynamic display contracts, the platform-appropriate responsive set and obligations, and `UI-*` / `UX-*` traces. UI Design Builder decides region grouping, order, layout, spans, reflow, density, and the staged Copy Freeze review.
- `ui-design.md` owns UI direction, motion and media intent, wireframe evidence, grading, and human UI decisions.
- `wireframes.html` is the interactive structural projection of that contract. It owns no new behavior and never changes product scope.
- A native mobile or desktop app is UI-bearing without a browser frontend and gets the same single `wireframes.html` deliverable: every `UI-*` screen in one file, with the product's own size classes standing in as the viewport toggle. The product ships no browser surface; the file exists purely as the review projection.
- When the HTML exposes a product gap, return it to `product-definition-builder`. A changed PRD invalidates Product Definition Approval; obtain approval for a new package revision, then regenerate only the affected `UI-*` page.
- Later visual or implementation work consumes the approved HTML but does not edit it. Structural changes return to `product-definition-builder`.

## Reference Pass

Before drafting the HTML, look up how comparable products structure the same task, screen, and flow. The result is a small structural evidence set, not a mood board and not a list of fashionable products.

- Run it inline as part of wireframe drafting; it needs no separate delegation. Skip it only when the user declined it, no web search or fetch tool is available, or the package is a trivial stub, and record which reason applied.
- Inspect two to four useful sources in total. Start with first-party live products, official product documentation, or first-party case studies that expose the relevant task. Match a source to the exact screen or flow, not merely the same product category. A real reachable flow outranks a marketing screenshot or secondhand description.
- Inspect the source at the viewport and state needed to support the claim. A single desktop screenshot cannot establish mobile reflow, a still cannot establish interaction, and an isolated gallery image cannot establish a multi-screen flow. Mark those dimensions `not observable` instead of inferring them.
- Use a design gallery only as a supplemental composition source when first-party evidence does not show the needed structural alternative. Never let an isolated gallery image outrank a working product flow, and never carry its color, typography, imagery, or decorative styling into the structural wireframe.
- Record every source as a stable `WREF-*` entry under `Wireframe references consulted:` in `ui-design.md`'s `## Wireframe Approval`. Each entry names the direct URL, publisher, retrieval date, exact screen or flow, inspected viewport and state, evidence status (`observed`, `partial`, or `blocked`), structural mechanic, `Adopt / Adapt / Avoid` decision, product-fit reason, and limitation. Preserve IDs across revisions and never reuse a retired ID.
- References inform structure only. They never create scope, mint `UI-*` entries, or override the approved UI Design Intake. When a reference conflicts with `PRD.md`, `PRD.md` wins and the divergence is recorded as a revision note.
- A reference with no inspectable URL or attachment is `UNVALIDATED`. A visual source proves no market claim, and a market source becomes structural evidence only after its relevant screen is separately inspected.

## HTML Requirements

### Mid-Fidelity Completion Standard

The target is a mid-fidelity interactive structural prototype. Use exact product copy, realistic bounded data, readable type roles, intentional spacing, task-fit proportions and distinct navigation, list, table and form structures. Inspect long copy, dense data and every PRD-required alternate state at the declared responsive targets. Images remain labeled placeholders with purpose and proportions; final brand assets and animation belong to HiFi.

Walk each declared primary journey using product controls, including keyboard operation where applicable. Review-shell page/state switching is capture setup, not journey evidence. Required input, validation and recovery behavior must be represented locally from the approved PRD, with no network or real account side effects. The template's local field inputs retain edits for review, but only declared actions and flows prove a product journey; if the canonical runtime cannot express a required interaction, record the unsupported case as blocked and extend the canonical renderer and checker together before approval. Do not modify the frozen shell ad hoc, invent behavior, or call an undeclared flow complete.

### Left Sidebar And Initial Page

Keep Overview, every product page, Design System, responsive targets and state controls in the fixed left reviewer sidebar. Open the first declared product page by default; preserve explicit page, `#overview` and `#design-system` links. Unknown hashes recover to the first page and its first state. Put the complete screen/flow summary in Overview, reached intentionally from the sidebar. Product previews keep their own task controls; reviewer navigation is not product interaction evidence.

### Design System Draft View

The reviewer navigation includes `Design System` at `#design-system`, labeled `Wireframe Draft`. It is not a product surface, route or `UI-*` entry and does not join the product copy inventory. It shows prototype type sizes/weights/line heights, neutral colors, spacing, control dimensions, padding and corners, plus type, button, field, list and table specimens. Specimen wording is reviewer-only. Actual product wording remains in its approved copy records.

Use the same CSS values and renderer classes as the product canvas. Read values from those sources and computed specimens; do not hand-maintain a second value table. Keep reviewer chrome separate from the `--wf-*` prototype values. These values describe the current prototype, not approved brand tokens, a production library or native rendering proof. Record additional platform or product-specific values only when the actual renderer uses them.

Check navigation, keyboard focus, specimen behavior, wrapping and value equality alongside the existing browser matrix. W5 judges hierarchy and consistency, while W3 checks real product journeys. Static checks cannot certify either. A changed draft view changes the HTML approval identity. Once approved, preserve that file; later formal values appear in the compiler's separate derived preview, never by rewriting the approved wireframe.

Use `assets/templates/WIREFRAMES.template.html`. Generate one self-contained file containing every `UI-*` surface. It must open directly from disk without a server, build step, package install, network request, external font, or external asset. The checker decodes CSS escapes before evaluating `url()`, `image-set()`, and `@import`, so escaped remote schemes are rejected like literal ones.

New and structurally revised files use schema `wireframes/4`; the checker keeps `wireframes/2` and `wireframes/3` read compatibility for unchanged historical files. Schema 4 must provide:

1. an all-pages overview plus a page switcher showing each `UI-*` ID, page name, route or surface, and primary goal;
2. controls generated from the exact PRD responsive contract: a single-platform file uses one global set of at least three ascending positive numeric `viewports` for web/extensions or at least two ordered string `sizeClasses` for native/desktop; a hybrid file omits both global keys and uses `responsiveBySurface`, with exactly one `{kind, targets, canvasWidths}` entry for every `UI-*` screen and one positive review-canvas width per target;
3. a state selector for every required state represented by that screen;
4. annotation-mode reviewer-only section labels such as `Global Header`, `Hero Section`, `Feature Grid`, `Primary Workspace`, `Results Table`, or `CTA`, using product-fit labels rather than a fixed catalog;
5. implementation-bound product copy rendered in the canvas, with reviewer-only purpose, priority, traces, layout rules, and source notes kept in the inspector;
6. a copy inventory, visible structural approval status, and visible Copy Freeze status; and
7. visible runtime layout QA for the selected page, responsive target, and state.

Create one screen for every `UI-*` entry in `PRD.md`; do not create an untraced screen. Every entry carries exactly one invariant `` `copy`: `` anchor whose status matches the screen's `copyStatus`. The canvas distinguishes product copy from reviewer notes:

- Static product copy uses `{kind: "static", role, text, status, source}`. `text` is the exact string the implementation must reuse. This includes navigation, headings, buttons, field labels, instructions, validation, loading announcements, empty states, errors, permission messages, confirmations, recovery, and other user-visible or assistive text.
- Dynamic content uses `{kind: "dynamic", role, example, status, source, contract}`. `example` is realistic review data, not a string to ship. `contract` states `source`, `order`, `format`, `count`, `length`, and exact `fallback` copy.
- Actions use `{label, status, source}`. Their exact labels remain the flow triggers, so implementation cannot silently rename a control without a copy delta.
- A `feedback` flow also carries one structured `feedback` copy item. The reviewer shows that approved text directly; it never invents `Result:` or another runtime message from the flow target.
- The first state is `ready`, the schema-4 baseline. Alternate-state treatments use `{layout, copy}`. `layout` is reviewer-only; every alternate state supplies at least one exact visible or assistive copy item, even when its visible treatment is primarily a skeleton or other non-text state.

Schema 4's top-level `copyFreeze` records `status`, human `owner`, primary BCP 47 `locale`, and `approvedOn`. An approved Copy Freeze requires an ISO `YYYY-MM-DD` date, every screen `copyStatus: approved`, and every static, dynamic-contract, action, feedback, and alternate-state copy item `status: approved`. No placeholder or draft product copy survives `--require-filled --require-approved`. The approved HTML hash freezes the words together with structure; no separate hand-maintained copy digest is needed.

Use the template's embedded data block as the only product-specific input. Replace its example screens with the complete surface set and escape `<`, `>`, `&`, U+2028, and U+2029 inside JSON string values before embedding untrusted or user-supplied text. Render values through `textContent`, not `innerHTML`.

Project the PRD's flows and traces through the same block. `flows` lists each flow as `{from, trigger, to, presentation}` plus structured `feedback` copy when that presentation applies, where `from` is a screen ID, `trigger` exactly matches one visible action object's `label` on that screen, and `presentation` is `page`, `overlay`, or `feedback`. A `page` or `overlay` target is another `UI-*` screen in the same file; `feedback` may name a local result or external destination but never performs a network request. The reviewer shell renders region actions as working buttons: `page` switches screens, `overlay` opens an accessible local dialog for the target screen, and `feedback` shows its exact approved local message. A label may repeat across distinct regions only when all copies resolve to the same single outgoing flow; repeating it within one region fails, and at least one copy must remain visible in a responsive target. Per-screen or per-region `traces` list the `UX-*` IDs the surface traces to.

An optional `mediaIntent` object on a screen or region records the approved Motion and Media Intent decision. It carries a stable `id` equal to its `MM-*` row plus `treatment` — `none`, `image`, `motion`, or `image + motion` — plus non-empty `purpose`, `trigger`, `draftPrompt`, `source`, `reducedMotionFallback`, and `generationRoute`, with `generationStatus: deferred`. Add one only where a decision exists. A blocked region returns to the owner before wireframe approval. The reviewer shell renders the record as a visible note. The wireframe implements no final image or animation and invokes no provider. Deterministic UI motion and generated assets are routed only after structural approval under `motion-and-media-routing.md`.

Every PRD `UI-*` entry carries one invariant `` `responsive`: `` anchor. Its kind and values match either the HTML's single global set or that screen's exact `responsiveBySurface` entry. A hybrid entry also preserves the PRD `releaseSurface`, `surfaceClass`, and `captureMode`; one platform's targets never stand in for another's. Every screen carries a non-empty `neverDrop` list and a `responsiveLayouts` object keyed by its own targets. Each target entry declares `order`, `hidden`, `columns`, a `spans` value for every region, plus filled `reflow` and `interaction` rules. `order` contains every region exactly once. `hidden` may omit secondary material only; it cannot contain a never-drop region, and every primary region belongs to `neverDrop`. These fields make responsive behavior inspectable instead of treating a generic compact stack as proof.

Schema-4 may add a bounded `composition` object to a target layout when relative geometry needs to be explicit. Its shape is `{ "canvas": { "padding": number, "gap": number }, "regions": { "region-id": { "padding"?: number, "gap"?: number, "maxWidth"?: number, "actionsPlacement"?: "before" | "after" | "inline", "itemColumns"?: integer, "mediaAspectRatio"?: number } } }`. `canvas.padding` and `canvas.gap` are 0–128; region padding and gap are 0–128; `maxWidth` is 1–2400; `itemColumns` is 1–12; and `mediaAspectRatio` is 0.25–4. Unknown keys or region IDs fail validation. The template applies these values to the review canvas, region spacing and measure, action position, list columns and media placeholder ratio; they are not arbitrary CSS or product behavior.

Inline CSS and JavaScript implement the reviewer studio, page switching, working PRD actions, local overlays and feedback, viewport switching, state switching, copy inventory, reviewer-only inspector, and printing. They are not product implementation. Keep the canvas grayscale and structural: use typography, spacing, content silhouettes, and contrast only to make hierarchy legible. Add no brand palette, decorative imagery, generated media, final animation, production component library, polished marketing treatment, or formal design-system token decision. Shared prototype values and their Draft view are allowed.

## Composition Before Coverage

Use the W5 composition criteria in `ui-grading-rubric.md` while authoring, before Copy Freeze. Start with a frequent task and a dense or alternate-state case at wide and compact targets; inspect their hierarchy, spacing, content form, and reflow before expanding the full surface matrix. This is an authoring checkpoint, not another human approval. Do not alter the approved product scope or wording to make a composition easier.

The default canvas is a neutral grayscale interface. Keep region IDs, section labels, priority badges, review buttons, and flow notes behind the keyboard-accessible Annotations toggle. The shell keeps approval status, page/state/target controls, Copy inventory, and runtime QA available. Turning annotations on must preserve product content and flow destinations. Do not use inherited brand color, identical card wrappers, or fixed empty region heights as a substitute for hierarchy.

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

## Copy Freeze Gate

Run this gate after the first complete wireframe draft and before UI grading, final responsive review, or structural approval. The wireframe is the copy review surface: do not start visual design or frontend implementation while any product string or dynamic display contract remains unresolved.

1. Show the copy inventory to the human copy owner. Review every static string, action label, feedback message, alternate-state visible or assistive message, primary locale, and dynamic source/order/format/count/length/fallback contract.
2. Revise the schema-4 data until the copy owner accepts the complete set. Keep `approvalStatus: draft` while this copy work is still underway.
3. Record `copyFreeze.status: approved`, the human owner, primary BCP 47 locale, and approval date. Set every screen and copy item to `approved`.
4. Validate the copy-frozen but not yet structurally approved file from the repository root:

```text
python skills/ui-design-builder/scripts/check_wireframe_html.py --html <staged wireframes.html> --prd <approved PRD.md> --require-filled --require-copy-approved
python skills/ui-design-builder/scripts/check_ui_design_contract.py --repo-root <repository-root> --ui-design <staged ui-design.md> --prd <approved PRD.md> --wireframes <staged wireframes.html> --require-filled --require-wireframe-approved
```

A passing Copy Freeze Gate proves that the implementation-facing words and dynamic contracts are complete and approved; it does not approve layout or structure. Copy remains frozen through the subsequent browser matrix, grading, Wireframe Approval, UI Design Pass, and implementation. Any wording or display-contract change returns `copyFreeze.status`, affected screen `copyStatus`, and affected copy items to `draft`, then repeats this gate before structural approval can proceed.

## Wireframe Approval Gate

Only after the Copy Freeze Gate passes, run `references/ui-grading-rubric.md` against the frozen PRD, `ui-design.md`, and copy-frozen candidate HTML. When the host has the required multi-agent browser capability and dispatch is explicitly authorized, run one complete diagnostic wave: one lead grader by default, with at most two non-overlapping specialists only for an owner request or recorded high-impact risk. Reconcile every finding into one root-cause defect ledger before editing. The candidate then gets at most one repair batch and one re-review; a second failure stops at the rubric's owner-decision gate instead of opening another round. If the required grading capability or authorization is unavailable, the grading gate is blocked and the exact missing capability is recorded. Record the resulting `UI grading:` line in `ui-design.md`'s Wireframe Approval record. The grading stage supplements the runtime QA; it does not replace the browser check or the human decision. A hybrid `responsiveBySurface` package must not also declare global `viewports` or `sizeClasses`; each surface owns one complete responsive set.

Before presentation, re-run the core package checker and confirm the wireframe is still bound to the approved package revision. Present `wireframes.html` to the human product/design decision owner. Ask for one decision: approve the structure, or return named `UI-*` pages for revision.

Proactively send one user-visible response with verified absolute Markdown links to the complete interactive current `wireframes.html` and affected `ui-design.md` scope. Use the final logical paths in the authorized publication checkout for approval; after publication, link canonical files in the source checkout. Do not collect approval on `.ui-staging` paths. Say that every page and required state is included, name what the owner should review, and ask explicitly for Wireframe Approval. A browser or panel open is convenience only and cannot replace the response or links; if the file or preview cannot be verified or opened, report that blockage instead of approval readiness.

Before approval, open the file in a real browser and exercise the full `UI-* × responsive target × non-n/a state` matrix. For every combination, the visible runtime QA must pass, including its exact review-canvas width check; enlarge the browser when its reviewer shell cannot display the selected target at that width. No reviewer-shell or canvas element may be unintentionally overlapped, clipped, occluded, or force horizontal page scrolling, long content must stay readable, and controls must remain usable by the input modes named in `interaction`. A modal, dropdown, tooltip, sticky region, or other intended overlap passes only when the target's `interaction` rule names its stacking, focus, and dismissal behavior. Record the browser and result in `ui-design.md`. Missing browser capability blocks approval.

Approval confirms only:

- screen and route coverage;
- region order and information hierarchy;
- action placement and transitions;
- state and full responsive-matrix coverage with a passing browser layout check; and
- agreement with the approved UI Design Intake.

Wireframe Approval consumes the already approved Copy Freeze; it does not write, revise, or implicitly approve product wording. Approval does not prove usability and does not freeze a page theme or design tokens. Record the structural owner, decision, date, approved `UI-*` scope, frozen-copy identity, copy owner, primary locale, Copy Freeze date, and unresolved items in `ui-design.md`'s `## Wireframe Approval`. The HTML `approvalStatus` and `copyFreeze.status` use the same decision vocabulary as their matching records. `copyFreeze.status` must already be `approved` before `approvalStatus` can become `approved`.

After explicit structural approval, run the final combined check from the repository root:

```text
python skills/ui-design-builder/scripts/check_wireframe_html.py --html <staged wireframes.html> --prd <approved PRD.md> --require-filled --require-approved
python skills/ui-design-builder/scripts/check_ui_design_contract.py --repo-root <repository-root> --ui-design <staged ui-design.md> --prd <approved PRD.md> --wireframes <staged wireframes.html> --hifi <connected HiFi target> --require-filled --require-wireframe-approved --require-visual-approved [--design-system-markdown <staged pair markdown> --design-system-registry <staged pair JSON>]
```

A passing final check proves internal structure, self-containment, complete responsive data, approved Copy Freeze, structural approval, and PRD agreement. It does not prove rendered usability or visual quality.

An approved `wireframes.html`, together with the still-approved Product Definition package, completes the structural stage. Continue to motion routing and Style Integration only under the approved UI Design run; never jump directly to Design System Compiler or Harness.

## Enhancement Revisions

An enhancement run first classifies the delta's UI impact with the owner — `none`, `structure`, `style`, or `both`. Never assume `none` because the request reads backend- or data-side.

Apply `enhancement-recommendations.md`'s Incremental UI Scope before authoring. Append a new screen or patch named regions in the existing data; retain all other screen objects, copy, composition and flow bindings. Necessary entry links are a named change, not permission to redesign their entire page. Re-serializing the container HTML does not authorize new product content or geometry. Review the full package without re-authoring the preserved scope.

- `none`: preserve `wireframes.html` and any approved UI target verbatim.
- `structure` or `both`: update the affected `UI-*` entries in `PRD.md` first, then regenerate the affected pages in `wireframes.html`, then re-run the Wireframe Approval Gate on the changed scope and refresh `### Wireframe Approval`. A changed PRD UI contract with a stale wireframe artifact is not a complete package.
- `style` or `both`: re-run `references/ui-design-pass.md` for the affected scope. Reuse the recorded approved direction unless the accepted delta changes it; do not seek a fresh style selection merely because a page was added. Refresh affected target and source bindings, and renew applicable approval/evidence. A stale visual contract never publishes silently.

A user-visible wording change is a copy delta and uses `structure` (or `both` when style also changes) under the existing four-value UI-impact classifier. Update the affected PRD `` `copy` `` anchors and schema-4 items, return `copyFreeze.status` and the affected screen `copyStatus` to `draft`, inspect every impacted viewport and state for reflow, and renew both Copy Freeze and Wireframe Approval. A dynamic source/order/format/count/length/fallback change follows the same route even when its representative example stays unchanged.

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
- No design-reference styling, generated imagery, formal design-system token contract, or product implementation code appears. The prototype-only Draft view remains separate from final tokens.
- `check_wireframe_html.py` first passes with `--prd <staged PRD.md> --require-filled --require-copy-approved` while structural status remains draft, then passes with `--require-approved` after the browser matrix and Wireframe Approval.
- The PRD-bound diagnostic stage ran as one complete diagnostic wave with its scores, consolidated defect ledger, and bounded repair/re-review outcome recorded; an unavailable capability is a blocking outcome, not a skipped PASS.
- `ui-design.md` records the structural owner, approval status, date, approved `UI-*` scope, unresolved items, copy owner, primary locale, Copy Freeze approval date, and that Copy Freeze passed before UI grading, final layout review, structural approval, visual design, or implementation. Any later wording change is a product-definition copy delta requiring renewed approval.

If any check fails, keep the package staged and repair the PRD or HTML before approval.
