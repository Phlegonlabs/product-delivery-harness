# Design System Artifact Lifecycle

`sourceBindings.uiDesign.sha256` uses the canonical UI approval digest, not the raw file hash. Run `python "<ui-design-builder-skill-root>/scripts/ui_approval_digest.py" <ui-design.md>`; it excludes active derived pair/replacement linkage lines so linking the compiled pair does not invalidate its own input. All other source bindings use raw-file SHA-256.

Current design sources live under `docs/design/`. Draft a pair in one run-specific directory under `docs/design/.ui-staging/<run-id>/` and publish to:

- `docs/design/design-system.md`
- `docs/design/design-system.json`

Before drafting, read the approved `PRD.md`, `architecture.md`, `stack-decisions.md`, `docs/design/ui-design.md`, `docs/design/wireframes.html` as `wireframes/4`, approved HiFi target, and both design-system files when either exists. Legacy `docs/product/wireframes.html` and `docs/product/design-system.*` remain readable; do not move them merely to normalize paths without exact owner authorization. A legacy `design-system/1` pair is inspection-only and never grants new approval authority.

Freeze the source paths and current SHA-256 values in `sourceBindings`, Product Definition and Stack approvals, Wireframe Approval with approved Copy Freeze, Visual Approval, approved target, and Design System Need Gate. Product Definition is already published. Stage the wireframe, `ui-design.md`, HiFi target, and—when the gate is required—this pair together; publish only after the exact staged set passes its checkers. If any source changes, mark the draft stale and reconcile it before publication.

Publish or archive the Markdown and JSON files together. Never publish half a pair, silently overwrite a current pair, delete an old pair, or leave `ui-design.md` pointing to an archived source. Archive a superseded pair under `docs/design/archived/<YYYYMMDD-HHMMSS>-<run-id>/` only after disclosing the exact move and receiving authorization.

Generated Markdown writes preserve CAS bytes, file mode, and fsync durability. Compliant writers share a host-local destination lock/version token across the compare-to-commit window. The writer walks POSIX parents with no-follow dirfds and holds a Windows non-reparse parent handle without delete sharing; replacement is native and fail-closed if that binding or the destination token cannot be maintained.

UI references remain owned by `ui-design-builder`; Design System Compiler never republishes them. Product Definition artifacts remain under `docs/product/` and are never moved into design staging.

Use the UI builder’s publication-checkout workflow in `../../ui-design-builder/references/artifact-lifecycle.md`: final logical paths inside an exact-source Git checkout, upstream byte comparison before publication, and exact-byte verification after publication. A `.ui-staging` draft is not an approval identity.
