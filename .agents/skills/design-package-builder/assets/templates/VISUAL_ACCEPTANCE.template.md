# Visual Acceptance: <product name>

## Review Gates

| TEST ID | Gate | Required | Upstream trace IDs | Expected Signal | Evidence |
|---|---|---|---|---|---|
| TEST-VIS-001 | Design system conformance | yes | DS-* | Components use approved tokens and variants | screenshot / code review |
| TEST-VIS-002 | Builder UX Direction conformance | when a Builder UX Direction exists | UX-*, DS-* | Selected decisions are implemented; provisional or assumed decisions and conflicts remain explicit | source review / design review |
| TEST-VIS-003 | Page UI conformance | yes | UI-*, DS-* | Implemented page matches mockup source | screenshot / trace |
| TEST-VIS-004 | Responsive behavior | yes | UI-* | No overflow or broken hierarchy at required breakpoints | screenshot |
| TEST-VIS-005 | State coverage | yes | UI-*, PRD-* | Required loading/empty/error/disabled states exist | screenshot / test |
| TEST-VIS-006 | Accessibility basics | yes | UX-*, UI-* | Focus, contrast intent, labels, keyboard path checked | audit / screenshot |
| TEST-VIS-007 | Icon system conformance | yes | DS-* | Icons use the approved source, tokens, semantics, labels, and documented exceptions | screenshot / code review |
| TEST-VIS-008 | Motion system conformance | yes | DS-*, UI-* | Motion uses approved purpose, tokens, choreography, responsive behavior, and reduced-motion fallbacks | live demo / code review |
| TEST-VIS-009 | Motion performance | yes | DS-*, UI-* | Critical content is static-first; routine motion avoids layout-heavy properties and does not block interaction | performance trace / live demo |
| TEST-VIS-010 | Taste and anti-slop review | yes | DS-* | The taste statement is visible, product-specific cues recur, and unsupported AI-UI pattern clusters are absent | screenshot / checklist |
| TEST-VIS-011 | Rendered visual review loop | when visual artifacts or an implementation exist | UI-*, DS-* | Required breakpoint renders were critiqued; the highest-impact failure was repaired and rechecked | before/after screenshots / review notes |
| TEST-VIS-012 | Spec-only review path | when rendered visuals do not exist | UI-*, DS-* | The Markdown package was checked for taste, hierarchy, container and border purpose, responsive intent, and internal consistency; render evidence is marked unavailable and no visual-verification claim is made | text review notes |
| TEST-VIS-013 | Content specificity | yes | PRD-*, UI-* | Every visible region preserves exact wording or a bounded display contract; generic placeholder copy is absent | product source / mockup review |
| TEST-VIS-014 | Container and border purpose | yes | DS-*, UI-* | Regions default to open layouts; every visible border, frame, rail, or elevation has a named hierarchy, interaction, state, data, or accessibility purpose | screenshot / border inventory / design review |
| TEST-VIS-015 | Landing-page simplicity | when applicable | PRD-*, UI-* | First viewport has one clear message and primary action; each section has one job; secondary detail is deferred | content review / screenshot |
| TEST-VIS-016 | Media and motion traceability | when applicable | UI-*, DS-* | Every relevant region labels image/media and motion as required, optional, or none with a purpose and fallback | design system / mockup review |

## Page Acceptance

| UI ID | Page / route | Source | TEST IDs | Required evidence | Status |
|---|---|---|---|---|---|
| UI-001 | <route> | <source> | TEST-VIS-001 | <evidence> | planned |

## Known Visual Risks

| Risk | Impact | Decision |
|---|---|---|
| <risk> | <impact> | <decision> |
