# Design Interview Guide

Use this guide before drafting a design package.

## Required Questions

Ask one organized interview message. Skip questions already answered by the user's prompt or supplied files.

Bullets marked `(AskUserQuestion)` are a closed, enumerable set — resolve them with Claude Code's `AskUserQuestion` tool immediately after the free-text interview message, not as open questions inside it. Everything else stays free text, since it is too product-specific to enumerate.

The closed-set questions fit one or two `AskUserQuestion` calls of at most four questions each. Almost every one carries a skip rule, so a real run asks far fewer. When more than eight are still unresolved, do not open a third call. Drop in this order and record the documented default as an explicit assumption instead:

1. Validation depth — assume documented assumptions.
2. Icon style — assume the primary library's default per `references/icon-system-guide.md`.
3. Motion delivery format — assume storyboard plus implementation code, no runnable showcase.

The architecture-contract questions — styling engine, registry enforcement, and adoption mode — outrank all three. A wrong guess there points the contract check at the wrong allowlist and invalidates the guardrails.

### Product And Audience

- What product or page set is this design package for?
- Who uses it, and what are they trying to accomplish?
- Who is the human builder or product/design decision owner for the UX direction?
- Is the target a SaaS app, dashboard, internal tool, public website, marketing page, docs/content site, ecommerce/catalog, mobile app, desktop app, or hybrid? (AskUserQuestion, using SaaS app/dashboard / public website or marketing page / internal tool / ecommerce or catalog as the four options and the tool's built-in Other for docs/content site, mobile app, desktop app, or hybrid) Skip this when `architecture.md`'s `Product Archetype` already resolved the platform; carry that value forward.
- If the answer is a mobile app, which platform does it target: native iOS, native Android, Flutter (cross-platform), or React Native (cross-platform)? (AskUserQuestion) This decides the visual vocabulary — iOS follows Apple's Human Interface Guidelines, Android follows Material Design, and Flutter or React Native follow the target platform's own convention per `references/visual-decision-guide.md`. Skip it when the PRD or `architecture.md` already resolved the mobile platform.
- If the answer is a desktop app, which platform does it target: macOS, Windows, or cross-platform (e.g. Electron or Tauri)? (AskUserQuestion) This decides platform-native chrome and desktop interaction patterns per `references/visual-decision-guide.md`. Skip it when the PRD or `architecture.md` already resolved the desktop platform.

### Builder UX Direction

- Does the PRD already contain a `Builder UX Direction Decision`? If so, which choices are selected, provisional, or assumed?
- What should the experience optimize first: speed, clarity, guided completion, expert control, exploration, conversion, or content comprehension? (AskUserQuestion, using speed / clarity / guided completion / expert control as the four options and the tool's built-in Other for exploration, conversion, or content comprehension) Skip this question when the PRD's `Builder UX Direction Decision` already resolves the experience priority as `selected`; carry that value forward silently instead. Only ask when it is `provisional` or `assumed`, missing, or the design interview's own free-text discovery surfaces a genuine conflict with it.
- What guidance/control balance, information density, interaction familiarity, primary layout pattern, and confirmation/recovery behavior does the builder prefer? For each of these axes, skip the question when the PRD's `Builder UX Direction Decision` already resolves it as `selected`; carry that value forward silently instead. Only ask about an axis when it is `provisional` or `assumed`, missing, or the design interview's own free-text discovery surfaces a genuine conflict with it.
- What validation depth does the builder expect: documented assumptions, internal prototype review, testing with likely users, or recurring usability benchmarking? (AskUserQuestion, using documented assumptions / internal prototype review / testing with likely users / recurring usability benchmarking as the four options; first to drop when the closed-set budget is full) Skip this question when the PRD's `Builder UX Direction Decision` already resolves the validation depth as `selected`; carry that value forward silently instead. Only ask when it is `provisional` or `assumed`, missing, or the design interview's own free-text discovery surfaces a genuine conflict with it.
- Which preferences are supported by user evidence, and which remain hypotheses that need prototype or usability testing?

### Visual Direction

- Are there existing brand guidelines, logo files, screenshots, Figma frames, websites, or reference products to follow? When the answer names a live reference website rather than a supplied file, see `SKILL.md`'s workflow step 8 for capturing it with a browser tool before extracting brand cues from it.
- Should the design feel dense and operational, editorial and content-led, commercial and conversion-led, premium and minimal, playful, technical, or another direction? (AskUserQuestion, using dense and operational / editorial and content-led / commercial and conversion-led / premium and minimal as the four options and the tool's built-in Other for playful, technical, or another direction) Skip this question when the PRD or `wireframes.md` already records a `selected` interface-style / visual direction; carry that value forward silently instead. Only ask when it is `provisional` or `assumed` (for example a provisional `modern-minimal` baseline), missing, or the design interview's own free-text discovery surfaces a genuine conflict with it.
- Which visual or content details should make the product recognizable even without its logo?
- Are there visual directions or generic AI-UI patterns to avoid?
- Are there existing brand colors, a required palette, or a dark-mode requirement to preserve, or should the palette be recommended? When a recommendation is wanted, choose it with `visual-decision-guide.md`'s Color Palette Decision guidance, and offer `frontend-design` (per `SKILL.md`'s Optional External Skill Assist) for an expert color-pairing pass only after an explicit yes, when the user wants a more distinctive combination than that guidance alone would produce.

### Scope And Pages

- Which routes/pages/screens need high-fidelity UI treatment?
- Which states matter for each page: ready, loading, empty, error, disabled, permission denied, long content, responsive overflow?
- Which breakpoints must be specified? The default required set is 390 / 768 / 1200 / 1440 px; ask only whether the product needs different or additional ones.
- For a landing page, what single message and primary action must the first viewport communicate? Which details can move to deeper pages or be omitted?
- Which page regions require an image, product media, illustration, video, or animation, and what must each asset help the user understand or do?

### Motion Direction

- Which surfaces need motion, and which one purpose does each animation serve: feedback, continuity, processing, or storytelling? An animation that fits none of the four does not ship (see `references/motion-system-guide.md`).
- For a hero, which elements should enter or react: eyebrow, headline, supporting copy, CTA, product media, background, or illustration?
- Beyond the hero, which of these need motion, and what should each communicate: modal/sheet open-close, list add/remove/reorder, toast/notification, skeleton/loading transitions, form validation feedback, drag-and-drop, chart/data-viz updates, scroll-triggered reveal, or empty-state illustration?
- Should motion run once on load, on deliberate interaction, on viewport entry, with scroll progress, or continuously? (AskUserQuestion, using on load / on deliberate interaction / on viewport entry / continuously as the four options and the tool's built-in Other for scroll-progress-linked motion) Which motion must be pausable?
- Is a runnable HTML/React motion showcase required, or is a storyboard plus implementation code sufficient? (AskUserQuestion, using runnable HTML/React showcase / storyboard plus implementation code as the two options and the tool's built-in Other; third to drop when the closed-set budget is full)

### Implementation Constraints

- What frontend stack or component library should the design respect, if any?
- Which styling engine and theming mechanism must the token and primitive layers use: utility CSS, CSS-in-JS, CSS modules, or plain CSS? (AskUserQuestion, using utility CSS (for example Tailwind) / CSS-in-JS / CSS modules / plain CSS as the four options and the tool's built-in Other for a native platform theme system) The engine is swappable per `references/ui-architecture-guide.md`'s Stack Independence, but the answer fixes how tokens are declared and how the contract check recognizes a raw value. Skip it when the PRD or `architecture.md` already names the styling engine; carry that value forward.
- How strictly is the registry enforced: a blocking contract check that fails the build when a page leaves the allowlist, or an advisory allowlist? (AskUserQuestion, using blocking contract check / advisory allowlist as the two options and the tool's built-in Other) Blocking is what `references/ui-architecture-guide.md` assumes — an architecture nothing enforces drifts back. Advisory still gets the full guardrail specification, but `visual-acceptance.md` must record that no check fails when a rule is violated.
- Is this a greenfield build, or must an existing codebase be migrated in phases? (AskUserQuestion, using greenfield / phased migration of an existing codebase as the two options and the tool's built-in Other for a partial rewrite) This picks the adoption sequence in `references/ui-architecture-guide.md`: greenfield lands phases 1–2 before the first route and phase 5 with the first two routes, while a migration runs the phases in order. For a migration, also ask in free text which routes are highest traffic or highest risk, and which existing components must keep working unchanged.
- Which animation runtime owns enter/exit, layout change, list insertion and removal, dialogs and drawers, gesture, and state choreography, given that the style layer already owns hover, focus, pressed, and color transitions? (AskUserQuestion, using Web Animations API (no dependency) / Motion (Framer Motion) / GSAP / native platform animation API as the four options and the tool's built-in Other for Rive or another dependency) `references/ui-architecture-guide.md`'s Motion Architecture splits motion three ways; only the runtime half needs a dependency decision. Ask in the same breath whether route-level transitions are wanted, and skip the question when a runtime is already approved in the project.
- Is an icon library already installed or required by the platform, brand, component library, or engineering team?
- Which domain-specific actions or objects need icons?
- Are outline, filled, duotone, compact, or platform-native icon styles preferred? (AskUserQuestion, using outline / filled / duotone / platform-native as the four options and the tool's built-in Other for compact; second to drop when the closed-set budget is full)
- Are brand or partner logos needed, and are there trademark, licensing, self-hosting, offline, or bundle-size constraints?
- Are there accessibility, localization, dark mode, charting, table density, mobile, or content/CMS constraints?
- Are there performance budgets, low-power/device constraints, reduced-motion requirements, autoplay restrictions, or analytics events that affect animation?
- Is representative product copy, data, or imagery available, or should the package define realistic content constraints without inventing claims?
- The mockup deliverable defaults to real static HTML files under `mockups/` for every platform, styled to the resolved platform's own conventions (see `references/output-contract.md`); confirm whether additional generated bitmap images or prototypes are also wanted if image tools are available.

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
- Required states and the required viewport set
- Brand/source references or confirmation that none exist
- Implementation constraints that affect components and layout
- Styling engine and theming mechanism, so the token layer has one declaration form
- Registry enforcement mode: a blocking contract check or an advisory allowlist
- Adoption mode: greenfield, or a phased migration with its first routes named
- Any conflict between builder preference and user evidence, product requirements, platform conventions, or accessibility

If the user authorizes assumptions, draft with explicit assumptions and open questions rather than continuing the interview.
