# Wireframe Guide

Use low-fidelity ASCII wireframes plus Mermaid flows. Do not produce Figma or HTML unless the user asks for them.

## Direction And Configuration

- Ask what overall visual character the user wants before drafting interface wireframes unless the prompt already answers it. Capture the answer as downstream design intent, not as permission to turn the wireframe into a high-fidelity mockup.
- Keep the wireframe itself simple for every style direction: grayscale in visual tools, clear hierarchy, consistent alignment, restrained containers, and only enough detail to explain content, behavior, and flow.
- If the user authorizes assumptions and gives no style direction, record `modern-minimal` as provisional. Interpret it structurally as clear hierarchy, balanced whitespace, familiar interaction patterns, restrained grouping, and no decorative UI. Do not present it as an approved design system.
- Do not accept `modern` as a complete layout decision. Translate it into concrete choices about information density, spacing, typography role, imagery, container use, and interaction tone. Record unresolved choices as handoff questions.
- Choose the layout pattern from the screen's primary task and content shape:
  - Landing or narrative page: ordered story, one first-viewport value proposition, one primary action, and secondary detail deferred.
  - App workspace or CRUD screen: stable navigation, task context, primary work area, and actions near the object they affect.
  - Dashboard or monitoring screen: summary, exceptions, trends, then records or next actions; do not force every metric into a card.
  - Form or wizard: progress and context, grouped inputs, inline validation, then one clear next action.
  - Search, catalog, or comparison screen: query and filters, result summary, scannable results, then detail or comparison.
- State the selected layout pattern and density for each important screen. Change the pattern only when the user task or content shape changes.

## ASCII Wireframe Rules

- Use fixed-width fenced code blocks with `text`.
- Keep layouts low fidelity and structural, not decorative.
- Label key regions, controls, data, errors, and actions.
- Label image/media and motion needs as `required`, `optional`, or `none`, with a short purpose. Label the style direction of visually important regions with its intended effect on hierarchy or comprehension. Keep tokens, art direction, and detailed choreography out of the low-fidelity wireframe.
- Show responsive differences when mobile and desktop experiences materially differ.
- Include primary, secondary, and destructive actions when relevant.
- Include loading, empty, error, permission, and success states for each major screen or workflow.

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

## KISS Landing Page Rules

- Put one clear value proposition and one primary action in the first viewport.
- Give each section one job. Keep it only when it explains the offer, establishes necessary trust, resolves a blocking objection, or enables the next step.
- Do not turn every PRD requirement, feature, workflow, or proof point into a landing-page section. Defer secondary detail to deeper pages, docs, or a bounded FAQ.
- Prefer a short, ordered section list over a large collage of cards, badges, metrics, and repeated calls to action.
- Label media and motion where they are needed; do not add an image or animation merely to fill space.

## Screen Template

````markdown
## Screen: [Name]

Purpose: [What user accomplishes here]

Layout pattern: [Landing / workspace / dashboard / form or wizard / search or catalog / justified custom pattern]

Density: [Sparse / balanced / dense, with a task or content reason]

```text
+------------------------------------------------------------+
| Product / Section                                  [User]  |
+------------------------------------------------------------+
| Nav         | [Exact title or PURPOSE: ...]   [Exact CTA]  |
|-------------+----------------------------------------------|
| Item        | [Exact copy/data or DISPLAY: responsibility] |
| Item        |                                              |
|             | [Exact primary label] [Exact secondary label] |
+------------------------------------------------------------+
```

### States
- Loading: [Skeleton, spinner, progress, disabled controls]
- Empty: [Message and next best action]
- Error: [Error message, retry, support path]
- Permission: [Access denied or request access path]
- Success: [Confirmation and next step]

### Content, Style, Media & Motion Notes
| Region | Content mode | Exact wording or display contract | Content priority | Style direction | Image / media | Motion | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [Region] | [exact copy / display contract] | [Verbatim wording, or what to show + intended takeaway/action + source + constraints] | [must-have / secondary / defer] | [Visual job and hierarchy/comprehension purpose] | [required / optional / none; purpose] | [required / optional / none; purpose] | [Status, fallback, or handoff question] |
````

## Mobile Layout Template

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

## Dashboard Layout Template

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

## Automation Run Detail Template

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

For each primary screen or workflow, define:

- Default state.
- Loading or long-running state.
- Empty state.
- Validation error or integration failure state.
- Permission or blocked state.
- Success or completion state.

If a state does not apply, write `Not applicable` and briefly explain why.
