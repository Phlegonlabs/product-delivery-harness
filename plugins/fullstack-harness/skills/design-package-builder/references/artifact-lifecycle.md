# Artifact Lifecycle

Keep the current design package directly under `doc/` and retain superseded design artifacts safely.

## Fixed Paths

Use the repository root as the workspace root. Publish these files unless the user names different exact paths:

- `doc/design-system.md`
- `doc/page-ui-matrix.md`
- `doc/ui-mockups.md`
- `doc/visual-acceptance.md`
- `doc/motion-showcase.html` or bounded files under `doc/motion-demos/` when requested

Stage a run under `doc/.design-staging/<run-id>/`. Do not draft over existing final files.

## Inventory

Before drafting, list exact final-path files and other clearly superseded design-package artifacts for the same product. Exclude `doc/archived/`, PRDs, architecture, research, test evidence, and ambiguous files. Leave ambiguous candidates untouched and report them.

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
