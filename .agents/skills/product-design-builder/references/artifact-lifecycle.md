# Design Artifact Lifecycle

Use the repository's established product-document location. In this skill family, current design sources live under `docs/product/` and draft work lives in one run-specific directory under `docs/product/.prd-staging/`.

## Detect Existing Work

Before drafting, inspect the current `PRD.md`, `wireframes.html`, `design-system.md`, `design-system.json`, and any matching staged revision. Read the current PRD, approved wireframe HTML, and both design-system files when either design-system file exists. A staged package may be newer than the published package; ask whether to resume, publish, or discard it before creating another competing draft.

Freeze the current product-source paths, revisions or SHA-256 digests, `wireframes.html` approval, approved UI Design Handoff, Design System Need Gate, and decision owner. If the PRD, wireframe HTML, approved UI target, architecture, Builder UX Direction, or platform changes while design work is in progress, mark the design draft stale and reconcile the changed source before publication.

## Stage As One Set

Only when the Design System Need Gate is `required`, stage these files in the same run directory:

- `design-system.md`
- `design-system.json`

Do not publish directly while drafting. Do not create a placeholder for a product with no shipped UI surface.

Keep UI Design Pass previews and their evidence manifest outside `docs/product/`. When repository retention is useful, use the disclosed path recorded by `prd-builder`, such as `docs/design/ui-references/<run-id>/`; a set superseded by a later approved target archives under `docs/design/archived/` per `prd-builder`'s lifecycle. The selected target binds only through the immutable source and approval record in `PRD.md`; Product Design Builder does not republish the preview inside the pair.

## Validate And Publish

Validate the complete set before any overwrite or archive action. Show the exact source, destination, overwrite, and archive paths. Perform those mutations only when the user's instruction already authorizes those exact targets or after a direct approval.

Publish the two design-system files as one reconciled set. Never publish only one design-system file. When called by `prd-builder`, return the validated staged pair to that parent; the parent publishes the whole product package in one lifecycle.

After a successful standalone publication, archive only clearly superseded versions and remove only the now-empty run staging directory. Ambiguous or unrelated files remain untouched.
