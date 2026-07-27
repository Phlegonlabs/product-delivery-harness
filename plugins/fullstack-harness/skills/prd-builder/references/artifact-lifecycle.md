# Artifact Lifecycle

Use this procedure to keep the current PRD package in `docs/product/` and retain superseded product documents safely in `docs/product/archived/`.

## Detect Enhancement Mode

Before doing anything else, check whether `docs/product/PRD.md` — or another Markdown document whose title or content clearly describes the same product — already exists. If it does, this run enhances that package; it does not start a new one.

- Read the existing `PRD.md`, `architecture.md`, `stack-decisions.md`, and `wireframes.md` in full before drafting anything.
- Treat their content, decisions, and trace IDs (`PRD-*`, `ARCH-*`, `UI-*`, `UX-*`, `TEST-*`) as the baseline. Carry forward every section the new request does not touch, unchanged.
- Draft only the additions, edits, or removals the new discovery actually requires. Never regenerate the whole package from a blank slate because a new idea came up.
- The final publish paths stay the same fixed locations (`docs/product/PRD.md`, `docs/product/architecture.md`, `docs/product/stack-decisions.md`, `docs/product/wireframes.md`) — enhancement mode overwrites the existing package in place. It does not create a new dated folder, a differently named file, or a parallel PRD for the same product.
- Enhancement mode still uses the staging, validation, and archive steps below: the prior version is archived for history once the enhanced draft is validated, even though its content already carried forward into that draft.

## Handle an Unrelated Document at a Fixed Publish Path

If `docs/product/PRD.md`, `docs/product/architecture.md`, `docs/product/stack-decisions.md`, or `docs/product/wireframes.md` already exists but its content clearly describes a different, unrelated product, this is not enhancement mode: draft the new package from scratch instead of carrying forward its content or trace IDs.

The publish step still overwrites that exact path regardless of whether it enhances or replaces it, so the existing file must still be archived for safety — add it to the superseded-document inventory even though it is an unrelated product document. The general exclusion for unrelated product documents in "Inventory Superseded Documents" below applies to other documents found elsewhere in the repository, not to one already occupying a path this run will publish to.

In the Approval Gate, label this path explicitly as "existing unrelated content that will be overwritten and archived," not as a generic prior-version overwrite, so the user can catch the collision before approving.

## Resolve Locations

- Treat the Git repository root as the workspace root. If no Git repository exists, use the current workspace root.
- Create `docs/product/` when it does not exist.
- Publish the current package to these final paths unless the user explicitly requests different filenames:
  - `docs/product/PRD.md`
  - `docs/product/architecture.md`
  - `docs/product/stack-decisions.md`
  - `docs/product/wireframes.md`
  - `docs/product/design-system.md` for a UI-bearing product
  - `docs/product/design-system.json` for a UI-bearing product
  - `docs/product/implementation-plan.md` when requested
- `design-system.md` and `design-system.json` publish together, in the same approved move set. The JSON is the allowlist `fullstack-harness-engineering`'s contract check reads, so publishing one without the other leaves that check pointing at a stale allowlist and passing code that no longer conforms. If only one of the two is validated, stage both and wait rather than publishing the half that is ready.
- Never publish PRD artifacts at the repository root or flat in `docs/` by default. They belong in `docs/product/`.
- Never use `docs/product/archived/` as an input or output location for the current package.

## Inventory Superseded Documents

Before drafting, identify the documents that the new package will supersede. Candidates include:

- Earlier versions of the package's exact filenames in `docs/product/`, the repository root, or a legacy flat `docs/` directory.
- Other Markdown product documents whose title or contents clearly identify the same product and whose purpose is replaced by one of the new artifacts.
- A previous implementation plan only when a new implementation plan is being produced or the user explicitly says it is obsolete.

Exclude:

- Everything already under `docs/product/archived/`.
- Research, meeting notes, source material, test evidence, and unrelated product documents — unless the unrelated document occupies one of this run's exact final publish paths, per "Handle an Unrelated Document at a Fixed Publish Path" above, in which case it must still be inventoried and archived.

  `design-system.md` and `design-system.json` are this package's own artifacts and are **not** excluded: a superseded pair is archived together with the rest of the package. Never archive one without the other, and never archive a design system while keeping the `wireframes.md` that references its `DS-*` IDs.
- Any ambiguous candidate. Leave it in place and mention it to the user instead of guessing.

Record the candidate paths before creating staged artifacts. Do not archive or overwrite them yet.

## Stage and Validate

1. Create a run-specific staging directory under `docs/product/.prd-staging/`.
2. Write the complete new package there using the final artifact filenames.
3. Run the output-contract quality checklist against the staged files.
4. Keep all existing documents in place if the workflow is incomplete, paused, or fails validation.

## Approval Gate

Passing validation does not authorize an overwrite, move, or archive. Before publishing, list every exact final path that would be created or overwritten and every source-to-archive move. Continue only when the user's original request already authorized those exact mutations or the user explicitly approves the list. If approval is absent, keep the staged package and existing documents unchanged.

## Archive and Publish

After the entire staged package passes validation and the exact mutation list is authorized:

1. Create `docs/product/archived/<YYYYMMDD-HHMMSS>-<product-slug>/`.
2. Move only the previously inventoried superseded documents into that directory. Preserve recognizable filenames; when basenames collide, include the original parent directory or a numeric suffix.
3. Move the validated staged artifacts into their final paths under `docs/product/`.
4. Remove the now-empty run-specific staging directory. Remove `docs/product/.prd-staging/` only when it is empty.
5. If an archive or publish move fails, restore moved files when safe, keep every recoverable copy, stop, and report the exact state.

Do not delete superseded documents. Do not overwrite an archive directory. Do not add unrelated files merely to make the archive look complete.

## Completion Report

List:

- Every artifact published under `docs/product/`.
- Every document moved under `docs/product/archived/`.
- Any ambiguous legacy document deliberately left untouched.
- Whether publication was completed or the validated staging package is awaiting explicit approval.
