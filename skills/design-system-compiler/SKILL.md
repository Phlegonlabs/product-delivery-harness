---
name: design-system-compiler
description: Compile an owner-approved UI design into the frozen `docs/design/design-system.md` and `docs/design/design-system.json` pair. Use only after Product Definition, Stack Decision, Wireframe, Style Integration, Impeccable HiFi review, PRD-bound scoring, and Visual Approval have passed and ui-design.md records Design System Need Gate: required. It freezes tokens, primitives, product components, motion variants, responsive rules, and states; it does not choose product, stack, layout, or visual direction.
---

`sourceBindings.uiDesign.sha256` uses the canonical UI approval digest, not the raw file hash. Run `python "<ui-design-builder-skill-root>/scripts/ui_approval_digest.py" <ui-design.md>`; it excludes active derived pair/replacement linkage lines so linking the compiled pair does not invalidate its own input. All other source bindings use raw-file SHA-256.

# Design System Compiler

## Installed Commands

Resolve `<design-system-compiler-skill-root>` to the absolute directory containing this installed SKILL.md. Resolve sibling skill roots from the same installation (normally `~/.agents/skills/`). Quote script paths, keep the working directory and `--repo-root` at the target project, and never assume that project contains `skills/`. In references, `skills/<name>/scripts/`, `<name>/scripts/`, and bare `scripts/` are logical installed-skill paths: expand them to the observed absolute skill root before execution. Repository maintenance and CI commands still run from this source repository.

## Purpose

Turn an approved UI direction into two binding reusable UI sources:

- `design-system.md` for the selected visual direction and short human-facing rules; and
- `design-system.json` for machine-readable tokens, primitives, closed variants, product components, motion, responsive rules, source paths, and the state matrix.

This skill is optional. Invoke it only when Product Definition Approval and the Stack Decision Checkpoint are approved and `docs/design/ui-design.md` records approved Wireframe and Visual decisions plus `Design System Need Gate: required`. The compiler respects the approved component foundation and styling approach; it never changes stack by implication. `PRD.md` owns product behavior, while `ui-design-builder` owns `ui-design.md`, the approved wireframe, and the HiFi target. Do not duplicate or change those contracts, implement production UI, or create Harness PLAN/RUN state.

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
- `docs/design/ui-design.md`, including UI Design Intake, Motion and Media Intent, Wireframe Approval, Style Integration, Impeccable HiFi review, H1-H9 grading, Visual Approval, and `Design System Need Gate: required`;
- approved `wireframes.html`, including its matching `UI-*` page, complete viewport or size-class set, state, region, per-target layout, and passing browser overlap/overflow review;
- `architecture.md` and `stack-decisions.md`, including the approved Stack Decision Checkpoint and its platform, rendering, component-foundation, styling, accessibility, and performance constraints;
- existing `design-system.md` and `design-system.json` for an enhancement or delta; and
- the immutable approved UI target and any confirmed `REF-*` / `RP-*` evidence named by `ui-design.md`.

Read `market-research.md` only when `ui-design.md` cites its `MR-*` evidence. Repository-discovered images remain non-canonical design inspiration unless the UI design contract promotes one to a scoped page-faithful target with its hash, route, state, responsive scope, and tolerance.

If a required source is named but missing or unreadable, stop and request its path or contents. A statement that an approved source exists is not a substitute for reading it.

If an existing pair or staged revision describes the same product, enhance it. Preserve unaffected content and stable `UI-*`, `UX-*`, `DS-*`, and `DS-COMP-*` IDs. Never regenerate the pair from a blank slate.

Product scope, route, content, action, flow, state, responsive, architecture, or stack gaps return to `product-definition-builder`. Wireframe, style, motion/media, or approved-target gaps return to `ui-design-builder`. A treatment that needs one of those changes is a finding, not permission to edit the source.

## Workflow

1. From the repository root, run `python "<product-definition-builder-skill-root>/scripts/check_product_package.py" --prd <approved PRD.md> --architecture <approved architecture.md> --stack-decisions <approved stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved`. Stop on a missing or stale Product Definition/Stack approval.
2. Confirm that `ui-design.md` says `Design System Need Gate: required`; otherwise stop. A greenfield UI may carry the exact pending marker `Compiled design system pair: pending — design-system-compiler` during this preflight only.
3. Pass the Compilation Skills Gate.
4. Run the UI builder's exact pair-less preflight against the PRD UI Surface Contract, `ui-design.md`, approved wireframes/4 with approved Copy Freeze, HiFi target, component foundation, styling approach, and approved Stack rows. Then verify the normal pair checker after compilation. A visual direction that needs another stack returns upstream.
5. Read `references/design-system-guide.md` and compile only approved visual consequences with `frontend-design`. Register motion variants only for approved `functional_only` or `expressive` intents that use deterministic UI motion; `not_required` gets no decorative variant, and a blocked intent returns upstream. Generated provider assets remain media sources rather than motion variants. Every variant records reduced-motion behavior.
6. Build a `design-system/2` pair whose JSON `sourceBindings` names the current PRD, architecture, stack, `ui-design.md`, approved wireframes/4, and approved HiFi target with their current SHA-256 values. Bind rendering model, platform, component foundation, and styling per homogeneous or hybrid surface from the approved Stack rows; do not leave executable platform fields ungrounded.
7. Run the validation commands and final checklist, then stage and publish both files together through the existing artifact lifecycle.

## Validation

Run these from the repository root:

```text
python "<design-system-compiler-skill-root>/scripts/check_design_system_pair.py" --markdown <staged design-system.md> --registry <staged design-system.json> --repo-root <repository-root> --write
python "<design-system-compiler-skill-root>/scripts/check_design_system_pair.py" --markdown <staged design-system.md> --registry <staged design-system.json> --repo-root <repository-root> --require-filled
python "<design-system-compiler-skill-root>/scripts/check_color_contrast.py" <the arguments required by the staged design system>
python "<design-system-compiler-skill-root>/scripts/check_type_scale.py" <the arguments required by the staged design system>
python "<product-definition-builder-skill-root>/scripts/check_product_package.py" --prd <PRD.md> --architecture <architecture.md> --stack-decisions <stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved
```

Also confirm:

- `ui-design.md` records the Design System Need Gate as `required` with its owner and exact decision date; the pair remains absent until the Product Definition is published and all UI inputs and this compiled pair stage together;
- `design-system.json` is `design-system/2` and binds every listed source to its current bytes; a legacy `design-system/1` pair is inspection-only and cannot authorize a new approval;
- Product Definition Approval and the Stack Decision Checkpoint are approved, with no `Recommended` or `Provisional` executable layer;
- every PRD UI surface has an addressable route or an explicit `n/a` reason;
- every UI surface maps to an approved `wireframes.html` page with matching regions, states, responsive set, and per-target order, visibility, spans, reflow, and interaction rules;
- the approved UI target, Style Integration record, Impeccable critique/audit, H1-H9 scores, visual approval, scope, hash, exact responsive coverage, passing browser-matrix evidence, and tolerance are present in `ui-design.md`;
- every surface covers the final state matrix or records `<state>: n/a - <reason>` in `PRD.md`;
- every required UI element maps to a registered primitive or product component;
- every Motion and Media Intent row is resolved; approved deterministic motion maps to a registered variant plus reduced-motion behavior, while `not_required` introduces no decorative variant; generated Higgsfield or other provider assets remain media sources, not UI-state implementations;
- a homogeneous product has exactly one global responsive set (at least three ascending web `viewports` or at least two native/desktop `sizeClasses`); a hybrid uses each `surfaceContracts` entry’s exact responsive and release/capture set with no global platform, styling mechanism, viewports, or size classes; all sets match the PRD, approved wireframe, and stack;
- no unresolved placeholder, page-local value, or one-off control remains; and
- `design-system.md` and `design-system.json` publish together and agree through the pair checker.

## Reference Routing

- Read `references/design-system-guide.md` for normal contract compilation.
- Read `references/output-contract.md` for artifact boundaries and quality checks.
- Read `references/artifact-lifecycle.md` before creating staging files or publishing.
- Use `assets/templates/DESIGN_SYSTEM.template.md` and `assets/templates/DESIGN_SYSTEM.template.json` for the pair.
- Use the three scripts under `scripts/` for deterministic pair, contrast, and type-scale validation.
- When the owner asks to reopen direction, stop compilation and invoke `../ui-design-builder/SKILL.md`. Resume only after its updated `ui-design.md`, wireframe when affected, HiFi target, Impeccable review, grading, and human Visual Approval pass.

## Output Rules

- Default artifacts to English unless the user requests another language.
- Keep the design system implementation-facing.
- Keep candidate directions, reference analysis, and preview artifacts outside the published pair.
- Keep stable trace IDs across revisions; do not reuse retired IDs for different meanings.
- UI owner approval proves direction conformance, not representative-user usability. Record unresolved validation needs.
- Report exact staged and published paths, validation results, assumptions, and every intentionally unresolved gap.
