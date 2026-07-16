---
name: design-package-builder
description: Create distinctive visual design handoff packages from product docs, PRDs, architecture notes, low-fidelity wireframes, brand constraints, screenshots, or existing app baselines. Use when Codex is asked to create or refine a design system, iconography system or icon-library selection, motion system, animation showcase, hero-section choreography, UI style guide, page UI matrix, high-fidelity page mockup specification, responsive/state coverage, visual acceptance criteria, an implementation-ready UI design source of truth, or a UI that must avoid a generic or AI-generated look. Do not use for product PRDs, backend architecture, implementation harness planning, or writing production app code.
---

# Design Package Builder

## Overview

Use this skill to turn product and wireframe inputs into a visual design package that implementation agents can follow. Default all generated artifacts to English unless the user explicitly requests another language.

This skill owns the visual/design layer. It does not create PRDs, backend architecture, implementation plans, harness plans, mission maps, or E2E evidence registers.

## Workflow

1. If the user provides a document folder, inspect it first and identify product inputs such as `PRD.md`, `architecture.md`, `wireframes.md`, and `implementation-plan.md`.
2. Read `references/design-interview-guide.md` before asking design discovery questions.
3. Conduct a concise design interview unless the user explicitly says to skip questions, make assumptions, or draft a first pass immediately.
4. Classify the design target: SaaS app, dashboard, internal tool, public website, marketing page, docs/content site, ecommerce/catalog, mobile app, or hybrid.
5. After discovery, read `references/output-contract.md` and `references/visual-decision-guide.md`. Read `references/icon-system-guide.md` whenever icons are in scope or the icon source is unresolved. Read `references/motion-system-guide.md` whenever motion is requested, implied by a visual direction, or needed to explain hierarchy or state.
6. Establish the product-specific visual thesis before selecting tokens or components: extract brand cues, choose signature design decisions, identify generic defaults to avoid, define realistic content constraints, select an icon direction from the actual semantic inventory, and give every motion pattern a purpose.
7. Produce the design package:
   - `design-system.md`
   - `page-ui-matrix.md`
   - `ui-mockups.md`
   - `visual-acceptance.md`
   - Optional runnable `motion-showcase.html` or bounded files under `motion-demos/` when motion demonstration is requested
8. Run both the quality checklist and the anti-generic review in `references/output-contract.md` before finalizing.

## Input Boundaries

- Treat PRDs, architecture docs, and low-fidelity wireframes as product sources, not visual design sources.
- Use low-fidelity wireframes for structure and flow only. Do not copy their plain ASCII styling into the visual system.
- When product docs conflict with the requested visual direction, preserve product requirements and flag the visual conflict.
- If the user provides brand guidelines, screenshots, Figma links, or reference images, register them as visual sources and use them as higher-priority visual evidence than generic assumptions.
- If no visual direction exists, state assumptions and derive a coherent, product-specific system from the product archetype, audience, content, density, and workflow needs. Do not silently fall back to a generic SaaS or AI-generated aesthetic.

## Reference Routing

- Use `references/design-interview-guide.md` for required visual discovery questions and readiness criteria.
- Use `references/output-contract.md` for exact artifact names, headings, templates, and quality checks.
- Use `references/visual-decision-guide.md` for product-archetype visual rules, density, palette, component, state, and mockup decisions.
- Use `references/icon-system-guide.md` to research current icon libraries, score candidates, define icon tokens, create the semantic inventory, and specify accessibility and implementation rules.
- Use `references/motion-system-guide.md` to select a motion stack, define tokens and choreography, specify hero animation, create runnable demonstrations, and enforce performance and accessibility fallbacks.
- Use templates in `assets/templates/` when creating design package artifacts.

## Output Standards

- Prefer implementation-ready design rules over mood words.
- Define a product-specific visual thesis with three to five concrete brand or context cues, at least two signature design decisions, and explicit anti-patterns. Tie each decision to source evidence or a stated assumption.
- Treat common patterns as risks only when they are unsupported or clustered into a generic composition. Do not mechanically ban gradients, rounded cards, pills, centered layouts, glass effects, or familiar fonts when the brand or interaction model justifies them.
- Use realistic, domain-specific labels, data shapes, content lengths, and asset requirements. Do not invent vague benefit copy, fake metrics, testimonials, or social proof to make a mockup look complete.
- Select one primary functional icon family from a current official-source market scan. Test candidate coverage against the product's real actions, navigation, statuses, and domain objects; do not choose by catalog size or popularity alone.
- Record the chosen icon set, official URL, package or asset source, checked date, version when relevant, license, visual settings, naming rules, and allowed exceptions. Reverify unstable version, pricing, package, and license details at task time.
- Keep brand marks separate from functional UI icons. Do not mix icon families on one product surface unless a documented platform, brand, or coverage exception includes optical normalization rules.
- Include stack-appropriate reference code for one labeled icon action and one icon-only action using the exact chosen import, tokens, accessible naming, decorative hiding, and tooltip behavior.
- Define a motion system with intent categories, technology choice, duration/easing/distance tokens, triggers, interruption rules, responsive variants, reduced-motion behavior, and per-pattern choreography.
- Keep critical content and controls present and operable before animation starts. Treat animation as progressive enhancement; never require a hero entrance to reveal the headline, primary CTA, or essential product proof.
- When motion is requested for a hero or another important surface, provide a storyboard and stack-appropriate runnable demo or reference implementation. Include play, pause/restart, and reduced-motion preview controls in standalone showcases.
- Prefer opacity and transform for routine DOM motion. Justify scroll-linked motion, parallax, blur/filter animation, continuous loops, canvas, video, or animation runtimes with product value and performance evidence.
- Define concrete style-guide sections: overview, color palette, typography, iconography, spacing system, component styles, shadows/elevation, motion system, border radius, opacity/transparency, common Tailwind/CSS usage, reference component code, layout grid, breakpoints, and accessibility rules.
- Define component variants and states: loading, empty, error, disabled, hover, focus, active, selected, expanded, long content, permission denied, and responsive overflow where applicable.
- Map every important page or route to UI source, breakpoints, states, components, data source, and acceptance evidence.
- Require each important page mockup to show how the shared signature decisions appear without weakening task hierarchy, accessibility, or platform conventions.
- Keep high-fidelity mockups as page-level specifications or generated visual artifacts. Do not claim pixel fidelity unless an actual visual reference or generated mockup exists.
- Keep visual assumptions explicit and avoid hiding missing brand or asset decisions in confident prose.
