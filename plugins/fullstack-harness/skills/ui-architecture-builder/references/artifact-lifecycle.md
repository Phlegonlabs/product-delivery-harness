# Artifact Lifecycle

Keep the current UI architecture package directly under `docs/product/` and retain superseded design artifacts safely.

## Fixed Paths

Use the repository root as the workspace root. Publish these files unless the user names different exact paths (see `references/output-contract.md` for the deliverable contract):

- `docs/product/ui-architecture.md` (always)
- `docs/product/ui-registry.json` (always)
- `docs/product/page-recipes.md` (always)
- `docs/product/design-system.md` (always)
- `docs/product/design/design-system.html` (always; rendered projection of `design-system.md` and `ui-registry.json`)
- `docs/product/visual-acceptance.md` (always)
- One file per page/route/screen under `docs/product/mockups/` (for example `docs/product/mockups/dashboard.html`), plus `docs/product/mockups/catalog.html`, for every platform
- `docs/product/motion-showcase.html` or bounded files under `docs/product/motion-demos/` when requested

Do not publish `docs/product/ui-mockups.md` or `docs/product/page-ui-matrix.md`. Both are retired; `page-recipes.md` carries the route → mockup → trace → DS → TEST index.

`ui-architecture.md` and `ui-registry.json` publish together, in the same approved move set. The registry is the allowlist the contract check reads, so publishing one without the other leaves the check pointing at a stale allowlist and passing pages that no longer conform. If only one of the two is validated, stage both and wait rather than publishing the half that is ready.

`design-system.md` and `design-system.html` also publish together. The Markdown file remains the semantic source; the HTML file is its rendered projection and must never become a second authority. If tokens, primitives, variants, states, or parameters change, rebuild and validate the HTML from the Markdown plus `ui-registry.json` before publishing either artifact.

Stage a run under `docs/product/.design-staging/<run-id>/`, mirroring the same relative layout (including a `mockups/` subdirectory with its `catalog.html`). Do not draft over existing final files.

## Visual-Direction Candidate Lifecycle

When the explicitly authorized Frontend Design Visual Direction Pass is used, write its one coherent set of one to three representative screens under:

```text
docs/product/.design-staging/<run-id>/visual-directions/<direction-id>/
```

Keep candidate HTML and notes in that subtree only. They are non-canonical review evidence and are never part of the fixed publish set, never copied into `mockups/`, and never consumed by implementation. Record the human selection plus accepted, rejected, and deferred cues in staged `design-system.md`, then normalize the accepted cues into the package's tokens, primitive and component contracts, recipes, registry, and final mockups.

Before publication, list the exact candidate disposition with the canonical publish paths:

- **Archive:** move the candidate subtree to a new, non-overwriting `docs/product/archived/<YYYYMMDD-HHMMSS>-<product-slug>-visual-directions/` path.
- **Retain:** leave only the candidate subtree in the run staging directory and report it as non-canonical review evidence.

Archive or retain requires exact user authorization with the rest of the move set. Never delete candidate files without explicit approval. A retained `visual-directions/` subtree does not block publication because it contains no duplicate canonical package; report its exact path and do not remove its parent staging directory.

Before canonical publication, apply the approved candidate disposition and rewrite staged `design-system.md`'s `Candidate evidence` to the actual final archive or retained path. `pending publication approval` is valid only in staging. Rebuild `design-system.html` when it projects that record, then revalidate the canonical staged package after the provenance rewrite. A published `design-system.md` must never point to an Archive source under `.design-staging/`.

## Detect Package Enhancement Before Discovery

Before asking discovery questions, inspect the fixed paths above for a complete or partial UI package for the same product. When one exists, use package enhancement mode. This is separate from implementation adoption mode: package enhancement revises these design artifacts; greenfield or phased migration describes how the product code adopts them.

Read the full same-product package and freeze it as the enhancement baseline. Record its exact files, stable IDs, content, artifacts, and decisions, then record the requested change as an explicit add/modify/remove delta. Ask only delta questions and conflicts created by that delta. Do not reopen untouched baseline decisions.

## Enhancement Staging

Seed staging from the frozen baseline by copying it into the run-specific staging directory before editing. Preserve untouched files, IDs, content blocks, artifacts, and decisions byte-for-byte where practical. Apply only accepted delta entries. Preserve `design-system.html` when the delta does not affect its rendered inputs; when accepted delta changes a token, primitive, variant, state, reusable element, parameter, or responsive/motion rule, rebuild the projection from the revised `design-system.md` and `ui-registry.json` without changing unrelated specimens. An accepted removal may remove only the named baseline material and the directly required references; it is not permission to regenerate or simplify the rest of the package.

Do not use a fresh-generation dynamic workflow in package enhancement mode. The baseline plus accepted delta is the source of truth. Focused reviewers may inspect the revised candidate, but they must not replace it with a newly generated package.

Validate the whole revised staged package, including unchanged artifacts and all cross-file parity checks. Compare it to the frozen baseline and require evidence that every accepted delta landed and every untouched item was preserved. Add the conditional enhancement non-regression gate from `visual-acceptance.md`; it applies only when an enhancement baseline exists.

## Inventory

Before drafting, list exact final-path files and other clearly superseded design-package artifacts for the same product, including any existing `docs/product/mockups/` HTML files, `docs/product/design/design-system.html`, any existing `docs/product/ui-registry.json`, and any retired `docs/product/ui-mockups.md` or `docs/product/page-ui-matrix.md` left over from an earlier package. Exclude `docs/product/archived/`, PRDs, architecture, stack decisions, research, test evidence, and ambiguous files. Leave ambiguous candidates untouched and report them. When archiving a superseded package, move the whole prior `docs/product/mockups/` directory — catalog included — alongside the other superseded files rather than leaving orphaned page HTML behind.

## Validate Then Ask

Validate the complete staged package first. Passing validation does not authorize overwrite, move, or archive. Show every exact final path that would be created or overwritten and every source-to-archive move. Continue only when the original request already authorized those exact mutations or the user explicitly approves the list.

If approval is absent, keep the staged package and all existing files unchanged.

## Publish

After approval:

1. Create `docs/product/archived/<YYYYMMDD-HHMMSS>-<product-slug>-design/` only when superseded artifacts exist.
2. Move only the approved superseded files into that new archive directory. Never overwrite an archive.
3. Apply the approved candidate disposition: for **Archive**, create the approved non-overwriting candidate archive path and move the candidate subtree there; for **Retain**, leave the candidate subtree in its exact run-staging path.
4. Rewrite staged `design-system.md`'s `Candidate evidence` to the actual final path and disposition, rebuild `design-system.html` when applicable, and revalidate the canonical staged package. If this revalidation fails, leave the existing published package untouched and report the already-authorized candidate move.
5. Move the revalidated staged artifacts to their final `docs/product/` paths. Move `ui-architecture.md` with `ui-registry.json`, and move `design-system.md` with `design-system.html`, in the same step.
6. Remove only the now-empty run staging directory. If the user approved retaining `visual-directions/`, leave that subtree and its parent run directory in place and report the exact path.
7. If any move fails, preserve every recoverable copy, stop, and report the exact state. Say plainly whether the published architecture and registry are still a matching pair, since a mismatched pair makes the contract check unreliable.

Never delete superseded files. Report published paths, archived paths, untouched ambiguous files, and whether any staged package is still awaiting approval.
