# Design Reference Guide

Use this guide after UI Design Intake when the owner supplies a screenshot, image, URL, Figma view, named product, or brand reference, or when `frontend-design` needs a current public reference to ground a direction.

## Authority

References are evidence, not product authority. `PRD.md` owns product behavior and reviewed structure; `ui-design.md` owns the selected direction and design constraints. A reference cannot add a route, control, state, claim, or stack requirement.

Treat a supplied reference as `design inspiration` unless the owner explicitly requests page-faithful conformance and names the scope and tolerance.

Link supplied or inspected sources to the existing Design Brief with what the owner wants to learn, avoid and apply to specific UI surfaces. A useful source may be labeled for composition, typography, motion, or another bounded role; an avoid example records its concrete product reason. Keep owner preferences distinct from the agent's observations and proposed principles. A missing or inaccessible image, website or Figma view remains uninspected; record that limitation instead of inventing `REF-*` observations. A supplied reference is not permission to clone a page or change product/stack decisions. An explicit `no references` answer uses the research route below; do not treat an unanswered question as that answer.

## Proactive Reference Research

For a new visual scope, or a revised one without supplied references, inspect a few current public pages that match the product's task and platform—not a generic color collection. Curated candidate directories include [Astro themes](https://astro.build/themes/), [Tailwind Plus UI blocks](https://tailwindcss.com/plus/ui-blocks/marketing) (paid reuse—verify the license), [application UI blocks](https://tailwindcss.com/plus/ui-blocks/application-ui), [Codrops](https://tympanus.net/codrops/), [Uiverse](https://uiverse.io/), and [Open Props](https://open-props.style/). A directory entry is not evidence by itself: inspect the actual page and relevant desktop/mobile state before recording it. Record every inspected source as `REF-*` and its proposed `Adopt | Adapt | Avoid` rule as `RP-*`; never install a template or dependency without the approved stack's explicit component/source decision and license review.

For motion or 3D lessons, also look at [Motion examples](https://motion.dev/examples) (Motion+ entries are paid), the [GSAP showcase](https://gsap.com/showcase/) and [three.js examples](https://threejs.org/examples/). Use only the ones that match an approved route.

### Manual Website Discovery

Use manual website search and owner-shared example links or screenshots for this reference workflow. Do not install or connect design-reference MCP servers. The optional [design catalog](../../delivery-harness/references/option-library/design.md) compares Mobbin for real product screens/flows, Dribbble for visual studies, Awwwards for website/interaction references, Refero for app patterns, and MotionSites for landing/section/prompt ideas. MotionSites provisionally means `https://motionsites.ai/`; confirm a different owner-supplied URL before attributing an inspection to it. A product prototype, concept shot and original website are different evidence scopes.

For each chosen example, retain its URL, the original website URL when available through Visit Website or another link, the intended lesson and affected UI surface. Inspect the actual page, relevant viewport and state; for a motion lesson retain a short capture or a working source with an explicit capture limitation. If login, payment or access is unavailable, use inspectable owner-supplied material and state what remains uninspected. A directory listing or search snippet cannot become a confirmed `REF-*`.

React Bits is a reusable React effect/component source; Anime.js is an animation engine. Compare their roles with the adopted stack and the [motion catalog](../../delivery-harness/references/option-library/motion.md). A liked example does not authorize copied code or an added dependency: check the selected item's license, source, actual dependencies and maintenance duties first. Propose scoped `RP-*` principles and use the existing owner-confirmation step below before designing from them.

Keep what was inspected, not only a description of it. Save a screenshot, or a short screen recording for a motion lesson, of each confirmed `REF-*` under `docs/design/directions/<round>/references/`, and add its path and SHA-256 to the record. A source that cannot be captured keeps its written record with the limitation stated.

Adapting a template's markup, CSS or animation code into HiFi is allowed when its license permits it and the code fits the approved stack. Record the source URL, license and what was changed in the `RP-*` principle. Paid or unclear licenses need the owner's decision before any code is copied.

Research composition, typography, spacing, information density, responsive behavior, and control treatment. Two references may support one clear direction. A new package defaults to three distinct directions; the owner may explicitly choose one recommendation. Changing only an accent color is not a distinct direction. A structural finding returns to `product-definition-builder`; it cannot become a layout choice inside direction work.

For each useful reference, record whole-template adaptation, selected-component reuse or custom implementation in the RP principle, with stack compatibility, license/cost and maintenance implications. A reference never selects Tailwind or a component library by implication. On native surfaces, inspect platform-native patterns and official guidance instead of treating Web CSS examples as native components. If browsing is declined, unavailable or unsafe for confidential inputs, record the limitation and use inspectable supplied/local references; never invent a source or claim visual inspection from search snippets.

## Records

Record every inspected source with a stable `REF-*` ID:

```text
REF-001
Source: [URL, file, screenshot, Figma view, or named product]
Publisher / owner: [name]
Retrieved or supplied: [YYYY-MM-DD]
Inspected scope: [page, region, state, or mechanic]
Capture: [repo-relative path @ sha256:<hash> | not captured — reason]
Visible evidence: [what was actually observed]
Authority: design inspiration | page-faithful target
```

Turn useful observations into proposed `RP-*` principles:

```text
RP-001
Source: REF-001
Disposition: Adopt | Adapt | Avoid
Principle: [one concrete rule]
Scope: [UI-* surfaces or regions]
Reason: [product-specific reason]
Status: proposed | confirmed | rejected
```

Show the proposed Adopt / Adapt / Avoid set to the human owner and end the turn. Do not design from supplied references until the owner confirms the principles.

## Direction Records

`frontend-design` creates directions only after the Visual Preference Brief and any supplied-reference principles are confirmed. Give each direction a versioned `VD-R<round>-<number>` ID. The direction-mode rule is in [Style Intake Gate](ui-design-pass.md#style-intake-gate). A rejected set produces a complete new round; do not append a fourth direction to the old round.

Each direction records product fit, the accepted Design Brief page-purpose/profile and type/density/headline constraints, visual rules, confirmed `REF-*` and `RP-*` evidence with useful roles and avoid rationale, tradeoffs, avoid rules, and its relationship to the approved component foundation and styling approach. Carry selected direction decisions into connected HiFi and H1–H9 review; selected profile and motion decisions reach conditional compilation and implementation through their existing contracts. A current public reference may support a direction only after it has been inspected. Market evidence (`MR-*`) and visual evidence (`REF-*`) remain separate.

Use the representative studies and `### Direction comparison` table in `ui-design-pass.md` before asking the owner to select. The same primary and stress cases appear in every direction with unchanged content. Reference moodboards and written style labels do not replace rendered product studies. Preserve prior rounds as non-canonical evidence; only the current complete round belongs in the active table.

Impeccable does not generate directions. It reviews the connected HiFi candidate under `ui-design-pass.md`.
