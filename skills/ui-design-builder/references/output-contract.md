# UI Design Output Contract

## Canonical Artifacts

- `docs/design/ui-design.md`: UI decisions, sources, gates, scores, and handoff.
- `docs/design/wireframes.html`: one approved structural projection of every PRD `UI-*` surface.
- `docs/design/ui-references/<run-id>/index.html`: the approved connected HiFi design-reference target when retention is authorized.
- `docs/design/design-system.md` and `docs/design/design-system.json`: present together only when the Design System Need Gate is `required`.

Legacy `docs/product/wireframes.html` and `docs/product/design-system.*` remain readable. New or revised artifacts publish under `docs/design/`; do not move an existing legacy artifact without exact owner authorization.

## `ui-design.md`

Use these exact headings:

```markdown
# UI Design Contract

## Source Product Definition

Product: [name]

PRD source: [path plus revision or SHA-256]

Architecture source: [path plus revision or SHA-256]

Stack source: [path plus revision or SHA-256]

Product Definition Approval: approved — [owner and date]

Stack Decision Checkpoint: approved — [owner and date]

## UI Design Intake

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Visual Preference Brief: [experience priority, guidance/control, density, layout, desired character, avoids, color/theme, typography/language, imagery/icons, references]

Direction mode: [one recommended direction / three comparable directions]

## Motion And Media Intent

Motion direction: [not_required / functional_only / expressive] — [owner or accepted recommendation]

| Intent ID | UI scope / region | Treatment | Purpose and trigger | Static / reduced-motion fallback | Generation route | Status |
| --- | --- | --- | --- | --- | --- | --- |
| MM-001 | [UI-* / region] | [none / image / motion / image + motion] | [purpose and trigger] | [fallback] | [none / existing asset / CSS-WAAPI / GSAP / Higgsfield MCP / other owner-approved] | [approved / deferred / blocked] |

## Wireframe Approval

Wireframe: [path plus SHA-256]

Frozen PRD basis: [path plus revision or SHA-256]

Copy Freeze: [approved / revision_requested / blocked]

Copy owner: [human owner]

Copy locale: [primary BCP 47 locale]

Copy approved on: [YYYY-MM-DD]

Responsive browser check: [matrix and result]

Wireframe references consulted: [sources and structural pattern adopted/rejected, or skip reason]

UI grading: [W1-W5, overall, findings, repair/re-review history or authorized capability record]

Wireframe score: [0-100]

Wireframe lowest dimension: [0-100]

Wireframe blocks: [none / named blocks]

Decision: [approved / revision_requested / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

## Style Integration

Design author: frontend-design

Selected direction: [VD-* ID, intent, confirmed REF-* / RP-* IDs]

Direction decision: [approved / selected / mixed-and-approved]

Direction decision owner: [human owner]

Direction decided on: [YYYY-MM-DD]

Candidate theme: [color, typography, spacing, shape, iconography, imagery, and motion rules used in the HiFi reference; not yet a frozen design-system pair]

Connected HiFi reference: [path plus SHA-256, routes, states, responsive scope]

## HiFi Review

Impeccable critique: [target, method, score, P0-P3 findings, evidence]

Impeccable audit: [target, score, accessibility/responsive/performance findings, evidence]

UI grading: [H1-H9, overall, H2/H4/H8 thresholds, advisories, defect ledger, repair/re-review history]

HiFi score: [0-100]

H2 score: [0-100]

H4 score: [0-100]

H8 score: [0-100]

HiFi lowest dimension: [0-100]

HiFi blocks or disputes: [none / named blocks or disputes]

## Visual Approval

Decision: [approved / revision_requested / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Approved target: [immutable path/version, SHA-256, routes/states, responsive scope, tolerance, allowed deviations]

## Design System Need Gate

Decision: [required / not_required / blocked]

Decision owner: [human owner]

Reason: [product-specific reason]

Replacement visual contract when not_required: [approved target plus ui-design.md, wireframes.html, and PRD]
```

Impeccable's heuristic scores and audit scores are diagnostic. Only the `W1`–`W5` and `H1`–`H9` rows use the thresholds in `ui-grading-rubric.md` to decide readiness.
