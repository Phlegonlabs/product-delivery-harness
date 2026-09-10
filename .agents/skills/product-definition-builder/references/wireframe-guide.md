# Wireframe Guide

Use this guide after the `PRD.md` UI Surface Contract is complete. `product-definition-builder` owns one low-fidelity deliverable for every UI-bearing product: `wireframes.html`.

## Ownership

- `PRD.md` owns product scope, routes, screen purpose, content responsibilities, actions, flows, states, the platform-appropriate responsive set, per-target behavior, and `UI-*` / `UX-*` traces.
- `wireframes.html` is the interactive low-fidelity projection of that contract. It owns no new behavior and never changes product scope.
- A native mobile or desktop app is UI-bearing without a browser frontend and gets the same single `wireframes.html` deliverable: every `UI-*` screen in one file, with the product's own size classes standing in as the viewport toggle. The product ships no browser surface; the file exists purely as the review projection.
- When the HTML exposes a gap, update `PRD.md` first, then regenerate only the affected `UI-*` page.
- Later visual or implementation work consumes the approved HTML but does not edit it. Structural changes return to `product-definition-builder`.

## Reference Pass

Before drafting the HTML, look up how comparable products structure the same kind of screens. Do not invent screen composition from nothing when the industry has a settled pattern for the archetype.

- Run it inline as part of wireframe drafting; it needs no separate delegation. Skip it only when the user declined it, no web search or fetch tool is available, or the package is a trivial stub, and record which reason applied.
- Fetch the mainstream sites first: use the web fetch tool on two to four of the best-known live products in this product's category, and read how their relevant pages are actually composed — region order, navigation shape, and how each common flow (for example search and results, wizard, dashboard and detail, feed, checkout) is laid out. A fetched real page outranks any secondhand summary of it.
- Then pull composition references from a design gallery such as Dribbble for the main `UI-*` surfaces: search by surface type (landing page, dashboard, onboarding, settings) and read the shots for layout composition and region grouping only — color, typography, and imagery belong to the later visual phase, not the low-fidelity wireframe. A gallery shot ranks below a live mainstream product, because it shows an isolated screen without the flow between screens.
- Record every consulted source in `PRD.md`'s `### Wireframe Approval` as `Wireframe references consulted:` — one line per source with its URL, publisher, retrieval date, and the structural pattern adopted or rejected. A reference with no URL is recorded `UNVALIDATED`, the same rule as market research.
- References inform structure only. They never create scope, mint `UI-*` entries, or override the Builder UX Direction Decision. When a reference conflicts with `PRD.md`, `PRD.md` wins and the divergence is recorded as a revision note.

## HTML Requirements

Use `assets/templates/WIREFRAMES.template.html`. Generate one self-contained file containing every `UI-*` surface. It must open directly from disk without a server, build step, package install, network request, external font, or external asset. The checker decodes CSS escapes before evaluating `url()`, `image-set()`, and `@import`, so escaped remote schemes are rejected like literal ones.

New and structurally revised files use schema `wireframes/3`; the checker keeps `wireframes/2` read compatibility for unchanged historical files. Schema 3 must provide:

1. an all-pages overview plus a page switcher showing each `UI-*` ID, page name, route or surface, and primary goal;
2. controls generated from exactly one set with at least two targets: ascending positive numeric `viewports` for web, or ordered string `sizeClasses` for native or desktop, plus one positive `canvasWidths` value per target for the review projection;
3. a state selector for every required state represented by that screen;
4. visible section labels such as `Global Header`, `Hero Section`, `Feature Grid`, `Primary Workspace`, `Results Table`, or `CTA`, using product-fit labels rather than a fixed catalog;
5. each section's purpose, priority, elements, working actions, and state treatment;
6. a visible approval status; and
7. visible runtime layout QA for the selected page, responsive target, and state.

Create one screen for every `UI-*` entry in `PRD.md`; do not create an untraced screen. Preserve exact copy when approved. Otherwise use a bounded display contract stating source, order, format, count, and length limits.

Use the template's embedded data block as the only product-specific input. Replace its example screens with the complete surface set and escape `<`, `>`, `&`, U+2028, and U+2029 inside JSON string values before embedding untrusted or user-supplied text. Render values through `textContent`, not `innerHTML`.

Project the PRD's flows and traces through the same block. `flows` lists each flow as `{from, trigger, to, presentation}`, where `from` is a screen ID, `trigger` exactly matches one visible region action on that screen, and `presentation` is `page`, `overlay`, or `feedback`. A `page` or `overlay` target is another `UI-*` screen in the same file; `feedback` may name a local result or external destination but never performs a network request. The reviewer shell renders region actions as working buttons: `page` switches screens, `overlay` opens an accessible local dialog for the target screen, and `feedback` shows local inline feedback. Every visible region action maps to exactly one outgoing flow, and every outgoing flow maps back to one visible action. Per-screen or per-region `traces` list the `UX-*` IDs the surface traces to. An element is either exact approved copy as a string or a `{label, contract}` object whose contract states the bounded display contract's source, order, format, count, and length limits.

An optional `mediaIntent` object on a screen or a region records a motion or imagery treatment that is already decided before the design pass runs. It carries `treatment` — `motion-led`, `imagery-led`, or `motion + imagery`; a non-empty `draftPrompt` dedicated to that page or position; `source` naming the recorded Motion Need Gate decision that settled it; and `generationStatus: deferred`. Add one only where such a decision exists. A surface whose Motion Need Gate remains `blocked` stays unannotated and returns to the owner before visual approval. The reviewer shell renders the treatment, prompt, source, and deferred status as a visible note. The annotation is a later MCP-generation handoff only: the wireframe implements no final animation, and the UI Design Pass invokes no generation provider. Deterministic local UI motion required to demonstrate state feedback belongs to the later high-fidelity review, not this low-fidelity file.

Every PRD `UI-*` entry carries one invariant `` `responsive`: `` anchor whose kind and values match the HTML's global set exactly. Every screen carries a non-empty `neverDrop` list and a `responsiveLayouts` object keyed by every target. Each target entry declares `order`, `hidden`, `columns`, a `spans` value for every region, plus filled `reflow` and `interaction` rules. `order` contains every region exactly once. `hidden` may omit secondary material only; it cannot contain a never-drop region, and every primary region belongs to `neverDrop`. These fields make responsive behavior inspectable instead of treating a generic compact stack as proof.

Inline CSS and JavaScript implement the reviewer shell, page switching, working PRD actions, local overlays and feedback, viewport switching, state switching, annotations, and printing. They are not product implementation. Keep the canvas grayscale and low-fidelity: no brand palette, decorative imagery, generated media, final animation, production component library, polished marketing treatment, or design-system token decision.

After filling and approving the HTML, validate it from the repository root:

```text
python .agents/skills/product-definition-builder/scripts/check_wireframe_html.py --html <staged wireframes.html> --prd <staged PRD.md> --require-filled --require-approved
```

A passing static check proves internal structure, self-containment, complete responsive data, and that the wireframe screens and the PRD `UI-*` surface contract name the same IDs, routes, states, and responsive set. It does not prove rendered usability or visual quality.

## Wireframe Approval Gate

After the first draft and before presenting `wireframes.html` to the human product/design decision owner, run `references/ui-grading-rubric.md` against the frozen PRD and candidate HTML. When the host has the required multi-agent browser capability and dispatch is explicitly authorized, run one complete diagnostic wave: one lead grader by default, with at most two non-overlapping specialists only for an owner request or recorded high-impact risk. Reconcile every finding into one root-cause defect ledger before editing. The candidate then gets at most one repair batch and one re-review; a second failure stops at the rubric's owner-decision gate instead of opening another round. When the capability is unavailable, record the rubric's exact capability-unavailable skip and continue. Record the resulting `UI grading:` line in `PRD.md`'s Wireframe Approval record. The grading stage supplements the runtime QA; it does not replace the browser check or the human decision.

Present `wireframes.html` to the human product/design decision owner. Ask for one decision: approve the structure, or return named `UI-*` pages for revision.

Before approval, open the file in a real browser and exercise the full `UI-* × responsive target × non-n/a state` matrix. For every combination, the visible runtime QA must pass, including its exact review-canvas width check; enlarge the browser when its reviewer shell cannot display the selected target at that width. No reviewer-shell or canvas element may be unintentionally overlapped, clipped, occluded, or force horizontal page scrolling, long content must stay readable, and controls must remain usable by the input modes named in `interaction`. A modal, dropdown, tooltip, sticky region, or other intended overlap passes only when the target's `interaction` rule names its stacking, focus, and dismissal behavior. Record the browser and result in `PRD.md`'s Wireframe Approval record. Missing browser capability blocks approval.

Approval confirms only:

- screen and route coverage;
- region order and information hierarchy;
- action placement and transitions;
- state and full responsive-matrix coverage with a passing browser layout check; and
- agreement with the Builder UX Direction Decision.

Approval does not prove usability and does not select a visual style. Record the owner, decision, date, approved `UI-*` scope, and unresolved items in `PRD.md`'s `### Wireframe Approval`. The HTML `approvalStatus` uses the same decision vocabulary as that record: `draft` before the gate, then `approved`, `revision_requested`, or `blocked` matching the owner's latest decision — never a different wording.

An approved `wireframes.html` completes the wireframe stage. Do not run Taste, high-fidelity preview generation, Design System Compiler, or Harness unless the owner separately asks to continue.

## Enhancement Revisions

An enhancement run first classifies the delta's UI impact with the owner — `none`, `structure`, `style`, or `both` — per `interview-guide.md`'s Enhancement Mode. Never assume `none` because the request reads backend- or data-side; most enhancements are design-side.

- `none`: preserve `wireframes.html` and any approved UI target verbatim.
- `structure` or `both`: update the affected `UI-*` entries in `PRD.md` first, then regenerate the affected pages in `wireframes.html`, then re-run the Wireframe Approval Gate on the changed scope and refresh `### Wireframe Approval`. A changed PRD UI contract with a stale wireframe artifact is not a complete package.
- `style` or `both`: ask the owner to either re-run `references/ui-design-pass.md` for the affected scope or explicitly confirm the existing direction still applies, and record that decision. When a `### UI Design Handoff` or a design-system pair exists, keeping them unchanged through a style-impacting enhancement requires the owner's explicit confirmation — a stale visual contract never publishes silently. A `required` design-system pair is recompiled or explicitly retired per `references/artifact-lifecycle.md`, never left stale by omission.

## Quality Check

- Every `UI-*` entry appears exactly once and every route remains owned by exactly one PRD surface.
- Region order and actions agree with `PRD.md`; every visible action works from the local file.
- Every `flows` entry starts from a known screen ID, names `page`, `overlay`, or `feedback`, and matches exactly one visible action plus one PRD flow; `page` and `overlay` target known screens, and `traces` match the `UX-*` records in `PRD.md`.
- Every visible element has exact copy or a bounded display contract.
- Every required state is represented or explicitly `n/a` in the PRD.
- Every responsive layout contains every region exactly once, hides no never-drop region, and preserves all never-drop content and actions.
- Every `mediaIntent` annotation names a valid treatment (`motion-led`, `imagery-led`, or `motion + imagery`), a non-empty dedicated `draftPrompt`, its recorded Motion Need Gate decision `source`, and `generationStatus: deferred`.
- Every page-target-state combination renders without unintended overlap, clipping, occlusion, or horizontal overflow; intended overlays have documented stacking, focus, and dismissal behavior.
- The page switcher, overview, responsive-target control, state control, runtime layout QA, and visible section-purpose labels work from a local file.
- No high-fidelity styling, generated imagery, design-system token, or product implementation code appears.
- `check_wireframe_html.py` passes with `--prd <staged PRD.md> --require-filled --require-approved`.
- The PRD-bound diagnostic stage ran as one complete diagnostic wave with its scores, consolidated defect ledger, and bounded repair/re-review outcome recorded, or the host capability was unavailable and the exact skip was recorded; a parent-only review is never labeled as multi-agent grading.
- `PRD.md` records the human owner, approval status, date, approved `UI-*` scope, and unresolved items.

If any check fails, keep the package staged and repair the PRD or HTML before approval.
