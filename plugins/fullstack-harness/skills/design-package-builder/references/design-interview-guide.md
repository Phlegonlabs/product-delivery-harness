# Design Interview Guide

Use this guide before drafting a design package.

## Required Questions

Ask one organized interview message. Skip questions already answered by the user's prompt or supplied files.

### Product And Audience

- What product or page set is this design package for?
- Who uses it, and what are they trying to accomplish?
- Is the target a SaaS app, dashboard, internal tool, public website, marketing page, docs/content site, ecommerce/catalog, mobile app, or hybrid?

### Visual Direction

- Are there existing brand guidelines, logo files, screenshots, Figma frames, websites, or reference products to follow?
- Should the design feel dense and operational, editorial and content-led, commercial and conversion-led, premium and minimal, playful, technical, or another direction?
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
- Should motion run once on load, on deliberate interaction, on viewport entry, with scroll progress, or continuously? Which motion must be pausable?
- Is a runnable HTML/React motion showcase required, or is a storyboard plus implementation code sufficient?

### Implementation Constraints

- What frontend stack or component library should the design respect, if any?
- Is CSS, Web Animations API, Motion, GSAP, Rive, a native platform motion API, or another animation dependency already approved?
- Is an icon library already installed or required by the platform, brand, component library, or engineering team?
- Which domain-specific actions or objects need icons, and are outline, filled, duotone, compact, or platform-native styles preferred?
- Are brand or partner logos needed, and are there trademark, licensing, self-hosting, offline, or bundle-size constraints?
- Are there accessibility, localization, dark mode, charting, table density, mobile, or content/CMS constraints?
- Are there performance budgets, low-power/device constraints, reduced-motion requirements, autoplay restrictions, or analytics events that affect animation?
- Is representative product copy, data, or imagery available, or should the package define realistic content constraints without inventing claims?
- Should the output be only Markdown specs, or should actual mockup images/prototypes be generated if tools are available?

## Readiness Criteria

The design package is ready to draft when these are known or explicitly assumed:

- Product archetype and target audience
- Key pages/routes
- Visual direction or allowed assumptions
- Brand/context cues and anti-patterns, or permission to derive them
- Icon source constraints and representative icon needs, or permission to research and recommend them
- Motion scope, trigger, delivery format, and reduced-motion behavior, or an explicit `n/a`
- Landing-page content priority and per-region image/media/motion needs, or explicit permission to derive them
- Required states and breakpoints
- Brand/source references or confirmation that none exist
- Implementation constraints that affect components and layout

If the user authorizes assumptions, draft with explicit assumptions and open questions rather than continuing the interview.
