# UI Design Contract

UI contract: ui-design/3

## Source Product Definition

Product: [name]

PRD source: [repo-relative path @ sha256:<lowercase sha256>]

Architecture source: [repo-relative path @ sha256:<lowercase sha256>]

Stack source: [repo-relative path @ sha256:<lowercase sha256>]

Product Definition Approval: approved

Stack Decision Checkpoint: approved

## UI Design Intake

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Visual Preference Brief: [experience priority, guidance/control, density, layout, desired character, avoids, color/theme, typography/language, imagery/icons, references]

Direction mode: [three comparable directions / one recommended direction / one recommended direction (mvp)]

### Design Brief

- Purpose and scope: [link the approved PRD page, audience, primary job and non-goals; do not duplicate product requirements]
- Page-purpose mapping: [affected UI IDs by page purpose/profile, with the constraints that bind them, typography/headline, density, motion intent, justified exceptions, and the choices left to the design author; existing accepted decisions may be linked. Point to the PRD UI Surface Contract instead of repeating its per-page requirements.]
- Reference response: [owner answer and source/date; supplied / explicitly none / not supplied; name any unavailable material separately]
- Reference lessons: [source URL/file/product and relevant page/region; useful composition/typography/motion role, what to learn, what to avoid and affected UI IDs; an avoid example needs a concrete reason; link inspected REF-* and proposed/confirmed RP-* records]
- Visual constraints and avoid rules: [concrete layout/spacing, typography/language (chosen font pairing, avoided default faces and why), color/theme, imagery/icon and motion constraints; distinguish owner decisions, agent proposals and unresolved items]
- Detailed decisions: [link Style Integration/selected VD-* and applicable MM-* records as they become available; identify concrete visual features from the selected study and their capture/region, plus the existing font/asset sources; link the confirmed journey set and `journeys.html` @ sha256; do not create another token table or motion specification]

## Motion And Media Intent

Motion direction: [not_required / functional_only / expressive] — [owner or accepted recommendation]

| Intent ID | UI scope / region | Treatment | Purpose | Trigger | Draft prompt | Source | Static / reduced-motion fallback | Generation route | Status | Generation status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MM-001 | UI-001 / hero | image + motion | [purpose] | [trigger] | [draft prompt] | [owner decision or source] | [fallback] | [none / existing asset / CSS-WAAPI / Motion / GSAP / Three.js / native-framework / authorized provider] | [approved / deferred] | deferred |

### Frontend Design Usage

Frontend Design source: docs/design/<folder>/SKILL.md @ sha256:[observed source digest]

| Stage | Skill | Artifact | Application |
| --- | --- | --- | --- |
| direction | frontend-design @ sha256:[observed source digest] | docs/design/directions/round-1/primary.png @ sha256:[capture digest] | [alternatives and concrete design choices] |
| hifi | frontend-design @ sha256:[observed source digest] | docs/design/ui-references/<run-id>/index.html @ sha256:[candidate digest] | [typography, palette, layout and self-review applied] |

## Style Integration

Design author: frontend-design

Selected direction: [VD-* ID, intent, confirmed REF-* / RP-* IDs]

Direction decision: [approved / selected / mixed-and-approved / modified-and-approved / deferred to Visual Approval (mvp)]

Direction decision owner: [human owner; omitted when deferred to Visual Approval (mvp)]

Direction decided on: [YYYY-MM-DD; omitted when deferred to Visual Approval (mvp)]

Candidate theme: [color, typography, spacing, shape, iconography, imagery, and motion rules used in the HiFi reference; not yet a frozen design-system pair]

Review medium: HTML projection only

Connected HiFi reference: [repo-relative path @ sha256:<lowercase sha256>]

### Direction comparison

| Direction | UI surface | State | Target | Scenario | Content basis | Screenshot | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VD-R1-01 | UI-001 | ready | 390 | primary | [frozen copy and representative data] | docs/design/directions/round-1/primary.png @ sha256:[hash] | [specific hierarchy and type decisions] |
| VD-R1-01 | UI-001 | ready | 1200 | stress | [bounded dense data from the same copy contract] | docs/design/directions/round-1/dense.png @ sha256:[hash] | [how density and alignment hold up] |

### Direction studies

| Direction | Study | Author | Self-check by | Self-check |
| --- | --- | --- | --- | --- |
| VD-R1-01 | docs/design/directions/round-1/vd-01.html @ sha256:[hash] | [frontend author identity] | [same identity] | pass |

### Platform rules

| Platform | Navigation and input | Typography | Icons | Density and layout | Feedback and motion | Native proof | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| web | [navigation, keyboard, focus, hover] | [roles, loading, CJK fallback] | [selected family and fallback] | [task density and responsive layout] | [approved functional feedback] | not_applicable | [official URLs and inspection dates] |
| ios | [native navigation, back, sheets, keyboard] | [system text styles and Dynamic Type reasoning] | [SF Symbols or reasoned alternative] | [safe areas and touch density] | [system feedback and reduced motion] | required before expansion | [official URLs, inspection dates, OS range] |

### Required motion evidence

| Intent ID | UI scope / region | Trigger observed | End state observed | Normal-motion evidence | Reduced-motion evidence | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| MM-001 | UI-001 / hero | [the approved MM trigger, verbatim] | [observed end state] | PASS — evidence=[repo-relative evidence path] @ sha256:[hash] | PASS — evidence=[repo-relative evidence path] @ sha256:[hash] | PASS |

## HiFi Review

[Grading summary: grader count and lenses, medians and disputed dimensions, defect ledger path, and the repair/re-review outcome or the blocked owner decision]

Impeccable critique: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

Impeccable audit: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

UI grading: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

HiFi surface check: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

Intermediate width check: [PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256] / not_applicable — no adjacent approved web viewport widths]

HiFi score: [0-100]

H2 score: [0-100]

H4 score: [0-100]

H5 score: [80-100 for Visual Approval]

H7 score: [80-100 for Visual Approval]

H8 score: [0-100]

H9 score: [80-100 for Visual Approval]

HiFi lowest dimension: [0-100]

HiFi blocks or disputes: [none / named blocks or disputes]

## Visual Approval

Decision: [approved / revision_requested / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Approved target: [repo-relative path @ sha256:<lowercase sha256>; scope=surfaces=[{"id":"UI-001","route":"/path","states":["ready"]}]|routes=["/path"]|states=["ready"]|responsive={"kind":"viewports","targets":[390,768,1200]}|tolerance="exact"|allowedDeviations=[]|captureMode=hosted-browser]

Covers direction: [yes — only when Direction decision is deferred to Visual Approval (mvp)]

## Design System Need Gate

Decision: [required / not_required / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Reason: [product-specific reason]

Package action: [compile / update / reuse; omitted for an mvp not_required gate]

Existing design-system pair disposition: [none|retain|retire — reason; owner=<human>; decided=<YYYY-MM-DD>]

Replacement visual contract when not_required: target=[path @ sha256:hash]; ui-design=[path @ sha256:canonical-ui-approval-digest]; prd=[path @ sha256:hash]

Compiled design system pair: [markdown path @ sha256:<lowercase sha256> and json path @ sha256:<lowercase sha256>]
