# Design System: <product name>

## Overview

<Product archetype, audience, visual intent, density, tone, constraints, and source priority.>

<Resolved platform (web, native iOS, native Android, Flutter, React Native, macOS, Windows, or cross-platform desktop). The platform sets the vocabulary for the sections below: icon family, component-code language, breakpoint vs. size-class model, and the styling-pattern section. Do not default to web/Tailwind for a native or desktop target — see `references/design-system-guide.md`'s Product Archetype Rules.>

## Machine-Readable Companion

Artifact: `docs/product/design-system.json`

This Markdown file is the semantic authority: it carries the reasoning, the ratios, the guardrails, and the decisions. `design-system.json` is the machine-readable half — token names, primitive classes, closed variant sets, the responsive verification set, and the source paths where raw values may appear. Implementation and `fullstack-harness-engineering`'s `scripts/check_ui_contract.py` both read the JSON.

The two publish together. If a token, primitive, variant, or state changes here, change it in the JSON in the same move set. Neither file may carry a token or variant the other does not.

## Source Inputs

| Source | Path / URL | Role | Notes |
|---|---|---|---|
| PRD | <path> | product source | <notes> |
| Wireframes | <path> | structure source | <notes> |
| Brand / reference | <path or URL> | visual source | <notes> |

## Builder UX Direction Handoff

Decision owner: <human product/design owner or commissioning team>

| Dimension | Upstream direction | Status | Design-system expression | Evidence or validation need |
|---|---|---|---|---|
| Experience priority | <direction> | <selected / provisional / assumed> | <hierarchy, component, content, or interaction consequence> | <user evidence, prototype test, or none> |
| Guidance and control | <direction> | <selected / provisional / assumed> | <system expression> | <need> |
| Information density | <direction> | <selected / provisional / assumed> | <system expression> | <need> |
| Interaction and layout | <direction> | <selected / provisional / assumed> | <system expression> | <need> |
| Confirmation and recovery | <direction> | <selected / provisional / assumed> | <system expression> | <need> |

Builder approval proves direction conformance only, not usability. Keep unsupported preferences provisional or assumed until separate user evidence exists.

## Visual Direction

Status: <derived from product inputs / derived from brand sources / explored with frontend-design / n/a>

Decision owner: <human product/design owner; never an agent>
Basis: <brand assets, reference product, explored HTML path, or explicit assumption>
Approval: <explicit approval record, or `assumed — <reason>`>

When `frontend-design` is loaded and the user explicitly asked for it, use it to explore a direction before the tokens below are fixed. Record which direction was chosen and why. Exploration artifacts are evidence, not contract — only this file and `design-system.json` bind implementation. When no exploration happened, derive the system from recorded product inputs and explicit visual assumptions, and do not claim approved-direction extraction.

## Product-Specific Visual Thesis

| DS ID | Cue / signature decision | Product or source basis | Upstream trace IDs | System expression | Avoid |
|---|---|---|---|---|---|
| DS-001 | <concrete cue or recurring decision> | <evidence or explicit assumption> | PRD-001, UI-001, UX-001 | <tokens, components, layouts, imagery, or motion> | <unsupported generic default> |

## Taste & Anti-Slop Guardrails

Taste statement: <one sentence naming the intended visual character and the concrete typography, composition, color, imagery, or interaction choices that create it>

| Risk | Default rule | Allowed exception | Review test |
|---|---|---|---|
| <generic or AI-UI pattern risk> | <product-specific rule> | <evidence-based exception> | <how to verify> |
| Repeated bordered panels with a colored side rail or accent stripe | Do not use as a generic section treatment | Named state, selection, priority, category, or approved brand motif | Every use has a documented semantic or brand role |
| Uniform default border on every button, input, image, and avatar | Border only where rule 4 of Container & Border Decision Rules applies | Control boundary, data structure, focus, selection, validation, or status | Removal test leaves hierarchy and comprehension intact |
| Unexamined default font pairing (Inter/Poppins/Manrope/Geist) or default icon library (Lucide/Heroicons/Font Awesome) | Name the choice as deliberate with a brand or coverage reason | Evidence-based selection matching the product's audience and content | Taste statement cites the concrete typography/icon choice and why |

### Container & Border Rules

| Surface / region | Default treatment | Primary grouping cue | Border / elevation allowed for | Must avoid |
|---|---|---|---|---|
| Ordinary content section | open | spacing | n/a | decorative frame, nested card, accent rail |
| <surface> | <open / background band / real container> | <spacing / alignment / background / divider / border / elevation> | <named interaction, hierarchy, state, data, or accessibility purpose> | <unsupported framing or stacked effects> |

## Content & Data Realism

<Domain vocabulary, representative data shapes and lengths, asset constraints, placeholder rules, and claims that must not be fabricated.>

## Landing Page Simplicity & Media Plan

<Use when a public website, marketing page, or landing page is in scope. Keep one clear value proposition and one primary action in the first viewport. Give each section one job.>

| Section / region | Single job | Exact wording / display contract | Style direction | Image / media | Motion | Defer / exclude |
|---|---|---|---|---|---|---|
| <region> | <what the user must understand or do> | <verbatim wording, or what to show + intended takeaway/action + source + constraints> | <visual job; open/container/background/layout treatment; purpose> | <required / optional / none; purpose; source or creation need; responsive and static fallback> | <required / optional / none; purpose; trigger; reduced-motion fallback> | <content that belongs elsewhere> |

## Color Palette

Harmony method: <complementary / analogous / monochromatic / triadic / brand-anchored, and why it fits the product-specific visual thesis>

| Token | Value / Direction | CSS reference | Usage | Contrast ratio (if text/UI pairing) |
|---|---|---|---|---|
| Background | <value> | <class or CSS var> | <usage> | <n/a> |
| Surface | <value> | <class or CSS var> | <usage> | <n/a> |
| Text | <value> | <class or CSS var> | <usage> | <e.g. 7.2:1 on Background> |
| Accent | <value> | <class or CSS var> | <usage> | <e.g. 4.8:1 on Background> |
| Border | <value> | <class or CSS var> | <usage> | <n/a> |
| Success / warning / danger | <value> | <class or CSS var> | <usage> | <ratio on their usual background, plus the non-color cue used to keep them colorblind-safe> |

Ratios computed with `scripts/check_color_contrast.py`, not estimated.

## Typography

Pay attention to font family, font weight, font size, line height, and how different fonts or font roles are used together.

Pairing rationale: <why these families/roles work together, and the type-scale ratio or logic tying the sizes below into one system>

| Role | Font / family | Size | Weight | Line height | Line-height ratio | Usage |
|---|---|---|---|---|---|---|
| Display / page title | <font> | <size> | <weight> | <line height> | <e.g. 1.15 (heading floor 1.1)> | <usage> |
| Section heading | <font> | <size> | <weight> | <line height> | <e.g. 1.2 (heading floor 1.1)> | <usage> |
| Body | <font> | <size> | <weight> | <line height> | <e.g. 1.5 (WCAG 1.4.12 minimum)> | <usage> |
| Caption / metadata | <font> | <size> | <weight> | <line height> | <e.g. 1.5 (WCAG 1.4.12 minimum)> | <usage> |

Ratios computed with `scripts/check_type_scale.py`, not estimated.

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

## Spacing System

| Token | Value | Usage |
|---|---|---|
| Base spacing | <value> | <usage> |
| Component padding | <value> | <usage> |
| Section gap | <value> | <usage> |
| Grid gap | <value> | <usage> |

## Primitive Inventory

Four layers, in order: layout, surface, typography, control. Layer N uses only layers below N. Every variant list below is a closed set — a page picks from it and may not extend it. The machine-readable form of this table is `design-system.json`'s `primitives` object; the two must agree.

| DS ID | Primitive | Layer | Class | Closed variant sets | Composes | Notes |
|---|---|---|---|---|---|---|
| DS-LAY-001 | <Container> | layout | <class> | <sizes: shell, content, narrow, dialog> | n/a | <notes> |
| DS-SUR-001 | <Surface> | surface | <class> | <variants: plain, raised, inset> | <layout> | <notes> |
| DS-TYP-001 | <Text> | typography | <class> | <roles: display, heading, body, caption> | n/a | <notes> |
| DS-CTL-001 | <Button> | control | <btn> | <variants; sizes> | <typography> | <min target, accessible name> |

### Product Components

| DS ID | Component | Composes | Required content order | States | Notes |
|---|---|---|---|---|---|
| DS-COMP-001 | <DomainComponentName> | <DS-LAY-001, DS-SUR-001, DS-CTL-001> | <field, field, field> | <ready, loading, empty, error> | <notes> |

### The Two Binding Rules

- Every raw color, dimension, and motion value in the product appears in this document's token sections and in the JSON's declared `tokenSources`, and nowhere else.
- Nothing outside this document may invent a value or a control. A page that needs one gets a new token here plus a new entry in `design-system.json` — it does not style its own.

## Shadows & Elevation

| Token | Value / Direction | Usage |
|---|---|---|
| None / flat | <value> | <usage> |
| Raised | <value> | <usage> |
| Overlay | <value> | <usage> |

## Motion System

### Motion Principles & Stack

| Mechanism | Technology | Owns | Dependency / version | Performance constraints | Fallback |
|---|---|---|---|---|---|
| <style-layer transition / animation runtime / route-level transition> | <CSS, WAAPI, Motion, GSAP, Rive, native, or none> | <the work this mechanism owns> | <dependency / version or built-in> | <constraints> | <fallback> |

Mechanism and purpose are separate decisions. Every pattern below uses exactly one purpose: feedback, continuity, processing, or storytelling. There is no decorative or ambient exception.

### Global Reduced-Motion Configuration

| Configuration point | Location | Normal behavior | Reduced-motion behavior | Opt-out / exception rule |
|---|---|---|---|---|
| Application boundary | <single style-layer media query, runtime provider/configuration, and route-transition setting> | <global default inherited by every registered variant> | <final state immediately, or opacity-only; no spatial transform, parallax, autoplay, continuous ambience, or scale> | <route-level opt-out or justified per-variant exception; name the owner and reason> |

Call sites do not query reduced-motion preferences. They reference registered variants that inherit this global configuration.

### Motion Tokens

| Token | Duration | Easing / spring | Distance / scale | Usage | Reduced-motion value |
|---|---|---|---|---|---|
| <token> | <duration> | <curve or spring> | <distance or scale> | <usage> | <none, instant, or opacity-only> |

### Motion Pattern Inventory

| Motion ID | Surface / component | Mechanism | Purpose | Trigger | Properties | Token / sequence | Repeat / interruption | Responsive and reduced-motion behavior |
|---|---|---|---|---|---|---|---|---|
| MOTION-001 | <surface> | <mechanism> | <feedback / continuity / processing / storytelling> | <load, viewport, interaction, state, or scroll> | <opacity/transform/etc.> | <tokens> | <rules> | <behavior> |

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

<Grid, max widths, navigation layout, and region rules.>

Responsive verification set: <the exact `viewports` or `sizeClasses` list published in `design-system.json`. Web targets use pixel viewports; native and desktop targets use that platform's own size-class or window-size model.>

## State Matrix

Every screen covers these states, or marks the inapplicable ones `n/a` with a reason. Shipping the ready state alone does not close a task.

| State | Applies to | Behavior | Notes |
|---|---|---|---|
| ready | <scope> | <behavior> | <notes> |
| loading | <scope> | <behavior> | <notes> |
| empty | <scope> | <behavior> | <notes> |
| error | <scope> | <behavior> | <notes> |
| disabled | <scope> | <behavior> | <notes> |
| permission denied | <scope> | <behavior> | <notes> |
| stale | <scope> | <behavior> | <notes> |
| expired | <scope> | <behavior> | <notes> |
| long content | <scope> | <behavior> | <notes> |
| reduced motion | <scope> | <behavior> | <notes> |
| mobile reflow | <scope> | <behavior> | <notes> |

## Styling Pattern Usage

<Web target. For a native or desktop target, rename this to the platform's styling model (SwiftUI view modifiers, Compose Modifier chains and MaterialTheme tokens, Flutter ThemeData/widget styles, or WinUI resources) and list the reusable style patterns implementers apply.>

| Pattern | Classes / tokens | Usage | Notes |
|---|---|---|---|
| Page shell | <classes> | <usage> | <notes> |
| Card / panel | <classes> | <usage> | <notes> |
| Button | <classes> | <usage> | <notes> |
| Form control | <classes> | <usage> | <notes> |
| Responsive grid | <classes> | <usage> | <notes> |

## Example Component Reference Code

```tsx
// Example only. Adapt to the target project stack.
export function ExampleContentSection() {
  return (
    <section className="<open layout classes>">
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
