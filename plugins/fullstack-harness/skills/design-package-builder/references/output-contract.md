# Output Contract

Produce a multi-file Markdown design package. Use exactly these artifact names unless the user requests different names:

- `design-system.md`
- `page-ui-matrix.md`
- `ui-mockups.md`
- `visual-acceptance.md`

Default all artifact content to English unless the user explicitly asks for another language.

Use the templates in `assets/templates/` when creating these files.

When the user requests a runnable animation demonstration, also produce `motion-showcase.html` or bounded files under `motion-demos/`. Use `assets/templates/MOTION_SHOWCASE.template.html` as the dependency-free baseline unless the project stack or requested animation requires another implementation. Record every demo path in `design-system.md` and `ui-mockups.md`.

## `design-system.md`

Use this structure:

````markdown
# Design System: [Product Name]

## Overview
[Product archetype, audience, visual intent, density, tone, constraints, and source priority.]

## Source Inputs
| Source | Path / URL | Role | Notes |
| --- | --- | --- | --- |

## Product-Specific Visual Thesis
| Cue / signature decision | Product or source basis | System expression | Avoid |
| --- | --- | --- | --- |

## Taste & Anti-Slop Guardrails
Taste statement: [One sentence naming the intended visual character and the concrete typography, composition, color, imagery, or interaction choices that create it.]

| Risk | Default rule | Allowed exception | Review test |
| --- | --- | --- | --- |

### Container & Border Rules
| Surface / region | Default treatment | Primary grouping cue | Border / elevation allowed for | Must avoid |
| --- | --- | --- | --- | --- |
| [Surface] | [open / background band / real container] | [spacing / alignment / background / divider / border / elevation] | [named interaction, hierarchy, state, data, or accessibility purpose] | [unsupported framing or stacked effects] |

## Content & Data Realism
[Domain vocabulary, representative data shapes and lengths, asset constraints, placeholder rules, and claims that must not be fabricated.]

## Landing Page Simplicity & Media Plan
Use this section when a public website, marketing page, or landing page is in scope. Keep one clear value proposition and one primary action in the first viewport. Give each section one job. Do not copy the whole PRD into the page.

| Section / region | Single job | Exact wording / display contract | Style direction | Image / media | Motion | Defer / exclude |
| --- | --- | --- | --- | --- | --- | --- |
| [Region] | [What the user must understand or do] | [Verbatim wording, or what to show + intended takeaway/action + source + constraints] | [Visual job; open/container/background/layout treatment; purpose] | [required / optional / none; purpose; source or creation need; responsive and static fallback] | [required / optional / none; purpose; trigger; reduced-motion fallback] | [Content that belongs elsewhere] |

## Color Palette
| Token | Value / Direction | Tailwind / CSS reference | Usage |
| --- | --- | --- | --- |

## Typography
Pay attention to font family, font weight, font size, line height, and how different fonts or font roles are used together.

| Role | Font / family | Size | Weight | Line height | Usage |
| --- | --- | --- | --- | --- | --- |

## Iconography System

### Market Scan & Decision
| Candidate | Official source | Visual fit | Required-icon coverage | Integration | License / checked date | Decision |
| --- | --- | --- | --- | --- | --- | --- |

### Icon Tokens
| Token | Optical size | Stroke / weight / fill | Color behavior | Usage |
| --- | --- | --- | --- | --- | --- |

### Semantic Icon Inventory
| Intent / object | Visible label | Icon name | Source | Token / variant | State behavior | Accessibility behavior |
| --- | --- | --- | --- | --- | --- | --- |

### Source & Exception Rules
[Primary package/import path or asset source, version policy, tree-shaking or subsetting, RTL handling, brand-icon source, custom-icon construction rules, and approved secondary-library exceptions.]

### Example Icon Usage Code
Include stack-appropriate code using the chosen primary library. Show one action with visible text and one icon-only action. Use the exact package import and icon token, place the accessible name on the control, hide a redundant glyph from assistive technology, and define tooltip behavior for the icon-only control.

```tsx
// Example structure only. Replace with the selected library and project primitives.
import { ExampleIcon } from "<approved-icon-package>";

export function IconActions() {
  return (
    <>
      <button><ExampleIcon aria-hidden="true" className="<icon-token>" />Visible action</button>
      <button aria-label="Descriptive action"><ExampleIcon aria-hidden="true" className="<icon-token>" /></button>
    </>
  );
}
```

## Spacing System
| Token | Value | Usage |
| --- | --- | --- |

## Component Styles
| Component | Variants | States | Usage Rules |
| --- | --- | --- | --- |

## Shadows & Elevation
| Token | Value / Direction | Usage |
| --- | --- | --- |

## Motion System

### Motion Principles & Stack
| Layer / purpose | Technology | Why | Dependency / version | Performance constraints | Fallback |
| --- | --- | --- | --- | --- | --- |

### Motion Tokens
| Token | Duration | Easing / spring | Distance / scale | Usage | Reduced-motion value |
| --- | --- | --- | --- | --- | --- |

### Motion Pattern Inventory
| Motion ID | Surface / component | Purpose | Trigger | Properties | Token / sequence | Repeat / interruption | Responsive and reduced-motion behavior |
| --- | --- | --- | --- | --- | --- | --- | --- |

### Hero Choreography
| Step | Element | Start / relation | From → to | Purpose | Mobile behavior | Reduced-motion behavior |
| --- | --- | --- | --- | --- | --- | --- |

### Motion Demo Index
| Demo ID | Pattern / page | Artifact path | Stack | Controls | Status |
| --- | --- | --- | --- | --- | --- |

### Example Motion Implementation Code
Include a static-first, stack-appropriate implementation for one important pattern. The final DOM/CSS state must remain usable if animation code does not load. Show reduced-motion handling and cleanup or cancellation when the stack requires it.

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
export function ExampleContentSection() {
  return <section className="[open layout classes]">...</section>;
}
```

## Accessibility Rules
[Contrast, focus, keyboard, text sizing, motion.]

## Assumptions
- [Assumption]

## Open Questions
- [Question]
````

## `page-ui-matrix.md`

Use this structure:

```markdown
# Page UI Matrix: [Product Name]

| Page / route | UI source | Motion source | Breakpoints | States | Components | Data source | Acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| /example | ui-mockups.md#example | motion-showcase.html#example | mobile/tablet/desktop | ready/loading/error | cards/table/actions | API-001 | screenshot + motion review |

## State Coverage Notes
- [Page]: [missing or derived states]
```

## `ui-mockups.md`

Use this structure:

```markdown
# UI Mockups: [Product Name]

## Mockup Index
| Mockup ID | Page / route | Breakpoint | State | Source / artifact | Motion demo |
| --- | --- | --- | --- | --- | --- |

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

### Content Budget
Use for landing pages and other content-heavy public pages.

| Region | Single job | Content mode | Exact wording / display contract | Style direction | Defer / exclude |
| --- | --- | --- | --- | --- | --- |
| [Region] | [User understanding or action] | [exact copy / display contract] | [Verbatim wording, or what to show + intended takeaway/action + source + constraints] | [Visual job; open/container/background/layout treatment; purpose] | [Move elsewhere or omit] |

### Product-Specific Design Decisions
- Signature cues applied: [decisions]
- Generic patterns intentionally avoided: [patterns and rationale]
- Container and border treatment: [open-layout default and the named purpose of any visible frame or elevation]
- Content realism: [representative content/data or explicit placeholders]

### Icon Usage
| Intent / object | Icon name | Source | Token / variant | Label / accessibility | State |
| --- | --- | --- | --- | --- | --- |

### Motion & Choreography
| Motion ID | Element | Purpose | Trigger | Sequence / token | Responsive behavior | Reduced-motion fallback | Demo path |
| --- | --- | --- | --- | --- | --- | --- | --- |

### Asset Requirements
| Region | Asset type | Need | Purpose | Source / creation | Responsive and static fallback |
| --- | --- | --- | --- | --- | --- |
| [Region] | [image, product media, illustration, video, icon, logo, generated asset, screenshot, or none] | [required / optional / none] | [What it helps the user understand or do] | [Existing path, source, or create] | [Crop, alternate, poster, or text/structure fallback] |

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
| --- | --- | --- | --- |

## Known Visual Risks
| Risk | Impact | Decision |
| --- | --- | --- |
```

## Quality Checklist

Before finalizing, verify:

- All four artifacts are present.
- `design-system.md` defines overview, a product-specific visual thesis, taste and anti-slop guardrails, container and border rules, content/data realism, color palette, typography, iconography, spacing, component styles, shadows/elevation, a complete motion system, border radius, opacity/transparency, common Tailwind/CSS usage, example component reference design code, layout rules, states, and accessibility rules.
- The visual thesis includes three to five concrete brand or context cues, at least two recurring signature decisions, and avoided defaults tied to product evidence or explicit assumptions.
- The taste statement names a concrete visual character and the compositional choices that create it; it does not stop at generic adjectives.
- The container and border table defaults ordinary regions to open layouts, chooses one primary grouping cue per nesting level, and gives every visible frame or elevation a named purpose.
- The iconography section records a current official-source market scan, evidence-based primary choice, actual required-icon coverage, token rules, semantic inventory, package or asset source, checked date, license, accessibility behavior, and documented exceptions.
- The iconography section includes stack-appropriate reference code for labeled and icon-only actions using the exact approved import, tokens, accessible-name ownership, decorative hiding, and tooltip behavior.
- The motion system defines purpose, stack choice, tokens, pattern inventory, triggers, interruption/repeat rules, responsive variants, reduced-motion behavior, performance limits, and hero choreography when a hero exists.
- Requested runnable motion showcases exist, work without production dependencies unless justified, expose preview controls, and keep essential content usable when animation is unavailable.
- `page-ui-matrix.md` maps every important page or route to UI and motion sources, breakpoints, states, components, data source, and acceptance evidence.
- `ui-mockups.md` includes high-fidelity page-level specifications or links to actual visual artifacts, plus product-specific decisions, content-realism notes, and motion choreography for every important animated page.
- `ui-mockups.md` preserves product-source exact wording or a bounded display contract for every visible region; generic mockup placeholders do not pass validation.
- `ui-mockups.md` resolves each required style label, states the container and border treatment, and does not default regions to framed panels, nested cards, or colored accent rails without a named purpose.
- When a landing page is in scope, `design-system.md` and `ui-mockups.md` define the first-viewport message and action, one job per section, content to defer, and per-region image/media/motion status.
- `visual-acceptance.md` defines implementation-verifiable visual gates, including taste, unsupported AI-UI pattern clusters, and container and border purpose.
- Missing brand assets, mockups, states, or breakpoints are explicit assumptions or open questions.
- The package does not create product scope, backend architecture, harness mission maps, or E2E evidence registers.

## Taste & Anti-Slop Review Checklist

Before finalizing, verify:

- The interface remains understandable when decorative effects are removed.
- The one-sentence taste statement is visible in the hierarchy and at least two recurring decisions, not only in the logo or adjectives.
- At least two signature decisions recur across the system and important pages without becoming repetitive decoration.
- Ordinary content regions default to open layouts, and each nesting level uses one primary grouping cue unless a documented reason requires more.
- Every visible border, frame, rail, or elevation has a named hierarchy, interaction, state, data, or accessibility purpose; the removal test eliminates treatments that add no information.
- Repeated bordered cards, nested frames, colored side rails, accent stripes, dashed outlines, and double frames are absent unless every use has a named semantic or approved brand role.
- Radii, pills, shadows, gradients, glass effects, icons, and motion each have a product, hierarchy, or interaction rationale.
- Page composition follows task priority and content shape instead of defaulting to centered heroes, uniform card grids, or equal visual weight.
- Landing pages do not summarize the entire PRD. The first viewport has one message and primary action, and every later section earns its place with one clear job.
- Images, media, and animation are tied to a named user or product purpose; decorative assets are not added merely to fill space.
- Labels, sample data, imagery, and content lengths reflect the domain; unsupported claims, metrics, testimonials, and logos are not fabricated.
- Familiar patterns retained for usability, platform convention, or brand fit have a documented reason rather than being removed mechanically.
- When visual artifacts or an implementation exist, required breakpoint renders were critiqued, the highest-impact failure was repaired, and the package was rechecked against these gates. For a spec-only package, a text-only conformance review covers taste, hierarchy, container and border purpose, responsive intent, and internal consistency; render evidence is marked unavailable and the package makes no visual-verification claim.
