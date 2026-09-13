# Artifact Lifecycle

Use this procedure to keep the current PRD package in `docs/product/` and retain superseded product documents safely in `docs/product/archived/`.

## Detect Enhancement Mode

Before doing anything else, check both places a package for this product can be sitting:

1. `docs/product/PRD.md` — or another Markdown document whose title or content clearly describes the same product. If it exists, this run enhances that package; it does not start a new one.
2. `docs/product/.prd-staging/` — a validated package a previous run staged but never published, because the user declined or never answered the publication question.

A staged package for the same product is **newer than the published one** and is the real baseline. Do not create a second staging directory beside it and do not silently enhance the older published copy:

- Read the staged package in full, tell the user it exists and what it contains, and ask whether to resume it, publish it as-is first, or discard it.
- Resume means: reuse that directory, carry its content forward as the baseline, and apply this run's delta on top.
- Discard means the user explicitly says so; move it to `docs/product/archived/<YYYYMMDD-HHMMSS>-abandoned-staging/` rather than deleting it, and say where it went.
- Until the user answers, change nothing in `.prd-staging/`.

A staging directory describing a *different* product is left untouched and reported; start this run's own staging directory beside it.

- Read the existing `PRD.md`, `architecture.md`, `stack-decisions.md`, `market-research.md`, `research-assessment.md`, and `outcome-review.md` in full before drafting. Read `docs/design/ui-design.md`, its wireframe, and its design-system pair only to identify downstream impact; never carry them into Product Definition staging or rewrite them here. Read an existing `docs/ACTIVATION.md` for operational context, but do not overwrite it.
- Treat their content, decisions, and trace IDs (`PRD-*`, `ARCH-*`, `UI-*`, `UX-*`, `TEST-*`, `DS-*`, `MR-*`, `RA-*`) as the baseline. Carry forward every section the new request does not touch, unchanged.
- Draft only the additions, edits, or removals the new discovery actually requires. Never regenerate the whole package from a blank slate because a new idea came up.
- The final publish paths stay the same fixed locations listed in Resolve Locations below — `PRD.md`, `architecture.md`, `stack-decisions.md`, and, when they apply, `market-research.md`, `research-assessment.md`, and `implementation-plan.md`, all directly under `docs/product/`. The seeded operational documents — `docs/DEPLOYMENT.md` and `docs/DOCUMENTS.md` — publish under `docs/` in the same move. A new `docs/ACTIVATION.md` seed joins that move only when the product has a web, iOS, or browser-extension release target, the sibling skill is available, and the live path is absent; an existing Activation record is preserved. Enhancement mode overwrites the existing product package in place. It does not create a new dated folder, a differently named file, or a parallel PRD for the same product.
- Enhancement mode still uses the staging, validation, and archive steps below: the prior version is archived for history once the enhanced draft is validated, even though its content already carried forward into that draft.

## Handle an Unrelated Document at a Fixed Publish Path

If `docs/product/PRD.md`, `docs/product/architecture.md`, `docs/product/stack-decisions.md`, `docs/product/market-research.md`, `docs/product/research-assessment.md`, or `docs/product/outcome-review.md` already exists but its content clearly describes a different, unrelated product, this is not enhancement mode: draft the new package from scratch instead of carrying forward its content or trace IDs.

The publish step still overwrites that exact path regardless of whether it enhances or replaces it, so the existing file must still be archived for safety — add it to the superseded-document inventory even though it is an unrelated product document. The general exclusion for unrelated product documents in "Inventory Superseded Documents" below applies to other documents found elsewhere in the repository, not to one already occupying a path this run will publish to.

In the Publication Authorization Gate, label this path explicitly as "existing unrelated content that will be overwritten and archived," not as a generic prior-version overwrite, so the user can catch the collision before authorizing it.

## Resolve Locations

- Treat the Git repository root as the workspace root. If no Git repository exists, use the current workspace root.
- Create `docs/product/` when it does not exist.
- Publish the current package to these final paths unless the user explicitly requests different filenames:
  - `docs/product/PRD.md`
  - `docs/product/architecture.md`
  - `docs/product/stack-decisions.md`
  - `docs/product/market-research.md` when the market-research gap pass produced it
  - `docs/product/research-assessment.md` when the research-first assessment produced it
  - `docs/product/outcome-review.md` after a deployed release's outcome review
  - `docs/product/implementation-plan.md` when requested
- Publish a create-once operational seed to `docs/ACTIVATION.md` only when the output contract says it applies and that final path is absent. Never use this workflow to refresh an existing Activation record.
- `ui-design-builder` owns every `docs/design/` artifact, Copy Freeze, and their separate publication and archival gate. A PRD `` `copy` `` anchor records only product-owned copy responsibility; schema-4 wireframe approval may advance a PRD draft responsibility to approved wireframe copy without a circular PRD rewrite. `revision_requested` or `blocked` PRD copy stops UI work. Product Definition only records whether the later design phase is pending or not required.
- Never publish PRD artifacts at the repository root or flat in `docs/` by default. They belong in `docs/product/`. The seeded operational documents `docs/DEPLOYMENT.md` and `docs/DOCUMENTS.md` publish flat under `docs/` and refresh in place. `docs/ACTIVATION.md` also lives flat under `docs/`, but Product Definition creates it only when absent; `product-activation` owns every later refresh. None of these operational documents is archived with the product package. The PRD seed records known secret and variable names plus external-console work without values; `delivery-harness` reconciles that deployment handoff before a deployable push, and `product-activation` reconciles post-delivery actions and measurement sources.
- Never use `docs/product/archived/` as an input or output location for the current package.

## Inventory Superseded Documents

Before drafting, identify the documents that the new package will supersede. Candidates include:

- Earlier versions of the package's exact filenames in `docs/product/`, the repository root, or a legacy flat `docs/` directory.
- Other Markdown product documents whose title or contents clearly identify the same product and whose purpose is replaced by one of the new artifacts.
- A previous implementation plan only when a new implementation plan is being produced or the user explicitly says it is obsolete.

Exclude:

- Everything already under `docs/product/archived/`.
- Research, meeting notes, source material, test evidence, and unrelated product documents — unless the unrelated document occupies one of this run's exact final publish paths, per "Handle an Unrelated Document at a Fixed Publish Path" above, in which case it must still be inventoried and archived.

  `docs/design/ui-design.md`, wireframes, retained references, and design-system files are downstream UI artifacts. Exclude them from Product Definition archival. Report that a changed PRD may make them stale and leave reconciliation to `ui-design-builder`.

  `market-research.md` is also this package's own artifact, not the general "research" the exclusion means. A superseded `market-research.md` is archived with the rest of the package. Never archive it while keeping a `PRD.md` that cites its `MR-*` IDs, and — when this run's research pass was skipped or blocked — do not archive a prior `market-research.md` at all: leave it published, since nothing replaces it.

  `research-assessment.md` follows the same rule: archive it with the rest of the package, never while keeping a `PRD.md` that cites its `RA-*` IDs, and — when this run's research-first assessment was skipped — leave the prior one published, since nothing replaces it.

  `outcome-review.md` is a post-deployment record, not part of the drafting package. A superseded review archives with the rest of the package; a package that ships without a new review leaves the prior one published, since it still describes the last observed outcome.

  `docs/ACTIVATION.md` is an operational record outside `docs/product/`. Exclude it from the superseded-document inventory. If it exists, preserve it byte-for-byte and let `product-activation` reconcile it after delivery.
- Any ambiguous candidate. Leave it in place and mention it to the user instead of guessing.

Record the candidate paths before creating staged artifacts. Do not archive or overwrite them yet.

## Stage and Validate

1. Create a run-specific staging directory under `docs/product/.prd-staging/` — unless Detect Enhancement Mode found a staged package for this product and the user chose to resume it, in which case reuse that directory instead of opening a second one.
2. Write the core Markdown candidate there using the final artifact filenames, including the drafted `DEPLOYMENT.md` and `DOCUMENTS.md` and the create-once `ACTIVATION.md` seed when applicable. Do not prepare UI wireframe data.
3. Complete market reconciliation, Stack Decision Checkpoint, and Product Definition Approval. A substantive approved-content revision reopens approval.
4. Run `python <product-definition-builder-root>/scripts/check_product_package.py --prd <staged PRD.md> --architecture <staged architecture.md> --stack-decisions <staged stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved`.
5. Run the output-contract quality checklist against the complete staged files.
6. Keep all existing documents in place if the workflow is incomplete, paused, or fails validation.

## Publication Authorization Gate

Product Definition Approval accepts the package's content; it does not authorize filesystem changes. Passing validation also does not authorize an overwrite, move, or archive. Before publishing, list every exact final path that would be created or overwritten and every source-to-archive move. Continue only when the user's original request already authorized those exact mutations or the user explicitly approves the list. If authorization is absent, keep the staged package and existing documents unchanged; its recorded content approval remains intact.

## Archive and Publish

After the entire staged package has an approved Product Definition decision, passing core-package checkers, and an authorized exact mutation list:

1. Create `docs/product/archived/<YYYYMMDD-HHMMSS>-<product-slug>/`.
2. Move only the previously inventoried superseded documents into that directory. Preserve recognizable filenames; when basenames collide, include the original parent directory or a numeric suffix.
3. Move the validated staged artifacts into their final paths under `docs/product/`, publish the seeded `DEPLOYMENT.md`/`DOCUMENTS.md` to `docs/`, and create `docs/ACTIVATION.md` only when the approved move lists a new seed and the path is still absent. If that path appeared after staging, stop instead of overwriting it.
4. Remove the now-empty run-specific staging directory. Remove `docs/product/.prd-staging/` only when it is empty.
5. If an archive or publish move fails, restore moved files when safe, keep every recoverable copy, stop, and report the exact state.

Do not delete superseded documents. Do not overwrite an archive directory. Do not add unrelated files merely to make the archive look complete.

## Completion Report

List:

- Every artifact published under `docs/product/`.
- The operational documents published or refreshed under `docs/` (`DEPLOYMENT.md`, `DOCUMENTS.md`) and whether `ACTIVATION.md` was created or preserved.
- Every document moved under `docs/product/archived/`.
- Any ambiguous legacy document deliberately left untouched.
- Whether publication was completed or the validated staging package is awaiting explicit approval.
