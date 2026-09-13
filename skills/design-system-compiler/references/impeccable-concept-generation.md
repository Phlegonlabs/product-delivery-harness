# Impeccable Concept-Generation Bridge

Use this bridge only inside an owner-requested Visual Direction Gate. It adapts Impeccable's concept-generation method to this repository's canonical PRD and design lifecycle; normal design-system compilation skips it.

## Authority Boundary

- `PRD.md` and its Builder UX Direction remain product truth; approved `wireframes.html` is the structural interactive projection.
- `PRD.md`, `wireframes.html`, `design-system.md`, and `design-system.json` remain the only canonical product and design handoff.
- Do not run Impeccable `init`, `document`, `craft`, `live`, build, or finish flows from this bridge. Do not create `PRODUCT.md`, `DESIGN.md`, `.impeccable/`, or another competing product authority. The connected interactive HTML and deferred media or motion handoffs may be created only through `../../product-definition-builder/references/ui-design-pass.md`.
- Treat Impeccable output as design-stage evidence. `design-system-compiler` normalizes accepted results into `VD-*`, `REF-*`, and `RP-*` records before anything becomes canonical.
- Do not run `concept-seed.mjs` directly here. Its required `PRODUCT.md` would create a second product authority. Apply the same generation and challenger method to the frozen inputs instead.

## Required Inputs

Before generation, freeze:

- the staged PRD, approved wireframes and Copy Freeze, architecture, stack decisions, and Builder UX Direction;
- approved scope, routes, representative screens, actions, content responsibilities, states, traces, accessibility, platform, and performance constraints;
- the PRD UI surface contract and Market Design Evidence Brief;
- the Visual Preference Brief, avoid list, and confirmed `RP-*` principles from supplied or repository-discovered references.

Missing product truth returns upstream. It is not filled with design taste.

## Generation Route

For each representative surface, name its primary mode:

- `Persuade` — earn attention and move the visitor through a story toward action.
- `Operate` — support repeated work, decisions, and dense state changes.
- `Read` — make sustained reading, scanning, and comprehension comfortable.
- `Experience` — make an immersive sequence or atmosphere central to the product value.

Then classify the visual-authority scope:

1. **Local extension of an established world** — inherit the incumbent system. Do not run a concept tournament. Generate one bounded treatment that fits the existing world, then apply the normal reference and owner gates.
2. **Whole surface inside an established world** — derive five to seven materially different structural concepts for the surface mode. Stress-test them against the frozen product, then carry the strongest three into the normal `VD-*` set.
3. **New or replacement visual world** — write four prompts before proposing a direction:
   - the product's unique mechanism;
   - the audience's real cultural home or working scene;
   - the category's common visual rut; and
   - the useful opposite of that rut.

   Derive seven concrete cultural systems, artifacts, places, or rituals spanning at least three material families, such as editorial, industrial, civic, archival, scientific, domestic, retail, performance, craft, or transport. Convert the viable candidates into complete product directions, not mood-board adjectives.

## Challenger Pass

Compare candidates on both:

- **audience identification** — the intended user can recognize a world that feels made for them; and
- **product clarity** — the world makes the product mechanism and next action easier to understand.

Classify each candidate as `winner`, `competitive`, or `declined`. A declined candidate may donate one useful discipline — a stronger first viewport, clearer form, more legible hierarchy, or better material contrast — but does not survive as a hidden fourth direction.

Normalize the result into exactly three materially distinct `VD-R<round>-01..03` directions, except for the existing owner-requested lightweight exception. The set should contain the committed lead plus the strongest challengers that remain product-fit. Impeccable's assignment, challenger, and optional-pick framing may help debias ordering; it never overrides the exact-three set or the human selection gate.

For each normalized direction, add to the existing direction anatomy:

- concept thesis and named visual world;
- why the audience would recognize that world;
- visitor or operator path through the representative surface;
- first-viewport composition;
- form language and signature interaction;
- how the idea reaches the other shipped surfaces without changing their structure;
- honest risk; and
- the inspected `REF-*` evidence and proposed `RP-*` consequences required by `design-reference-guide.md`.
- one coherent reference-role map and avoid list; do not splice unrelated sources into the concept.

A concept catalog, cultural example, or Impeccable challenger is not visual evidence by itself. Every presented direction still needs its own inspected current public `REF-*` source.

## Rerolls And Selection

- `Reject`-all is a reroll. Ask what failed, update the Visual Preference Brief and avoid list, then regenerate a complete versioned set.
- Map an owner request for more restraint, familiarity, or convention to a `safer` register.
- Map an owner request for more contrast, novelty, or commitment to a `bolder` register.
- `Mix` may combine named disciplines from multiple directions, but returns one consolidated direction for explicit review.
- Do not fix token values, primitives, components, or motion variants before the owner passes the Direction Checkpoint, selects a direction, and confirms its `RP-*` principles. Never rewrite the approved Copy Freeze during concept generation.

Keep rejected candidates, generation notes, and challenger verdicts outside the published package. The selected `VD-*` provenance and its frozen implementation consequences are the only results that enter `design-system.md` and `design-system.json`.
