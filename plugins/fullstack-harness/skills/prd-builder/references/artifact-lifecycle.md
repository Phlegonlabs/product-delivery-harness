# Artifact Lifecycle

Use this procedure to keep the current PRD package in `doc/` and retain superseded product documents safely in `doc/archived/`.

## Resolve Locations

- Treat the Git repository root as the workspace root. If no Git repository exists, use the current workspace root.
- Create `doc/` when it does not exist.
- Publish the current package to these final paths unless the user explicitly requests different filenames:
  - `doc/PRD.md`
  - `doc/architecture.md`
  - `doc/wireframes.md`
  - `doc/implementation-plan.md` when requested
- Never publish PRD artifacts at the repository root or under `docs/` by default.
- Never use `doc/archived/` as an input or output location for the current package.

## Inventory Superseded Documents

Before drafting, identify the documents that the new package will supersede. Candidates include:

- Earlier versions of the package's exact filenames in `doc/`, the repository root, or a legacy `docs/` directory.
- Other Markdown product documents whose title or contents clearly identify the same product and whose purpose is replaced by one of the new artifacts.
- A previous implementation plan only when a new implementation plan is being produced or the user explicitly says it is obsolete.

Exclude:

- Everything already under `doc/archived/`.
- Research, meeting notes, source material, design-system documents, test evidence, and unrelated product documents.
- Any ambiguous candidate. Leave it in place and mention it to the user instead of guessing.

Record the candidate paths before creating staged artifacts. Do not archive or overwrite them yet.

## Stage and Validate

1. Create a run-specific staging directory under `doc/.prd-staging/`.
2. Write the complete new package there using the final artifact filenames.
3. Run the output-contract quality checklist against the staged files.
4. Keep all existing documents in place if the workflow is incomplete, paused, or fails validation.

## Approval Gate

Passing validation does not authorize an overwrite, move, or archive. Before publishing, list every exact final path that would be created or overwritten and every source-to-archive move. Continue only when the user's original request already authorized those exact mutations or the user explicitly approves the list. If approval is absent, keep the staged package and existing documents unchanged.

## Archive and Publish

After the entire staged package passes validation and the exact mutation list is authorized:

1. Create `doc/archived/<YYYYMMDD-HHMMSS>-<product-slug>/`.
2. Move only the previously inventoried superseded documents into that directory. Preserve recognizable filenames; when basenames collide, include the original parent directory or a numeric suffix.
3. Move the validated staged artifacts into their final paths under `doc/`.
4. Remove the now-empty run-specific staging directory. Remove `doc/.prd-staging/` only when it is empty.
5. If an archive or publish move fails, restore moved files when safe, keep every recoverable copy, stop, and report the exact state.

Do not delete superseded documents. Do not overwrite an archive directory. Do not add unrelated files merely to make the archive look complete.

## Completion Report

List:

- Every artifact published under `doc/`.
- Every document moved under `doc/archived/`.
- Any ambiguous legacy document deliberately left untouched.
- Whether publication was completed or the validated staging package is awaiting explicit approval.
