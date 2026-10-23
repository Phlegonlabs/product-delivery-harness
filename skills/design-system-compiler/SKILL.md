---
name: design-system-compiler
description: "Compile an owner-approved UI design into the frozen `docs/design/design-system.md` and `docs/design/design-system.json` pair plus its derived `design-system-preview.html`. Run it after Visual Approval and Design System Need Gate: required. It freezes tokens, primitives, components, motion, responsive rules, and states; it does not choose product, stack, layout, or visual direction."
---

`sourceBindings.uiDesign.sha256` uses the canonical UI approval digest, not the raw file hash. Run `python "<ui-design-builder-skill-root>/scripts/ui_approval_digest.py" <ui-design.md>`; it excludes active derived pair/replacement linkage lines so linking the compiled pair does not invalidate its own input. For `ui-design/3` it also excludes the `Package action` and `Existing design-system pair disposition` lines, so switching to `reuse` keeps an unchanged package valid while any other approval edit makes it stale. All other source bindings use raw-file SHA-256.

# Design System Compiler

## Installed Commands

Resolve `<design-system-compiler-skill-root>` and logical script paths as [Installed Commands](../delivery-harness/references/installed-commands.md) states.

## Purpose

At every invocation, run the [entry checklist](../delivery-harness/references/governance/task-and-handoff.md#project-entry-and-current-work). Compile the approved persona-dependent component states without creating accounts or changing requirements. Rechecking or rebuilding the same approved direction is technical verification, not a reason to repeat its approval; changed direction remains an upstream gap.

Turn an approved UI direction into two binding reusable UI sources:

- `design-system.md` for the selected visual direction and short human-facing rules; and
- `design-system.json` for machine-readable tokens, primitives, closed variants, product components, motion, responsive rules, source paths, and the state matrix.

Invoke it only when Product Definition Approval and the Stack Decision Checkpoint are approved and `docs/design/ui-design.md` records the approved complete HiFi decision plus `Design System Need Gate: required`. A `ui-design/3` package always requires it and names `Package action: compile|update|reuse`. The compiler respects the approved component foundation and styling approach; it never changes stack by implication. `PRD.md` owns product behavior, while `ui-design-builder` owns `ui-design.md` and the HiFi target; a historical wireframe remains legacy evidence only. Do not duplicate or change those contracts, implement production UI, or create Harness PLAN/RUN state.

## Stage Routing

Read the owning section before its matching action. Domain and direction guidance stays conditional.

- Before compile or update, read [Compilation Skills Gate](references/stages/design-compilation.md#compilation-skills-gate), [Inputs And Ownership](references/stages/design-compilation.md#inputs-and-ownership), [Workflow](references/stages/design-compilation.md#workflow), [Validation](references/stages/design-compilation.md#validation), and [Output Rules](references/stages/design-compilation.md#output-rules).
- Before validate or reuse, read [Compilation Skills Gate](references/stages/design-compilation.md#compilation-skills-gate), [Inputs And Ownership](references/stages/design-compilation.md#inputs-and-ownership), and [Validation](references/stages/design-compilation.md#validation).
- Before publication, read [Output Rules](references/stages/design-compilation.md#output-rules) and [Artifact Lifecycle](references/artifact-lifecycle.md#design-system-artifact-lifecycle).
- For an unresolved domain decision or reference route, read [Reference Routing](references/stages/design-compilation.md#reference-routing). Do not reselect the stack or visual direction.

## Entry Boundary

- Product Definition Approval and the Stack Decision Checkpoint must be approved before compilation.
- A `ui-design/3` package compiles `design-system/4`; a `ui-design/2` package compiles `design-system/3` only when its Design System Need Gate is required. Both consume the complete approved `ui-hifi/2` package.
- `PRD.md` owns product behavior; `ui-design-builder` owns `ui-design.md` and the approved HiFi target. The compiler owns the design-system pair and its derived HTML.
- `frontend-design` is required without a fallback; compilation does not reopen direction. Product or stack changes return upstream.
- Compilation derives approved consequences only. Validation includes mutating `--write` commands and does not auto-authorize publication.
- Script- or state-driven motion uses `ds-showcase/2` source-runtime rows.
