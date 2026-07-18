# Visual Decision Guide

Use this guide when turning product inputs into design-system and mockup decisions.

## Product Archetype Rules

SaaS apps, dashboards, and internal tools:

- Prioritize scanning, comparison, repeated action, predictable navigation, dense but organized information, and restrained styling.
- Avoid marketing-style hero layouts, oversized decorative cards, and decorative gradients in operational surfaces.
- Use compact tables, filters, status indicators, sidebars, tabs, split panes, and toolbar actions when workflows need repeated use.

Public websites, marketing pages, and conversion landing pages:

- Make the product, offer, venue, person, or object immediately visible in the first viewport.
- Keep the first viewport to one clear value proposition and one primary action. Give each later section one job and include it only when it helps the user understand the offer, trust it, resolve a blocking objection, or take the next step.
- Do not mirror the whole PRD on the landing page. Move secondary workflows, exhaustive feature detail, long explanations, and low-priority proof to deeper pages, docs, or a bounded FAQ.
- Use visual assets that reveal the actual subject. Avoid purely abstract decoration as the primary visual.
- For every region, label image/media and motion as `required`, `optional`, or `none`, then state its purpose, source or creation need, responsive treatment, and fallback.
- Define conversion states, form states, trust signals, SEO/content modules, and responsive section order.

Docs and content sites:

- Prioritize readable typography, navigation depth, search, table of contents, code/content treatment, and content hierarchy.
- Define article, collection, landing, search, and empty-result patterns when relevant.

Ecommerce and catalog experiences:

- Prioritize product inspection, filtering, comparison, pricing/inventory clarity, PDP/PLP structure, cart boundaries, and trust cues.
- Define image ratios, product card variants, search/filter states, unavailable states, and schema/SEO surfaces when relevant.

Mobile apps:

- Prioritize thumb reach, native navigation patterns, compact states, offline/loading/error handling, and platform conventions.

## Product-Specific Visual Thesis

Establish this thesis before choosing tokens or composing pages:

1. Extract three to five concrete cues from the product, audience, domain, content, brand sources, or physical context. Avoid stopping at mood adjectives such as "clean" or "modern."
2. Select at least two signature decisions across typography, layout rhythm, color proportion, imagery, iconography, shape, interaction, or motion. State where each decision recurs in the system.
3. Name the generic defaults and visual cliches that would weaken this product. Tie each avoided pattern to the target rather than using a universal blacklist.
4. Define realistic content and data constraints: domain vocabulary, likely label lengths, image ratios, data density, empty-state facts, and claims that must not be fabricated.

The result should remain usable without decoration and recognizable without relying only on the logo. Consistency does not require every section to use the same card, alignment, density, or rhythm.

## Taste & Anti-Slop Guardrails

Taste here means product-specific judgment that is visible in the hierarchy, restraint, and recurring decisions. It is not a universal style or a longer blacklist.

Every design system must define:

- A one-sentence taste statement that names the intended character and the concrete typography, composition, color, imagery, or interaction choices that create it
- What receives the strongest emphasis, what stays quiet, and how that priority changes across responsive layouts
- Two or more signature decisions that recur without turning every section into the same component
- The unsupported pattern clusters that would make the product look interchangeable
- A container and border policy that defaults content regions to open layouts and records the purpose of every visible frame
- An evidence-appropriate review path: render, critique, repair, and recheck required breakpoints when visual artifacts or an implementation exist; otherwise run a text-only conformance review and mark render evidence unavailable

### Container & Border Decision Rules

1. Default to an open region. Use typography, spacing, alignment, grid, or a deliberate background change before adding a box.
2. Use a card only for a self-contained, modular subject that can stand independently and usually has its own action, state, or destination. Sequential prose, a simple call to action, or tabular data does not become a card merely to gain a border.
3. At each nesting level, choose one primary grouping cue: whitespace, alignment, background, divider or border, or elevation. Stacking cues requires a named hierarchy, interaction, or state reason.
4. Allow a persistent border when it communicates a control boundary, data structure, focus, selection, validation, status, or necessary contrast. "Decoration," "visual interest," and "make it pop" are not valid purposes.
5. Avoid bordered containers inside bordered containers. Keep the inner border only when it represents an independent interactive, scrollable, selectable, or stateful region.
6. Do not use decorative colored side rails, accent stripes, dashed frames, double frames, or arbitrary corner treatments as generic section styling.
7. Do not remove borders or outlines needed for form controls, keyboard focus, error identification, selected state, data comprehension, or non-text contrast.

Use the removal test: temporarily remove a container, border, shadow, or accent. If hierarchy, interaction, state, and comprehension remain clear, leave it out.

Research basis checked on 2026-07-17:

- [Puck's constrained UI guidance](https://puckeditor.com/blog/ai-slop-vs-constrained-ui) supports explicit component, schema, and composition boundaries for generated interfaces.
- [U.S. Web Design System card guidance](https://designsystem.digital.gov/components/card/) defines cards as modular, single-subject content and says not to use them only for decoration.
- [GOV.UK focus-state guidance](https://design-system.service.gov.uk/get-started/focus-states/) shows why visible borders and outlines must remain when they communicate keyboard focus and contrast.
- [SmoothUI's AI design slop review](https://smoothui.dev/blog/ai-design-slop) recommends a guardrail, critique, repair, and recheck loop instead of a one-shot checklist.

## Anti-Generic Review

Review the system and every important mockup for unsupported clusters of common AI-generated UI patterns:

- A badge, oversized gradient headline, generic benefit copy, two CTA buttons, and a floating dashboard mockup used as a default hero formula
- Every content group placed inside a floating rounded card, including nested cards that do not communicate hierarchy or interaction
- Repeated bordered cards or panels with a colored side rail or accent stripe used as generic decoration rather than a named state, selection, priority, category, or approved brand motif
- Excessive pills, large corner radii, glows, glass effects, gradients, icon chips, or soft shadows without a semantic or brand role
- Uniformly centered or evenly weighted sections that ignore task priority, content shape, reading flow, or data density
- Repeated three-column feature grids, interchangeable icons, and equal-length placeholder copy that could describe any product
- Landing pages that expose every feature, proof point, workflow, and content module at equal weight instead of making a clear editorial choice
- Decorative images, video, or animation added to fill space without helping comprehension, trust, orientation, feedback, or action
- Fabricated metrics, testimonials, customer logos, activity, or polished sample data presented as if factual
- A default font, palette, or component-library appearance left unchanged without an intentional product rationale

Do not fail a design because one familiar pattern appears. Fail or revise it when several unsupported defaults cluster together, when the layout could belong to any product, or when decoration replaces information hierarchy.

Repair generic results in this order:

1. Restore task and content hierarchy.
2. Replace invented or vague content with representative domain content or explicit placeholders.
3. Remove unnecessary containers and decorative treatments.
   Remove repeated borders and accent rails before inventing a new decorative replacement.
4. Apply the product's signature typography, layout, color, imagery, or interaction decisions.
5. Recheck responsive behavior, accessibility, and platform conventions.
6. When visual artifacts or an implementation exist, render again, compare against the taste statement and acceptance gates, and repeat until the package passes or the remaining constraint is explicit. For a spec-only package, repeat the same critique over the Markdown sources, record render evidence as unavailable, and do not claim visual fidelity or implementation verification.

## Design System Coverage

Define only rules that implementation can apply:

- Overview: product archetype, audience, visual intent, density, tone, constraints, and source priority
- Color palette: background, surface, text, border, accent, semantic states, charts if needed
- Typography: font family category, scale, weight, line height, heading/body/caption usage, and how font roles work together
- Iconography: primary library, market evidence, size and weight tokens, semantic inventory, state variants, brand-icon separation, implementation source, and accessibility behavior
- Spacing system: base unit, section rhythm, component padding, grid gaps
- Component styles: buttons, inputs, selects, tables, cards, dialogs, nav, tabs, alerts, charts, content blocks as relevant
- Shadows and elevation: component hierarchy, overlays, panels, and depth rules
- Motion system: purpose, technology and delivery choice, duration/easing/distance tokens, triggers, choreography, interruption, responsive behavior, reduced-motion fallback, and performance limits
- Border radius: token values and component usage rules
- Opacity and transparency: disabled states, overlays, glass/subtle surfaces, and contrast risks
- Layout: grid, max widths, sidebars, headers, responsive breakpoints
- Common Tailwind CSS usage in project: recurring utility patterns, component class patterns, and CSS variable mappings when relevant
- Example component reference design code: a small implementation-oriented component example that demonstrates the style guide
- Product-specific visual thesis: concrete cues, recurring signature decisions, avoided defaults, and content realism rules
- Landing-page simplicity and media plan when relevant: first-viewport message and action, one job per section, content to defer, and per-region image/media/motion labels
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
- For landing pages, the single job of each region, required content, and content intentionally deferred or excluded
- The style direction and visual job of each important region, including whether it should remain open, use a real container, change background, split layout, or apply another hierarchy treatment
- Layout regions
- Component composition
- Approved or draft exact wording, or a bounded display contract that states what the region shows, the intended takeaway or action, the source, and relevant constraints
- State-specific changes
- Responsive behavior
- Asset requirements
- Per-region image/media status (`required`, `optional`, or `none`), purpose, source or creation need, responsive treatment, and fallback
- Product-specific signature decisions and generic patterns intentionally avoided
- Motion purpose, trigger, sequence, responsive variant, reduced-motion fallback, and runnable demo path when applicable
- Visual acceptance criteria

If generating actual bitmap mockups or visual alternatives is requested and image tools are available, use the generated files as visual sources and record their paths in `ui-mockups.md`.

## Conflict Rules

- Product requirements beat visual preference.
- Design system beats one-off mockup styling unless the user accepts an exception.
- Page UI mockups beat low-fidelity wireframes for visual hierarchy and layout detail.
- Low-fidelity wireframes remain authoritative for flow, required regions, supplied exact wording, and bounded display contracts.
- Wireframe style, media, and motion labels define required intent; the design system owns the final visual and choreography choices.
- Missing brand direction should become explicit assumptions, not hidden generic styling.
