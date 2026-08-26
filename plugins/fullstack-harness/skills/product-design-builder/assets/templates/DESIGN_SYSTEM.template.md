# Design System: <product name>

## Overview

<One paragraph: product, platform, audience, implementation mechanism, and what this contract controls.>

This design system is the frontend implementation contract. It contains only the selected direction, tokens, primitives, recurring product components, states, responsive rules, accessibility rules, and source boundaries needed to build the product consistently.

## Machine-Readable Companion

Artifact: `docs/product/design-system.json`

`design-system.json` is the sole structured authority for token names, source paths, primitives, closed variant sets, product-component contracts, responsive verification, motion variants, and states. This Markdown file keeps the short human rationale and generated contract view.

The two files publish together. Edit structured fields in JSON, then run `scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --write`. Verify with `scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --require-filled`.

## Source Inputs

| Source | Path / URL | Role |
|---|---|---|
| PRD | <path> | product scope and requirements |
| PRD UI surface contract | <path and section> | screen structure, content, actions, states, and flows |
| Selected direction / brand | <VD-* direction ID or decision record> | approved visual input |

## Selected Visual Direction

- Status: <selected / provisional / assumed>
- Decision owner: <human product/design owner>
- Direction ID: <VD-R1-01 or consolidated direction ID>
- Approval or assumption: <record>
- Summary: <one paragraph describing the selected visual character and why it fits>

| DS ID | Implementation rule | Product or source basis | Upstream trace IDs |
|---|---|---|---|
| DS-001 | <specific hierarchy, density, typography, color, surface, icon/media, or motion rule> | <basis> | PRD-001, UX-001, UI-001 |

### Do / Don't

| Do | Don't |
|---|---|
| <specific implementation behavior> | <specific unsupported pattern> |

Do not copy candidate directions or the full `Check This` analysis into this document.

## Reference Influence

- Market evidence: <applicable MR-* IDs, or `none — no valid market evidence for the visual decision`>
- Visual references: <REF-* — direct URL or attachment label — inspected YYYY-MM-DD>
- Confirmed principles: <RP-* — Adopt / Adapt / Avoid — implementation consequence>
- Owner confirmation: <decision record and date>

Keep this trace short. Do not embed source images, copied assets, or the full extraction history.

## Token Decisions

Define only tokens the product uses. Raw values live only in the files declared by JSON `tokenSources`.

### Color

Palette basis: <brand or selected-direction reason>

| Pairing | Tokens | Computed contrast | Non-color cue or notes |
|---|---|---|---|
| <text on background / UI boundary / semantic state> | <token names> | <ratio from check_color_contrast.py> | <notes> |

### Typography

Family and scale rationale: <reason>

| Role | Token names | Weight | Computed line-height ratio | Usage |
|---|---|---|---|---|
| <display / heading / body / caption> | <font-size and line-height tokens> | <weight> | <ratio from check_type_scale.py> | <usage> |

### Space, Shape, Elevation, And Motion

<One short paragraph explaining the spacing rhythm, radius/elevation rule, and motion rule. Omit a category the product does not use. Exact values live in the generated JSON contract.>

## Primitive And Component Rules

Primitive rationale: <why the JSON layout, surface, typography, and control primitives cover the PRD UI surfaces>

Product-component rationale: <why each JSON product component recurs and belongs in the system>

Every JSON `requiredContentOrder` entry is a never-drop field. It renders in that order wherever the component appears. The downstream Content contract conformance gate checks it.

Do not duplicate the machine-owned primitive, variant, component, composition, or state inventory here.

## Responsive Rules

- Responsive set: <JSON viewports or sizeClasses and why this smallest set covers the product>
- Reflow rule: <what moves, stacks, or resizes>
- Never-drop content: <what remains visible>
- Platform rule: <web, native, or desktop convention>

## State And Interaction Rules

Every screen implements every JSON `stateMatrix` entry or records `<state>: n/a — <reason>` in `PRD.md`.

<Concise rules for focus, hover where applicable, active, loading, disabled, selected, expanded, validation, retry, and reduced motion.>

## Accessibility Rules

- Focus: <visible focus and order>
- Keyboard: <path or n/a>
- Labels and announcements: <accessible names, errors, and status>
- Targets: <minimum target size>
- Contrast: <required level>
- Reduced motion: <fallback>

## Source And Enforcement Rules

- Raw colors, dimensions, and motion values appear only in JSON `tokenSources`.
- Reusable control and surface definitions appear only in JSON `primitiveSources`.
- Pages use registered tokens, primitives, variants, and product components.
- If the contract cannot express a required UI, update the design system before implementing the page.

## Assumptions

- <assumption>

## Open Questions

- <question>
