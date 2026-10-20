# Design System Compilation

## Path Interpretation

Outside a real Markdown link, `references/...`, `assets/...`, `scripts/...`, and sibling skill paths such as `../delivery-harness/...` are logical paths from `<design-system-compiler-skill-root>`, not from this stage file. Actual Markdown links resolve relative to this stage file.

## Compilation Skills Gate

Before creating or revising a formal pair:

1. Confirm that the installed skill with exact frontmatter name `frontend-design` is available.
2. Use `frontend-design` only for approved visual-direction and frontend-authoring judgment. Design System Compiler performs the compilation itself into a coherent token, primitive, component, motion, responsive, and state system; it does not ask `frontend-design` to compile or conform the pair.
3. If `frontend-design` cannot be loaded, stop. Do not draft, revise, or validate the pair through a fallback path.

For a Harness design-source mission, `required_skills` must contain `design-system-compiler` and `frontend-design`. `design-system-compiler` owns contract compilation; Harness implementation owns later conformance to those frozen sources.

Do not run Impeccable or another design pass merely to compile the pair. Their approved consequences are already frozen in `ui-design.md`. A request to reopen layout, style, motion, media, or visual direction returns to `ui-design-builder`; a product or stack change returns to `product-definition-builder`.

## Inputs And Ownership

Read the current sources in full before drafting:

- `PRD.md`, including Product Definition Approval and its UI Surface Contract;
- `docs/design/ui-design.md`, including UI Design Intake, Motion and Media Intent, Style Integration, Impeccable HiFi review, H1-H9 grading, Visual Approval, and `Design System Need Gate: required`;
- the approved complete `ui-hifi/2` package, including the entry, closed child-page manifest, matching `UI-*` surfaces, complete viewport or size-class set, states, product controls, reviewer shell, and inline assets;
- a legacy `wireframes.html` only when the named unmarked legacy UI package retains it under its original approval semantics;
- `architecture.md` and `stack-decisions.md`, including the approved Stack Decision Checkpoint and its platform, rendering, component-foundation, styling, accessibility, and performance constraints;
- existing `design-system.md` and `design-system.json` for an enhancement or delta; and
- the immutable approved UI target and any confirmed `REF-*` / `RP-*` evidence named by `ui-design.md`.

Read `market-research.md` only when `ui-design.md` cites its `MR-*` evidence. Repository-discovered images remain non-canonical design inspiration unless the UI design contract promotes one to a scoped page-faithful target with its hash, route, state, responsive scope, and tolerance.

If a required source is named but missing or unreadable, stop and request its path or contents. A statement that an approved source exists is not a substitute for reading it.

If an existing pair or staged revision describes the same product, enhance it. Preserve unaffected content and stable `UI-*`, `UX-*`, `DS-*`, and `DS-COMP-*` IDs. Never regenerate the pair from a blank slate.

Apply [Incremental UI Scope](../../../ui-design-builder/references/enhancement-recommendations.md#incremental-ui-scope). Reuse existing tokens and components for an added page. Change the pair only for approved additions or changed reusable contracts, preserving unrelated entries; refresh source bindings without treating a new hash as a new visual direction. A shared entry change names every affected consumer and its regression checks. Record the delta and small repairs in the existing Epic or direct task.

The optional reference catalog is downstream consumption only. If relevant to an already adopted CSS, component, icon, or motion choice, use [Reference Selection](../../../delivery-harness/references/reference-selection.md) and only the relevant material under [Option Library](../../../delivery-harness/references/option-library/) to understand that decision; never reselect a stack or direction here. A candidate that needs a new choice is an upstream finding.

Product scope, route, content, action, flow, state, responsive, architecture, or stack gaps return to `product-definition-builder`. Style, motion/media, approved-target, or HiFi-package gaps return to `ui-design-builder`. A treatment that needs one of those changes is a finding, not permission to edit the source.

## Workflow

1. From the repository root, run the current-package preflight with the package's own marker (`ui-design/3` or `ui-design/2`): `python "<product-definition-builder-skill-root>/scripts/check_product_package.py" --prd <approved PRD.md> --architecture <approved architecture.md> --stack-decisions <approved stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved --ui-contract <ui-design/3|ui-design/2>`. Stop on a missing or stale Product Definition/Stack approval or on missing PRD copy, operations, states, or responsive inputs.
2. Confirm that `ui-design.md` says `Design System Need Gate: required`; otherwise stop. A greenfield UI may carry the exact pending marker `Compiled design system pair: pending — design-system-compiler` during this preflight only.
3. Pass the Compilation Skills Gate.
4. The UI builder's pair-less preflight has no separate command; it runs inside `check_design_system_pair.py --repo-root`. That check validates the `ui-design.md` named by `sourceBindings.uiDesign` against the PRD UI Surface Contract, complete approved `ui-hifi/2` package, component foundation, styling approach, and approved Stack rows, and accepts the pending pair marker only there. `design-system/4` requires the `ui-design/3` marker and `design-system/3` the `ui-design/2` marker; both reject a missing, unknown, duplicate or mismatched marker and every wireframe binding. Draft the source bindings first, run the pair checker, and fix every `ui-design:` finding upstream before completing compilation. A visual direction that needs another stack returns upstream.
5. Read [Design System Guide](../design-system-guide.md) and compile only approved visual consequences with `frontend-design`. Register motion variants only for approved `functional_only` or `expressive` intents that use deterministic UI motion; `not_required` gets no decorative variant, and a blocked intent returns upstream. Generated provider assets remain media sources rather than motion variants. Every variant records reduced-motion behavior.
6. Build a `design-system/4` pair for `ui-design/3` (`design-system/3` for `ui-design/2`) whose JSON `sourceBindings` names exactly the current PRD, architecture, stack, `ui-design.md`, and approved HiFi entry with their current SHA-256 values. It has no wireframe binding. Bind rendering model, platform, component foundation, and styling per homogeneous or hybrid surface from the approved Stack rows; do not leave executable platform fields ungrounded.
7. For `design-system/4`, register the `showcase` in [Output Contract](../output-contract.md): one specimen per primitive variant value, product-component state and motion variant, each bound to an approved HiFi product element by page, simple selector, `data-specimen-variant` and `data-specimen-state`. Never add a style, sample or selector the approved HiFi lacks; a missing element returns to `ui-design-builder` for the same frontend author and renewed approval.
   Reuse the UI preflight's advisory source limitations as context. They do not replace registry coverage or trigger-specific provenance checks.
   For approved motion that a product script or product state drives, use `ds-showcase/2` with a `source-runtime` row bound to its approved intent, evidence, script hash, surface, state and target. Never relabel it as a CSS trigger or invent a substitute animation. Missing intents, evidence or specimen annotations return to `ui-design-builder`.
8. Run the validation commands and final checklist, then stage and publish the files together through the existing artifact lifecycle. Generate and check `docs/design/design-system-preview.html` with `scripts/render_design_system_preview.py` as described in [Output Contract](../output-contract.md). This derived view adds no approval gate or new authority; it never rewrites an approved HiFi package or a historical wireframe.

## Validation

Run these from the repository root:

```text
python "<design-system-compiler-skill-root>/scripts/check_design_system_pair.py" --markdown <staged design-system.md> --registry <staged design-system.json> --repo-root <repository-root> --write
python "<design-system-compiler-skill-root>/scripts/check_design_system_pair.py" --markdown <staged design-system.md> --registry <staged design-system.json> --repo-root <repository-root> --require-filled
python "<design-system-compiler-skill-root>/scripts/check_color_contrast.py" --pair <foreground-hex>,<background-hex>[,normal|large|ui] (one --pair per registry color pairing)
python "<design-system-compiler-skill-root>/scripts/check_type_scale.py" --step <role>,<font-size>,<line-height>[,text|heading] (one --step per registry type role) [--root-font-size <px>]
python "<product-definition-builder-skill-root>/scripts/check_product_package.py" --prd <PRD.md> --architecture <architecture.md> --stack-decisions <stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved
```

Also confirm:

- `ui-design.md` records the Design System Need Gate as `required` with its owner and exact decision date; the pair remains absent until the Product Definition is published and all UI inputs and this compiled pair stage together;
- `design-system.json` is `design-system/4` for `ui-design/3` or `design-system/3` for `ui-design/2`, has exactly PRD, architecture, stack, UI design, and HiFi source bindings, and binds every listed source to its current bytes; legacy `design-system/1` is inspection-only; `design-system/2` retains its original checks for pinned legacy packages;
- for `design-system/4`, every showcase specimen resolves to the hash-checked HiFi package and the checker reports no coverage gap;
- for `ds-showcase/2` source-runtime rows, `scripts/verify_runtime_motion.py` passes on the exact generated preview and writes a new receipt; the preview stays an unverified candidate until then;
- Product Definition Approval and the Stack Decision Checkpoint are approved, with no `Recommended` or `Provisional` executable layer;
- every PRD UI surface has an addressable route or an explicit `n/a` reason;
- every UI surface maps to the complete approved `ui-hifi/2` package with matching route, states, responsive set, product controls, interaction endpoints, and reviewer shell;
- the approved UI target, Style Integration record, Impeccable critique/audit, H1-H9 scores, visual approval, scope, hash, exact responsive coverage, passing browser-matrix evidence, and tolerance are present in `ui-design.md`;
- every surface covers the final state matrix or records `<state>: n/a - <reason>` in `PRD.md`;
- every required UI element maps to a registered primitive or product component;
- every Motion and Media Intent row is resolved; approved deterministic motion maps to a registered variant plus reduced-motion behavior, while `not_required` introduces no decorative variant; generated Higgsfield or other provider assets remain media sources, not UI-state implementations;
- a homogeneous product has exactly one global responsive set (at least three ascending web `viewports` or at least two native/desktop `sizeClasses`); a hybrid uses each `surfaceContracts` entry’s exact responsive and release/capture set with no global platform, styling mechanism, viewports, or size classes; all sets match the PRD, approved HiFi scope, and stack;
- no unresolved placeholder, page-local value, or one-off control remains; and
- `design-system.md` and `design-system.json` publish together and agree through the pair checker.

## Reference Routing

- Read `references/design-system-guide.md` for normal contract compilation.
- Read `references/output-contract.md` for artifact boundaries and quality checks.
- Read `references/artifact-lifecycle.md` before creating staging files or publishing.
- Use `assets/templates/DESIGN_SYSTEM.template.md` and `assets/templates/DESIGN_SYSTEM.template.json` for the pair; for `design-system/4`, set that schema and add the block from `assets/templates/DESIGN_SYSTEM_SHOWCASE.template.json`.
- Use the three scripts under `scripts/` for deterministic pair, contrast, and type-scale validation.
- Use `scripts/render_design_system_preview.py` to emit a derived HTML view or check its exact bytes against the current validated pair and sources.
- When the owner asks to reopen direction, stop compilation and invoke `../ui-design-builder/SKILL.md`. Resume only after its updated `ui-design.md`, complete HiFi package when affected, Impeccable review, grading, and human Visual Approval pass.

## Output Rules

- Default artifacts to English unless the user requests another language.
- Keep the design system implementation-facing.
- Keep candidate directions, reference analysis, and preview artifacts outside the published pair.
- Keep stable trace IDs across revisions; do not reuse retired IDs for different meanings.
- UI owner approval proves direction conformance, not representative-user usability. Record unresolved validation needs.
- Report exact staged and published paths, validation results, assumptions, and every intentionally unresolved gap.
