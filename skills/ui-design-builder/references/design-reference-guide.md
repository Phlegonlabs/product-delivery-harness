# Design Reference Guide

Use this guide after UI Design Intake when the owner supplies a screenshot, image, URL, Figma view, named product, or brand reference, or when `frontend-design` needs a current public reference to ground a direction.

## Authority

References are evidence, not product authority. `PRD.md` owns product behavior, approved `wireframes.html` owns reviewed structure, and `ui-design.md` owns the selected direction. A reference cannot add a route, control, state, claim, or stack requirement.

Treat a supplied reference as `design inspiration` unless the owner explicitly requests page-faithful conformance and names the scope and tolerance.

## Records

Record every inspected source with a stable `REF-*` ID:

```text
REF-001
Source: [URL, file, screenshot, Figma view, or named product]
Publisher / owner: [name]
Retrieved or supplied: [YYYY-MM-DD]
Inspected scope: [page, region, state, or mechanic]
Visible evidence: [what was actually observed]
Authority: design inspiration | page-faithful target
```

Turn useful observations into proposed `RP-*` principles:

```text
RP-001
Source: REF-001
Disposition: Adopt | Adapt | Avoid
Principle: [one concrete rule]
Scope: [UI-* surfaces or regions]
Reason: [product-specific reason]
Status: proposed | confirmed | rejected
```

Show the proposed Adopt / Adapt / Avoid set to the human owner and end the turn. Do not design from supplied references until the owner confirms the principles.

## Direction Records

`frontend-design` creates directions only after the Visual Preference Brief and any supplied-reference principles are confirmed. Give each direction a versioned `VD-R<round>-<number>` ID.

- When the owner states a clear direction, create one direction, normally `VD-R1-01`.
- When the owner asks to compare or remains unsure, create exactly three materially different directions over the same frozen screens, states, and responsive set.
- A rejected set produces a complete new round; do not append a fourth direction to the old round.

Each direction records product fit, visual rules, confirmed `REF-*` and `RP-*` evidence, tradeoffs, avoid rules, and its relationship to the approved component foundation and styling approach. A current public reference may support a direction only after it has been inspected. Market evidence (`MR-*`) and visual evidence (`REF-*`) remain separate.

Impeccable does not generate directions. After `frontend-design` creates the connected HiFi candidate, Impeccable critiques and audits it under `ui-design-pass.md`, and the PRD-bound H1-H9 rubric remains the approval score.
