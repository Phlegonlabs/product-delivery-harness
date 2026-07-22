# Artifact Lifecycle

Keep the current design package directly under `doc/` and retain superseded design artifacts safely.

## Fixed Paths

Use the repository root as the workspace root. Publish these files unless the user names different exact paths (see `references/output-contract.md` for the deliverable contract):

- `doc/design-system.md` (always)
- `doc/visual-acceptance.md` (always)
- `doc/ui-mockups.md` (the slim index) plus one file per page/route/screen under `doc/mockups/` (for example `doc/mockups/dashboard.html`), for every platform. Do not publish `doc/page-ui-matrix.md`.
- `doc/motion-showcase.html` or bounded files under `doc/motion-demos/` when requested

Stage a run under `doc/.design-staging/<run-id>/`, mirroring the same relative layout (including a `mockups/` subdirectory). Do not draft over existing final files.

## Inventory

Before drafting, list exact final-path files and other clearly superseded design-package artifacts for the same product, including any existing `doc/mockups/` HTML files. Exclude `doc/archived/`, PRDs, architecture, research, test evidence, and ambiguous files. Leave ambiguous candidates untouched and report them. When archiving a superseded package, move the whole prior `doc/mockups/` directory alongside the other superseded files rather than leaving orphaned page HTML behind.

## Validate Then Ask

Validate the complete staged package first. Passing validation does not authorize overwrite, move, or archive. Show every exact final path that would be created or overwritten and every source-to-archive move. Continue only when the original request already authorized those exact mutations or the user explicitly approves the list.

If approval is absent, keep the staged package and all existing files unchanged.

## Publish

After approval:

1. Create `doc/archived/<YYYYMMDD-HHMMSS>-<product-slug>-design/` only when superseded artifacts exist.
2. Move only the approved superseded files into that new archive directory. Never overwrite an archive.
3. Move the validated staged artifacts to their final `doc/` paths.
4. Remove only the now-empty run staging directory.
5. If any move fails, preserve every recoverable copy, stop, and report the exact state.

Never delete superseded files. Report published paths, archived paths, untouched ambiguous files, and whether any staged package is still awaiting approval.
