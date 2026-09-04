# Wireframe Guide

Use this guide after the `PRD.md` UI Surface Contract is complete. `prd-builder` owns one low-fidelity deliverable for every UI-bearing product: `wireframes.html`.

## Ownership

- `PRD.md` owns product scope, routes, screen purpose, content responsibilities, actions, flows, states, responsive behavior, and `UI-*` / `UX-*` traces.
- `wireframes.html` is the interactive low-fidelity projection of that contract. It owns no new behavior and never changes product scope.
- A native mobile or desktop app is UI-bearing without a browser frontend and gets the same single `wireframes.html` deliverable: every `UI-*` screen in one file, with the product's own size classes standing in as the viewport toggle. The product ships no browser surface; the file exists purely as the review projection.
- When the HTML exposes a gap, update `PRD.md` first, then regenerate only the affected `UI-*` page.
- Later visual or implementation work consumes the approved HTML but does not edit it. Structural changes return to `prd-builder`.

## Reference Pass

Before drafting the HTML, look up how comparable products structure the same kind of screens. Do not invent screen composition from nothing when the industry has a settled pattern for the archetype.

- Run it inline as part of wireframe drafting; it needs no separate delegation. Skip it only when the user declined it, no web search or fetch tool is available, or the package is a trivial stub, and record which reason applied.
- Fetch the mainstream sites first: use the web fetch tool on two to four of the best-known live products in this product's category, and read how their relevant pages are actually composed — region order, navigation shape, and how each common flow (for example search and results, wizard, dashboard and detail, feed, checkout) is laid out. A fetched real page outranks any secondhand summary of it.
- Then pull composition references from a design gallery such as Dribbble for the main `UI-*` surfaces: search by surface type (landing page, dashboard, onboarding, settings) and read the shots for layout composition and region grouping only — color, typography, and imagery belong to the later visual phase, not the low-fidelity wireframe. A gallery shot ranks below a live mainstream product, because it shows an isolated screen without the flow between screens.
- Record every consulted source in `PRD.md`'s `### Wireframe Approval` as `Wireframe references consulted:` — one line per source with its URL, publisher, retrieval date, and the structural pattern adopted or rejected. A reference with no URL is recorded `UNVALIDATED`, the same rule as market research.
- References inform structure only. They never create scope, mint `UI-*` entries, or override the Builder UX Direction Decision. When a reference conflicts with `PRD.md`, `PRD.md` wins and the divergence is recorded as a revision note.

## HTML Requirements

Use `assets/templates/WIREFRAMES.template.html`. Generate one self-contained file containing every `UI-*` surface. It must open directly from disk without a server, build step, package install, network request, external font, or external asset.

The file must provide:

1. an all-pages overview plus a page switcher showing each `UI-*` ID, page name, route or surface, and primary goal;
2. an expanded/desktop and compact/mobile or alternate-size-class toggle;
3. a state selector for every required state represented by that screen;
4. visible section labels such as `Global Header`, `Hero Section`, `Feature Grid`, `Primary Workspace`, `Results Table`, or `CTA`, using product-fit labels rather than a fixed catalog;
5. each section's purpose, priority, elements, actions, and state treatment; and
6. a visible approval status.

Create one screen for every `UI-*` entry in `PRD.md`; do not create an untraced screen. Preserve exact copy when approved. Otherwise use a bounded display contract stating source, order, format, count, and length limits.

Use the template's embedded data block as the only product-specific input. Replace its example screens with the complete surface set and escape `<`, `>`, `&`, U+2028, and U+2029 inside JSON string values before embedding untrusted or user-supplied text. Render values through `textContent`, not `innerHTML`.

Project the PRD's flows and traces through the same block. `flows` lists each flow as `{from, trigger, to}`, where `from` is a screen ID and `to` is a screen ID or an external destination; the reviewer shell renders them per screen and on the overview. Per-screen or per-region `traces` list the `UX-*` IDs the surface traces to. An element is either exact approved copy as a string or a `{label, contract}` object whose contract states the bounded display contract's source, order, format, count, and length limits.

Inline CSS and JavaScript may implement the reviewer shell, page switching, viewport switching, state switching, annotations, and printing. They are not product implementation. Keep the canvas grayscale and low-fidelity: no brand palette, decorative imagery, production component library, animation concept, polished marketing treatment, or design-system token decision.

After filling and approving the HTML, validate it from the repository root:

```text
python .agents/skills/prd-builder/scripts/check_wireframe_html.py --html <staged wireframes.html> --prd <staged PRD.md> --require-filled --require-approved
```

A passing check proves internal structure, self-containment, and that the wireframe screens and the PRD `UI-*` surface contract name the same set — not usability or visual quality.

## Wireframe Approval Gate

Present `wireframes.html` to the human product/design decision owner. Ask for one decision: approve the structure, or return named `UI-*` pages for revision.

Approval confirms only:

- screen and route coverage;
- region order and information hierarchy;
- action placement and transitions;
- state and responsive coverage; and
- agreement with the Builder UX Direction Decision.

Approval does not prove usability and does not select a visual style. Record the owner, decision, date, approved `UI-*` scope, and unresolved items in `PRD.md`'s `### Wireframe Approval`. The HTML `approvalStatus` uses the same decision vocabulary as that record: `draft` before the gate, then `approved`, `revision_requested`, or `blocked` matching the owner's latest decision — never a different wording.

An approved `wireframes.html` completes the wireframe stage. Do not run Taste, high-fidelity preview generation, Product Design Builder, or Harness unless the owner separately asks to continue.

## Enhancement Revisions

An enhancement run first classifies the delta's UI impact with the owner — `none`, `structure`, `style`, or `both` — per `interview-guide.md`'s Enhancement Mode. Never assume `none` because the request reads backend- or data-side; most enhancements are design-side.

- `none`: preserve `wireframes.html` and any approved UI target verbatim.
- `structure` or `both`: update the affected `UI-*` entries in `PRD.md` first, then regenerate the affected pages in `wireframes.html`, then re-run the Wireframe Approval Gate on the changed scope and refresh `### Wireframe Approval`. A changed PRD UI contract with a stale wireframe artifact is not a complete package.
- `style` or `both`: ask the owner to either re-run `references/ui-design-pass.md` for the affected scope or explicitly confirm the existing direction still applies, and record that decision. When a `### UI Design Handoff` or a design-system pair exists, keeping them unchanged through a style-impacting enhancement requires the owner's explicit confirmation — a stale visual contract never publishes silently. A `required` design-system pair is recompiled or explicitly retired per `references/artifact-lifecycle.md`, never left stale by omission.

## Quality Check

- Every `UI-*` entry appears exactly once and every route remains owned by exactly one PRD surface.
- Region order and actions agree with `PRD.md`.
- Every `flows` entry starts from a known screen ID and matches a PRD flow; `traces` match the `UX-*` records in `PRD.md`.
- Every visible element has exact copy or a bounded display contract.
- Every required state is represented or explicitly `n/a` in the PRD.
- Compact rearrangement preserves all never-drop content and actions.
- The page switcher, overview, viewport control, state control, and visible section-purpose labels work from a local file.
- No high-fidelity styling, generated imagery, design-system token, or product implementation code appears.
- `check_wireframe_html.py` passes with `--prd <staged PRD.md> --require-filled --require-approved`.
- `PRD.md` records the human owner, approval status, date, approved `UI-*` scope, and unresolved items.

If any check fails, keep the package staged and repair the PRD or HTML before approval.
