# Design Reference Guide

Use this guide after UI Design Intake when the owner supplies a screenshot, image, URL, Figma view, named product, or brand reference, or when `frontend-design` needs a current public reference to ground a direction.

## Authority

References are evidence, not product authority. `PRD.md` owns product behavior, approved `wireframes.html` owns reviewed structure, and `ui-design.md` owns the selected direction. A reference cannot add a route, control, state, claim, or stack requirement.

Treat a supplied reference as `design inspiration` unless the owner explicitly requests page-faithful conformance and names the scope and tolerance.

Link supplied or inspected sources to the existing Design Brief with what the owner wants to learn, avoid and apply to specific UI surfaces. Keep owner preferences distinct from the agent's observations and proposed principles. A missing or inaccessible image, website or Figma view remains uninspected; record that limitation instead of inventing `REF-*` observations. A supplied reference is not permission to clone a page or change product/stack decisions. An explicit `no references` answer uses the research route below; do not treat an unanswered question as that answer.

## Proactive Reference Research

For a new visual scope, or a revised one without supplied references, inspect a few current public pages that match the product's task and platform—not a generic color collection. Curated candidate directories include [Astro themes](https://astro.build/themes/), [Tailwind Plus UI blocks](https://tailwindcss.com/plus/ui-blocks/marketing) (paid reuse—verify the license), [application UI blocks](https://tailwindcss.com/plus/ui-blocks/application-ui), [Codrops](https://tympanus.net/codrops/), [Uiverse](https://uiverse.io/), and [Open Props](https://open-props.style/). A directory entry is not evidence by itself: inspect the actual page and relevant desktop/mobile state before recording it. Record every inspected source as `REF-*` and its proposed `Adopt | Adapt | Avoid` rule as `RP-*`; never install a template or dependency without the approved stack's explicit component/source decision and license review.

Research composition, typography, spacing, information density, responsive behavior, and control treatment. Two references may support one clear direction. If the owner is uncertain or explicitly asks to compare, use the existing three-distinct-directions gate; changing only an accent color is not a distinct direction. A structural finding returns to wireframe review. Cosmetic direction work belongs after Wireframe Validation.

For each useful reference, record whole-template adaptation, selected-component reuse or custom implementation in the RP principle, with stack compatibility, license/cost and maintenance implications. A reference never selects Tailwind or a component library by implication. On native surfaces, inspect platform-native patterns and official guidance instead of treating Web CSS examples as native components. If browsing is declined, unavailable or unsafe for confidential inputs, record the limitation and use inspectable supplied/local references; never invent a source or claim visual inspection from search snippets.

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

Use the representative studies and `### Direction comparison` table in `ui-design-pass.md` before asking the owner to select. The same primary and stress cases appear in every direction with unchanged content. Reference moodboards and written style labels do not replace rendered product studies. Preserve prior rounds as non-canonical evidence; only the current complete round belongs in the active table.

Impeccable does not generate directions. After `frontend-design` creates the connected HiFi candidate, Impeccable critiques and audits it under `ui-design-pass.md`, and the PRD-bound H1-H9 rubric remains the approval score.
