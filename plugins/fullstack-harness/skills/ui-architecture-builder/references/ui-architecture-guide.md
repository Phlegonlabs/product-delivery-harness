# UI Architecture Guide

This guide defines the architecture the package specifies, and how to derive it from real product inputs. `references/output-contract.md` holds the exact artifact structure; this file holds the model and the decision method.

The point of the published architecture is a single rule:

> A page cannot be freely designed. A page may only use approved content contracts, page recipes, product components, and primitives.

That rule starts after the validated package is approved and published. In the preferred exploration path, `frontend-design` produces two or three direction-local HTML candidates for the same representative screens, Hallmark audits their structural difference and anti-slop quality without editing them, the human selects or mixes them, and the human explicitly approves consolidated selected HTML bound to an immutable digest manifest. Tokens, primitives, components, recipes, and the registry are then extracted from that approved source. Candidate HTML is not required to obey a registry that has not been derived yet. When exploration is explicitly `not used` or `rejected`, the validated and published package becomes binding from its recorded product inputs and explicit visual assumptions; it must not claim approved-HTML extraction.

## Layer Model

```text
Product rules
  ├── Content contracts
  └── Route and state contracts
        ▼
Visual Preference Brief
        |
Two or three candidate HTML directions
        |
Hallmark candidate audits (read-only evidence)
        |
Human-approved selected HTML + digest manifest
        |
Design tokens
  ├── Visual tokens
  ├── Layout tokens
  └── Motion tokens
        ▼
UI primitives
  ├── Layout primitives
  ├── Surface primitives
  ├── Typography primitives
  └── Control primitives
        ▼
Product components
        ▼
Interaction and motion patterns
        ▼
Page recipes
        ▼
Routes / pages
        ▼
Automated verification
```

Every component belongs to exactly one layer and composes only layers above it in this list. Nothing depends downward toward pages.

## Source Of Truth Precedence

When two sources disagree, the higher one wins:

```text
Product rules
> Content contract
> Human-approved selected HTML and digest manifest, when approved
> Explicit visual assumptions, when exploration is not used or rejected
> Page recipe
> Product component
> Primitive contract
> Design token
> Page-specific preference
```

Page-specific preference is last after the architecture freeze. "This page looks better with a bit more space" is not a reason to leave the published contract; it is a reason to change the token or primitive, or to add a variant. Before that freeze, candidate HTML may explore direction-local values, and the approved selected HTML outranks the extracted visual layers when checking whether extraction changed the chosen design.

Rejected candidate HTML does not enter this precedence list. The approved selected HTML does: it is non-canonical exploration evidence retained as the visual source from which the canonical package is extracted. Its per-screen SHA-256 values and manifest SHA-256 bind the approval to exact bytes. Implementation consumes the canonical package, while reviewers use the approved selected HTML to catch extraction drift. Hallmark reports are review evidence, not a source of product authority, and never outrank the human decision.

## Layer Responsibilities

| Layer | Owns | Must not own |
| --- | --- | --- |
| Product rules | What the product must always show, never hide, and never claim | Visual values |
| Content contracts | Required fields, length limits, formats, CTA counts, empty/long-content handling, what may never be truncated away | Layout, color |
| Route and state contracts | Which routes exist, which states each must support, what SSR/no-JS must still render | Component internals |
| Visual derivation source | Approved selected HTML bound to its digest manifest, or explicit visual assumptions when exploration is not used or rejected | Product scope or hard-limit changes |
| Hallmark review evidence | Named structural and anti-slop findings for candidate, selected, and final projections | Editing files, selecting a direction, or changing product authority |
| Design tokens | Every repeated raw visual, layout, and motion value extracted from the visual derivation source | Markup, component structure |
| Layout primitives | Space, flow, alignment, max width, responsive rearrangement | Color, background, border, elevation, domain content |
| Surface primitives | Background, border, divider, radius, elevation, and the padding of the surface itself | Spacing between its own children (it wraps a layout primitive), domain content |
| Typography primitives | Type role, size, weight, line height, truncation and wrapping behavior | Layout, color decisions outside the role's token |
| Control primitives | Interaction, variants, sizes, states, focus, accessible name, hit target | Page layout, domain rules, data access |
| Product components | Domain naming, required content order, composition of primitives | Raw token values, ad-hoc spacing or color, data fetching |
| Motion patterns | Registered variants, durations, easing, choreography, reduced-motion behavior | Carrying information that exists nowhere else |
| Page recipes | Section order, container, density, allowed surfaces, forbidden patterns | New visual treatment |
| Routes / pages | Route composition, data, page state | Any new visual value or component |

## Derivation Method

Work from the real screens and product rules, not from a component-library catalog.

1. **Content contracts first.** Freeze routes, flow, required regions, exact wording or display contracts, never-drop fields, platform, required states, accessibility, and product scope. Do not define tokens or visual primitives.
2. **Dynamic Visual Preference Discovery.** Read the product sources and `frontend-design`, derive product-specific choices from Purpose, Tone, Constraints, and Differentiation, and ask them with the host's Ask User tool. Record a non-binding Visual Preference Brief. Never use a fixed style catalog or ask the user to choose token values.
3. **Representative screens.** Obtain authorization for the same one or two `UI-*` screens that best expose hierarchy, content density, controls, imagery, and motion. Every candidate direction implements this exact set.
4. **Two or three candidate HTML directions.** Invoke `frontend-design` separately for each direction. Every execution receives the same hard limits and preference brief, commits to one clear direction, and produces complete dependency-free HTML for every representative screen. Candidate-local CSS values and composition are allowed. A later candidate must differ from the earlier ones across both material visual axes and its structural fingerprint; changing only color does not count.
5. **Read-only Hallmark candidate audit.** When Hallmark is loaded, audit every candidate against the same product inputs and scope. Save named findings with exact paths, severity, and one-line repairs beside each candidate as `hallmark-audit.md`. Critical or major structural-template findings return to `frontend-design` for repair. Hallmark never edits a candidate or chooses the winner. When Hallmark is unavailable, record that status and use the existing taste verifier without claiming a Hallmark pass.
6. **Human comparison and selected HTML.** Render or otherwise make every candidate directly reviewable. Show the structural fingerprints and concise audit summaries, then use Ask User so the human can select, reject, or mix cues. A mix requires one consolidated `visual-directions/selected/` HTML pass. The human must explicitly approve that selected HTML. Agent or delegated selection does not unlock the next step.
7. **Immutable approval binding.** Store selected files only under `visual-directions/selected/`. Record an ordered manifest containing each representative `ui_id`, canonical HTML path, and lowercase SHA-256, then hash that manifest. Put the manifest SHA-256 in the human approval evidence. Immediately before Dynamic Workflow launch, the parent re-reads and hashes every selected file and records manifest-bound verification; the workflow independently recomputes the canonical manifest SHA-256. Any byte, path, or order change invalidates approval and requires a fresh audit and human approval.
8. **Token extraction.** Inventory repeated actual values in the approved selected HTML and name the semantic visual, layout, and motion tokens. Do not retrofit the selected HTML to a preselected scale or palette. Record selected-HTML source evidence for every token group. When exploration is not used or rejected, derive the package from explicit assumptions and label that path instead of claiming selected-HTML extraction.
9. **Layout primitives.** Extract the spacing and flow patterns that repeat in the approved selected HTML — page shell and widths, section rhythm, stacks, clusters, and grids — then give each a closed set of variants.
10. **Surface primitives.** Extract surviving background, border, divider, radius, elevation, and surface-padding treatments. Apply the Container & Border Decision Rules; if a required repair materially changes the approved direction, update selected HTML, recompute the manifest, and obtain fresh approval before extraction continues.
11. **Typography and control primitives.** Extract type roles and interactive atoms from the approved selected HTML, then define their variants, sizes, states, focus, accessible naming, and platform hit targets.
12. **Product components.** Name recurring domain compositions and bind each to its content contract. A composition that appears once stays inside that page.
13. **Motion patterns.** Split approved motion by mechanism, then register every repeated variant. A published page may reference registered variants only.
14. **Page recipes and registry.** Derive each representative recipe from the approved selected HTML, extend recipes to remaining routes without inventing a new direction, and emit the machine-readable allowlist.
15. **Verification.** Prove that canonical mockups and the extracted system reproduce the approved selected HTML. When Hallmark is loaded, audit the final mockups and design-system projection for extraction drift and new anti-slop findings. Then define the contract checks, viewport set, and state set that prevent later drift.

Check the direction at the end: a layout primitive that sets color, a surface that spaces its own children, a product component holding a raw hex value, or a page defining its own button means a layer boundary leaked.

## Closed Variant Sets

After selected-HTML approval and extraction, every primitive prop is a closed set, never a free value. Candidate HTML is exempt because it exists to discover the set.

```text
Good:  gap="4"        size="md"       variant="raised"      density="compact"
Bad:   gap="13px"     height={44}     style={{ gap: 13 }}   className="mt-[13px]"
```

A closed set is what makes the registry checkable and what makes a new page impossible to drift. When a page genuinely needs a value the set does not contain, the fix is to add a variant to the primitive and the registry — a reviewable change in one place — not to pass a raw value at the call site.

Record for each primitive: the variant names, what each is for, and what it must not be used for. A variant with no stated purpose gets deleted, not documented.

## Motion Architecture

Split motion by mechanism, and give each mechanism the work it is actually good at:

| Mechanism | Use for | Example technology |
| --- | --- | --- |
| Style-layer transitions | Hover, focus, pressed, color and simple opacity transitions | CSS transitions; platform-native state styling |
| Animation runtime | Enter/exit, layout change, list insertion and removal, dialogs and drawers, gesture, shared element, state choreography | An animation library, the platform's animation API |
| Route-level transition | Continuity across navigation | View transitions, native navigation transitions |

Rules:

- Motion never carries information that exists nowhere else. Remove the animation and the interface still tells the whole story.
- No permanent looping animation.
- Do not hydrate or wake an interactive runtime on a static page just to fade content in.
- Avoid scale and parallax on large regions.
- Reduced motion shows the final state, not a slower version of the entrance.
- Every animation has one purpose: feedback, continuity, processing, or storytelling. No fourth category, and no decoration.
- Pages reference registered variants only. Duration, distance, easing, and spring values live in motion tokens.
- Set the reduced-motion policy once, globally, and let variants inherit it, instead of repeating the check at each call site.

## Page Recipes

A page recipe is the only legal way to assemble a route. Each recipe fixes:

- Section order, top to bottom
- The container size the route uses
- The section density
- Allowed surfaces — the visual treatments this route may use at all
- Required product components and their content contracts
- Forbidden patterns — the specific compositions this route must never grow into
- Required states, and what must still render with no JavaScript

Forbidden patterns matter as much as the allowed list. They are where a route's known failure mode gets written down: a wall of cards, a feature grid, a second primary action, a comparison table on a page that is supposed to ask one question. Derive them from the anti-slop review and from what the route has drifted into before.

An agent reads the recipe for the route before writing anything, and treats a missing recipe as a blocker, not an invitation to improvise.

## State Matrix

Every important component and route covers, or explicitly marks `n/a` for:

```text
Ready
Loading
Empty
Error
Disabled
Permission denied
Stale
Expired
Long content
Reduced motion
Mobile reflow
```

Shipping only the ready state is the single most common source of a UI that fails in real use. Empty, error, stale, and long-content states are part of the design, not a follow-up task.

## Registry

The registry is the machine-readable allowlist that both agents and contract checks read. It carries every primitive with its closed variant sets, every product component with its content contract, every registered motion variant, every page recipe, and the flags that say what is not allowed (raw styles, arbitrary values, page-local controls).

Keep it generated from, or checked against, the same source as the architecture document — one of the two must be derived, so they cannot disagree. Adding a primitive means updating the registry and the catalog in the same change; an unregistered primitive is not usable.

## Catalog

The catalog is one place where every token, primitive variant, and component state is visible at once, under realistic content. It is the shared visual reference for humans and agents, and the thing a reviewer opens instead of hunting through routes.

Cover: every token, every primitive variant, every component state, short and long real content in the product's actual language, large numeric and currency values when the domain has them, empty and error data, each required viewport, and both normal and reduced motion.

## Automated Guardrails

The architecture is only real if a check fails when it is violated after the freeze. Specify these as project checks:

- No raw color values outside the token layer
- No unapproved dimension values (arbitrary spacing, radius, font size) outside the token layer
- No inline layout styles on pages
- No page-local control or surface styling
- Every section wraps an approved container, unless it is an approved full-bleed band
- Every public claim that needs evidence carries its evidence component
- Motion uses registered variants only
- No interactive-runtime hydration on a static page for decoration alone
- Every registry entry exists in the catalog, and every catalog entry exists in the registry

Visual and behavioral verification runs across the fixed viewport set and the state set, plus the JavaScript-disabled path for anything that must render server-side.

This package specifies these checks. Running them is implementation work owned by `fullstack-harness-engineering`, which ships `scripts/check_ui_contract.py` for the source-scanning subset and wires it into the project's verify command, CI, and visual-regression tooling.

The checks run against the product's real source, not against exploration candidates or this package's own mockups. Candidate HTML may contain direction-local values. Final dependency-free mockups inline extracted tokens and primitive definitions in one file on purpose, so "pages only consume primitives" cannot be judged there. What a final mockup must do instead is compose registry-named classes in recipe order, carry no inline layout styling, and visually reproduce the approved selected HTML.

## Definition Of Done

A route is done only when all of these hold:

- It uses registered primitives only
- It follows its page recipe
- It satisfies every content contract it renders
- It contains no raw visual values
- It reimplements no control, surface, or section
- Every required state is complete
- Keyboard path and focus work
- Reduced motion works
- No overflow at any required viewport
- Content that must render server-side still renders with JavaScript disabled
- Visual regression was reviewed
- The full contract check passes

## Adoption Sequence

For an existing product, land the architecture in this order. Each phase stops a class of drift before the next begins.

| Phase | Goal | Content |
| --- | --- | --- |
| 1 | Stop new drift | Freeze tokens, define primitive APIs, publish the registry, forbid new inline layout styling |
| 2 | Core primitives | Container, section, stack, cluster, surface, text, control primitives, inputs |
| 3 | Core routes | Migrate the highest-traffic and highest-risk routes first, one route at a time |
| 4 | Motion | Motion tokens, global reduced-motion config, registered variants, the routes whose motion carries real work |
| 5 | Automated verification | Catalog, contract checks, visual regression, accessibility checks |
| 6 | Tooling connections | Design-tool code connections, component workshop, styling-engine swap if wanted |

For a new product, phases 1–2 come before the first route is built, and phase 5 lands with the first two routes rather than at the end.

## Stack Independence

The styling engine is an implementation detail. Utility CSS, a CSS-in-JS engine, CSS modules, plain CSS, or a native platform's styling model can all satisfy this architecture, and any of them can be swapped without rewriting product components — provided the token, primitive, and registry layers stay intact.

What must stay stable regardless of stack:

```text
Agents do not decide visual values
Agents do not reinvent components
Agents do not freely rearrange product content
Agents only pick approved recipes, components, primitives, and variants
```

For a native or desktop target, keep the same layers and rename the mechanisms to that platform's vocabulary: tokens become the platform's theme values, layout primitives become its layout containers, control primitives wrap its native controls, and the motion split follows its state-styling and animation APIs. Do not drop a layer because the platform ships its own component library — a platform component gets wrapped by a primitive that fixes its variants, or the closed-variant rule is lost.
