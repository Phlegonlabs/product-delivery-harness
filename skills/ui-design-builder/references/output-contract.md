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

PRD source: [repo-relative path @ sha256:<lowercase sha256>]

Architecture source: [repo-relative path @ sha256:<lowercase sha256>]

Stack source: [repo-relative path @ sha256:<lowercase sha256>]

Product Definition Approval: approved — [owner and date]

Stack Decision Checkpoint: approved — [owner and date]

## UI Design Intake

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Visual Preference Brief: [experience priority, guidance/control, density, layout, desired character, avoids, color/theme, typography/language, imagery/icons, references]

Direction mode: [one recommended direction / three comparable directions]

## Motion And Media Intent

Motion direction: [not_required / functional_only / expressive] — [owner or accepted recommendation]

| Intent ID | UI scope / region | Treatment | Purpose | Trigger | Draft prompt | Source | Static / reduced-motion fallback | Generation route | Status | Generation status |
| --- | --- | --- | --- | --- | --- | --- |
| MM-001 | [UI-* / region] | [none / image / motion / image + motion] | [purpose and trigger] | [fallback] | [none / existing asset / CSS-WAAPI / GSAP / Higgsfield MCP / other owner-approved] | [approved / deferred] |

## Wireframe Approval

Wireframe: [repo-relative path @ sha256:<lowercase sha256>]

Frozen PRD basis: [repo-relative path @ sha256:<lowercase sha256>]

Copy Freeze: [approved / revision_requested / blocked]

Copy owner: [human owner]

Copy locale: [primary BCP 47 locale]

Copy approved on: [YYYY-MM-DD]

Responsive browser check: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

Wireframe references consulted: [sources and structural pattern adopted/rejected, or skip reason]

UI grading: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

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

Connected HiFi reference: [repo-relative path @ sha256:<lowercase sha256>]

The connected HiFi HTML must pass the generic self-contained surface check: no active external resources, network or executable APIs, remote forms, base/meta refresh navigation, CSS imports, or external scripts. This check does not apply the wireframe schema or canonical reviewer shell.

## HiFi Review

Impeccable critique: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

Impeccable audit: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

UI grading: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

HiFi browser check: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

HiFi score: [0-100]

H2 score: [0-100]

H4 score: [0-100]

H8 score: [0-100]

HiFi lowest dimension: [0-100]

HiFi blocks or disputes: [none / named blocks or disputes]

Each PASS evidence file is a `ui-evidence/1` JSON object with exactly `schema`, `check`, `result`, `reviewedArtifact`, `execution`, and `owner`. `check` is one of `wireframe-browser`, `wireframe-grading`, `hifi-impeccable-critique`, `hifi-impeccable-audit`, `hifi-grading`, or `hifi-browser`; `reviewedArtifact` carries the exact current path and SHA-256; `execution` carries `command`, `method`, and a past timezone-aware `executedAt`; and `owner` names a human.

## Visual Approval

Decision: [approved / revision_requested / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Approved target: [repo-relative path @ sha256:<lowercase sha256>; scope=surfaces=<...>|routes=<...>|states=<...>|responsive=<kind and ordered targets>|tolerance=<...>|allowedDeviations=<...>|captureMode=<hosted-browser|browser-extension|native|desktop>]

## Design System Need Gate

Decision: [required / not_required / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Reason: [product-specific reason]

Replacement visual contract when not_required: target=[path @ sha256:hash]; ui-design=[path @ sha256:hash]; wireframe=[path @ sha256:hash]; prd=[path @ sha256:hash]

Compiled design system pair: [markdown path @ sha256:<lowercase sha256> and json path @ sha256:<lowercase sha256>]

Use `Compiled design system pair` only for `required` and the replacement field only for `not_required`. `blocked` cannot pass publication.
```

Impeccable's heuristic scores and audit scores are diagnostic. Only the `W1`–`W5` and `H1`–`H9` rows use the thresholds in `ui-grading-rubric.md` to decide readiness.
