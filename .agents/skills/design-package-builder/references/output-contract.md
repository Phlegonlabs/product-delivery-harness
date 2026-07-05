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

## Overview
[Product archetype, audience, visual intent, density, tone, constraints, and source priority.]

## Source Inputs
| Source | Path / URL | Role | Notes |
| --- | --- | --- | --- |

## Color Palette
| Token | Value / Direction | Tailwind / CSS reference | Usage |
| --- | --- | --- | --- |

## Typography
Pay attention to font family, font weight, font size, line height, and how different fonts or font roles are used together.

| Role | Font / family | Size | Weight | Line height | Usage |
| --- | --- | --- | --- | --- | --- |

## Spacing System
| Token | Value | Usage |
| --- | --- | --- |

## Component Styles
| Component | Variants | States | Usage Rules |
| --- | --- | --- | --- |

## Shadows & Elevation
| Token | Value / Direction | Usage |
| --- | --- | --- |

## Animations & Transitions
| Pattern | Duration | Easing | Usage | Reduced-motion fallback |
| --- | --- | --- | --- | --- |

## Border Radius
| Token | Value | Usage |
| --- | --- | --- |

## Opacity & Transparency
| Token / Pattern | Value | Usage |
| --- | --- | --- |

## Layout Rules
[Grid, max widths, navigation layout, responsive breakpoints.]

## Common Tailwind CSS Usage In Project
| Pattern | Classes / tokens | Usage | Notes |
| --- | --- | --- | --- |

## Example Component Reference Design Code
Include a small reference component that demonstrates the design rules. Use the project's likely stack and mark framework assumptions clearly.

```tsx
// Example only. Adapt to the target project stack.
export function ExampleCard() {
  return <div className="[classes]">...</div>;
}
```

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
- `design-system.md` defines overview, color palette, typography, spacing, component styles, shadows/elevation, animations/transitions, border radius, opacity/transparency, common Tailwind/CSS usage, example component reference design code, layout rules, states, and accessibility rules.
- `page-ui-matrix.md` maps every important page or route to UI source, breakpoints, states, components, data source, and acceptance evidence.
- `ui-mockups.md` includes high-fidelity page-level specifications or links to actual visual artifacts.
- `visual-acceptance.md` defines implementation-verifiable visual gates.
- Missing brand assets, mockups, states, or breakpoints are explicit assumptions or open questions.
- The package does not create product scope, backend architecture, harness mission maps, or E2E evidence registers.
