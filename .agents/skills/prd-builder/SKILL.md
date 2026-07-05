---
name: prd-builder
description: Create product requirement document packages from user needs, including product discovery, implementation-ready architecture, UX flows, and low-fidelity ASCII and Mermaid wireframes. Use when Codex is asked to build, draft, plan, or refine a PRD, product spec, app spec, web product spec, internal tool spec, automation or agent workflow spec, UI wireframes, or architecture for a product idea.
---

# PRD Builder

## Overview

Use this skill to turn a user's product idea or requirement into a complete Markdown PRD package. Default all generated artifacts to English unless the user explicitly requests another language.

## Workflow

1. Read `references/interview-guide.md` before asking discovery questions.
2. Conduct a complete but concise product interview before drafting, unless the user explicitly says to skip questions, make assumptions, or produce a first draft immediately.
3. Classify the product as one or more archetypes: web app, mobile app, internal tool, automation or agent workflow, API or backend service, or hybrid.
4. After discovery, read `references/output-contract.md`, `references/architecture-playbook.md`, and `references/wireframe-guide.md`.
5. Produce the core Markdown artifact package:
   - `PRD.md`
   - `architecture.md`
   - `wireframes.md`
6. Produce `implementation-plan.md` only when the user explicitly asks for delivery sequencing or implementation planning.
7. Run the quality checklist in `references/output-contract.md` before finalizing.

## Interview Rules

- Ask one organized interview message, grouped by topic, rather than many separate turns.
- Do not ask questions already answered by the user's prompt.
- Mark optional questions clearly when they would improve quality but should not block progress.
- If the user authorizes assumptions, draft with explicit assumptions and open questions instead of continuing the interview.
- If the user gives conflicting requirements, resolve them before drafting or call out the conflict in `open questions`.

## Reference Routing

- Use `references/interview-guide.md` for required discovery questions and readiness criteria.
- Use `references/output-contract.md` for the exact artifact names, headings, and final quality checklist.
- Use `references/architecture-playbook.md` for implementation-ready architecture content across web, mobile, internal tools, and automations.
- Use `references/wireframe-guide.md` for ASCII wireframes, Mermaid flows, and required UI states.

## Output Standards

- Prefer specific, buildable requirements over vague product language.
- Tie every major requirement to a user need, workflow, metric, or constraint.
- Include loading, empty, error, permission, and edge states when a UI or workflow has them.
- Keep outputs in the product/spec layer. Do not produce design systems, high-fidelity UI mockups, visual tokens, or page-level visual acceptance specs.
- Keep assumptions explicit and avoid hiding unresolved decisions in confident prose.
- Make architecture technology-neutral unless the user names a stack or the surrounding repo makes the stack obvious.
