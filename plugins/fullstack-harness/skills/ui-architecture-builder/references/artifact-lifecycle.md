# Artifact Lifecycle

Keep the current UI architecture package directly under `docs/product/` and retain superseded design artifacts safely.

## Fixed Paths

Use the repository root as the workspace root. Publish these files unless the user names different exact paths (see `references/output-contract.md` for the deliverable contract):

- `docs/product/ui-architecture.md` (always)
- `docs/product/ui-registry.json` (always)
- `docs/product/page-recipes.md` (always)
- `docs/product/design-system.md` (always)
- `docs/product/visual-acceptance.md` (always)
- One file per page/route/screen under `docs/product/mockups/` (for example `docs/product/mockups/dashboard.html`), plus `docs/product/mockups/catalog.html`, for every platform
- `docs/product/motion-showcase.html` or bounded files under `docs/product/motion-demos/` when requested

Do not publish `docs/product/ui-mockups.md` or `docs/product/page-ui-matrix.md`. Both are retired; `page-recipes.md` carries the route → mockup → trace → DS → TEST index.

`ui-architecture.md` and `ui-registry.json` publish together, in the same approved move set. The registry is the allowlist the contract check reads, so publishing one without the other leaves the check pointing at a stale allowlist and passing pages that no longer conform. If only one of the two is validated, stage both and wait rather than publishing the half that is ready.

Stage a run under `docs/product/.design-staging/<run-id>/`, mirroring the same relative layout (including a `mockups/` subdirectory with its `catalog.html`). Do not draft over existing final files.

## Inventory

Before drafting, list exact final-path files and other clearly superseded design-package artifacts for the same product, including any existing `docs/product/mockups/` HTML files, any existing `docs/product/ui-registry.json`, and any retired `docs/product/ui-mockups.md` or `docs/product/page-ui-matrix.md` left over from an earlier package. Exclude `docs/product/archived/`, PRDs, architecture, stack decisions, research, test evidence, and ambiguous files. Leave ambiguous candidates untouched and report them. When archiving a superseded package, move the whole prior `docs/product/mockups/` directory — catalog included — alongside the other superseded files rather than leaving orphaned page HTML behind.

## Validate Then Ask

Validate the complete staged package first. Passing validation does not authorize overwrite, move, or archive. Show every exact final path that would be created or overwritten and every source-to-archive move. Continue only when the original request already authorized those exact mutations or the user explicitly approves the list.

If approval is absent, keep the staged package and all existing files unchanged.

## Publish

After approval:

1. Create `docs/product/archived/<YYYYMMDD-HHMMSS>-<product-slug>-design/` only when superseded artifacts exist.
2. Move only the approved superseded files into that new archive directory. Never overwrite an archive.
3. Move the validated staged artifacts to their final `docs/product/` paths. Move `ui-architecture.md` and `ui-registry.json` in the same step.
4. Remove only the now-empty run staging directory.
5. If any move fails, preserve every recoverable copy, stop, and report the exact state. Say plainly whether the published architecture and registry are still a matching pair, since a mismatched pair makes the contract check unreliable.

Never delete superseded files. Report published paths, archived paths, untouched ambiguous files, and whether any staged package is still awaiting approval.
