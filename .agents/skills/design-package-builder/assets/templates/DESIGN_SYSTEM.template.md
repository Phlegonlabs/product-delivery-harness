# Design System: <product name>

## Overview

<Product archetype, audience, visual intent, density, tone, constraints, and source priority.>

## Source Inputs

| Source | Path / URL | Role | Notes |
|---|---|---|---|
| PRD | <path> | product source | <notes> |
| Wireframes | <path> | structure source | <notes> |
| Brand / reference | <path or URL> | visual source | <notes> |

## Color Palette

| Token | Value / Direction | Tailwind / CSS reference | Usage |
|---|---|---|---|
| Background | <value> | <class or CSS var> | <usage> |
| Surface | <value> | <class or CSS var> | <usage> |
| Text | <value> | <class or CSS var> | <usage> |
| Accent | <value> | <class or CSS var> | <usage> |
| Border | <value> | <class or CSS var> | <usage> |
| Success / warning / danger | <value> | <class or CSS var> | <usage> |

## Typography

Pay attention to font family, font weight, font size, line height, and how different fonts or font roles are used together.

| Role | Font / family | Size | Weight | Line height | Usage |
|---|---|---|---|---|---|
| Display / page title | <font> | <size> | <weight> | <line height> | <usage> |
| Section heading | <font> | <size> | <weight> | <line height> | <usage> |
| Body | <font> | <size> | <weight> | <line height> | <usage> |
| Caption / metadata | <font> | <size> | <weight> | <line height> | <usage> |

## Spacing System

| Token | Value | Usage |
|---|---|---|
| Base spacing | <value> | <usage> |
| Component padding | <value> | <usage> |
| Section gap | <value> | <usage> |
| Grid gap | <value> | <usage> |

## Component Styles

| Component | Variants | States | Usage Rules |
|---|---|---|---|
| Button | <variants> | <states> | <rules> |
| Input | <variants> | <states> | <rules> |
| Navigation | <variants> | <states> | <rules> |
| Card / panel | <variants> | <states> | <rules> |
| Table / list | <variants> | <states> | <rules> |
| Modal / drawer | <variants> | <states> | <rules> |

## Shadows & Elevation

| Token | Value / Direction | Usage |
|---|---|---|
| None / flat | <value> | <usage> |
| Raised | <value> | <usage> |
| Overlay | <value> | <usage> |

## Animations & Transitions

| Pattern | Duration | Easing | Usage | Reduced-motion fallback |
|---|---|---|---|---|
| Hover feedback | <duration> | <easing> | <usage> | <fallback> |
| Panel / modal entry | <duration> | <easing> | <usage> | <fallback> |
| Loading / skeleton | <duration> | <easing> | <usage> | <fallback> |

## Border Radius

| Token | Value | Usage |
|---|---|---|
| Small | <value> | <usage> |
| Medium | <value> | <usage> |
| Large | <value> | <usage> |

## Opacity & Transparency

| Token / Pattern | Value | Usage |
|---|---|---|
| Disabled | <value> | <usage> |
| Overlay | <value> | <usage> |
| Subtle surface | <value> | <usage> |

## Layout Rules

<Grid, max widths, navigation layout, responsive breakpoints, and region rules.>

## Common Tailwind CSS Usage In Project

| Pattern | Classes / tokens | Usage | Notes |
|---|---|---|---|
| Page shell | <classes> | <usage> | <notes> |
| Card / panel | <classes> | <usage> | <notes> |
| Button | <classes> | <usage> | <notes> |
| Form control | <classes> | <usage> | <notes> |
| Responsive grid | <classes> | <usage> | <notes> |

## Example Component Reference Design Code

```tsx
// Example only. Adapt to the target project stack.
export function ExampleCard() {
  return (
    <section className="<container classes>">
      <div className="<header classes>">
        <h2 className="<title classes>">Example title</h2>
        <p className="<body classes>">Example supporting copy.</p>
      </div>
      <button className="<button classes>">Primary action</button>
    </section>
  );
}
```

## Interaction Rules

<Focus, hover, active, loading, disabled, selected, expanded, and validation feedback.>

## Accessibility Rules

<Contrast intent, focus visibility, keyboard path, text sizing, labels, and motion.>

## Assumptions

- <assumption>

## Open Questions

- <question>
