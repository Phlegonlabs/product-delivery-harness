# Wireframe Guide

Use this guide after the `PRD.md` UI Surface Contract is complete. `product-definition-builder` owns one wireframe deliverable for every UI-bearing product: `wireframes.html`.

## Ownership

- `PRD.md` owns product scope, routes, screen purpose, content responsibilities, actions, flows, states, the platform-appropriate responsive set, per-target behavior, and `UI-*` / `UX-*` traces.
- `wireframes.html` is the interactive structural projection of that contract. It owns no new behavior and never changes product scope.
- A native mobile or desktop app is UI-bearing without a browser frontend and gets the same single `wireframes.html` deliverable: every `UI-*` screen in one file, with the product's own size classes standing in as the viewport toggle. The product ships no browser surface; the file exists purely as the review projection.
- When the HTML exposes a gap, update `PRD.md` first, then regenerate only the affected `UI-*` page.
- Later visual or implementation work consumes the approved HTML but does not edit it. Structural changes return to `product-definition-builder`.

## Reference Pass

Before drafting the HTML, look up how comparable products structure the same task, screen, and flow. The result is a small structural evidence set, not a mood board and not a list of fashionable products.

- Run it inline as part of wireframe drafting; it needs no separate delegation. Skip it only when the user declined it, no web search or fetch tool is available, or the package is a trivial stub, and record which reason applied.
- Inspect two to four useful sources in total. Start with first-party live products, official product documentation, or first-party case studies that expose the relevant task. Match a source to the exact screen or flow, not merely the same product category. A real reachable flow outranks a marketing screenshot or secondhand description.
- Inspect the source at the viewport and state needed to support the claim. A single desktop screenshot cannot establish mobile reflow, a still cannot establish interaction, and an isolated gallery image cannot establish a multi-screen flow. Mark those dimensions `not observable` instead of inferring them.
- Use a design gallery only as a supplemental composition source when first-party evidence does not show the needed structural alternative. Never let an isolated gallery image outrank a working product flow, and never carry its color, typography, imagery, or decorative styling into the structural wireframe.
- Record every source as a stable `WREF-*` entry under `Wireframe references consulted:` in `PRD.md`'s `### Wireframe Approval`. Each entry names the direct URL, publisher, retrieval date, exact screen or flow, inspected viewport and state, evidence status (`observed`, `partial`, or `blocked`), structural mechanic, `Adopt / Adapt / Avoid` decision, product-fit reason, and limitation. Preserve IDs across revisions and never reuse a retired ID.
- References inform structure only. They never create scope, mint `UI-*` entries, or override the Builder UX Direction Decision. When a reference conflicts with `PRD.md`, `PRD.md` wins and the divergence is recorded as a revision note.
- A reference with no inspectable URL or attachment is `UNVALIDATED`. A visual source proves no market claim, and a market source becomes structural evidence only after its relevant screen is separately inspected.

## HTML Requirements

Use `assets/templates/WIREFRAMES.template.html`. Generate one self-contained file containing every `UI-*` surface. It must open directly from disk without a server, build step, package install, network request, external font, or external asset. The checker decodes CSS escapes before evaluating `url()`, `image-set()`, and `@import`, so escaped remote schemes are rejected like literal ones.

New and structurally revised files use schema `wireframes/4`; the checker keeps `wireframes/2` and `wireframes/3` read compatibility for unchanged historical files. Schema 4 must provide:

1. an all-pages overview plus a page switcher showing each `UI-*` ID, page name, route or surface, and primary goal;
2. controls generated from exactly one set: at least three ascending positive numeric `viewports` for web, or at least two ordered string `sizeClasses` for native or desktop, plus one positive `canvasWidths` value per target for the review projection;
3. a state selector for every required state represented by that screen;
4. visible reviewer-only section labels such as `Global Header`, `Hero Section`, `Feature Grid`, `Primary Workspace`, `Results Table`, or `CTA`, using product-fit labels rather than a fixed catalog;
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

Project the PRD's flows and traces through the same block. `flows` lists each flow as `{from, trigger, to, presentation}` plus structured `feedback` copy when that presentation applies, where `from` is a screen ID, `trigger` exactly matches one visible action object's `label` on that screen, and `presentation` is `page`, `overlay`, or `feedback`. A `page` or `overlay` target is another `UI-*` screen in the same file; `feedback` may name a local result or external destination but never performs a network request. The reviewer shell renders region actions as working buttons: `page` switches screens, `overlay` opens an accessible local dialog for the target screen, and `feedback` shows its exact approved local message. Every visible region action maps to exactly one outgoing flow, and every outgoing flow maps back to one visible action. Per-screen or per-region `traces` list the `UX-*` IDs the surface traces to.

An optional `mediaIntent` object on a screen or a region records a motion or imagery treatment that is already decided before the design pass runs. It carries `treatment` — `motion-led`, `imagery-led`, or `motion + imagery`; a non-empty `draftPrompt` dedicated to that page or position; `source` naming the recorded Motion Need Gate decision that settled it; and `generationStatus: deferred`. Add one only where such a decision exists. A surface whose Motion Need Gate remains `blocked` stays unannotated and returns to the owner before visual approval. The reviewer shell renders the treatment, prompt, source, and deferred status as a visible note. The annotation is a later MCP-generation handoff only: the wireframe implements no final animation, and the UI Design Pass invokes no generation provider. Deterministic local UI motion required to demonstrate state feedback belongs to the later design-reference review, not this structural file.

Every PRD `UI-*` entry carries one invariant `` `responsive`: `` anchor whose kind and values match the HTML's global set exactly. Every screen carries a non-empty `neverDrop` list and a `responsiveLayouts` object keyed by every target. Each target entry declares `order`, `hidden`, `columns`, a `spans` value for every region, plus filled `reflow` and `interaction` rules. `order` contains every region exactly once. `hidden` may omit secondary material only; it cannot contain a never-drop region, and every primary region belongs to `neverDrop`. These fields make responsive behavior inspectable instead of treating a generic compact stack as proof.

Inline CSS and JavaScript implement the reviewer studio, page switching, working PRD actions, local overlays and feedback, viewport switching, state switching, copy inventory, reviewer-only inspector, and printing. They are not product implementation. Keep the canvas grayscale and structural: use typography, spacing, content silhouettes, and contrast only to make hierarchy legible. Add no brand palette, decorative imagery, generated media, final animation, production component library, polished marketing treatment, or design-system token decision.

## Copy Freeze Gate

Run this gate after the first complete wireframe draft and before UI grading, final responsive review, or structural approval. The wireframe is the copy review surface: do not start visual design or frontend implementation while any product string or dynamic display contract remains unresolved.

1. Show the copy inventory to the human copy owner. Review every static string, action label, feedback message, alternate-state visible or assistive message, primary locale, and dynamic source/order/format/count/length/fallback contract.
2. Revise the schema-4 data until the copy owner accepts the complete set. Keep `approvalStatus: draft` while this copy work is still underway.
3. Record `copyFreeze.status: approved`, the human owner, primary BCP 47 locale, and approval date. Set every screen and copy item to `approved`.
4. Validate the copy-frozen but not yet structurally approved file from the repository root:

```text
python skills/product-definition-builder/scripts/check_wireframe_html.py --html <staged wireframes.html> --prd <staged PRD.md> --require-filled --require-copy-approved
```

A passing Copy Freeze Gate proves that the implementation-facing words and dynamic contracts are complete and approved; it does not approve layout or structure. Copy remains frozen through the subsequent browser matrix, grading, Wireframe Approval, UI Design Pass, and implementation. Any wording or display-contract change returns `copyFreeze.status`, affected screen `copyStatus`, and affected copy items to `draft`, then repeats this gate before structural approval can proceed.

## Wireframe Approval Gate

Only after the Copy Freeze Gate passes, run `references/ui-grading-rubric.md` against the frozen PRD and copy-frozen candidate HTML. When the host has the required multi-agent browser capability and dispatch is explicitly authorized, run one complete diagnostic wave: one lead grader by default, with at most two non-overlapping specialists only for an owner request or recorded high-impact risk. Reconcile every finding into one root-cause defect ledger before editing. The candidate then gets at most one repair batch and one re-review; a second failure stops at the rubric's owner-decision gate instead of opening another round. When the capability is unavailable, record the rubric's exact capability-unavailable skip and continue. Record the resulting `UI grading:` line in `PRD.md`'s Wireframe Approval record. The grading stage supplements the runtime QA; it does not replace the browser check or the human decision.

Present `wireframes.html` to the human product/design decision owner. Ask for one decision: approve the structure, or return named `UI-*` pages for revision.

Before approval, open the file in a real browser and exercise the full `UI-* × responsive target × non-n/a state` matrix. For every combination, the visible runtime QA must pass, including its exact review-canvas width check; enlarge the browser when its reviewer shell cannot display the selected target at that width. No reviewer-shell or canvas element may be unintentionally overlapped, clipped, occluded, or force horizontal page scrolling, long content must stay readable, and controls must remain usable by the input modes named in `interaction`. A modal, dropdown, tooltip, sticky region, or other intended overlap passes only when the target's `interaction` rule names its stacking, focus, and dismissal behavior. Record the browser and result in `PRD.md`'s Wireframe Approval record. Missing browser capability blocks approval.

Approval confirms only:

- screen and route coverage;
- region order and information hierarchy;
- action placement and transitions;
- state and full responsive-matrix coverage with a passing browser layout check; and
- agreement with the Builder UX Direction Decision.

Wireframe Approval consumes the already approved Copy Freeze; it does not write, revise, or implicitly approve product wording. Approval does not prove usability and does not select a visual style. Record the structural owner, decision, date, approved `UI-*` scope, frozen-copy identity, and unresolved items in `PRD.md`'s `### Wireframe Approval`. The HTML `approvalStatus` and `copyFreeze.status` use the same decision vocabulary as their matching records. `copyFreeze.status` must already be `approved` before `approvalStatus` can become `approved`.

After structural approval, run the final combined check from the repository root:

```text
python skills/product-definition-builder/scripts/check_wireframe_html.py --html <staged wireframes.html> --prd <staged PRD.md> --require-filled --require-approved
```

A passing final check proves internal structure, self-containment, complete responsive data, approved Copy Freeze, structural approval, and PRD agreement. It does not prove rendered usability or visual quality.

An approved `wireframes.html` completes the wireframe stage. Do not run Taste, design-reference preview generation, Design System Compiler, or Harness unless the owner separately asks to continue.

## Enhancement Revisions

An enhancement run first classifies the delta's UI impact with the owner — `none`, `structure`, `style`, or `both` — per `interview-guide.md`'s Enhancement Mode. Never assume `none` because the request reads backend- or data-side; most enhancements are design-side.

- `none`: preserve `wireframes.html` and any approved UI target verbatim.
- `structure` or `both`: update the affected `UI-*` entries in `PRD.md` first, then regenerate the affected pages in `wireframes.html`, then re-run the Wireframe Approval Gate on the changed scope and refresh `### Wireframe Approval`. A changed PRD UI contract with a stale wireframe artifact is not a complete package.
- `style` or `both`: ask the owner to either re-run `references/ui-design-pass.md` for the affected scope or explicitly confirm the existing direction still applies, and record that decision. When a `### UI Design Handoff` or a design-system pair exists, keeping them unchanged through a style-impacting enhancement requires the owner's explicit confirmation — a stale visual contract never publishes silently. A `required` design-system pair is recompiled or explicitly retired per `references/artifact-lifecycle.md`, never left stale by omission.

A user-visible wording change is a copy delta and uses `structure` (or `both` when style also changes) under the existing four-value UI-impact classifier. Update the affected PRD `` `copy` `` anchors and schema-4 items, return `copyFreeze.status` and the affected screen `copyStatus` to `draft`, inspect every impacted viewport and state for reflow, and renew both Copy Freeze and Wireframe Approval. A dynamic source/order/format/count/length/fallback change follows the same route even when its representative example stays unchanged.

## Quality Check

- Every `UI-*` entry appears exactly once and every route remains owned by exactly one PRD surface.
- Region order and actions agree with `PRD.md`; every visible action works from the local file.
- Every `flows` entry starts from a known screen ID, names `page`, `overlay`, or `feedback`, and matches exactly one visible action plus one PRD flow; `page` and `overlay` target known screens, and `traces` match the `UX-*` records in `PRD.md`.
- Every static string, action label, feedback message, and alternate-state message is exact implementation-bound copy with status and source; every dynamic item has a realistic example and complete source/order/format/count/length/fallback contract.
- The canvas shows product copy while reviewer-only purpose, priority, traces, responsive rules, and source notes stay visually separate in the inspector.
- Every required state is represented or explicitly `n/a` in the PRD.
- Every responsive layout contains every region exactly once, hides no never-drop region, and preserves all never-drop content and actions.
- Every `mediaIntent` annotation names a valid treatment (`motion-led`, `imagery-led`, or `motion + imagery`), a non-empty dedicated `draftPrompt`, its recorded Motion Need Gate decision `source`, and `generationStatus: deferred`.
- Every page-target-state combination renders without unintended overlap, clipping, occlusion, or horizontal overflow; intended overlays have documented stacking, focus, and dismissal behavior.
- The page switcher, overview, responsive-target control, state control, copy inventory, reviewer-only inspector, runtime layout QA, and visible section labels work from a local file.
- No design-reference styling, generated imagery, design-system token, or product implementation code appears.
- `check_wireframe_html.py` first passes with `--prd <staged PRD.md> --require-filled --require-copy-approved` while structural status remains draft, then passes with `--require-approved` after the browser matrix and Wireframe Approval.
- The PRD-bound diagnostic stage ran as one complete diagnostic wave with its scores, consolidated defect ledger, and bounded repair/re-review outcome recorded, or the host capability was unavailable and the exact skip was recorded; a parent-only review is never labeled as multi-agent grading.
- `PRD.md` records the human owner, approval status, date, approved `UI-*` scope, and unresolved items.
- `PRD.md` records the copy owner, primary locale, Copy Freeze approval date, and that this gate passed before UI grading, final layout review, structural approval, visual design, or implementation. Any later wording change is a copy delta requiring renewed approval.

If any check fails, keep the package staged and repair the PRD or HTML before approval.
