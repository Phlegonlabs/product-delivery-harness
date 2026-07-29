# Wireframe Guide

Use low-fidelity ASCII wireframes plus Mermaid flows. Do not produce Figma or HTML unless the user asks for them.

Across the design handoff, `PRD.md` remains canonical for product scope and low-fidelity wireframes remain canonical for screen structure, flow, visible-region responsibilities, actions, states, and trace IDs. A later visual prototype can interpret that structure, but it cannot replace it.

## Builder UX Direction Gate

Before drafting interface wireframes, ask one organized set of questions about the builder's intended experience. Resolve the builder to the human product/design decision owner or commissioning team; the implementation agent does not supply its own taste as a substitute.

Record the resulting `Builder UX Direction Decision` in `PRD.md` and carry it into `wireframes.md`. It must cover experience priority, guided versus expert control, information density, familiar versus expressive interaction, primary layout preference, confirmation/recovery behavior, and validation depth. Mark every decision `selected`, `provisional`, or `assumed`.

Builder preference controls direction, not usability claims. When preference conflicts with observed user needs, accessibility, or task evidence, preserve the conflict as a hypothesis and name the prototype or user test needed to resolve it. Never label a wireframe user-validated merely because the builder approved it.

## Structural Direction And Configuration

- Freeze product and structural constraints before visual exploration: screen purpose, content responsibilities, actions, states, trace IDs, brand rules, accessibility, platform, and performance limits.
- Keep the wireframe simple: grayscale in visual tools, clear hierarchy, consistent alignment, restrained containers, and only enough detail to explain content, behavior, and flow.
- Do not ask the user to choose a fixed high-fidelity style catalog or record `modern-minimal` as the default. Product-specific visual preference discovery happens later through the Visual Direction Gate.
- Translate vague product direction into structural consequences such as information density, hierarchy, region order, imagery responsibility, container use, and interaction behavior. Defer typeface, palette, spacing scale, radius, surface styling, and motion choreography.
- Choose the layout pattern from the screen's primary task and content shape:
  - Landing or narrative page: ordered story, one first-viewport value proposition, one primary action, and secondary detail deferred.
  - App workspace or CRUD screen: stable navigation, task context, primary work area, and actions near the object they affect.
  - Dashboard or monitoring screen: summary, exceptions, trends, then records or next actions; do not force every metric into a card.
  - Form or wizard: progress and context, grouped inputs, inline validation, then one clear next action.
  - Search, catalog, or comparison screen: query and filters, result summary, scannable results, then detail or comparison.
- State the selected layout pattern and density for each important screen. Change the pattern only when the user task or content shape changes.

## Visual Direction Gate

Run this gate for every UI-bearing product after the structural wireframes pass their quality checklist and before fixing design-system tokens or components. The gate is required; optional preview tooling is not.

Select the same one or two representative screens for every direction and carry:

- the selected `UI-*` screen and region IDs;
- each screen's purpose, layout pattern, density, exact copy or display contracts, actions, states, and responsive constraints;
- the Builder UX Direction Decision, known brand constraints, and product-specific visual goals;
- an instruction that scope, routes, content responsibilities, interaction behavior, and trace IDs are frozen.

### Reference Image Checkpoint

Before asking for the remaining visual preference details or presenting directions, ask whether the human owner wants to provide one or more reference images or screenshots. This is optional. Unless usable reference images are already attached, end the turn and wait for attachments or an explicit skip; do not present visual directions in the same turn as this prompt.

When reference images are provided:

1. Confirm that every image is readable. If an attachment cannot be inspected with the available tools, ask the user to attach it again and do not infer unseen details.
2. Label each image so the analysis is traceable. For multiple images, separate repeated patterns from one-off details or contradictions.
3. Extract candidate **design-system signals** across hierarchy and density, palette roles and contrast intent, typography character and scale, spacing rhythm, borders, radius, shadow and surface treatment, controls and recurring component patterns, states, icons or media, and motion.
4. Return a concise `Adopt / Adapt / Avoid` analysis and ask the owner to confirm or correct it before using those signals to generate directions.

Reference pixels are evidence, not token values. Recreate the approved principles for this product and its frozen wireframes; do not copy protected artwork, branding, exact copy, or a distinctive composition. Accessibility, product requirements, and platform conventions still outrank the reference. Reference images and the full extraction analysis remain non-canonical design-stage evidence outside the published package.

First ask a short, product-specific visual preference set covering desired character, density, color constraints, typography feel, imagery or icon preferences, motion tolerance, references, and disliked patterns. Derive the choices from the product's purpose, audience, content, platform, brand inputs, and structural wireframes. Never reuse a fixed catalog. The answers form a non-binding Visual Preference Brief, not a token specification.

Present three materially different directions by default. Present four only when a real product tension makes the fourth useful. Each direction uses the same frozen structure and states and explains its character, hierarchy, density, color, typography, surfaces, icon or media treatment, motion approach, signature decisions, and explicit avoid list. Make every direction reviewable, then ask the human owner to:

- `Select` one direction;
- `Reject` one or all directions;
- `Mix` named parts of multiple directions into one consolidated direction for another review; or
- `Check This` by providing a URL, screenshot, Figma view, named product, or brand reference.

For `Check This`, apply the same Reference Image Checkpoint extraction and confirmation rules to the new reference, then return to the direction choice. Record what the user actually likes instead of treating the whole reference as approval. Generate a revised set of directions from the confirmed principles.

If the user explicitly authorizes `frontend-design`, use it to render complete dependency-free HTML previews for the same representative screens and frozen constraints. No other approval implies approval for that skill. Preview HTML is optional; the direction decision is not. Fix tokens, primitives, components, and the registry only after the human explicitly selects the consolidated direction, or explicitly authorizes a provisional assumption.

Candidate and selected HTML are non-canonical design-stage evidence. Keep them outside the staged and published PRD package. They may explore typography, color, composition, texture, imagery, and motion, but they must not add product scope or silently change the canonical wireframes.

The published design system records only the selected direction's short summary and implementation consequences. It does not preserve candidate directions or the full `Check This` analysis.

If the visual pass exposes a structural problem, return a concise finding tied to the affected `UI-*` IDs. The parent or human product/design owner decides whether to make one bounded wireframe revision, preserves unaffected scope and IDs, and reruns the PRD quality checklist. Only then may the visual pass continue from the revised wireframe.

## ASCII Wireframe Rules

- Use fixed-width fenced code blocks with `text`.
- Keep layouts low fidelity and structural, not decorative.
- Label key regions, controls, data, errors, and actions.
- Label image/media and motion needs as `required`, `optional`, or `none`, with a short purpose. Label the style direction of visually important regions with its intended effect on hierarchy or comprehension. Before the Visual Direction Gate, use structural spacing and type-role descriptions rather than invented token values. After the design system is complete, reconcile those descriptions to the final token and component names.
- Show responsive differences when mobile and desktop experiences materially differ.
- Include primary, secondary, and destructive actions when relevant.
- Before the design system exists, include ready, loading, empty, error, permission-denied, and success outcomes plus known edge states. During final reconciliation, make each screen cover every `design-system.json` `stateMatrix` entry or mark it `n/a` with a reason.

## Content Specificity Rules

Every visible region must use one of these content modes:

1. `Exact copy`: write the actual heading, body copy, label, CTA, helper text, validation message, or state message. Mark wording as `approved` or `draft` when that status matters.
2. `Display contract`: when final wording is not available or the region is data-driven, state what the region must display, what the user should understand or do, the content or data source, and any ordering, format, count, or length constraints.

Do not leave `Main content`, `Feature section`, `Card 1`, `Lorem ipsum`, or similar generic placeholders in a final wireframe. If a decision is genuinely unresolved, write `[COPY TBD: specific question or owner]`, add it to open questions, and still provide the section's display responsibility.

## Style And Anti-Slop Structure Rules

- Give each visually important region a short `STYLE` label that describes its visual job, not just a mood word. Examples: `editorial split for narrative contrast`, `full-bleed product proof`, `dense comparison table`, or `unframed text for a quiet transition`.
- Give each animated region a `MOTION` label with `required`, `optional`, or `none`, plus what the animation communicates. `Add animation` without a purpose does not pass.
- A box in an ASCII wireframe must mean real grouping, interaction, state, or hierarchy. Do not box every section merely because ASCII makes it easy.
- Do not imply repeated bordered cards or panels with a colored side rail or accent stripe as a default visual treatment. Allow that pattern only when the stripe communicates a named state, selection, priority, category, or approved brand motif.
- Prefer open layout regions, spacing, typography, alignment, rules, or background changes when they communicate the hierarchy without another container.

## Element Inventory And Spacing

Each region contract lists its elements top-to-bottom, one line each:

`- [element type] [content ref] — [component or custom] — [type role]`

- Element type: `heading`, `text`, `button`, `link`, `input`, `image`, `icon`, `divider`, `list`, or `table`.
- Content ref: the exact-copy key or display-contract summary already in the region contract.
- Component: before the design system exists, write the required role or `custom — [one-line reason]`; during final reconciliation, replace it with the selected design-system primitive or product component. Every unresolved `custom` flag blocks publication.
- Type role: before the design system exists, use a structural role (`display`, `title`, `body`, `caption`), not a font size. Final reconciliation binds it to the design-system type token.

An element not in the inventory does not exist. Downstream image generation and implementation must not invent one; a plausible extra element in a generated image or a built page is a spec gap to add here, never something to copy into code.

Before the Visual Direction Gate, declare spacing relationships as `compact`, `default`, or `generous`, with above, below, padding, and element-gap roles. Never use raw values or vague words such as "some breathing room".

- During final reconciliation, replace each role with the selected design-system token: `Spacing: above <token>, below <token>, padding <token>, element gap <token>`. Above/below is the gap to neighboring regions, padding is inside the region's own container, and element gap sits between inventory elements.
- The same region type uses the same final tokens on every screen; only a stated reason changes them.
- Note mobile only where the relationship or final token differs from desktop. Silence means the same rule.

The final published wireframes cite names only; values live in `design-system.md` and `design-system.json`.

## SEO Copy Rules

Every screen with a public route gets an SEO block right after its Density line:

```text
SEO:
- Primary keyword: [one phrase, the way the target audience actually searches]
- Secondary keywords: [1-2 phrases]
- Meta title: [≤ 60 chars, contains the primary keyword]
- Meta description: [≤ 160 chars, primary keyword plus one concrete benefit]
```

A screen with no public route — an authenticated workspace, a modal, a wizard step — records `SEO: n/a` with the reason, so the skip reads as a decision.

- A primary keyword belongs to exactly one route in the product. Keep the route-to-keyword map in `wireframes.md`'s direction section; two routes competing for one keyword is an authoring error.
- Exactly one `H1` per screen, containing the primary keyword. Heading order `H1 → H2 → H3` never skips a level; the element inventory marks each heading's level.
- Exact copy for the H1, first paragraph, and primary CTA each contains the primary or a secondary keyword, written naturally. Copy that misses every keyword stays `draft`, not `approved`.
- Write keywords in the language the audience searches in, not the language of the internal docs.
- Every meaningful `image` element declares its alt text in the region contract (`alt: "..."`, descriptive, with a keyword only when it fits naturally). Decorative images declare `alt: ""`.
- Implementation never paraphrases a heading, meta field, or alt text. SEO copy is frozen copy: the wireframe wins.

## KISS Landing Page Rules

- Put one clear value proposition and one primary action in the first viewport.
- Give each section one job. Keep it only when it explains the offer, establishes necessary trust, resolves a blocking objection, or enables the next step.
- Do not turn every PRD requirement, feature, workflow, or proof point into a landing-page section. Defer secondary detail to deeper pages, docs, or a bounded FAQ.
- Prefer a short, ordered section list over a large collage of cards, badges, metrics, and repeated calls to action.
- Label media and motion where they are needed; do not add an image or animation merely to fill space.

## Screen Intent

Write this before drawing a screen's ASCII layout. It is the reasoning step that drives the box layout, not a label filled in after the boxes already exist:

- Main purpose: the single primary goal the user must accomplish on this screen, in one sentence. If it cannot be stated in one sentence, the screen is doing too many jobs — split it or pick the one job that wins.
- Primary emphasis: what gets the strongest visual and structural weight, and why that thing serves the main purpose.
- Secondary / quiet: what stays present but subordinate. Do not give it equal visual weight with the primary emphasis.
- Structural rationale: which layout pattern from Direction And Configuration answers the main purpose, and why that pattern over the others.

Carry all four lines into the Screen Template below verbatim. They make the layout pattern choice and the box layout traceable back to a stated reason instead of a default template.

## Screen Template

Lead the screen with the human-readable intent lines. The `UI ID` and trace IDs close the screen in a `### Trace` block, so a reader learns what the screen is for before meeting its identifiers.

`Route(s):` is the one machine-consumed line among them. Implementation looks a route up here to find its screen entry, and a route with no entry is a hard stop downstream — so write the route the way the product actually addresses it (`/settings/billing`, `/orders/:id`, a native route or deep-link name), not a prose description of it. One screen may serve several routes; list them all. A screen with no addressable route — a modal, a step inside a wizard already covered by its parent route, an email or notification surface — records `n/a` with the reason, so a missing route reads as a decision rather than an omission.

````markdown
## Screen: [Name]

Route(s): [Every route this screen serves, exactly as the product addresses it]

Main purpose: [Single primary goal, one sentence]

Primary emphasis: [What gets the strongest weight, and why]

Secondary / quiet: [What stays present but subordinate]

Layout pattern: [Landing / workspace / dashboard / form or wizard / search or catalog / justified custom pattern] — chosen because: [one sentence tying the pattern to the main purpose]

Density: [Sparse / balanced / dense, with a task or content reason]

SEO: [public route: primary keyword, 1-2 secondary keywords, meta title ≤ 60 chars, meta description ≤ 160 chars — otherwise `n/a` with the reason]

```text
[Start from the matching skeleton in Layout Skeletons by Pattern below, then adapt its regions to this screen's actual content.]
```

### States
- Ready: [Normal usable state]
- Loading: [Skeleton, spinner, progress, disabled controls]
- Empty: [Message and next best action]
- Error: [Error message, retry, support path]
- Disabled: [Why the action is unavailable]
- Permission denied: [Access denied or request-access path]
- Stale: [Freshness warning and refresh behavior]
- Expired: [Expired-session or expired-object recovery]
- Long content: [Wrapping, truncation, overflow, or expansion]
- Reduced motion: [Equivalent non-spatial feedback]
- Mobile reflow: [Order, stacking, and never-drop content]

### Content, Style, Media & Motion Notes
One block per visible region, in the order the region appears on screen.

**UI-001-R01 — [Region]**
- Content mode: [exact copy / display contract]
- Exact wording or display contract: [Verbatim wording, or what to show + intended takeaway/action + source + constraints]
- Content priority: [must-have / secondary / defer]
- Style direction: [Visual job and hierarchy/comprehension purpose]
- Element inventory: [one line per element: type, content ref, design-system component or `custom — reason`, type role]
- Spacing: [above / below / padding / element gap as spacing tokens; mobile only where it differs]
- Image / media: [required / optional / none; purpose]
- Motion: [required / optional / none; purpose]
- Notes: [Status, fallback, or handoff question]
- Trace IDs: PRD-001, UX-001

### Trace
UI ID: UI-001

Trace IDs: PRD-001, UX-001, ARCH-001
````

Write the region notes as blocks, not as one wide table. The same fields in a ten-column Markdown table wrap or need horizontal scrolling in every viewer.

## Layout Skeletons by Pattern

Start from the skeleton matching the screen's Structural rationale, then adapt region contents to the real product. Do not reuse the workspace skeleton for a landing page or a wizard merely because it is the most familiar box shape — each pattern reflects a different information architecture, and low-fidelity wireframes should already show that difference instead of hiding it behind one generic box.

### Landing or Narrative Page

```text
+------------------------------------------------------------+
| Logo / Product                                  [Primary nav] |
+------------------------------------------------------------+
| [Value proposition headline]                                |
| [One supporting sentence]                                   |
| [Primary action]                                            |
+------------------------------------------------------------+
| Section: [one job — proof, trust, or how-it-works]          |
+------------------------------------------------------------+
| Section: [next section, one job]                            |
+------------------------------------------------------------+
| Footer: [secondary links, legal]                             |
+------------------------------------------------------------+
```

### App Workspace or CRUD Screen

```text
+------------------------------------------------------------+
| Product / Section                                  [User]  |
+------------------------------------------------------------+
| Nav         | [Exact title or DISPLAY: ...]   [Exact CTA]  |
|-------------+----------------------------------------------|
| Item        | [Exact copy/data or DISPLAY: responsibility] |
| Item        |                                              |
|             | [Exact primary label] [Exact secondary label] |
+------------------------------------------------------------+
```

### Dashboard or Monitoring Screen

```text
+----------------------------------------------------------------+
| Header                                           Filters [Run]  |
+----------------------------------------------------------------+
| KPI 1        | KPI 2        | KPI 3        | Alert summary      |
+----------------------------------------------------------------+
| Chart / trend                         | Activity / exceptions  |
|                                       |                        |
+----------------------------------------------------------------+
| Table: records, status, owner, next action                      |
+----------------------------------------------------------------+
```

### Form or Wizard

```text
+------------------------------------------------------------+
| [Step indicator: Step 2 of 4 — Step name]                   |
+------------------------------------------------------------+
| [Context: why this step, what happens after]                |
+------------------------------------------------------------+
| [Field group: label, input, inline validation]               |
| [Field group: label, input, inline validation]               |
+------------------------------------------------------------+
| [Back]                                    [Primary: Continue]|
+------------------------------------------------------------+
```

### Search, Catalog, or Comparison Screen

```text
+------------------------------------------------------------+
| [Query input]                          [Sort] [View toggle] |
+------------------------------------------------------------+
| Filters: [Filter] [Filter] [Filter]           [Result count] |
+------------------------------------------------------------+
| Result       | Result       | Result                        |
| Result       | Result       | Result                        |
+------------------------------------------------------------+
| [Pagination or load more]                                    |
+------------------------------------------------------------+
```

## Mobile Layout Template

Adapt this cross-cutting responsive variant to whichever pattern skeleton above the screen uses; it is a viewport adjustment, not a sixth pattern.

```text
+--------------------------+
| Header              Icon |
+--------------------------+
| Summary / context        |
+--------------------------+
| Primary content          |
|                          |
|                          |
+--------------------------+
| [Primary action]         |
+--------------------------+
| Tab 1 | Tab 2 | Tab 3    |
+--------------------------+
```

## Specialized Example: Automation Run Detail

```text
+----------------------------------------------------------------+
| Workflow: [Name]                         Status: [Running]      |
+----------------------------------------------------------------+
| Trigger       | Input summary            | Started / Duration   |
+----------------------------------------------------------------+
| Step timeline                                                  |
| 1. Validate input                         [Done]                |
| 2. Call integration                       [Running]             |
| 3. Write result                           [Pending]             |
+----------------------------------------------------------------+
| Logs / errors / retry controls                                  |
+----------------------------------------------------------------+
```

## Mermaid Flow Rules

- Use Mermaid for user journeys, system flows, or automation workflows.
- Use quoted node labels.
- Show decision points and failure paths, not only the happy path.
- Keep each diagram focused on one flow.

Example:

```mermaid
flowchart TD
  A["User opens dashboard"] --> B["System loads account data"]
  B --> C{"Data available?"}
  C -->|Yes| D["Show dashboard"]
  C -->|No| E["Show empty state"]
  B --> F{"Permission valid?"}
  F -->|No| G["Show request access state"]
```

## State Coverage

For each primary screen or workflow, define every state in the final `design-system.json` `stateMatrix`. Use the template's common set as the starting point, then add or remove states only through the design-system contract. If a state does not apply, write `<state>: n/a — <reason>` so validation can distinguish a deliberate exclusion from an omission.
