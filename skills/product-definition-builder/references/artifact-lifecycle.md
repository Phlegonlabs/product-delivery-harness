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

- Read the existing `PRD.md`, `architecture.md`, `stack-decisions.md`, and — when present — `wireframes.html`, `design-system.md`, `design-system.json`, `market-research.md`, `research-assessment.md`, and `outcome-review.md` in full before drafting anything. Read an existing `docs/ACTIVATION.md` for operational context, but do not carry it into the product drafting package or overwrite it.
- Treat their content, decisions, and trace IDs (`PRD-*`, `ARCH-*`, `UI-*`, `UX-*`, `TEST-*`, `DS-*`, `MR-*`, `RA-*`) as the baseline. Carry forward every section the new request does not touch, unchanged.
- Draft only the additions, edits, or removals the new discovery actually requires. Never regenerate the whole package from a blank slate because a new idea came up.
- The final publish paths stay the same fixed locations listed in Resolve Locations below — `PRD.md`, `architecture.md`, `stack-decisions.md`, and, when they apply, `wireframes.html`, `design-system.md`, `design-system.json`, `market-research.md`, `research-assessment.md`, and `implementation-plan.md`, all directly under `docs/product/`. The seeded operational documents — `docs/DEPLOYMENT.md` and `docs/DOCUMENTS.md` — publish under `docs/` in the same move. A new `docs/ACTIVATION.md` seed joins that move only when the product has a web, iOS, or browser-extension release target, the sibling skill is available, and the live path is absent; an existing Activation record is preserved. Enhancement mode overwrites the existing product package in place. It does not create a new dated folder, a differently named file, or a parallel PRD for the same product.
- Enhancement mode still uses the staging, validation, and archive steps below: the prior version is archived for history once the enhanced draft is validated, even though its content already carried forward into that draft.

## Handle an Unrelated Document at a Fixed Publish Path

If `docs/product/PRD.md`, `docs/product/architecture.md`, `docs/product/stack-decisions.md`, `docs/product/wireframes.html`, `docs/product/design-system.md`, `docs/product/design-system.json`, `docs/product/market-research.md`, `docs/product/research-assessment.md`, or `docs/product/outcome-review.md` already exists but its content clearly describes a different, unrelated product, this is not enhancement mode: draft the new package from scratch instead of carrying forward its content or trace IDs.

The publish step still overwrites that exact path regardless of whether it enhances or replaces it, so the existing file must still be archived for safety — add it to the superseded-document inventory even though it is an unrelated product document. The general exclusion for unrelated product documents in "Inventory Superseded Documents" below applies to other documents found elsewhere in the repository, not to one already occupying a path this run will publish to.

In the Approval Gate, label this path explicitly as "existing unrelated content that will be overwritten and archived," not as a generic prior-version overwrite, so the user can catch the collision before approving.

## Resolve Locations

- Treat the Git repository root as the workspace root. If no Git repository exists, use the current workspace root.
- Create `docs/product/` when it does not exist.
- Publish the current package to these final paths unless the user explicitly requests different filenames:
  - `docs/product/PRD.md`
  - `docs/product/architecture.md`
  - `docs/product/stack-decisions.md`
  - `docs/product/wireframes.html` for a UI-bearing product
  - `docs/product/design-system.md` when a UI-bearing product's Design System Need Gate is `required`
  - `docs/product/design-system.json` when that gate is `required`
  - `docs/product/market-research.md` when the market-research gap pass produced it
  - `docs/product/research-assessment.md` when the research-first assessment produced it
  - `docs/product/outcome-review.md` after a deployed release's outcome review
  - `docs/product/implementation-plan.md` when requested
- Publish a create-once operational seed to `docs/ACTIVATION.md` only when the output contract says it applies and that final path is absent. Never use this workflow to refresh an existing Activation record.
- When the Design System Need Gate is `required`, `design-system.md` and `design-system.json` publish together in the same approved move set. The JSON is the allowlist `delivery-harness`'s contract check reads, so publishing one without the other leaves that check pointing at a stale allowlist. If only one is validated, stage both and wait rather than publishing half a pair. When the gate is `not_required`, publish neither file.
- For a UI-bearing product, publish approved `wireframes.html` plus `PRD.md`'s `### Wireframe Approval` in the same whole-package move. A changed PRD UI contract with a stale wireframe artifact is not a complete package. A later explicitly requested visual-design handoff and design-system pair join a future approved move only when they apply.
- The UI Design Pass produces one design-reference preview HTML with deferred image and motion prompts; it does not generate media or a React prototype. Keep that HTML outside `docs/product/`. The `wireframes.html` review projection is the sole HTML exception. When the owner requests retention of the design-reference HTML, use a disclosed path under `docs/design/ui-references/<run-id>/` for the one connected all-screens implementation reference and obtain exact write approval. Only the selected immutable preview becomes binding through the optional `PRD.md` UI Design Handoff. A later separately authorized MCP generation flow owns its generated assets and follow-up evidence; this pass does not pre-authorize or retain them.
- A later approved UI target that supersedes retained UI references archives the superseded files under `docs/design/archived/<YYYYMMDD-HHMMSS>-<run-id>/`, mirroring how superseded product documents move to `docs/product/archived/`. Move, never delete, and update the UI Design Handoff to the replacement live paths so no live contract points at an archived reference.
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

  `design-system.md` and `design-system.json` are this package's own artifacts and are **not** excluded when the Design System Need Gate is or was `required`: a superseded pair is archived together with the rest of the package. Never archive one without the other. A new `not_required` decision does not silently delete an existing canonical pair; record and explicitly authorize its retirement or keep the existing pair as the effective source.

  `wireframes.html` is also this package's own artifact. Archive it with the matching PRD and, when one exists, the design-system pair; do not leave a current review projection or visual contract pointing at an archived product source.

  `market-research.md` is also this package's own artifact, not the general "research" the exclusion means. A superseded `market-research.md` is archived with the rest of the package. Never archive it while keeping a `PRD.md` that cites its `MR-*` IDs, and — when this run's research pass was skipped or blocked — do not archive a prior `market-research.md` at all: leave it published, since nothing replaces it.

  `research-assessment.md` follows the same rule: archive it with the rest of the package, never while keeping a `PRD.md` that cites its `RA-*` IDs, and — when this run's research-first assessment was skipped — leave the prior one published, since nothing replaces it.

  `outcome-review.md` is a post-deployment record, not part of the drafting package. A superseded review archives with the rest of the package; a package that ships without a new review leaves the prior one published, since it still describes the last observed outcome.

  `docs/ACTIVATION.md` is an operational record outside `docs/product/`. Exclude it from the superseded-document inventory. If it exists, preserve it byte-for-byte and let `product-activation` reconcile it after delivery.
- Any ambiguous candidate. Leave it in place and mention it to the user instead of guessing.

Record the candidate paths before creating staged artifacts. Do not archive or overwrite them yet.

## Stage and Validate

1. Create a run-specific staging directory under `docs/product/.prd-staging/` — unless Detect Enhancement Mode found a staged package for this product and the user chose to resume it, in which case reuse that directory instead of opening a second one.
2. Write the complete new package there using the final artifact filenames, including the drafted `DEPLOYMENT.md` and `DOCUMENTS.md` (published under `docs/`) and the create-once `ACTIVATION.md` seed when applicable.
3. Run the output-contract quality checklist against the staged files.
4. Keep all existing documents in place if the workflow is incomplete, paused, or fails validation.

## Approval Gate

Passing validation does not authorize an overwrite, move, or archive. Before publishing, list every exact final path that would be created or overwritten and every source-to-archive move. Continue only when the user's original request already authorized those exact mutations or the user explicitly approves the list. If approval is absent, keep the staged package and existing documents unchanged.

## Archive and Publish

After the entire staged package passes validation and the exact mutation list is authorized:

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
