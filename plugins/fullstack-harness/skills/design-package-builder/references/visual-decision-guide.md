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

## Builder UX Direction Handoff

Use the PRD's Builder UX Direction Decision before composing pages or choosing tokens. Preserve the named human owner and the status of every choice:

- `selected`: carry it into the design system unless it conflicts with a product requirement, user evidence, platform convention, or accessibility requirement.
- `provisional`: implement it as a reviewable direction and keep the validation need visible.
- `assumed`: do not present it as the builder's decision; keep it easy to revisit.

Translate preference into consequences for task hierarchy, guidance versus expert control, density, layout, feedback, confirmation, recovery, content, and motion. Builder approval proves that the design follows the intended direction. It does not prove usability for representative users or show that they can understand and complete the task.

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
6. Treat a decorative colored side rail or accent stripe (including a top/left accent border on a rounded card) as a near-automatic anti-slop failure, not a style choice to weigh. Independent audits of AI-generated interfaces name this pattern the single most recognizable AI tell (as reliable a signal as em-dash-heavy copy). Allow it only with an airtight, documented state/selection/priority/brand-motif reason recorded in the guardrails table, and prefer an open, undashed, un-railed alternative first. Dashed frames, double frames, and arbitrary corner treatments used as generic section styling fail the same way.
7. Do not remove borders or outlines needed for form controls, keyboard focus, error identification, selected state, data comprehension, or non-text contrast.
8. Do not apply the same faint 1px border to every button, input, image, avatar, and plain content block by default. A uniform component-library or AI-generated border set is a distinct tell from the card and side-rail patterns above; each bordered element still needs its own answer to rule 4, not inherited default styling.

Use the removal test: temporarily remove a container, border, shadow, or accent. If hierarchy, interaction, state, and comprehension remain clear, leave it out.

Research basis checked on 2026-07-21 (refreshed from 2026-07-17):

- [Puck's constrained UI guidance](https://puckeditor.com/blog/ai-slop-vs-constrained-ui) supports explicit component, schema, and composition boundaries for generated interfaces.
- [U.S. Web Design System card guidance](https://designsystem.digital.gov/components/card/) defines cards as modular, single-subject content and says not to use them only for decoration.
- [GOV.UK focus-state guidance](https://design-system.service.gov.uk/get-started/focus-states/) shows why visible borders and outlines must remain when they communicate keyboard focus and contrast.
- [SmoothUI's AI design slop review](https://smoothui.dev/blog/ai-design-slop) recommends a guardrail, critique, repair, and recheck loop instead of a one-shot checklist.
- [Developers Digest: 16 AI design slop patterns](https://www.developersdigest.tech/blog/ai-design-slop-and-how-to-spot-it) and [Impeccable's 46-pattern slop catalog](https://impeccable.style/slop/) independently name the same recurring visual, typography, motion, and copy tells across audited AI-generated sites.
- [925 Studios on AI design tells](https://www.925studios.co/blog/ai-slop-design-tells) and [prg.sh on the purple-gradient origin](https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website) trace the indigo/violet gradient default back to Tailwind's `indigo-500` default color and a training-data feedback loop, not a deliberate brand choice.
- [popularai.org on em-dash cadence](https://www.popularai.org/p/how-to-spot-ai-writing-by-its-em-dashes-and-punch-up-punctuation) and [contentbeta's overused-AI-words list](https://www.contentbeta.com/blog/list-of-words-overused-by-ai/) document the copy-side tells used below.

## Anti-Generic Review

Review the system and every important mockup for unsupported clusters of common AI-generated UI patterns. Named patterns below are sourced from independent 2026 audits of AI-generated interfaces; treat the side-rail/accent-border pattern as a near-automatic failure per the Container & Border rule above, and treat every other pattern as a risk to weigh in combination, not a universal ban.

**Layout and composition:**
- A badge or small pill directly above an oversized centered headline, generic benefit copy, two CTA buttons, and a floating dashboard mockup used as a default hero formula
- Every content group placed inside a floating rounded card, including nested cards that do not communicate hierarchy or interaction
- Identical feature cards built from the same template: a decorative icon tile stacked above a heading and one line of interchangeable copy, repeated in a three-column grid
- Numbered section markers (01 / 02 / 03) used as purely decorative "editorial scaffolding" rather than a real sequence the user follows
- A stat-counter row of large numbers and short labels (for example "10K+ users," "99.9% uptime," "24/7 support") with no cited source
- A testimonial carousel or logo strip of generic circular avatar placeholders, unverifiable names and quotes, or unnamed customer logos
- Uniformly centered or evenly weighted sections that ignore task priority, content shape, reading flow, or data density
- Landing pages that expose every feature, proof point, workflow, and content module at equal weight instead of making a clear editorial choice

**Color, surface, and shape:**
- The specific indigo-to-violet/purple gradient that traces back to Tailwind's `indigo-500` default rather than a chosen brand palette; any near-identical blue-purple gradient used as decoration deserves the same scrutiny
- Glassmorphism or blur effects used as decoration rather than to communicate a real overlay, modal, or layering relationship
- Corner radii pushed past a functional rounding into "blob" shapes (roughly 24px+ on standard-sized cards) with no stated rationale
- Default-dark-mode surfaces paired with colored glow box-shadows and medium-grey body text, kept because it looks "premium" rather than for a stated brand or contrast reason
- Gradient text applied to headlines, which reduces legibility and scannability without a stated purpose
- The same faint 1px border applied to every button, input, image, avatar, and plain content block by default, independent of the control/data/state purpose Container & Border Decision Rules requires
- Excessive pills, glows, icon chips, or soft shadows stacked with a hairline border on the same element without a semantic or brand role

**Typography and iconography:**
- A default font, palette, or component-library appearance left unchanged without an intentional product rationale, including the now-ubiquitous Inter/Poppins/Manrope/Geist/Space Grotesk/Instrument Serif stack (or an oversized italic serif applied to one hero word against an otherwise generic sans-serif) kept only because it shipped with the starting template
- Thin, interchangeable line icons that could illustrate any product, or emoji used as navigation/UI icons in place of a real, evidence-based icon system

**Motion:**
- Default bounce or elastic spring easing applied to ordinary dialogs, buttons, or menus with no product reason (see `references/motion-system-guide.md` for the intent-driven alternative)

**Fabrication:**
- Decorative images, video, or animation added to fill space without helping comprehension, trust, orientation, feedback, or action
- Fabricated metrics, testimonials, customer logos, activity, or polished sample data presented as if factual

Do not fail a design because one familiar pattern appears. Fail or revise it when several unsupported defaults cluster together, when the layout could belong to any product, or when decoration replaces information hierarchy.

### Copy and Wording Anti-Slop Rules

Generic AI-generated copy is as recognizable as generic AI-generated layout. Flag and replace, rather than silently keep, any of these in product copy, headlines, button labels, or written design rationale:

- Marketing-buzzword verbs and adjectives used as filler rather than for a concrete claim: *unlock, elevate, leverage, streamline, empower, supercharge, harness the power of, seamless, robust, cutting-edge, game-changing, revolutionary, world-class, best-in-class, end-to-end, scalable solution*
- Abstract nouns standing in for a specific outcome: *synergy, paradigm shift, actionable insights, drive innovation, drive impact*
- The "setup, em dash, vague uplift" rhythm — a plain claim followed by an em dash and a burst of unearned abstraction — repeated more than once on the same page or in the same document
- Manufactured-contrast rebuttal sentences ("It's not just X — it's Y") used as a stock structure rather than because a real contrast exists
- Generic openers such as "In today's fast-paced world..." or "In the ever-evolving landscape of..."
- Clickbait title templates such as "The Ultimate Guide to X" or "Everything You Need to Know About X" applied to product copy or section headings

Prefer concrete, product-specific claims with a real number, named capability, or verifiable source over any of the above. This rule applies in addition to, not instead of, the exact-wording and bounded-display-contract requirements elsewhere in this package.

Repair generic results in this order:

1. Restore task and content hierarchy.
2. Replace invented or vague content with representative domain content or explicit placeholders; replace marketing-buzzword and manufactured-contrast copy with concrete, product-specific wording per the Copy and Wording Anti-Slop Rules above.
3. Remove unnecessary containers and decorative treatments.
   Remove repeated borders and accent rails before inventing a new decorative replacement; side-rail/accent-border removal comes first, not last, given how strongly it reads as AI-generated.
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
- Interaction rules: focus, hover, active, loading, disabled, selected, expanded, and validation feedback
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
- User evidence and accessibility requirements beat unsupported builder preference. Record the conflict and the validation decision rather than silently changing either source.
- A selected Builder UX Direction controls visual and interaction direction when higher-priority evidence does not conflict; provisional and assumed choices remain visibly unresolved.
- Design system beats one-off mockup styling unless the user accepts an exception.
- Page UI mockups beat low-fidelity wireframes for visual hierarchy and layout detail.
- Low-fidelity wireframes remain authoritative for flow, required regions, supplied exact wording, and bounded display contracts.
- Wireframe style, media, and motion labels define required intent; the design system owns the final visual and choreography choices.
- Missing brand direction should become explicit assumptions, not hidden generic styling.
