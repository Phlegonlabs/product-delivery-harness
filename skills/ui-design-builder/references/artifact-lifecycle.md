# UI Design Artifact Lifecycle

## Detect Existing UI Design

Before drafting, read the approved Product Definition package and inspect, in order:

- `docs/design/ui-design.md`;
- `docs/design/wireframes.html`;
- `docs/design/ui-references/`;
- `docs/design/design-system.md` and `docs/design/design-system.json`; and
- legacy `docs/product/wireframes.html` and `docs/product/design-system.*` when present.

If a staged UI package exists, ask whether to resume, publish, or discard it before starting a competing draft. Never delete or silently replace an existing UI artifact.

## Locations

Stage one run under `docs/design/.ui-staging/<run-id>/`. New canonical publish locations are:

- `docs/design/ui-design.md`;
- `docs/design/wireframes.html`;
- `docs/design/ui-references/<run-id>/index.html` when retention is approved; and
- `docs/design/design-system.md` plus `docs/design/design-system.json` when required.

The approved Product Definition remains under `docs/product/` and is never moved into UI staging.

## Publish And Archive

Show the exact source, destination, overwrite, and archive paths before publication. Product, Wireframe, Visual, and Design System approvals do not authorize filesystem changes. Obtain exact publication authorization when it is not already present.

When an approved artifact supersedes a current UI artifact, archive the old file or complete pair under `docs/design/archived/<YYYYMMDD-HHMMSS>-<run-id>/` and update every live pointer. Move; never delete. Do not move a legacy `docs/product/` UI artifact merely to normalize its location without exact owner approval. New work may publish alongside a legacy artifact only when `ui-design.md` explicitly names which one is authoritative and the legacy one is marked superseded.

The design-system pair publishes and archives atomically. A `not_required` decision does not silently remove an existing pair; explicitly retain or retire it with owner approval.
