---
name: prd-builder
description: Create product requirement document packages from user needs, including product discovery, explicit or recommended frontend stack selection, implementation-ready architecture, UX flows, and low-fidelity ASCII and Mermaid wireframes. Use when Codex is asked to build, draft, plan, or refine a PRD, product spec, app spec, web product spec, internal tool spec, automation or agent workflow spec, UI wireframes, frontend technology recommendation, or architecture for a product idea.
---

# PRD Builder

## Overview

Use this skill to turn a user's product idea or requirement into a complete Markdown PRD package. Default all generated artifacts to English unless the user explicitly requests another language.

## Workflow

1. Read `references/interview-guide.md` before asking discovery questions.
2. Conduct a complete but concise product interview before drafting, unless the user explicitly says to skip questions, make assumptions, or produce a first draft immediately.
3. Classify the product as one or more archetypes: web app, mobile app, internal tool, automation or agent workflow, API or backend service, or hybrid.
4. After discovery, read `references/output-contract.md`, `references/artifact-lifecycle.md`, `references/architecture-playbook.md`, and `references/wireframe-guide.md`. For a web app, internal tool, public website, or hybrid with a browser frontend, also read `references/frontend-stack-selection.md`.
5. Before drafting, inventory earlier documents related to the same product as described in `references/artifact-lifecycle.md`. Do not move anything yet.
6. Draft the core Markdown package in the staging location defined by `references/artifact-lifecycle.md`:
   - `PRD.md`
   - `architecture.md`
   - `wireframes.md`
7. Produce `implementation-plan.md` only when the user explicitly asks for delivery sequencing or implementation planning.
8. Run the quality checklist in `references/output-contract.md` against the staged package.
9. Only after the complete package passes validation, archive the previously inventoried superseded documents under `doc/archived/`, then publish the new package under `doc/`. Never archive documents when the workflow is incomplete, paused, or failing validation.
10. Report the final artifact paths and every archived path.
11. After reporting a completed PRD package, ask whether the user wants to run `$design-package-builder` next using the new package as its product input. Do not invoke the design skill without an explicit yes, and do not offer the handoff while the PRD workflow is incomplete, paused, or failing validation.

## Interview Rules

- Ask one organized interview message, grouped by topic, rather than many separate turns.
- Do not ask questions already answered by the user's prompt.
- Mark optional questions clearly when they would improve quality but should not block progress.
- If the user authorizes assumptions, draft with explicit assumptions and open questions instead of continuing the interview.
- If the user gives conflicting requirements, resolve them before drafting or call out the conflict in `open questions`.

## Reference Routing

- Use `references/interview-guide.md` for required discovery questions and readiness criteria.
- Use `references/output-contract.md` for the exact artifact names, headings, and final quality checklist.
- Use `references/artifact-lifecycle.md` for staging, final `doc/` locations, safe identification of superseded documents, and post-validation archival.
- Use `references/architecture-playbook.md` for implementation-ready architecture content across web, mobile, internal tools, and automations.
- Use `references/frontend-stack-selection.md` to separate frontend technology layers, recommend one product-fit stack, and verify current Cloudflare support when that platform is in scope.
- Use `references/wireframe-guide.md` for ASCII wireframes, Mermaid flows, and required UI states.

## Output Standards

- Prefer specific, buildable requirements over vague product language.
- Keep the current PRD package directly under `doc/`; reserve `doc/archived/` for superseded documents only.
- Tie every major requirement to a user need, workflow, metric, or constraint.
- Include loading, empty, error, permission, and edge states when a UI or workflow has them.
- Keep every low-fidelity wireframe structurally simple regardless of the intended final visual style. For browser or mobile interfaces, ask what overall style the user wants unless the prompt already answers it. If the user authorizes assumptions and gives no direction, record `modern-minimal` as a provisional baseline rather than silently treating it as approved design.
- Keep public-site and landing-page wireframes simple: one clear value proposition and one primary action in the first viewport, one job per section, and secondary detail deferred instead of copying the whole PRD into the page.
- Make every visible wireframe region implementation-ready with either exact UI wording or a bounded display contract that states what the region must show, the intended user takeaway or action, the content or data source, and relevant format or length constraints. Do not leave generic labels such as `Main content`, `Feature section`, or `Card 1` in a final wireframe.
- In each relevant wireframe, label image/media and motion as `required`, `optional`, or `none`, and state the purpose. Also label the intended style direction for each visually important region, such as editorial split, full-bleed product proof, dense comparison, or unframed text. Keep these labels structural; leave tokens, asset art direction, and detailed choreography to the design package.
- Do not use boxes in ASCII wireframes as automatic decoration. A drawn container must represent real grouping, interaction, state, or hierarchy. Do not imply repeated bordered panels with a colored side rail or accent stripe unless the stripe has a named semantic or approved brand role.
- Keep outputs in the product/spec layer. Do not produce design systems, high-fidelity UI mockups, visual tokens, or page-level visual acceptance specs.
- Keep assumptions explicit and avoid hiding unresolved decisions in confident prose.
- Architecture may remain technology-neutral overall. For every product with a browser frontend, record the required or already selected frontend stack, or recommend one explicit stack when the user has not chosen and discovery provides enough evidence. Label the decision status so a recommendation is not misrepresented as a fixed requirement. Record the deployment platform, rendering model, framework, UI library, build tool, and key supporting choices as separate layers.
- Do not present Cloudflare, Astro, React, and Vite as peer alternatives: Cloudflare is a deployment/runtime platform, Astro is a web framework, React is a UI library, and Vite is a build tool that can be paired with React or used by frameworks.
- Keep a decision technology-neutral only when evidence is genuinely insufficient. In that case, document the missing evidence, decision owner, decision deadline, and a time-boxed spike with pass/fail criteria.
- When recommending a fast-moving hosted platform or framework, verify current official documentation and record the check date and sources in `architecture.md`.
