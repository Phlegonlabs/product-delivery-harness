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

The approved Product Definition is already published and remains under `docs/product/`; it is never moved into UI staging. Before publication, run `../scripts/check_ui_design_contract.py --repo-root <repository-root> --ui-design <staged ui-design.md> --prd <approved PRD.md> --wireframes <staged wireframes.html> --hifi <connected HiFi target> --require-filled --require-wireframe-approved --require-visual-approved`. When the Design System Need Gate is `required`, add `--design-system-markdown <staged design-system.md> --design-system-registry <staged design-system.json>` and stage the approved `design-system/2` pair in that same publication set. Do not publish a partial UI stage.

## Publish And Archive

Show the exact source, destination, overwrite, and archive paths before publication. Product, Wireframe, Visual, and Design System approvals do not authorize filesystem changes. Obtain exact publication authorization when it is not already present.

When an approved artifact supersedes a current UI artifact, archive the old file or complete pair under `docs/design/archived/<YYYYMMDD-HHMMSS>-<run-id>/` and update every live pointer. Move; never delete. Do not move a legacy `docs/product/` UI artifact merely to normalize its location without exact owner approval. New work may publish alongside a legacy artifact only when `ui-design.md` explicitly names which one is authoritative and the legacy one is marked superseded.

The design-system pair publishes and archives atomically. Legacy `design-system/1` files remain inspection-only and never grant new approval authority. A `not_required` decision does not silently remove an existing pair; explicitly retain or retire it with owner approval.
