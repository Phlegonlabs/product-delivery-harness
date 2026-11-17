# Design Reference Guide

Use this guide after UI Design Intake when the owner supplies a screenshot, image, URL, Figma view, named product, or brand reference, or when `frontend-design` needs a current public reference to ground a direction.

## Authority

References are evidence, not product authority. `PRD.md` owns product behavior and reviewed structure; `ui-design.md` owns the selected direction and design constraints. A reference cannot add a route, control, state, claim, or stack requirement.

Treat a supplied reference as `design inspiration` unless the owner explicitly requests page-faithful conformance and names the scope and tolerance.

Link supplied or inspected sources to the existing Design Brief with what the owner wants to learn, avoid and apply to specific UI surfaces. A useful source may be labeled for composition, typography, motion, or another bounded role; an avoid example records its concrete product reason. Keep owner preferences distinct from the agent's observations and proposed principles. A missing or inaccessible image, website or Figma view remains uninspected; record that limitation instead of inventing `REF-*` observations. A supplied reference is not permission to clone a page or change product/stack decisions. An explicit `no references` answer uses the research route below; do not treat an unanswered question as that answer.

## Proactive Reference Research

### Reference Board

Words cannot carry layout, spacing and type; pictures can. For a new visual scope (initial design, explicit full redesign, or an enhancement whose accepted delta changes the direction), gather a board of **9 to 12 captured references** before direction studies. Owner-supplied references count toward it. The direction and HiFi author works from the captures, so the prompt stays short.

- Pick current public pages that match the product's task and platform, not a generic color collection.
- Between them, the entries cover layout and section structure, spacing and density, typography, color and surface, control treatment, and motion when a motion intent is in scope. Each entry names the one or two roles it is there for.
- Each entry is a real inspected page at the relevant viewport and state, captured as a full-page screenshot under `docs/design/directions/<round>/references/`, with its path and SHA-256 in its `REF-*` record. A motion lesson also keeps a short recording there, with its own path and SHA-256, and one still frame from it; the still is the entry's image on the board sheet.
- A smaller board is allowed with its count and reason recorded: `Delivery profile: mvp` (floor of 5), an owner-named page-faithful target, or an owner who supplied a complete set. An enhancement that keeps the approved direction needs no board.
- References set quality and feel; the design is this product's own. Two or more references may feed one direction; no direction copies one reference. An owner-named page-faithful target is the exception: it follows its recorded scope and tolerance.

Show the board to the owner as one page built with `capture_sheet.py`, together with the proposed Adopt / Adapt / Avoid principles, in the confirmation turn under [Records](#records). It adds no turn. Resolve `<ui-design-builder-skill-root>` as [Installed Commands](../../delivery-harness/references/installed-commands.md) states.

```text
python "<ui-design-builder-skill-root>/scripts/capture_sheet.py" --repo-root . --title <text> --row <label> <image> [<image> ...] [--row ...] --out <html>
```

A one-image row is a board entry. The script prints each image's SHA-256.

Curated candidate directories include [Astro themes](https://astro.build/themes/), [Tailwind Plus UI blocks](https://tailwindcss.com/plus/ui-blocks/marketing) (paid reuse—verify the license), [application UI blocks](https://tailwindcss.com/plus/ui-blocks/application-ui), [Codrops](https://tympanus.net/codrops/), [Uiverse](https://uiverse.io/), and [Open Props](https://open-props.style/). A directory entry is not evidence by itself: inspect the actual page and relevant desktop/mobile state before recording it. Record every inspected source as `REF-*` and its proposed `Adopt | Adapt | Avoid` rule as `RP-*`; never install a template or dependency without the approved stack's explicit component/source decision and license review.

For motion or 3D lessons, also look at [Motion examples](https://motion.dev/examples) (Motion+ entries are paid), the [GSAP showcase](https://gsap.com/showcase/) and [three.js examples](https://threejs.org/examples/). Use only the ones that match an approved route. A motion reference is a recording; before implementing from it, write motion notes as [Motion And Media Routing](motion-and-media-routing.md#motion-references-and-notes) states.

### Finding And Capturing References

Use manual website search, owner-shared example links or screenshots, and any reference tool the owner has already connected. A reference MCP (for example Inspo or Awwwards) or a browser tool (for example agent-browser) may find candidates and capture pages and recordings. An agent never installs or connects one itself; it asks the owner. A tool hit is still only a candidate: the actual page, viewport and state must be inspected and captured before it becomes a `REF-*`. The optional [design catalog](../../delivery-harness/references/option-library/design.md) compares Mobbin for real product screens/flows, Dribbble for visual studies, Awwwards for website/interaction references, Refero for app patterns, and MotionSites for landing/section/prompt ideas. MotionSites provisionally means `https://motionsites.ai/`; confirm a different owner-supplied URL before attributing an inspection to it. A product prototype, concept shot and original website are different evidence scopes.

For each chosen example, retain its URL, the original website URL when available through Visit Website or another link, the intended lesson and affected UI surface. Inspect the actual page, relevant viewport and state; for a motion lesson retain a short capture or a working source with an explicit capture limitation. If login, payment or access is unavailable, use inspectable owner-supplied material and state what remains uninspected. A directory listing or search snippet cannot become a confirmed `REF-*`.

React Bits is a reusable React effect/component source; Anime.js is an animation engine. Compare their roles with the adopted stack and the [motion catalog](../../delivery-harness/references/option-library/motion.md). A liked example does not authorize copied code or an added dependency: check the selected item's license, source, actual dependencies and maintenance duties first. Propose scoped `RP-*` principles and use the existing owner-confirmation step below before designing from them.

Keep what was inspected, not only a description of it: every confirmed `REF-*` has its capture under `docs/design/directions/<round>/references/` with path and SHA-256, as the [Reference Board](#reference-board) states. A source that cannot be captured keeps its written record with the limitation stated and does not count toward the board.

Adapting a template's markup, CSS or animation code into HiFi is allowed when its license permits it and the code fits the approved stack. Record the source URL, license and what was changed in the `RP-*` principle. Paid or unclear licenses need the owner's decision before any code is copied.

Research composition, typography, spacing, information density, responsive behavior, and control treatment. Two references may support one clear direction. A new package defaults to three distinct directions; the owner may explicitly choose one recommendation. Changing only an accent color is not a distinct direction. A structural finding returns to `product-definition-builder`; it cannot become a layout choice inside direction work.

For each useful reference, record whole-template adaptation, selected-component reuse or custom implementation in the RP principle, with stack compatibility, license/cost and maintenance implications. A reference never selects Tailwind or a component library by implication. On native surfaces, inspect platform-native patterns and official guidance instead of treating Web CSS examples as native components. If browsing is declined, unavailable or unsafe for confidential inputs, record the limitation and use inspectable supplied/local references; never invent a source or claim visual inspection from search snippets.

## Records

Record every inspected source with a stable `REF-*` ID, one record per source:

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

Show the proposed Adopt / Adapt / Avoid set, with the reference board when one was gathered, to the human owner and end the turn. Do not design from supplied or researched references until the owner confirms the principles. `Delivery profile: mvp` is the exception for a researched board: it takes no turn of its own. The author designs the one study from it as a proposal, presents the board and principles with that study, and the owner confirms them in the Visual Approval. References the owner supplied, and principles the owner already confirmed, bind from the start. Keep `RP-*` principles few: only what is adopted, adapted or avoided.

## Direction Records

`frontend-design` creates directions only after the Visual Preference Brief and any supplied-reference principles are confirmed. Give each direction a versioned `VD-R<round>-<number>` ID. The direction-mode rule is in [Style Intake Gate](ui-design-pass.md#style-intake-gate). A rejected set produces a complete new round; do not append a fourth direction to the old round. In the selection reply the owner may instead ask for variants of one study. That opens one new complete round of three studies that keep the chosen study's concept and each change one named axis, such as layout, typography, color and surface, or motion. Each records the study it is based on (`Based on`) and its axis in `### Variant round` ([Direction Review Assembly](output-contract.md#direction-review-assembly)). It follows every round rule: the same frozen inputs and representative cases, one author per study, the chosen study's author writing or continuing it when the host allows. The earlier round stays as non-canonical evidence, and only the new round is in the active tables. Allow one variant round per visual scope unless the owner asks for another, and none under `Delivery profile: mvp` unless the owner asks. It is the same owner decision as selection, not another approval step.

Each direction records product fit, the accepted Design Brief page-purpose/profile and type/density/headline constraints, visual rules, confirmed `REF-*` and `RP-*` evidence with useful roles and avoid rationale, tradeoffs, avoid rules, and its relationship to the approved component foundation and styling approach. Carry selected direction decisions into connected HiFi and H1–H9 review; selected profile and motion decisions reach conditional compilation and implementation through their existing contracts. A current public reference may support a direction only after it has been inspected. Market evidence (`MR-*`) and visual evidence (`REF-*`) remain separate.

Use the representative studies and `### Direction comparison` table in `ui-design-pass.md` before asking the owner to select. The same primary and stress cases appear in every direction with unchanged content. Reference moodboards and written style labels do not replace rendered product studies. Preserve prior rounds as non-canonical evidence; only the current complete round belongs in the active table. `VD-R0-*` studies from the [optional R0 round](review-workflow.md#optional-r0-exploration-round) are exploratory and never enter that table.

Impeccable does not generate directions. It reviews the connected HiFi candidate under `ui-design-pass.md`.
