# Visual Decision Guide

Use this guide when turning product inputs into design-system and mockup decisions.

## Product Archetype Rules

SaaS apps, dashboards, and internal tools:

- Prioritize scanning, comparison, repeated action, predictable navigation, dense but organized information, and restrained styling.
- Avoid marketing-style hero layouts, oversized decorative cards, and decorative gradients in operational surfaces.
- Use compact tables, filters, status indicators, sidebars, tabs, split panes, and toolbar actions when workflows need repeated use.

Public websites, marketing pages, and conversion landing pages:

- Make the product, offer, venue, person, or object immediately visible in the first viewport.
- Use visual assets that reveal the actual subject. Avoid purely abstract decoration as the primary visual.
- Define conversion states, form states, trust signals, SEO/content modules, and responsive section order.

Docs and content sites:

- Prioritize readable typography, navigation depth, search, table of contents, code/content treatment, and content hierarchy.
- Define article, collection, landing, search, and empty-result patterns when relevant.

Ecommerce and catalog experiences:

- Prioritize product inspection, filtering, comparison, pricing/inventory clarity, PDP/PLP structure, cart boundaries, and trust cues.
- Define image ratios, product card variants, search/filter states, unavailable states, and schema/SEO surfaces when relevant.

Mobile apps:

- Prioritize thumb reach, native navigation patterns, compact states, offline/loading/error handling, and platform conventions.

## Design System Coverage

Define only rules that implementation can apply:

- Overview: product archetype, audience, visual intent, density, tone, constraints, and source priority
- Color palette: background, surface, text, border, accent, semantic states, charts if needed
- Typography: font family category, scale, weight, line height, heading/body/caption usage, and how font roles work together
- Spacing system: base unit, section rhythm, component padding, grid gaps
- Component styles: buttons, inputs, selects, tables, cards, dialogs, nav, tabs, alerts, charts, content blocks as relevant
- Shadows and elevation: component hierarchy, overlays, panels, and depth rules
- Animations and transitions: hover, focus, active, selected, disabled, loading, skeletons, reduced-motion fallback
- Border radius: token values and component usage rules
- Opacity and transparency: disabled states, overlays, glass/subtle surfaces, and contrast risks
- Layout: grid, max widths, sidebars, headers, responsive breakpoints
- Common Tailwind CSS usage in project: recurring utility patterns, component class patterns, and CSS variable mappings when relevant
- Example component reference design code: a small implementation-oriented component example that demonstrates the style guide
- Accessibility: contrast intent, focus visibility, keyboard path, reduced motion

## Page UI Matrix Rules

Every important page or route should name:

- UI source
- Breakpoints
- Required states
- Components
- Data source
- Acceptance evidence

If only ready-state mockups exist, derive other states from the design system and mark that decision.

## Mockup Rules

Use mockups to define high-fidelity layout and visual hierarchy, not product scope.

For each page mockup, specify:

- Viewport and breakpoint
- Primary content hierarchy
- Layout regions
- Component composition
- Copy/content placeholders
- State-specific changes
- Responsive behavior
- Asset requirements
- Visual acceptance criteria

If generating actual bitmap mockups or visual alternatives is requested and image tools are available, use the generated files as visual sources and record their paths in `ui-mockups.md`.

## Conflict Rules

- Product requirements beat visual preference.
- Design system beats one-off mockup styling unless the user accepts an exception.
- Page UI mockups beat low-fidelity wireframes for visual hierarchy and layout detail.
- Low-fidelity wireframes remain useful for flow and required regions.
- Missing brand direction should become explicit assumptions, not hidden generic styling.
