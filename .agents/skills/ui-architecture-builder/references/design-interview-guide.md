# Design Interview Guide

Use this guide before drafting a UI architecture package.

## Required Questions

Ask one organized interview message. Skip questions already answered by the user's prompt or supplied files.

Bullets marked `(AskUserQuestion)` are a closed, enumerable set. Use the host's structured closed-choice facility when it is available. When it is not, present the same options as numbered closed choices and include `Other`; do not select a default, remove choices, or convert the decision into an open-ended question. Everything else stays free text because it is product-specific.

Resolve closed product and technical choices in at most three dependency waves, with at most four questions in each wave:

1. **Target and platform-independent decisions.** Resolve the design target first, plus platform-independent choices such as registry enforcement, implementation adoption mode, experience priority, or validation depth as space allows.
2. **Conditional platform resolution.** Run this wave only when the target is mobile, desktop, or hybrid and the upstream package did not resolve the platform. Resolve native/cross-platform and platform family before continuing.
3. **Platform-specific and remaining decisions.** Ask styling/theming mechanism and animation runtime only now, using options valid for the resolved platform, then fill remaining slots with still-unanswered validation, motion, or icon choices.

Never ask styling, theming, or runtime questions while the design target or required platform is unresolved. Skip questions already answered by the prompt or supplied files. If more unresolved closed decisions remain after the bounded waves, leave them as explicit open questions; do not silently default them.

Visual Preference Discovery is separate from those closed technical waves. When `frontend-design` is loaded and the user authorizes the exploration, first read the product sources and the skill's Purpose, Tone, Constraints, and Differentiation criteria. Derive one compact Ask User call of project-specific questions and choices from that evidence. Do not reuse a fixed style catalog across products. Each question offers two to four grounded choices plus the tool's built-in `Other`; a follow-up call is allowed only when the first answer exposes one material unresolved preference.

When a same-product UI package already exists, freeze it before this interview and switch to package enhancement mode. Ask only about the requested add/modify/remove delta or conflicts it creates. Do not reopen untouched baseline decisions. Package enhancement is separate from implementation adoption mode: enhancement revises the design package; greenfield or phased migration controls how code adopts it.

### Product And Audience

- What product or page set is this UI architecture package for?
- Who uses it, and what are they trying to accomplish?
- Who is the human builder or product/design decision owner for the UX direction?
- Is the target a SaaS app, dashboard, internal tool, public website, marketing page, docs/content site, ecommerce/catalog, mobile app, desktop app, or hybrid? (AskUserQuestion, using SaaS app/dashboard / public website or marketing page / internal tool / ecommerce or catalog as the four options and the tool's built-in Other for docs/content site, mobile app, desktop app, or hybrid) Skip this when `architecture.md`'s `Product Archetype` already resolved the platform; carry that value forward.
- If the answer is a mobile app, which platform does it target: native iOS, native Android, Flutter (cross-platform), or React Native (cross-platform)? (AskUserQuestion) This decides the visual vocabulary — iOS follows Apple's Human Interface Guidelines, Android follows Material Design, and Flutter or React Native follow the target platform's own convention per `references/visual-decision-guide.md`. Skip it when the PRD or `stack-decisions.md` already resolved the mobile platform.
- If the answer is a desktop app, which platform does it target: macOS, Windows, or cross-platform (e.g. Electron or Tauri)? (AskUserQuestion) This decides platform-native chrome and desktop interaction patterns per `references/visual-decision-guide.md`. Skip it when the PRD or `stack-decisions.md` already resolved the desktop platform.

### Builder UX Direction

- Does the PRD already contain a `Builder UX Direction Decision`? If so, which choices are selected, provisional, or assumed?
- What should the experience optimize first: speed, clarity, guided completion, expert control, exploration, conversion, or content comprehension? (AskUserQuestion, using speed / clarity / guided completion / expert control as the four options and the tool's built-in Other for exploration, conversion, or content comprehension) Skip this question when the PRD's `Builder UX Direction Decision` already resolves the experience priority as `selected`; carry that value forward silently instead. Only ask when it is `provisional` or `assumed`, missing, or the design interview's own free-text discovery surfaces a genuine conflict with it.
- What guidance/control balance, information density, interaction familiarity, primary layout pattern, and confirmation/recovery behavior does the builder prefer? For each of these axes, skip the question when the PRD's `Builder UX Direction Decision` already resolves it as `selected`; carry that value forward silently instead. Only ask about an axis when it is `provisional` or `assumed`, missing, or the design interview's own free-text discovery surfaces a genuine conflict with it.
- What validation depth does the builder expect: documented assumptions, internal prototype review, testing with likely users, or recurring usability benchmarking? (AskUserQuestion, using documented assumptions / internal prototype review / testing with likely users / recurring usability benchmarking as the four options; first to drop when the closed-set budget is full) Skip this question when the PRD's `Builder UX Direction Decision` already resolves the validation depth as `selected`; carry that value forward silently instead. Only ask when it is `provisional` or `assumed`, missing, or the design interview's own free-text discovery surfaces a genuine conflict with it.
- Which preferences are supported by user evidence, and which remain hypotheses that need prototype or usability testing?

### Visual Direction

- Are there existing brand guidelines, logo files, screenshots, Figma frames, websites, or reference products to follow? When the answer names a live reference website rather than a supplied file, see `SKILL.md`'s workflow step 8 for capturing it with a browser tool before extracting brand cues from it.
- Which visual or content details should make the product recognizable even without its logo?
- Are there visual directions or generic AI-UI patterns to avoid?
- Are there existing brand colors, a required palette, or a dark-mode requirement to preserve, or should the palette be recommended? When a recommendation is wanted, choose it with `visual-decision-guide.md`'s Color Palette Decision guidance, and offer `frontend-design` (per `SKILL.md`'s Optional External Skill Assist) for an expert color-pairing pass only after an explicit yes, when the user wants a more distinctive combination than that guidance alone would produce.

### Dynamic Visual Preference Discovery

Use `frontend-design` to analyze the product before composing the Ask User choices. The choices must be specific to this audience, domain, content, brand evidence, and representative screens. Ask only unresolved dimensions, choosing up to four that will materially separate candidate directions:

- What should receive the strongest visual emphasis, and what should stay quiet?
- What should someone remember after seeing the interface once?
- Which product-specific composition or interaction approaches are credible here, and how far from familiar conventions may the candidates go?
- Which supplied references, physical-world cues, brand materials, or existing product surfaces should influence the work?
- Which patterns, moods, or competitor similarities must the directions avoid?
- What information-density, imagery, surface, and motion tradeoffs matter for this product?

Do not ask the user to choose token values, font sizes, spacing steps, radius values, primitive variants, or registry structure. Do not hardcode reusable labels such as editorial, premium minimal, playful, technical, or operational as the product's options. A context-specific choice may use one of those words only when the source analysis makes it meaningful and pairs it with concrete product consequences.

Record the answers in a non-binding Visual Preference Brief:

```text
Purpose and audience:
Strongest emphasis:
Memorable differentiator:
Reference and brand cues:
Avoid:
Density / composition tolerance:
Imagery / surface / motion appetite:
Evidence status: selected / provisional / assumed
```

The brief guides two or three distinct HTML directions. It does not freeze the palette, typography, spacing, components, tokens, primitives, recipes, or registry.

### Scope And Pages

- Which routes/pages/screens need high-fidelity UI treatment?
- Which of the eleven states matter for each page, and which are genuinely `n/a`: ready, loading, empty, error, disabled, permission denied, stale, expired, long content, reduced motion, mobile reflow? Every page carries ready, long content, reduced motion, and mobile reflow; the rest need a reason to be `n/a` (see `references/ui-architecture-guide.md`'s State Matrix).
- Which responsive verification set must be specified? It follows the resolved platform. For a web target the default required set is 390 / 768 / 1200 / 1440 px. For a native or desktop target it is that platform's own model — iOS/macOS size classes and safe areas, Android window size classes, or the named desktop window sizes — and pixel breakpoints do not apply (see `references/visual-decision-guide.md`). Ask only whether the product needs different or additional entries in its own set.
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
- Which styling engine and theming mechanism must the token and primitive layers use? (AskUserQuestion) Offer the options the resolved platform actually has. For a web target: utility CSS (for example Tailwind) / CSS-in-JS / CSS modules / plain CSS. For a native or desktop target: the resolved toolchain's own theming mechanism, and ask where the tokens are declared inside it — SwiftUI view modifiers plus a theme type or asset catalog for iOS/macOS, `MaterialTheme` tokens for Jetpack Compose, `ThemeData` for Flutter, `StyleSheet` plus a theme provider for React Native, or XAML resource styles for WinUI. Use the tool's built-in Other for anything else. The engine is swappable per `references/ui-architecture-guide.md`'s Stack Independence, but the answer fixes how tokens are declared and how the contract check recognizes a raw value. Skip it when an upstream document already fixes the mechanism: for a web target that is `stack-decisions.md`'s `Frontend Technology Decision` → `Styling and components` row. A native-only product has no `Frontend Technology Decision` section at all, so read `stack-decisions.md`'s `Mobile/Desktop Technology Decision` → `Toolchain` row instead; the toolchain's own theming mechanism is the answer. Carry that value forward.
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

The hard-limit and exploration inputs are ready when these are known or explicitly assumed:

- Product archetype and target audience
- Human Builder UX Direction owner plus concrete selected, provisional, or assumed choices for experience priority, guidance/control, density, interaction/layout, confirmation/recovery, and validation depth
- Key pages/routes
- A project-specific Visual Preference Brief, or an explicit record that Frontend Design Preference & HTML Exploration was not used or was rejected
- One or two exact representative `UI-*` screen IDs for the candidate HTML directions when exploration is used
- Brand/context cues and anti-patterns, or permission to derive them
- Icon source constraints and representative icon needs, or permission to research and recommend them
- Motion scope, trigger, delivery format, and reduced-motion behavior, or an explicit `n/a`. Scope includes non-hero surfaces in play — modal/sheet, list add/remove/reorder, toast, skeleton/loading, form validation, drag-and-drop, chart/data-viz, scroll-triggered reveal, empty state — each addressed or explicitly marked `n/a`
- Landing-page content priority and per-region image/media/motion needs, or explicit permission to derive them
- Required states and the required responsive verification set: the pixel viewports for a web target, or the platform's size classes or window sizes for a native or desktop target
- Brand/source references or confirmation that none exist
- Implementation constraints that affect components and layout
- Styling engine and theming mechanism, so the token layer has one declaration form
- Registry enforcement mode: a blocking contract check or an advisory allowlist
- Adoption mode: greenfield, or a phased migration with its first routes named
- Any conflict between builder preference and user evidence, product requirements, platform conventions, or accessibility

Tokens, primitives, components, recipes, and the registry are not ready to draft until two or three candidate HTML directions have been compared, a consolidated selected HTML direction exists, and the human owner has explicitly approved it. If exploration is not used, draft with explicit assumptions and do not claim approved-HTML extraction.
