# Design Reference Guide

Use this guide after structural wireframes pass and before visual-direction selection. It governs public references found by the agent and images, screenshots, Figma views, URLs, named products, or brand references supplied by the owner. Treat them as `design inspiration` by default. A `page-faithful target` requires a separate explicit user request and frozen conformance scope; never infer faithful-copy intent from the presence of a visual source.

## Evidence Boundary

Keep product-market evidence and visual evidence separate:

- `MR-*` and `S-*` belong to `market-research.md`. They support audience, category, trust, and product-fit claims.
- `REF-*` records an inspected visual source. It supports only the design mechanics actually visible in that source.
- `RP-*` records a proposed `Adopt / Adapt / Avoid` principle derived from one or more `REF-*` sources.

Never add `REF-*` or `RP-*` rows to `market-research.md`. A visual reference does not prove market demand, and market research does not prove a visual treatment. Label every market-to-design implication as an inference.

Search results, snippets, text-only descriptions, and thumbnails may help discover a source, but they are not visual inspection. Open and inspect the source before claiming that it demonstrates a design mechanic. Record the retrieval date because public references can change.

## Reference Record

Create a non-canonical record for every candidate source:

```text
REF-001
- Type: attachment | screenshot | figma | url | named-product | agent-discovered
- Source: <attachment label or direct public URL>
- Supplied by: owner | agent
- Inspected: <YYYY-MM-DD>
- Scope: <pages or frames; desktop/mobile viewport; visible states>
- Status: inspected | partial | blocked
- Limitations: <what the evidence cannot establish>
```

Preserve existing `REF-*`, `RP-*`, and selected `VD-*` identities across revisions and enhancements. Append new IDs and never reuse a retired ID for a different source, principle, or direction.

Tag every extracted statement:

- `observed`: directly visible in the inspected source;
- `measured`: established from available DOM/style information or comparable multi-viewport evidence;
- `inferred`: a design interpretation rather than a source fact; or
- `not observable`: unavailable from the current evidence.

Do not turn screenshot pixels into tokens. Recreate confirmed principles with accessible, platform-fit values and validate them through the normal design-system checks.

## Source Routing

| Source | Inspect | If blocked or ambiguous |
|---|---|---|
| Attached image or screenshot | Open every image with the available image-inspection capability. Label images separately; distinguish repeated, one-off, and conflicting signals. | Ask the owner to attach a readable copy. Do not infer unseen content. |
| Figma view | Inspect the named frame with an available Figma capability or a public browser view. | Request exported PNG/PDF or screenshots. Never bypass permissions. |
| Live URL | Use an available browser to inspect the supplied page plus at most two related representative pages. Compare desktop and mobile and inspect only reachable relevant states. | Do not bypass login, paywalls, robots, or access controls. Request screenshots or an export. |
| Named product | Resolve it to a specific public screen, flow, or page before inspection; prefer official product pages, official design systems, or first-party case studies. | Ask which screen or flow matters when multiple interpretations would change the result. Never treat an entire brand as inspected. |
| Agent-discovered reference | Search current public sources, then open and inspect the selected source. Prefer first-party pages and design systems over roundups. | Skip blocked candidates and find an inspectable source. If no visual-inspection path remains, stop and request owner-supplied material. |

A static image cannot establish motion, responsive behavior, hover, focus, or interaction transitions. Mark those dimensions `not observable` unless they were inspected directly. A single viewport cannot establish responsive behavior.

If no usable visual-inspection tool or readable source is available, disclose the limitation and stop at the Visual Direction Gate. Do not fabricate references, URLs, access dates, or observed traits, and do not fall back to unaided design.

## Extraction Dimensions

Extract only what the evidence supports:

- hierarchy, reading order, and information density;
- grid, alignment, container logic, and spacing rhythm;
- typography character, roles, and scale relationships;
- palette roles, contrast intent, and non-color status cues;
- surfaces, borders, radius, shadow, and layering;
- recurring components, controls, icons, imagery, and data display;
- visible interaction and content states;
- motion only when directly observed;
- responsive behavior only from multi-viewport or inspectable implementation evidence; and
- accessibility risks and evidence limitations.

Do not copy a logo, brand identity, illustration, photography, exact copy, HTML/CSS, source asset, exact screen structure, or distinctive composition. `image-to-code` and `url-to-code` are separate implementation or cloning workflows; never invoke them automatically from this extraction flow.

## Principle Confirmation

Return a concise analysis before using owner-supplied or `Check This` material:

```text
RP-001
- Treatment: Adopt | Adapt | Avoid
- Principle: <design mechanic, not a copied asset>
- Evidence: REF-001
- Product fit: <why it fits or conflicts with the frozen product>
- Expected consequence: <hierarchy, token, component, state, motion, or responsive effect>
- Status: proposed | confirmed | rejected
```

End the turn and wait for the human owner to confirm or correct the principles. Only confirmed `RP-*` items may shape revised directions or the final design system. Agent-discovered sources may illustrate an initial candidate while their `RP-*` items remain proposed; selecting that direction confirms them only when the owner explicitly accepts the listed principles.

## Initial Direction Set

After the combined Style And Reference Intake is resolved:

1. Run `impeccable-concept-generation.md` from the frozen wireframes, Visual Preference Brief, Builder UX Direction, and valid market evidence. Normalize its surface-mode, concept-world, and challenger results into product-specific direction hypotheses.
2. Find and inspect one primary current public reference for every direction. Add a second only when it demonstrates a different useful mechanic.
3. Present exactly three materially different directions with IDs `VD-R1-01` through `VD-R1-03`. Do not add a fourth.
4. Include one contemporary/modern reference-informed direction by default. Include a second only when owner preference, product constraints, and valid evidence support a materially different modern treatment. Keep the remaining direction deliberately contrasting.
5. If the owner rejects modern or product, platform, accessibility, or brand constraints make it unsuitable, explain the exception instead of forcing it.

Lightweight exception: the human owner may explicitly request a lightweight direction pass — one direction with one inspected current public reference — when the surface is small, such as a single-screen internal tool. Record that request in the Builder UX Direction decision. The agent must not propose or initiate the reduction. Inspection, `REF-*`/`RP-*` records, confirmation pauses, and frozen structure still apply; rules that only exist for a three-direction set — deliberate contrast between directions, `Mix`, the three-ID ranges — scale down instead: a lightweight round presents its single direction as `VD-R1-01`, and each revision round produces one direction per set instead of three.

Modern/contemporary is an evidence-backed quality lane, not a fixed style name or synonym for `modern-minimal`. Every direction must include its ID, modernity classification, preference fit, applicable `MR-*`/`S-*` evidence, clearly labeled inference, `REF-*` sources with direct URL and retrieval date, observed design mechanics, proposed `RP-*` items resolving to those inspected sources, tradeoff, and avoid list. When valid market evidence is absent, say so and never call the directions market-supported.

## Selection And Revision Loop

- `Select`: select one direction and explicitly confirm or edit its proposed `RP-*` items.
- `Mix`: name parts of multiple directions, produce one consolidated direction for review, then wait for explicit selection and principle confirmation.
- `Reject`: when some directions are rejected, record why and keep the remaining directions selectable. If the owner requests replacements, ask what should change and present a complete versioned set of exactly three rather than appending candidates. If all are rejected, ask what did not fit, update the Visual Preference Brief and avoid list, inspect new references, and produce a new set of exactly three.
- `Check This`: inspect the supplied source, return `Adopt / Adapt / Avoid`, wait for confirmation, then produce a new set of exactly three from confirmed principles.

Version every new set as `VD-R2-01` through `VD-R2-03`, then increment the round number. In an owner-requested lightweight pass, every count of three in this loop reads as one: `Reject`-all and `Check This` produce a revised set of one direction (`VD-R2-01`), and `Mix` does not apply. Preserve the same representative screens, structure, content responsibilities, states, responsive constraints, and trace IDs in every round. Do not fix tokens, primitives, components, or motion variants until one direction and its contributing principles are explicitly confirmed.
