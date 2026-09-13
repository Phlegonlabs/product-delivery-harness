# Visual Direction Guide

Use this guide only when the human owner explicitly asks `design-system-compiler` to reopen visual direction after `PRD.md` has frozen the UI surface contract and approved `wireframes.html`. The normal Design System Compiler path consumes the already approved UI Design Handoff and skips this guide. `PRD.md` remains canonical for product structure and behavior; `wireframes.html` is its structural interactive projection.

## Builder UX Direction Gate

Consume the recorded `Builder UX Direction Decision` from `PRD.md`. It must cover experience priority, guided versus expert control, information density, familiar versus expressive interaction, primary layout preference, confirmation and recovery behavior, and validation depth. Mark every decision `selected`, `provisional`, or `assumed`.

Use `assumed` only when the human owner explicitly authorizes that assumption; the agent cannot self-authorize it. If the decision is missing or incomplete, ask the questions, return the bounded decision update to `product-definition-builder` or the named product owner for recording, and stop. Do not edit `PRD.md` from this skill. Resume only after the recorded source is available.

Builder preference controls direction, not usability claims. When preference conflicts with observed user needs, accessibility, or task evidence, preserve the conflict as a hypothesis and name the prototype or user test needed to resolve it.

## Visual Direction Gate

Run this gate only for the explicit direction-reopen request, after the PRD UI surface contract and matching wireframes pass their quality and approval checks, and before fixing design-system tokens or components. The direction gate and the UI Preview Gate are required unless the human owner explicitly waives preview review with a recorded reason.

Select the same one or two representative PRD surfaces for every direction and carry:

- the selected `UI-*` surface and region IDs;
- the approved wireframe's region order, grouping, element inventory, state coverage, and responsive rearrangement;
- each surface's purpose, layout pattern, density, actions, states, and responsive constraints;
- the approved Copy Freeze owner, locale, date, exact static strings, action labels, alternate-state copy, and dynamic display contracts;
- the Builder UX Direction Decision, known brand constraints, and product-specific visual goals;
- relevant sourced or reported `MR-*` findings and their source IDs; and
- an instruction that scope, routes, content responsibilities, interaction behavior, and trace IDs are frozen.

### Style And Reference Intake

Read `market-research.md` and the `MR-*` citations in `PRD.md` when they exist. Build a short Market Design Evidence Brief containing only findings that can reasonably affect audience fit, category expectations, trust, information density, differentiation, or product tone. Keep each item tied to its `MR-*` and `S-*` source IDs. Use only `sourced` or `reported` findings. Treat `UNVALIDATED` rows as open questions, not evidence. Label every resulting design implication as an inference.

If prior market research was skipped, blocked, missing, or contains no relevant supported finding, say so. Ask whether the owner wants to return to `product-definition-builder` for research or continue with product evidence only. Do not claim that a recommendation is market-research-backed when that evidence is unavailable.

Ask the human owner what style they want and whether they already have visual references in one combined, product-specific set. Cover desired character, density, color constraints, typography feel, imagery or icon preferences, motion tolerance, disliked patterns, and optional images, screenshots, URLs, Figma views, named products, or brand references. Say that `Check This` remains available if the first directions do not fit. Derive the questions from the product's purpose, audience, content, platform, brand inputs, PRD surface contract, and Market Design Evidence Brief. Never reuse a fixed catalog. The answers form a non-binding Visual Preference Brief, not a token specification. End the turn and wait for the answer; do not recommend styles in the same turn as these questions.

If the owner supplies a reference, read `design-reference-guide.md`, inspect it through the matching source route, return traceable `Adopt / Adapt / Avoid` principles, and end the turn for confirmation. Do not generate directions from owner-supplied signals before that confirmation.

### Reference-Informed Direction Recommendations

After the combined intake and any owner-supplied reference confirmation are resolved, run `impeccable-concept-generation.md` first. Use its surface-mode, cultural-world, and challenger pass to widen the conceptual field, then use `frontend-design`, the design method selected by the PRD UI Design Handoff, and `design-reference-guide.md` to normalize the result into exactly three materially different, product-specific style directions. Record Taste applicability, Design Read, and dials through `../../product-definition-builder/references/ui-design-pass.md` when Taste applies; use `frontend-design` plus the platform or official design-system conventions when it does not. Do not add a fourth. The only reduction is an owner-requested lightweight direction pass per `design-reference-guide.md`'s Lightweight exception, which the agent never proposes.

Find and inspect one current public reference for every direction; add a second only when it contributes a distinct useful mechanic. Include one contemporary or modern direction by default and a second only when preference, product constraints, and valid evidence support a materially different modern treatment. Modern is an evidence-backed quality lane, not a fixed catalog entry or `modern-minimal` default.

Base each recommendation on the Visual Preference Brief, valid Market Design Evidence Brief, inspected visual references, and frozen product constraints. For each direction, provide a versioned `VD-*` ID, its product fit, evidence, inspected `REF-*` sources, proposed `RP-*` principles, visual rules, tradeoff, and avoid list.

Do not call a direction market-supported when prior market research was skipped, blocked, missing, `UNVALIDATED`, or irrelevant. `MR-*` and `S-*` market evidence and `REF-*` visual evidence are separate lanes.

The three directions use the same frozen PRD, approved wireframe structure and states, and Copy Freeze. Present the full direction set through `design-reference-guide.md`'s Direction Checkpoint before building connected HTML. The human owner may `Select`, `Reject`, `Mix`, or `Check This`; only a selected direction with confirmed principles proceeds through `../../product-definition-builder/references/ui-design-pass.md`'s connected interactive HTML route. Image and motion positions remain deferred-generation placeholders. A revision produces a complete versioned set of exactly three directions, not an appended fourth. In an owner-requested lightweight direction pass, each set contains one direction instead of three.

For an explicit direction-reopen request, `design-system-compiler` must load `impeccable`, `frontend-design`, and the design method selected by the PRD UI Design Handoff. Load `design-taste-frontend` only where its recorded applicability allows it. If a required skill is unavailable, stop; do not use a fallback design path. The connected HTML remains non-canonical until the human owner approves it and `product-definition-builder` records it in the UI Design Handoff. Deferred media or motion prompts explore intent only; this pass does not invoke a generator, add product scope, or silently change the canonical PRD or wireframe contract.

If the visual pass exposes a structural problem, return a concise finding tied to the affected `UI-*` IDs. `product-definition-builder` and the human owner decide whether to revise and reapprove the PRD and wireframes. Only then may the visual pass continue.
