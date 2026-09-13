# Design System Artifact Lifecycle

Current design sources live under `docs/design/`. Draft a pair in one run-specific directory under `docs/design/.ui-staging/<run-id>/` and publish to:

- `docs/design/design-system.md`
- `docs/design/design-system.json`

Before drafting, read the approved `PRD.md`, `architecture.md`, `stack-decisions.md`, `docs/design/ui-design.md`, `docs/design/wireframes.html`, approved HiFi target, and both design-system files when either exists. Legacy `docs/product/wireframes.html` and `docs/product/design-system.*` remain readable; do not move them merely to normalize paths without exact owner authorization.

Freeze the source paths and SHA-256 values, Product Definition and Stack approvals, Wireframe Approval, Visual Approval, approved target, and Design System Need Gate. If any source changes, mark the draft stale and reconcile it before publication.

Publish or archive the Markdown and JSON files together. Never publish half a pair, silently overwrite a current pair, delete an old pair, or leave `ui-design.md` pointing to an archived source. Archive a superseded pair under `docs/design/archived/<YYYYMMDD-HHMMSS>-<run-id>/` only after disclosing the exact move and receiving authorization.

UI references remain owned by `ui-design-builder`; Design System Compiler never republishes them. Product Definition artifacts remain under `docs/product/` and are never moved into design staging.
