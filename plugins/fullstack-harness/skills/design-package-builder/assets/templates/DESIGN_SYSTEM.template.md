# Design System: <product name>

## Overview

<Product archetype, audience, visual intent, density, tone, constraints, and source priority.>

## Source Inputs

| Source | Path / URL | Role | Notes |
|---|---|---|---|
| PRD | <path> | product source | <notes> |
| Wireframes | <path> | structure source | <notes> |
| Brand / reference | <path or URL> | visual source | <notes> |

## Product-Specific Visual Thesis

| Cue / signature decision | Product or source basis | System expression | Avoid |
|---|---|---|---|
| <concrete cue or recurring decision> | <evidence or explicit assumption> | <tokens, components, layouts, imagery, or motion> | <unsupported generic default> |

## Anti-Generic Design Rules

| Risk | Default rule | Allowed exception | Review test |
|---|---|---|---|
| <generic or AI-UI pattern risk> | <product-specific rule> | <evidence-based exception> | <how to verify> |

## Content & Data Realism

<Domain vocabulary, representative data shapes and lengths, asset constraints, placeholder rules, and claims that must not be fabricated.>

## Landing Page Simplicity & Media Plan

<Use when a public website, marketing page, or landing page is in scope. Keep one clear value proposition and one primary action in the first viewport. Give each section one job.>

| Section / region | Single job | Exact wording / display contract | Image / media | Motion | Defer / exclude |
|---|---|---|---|---|---|
| <region> | <what the user must understand or do> | <verbatim wording, or what to show + intended takeaway/action + source + constraints> | <required / optional / none; purpose; source or creation need; responsive and static fallback> | <required / optional / none; purpose; trigger; reduced-motion fallback> | <content that belongs elsewhere> |

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

## Iconography System

### Market Scan & Decision

| Candidate | Official source | Visual fit | Required-icon coverage | Integration | License / checked date | Decision |
|---|---|---|---|---|---|---|
| <icon set> | <official URL> | <fit> | <pass / gaps> | <package, SVG, font, or platform API> | <license / YYYY-MM-DD> | <primary, exception, or rejected> |

### Icon Tokens

| Token | Optical size | Stroke / weight / fill | Color behavior | Usage |
|---|---|---|---|---|
| <token> | <size> | <setting> | <currentColor or semantic token> | <usage> |

### Semantic Icon Inventory

| Intent / object | Visible label | Icon name | Source | Token / variant | State behavior | Accessibility behavior |
|---|---|---|---|---|---|---|
| <action, status, navigation, or domain object> | <label or none> | <exact name> | <library or custom source> | <token / variant> | <selected, disabled, RTL, etc.> | <hidden, named control, tooltip, etc.> |

### Source & Exception Rules

<Primary package/import path or asset source, version policy, tree-shaking or subsetting, RTL handling, brand-icon source, custom-icon construction rules, and approved secondary-library exceptions.>

### Example Icon Usage Code

```tsx
// Example structure only. Replace with the selected library and project primitives.
import { ExampleIcon } from "<approved-icon-package>";

export function IconActions() {
  return (
    <>
      <button>
        <ExampleIcon aria-hidden="true" className="<icon-token>" />
        Visible action
      </button>
      <button aria-label="Descriptive action">
        <ExampleIcon aria-hidden="true" className="<icon-token>" />
      </button>
    </>
  );
}
```

<Define tooltip behavior for the icon-only control and adapt accessibility details to the target stack.>

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

## Motion System

### Motion Principles & Stack

| Layer / purpose | Technology | Why | Dependency / version | Performance constraints | Fallback |
|---|---|---|---|---|---|
| <feedback, orientation, continuity, emphasis, or storytelling> | <CSS, WAAPI, Motion, GSAP, Rive, native, or none> | <rationale> | <dependency / version or built-in> | <constraints> | <fallback> |

### Motion Tokens

| Token | Duration | Easing / spring | Distance / scale | Usage | Reduced-motion value |
|---|---|---|---|---|---|
| <token> | <duration> | <curve or spring> | <distance or scale> | <usage> | <none, instant, or opacity-only> |

### Motion Pattern Inventory

| Motion ID | Surface / component | Purpose | Trigger | Properties | Token / sequence | Repeat / interruption | Responsive and reduced-motion behavior |
|---|---|---|---|---|---|---|---|
| MOTION-001 | <surface> | <purpose> | <load, viewport, interaction, state, or scroll> | <opacity/transform/etc.> | <tokens> | <rules> | <behavior> |

### Hero Choreography

| Step | Element | Start / relation | From → to | Purpose | Mobile behavior | Reduced-motion behavior |
|---|---|---|---|---|---|---|
| 1 | <eyebrow, headline, copy, CTA, media, or decoration> | <time or relation> | <values> | <reason> | <variant> | <fallback> |

### Motion Demo Index

| Demo ID | Pattern / page | Artifact path | Stack | Controls | Status |
|---|---|---|---|---|---|
| DEMO-001 | <hero or pattern> | <motion-showcase.html or path> | <stack> | play / pause / restart / reduced motion | <draft or approved> |

### Example Motion Implementation Code

<Provide static-first, stack-appropriate implementation code with reduced-motion handling and cleanup/cancellation where required.>

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
