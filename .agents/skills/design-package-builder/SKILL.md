---
name: design-package-builder
description: Create visual design handoff packages from product docs, PRDs, architecture notes, low-fidelity wireframes, brand constraints, screenshots, or existing app baselines. Use when Codex is asked to create or refine a design system, UI style guide, page UI matrix, high-fidelity page mockup specification, responsive/state coverage, visual acceptance criteria, or implementation-ready UI design source of truth. Do not use for product PRDs, backend architecture, implementation harness planning, or writing production app code.
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
5. After discovery, read `references/output-contract.md` and `references/visual-decision-guide.md`.
6. Produce the design package:
   - `design-system.md`
   - `page-ui-matrix.md`
   - `ui-mockups.md`
   - `visual-acceptance.md`
7. Run the quality checklist in `references/output-contract.md` before finalizing.

## Input Boundaries

- Treat PRDs, architecture docs, and low-fidelity wireframes as product sources, not visual design sources.
- Use low-fidelity wireframes for structure and flow only. Do not copy their plain ASCII styling into the visual system.
- When product docs conflict with the requested visual direction, preserve product requirements and flag the visual conflict.
- If the user provides brand guidelines, screenshots, Figma links, or reference images, register them as visual sources and use them as higher-priority visual evidence than generic assumptions.
- If no visual direction exists, state assumptions and create a coherent system from the product archetype, audience, density, and workflow needs.

## Reference Routing

- Use `references/design-interview-guide.md` for required visual discovery questions and readiness criteria.
- Use `references/output-contract.md` for exact artifact names, headings, templates, and quality checks.
- Use `references/visual-decision-guide.md` for product-archetype visual rules, density, palette, component, state, and mockup decisions.
- Use templates in `assets/templates/` when creating design package artifacts.

## Output Standards

- Prefer implementation-ready design rules over mood words.
- Define concrete tokens: colors, type scale, spacing, radius, shadows, layout grid, breakpoints, and motion rules when relevant.
- Define component variants and states: loading, empty, error, disabled, hover, focus, active, selected, expanded, long content, permission denied, and responsive overflow where applicable.
- Map every important page or route to UI source, breakpoints, states, components, data source, and acceptance evidence.
- Keep high-fidelity mockups as page-level specifications or generated visual artifacts. Do not claim pixel fidelity unless an actual visual reference or generated mockup exists.
- Keep visual assumptions explicit and avoid hiding missing brand or asset decisions in confident prose.
