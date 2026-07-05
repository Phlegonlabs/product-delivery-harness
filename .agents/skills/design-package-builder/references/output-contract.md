# Output Contract

Produce a multi-file Markdown design package. Use exactly these artifact names unless the user requests different names:

- `design-system.md`
- `page-ui-matrix.md`
- `ui-mockups.md`
- `visual-acceptance.md`

Default all artifact content to English unless the user explicitly asks for another language.

Use the templates in `assets/templates/` when creating these files.

## `design-system.md`

Use this structure:

```markdown
# Design System: [Product Name]

## Source Inputs
| Source | Path / URL | Role | Notes |
| --- | --- | --- | --- |

## Design Direction
[Audience, archetype, visual intent, density, tone, constraints.]

## Tokens
### Color
| Token | Value / Direction | Usage |
| --- | --- | --- |

### Typography
| Role | Size | Weight | Line height | Usage |
| --- | --- | --- | --- | --- |

### Spacing, Radius, Elevation
| Token | Value | Usage |
| --- | --- | --- |

## Layout Rules
[Grid, max widths, navigation layout, responsive breakpoints.]

## Components
| Component | Variants | States | Usage Rules |
| --- | --- | --- | --- |

## Interaction And Motion
[Focus, hover, active, loading, transitions, reduced motion.]

## Accessibility Rules
[Contrast, focus, keyboard, text sizing, motion.]

## Assumptions
- [Assumption]

## Open Questions
- [Question]
```

## `page-ui-matrix.md`

Use this structure:

```markdown
# Page UI Matrix: [Product Name]

| Page / route | UI source | Breakpoints | States | Components | Data source | Acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- |
| /example | ui-mockups.md#example | mobile/tablet/desktop | ready/loading/error | cards/table/actions | API-001 | screenshot + visual review |

## State Coverage Notes
- [Page]: [missing or derived states]
```

## `ui-mockups.md`

Use this structure:

```markdown
# UI Mockups: [Product Name]

## Mockup Index
| Mockup ID | Page / route | Breakpoint | State | Source / artifact |
| --- | --- | --- | --- | --- |

## Mockup: [Page Name] - [Breakpoint] - [State]
### Purpose
[What this screen accomplishes.]

### Layout
[Regions, hierarchy, grid, spacing, responsive behavior.]

### Components
| Component | Variant | Content / data | State |
| --- | --- | --- | --- |

### Visual Details
[Color, typography, imagery, icons, density, alignment.]

### Asset Requirements
- [Images, icons, logos, generated assets, screenshots.]

### Acceptance Criteria
- [Visual requirement]
```

## `visual-acceptance.md`

Use this structure:

```markdown
# Visual Acceptance: [Product Name]

## Review Gates
| Gate | Required | Expected Signal | Evidence |
| --- | --- | --- | --- |
| Design system conformance | yes | Components use approved tokens and variants | screenshot / code review |
| Page UI conformance | yes | Implemented page matches mockup source | screenshot / trace |
| Responsive behavior | yes | No overflow or broken hierarchy at required breakpoints | screenshot |
| State coverage | yes | Required loading/empty/error/disabled states exist | screenshot / test |
| Accessibility basics | yes | Focus, contrast intent, labels, keyboard path checked | audit / screenshot |

## Page Acceptance
| Page / route | Source | Required evidence | Status |
| --- | --- | --- | --- |

## Known Visual Risks
| Risk | Impact | Decision |
| --- | --- | --- |
```

## Quality Checklist

Before finalizing, verify:

- All four artifacts are present.
- `design-system.md` defines concrete tokens, layout rules, components, states, and accessibility rules.
- `page-ui-matrix.md` maps every important page or route to UI source, breakpoints, states, components, data source, and acceptance evidence.
- `ui-mockups.md` includes high-fidelity page-level specifications or links to actual visual artifacts.
- `visual-acceptance.md` defines implementation-verifiable visual gates.
- Missing brand assets, mockups, states, or breakpoints are explicit assumptions or open questions.
- The package does not create product scope, backend architecture, harness mission maps, or E2E evidence registers.
