# Design Artifact Lifecycle

Use the repository's established product-document location. In this skill family, current design sources live under `docs/product/` and draft work lives in one run-specific directory under `docs/product/.prd-staging/`.

## Detect Existing Work

Before drafting, inspect the current `wireframes.md`, `design-system.md`, `design-system.json`, and any matching staged revision. Read all three current files when any one exists. A staged package may be newer than the published package; ask whether to resume, publish, or discard it before creating another competing draft.

Freeze the current product-source paths, revisions or SHA-256 digests, and decision owner. If the PRD, architecture, Builder UX Direction, or platform changes while design work is in progress, mark the design draft stale and reconcile the changed source before publication.

## Stage As One Set

Stage these files in the same run directory:

- `wireframes.md`
- `design-system.md`
- `design-system.json`

Do not publish directly while drafting. Do not create a placeholder for a product with no shipped UI surface.

## Validate And Publish

Validate the complete set before any overwrite or archive action. Show the exact source, destination, overwrite, and archive paths. Perform those mutations only when the user's instruction already authorizes those exact targets or after a direct approval.

Publish the three files as one reconciled set. Never publish only one design-system file, or publish a changed registry without the wireframes that reference its token and component names. When called by `prd-builder`, return the validated staged files to that parent; the parent publishes the whole product package in one lifecycle.

After a successful standalone publication, archive only clearly superseded versions and remove only the now-empty run staging directory. Ambiguous or unrelated files remain untouched.
