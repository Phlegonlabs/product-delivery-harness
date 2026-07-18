# Visual Acceptance: <product name>

## Review Gates

| Gate | Required | Expected Signal | Evidence |
|---|---|---|---|
| Design system conformance | yes | Components use approved tokens and variants | screenshot / code review |
| Page UI conformance | yes | Implemented page matches mockup source | screenshot / trace |
| Responsive behavior | yes | No overflow or broken hierarchy at required breakpoints | screenshot |
| State coverage | yes | Required loading/empty/error/disabled states exist | screenshot / test |
| Accessibility basics | yes | Focus, contrast intent, labels, keyboard path checked | audit / screenshot |
| Icon system conformance | yes | Icons use the approved source, tokens, semantics, labels, and documented exceptions | screenshot / code review |
| Motion system conformance | yes | Motion uses approved purpose, tokens, choreography, responsive behavior, and reduced-motion fallbacks | live demo / code review |
| Motion performance | yes | Critical content is static-first; routine motion avoids layout-heavy properties and does not block interaction | performance trace / live demo |
| Taste and anti-slop review | yes | The taste statement is visible, product-specific cues recur, and unsupported AI-UI pattern clusters are absent | screenshot / checklist |
| Rendered visual review loop | when visual artifacts or an implementation exist | Required breakpoint renders were critiqued; the highest-impact failure was repaired and rechecked | before/after screenshots / review notes |
| Spec-only review path | when rendered visuals do not exist | The Markdown package was checked for taste, hierarchy, container and border purpose, responsive intent, and internal consistency; render evidence is marked unavailable and no visual-verification claim is made | text review notes |
| Content specificity | yes | Every visible region preserves exact wording or a bounded display contract; generic placeholder copy is absent | product source / mockup review |
| Container and border purpose | yes | Regions default to open layouts; every visible border, frame, rail, or elevation has a named hierarchy, interaction, state, data, or accessibility purpose | screenshot / border inventory / design review |
| Landing-page simplicity | when applicable | First viewport has one clear message and primary action; each section has one job; secondary detail is deferred | content review / screenshot |
| Media and motion traceability | when applicable | Every relevant region labels image/media and motion as required, optional, or none with a purpose and fallback | design system / mockup review |

## Page Acceptance

| Page / route | Source | Required evidence | Status |
|---|---|---|---|
| <route> | <source> | <evidence> | planned |

## Known Visual Risks

| Risk | Impact | Decision |
|---|---|---|
| <risk> | <impact> | <decision> |
