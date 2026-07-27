# UI Architecture: <product name>

Binding rule after package approval and publication: a page cannot be freely designed. A page may only use approved content contracts, page recipes, product components, and primitives. Adding a value means adding a token or a variant here and in `ui-registry.json`, never a one-off at the call site.

Resolved platform: <web, native iOS, native Android, Flutter, React Native, macOS, Windows, or cross-platform desktop>
Styling / theming mechanism: <utility CSS, CSS-in-JS engine, CSS modules, plain CSS, or the platform's theme system>
Animation runtime: <style-layer only, or the named animation runtime plus route-transition mechanism>
Registry enforcement: <advisory / blocking contract check>

## Enhancement Baseline & Delta

Mode: <fresh package / enhancement of same-product package>
Baseline: <n/a for fresh package, or frozen package paths and captured revision/date>

| Delta ID | Action | Target IDs / artifacts | Accepted change | Preserved dependencies | Status |
|---|---|---|---|---|---|
| DELTA-001 | <add / modify / remove> | <IDs and exact paths> | <bounded change> | <untouched IDs, content, artifacts, and decisions that must remain> | <accepted / applied / blocked> |

For enhancement mode, this table is the complete mutation allowlist. Preserve everything outside it and validate the whole revised package. For a fresh package, record `n/a — no enhancement baseline`.

## Approved Visual Source & Extraction Gate

Visual Preference Brief: <path or summary of product-specific Ask User answers>
Candidate set: <exactly two or three direction paths covering the same one or two UI IDs, or n/a>
Selected HTML: <exact `visual-directions/selected/` path or n/a>
Human approval: <owner and explicit approval evidence, or n/a>
Selected-file manifest: <ordered UI ID, canonical HTML path, and SHA-256 entries plus approval-manifest SHA-256, or n/a>
Hallmark review: <loaded with candidate/selected/final report paths and dispositions, or unavailable / n/a>
Extraction evidence: <design-system.md Token Extraction Trace section>

Candidate HTML may use direction-local values before this gate. In the preferred exploration path, tokens, primitives, components, recipes, the registry, and final mockups are extracted only after the human approves the selected HTML's exact manifest digest. When exploration is `not used` or `rejected`, derive the package from recorded product inputs and explicit visual assumptions and say so here; do not claim selected-HTML extraction. In both paths, the validated package becomes binding only after approval and publication.

## Layer Model

| Layer | Owns | Must not own | Where it lives |
|---|---|---|---|
| Product rules | What the product must always show, never hide, never claim | Visual values | PRD-*, this document |
| Content contracts | Required fields, limits, formats, empty and long-content handling | Layout, color | this document |
| Route and state contracts | Routes, required states, what must render without JavaScript (or `n/a` plus a reason when the route has no server-rendered web surface) | Component internals | `page-recipes.md` |
| Visual derivation source | Digest-bound human-approved selected HTML, or explicit assumptions when exploration is not used or rejected | Product scope, route behavior, content requirements | `visual-directions/selected/` evidence or this document's assumptions |
| Hallmark review evidence | Named structural and anti-slop findings for candidate, selected, and final projections | Editing files, selecting a direction, product authority | retained `hallmark-audit.md` evidence |
| Design tokens | Every repeated raw visual, layout, and motion value extracted from the visual derivation source | Markup, structure | `design-system.md` |
| Layout primitives | Space, flow, alignment, max width, responsive rearrangement | Color, background, border, elevation, domain content | this document |
| Surface primitives | Background, border, divider, radius, elevation, own padding | Spacing between its own children, domain content | this document |
| Typography primitives | Type role, size, weight, line height, truncation | Layout, color outside the role's token | this document |
| Control primitives | Interaction, variants, sizes, states, focus, accessible name, hit target | Page layout, domain rules, data access | this document |
| Product components | Domain naming, required content order, composition of primitives | Raw values, ad-hoc spacing or color, data fetching | this document |
| Motion patterns | Registered variants and choreography | Information that exists nowhere else | this document + `design-system.md` tokens |
| Page recipes | Section order, container, density, allowed surfaces, forbidden patterns | New visual treatment | `page-recipes.md` |
| Routes / pages | Route composition, data, page state | Any new visual value or component | `mockups/*.html`, implementation |

Composition runs one way: a layer may compose only the layers above it. Nothing depends downward toward pages.

## Source Of Truth Precedence

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

<State any conflict found between these sources and how it was resolved.>

## Content Contracts

| Contract ID | Object / region | Required fields | Never drop | Limits & formats | Empty | Long content | Mobile truncation | Upstream trace IDs |
|---|---|---|---|---|---|---|---|---|
| CONTRACT-001 | <product object> | <fields> | <fields that may never be removed for layout reasons> | <max lengths, date format, number format, CTA count, image ratio> | <what shows> | <what wraps, clamps, or expands> | <what truncates and how> | PRD-001, UI-001 |

Sources, limits, dates, and commercial disclosure belong in Never drop whenever the product makes a claim a reader could act on. Content is never removed to make a layout work.

## Primitive Contracts

Every prop is a closed set. No free numeric or color values at the call site.

### Layout Primitives

| DS ID | Name | Purpose | Closed variants | Must not | Tokens used |
|---|---|---|---|---|---|
| DS-LAY-001 | <container> | <max width, gutter, centering> | <named sizes> | <set color, background, border, or vertical rhythm> | <layout tokens> |
| DS-LAY-002 | <section> | <vertical rhythm of a page region> | <named densities with their values> | <set background or width> | <spacing tokens> |
| DS-LAY-003 | <stack> | <vertical flow with one gap> | <named gap steps> | <free gap values> | <spacing tokens> |
| DS-LAY-004 | <cluster> | <horizontal wrapping group> | <named gap steps, alignment> | <free gap values> | <spacing tokens> |

### Surface Primitives

| DS ID | Name | Purpose | Closed variants | Named purpose per variant | Must not |
|---|---|---|---|---|---|
| DS-SUR-001 | <surface> | <background, border, radius, elevation, own padding> | <plain / raised / inset / selected / warning / danger / product-specific> | <one named hierarchy, interaction, state, data, or accessibility purpose per variant> | <space its own children; create a second card style in a page> |

Every variant carries a purpose from `visual-decision-guide.md`'s Container & Border Decision Rules. A variant with no purpose gets deleted, not documented.

### Typography Primitives

| DS ID | Name | Type roles | Truncation / wrapping | Must not |
|---|---|---|---|---|
| DS-TXT-001 | <text> | <roles from design-system.md Typography> | <clamp, ellipsis, wrap rules> | <set its own size or color outside the role> |

### Control Primitives

| DS ID | Name | Closed variants | Sizes & hit targets | States | Accessible name | Must not |
|---|---|---|---|---|---|---|
| DS-CTL-001 | <button> | <primary / secondary / tertiary / danger> | <named sizes with values; minimum target per platform> | <hover, focus, active, loading, disabled> | <owner and rules> | <be reimplemented in a page> |
| DS-CTL-002 | <icon button> | <variants> | <sizes; minimum target> | <states> | <required label source> | <ship without an accessible name> |

Minimum interactive target: <platform value, e.g. 44px for public web and mobile>. A smaller size exists only for a named high-density surface.

## Product Components

| DS ID | Component | Content contract | Required content order | Composes | Variants | States | Upstream trace IDs |
|---|---|---|---|---|---|---|---|
| DS-COMP-001 | <domain name> | CONTRACT-001 | <the fixed order of the fields it must render> | DS-LAY-*, DS-SUR-*, DS-CTL-* | <variants> | <states> | UI-001, PRD-001 |

Required content order is binding. A page or an agent may not reorder, hide, or drop fields inside a product component.

## Motion Architecture

| Mechanism | Used for | Technology | Fallback |
|---|---|---|---|
| Style-layer transition | <hover, focus, pressed, color, simple opacity> | <CSS transitions or platform state styling> | <none needed> |
| Animation runtime | <enter/exit, layout change, list insert/remove, dialog, gesture, shared element, state choreography> | <named runtime> | <final state> |
| Route-level transition | <navigation continuity> | <view transitions or native navigation> | <plain navigation> |

### Registered Motion Variants

| Motion ID | Variant name | Purpose | Mechanism | Tokens | Reduced-motion behavior |
|---|---|---|---|---|---|
| MOTION-001 | <variant> | feedback / continuity / processing / storytelling | <mechanism> | <duration, distance, easing tokens from design-system.md> | <final state> |

Reduced-motion policy is set once, globally: <where and how>. Pages reference variant names only; durations, distances, easings, and springs live in motion tokens.

## State Matrix

| State | Required | Applies to | Behavior | Verified by |
|---|---|---|---|---|
| Ready | yes | <scope> | <behavior> | TEST-VIS-* |
| Loading | <yes / n/a + reason> | <scope> | <behavior> | TEST-VIS-* |
| Empty | <yes / n/a> | <scope> | <behavior> | TEST-VIS-* |
| Error | <yes / n/a> | <scope> | <behavior> | TEST-VIS-* |
| Disabled | <yes / n/a> | <scope> | <behavior> | TEST-VIS-* |
| Permission denied | <yes / n/a> | <scope> | <behavior> | TEST-VIS-* |
| Stale | <yes / n/a> | <scope> | <behavior> | TEST-VIS-* |
| Expired | <yes / n/a> | <scope> | <behavior> | TEST-VIS-* |
| Long content | yes | <scope> | <behavior> | TEST-VIS-* |
| Reduced motion | yes | <scope> | <final state shown> | TEST-VIS-* |
| Mobile reflow | yes | <scope> | <behavior at the narrowest entry in the verified responsive set: 390px for a web target, the compact size class or smallest window size otherwise> | TEST-VIS-* |

## Registry

`ui-registry.json` is the machine-readable allowlist for every table above. It is published with this document; publishing one without the other points the contract check at a stale allowlist.

Adding a primitive, variant, motion variant, product component, or recipe means updating this document, `ui-registry.json`, and `mockups/catalog.html` in the same change. An unregistered primitive is not usable.

## Rendered Design System

`docs/product/design/design-system.html` is the dependency-free rendered projection of `design-system.md` and `ui-registry.json`, not a second source of truth. It shows the complete reusable element catalog, and every live specimen's reproduction block uses the exact fields `IDs`, `Parameters`, `States`, `Responsive`, `Accessibility`, `Use`, and `Do not use`. `IDs` includes token IDs plus primitive/component and variant IDs as applicable. Any shown ID absent from the Markdown source or registry is a contract failure. Rebuild it when accepted enhancement delta changes a rendered input; otherwise preserve it unchanged.

## Catalog

`mockups/catalog.html` shows every token, primitive variant, and component state under realistic content: short and long real copy, large numeric and currency values where the domain has them, empty and error data, every entry in the verified responsive set below, and normal versus reduced motion. Every registry entry appears there, and every catalog entry exists in the registry.

## Automated Guardrails

| Check | Rule | Enforcement | Owner |
|---|---|---|---|
| Raw color values | none outside the token layer | <blocking / advisory> | project verify command |
| Unapproved dimension values | none outside the token layer | <blocking / advisory> | project verify command |
| Inline layout styles | none on pages | <blocking / advisory> | project verify command |
| Page-local control or surface styling | none | <blocking / advisory> | project verify command |
| Section wraps an approved container | required, except approved full-bleed bands | <blocking / advisory> | project verify command |
| Registered motion variants only | required | <blocking / advisory> | project verify command |
| Registry ↔ catalog completeness | two-way | <blocking / advisory> | project verify command |
| Design-system Markdown/registry ↔ HTML projection | every rendered specimen and ID/parameter agrees; every required reusable element category is present | <blocking / advisory> | design review + project verify command |
| Evidence present for claims that need it | required | <blocking / advisory> | design + code review |

Responsive set verified: <the set recorded in ui-registry.json — the 390 / 768 / 1200 / 1440 px web default unless a stated reason changed it, or the resolved platform's own model for a native or desktop target — iOS/macOS size classes and safe areas, Android window size classes, or the named desktop window sizes. `ui-registry.json` carries `viewports` or `sizeClasses`, exactly one of the two; name the one this package uses here: <viewports / sizeClasses, with the values>.

States verified: the State Matrix above, plus the JavaScript-disabled path for anything that must render server-side. A native or desktop target has no such path; record that as `n/a` with the reason rather than leaving it blank.

This document specifies the checks. `fullstack-harness-engineering` runs them against the real source with its own `scripts/check_ui_contract.py` and wires them into the project's verify command, CI, and visual-regression tooling. They are not run against this package's mockups, which inline their own tokens and primitive definitions by design.

## Definition Of Done

A route is done only when all of these hold:

- Registered primitives only
- Follows its page recipe
- Satisfies every content contract it renders
- No raw visual values
- No reimplemented control, surface, or section
- Every required state complete
- Keyboard path and focus work
- Reduced motion works
- No overflow anywhere in the verified responsive set recorded above
- Server-rendered content still renders with JavaScript disabled, or the route records that requirement as `n/a` with a reason
- Visual regression reviewed
- Contract check passes

## Adoption Sequence

| Phase | Goal | Content | Status |
|---|---|---|---|
| 1 | Stop new drift | Tokens frozen, primitive APIs defined, registry published, new inline layout styling forbidden | <planned / done> |
| 2 | Core primitives | <the primitives this product needs first> | <status> |
| 3 | Core routes | <route order, highest traffic and risk first> | <status> |
| 4 | Motion | Motion tokens, global reduced-motion policy, registered variants, the routes whose motion carries real work | <status> |
| 5 | Automated verification | Catalog, contract checks, visual regression, accessibility checks | <status> |
| 6 | Tooling connections | <design-tool connection, component workshop, styling-engine change if wanted> | <status> |

For a new product, phases 1–2 come before the first route is built and phase 5 lands with the first two routes.

## Assumptions

- <assumption>

## Open Questions

- <question>
