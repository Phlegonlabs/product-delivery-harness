# UI Design Output Contract

## Canonical Artifacts

- `docs/design/ui-design.md`: UI decisions, sources, gates, scores, and handoff.
- `docs/design/wireframes.html`: one internally validated structural projection of every PRD `UI-*` surface for new schema-5 work; older approvals retain their recorded meaning.
- `docs/design/ui-references/<run-id>/index.html` and its manifest-listed sibling HTML pages: the approved connected HiFi design-reference package when retention is authorized.
- `docs/design/design-system.md` and `docs/design/design-system.json`: present together only when the Design System Need Gate is `required`.

New `wireframes/5` authoring has no reviewer-only Design System Draft view, hash, or navigation entry. A historical schema-4 wireframe may retain that view unchanged. These provisional values never replace the formal pair. After formal compilation, `docs/design/design-system-preview.html` is a derived view checked against that pair and its current sources, not a third editable authority. Preserve validated schema-5 wireframe or approved legacy wireframe when generating it; see the compiler's output contract.

Legacy `docs/product/wireframes.html` and `docs/product/design-system.*` remain readable. New or revised artifacts publish under `docs/design/`; do not move an existing legacy artifact without exact owner authorization.

## Translation And Freshness Handoff

Keep the `design-translation.md` table and `design-freshness.md` observations in this existing handoff or linked task evidence. Record incremental versus explicit full rebuild, fixed/provisional decisions, selected recipe/version, language and iPhone scope, representative stress cases and animation boundaries. No new approval gate or product authority is created. Inspector metadata and bilingual/motion examples are not shipping copy unless the PRD's sourced copy contract includes them.

## Reviewer Navigation And Design Specifications

For an enhancement, record added, changed and preserved UI IDs against the existing baseline in the current Epic or direct task. Compare preserved Wireframe screen objects and flows, and HiFi product DOM, styles and behavior before approval. Explain every shared-component consumer that changes. Full package validation checks coverage; it does not authorize regenerating unaffected product pages. Reviewer-only shell or manifest updates must leave those product surfaces intact.

New or renewed Visual Approval requires the reviewer shell on every `ui-hifi/2` page. Version 3 is the current shell. Historical version-2 schema-2 bundles remain inspection-readable; missing new review evidence cannot obtain a fresh approval. Keep the closed manifest unchanged: reviewer views are DOM panels, not product surfaces or extra manifest pages.

The exact shared neutral reviewer stylesheet is `skills/ui-design-builder/assets/templates/REVIEWER_SHARED.css`. Both canonical templates embed the same bytes behind `<!-- hifi-reviewer:css:start -->`; the shell helper rejects drift. It fixes reviewer sidebar width, CJK-capable type, surface, focus and main offset without styling product classes. At runtime, the HiFi shell mounts in its own Shadow DOM and the Overview/Design Tokens panels mount in a separate Shadow DOM. The `reviewer-stage` hosts the product canvas in light DOM so product styles and interactions remain intact. The schema-5 Wireframe shell also uses Shadow DOM. Product colors, fonts, layout and JS remain in product source CSS.

- Each source page has one `aside[data-hifi-reviewer-shell][data-hifi-reviewer-version="3"]` with `data-hifi-platform` equal to that page's manifest platform group (or `shared`). It contains one `nav[data-hifi-page-nav]`, with exactly one link per manifest page including `index.html`; its own link has `aria-current="page"`. When a manifest row supplies `platformGroup: App|Web|Admin`, the sidebar renders that exact label as a group heading; assembly never invents a label. The shell also has links `data-hifi-review-view="overview"` and `data-hifi-review-view="design-tokens"` to `index.html#overview` and `index.html#design-tokens`, plus one `fieldset[data-hifi-responsive-controls]` of real `button[data-hifi-target-control]` controls in that page's manifest target order. Exactly one target button has `aria-pressed="true"`.
- Each page wraps its one assigned product surface as the direct child of one `[data-hifi-canvas]`. The canvas declares all targets applicable to that page in `data-hifi-targets`, selects one in `data-hifi-target`, uses `container-type: inline-size`, and has an exact `width:<target>px` rule for every target. Named native or size-class targets also declare `data-hifi-target-widths` as an exact finite positive JSON target-to-pixel map. Product reflow uses `@container`; preference and print media rules may remain, but host viewport-dimension media queries (including comparison and colon forms) and `transform: scale` are not allowed. The reviewer shell is fixed and never occupies the product canvas's nominal width. Static checks verify these bindings, not visual quality.
- Entry panels use `data-hifi-panel="overview"` and `data-hifi-panel="design-tokens"`, initially `hidden`. The entry declares `data-hifi-default-surface` equal to the first manifest surface, which belongs to index.html. Initial load shows that product surface. Explicit panel links open the requested panel, update focus and preserve normal browser back navigation. Unknown hashes recover to the primary product page.
- Overview contains one `data-hifi-summary="UI-*"` row per manifest surface, in order, with `data-route`, space-separated `data-states` and `data-targets`. Show readable screen purpose, page contents and flow summaries there; individual pages prioritize the product preview. State coverage exists only in Overview as ordered `data-hifi-state-coverage="UI-* state"` elements. Applicable states are real anchors with `data-state-destination="state"` and an `href` to that surface's actual page; activation navigates to `#hifi-state=<encoded surface>/<encoded state>`. `n/a` states are explanatory non-links with a nonempty `data-state-reason` and no destination. A state label duplicated inside the product screen is not coverage.
- Design Tokens shows actual tokens, components, variants, states and patterns, including buttons, forms, feedback and recovery where used. Each `data-hifi-spec="token|component|pattern"` specimen binds `data-name`, `data-source-page` (manifest page), `data-source` (actual CSS selector), `data-property`, `data-variant` and `data-state`. Token specimens also require nonempty `data-token-purpose`. Every page has source-bound token, component and pattern specimens, and every actual product control variant/state bound to a source selector has a matching component specimen. Token properties cover all actual product CSS custom properties on each page; reserve `--review-*` for reviewer chrome. Derive displayed values from real product computed style and refresh specimens when the selected target or state changes. Do not maintain a second token-value table. Review all used variants/states and patterns; static category coverage alone does not prove completeness.
- A specimen wrapper also declares `data-specimen-element`, and that actual element descendant carries nonempty `data-hifi-specimen-content`. Component specimens use real styled elements for controls actually used on the source page (for example `button`, `input`, and `select`), not plain text or lookalike wrappers. Component and pattern specimens use the bound source class. `data-shared-group` may visually group identical specimens, but every member page still has its own measured row; repeated names require the same shared group.
- Keep shell, panels and specimen controls outside `data-ui-surface`, without product `data-control-id` or `data-navigation-id`. Sidebar transitions never satisfy product interactions. Product navigation, editable forms, validation, tabs, dialogs, feedback and recovery must work locally according to the PRD, with click and keyboard results. Demonstrate required failures and recovery; a screenshot or declared destination alone is insufficient.
- Product menus and tabs are declared on native `button` elements in product DOM. A menu button carries `data-product-menu`, `aria-controls`, and `aria-expanded`; a tab button carries `data-product-tab`, `aria-controls`, and `aria-selected`. Each `aria-controls` value must identify exactly one distinct panel strictly inside that button's own `data-ui-surface`. A reviewer panel, another product surface, the button itself, or a duplicate ID cannot serve as its panel. Controls and panels must be live DOM nodes outside `<template>` and `<noscript>`; an ordinary hidden product state panel is allowed. Runtime and receipts must cover click, Enter/Space, Arrow/Home/End where applicable, selected/expanded state, panel visibility, Escape and focus return. Menu-open state must survive width-only resize and review-canvas geometry changes. Reviewer links and panels never count as these product controls.
- Version-3 source pages have `fieldset[data-hifi-state-controls]` with one real button `data-hifi-state-control="<state>"` and `data-hifi-state-surface="UI-*"` for each applicable state on that page. Each product surface provides visible content variants marked `data-hifi-state-view="<state>"` and `data-responsive-target="<target>"` for its state/target matrix. The runtime toggles those variants and the pressed state of the controls; changing a button label or `data-state` alone does not prove the state rendered. Overview state links navigate to the matching child page and encoded state hash.
- Tokens remain candidate values until the conditional formal design-system pair is compiled. Native HTML remains a design projection. Preserve existing unaffected pages, IDs and approved decisions on small changes; reopen only affected approvals and update their evidence.

Group actual tokens into color, typography, dimensions/spacing, border/radius, shadow, gradient and motion (duration/easing) when used. Show color swatches, type samples, measured spacing and styled border/shadow examples beside their source-derived values; show motion with reduced-motion handling. Do not invent unused categories or confuse a component with a token: buttons and forms are component specimens consuming tokens. See the [DTCG glossary](https://www.designtokens.org/glossary/) for token types and [Carbon spacing](https://carbondesignsystem.com/elements/spacing/overview/) for intra-component and layout spacing examples.

For new observations, `ui-output/3` retains the applicable offline transcript and adds exactly one `reviewer` object. It contains exactly `defaultSurface`, `defaultVisible: true`, `overviewInitiallyHidden: true`, `overview`, `views`, `navigation`, `recovery`, `viewport`, `retention` and `specimens`. The `hifi_reviewer.py` contract derives the required matrix from current DOM and manifest bytes. `views` covers every originating page (`from`) × Overview/Design Tokens × that page's target × click/keyboard, with control visibility, product invisibility, no visible product surfaces, focus and PASS. Reviewer `navigation` covers every page-to-page sidebar link at each source target, records the destination's selected target (the source target when applicable, otherwise that page's first valid target), and has exactly one visible product surface. `overview` matches surface/route/state/target coverage. `viewport` records each page/surface/target with numeric `measuredProductWidth` equal to the requested target, `containerQueryApplied: true`, `hostMediaQueryApplied: false`, and the one visible surface. `retention` records target switches plus Overview and Design Tokens round trips for every surface/target, with the selected target before and after plus unchanged nonempty observed input and selected values when those controls apply; pages without an applicable control record `null` instead of a fabricated probe. These are browser measurements, not `data-*` labels.

Every specimen records its exact DOM identity including `sourcePage`, `sharedGroup`, real `element` and visible `marker`, plus nonempty equal `sourceValue`, `specimenValue` and `displayValue`, measured in the browser on that source page for that variant/state. Reusing the entry-page value for a child page is not evidence; compare the child measurement with the entry specimen and displayed value. All members of a shared group must have equal source/specimen/display triples; grouping never removes page coverage. Restore the default product view after review. Product `interactions` and their navigation transcript remain separate and mandatory.

The same closed `reviewer` object also requires `recovery`. For every page and target, record `unknown-hash`, `back-from-overview` and `back-from-design-tokens`; Back begins on that product page, opens the named reviewer view, then uses browser Back. Each row records `from`, `case`, `target`, the exact restored product `surfaces`, `productVisible: true`, `panelsHidden: true` and `result: PASS`. Finish at each target with `final-default-restoration` from `index.html`, recording its primary surface. Missing or failed recovery rows block renewed approval. These are browser observations, not inferred results from static markup.

Version-3 sidebar coverage is per-page integration plus representative transitions rather than every page-to-page combination: every page must exercise its integration route to the entry, the entry must exercise every destination, and adjacent pages form the representative chain. Product interactions, states, target families and wrong-destination recovery remain complete. Version-2 evidence semantics do not change. Reviewer target restoration is keyed by package and page/platform family; unknown stored selections recover to the first valid target for the current page.

Assemble with `scripts/assemble_ui_review.py` and its documented CLI flags. The assembler derives `packageId` from the manifest and resolved output location. The version-3 reviewer stores each target, surface or state selection under `hifi-reviewer:<selection>:<packageId>:<platform>:<page>`, so equal manifests in different output directories do not share state. It rejects input/output aliases, links or junctions, duplicate or stale child hashes, and an embedded entry manifest that differs from the supplied manifest. `--overwrite` remains an explicit replacement boundary; assembly never grants publication or human approval.

Record only observed results in `ui-output/3` and assemble `ui-evidence/3` as described in `review-evidence.md`. These machine records do not claim human attestation. Synthetic fixture rows test validators; they are never real browser, native, auth or service evidence. Retain the exact source hashes and renew evidence after changes. Static checks cannot prove actual visibility, aesthetics, selector validity or arbitrary JavaScript behavior; browser and semantic review must do so.

## Human Review Presentation

Before the consolidated Visual Approval, proactively send one user-visible response with verified absolute Markdown links to the complete actual HiFi candidate, its entrypoint and every manifest-listed sibling page, validated `wireframes.html`, and affected `ui-design.md` scope. Use final logical paths in the authorized publication checkout; after publication, link canonical source paths. Do not collect approval on `.ui-staging` paths. State the scope and review focus, including copy, structure, menus, tabs, other interactions, visuals and tokens. Tool-only output, a hidden panel, a screenshot, or a plain path cannot replace the links. Opening a viewer is convenience only. Missing or stale files/evidence block readiness. Wait for the owner's explicit decision; a changed candidate reopens the affected decision.

## Token specimen completeness

For tokens, the existing `sourceValue`, `specimenValue` and `displayValue` triple records the raw custom-property value. Also record `sourceComputedValue` and `specimenComputedValue`: nonempty, equal browser-computed values of `previewProperty`. Normalize the source token through a probe on its source page with the same element, inherited/root font, containing-block dimensions, constraints and responsive target as the specimen. Read the applied property on the actual specimen separately. Preserve both forms: `#243447` may render as `rgb(36, 52, 71)`, `1.5rem` as `24px`, and `normal` as `400`. Never compare raw token text directly with the applied property or substitute a second custom-property read for applied-value evidence. Shared groups must agree on both forms across pages. Component and pattern records keep their existing three value fields.

Every declared and used product token needs a named purpose, its source value and a visible specimen applying that value. Inventory the actual design across typography, color, spacing, dimensions, shape, borders, elevation and motion; add only categories the product uses. A complete list of CSS variables alone does not prove that reusable values were tokenized or that component states were designed. Inspect shared raw values and actual variants/states during authoring, then check source-to-specimen equality in the browser.

Each HiFi token specimen adds `data-token-preview` naming the CSS property that consumes its token in the source page, directly or through declared token aliases. Dimension and background/transition shorthands retain their normal CSS meaning. Supported properties are color, background-color, background-image (gradients only), font-family, font-size, font-weight, line-height, letter-spacing, width, height, gap, padding, border-radius, border-width, box-shadow, opacity, z-index, transition-duration and transition-timing-function. The canonical reviewer applies `var(--token)` to the real specimen element and displays its computed token value. Preserve each source page's actual styles in its scoped specimen; never substitute the entry page's value for a sibling's different value or fetch/import styles at runtime. Unsupported required categories need a bounded renderer extension and tests, not a fabricated sample. Motion previews are user-triggered and respect reduced motion. Browser observations bind `previewProperty` along with the existing token identity and must inspect the applied property, not just inherited custom-property text.

## `ui-design.md`

Use these exact headings:

```markdown
# UI Design Contract

## Source Product Definition

Product: [name]

PRD source: [repo-relative path @ sha256:<lowercase sha256>]

Architecture source: [repo-relative path @ sha256:<lowercase sha256>]

Stack source: [repo-relative path @ sha256:<lowercase sha256>]

Product Definition Approval: approved

Stack Decision Checkpoint: approved

## UI Design Intake

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Visual Preference Brief: [experience priority, guidance/control, density, layout, desired character, avoids, color/theme, typography/language, imagery/icons, references]

Direction mode: [one recommended direction / three comparable directions]

## Motion And Media Intent

Motion direction: [not_required / functional_only / expressive] — [owner or accepted recommendation]

| Intent ID | UI scope / region | Treatment | Purpose | Trigger | Draft prompt | Source | Static / reduced-motion fallback | Generation route | Status | Generation status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MM-001 | [UI-* / region] | [none / image / motion / image + motion] | [purpose] | [trigger] | [draft prompt] | [owner decision or source] | [fallback] | [none / existing asset / CSS-WAAPI / GSAP / native-framework / authorized provider] | [approved / deferred] | deferred |

## Wireframe Validation

Wireframe: [repo-relative path @ sha256:<lowercase sha256>]

Frozen PRD basis: [repo-relative path @ sha256:<lowercase sha256>]

Copy locale: [primary BCP 47 locale]

Structure validation: [draft / validated / blocked]

Responsive surface check: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

Wireframe references consulted: [sources and structural pattern adopted/rejected, or skip reason]

UI grading: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

Wireframe score: [0-100]

W5 score: [80-100 for Wireframe Validation]

Wireframe lowest dimension: [0-100]

Wireframe blocks: [none / named blocks]

### Frontend Design Usage

Frontend Design source: docs/design/<folder>/SKILL.md @ sha256:[observed source digest]

| Stage | Skill | Artifact | Application |
| --- | --- | --- | --- |
| wireframe | frontend-design @ sha256:[observed source digest] | docs/design/wireframes.html @ sha256:[candidate digest] | [hierarchy, composition and interaction methods actually used] |
| direction | frontend-design @ sha256:[observed source digest] | docs/design/directions/round/primary.png @ sha256:[capture digest] | [alternatives and concrete design choices] |
| hifi | frontend-design @ sha256:[observed source digest] | docs/design/ui-references/round/index.html @ sha256:[candidate digest] | [typography, palette, layout and self-review applied] |

## Style Integration

Design author: frontend-design

Selected direction: [VD-* ID, intent, confirmed REF-* / RP-* IDs]

Direction decision: [approved / selected / mixed-and-approved]

Direction decision owner: [human owner]

Direction decided on: [YYYY-MM-DD]

Candidate theme: [color, typography, spacing, shape, iconography, imagery, and motion rules used in the HiFi reference; not yet a frozen design-system pair]

Review medium: HTML projection only

Connected HiFi reference: [repo-relative path @ sha256:<lowercase sha256>]

### Direction comparison

| Direction | UI surface | State | Target | Scenario | Content basis | Screenshot | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VD-R1-01 | UI-001 | ready | 390 | primary | [frozen copy and representative data] | docs/design/directions/round-1/primary.png @ sha256:[hash] | [specific hierarchy and type decisions] |
| VD-R1-01 | UI-001 | ready | 1200 | stress | [bounded dense data from the same copy contract] | docs/design/directions/round-1/dense.png @ sha256:[hash] | [how density and alignment hold up] |

The active table contains exactly one or three direction IDs as selected in `Direction mode`. Each direction covers the same surface/state/target/scenario/content tuples with both `primary` and `stress` scenarios. Every tuple belongs to the approved surface scope; a stress scenario may use bounded dense content in an existing state. Cover every platform with its own cases. `Selected direction` starts with one of these exact `VD-R<round>-<number>` IDs. Screenshots are repository-relative PNG, JPEG, or WebP paths under `docs/design/directions/` with lowercase SHA-256 values; identical captures cannot stand for different directions. Record only inspected captures and retain the authorized files. The checker validates scope, matrix equality, paths, and hashes; visual distinction and content fidelity remain human review judgments. Before Visual Approval these records may remain draft, but no missing or stale comparison can pass final validation. Never backfill an old approval: missing evidence requires renewed affected direction and Visual Approval.

### Platform rules

| Platform | Navigation and input | Typography | Icons | Density and layout | Feedback and motion | Native proof | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| web | [navigation, keyboard, focus, hover] | [roles, loading, CJK fallback] | [selected family and fallback] | [task density and responsive layout] | [approved functional feedback] | not_applicable | [official URLs and inspection dates] |
| ios | [native navigation, back, sheets, keyboard] | [system text styles and Dynamic Type reasoning] | [SF Symbols or reasoned alternative] | [safe areas and touch density] | [system feedback and reduced motion] | required before expansion | [official URLs, inspection dates, OS range] |

Include exactly the platforms present in Approved target `stackSemantics.platform`; omit example rows that do not apply. Every column contains a concrete rule or scoped reason. The iOS typography and icon columns explicitly address system text styles, Dynamic Type, and SF Symbols without requiring custom brands to abandon their chosen fonts or symbols. Web libraries are not default native foundations. Other native/desktop rows also use `required before expansion`. `Review medium` must remain the exact HTML projection value; actual platform proof belongs to the first approved implementation slice and final Harness evidence. Validators check declared coverage and required topics, not platform usability or the quality of the rationale.

Each connected HiFi page must pass the generic self-contained surface check: no active external resources, network or executable APIs, remote forms, base/meta refresh navigation, CSS imports, or external scripts. Each schema-2 page contains exactly one CSP meta, first in its head, with this exact policy (the parser is deterministic and does not claim to prove arbitrary JavaScript safe):

`default-src 'none'; base-uri 'none'; connect-src 'none'; form-action 'none'; frame-src 'none'; object-src 'none'; navigate-to 'self'; img-src data:; media-src data:; font-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'`

The CSP denies remote media, forms, frames, objects, base navigation, and connections while allowing inline CSS/script and embedded image/font/media. The browser must separately enforce the exact local-page allowlist; same-origin CSP alone is insufficient. This check does not apply the wireframe schema or canonical reviewer shell. Legacy `ui-hifi/1` single-file references remain inspection-only with the prior `navigate-to 'none'` policy and `ui-output/1`. Every current Visual Approval, compiler preflight, and Harness visual join requires schema 2, even when the legacy bytes are unchanged. No caller-supplied age or version field grants an exception.

The entry contains exactly one `<script id="ui-hifi-manifest" type="application/json">` with `schema: "ui-hifi/2"` and exactly `surfaces`, `pages`, and `interactions`. Child pages contain no manifest. `pages` lists `{ "path": "details.html", "sha256": "<64 lowercase hex>" }` rows for every child; the entry is implicitly `index.html` and is hashed by the existing Approved target field. Filenames are unique ignoring case and match `[A-Za-z0-9][A-Za-z0-9_-]*.html`; no directories, URL schemes, query strings, escapes, symlinks, or reparse points. Each page embeds all non-HTML resources. Changing any child invalidates the entry's approved package identity.

Inside `## Style Integration`, every `motion` or `image + motion` intent also has exactly one row in:

### Required motion evidence

| Intent ID | UI scope / region | Trigger observed | End state observed | Normal-motion evidence | Reduced-motion evidence | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| MM-001 | UI-001 / hero | Entry transition visible and interruptible | Data-flow overlay ends in the approved resting state | PASS — evidence=docs/evidence/motion-normal.json @ sha256:[hash] | PASS — evidence=docs/evidence/motion-reduced.json @ sha256:[hash] | PASS |

The rows exactly cover motion intents, including a deferred intent that remains in scope. Both evidence cells use `ui-evidence/3` observation receipts for the current HiFi projection. Old contracts remain inspectable without approval flags; every new Visual Approval requires these records. The frozen wireframe generation status stays deferred; completed assets and their exact authorization/output/review are recorded here instead of rewriting that history. A missing required generated asset blocks approval. Native implementation evidence remains a later obligation.

Each surface has exactly `id`, `page`, `route`, `states`, `responsive`, `navigation`, and `controls`. `page` names the entry or a listed child; the other fields keep the schema-1 surface/DOM contract. Every page renders exactly its assigned product surfaces, with one container per surface across the package, and the complete surface set equals the approved scope. Navigation/control IDs bind actual interactive elements inside that surface using `data-navigation-id` or `data-control-id`; a reviewer sidebar outside product surfaces is not interaction evidence.

Each interaction has exactly `id`, `source`, `control`, `kind`, and `destination`. Both endpoints are `{ "surface": "UI-001", "state": "ready" }` and must exist in the approved scope. IDs are unique. `kind: "navigate"` binds a real anchor whose `href` exactly equals the destination surface's page filename; `kind: "state"` changes to a different declared state on the same page, including feedback and overlays. Every page is reachable from index.html through product navigation. Every declared and rendered product control has an interaction. Derive these transitions from the approved PRD and wireframe actions; discrepancies return upstream, rather than inventing a new journey. Keep review-sidebar links to every page for capture setup, but verify product journeys through their own controls.

Current schema-2 HiFi surface checks require `ui-output/3`. Historical checks retain their original `ui-output/2` meaning. It retains all existing offline output fields and adds `interactions`. The sandbox field describes browser restrictions, not a Docker/Podman requirement. Its exact sandbox is `{ "network":"disabled", "topNavigation":"allowlisted-local-pages", "popups":"blocked", "forms":"blocked" }`. Each interaction runs at every source responsive target with both `trigger: "click"` and `trigger: "keyboard"`. Each output row contains exactly `id`, `target` (string), `trigger`, `source`, `destination`, `control`, `visible: true`, `focusCorrect: true`, and `result: "PASS"`; endpoints and control match the manifest. `navigation` records exactly one `{ "id", "target", "trigger", "from", "to" }` event per navigate case, with sibling page filenames. Missing, duplicate, or extra results/events fail. Retain blocked attempts too; never remove them to make the receipt pass. Non-document network requests, console errors, popups, and forms still fail. The browser setup and real click/key procedure are in `ui-design-pass.md`.

## HiFi Review

Impeccable critique: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

Impeccable audit: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

UI grading: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

HiFi surface check: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

HiFi score: [0-100]

H2 score: [0-100]

H4 score: [0-100]

H5 score: [80-100 for Visual Approval]

H7 score: [80-100 for Visual Approval]

H8 score: [0-100]

H9 score: [80-100 for Visual Approval]

HiFi lowest dimension: [0-100]

HiFi blocks or disputes: [none / named blocks or disputes]

For retained historical approvals only, each PASS evidence file is a `ui-evidence/2` human-attested JSON receipt with exactly `schema`, `check`, `result`, `reviewedArtifact`, `receipt`, `attestation`, and `owner`. `check` is platform-specific (for example `wireframe-browser`, `wireframe-browser-grading`, `wireframe-extension`, `wireframe-native`, `wireframe-desktop`, and corresponding HiFi checks); `reviewedArtifact` carries the exact current path and SHA-256; `receipt.matrix` is `{ "cases": [{"surface":"UI-*","state":"...","target":"..."}] }` derived per surface state × responsive target, `receipt.results` repeats those exact cases with `result: PASS`, and `receipt` carries a closed tool/method, a transcript/output artifact path+hash, and a past timezone-aware `executedAt`; `owner` names a human. Every `hifi-*` surface check uses method `sandboxed-offline-browser` with its platform tool. For legacy schema-1 HiFi, its retained `ui-output/1` output artifact additionally contains the exact `sandbox` object `{ "network":"disabled", "topNavigation":"blocked", "popups":"blocked", "forms":"blocked" }`, `console`, `network`, `navigation`, `popups`, and `forms` transcript arrays plus `popupAttempts` and `formAttempts` integer counts; any console error, request, navigation, popup, or form attempt fails. Legacy targets block all top navigation; schema-2 targets use the exact local-page allowlist and `ui-output/2` interaction contract above. The receipt is an attestation record, not an automatic approval—human Visual Approval remains required.

For new work, agents may assemble `ui-evidence/3` from actual observations, but must not invent a human owner, attestation or Visual Approval. Historical `ui-evidence/2` attestation remains the actual owner's record and cannot be relabeled.

Current grading, critique and audit assessments bind each matrix case to its own hashed screenshot, DOM or native capture, separate from the reviewed subject and execution input source files. A source hash or synthetic case label alone is not inspected capture evidence. See `review-evidence.md` for allowed capture formats and the limits of hash proof.

### Typed motion transcript

For each required motion intent, retain separate normal and reduced-motion `ui-evidence/3` receipts with `check: motion-preview`. These use `playwright` or `chrome-devtools` and `sandboxed-offline-browser` for every platform: the reviewed artifact is the current connected HiFi projection, never native execution. The receipt/output matrix uses the intent surface, each responsive target, and evidence-mode state `normal` or `reduced-motion`. These mode labels are not product states.

The retained `ui-output/3` includes all applicable offline transcript fields plus exactly one `motion` object with `intent`, exact `scope` (`UI-* / region`), `mode` (`normal` or `reduced`), boolean `reducedMotion`, `observations`, and `asset`. Record the actual browser preference. Each observation has exactly `target`, an approved product `state`, observed `trigger`, observed `endState`, `samples`, and boolean `fallbackObserved`. Cover each target once. The evidence-table trigger and each observation `trigger` must repeat the approved Motion And Media Intent trigger exactly. Normal `endState` must match the Required motion evidence row; reduced `endState` must match the approved intent fallback. Bind observations to the named region in the inspected artifact; a relabeled generic page transcript is insufficient.

Each sample is `{ "atMs": 0, "values": { "opacity": "0" } }`. Use strictly increasing finite nonnegative times and the same nonempty observed property keys. Normal motion needs before/during/after samples with an actual change; reduced motion needs at least two samples and `fallbackObserved: true`. Human inspection confirms the declared trigger, region, end state and fallback. These attestations cannot be manufactured by an agent.

Use `asset: null` only for code-only motion. Every `image + motion` treatment requires an asset even when CSS or GSAP animates it. Generated or reused media requires `asset` with exactly `path`, `sha256`, structured `authorization`, and `review: approved`; the retained file must match that hash. Authorization has exactly `decision: approved`, human `owner`, observed `provider`, `action` (`generate` or `reuse`), and the same asset `path` and `sha256`. The `existing asset` route requires `action: reuse` and records the actual asset library or source as `provider`; the route label is not a provider. The template phrase `authorized provider` is unresolved and cannot pass publication; name the observed provider. For a media-provider generation route, `provider` must match that approved route (case-insensitive); code-only motion routes may accompany separately authorized reused/generated imagery. This is a record of the separately authorized provider action and reviewed output, not a grant to invoke a provider or mint an approval; pending or denied prose cannot substitute for it. A pending asset does not complete an effect. All required motion intents must have status `approved` before Visual Approval; the separate wireframe `generationStatus: deferred` remains immutable. Actual iOS/Android behavior still requires platform evidence in the implementation gates.

## Visual Approval

Decision: [approved / revision_requested / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Approved target: [repo-relative path @ sha256:<lowercase sha256>; scope=surfaces=[{"id":"UI-001","route":"/path","states":["ready"]}]|routes=["/path"]|states=["ready"]|responsive={"kind":"viewports","targets":[390,768,1200]}|tolerance="exact"|allowedDeviations=[]|captureMode=hosted-browser]

For a hybrid target, each surface object additionally records `releaseSurface`, `surfaceClass`, `captureMode`, and its own `responsive` object. Use `captureMode=mixed` only together with complete per-surface fields; a global mode or responsive set never substitutes for a surface's platform contract.

## Design System Need Gate

Decision: [required / not_required / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Reason: [product-specific reason]

Existing design-system pair disposition: [none|retain|retire — reason; owner=<human>; decided=<YYYY-MM-DD>]

Replacement visual contract when not_required: target=[path @ sha256:hash]; ui-design=[path @ sha256:canonical-ui-approval-digest]; wireframe=[path @ sha256:hash]; prd=[path @ sha256:hash]

Compiled design system pair: [markdown path @ sha256:<lowercase sha256> and json path @ sha256:<lowercase sha256>]

Use `Compiled design system pair` only for `required` and the replacement field only for `not_required`. A new required pair may temporarily use the exact value `pending — design-system-compiler` only during the compiler preflight; normal publication rejects it. For `not_required`, the disposition is machine-bound: `none` forbids canonical pair files, `retain` requires both pair files, and `retire` requires the pair to be archived before publication. `blocked` cannot pass publication.
```

Impeccable's heuristic scores and audit scores are diagnostic. Only the `W1`–`W5` and `H1`–`H9` rows use the thresholds in `ui-grading-rubric.md` to decide readiness.
