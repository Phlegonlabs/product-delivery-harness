# Design Interview Guide

Use this guide before drafting a design package.

## Required Questions

Ask one organized interview message. Skip questions already answered by the user's prompt or supplied files.

Bullets marked `(AskUserQuestion)` are a closed, enumerable set — resolve them with Claude Code's `AskUserQuestion` tool immediately after the free-text interview message, not as open questions inside it. Everything else stays free text, since it is too product-specific to enumerate.

### Product And Audience

- What product or page set is this design package for?
- Who uses it, and what are they trying to accomplish?
- Who is the human builder or product/design decision owner for the UX direction?
- Is the target a SaaS app, dashboard, internal tool, public website, marketing page, docs/content site, ecommerce/catalog, mobile app, or hybrid? (AskUserQuestion, using SaaS app/dashboard / public website or marketing page / internal tool / ecommerce or catalog as the four options and the tool's built-in Other for docs/content site, mobile app, or hybrid)

### Builder UX Direction

- Does the PRD already contain a `Builder UX Direction Decision`? If so, which choices are selected, provisional, or assumed?
- What should the experience optimize first: speed, clarity, guided completion, expert control, exploration, conversion, or content comprehension? (AskUserQuestion, using speed / clarity / guided completion / expert control as the four options and the tool's built-in Other for exploration, conversion, or content comprehension)
- What guidance/control balance, information density, interaction familiarity, primary layout pattern, and confirmation/recovery behavior does the builder prefer?
- What validation depth does the builder expect: documented assumptions, internal prototype review, testing with likely users, or recurring usability benchmarking? (AskUserQuestion, using documented assumptions / internal prototype review / testing with likely users / recurring usability benchmarking as the four options)
- Which preferences are supported by user evidence, and which remain hypotheses that need prototype or usability testing?

### Visual Direction

- Are there existing brand guidelines, logo files, screenshots, Figma frames, websites, or reference products to follow?
- Should the design feel dense and operational, editorial and content-led, commercial and conversion-led, premium and minimal, playful, technical, or another direction? (AskUserQuestion, using dense and operational / editorial and content-led / commercial and conversion-led / premium and minimal as the four options and the tool's built-in Other for playful, technical, or another direction)
- Which visual or content details should make the product recognizable even without its logo?
- Are there visual directions or generic AI-UI patterns to avoid?

### Scope And Pages

- Which routes/pages/screens need high-fidelity UI treatment?
- Which states matter for each page: ready, loading, empty, error, disabled, permission denied, long content, responsive overflow?
- Which breakpoints must be specified?
- For a landing page, what single message and primary action must the first viewport communicate? Which details can move to deeper pages or be omitted?
- Which page regions require an image, product media, illustration, video, or animation, and what must each asset help the user understand or do?

### Motion Direction

- Which surfaces need motion, and what should each animation communicate: hierarchy, feedback, continuity, orientation, or storytelling?
- For a hero, which elements should enter or react: eyebrow, headline, supporting copy, CTA, product media, background, or illustration?
- Beyond the hero, which of these need motion, and what should each communicate: modal/sheet open-close, list add/remove/reorder, toast/notification, skeleton/loading transitions, form validation feedback, drag-and-drop, chart/data-viz updates, scroll-triggered reveal, or empty-state illustration?
- Should motion run once on load, on deliberate interaction, on viewport entry, with scroll progress, or continuously? (AskUserQuestion, using on load / on deliberate interaction / on viewport entry / continuously as the four options and the tool's built-in Other for scroll-progress-linked motion) Which motion must be pausable?
- Is a runnable HTML/React motion showcase required, or is a storyboard plus implementation code sufficient? (AskUserQuestion, using runnable HTML/React showcase / storyboard plus implementation code as the two options and the tool's built-in Other)

### Implementation Constraints

- What frontend stack or component library should the design respect, if any?
- Is CSS, Web Animations API, Motion, GSAP, Rive, a native platform motion API, or another animation dependency already approved? (AskUserQuestion, using CSS/Web Animations API / Motion (Framer Motion) / GSAP / native platform motion API as the four options and the tool's built-in Other for Rive or another dependency)
- Is an icon library already installed or required by the platform, brand, component library, or engineering team?
- Which domain-specific actions or objects need icons?
- Are outline, filled, duotone, compact, or platform-native icon styles preferred? (AskUserQuestion, using outline / filled / duotone / platform-native as the four options and the tool's built-in Other for compact)
- Are brand or partner logos needed, and are there trademark, licensing, self-hosting, offline, or bundle-size constraints?
- Are there accessibility, localization, dark mode, charting, table density, mobile, or content/CMS constraints?
- Are there performance budgets, low-power/device constraints, reduced-motion requirements, autoplay restrictions, or analytics events that affect animation?
- Is representative product copy, data, or imagery available, or should the package define realistic content constraints without inventing claims?
- Should the output be only Markdown specs, or should actual mockup images/prototypes be generated if tools are available?

## Readiness Criteria

The design package is ready to draft when these are known or explicitly assumed:

- Product archetype and target audience
- Human Builder UX Direction owner plus concrete selected, provisional, or assumed choices for experience priority, guidance/control, density, interaction/layout, confirmation/recovery, and validation depth
- Key pages/routes
- Visual direction or allowed assumptions
- Brand/context cues and anti-patterns, or permission to derive them
- Icon source constraints and representative icon needs, or permission to research and recommend them
- Motion scope, trigger, delivery format, and reduced-motion behavior, or an explicit `n/a`. Scope includes non-hero surfaces in play — modal/sheet, list add/remove/reorder, toast, skeleton/loading, form validation, drag-and-drop, chart/data-viz, scroll-triggered reveal, empty state — each addressed or explicitly marked `n/a`
- Landing-page content priority and per-region image/media/motion needs, or explicit permission to derive them
- Required states and breakpoints
- Brand/source references or confirmation that none exist
- Implementation constraints that affect components and layout
- Any conflict between builder preference and user evidence, product requirements, platform conventions, or accessibility

If the user authorizes assumptions, draft with explicit assumptions and open questions rather than continuing the interview.
