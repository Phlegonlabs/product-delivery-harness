# Wireframe Guide

Use this guide after the `PRD.md` UI Surface Contract is complete. `prd-builder` owns one low-fidelity deliverable for every UI-bearing product: `wireframes.html`.

## Ownership

- `PRD.md` owns product scope, routes, screen purpose, content responsibilities, actions, flows, states, responsive behavior, and `UI-*` / `UX-*` traces.
- `wireframes.html` is the interactive low-fidelity projection of that contract. It owns no new behavior and never changes product scope.
- When the HTML exposes a gap, update `PRD.md` first, then regenerate only the affected `UI-*` page.
- Later visual or implementation work consumes the approved HTML but does not edit it. Structural changes return to `prd-builder`.

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
python .agents/skills/prd-builder/scripts/check_wireframe_html.py --html <staged wireframes.html> --require-filled --require-approved
```

A passing check proves internal structure and self-containment, not usability or visual quality.

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

## Quality Check

- Every `UI-*` entry appears exactly once and every route remains owned by exactly one PRD surface.
- Region order and actions agree with `PRD.md`.
- Every `flows` entry starts from a known screen ID and matches a PRD flow; `traces` match the `UX-*` records in `PRD.md`.
- Every visible element has exact copy or a bounded display contract.
- Every required state is represented or explicitly `n/a` in the PRD.
- Compact rearrangement preserves all never-drop content and actions.
- The page switcher, overview, viewport control, state control, and visible section-purpose labels work from a local file.
- No high-fidelity styling, generated imagery, design-system token, or product implementation code appears.
- `check_wireframe_html.py` passes with `--require-filled --require-approved`.
- `PRD.md` records the human owner, approval status, date, approved `UI-*` scope, and unresolved items.

If any check fails, keep the package staged and repair the PRD or HTML before approval.
