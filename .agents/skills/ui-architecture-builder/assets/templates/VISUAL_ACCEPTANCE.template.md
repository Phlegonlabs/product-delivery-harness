# Visual Acceptance: <product name>

## Review Gates

| TEST ID | Gate | Required | Upstream trace IDs | Expected Signal | Evidence |
|---|---|---|---|---|---|
| TEST-VIS-001 | Design system conformance | yes | DS-* | Components use approved tokens and variants | screenshot / code review |
| TEST-VIS-002 | Builder UX Direction conformance | when a Builder UX Direction exists | UX-*, DS-* | Selected decisions are implemented; provisional or assumed decisions and conflicts remain explicit | source review / design review |
| TEST-VIS-003 | Page UI conformance | yes | UI-*, DS-* | Implemented page matches mockup source | screenshot / trace |
| TEST-VIS-004 | Responsive behavior | yes | UI-* | No overflow or broken hierarchy at required breakpoints | screenshot |
| TEST-VIS-005 | State coverage | yes | UI-*, PRD-* | Required loading/empty/error/disabled states exist | screenshot / test |
| TEST-VIS-006 | Accessibility basics | yes | UX-*, UI-* | Focus, computed WCAG 2.2 AA contrast ratio for every recorded text/UI color pairing, computed line-height ratio for every typography role (not just visual intent), labels, keyboard path checked | audit / screenshot |
| TEST-VIS-007 | Icon system conformance | yes | DS-* | Icons use the approved source, tokens, semantics, labels, and documented exceptions | screenshot / code review |
| TEST-VIS-008 | Motion system conformance | yes | DS-*, UI-* | Motion records mechanism separately from approved purpose, uses registered tokens and choreography, inherits the global reduced-motion configuration or a justified exception, and covers every in-scope non-hero pattern | live demo / code review |
| TEST-VIS-009 | Motion performance | yes | DS-*, UI-* | Critical content is static-first; routine motion avoids layout-heavy properties and does not block interaction | performance trace / live demo |
| TEST-VIS-010 | Taste and anti-slop review | yes | DS-* | The taste statement is visible, product-specific cues recur, and unsupported AI-UI pattern clusters are absent | screenshot / checklist |
| TEST-VIS-011 | Rendered visual review loop | when visual artifacts or an implementation exist | UI-*, DS-* | Required breakpoint renders were critiqued; the highest-impact failure was repaired and rechecked | before/after screenshots / review notes |
| TEST-VIS-012 | Spec-only review path | when rendered visuals do not exist | UI-*, DS-* | The Markdown package was checked for taste, hierarchy, container and border purpose, responsive intent, and internal consistency; render evidence is marked unavailable and no visual-verification claim is made | text review notes |
| TEST-VIS-013 | Content specificity | yes | PRD-*, UI-* | Every visible region preserves exact wording or a bounded display contract; generic placeholder copy is absent | product source / mockup review |
| TEST-VIS-014 | Container and border purpose | yes | DS-*, UI-* | Regions default to open layouts; every visible border, frame, rail, or elevation has a named hierarchy, interaction, state, data, or accessibility purpose | screenshot / border inventory / design review |
| TEST-VIS-015 | Landing-page simplicity | when applicable | PRD-*, UI-* | First viewport has one clear message and primary action; each section has one job; secondary detail is deferred | content review / screenshot |
| TEST-VIS-016 | Media and motion traceability | when applicable | UI-*, DS-* | Every relevant region labels image/media and motion as required, optional, or none with a purpose and fallback | design system / mockup review |
| TEST-VIS-017 | Component architecture conformance | yes | DS-*, UI-* | Every component maps to exactly one layer, composition runs downward only, and pages compose primitives instead of introducing one-off spacing, surfaces, or colors | component inventory / code review |
| TEST-VIS-018 | Registry conformance | yes | DS-*, UI-* | Every primitive, variant, motion variant, product component, and recipe used exists in `ui-registry.json`; no raw values, arbitrary variants, or page-local controls appear outside the token layer | registry diff / code review |
| TEST-VIS-019 | Page recipe conformance | yes | UI-*, DS-* | Each route matches its recipe's section order, container, density, allowed surfaces, and primary action, and contains none of its forbidden patterns | recipe diff / screenshot |
| TEST-VIS-020 | Content contract conformance | yes | PRD-*, UI-* | Every rendered product component keeps its required content order and never-drop fields, and respects limits, formats, empty, and long-content rules | content review / screenshot |
| TEST-VIS-021 | State matrix coverage | yes | UI-*, PRD-* | Every required state is implemented or marked `n/a` with a reason, at every required viewport | screenshot / test |
| TEST-VIS-022 | Contract check | yes | DS-*, UI-* | The UI contract check passes: no raw colors or dimensions outside the token layer, no inline layout styles, sections wrap approved containers, motion uses registered variants | project UI contract check / CI run |
| TEST-VIS-023 | Catalog completeness | yes | DS-* | `mockups/catalog.html` shows every registry entry under realistic content at every required viewport and in reduced motion; every catalog entry exists in the registry | catalog review |
| TEST-VIS-024 | No-JavaScript path | when server-rendered content exists | UI-*, ARCH-* | Content the route must render server-side is present and readable with JavaScript disabled | screenshot with JS disabled |
| TEST-VIS-025 | Enhancement non-regression | when enhancing an existing same-product UI package | UI-*, DS-*, preserved upstream TEST-* | Every accepted add/modify/remove delta is present; untouched baseline IDs, content, artifacts, decisions, and upstream TEST identities are preserved; the complete revised package passes validation | baseline-to-staged diff / full package validation |
| TEST-VIS-026 | Rendered design-system parity | yes | DS-*, UI-* | `docs/product/design/design-system.html` renders every reusable element category in scope; each specimen uses the exact fields `IDs`, `Parameters`, `States`, `Responsive`, `Accessibility`, `Use`, and `Do not use`; `IDs` includes valid token, primitive/component, and variant IDs as applicable; applicable motion/reduced-motion behavior agrees with `design-system.md` and `ui-registry.json` | rendered showcase review / source-to-projection diff |
| TEST-VIS-027 | HTML direction comparison and approval | when Frontend Design Preference & HTML Exploration is used | UI-*, DS-* | Exactly two or three materially different, complete HTML directions represent the same one or two authorized screens; the human comparison, consolidated selected path, and explicit selected-HTML approval are recorded | candidate renders / Ask User record / approval evidence |
| TEST-VIS-028 | Approved-HTML extraction fidelity | when selected HTML is approved | UI-*, DS-* | Tokens, primitives, components, recipes, registry entries, and final mockups trace to and reproduce the approved selected HTML; rejected candidate-only values do not survive | extraction trace / source-to-projection diff / screenshot review |
| TEST-VIS-029 | Hallmark structural and anti-slop review | when Hallmark is loaded | UI-*, DS-* | Every candidate and the selected HTML has a read-only named-finding report; critical and major structural-template findings are repaired or explicitly block approval; final projections introduce no unresolved extraction-drift finding | Hallmark reports / repair trace / final projection review |
| TEST-VIS-030 | Selected-HTML immutable approval binding | when selected HTML is approved | UI-*, DS-* | Every representative UI ID maps to one canonical file under `visual-directions/selected/` with a lowercase SHA-256; the ordered manifest SHA-256 appears in the human approval evidence; any byte, path, order, or mapping change forces fresh audit and approval | selected-file manifest / digest recomputation / approval record |

Responsive set verified: <resolved platform set from `ui-registry.json`: web `viewports` (390 / 768 / 1200 / 1440 px by default), native `sizeClasses` and safe areas, or named desktop window sizes>. States verified: the State Matrix in `ui-architecture.md`.

## Page Acceptance

| UI ID | Page / route | Source | TEST IDs | Required evidence | Status |
|---|---|---|---|---|---|
| UI-001 | <route> | <source> | TEST-VIS-001 | <evidence> | planned |

## Known Visual Risks

| Risk | Impact | Decision |
|---|---|---|
| <risk> | <impact> | <decision> |
