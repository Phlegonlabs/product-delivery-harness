# Design System Artifact Lifecycle

Current design sources live under `docs/design/`. Draft a pair in one run-specific directory under `docs/design/.ui-staging/<run-id>/` and publish to:

- `docs/design/design-system.md`
- `docs/design/design-system.json`

Before drafting, read the approved `PRD.md`, `architecture.md`, `stack-decisions.md`, `docs/design/ui-design.md`, approved HiFi target, and both design-system files when either exists. Legacy `docs/product/wireframes.html` and `docs/product/design-system.*` remain readable; do not move them merely to normalize paths without exact owner authorization. A legacy `design-system/1` pair is inspection-only and never grants new approval authority.

Freeze the source paths and current SHA-256 values in `sourceBindings`, Product Definition and Stack approvals, HiFi completeness with sourced copy, Visual Approval, approved target, and Design System Need Gate. Product Definition is already published. Stage `ui-design.md`, HiFi target, and—when the gate is required—this pair together; publish only after the exact staged set passes its checkers. If any source changes, mark the draft stale and reconcile it before publication.

Publish or archive the Markdown and JSON files together. Never publish half a pair, silently overwrite a current pair, delete an old pair, or leave `ui-design.md` pointing to an archived source. Archive a superseded pair under `docs/design/archived/<YYYYMMDD-HHMMSS>-<run-id>/` only after disclosing the exact move and receiving authorization.

UI references remain owned by `ui-design-builder`; Design System Compiler never republishes them. Product Definition artifacts remain under `docs/product/` and are never moved into design staging.

The derived `docs/design/design-system-preview.html` follows the pair's authorized staging, publication and archive scope. For `design-system/4` it is also rendered from the bound HiFi bytes, so a HiFi change makes it stale too. Run `render_design_system_preview.py --check` before and after its transfer. The UI publication check with `--design-system-required` also requires the exact derived bytes. A missing or stale preview blocks completion for a new or revised pair. Preserve prior previews when superseding them under the same explicit archive rules. Never change validated schema-5 or approved legacy wireframe bytes to display formal tokens.

Use the UI builder’s publication-checkout workflow in `../../ui-design-builder/references/artifact-lifecycle.md`: final logical paths inside an exact-source Git checkout, upstream byte comparison before publication, and exact-byte verification after publication. A `.ui-staging` draft is not an approval identity.
