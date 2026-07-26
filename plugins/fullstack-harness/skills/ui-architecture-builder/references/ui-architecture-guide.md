# UI Architecture Guide

This guide defines the architecture the package specifies, and how to derive it from real product inputs. `references/output-contract.md` holds the exact artifact structure; this file holds the model and the decision method.

The point of the architecture is a single rule:

> A page cannot be freely designed. A page may only use approved content contracts, page recipes, product components, and primitives.

That rule is what keeps a human's page and an agent's page consistent, and what keeps the design system, the code, and the mockups from drifting apart.

## Layer Model

```text
Product rules
  ├── Content contracts
  └── Route and state contracts
        ▼
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
> Page recipe
> Product component
> Primitive contract
> Design token
> Page-specific preference
```

Page-specific preference is last on purpose. "This page looks better with a bit more space" is not a reason to leave the contract; it is a reason to change the token or the primitive, or to add a variant.

`frontend-design` candidate screens do not enter this precedence list. They are non-canonical exploration. Only human-accepted visual decisions gain authority, and only after the parent normalizes them into the package's tokens, primitive and component contracts, recipes, registry, and final mockups.

## Layer Responsibilities

| Layer | Owns | Must not own |
| --- | --- | --- |
| Product rules | What the product must always show, never hide, and never claim | Visual values |
| Content contracts | Required fields, length limits, formats, CTA counts, empty/long-content handling, what may never be truncated away | Layout, color |
| Route and state contracts | Which routes exist, which states each must support, what SSR/no-JS must still render | Component internals |
| Design tokens | Every raw visual, layout, and motion value in the product | Markup, component structure |
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

1. **Content contracts first.** For each recurring product object, list required fields, max lengths, date and number formats, image ratios, CTA count, empty handling, long-content handling, mobile truncation, and the fields that may never be dropped for layout reasons. Sources, limits, dates, and commercial disclosure belong in the never-drop set whenever the product makes a claim a reader could act on.
2. **Optional Frontend Design Visual Direction Pass.** After the structural wireframes, route/state contracts, exact wording, and content contracts are frozen, an explicitly authorized `frontend-design` call may render one coherent set of one to three representative candidate screens. Run it once for the direction, not once per route. Candidates may explore hierarchy, typography, palette, spatial composition, imagery, and motion while preserving the frozen product structure. A human selects the direction, or explicitly delegates selection. Normalize only accepted decisions into the canonical layers below; candidate markup and candidate-only values never become a source implementation can consume.
3. **Tokens.** Fix the visual, layout, and motion token sets. Every accepted visual-direction value a page could otherwise invent must exist here as a named token.
4. **Layout primitives.** List the spacing and flow patterns that repeat across screens — the page shell and its widths, the section rhythm, vertical stacks, horizontal wrapping groups, grids. Name them, and give each a closed set of variants (sizes, gaps, densities) instead of a free numeric prop.
5. **Surface primitives.** Take the surviving treatments from `visual-decision-guide.md`'s Container & Border Decision Rules and turn each into a named surface variant with its purpose. A treatment that failed those rules does not become a variant.
6. **Typography and control primitives.** List the type roles and the interactive atoms the screens actually use, with their variants, sizes, and states. Controls own focus and accessible naming; record the minimum hit target per platform.
7. **Product components.** Only now, name the domain compositions, in the domain's own words, and bind each to its content contract. A composition that appears on one screen only stays inside that page.
8. **Motion patterns.** Split motion by mechanism (see below), then register every variant. A page may reference a registered variant; it may not write a duration, distance, spring, or easing value.
9. **Page recipes.** For each route, fix the section order, container, density, allowed surfaces, required components, and forbidden patterns.
10. **Registry.** Emit the machine-readable allowlist of everything above.
11. **Verification.** Define the contract checks, the viewport set, and the state set that prove conformance.

Check the direction at the end: a layout primitive that sets color, a surface that spaces its own children, a product component holding a raw hex value, or a page defining its own button means a layer boundary leaked.

## Closed Variant Sets

Every primitive prop is a closed set, never a free value.

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

The architecture is only real if a check fails when it is violated. Specify these as project checks:

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

The checks run against the product's real source, not against this package's own mockups. A dependency-free mockup inlines its tokens and its primitive definitions in one file on purpose, so "pages only consume primitives" cannot be judged there. What the mockup must do instead is compose registry-named classes in recipe order and carry no inline layout styling — reviewable by reading it.

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
