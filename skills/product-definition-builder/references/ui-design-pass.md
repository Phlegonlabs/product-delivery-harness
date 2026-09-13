# UI Design Pass

Run this optional pass only after the human owner explicitly asks to continue beyond an approved Product Definition package and approved `wireframes.html`. It turns the approved structural wireframe into a human-approved visual target before deciding whether a formal design-system pair is useful.

## Frozen Inputs

Every direction and preview uses the same:

- complete in-scope `UI-*` screen set and full responsive-target and non-`n/a` state matrix, with login, registration, recovery, and authentication-error previews marked `n/a` for this visual pass when excluded;
- approved `wireframes.html` page, section, element, action, state, and responsive projection, checked against `PRD.md`;
- exact copy or bounded display contracts;
- Builder UX Direction, brand, accessibility, platform, and performance constraints; and
- the approved Stack Decision Checkpoint, including component foundation and styling approach; and
- applicable `MR-*` market evidence and inspected `REF-*` visual evidence.

The pass may explore typography, color, composition, imagery, texture, and motion intent inside the PRD Motion Need Gate. Every direction records which moments move, their trigger and purpose, how strongly, what stays still, and the required reduced-motion fallback — `design-taste-frontend`'s recorded `MOTION_INTENSITY` when Taste ran, otherwise an explicit concept or `motion: minimal`. Required functional UI motion may run as deterministic local CSS or JavaScript in the review HTML so its meaning and fallback can be judged. Generated video, illustration animation, cinematic treatment, or other provider-created motion remains a labeled static placeholder with a deferred brief; the pass does not implement final generated motion. The pass may not add, remove, reorder, or reinterpret product scope, content responsibility, actions, flows, states, trace IDs, or approved implementation-stack constraints. A structural finding returns to PRD and wireframe approval. A direction that genuinely requires a different component foundation, styling method, runtime, or framework returns to the Stack Decision Checkpoint and then Product Definition Approval before visual work continues; visual approval never overrides technology by implication.

## Motion Stage Contract

1. PRD discovery records the Motion Need Gate and decision authority. It states why motion is required, recommended, not required, or blocked; it does not choose timing curves or implementation values.
2. `wireframes.html` shows motion intent as a static annotation only. It may describe the trigger, purpose, and fallback but contains no final animation.
3. The design-reference HTML may run deterministic local UI motion needed to judge state feedback, progress, continuity, spatial relationship, or interaction meaning. Test both normal and reduced-motion modes. Generated or cinematic motion stays deferred.
4. When the Design System Need Gate is `required`, `design-system-compiler` turns approved motion into named tokens and closed variants. When it is `not_required`, the approved HTML behavior and PRD handoff are the implementation authority.
5. Delivery Harness implements the approved motion and verifies its normal, reduced-motion, responsive, performance, and accessibility behavior. It does not invent a missing motion decision.
6. A later media-generation pass may create only the approved deferred asset. It needs its own authorization and cannot change product scope, controls, states, or flows.

## Taste Applicability Gate

The standard recipe is both skills, working from the approved PRD package: `design-taste-frontend` leads the overall design direction for the surfaces it covers, and `frontend-design` executes the surfaces Taste excludes. Decide the split first, then run the whole pass as one combined effort — Taste first for the overall direction, `frontend-design` filling its named surfaces. Neither skill reopens product scope; both start from the frozen inputs below.

Load `design-taste-frontend`, read its scope, and record one result:

- `applicable`: landing, portfolio, editorial, public marketing, or compatible redesign surfaces;
- `partially_applicable`: only the named compatible public surfaces use it; or
- `n/a: <reason>`: dense dashboards, data tables, multi-step operational UI, native mobile, or another exclusion declared by the skill.

When applicable, record its one-line Design Read plus explicit `DESIGN_VARIANCE`, `MOTION_INTENSITY`, and `VISUAL_DENSITY` values with product-specific reasons. When it is partially applicable or `n/a`, load `frontend-design` for the uncovered product surfaces and follow the selected platform or official design-system conventions. Do not force Taste rules onto a surface the skill excludes.

Do not load `gpt-taste` by default and never combine it with `design-taste-frontend`. It is an explicit owner-selected alternative only for a named high-motion experimental marketing surface; record the override and exact scope.

## Direction And UI Preview Gate

Ask the human owner once for desired character, disliked patterns, and any visual references. Consume the PRD Motion Need Gate without re-asking resolved choices. Ask one closed key-surface treatment question for the hero and each comparable marquee surface only when its gate is `blocked` or the owner asks to change it: `motion-led`, `imagery-led`, `motion + imagery`, or `quiet`. Record the answer per surface with the direction. When the owner chose AI recommendation, the pass may recommend `required`, `recommended`, or `not_required` with product-specific reasons, but it still returns generated motion, autoplay or sound, a material performance budget, an accessibility exception, or scope expansion to the owner. Treatments already recorded in `wireframes.html` arrive pre-answered: confirm or change each one instead of re-deriving it, then refine its dedicated `draftPrompt` into the later MCP-generation handoff. Generated positions record `generationStatus: deferred`; this pass never invokes the provider. When the product has no marquee surface, record the question `n/a` with a reason instead of asking. Inspect supplied or current public references before claiming their visible mechanics. Keep market evidence and visual evidence separate.

Default to one recommended product-specific direction. Produce three materially different directions only when the owner asks to compare alternatives or when a recorded visual conflict cannot be resolved with one recommendation. Every compared direction must use the same complete screens, content, states, and PRD viewport or size-class set. A single-width preview cannot establish responsive behavior.

Record every inspected visual source as a `REF-*` record and every owner-confirmed `Adopt / Adapt / Avoid` principle as an `RP-*` record, using the formats in `../design-system-compiler/references/design-reference-guide.md`. Give every direction a `VD-*` ID under that guide's round versioning: a default single-direction pass records `VD-R1-01`, and each later revision round increments. Name the selected `VD-*` direction and its confirmed `REF-*` / `RP-*` IDs in the handoff so the design-system step can read the provenance without re-deriving it.

Choose iconography through an online lookup, not from memory. When the approved structure uses icons — navigation, actions, status, empty states — consider exactly four maintained icon libraries: Lucide, Phosphor, Heroicons, and Tabler. Pick the primary set and the named fallback from this closed candidate set by fit with the selected direction's character (outline versus solid, stroke weight, density), and verify each candidate's license, framework support, and maintenance status against its official source on the pass date. Record them in the handoff's `Iconography:` line with the cited official-source URLs and retrieval dates, and mark an unevidenced pick `UNVALIDATED` — the same rule as market research. Do not widen the candidate set with other libraries; a need these four genuinely do not cover is recorded as an open question for the owner rather than a silent substitution. Skip the lookup only when the product uses no icons or no web search or fetch tool is available, and record which reason applied; never silently default to a remembered library.

Choose typography through the same online-lookup discipline. Recommend a font pairing — display and body, which may be the same family — that fits the selected direction: search maintained families on Google Fonts or the family's official site, and verify on the pass date the license, the needed weights and optical sizes (variable fonts where they help), and Latin plus CJK coverage. For a Chinese-language product, record the CJK stack explicitly — a Noto Sans TC/SC class family or the platform system-font stack — with the fallback order and how the Latin and CJK faces combine. Record the pairing, the loading strategy (self-host versus CDN, subsetting, `font-display`), and the cited official-source URLs with retrieval dates in the handoff's `Typography:` line; an unevidenced pick is `UNVALIDATED`. Skip with a recorded reason only when the platform fixes the faces (for example a native app bound to system fonts) or no web tool is available.

Record the color decision in the handoff's `Color & dark mode:` line: how the palette derives from the brand or direction base (name the scale approach), whether dark mode is in scope for this pass or a named later scope, and the cited source for any palette system the derivation used. This line records the selection; contrast verification stays with `design-system-compiler`'s `check_color_contrast.py` at design-system compile time, and a palette that cannot pass contrast is revised there, not silently kept.

Produce one self-contained design-reference HTML review file for every UI-bearing product: web, native or cross-platform mobile, and desktop. It contains every in-scope `UI-*` screen in one connected review surface, full design-reference CSS, a left sidebar, working screen and state switching, and the product actions needed to traverse every approved flow. Every visible product control responds: it navigates to the recorded screen, switches a declared state, opens the documented modal, drawer, or other overlay, or shows recorded inline feedback. A visible control with no response is removed or wired; no dead controls and no isolated stills.

The review file never calls a live backend, account, credential, identity provider, image generator, or animation generator. It may run deterministic local CSS or JavaScript motion required by the Motion Need Gate, and it must expose a working reduced-motion fallback. Login, registration, recovery, and authentication-error preview scenes are omitted; the file starts from the PRD-recorded authenticated or main entry surface, while the PRD records the omitted preview scope as `n/a` without deleting production authentication requirements. Each included screen implements every declared viewport or size class and non-`n/a` state. Native-only chrome may be represented by a labeled HTML placeholder; it does not change the one-file route.

When the selected direction calls for photographic, illustrative, or generated motion treatment, place a visible static placeholder at the exact page or region. Record treatment, placement or trigger, dedicated prompt, source decision, reduced-motion expectation for motion, and `generationStatus: deferred`. These entries are the provider-neutral handoff for a later explicitly authorized MCP generation pass. Do not generate, embed, or claim generated image or animation output during this UI Design Pass. This restriction does not prohibit the local functional UI motion described above.

Do not invoke `brandkit` or another generation workflow during this pass. When no approved brand system exists, record later brand exploration as an open option; it needs its own explicit owner instruction and remains non-canonical until its Adopt / Adapt / Avoid principles are confirmed.

The later MCP generation pass may not invent controls, content, states, or flows. Generated output that does so fails its later media review; it never changes the PRD by implication.

## Evidence And Approval

For every retained preview and every covered `UI-* × responsive target × non-n/a state` combination, record:

- preview ID and direction ID;
- `UI-*` surface and state;
- viewport or size class;
- interactive HTML route;
- functional UI motion evidence in normal and reduced-motion modes, plus any deferred generated-media or motion prompt, source, placement or trigger, and generation status when applicable;
- local path and SHA-256;
- observed limitations, including unreadable text;
- the `UI grading:` line from the rubric stage below — grader count or capability-unavailable skip, frozen PRD identity, rubric scope, and reconciled scores; and
- human decision: `approved`, `rejected`, `revision_requested`, or `waived` with reason.

## Responsive Browser Gate

After the first design-reference HTML draft and before human visual approval, run the sibling `ui-grading-rubric.md` against the frozen PRD and candidate HTML. The candidate first passes its Technical Hard Gate. When the host has the required multi-agent browser capability and dispatch is explicitly authorized, run one complete diagnostic wave with one fresh lead grader by default and at most two non-overlapping specialists for an owner request or recorded high-impact risk. The diagnostic wave returns every established finding before the parent creates one consolidated root-cause ledger. The reconciled overall score must be at least 90; `H2`, `H4`, and `H8` must each be at least 90; every dimension must be at least 60; and no `block` or `disputed` dimension may remain. Otherwise the owning design flow makes one repair batch and runs one re-review on the new candidate hash. Never send a below-threshold candidate to the owner for visual approval. If that re-review still blocks, stop for a PRD correction or an explicit owner-approved structural strategy and acceptance matrix; do not continue an open-ended grading loop. When multi-agent capability is unavailable, record the exact capability-unavailable skip and continue with the non-grading gates. Carry the diagnostic ledger, advisory scores, and bounded repair/re-review history into the preview evidence.

Render every in-scope page-target-state in the retained all-screens HTML reference in a real browser before visual approval. Use the left sidebar and in-product actions to reach every page, modal, drawer, and recorded feedback state. At every PRD-declared responsive target, inspect all visible peer elements and container boundaries with long labels, localized copy, validation errors, empty data, dense data, and the other declared edge states. Run the rubric's DOM geometry scan and retain its exact element-pair and boundary results. Reject broken navigation, dead controls, unintended element overlap, clipping, occlusion, broken spacing or wrapping, off-container content, or horizontal page overflow. Confirm readable order and line length, minimum target size, keyboard path where applicable, and that resizing does not strand focus or hide a required action. An intentional modal, menu, tooltip, sticky region, or other overlay must name its stacking, focus, escape/dismissal, and safe-area behavior in the evidence and handoff. Browser unavailability blocks approval of an HTML implementation target; a visual-review waiver does not convert an unchecked preview into binding page-faithful authority.

Preview artifacts stay outside `docs/product/`. When an approved HTML preview will serve as the page-faithful implementation reference, request retention by default: disclose and obtain exact write approval for one all-screens file under `docs/design/ui-references/<run-id>/`, the dedicated UI references folder. That file contains the full design-reference CSS and connected reviewer behavior for every recorded screen. Other previews are retained only when the owner requests it; otherwise use temporary storage and say that it will not publish with the package. When the owner declines retention and that preview is the approved page-faithful target, the handoff must record the target as temporary: the visual authority then reverts to `PRD.md` plus approved `wireframes.html` once the run ends, because the recorded path stops resolving. A durable target binding requires retention, and Harness cannot implement from an HTML reference whose recorded path is temporary.

When a later approved UI target supersedes retained UI references, archive the superseded files by moving them under `docs/design/archived/<YYYYMMDD-HHMMSS>-<run-id>/` — the same archive-not-delete discipline `references/artifact-lifecycle.md` applies to superseded product documents — and update the UI Design Handoff to the new live paths. Never delete a superseded reference file or leave a live handoff entry pointing at an archived path.

When a style-impacting enhancement updates a retained HTML reference, regenerate the affected screens' style layer from the current direction instead of appending to the previous file's CSS. Before presenting the updated reference for approval, check it for style blocks inherited from the superseded version — orphaned selectors, duplicate rules, and overrides the updated screens no longer use — and remove them; a reference that accumulates styles from previous versions is not approvable. Editing a retained reference file in place supersedes its previous content: refresh the handoff's recorded SHA-256 for that file in the same run and archive a copy of the pre-edit file under `docs/design/archived/`, exactly as a superseded reference set would be.

An approved preview becomes an implementation target only when `PRD.md` records its source path or immutable version, SHA-256, named routes and states, the exact responsive set, passing browser-matrix evidence, acceptance tolerance, and allowed deviations. This page-faithful target is visual authority for only that recorded scope. When the approved target is design-reference HTML, `delivery-harness` implements every recorded route from the same approved all-screens HTML reference within the recorded tolerance. Approval proves visual-direction conformance, not usability or production readiness.

## Design System Need Gate

After visual approval, record exactly one result in `PRD.md`:

- `required`: the owner requests a formal design system; an existing design-system pair is already canonical; or the product needs reusable shared tokens and closed component variants across multiple surfaces, themes, platforms, teams, or automated conformance checks;
- `not_required`: the approved work is a small or single-surface UI whose visual target, PRD behavior, and wireframes are sufficient for implementation; or
- `blocked`: the owner decision, source evidence, or approved preview needed to decide is missing.

Record the decision owner, reason, affected scope, and replacement visual contract. `not_required` is a normal outcome, not a waiver. When `required`, invoke `design-system-compiler` only after the UI target is approved; it compiles the approved direction into `design-system.md` and `design-system.json` without reopening visual direction by default. When `not_required`, pass the approved page-faithful target directly to Harness with `PRD.md` and the approved `wireframes.html` review projection; for an HTML pass that means the retained all-screens reference file with its recorded hash.
