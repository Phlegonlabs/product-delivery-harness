# UI Design Output Contract

## UI Contract Compatibility

A wireframe-free package starts `ui-design.md` with exactly one top-level marker immediately below `# UI Design Contract`: `UI contract: ui-design/3` for new initial or full-redesign work, `UI contract: ui-design/2` for a retained package. Neither needs wireframe authoring, `Wireframe Validation`, or a wireframe binding in its required design system.

The value is closed. A missing marker keeps the file's legacy checks and historical wireframe meaning. More than one marker, an unknown value, or a mixed current/legacy claim fails. Never add the marker to an old package afterward.

`ui-design/3` keeps the ui-design/2 rules, including the default `Direction mode: three comparable directions` and the explicit owner single-direction option, and adds a `### Direction studies` table, an `Intermediate width check`, and a Need Gate that is always `required` with a closed `Package action`. Existing `ui-design/2` packages, their `not_required` decisions and `design-system/3` pairs keep their meaning. Headless products have no UI package; accepted `none`/`style` maintenance keeps its retained design sources.

`ui-hifi/2` remains the current closed HiFi package: entry, hashed sibling pages, and every non-HTML asset inline. It has no external asset-folder registry. `ui-design/3` compiles `design-system/4`; `ui-design/2` compiles `design-system/3`; legacy `design-system/2` remains readable under its original checks.

## Canonical Artifacts

- `docs/design/ui-design.md`: UI decisions, sources, gates, scores, and handoff.
- `docs/design/ui-references/<run-id>/index.html` and its manifest-listed sibling HTML pages: the approved connected HiFi design-reference package when retention is authorized.
- `docs/design/design-system.md` and `docs/design/design-system.json`: present together only when the Design System Need Gate is `required`.

Historical `wireframes/2` through `wireframes/5` remain readable for inspection, legacy validation and approved-history checks; their bytes never become a current PRD-to-direction approval. New `ui-design/2` authoring creates no wireframe artifact. After formal compilation, `docs/design/design-system-preview.html` is a derived view checked against the current pair and sources, not a third editable authority.

Legacy `docs/product/wireframes.html` and `docs/product/design-system.*` remain readable. New or revised artifacts publish under `docs/design/`; do not move an existing legacy artifact without exact owner authorization.

## Translation And Freshness Handoff

Keep the `design-translation.md` table and current source/candidate freshness observations in this handoff or linked task evidence, with the incremental or explicit full rebuild scope, fixed/provisional decisions, selected recipe/version, language and iPhone scope, representative stress cases and animation boundaries. No approval gate or product authority is created. Inspector metadata and bilingual/motion examples are not shipping copy unless the PRD's sourced copy contract includes them.

## Reviewer Navigation And Design Specifications

For an enhancement, record added, changed and preserved UI IDs against the existing baseline in the current Epic or direct task, and explain every changed shared-component consumer. A current package compares HiFi product DOM, styles and behavior against the approved PRD joins and prior approved target; a package with an approved wireframe also compares its preserved screen objects and flows under the legacy rules. Full validation checks coverage but does not authorize regenerating unaffected pages.

New or renewed Visual Approval requires the version-3 reviewer shell on every `ui-hifi/2` page. Historical version-2 schema-2 bundles stay inspection-readable but cannot gain a fresh approval without the new review evidence. Reviewer views are DOM panels, not product surfaces or manifest pages; the closed manifest is unchanged.

The shared neutral reviewer stylesheet is `skills/ui-design-builder/assets/templates/REVIEWER_SHARED.css`. Both canonical templates embed the same bytes behind `<!-- hifi-reviewer:css:start -->`; the shell helper rejects drift. It styles no product classes.

- Each source page has one `aside[data-hifi-reviewer-shell][data-hifi-reviewer-version="3"]` with `data-hifi-platform` equal to the page's manifest platform group (or `shared`). It contains one `nav[data-hifi-page-nav]` with exactly one link per manifest page including `index.html`, its own link carrying `aria-current="page"`. A manifest row's `platformGroup: App|Web|Admin` renders as that exact group heading; assembly never invents one. The shell also has links `data-hifi-review-view="overview"` and `data-hifi-review-view="design-tokens"` to `index.html#overview` and `index.html#design-tokens`, plus one `fieldset[data-hifi-responsive-controls]` of real `button[data-hifi-target-control]` controls in the page's manifest target order, exactly one with `aria-pressed="true"`.
- Each page wraps its one assigned product surface as the direct child of one `[data-hifi-canvas]`, which declares all the page's applicable targets in `data-hifi-targets`, selects one in `data-hifi-target`, uses `container-type: inline-size`, and has an exact `width:<target>px` rule per target. Named native or size-class targets also declare `data-hifi-target-widths` as an exact finite positive JSON target-to-pixel map. Product reflow uses `@container`; preference and print media rules may remain, but host viewport-dimension media queries (including comparison and colon forms) and `transform: scale` are not allowed. The fixed reviewer shell never occupies the canvas's nominal width.
- Entry panels use `data-hifi-panel="overview"` and `data-hifi-panel="design-tokens"`, initially `hidden`. The entry declares `data-hifi-default-surface` equal to the first manifest surface, which belongs to index.html, and initial load shows that surface. Explicit panel links open the requested panel, update focus and preserve browser back navigation. Unknown hashes recover to the primary product page.
- Overview contains one `data-hifi-summary="UI-*"` row per manifest surface, in order, with `data-route` and space-separated `data-states` and `data-targets`, plus readable screen purpose, page contents and flow summaries (pages prioritize the product preview). Order manifest surfaces by the confirmed journeys: a journey's screens sit together in journey order, a shared screen sits at its first journey, and its flow summary names the journeys it serves. State coverage exists only in Overview, as ordered `data-hifi-state-coverage="UI-* state"` elements: applicable states are real anchors with `data-state-destination="state"` and an `href` to that surface's page, navigating to `#hifi-state=<encoded surface>/<encoded state>`; `n/a` states are non-links with a nonempty `data-state-reason` and no destination. A state label inside the product screen is not coverage.
- Design Tokens shows actual tokens, components, variants, states and patterns, including buttons, forms, feedback and recovery where used. Each `data-hifi-spec="token|component|pattern"` specimen binds `data-name`, `data-source-page` (manifest page), `data-source` (actual CSS selector), `data-property`, `data-variant` and `data-state`; token specimens also require nonempty `data-token-purpose`. Every page has source-bound token, component and pattern specimens, and every actual product control variant/state bound to a source selector has a component specimen. Token properties cover all actual product CSS custom properties on each page; reserve `--review-*` for reviewer chrome. Derive displayed values from real product computed style, refresh specimens when the selected target or state changes, and keep no second token-value table.
- A specimen wrapper also declares `data-specimen-element`, and that element descendant carries nonempty `data-hifi-specimen-content`. Component specimens use real styled elements for controls used on the source page (for example `button`, `input`, `select`), not plain text or lookalike wrappers; component and pattern specimens use the bound source class. `data-shared-group` may visually group identical specimens, but every member page keeps its own measured row; repeated names require the same shared group.
- Keep shell, panels and specimen controls outside `data-ui-surface`, without product `data-control-id` or `data-navigation-id`; sidebar transitions never satisfy product interactions. Product navigation, editable forms, validation, tabs, dialogs, feedback and recovery work locally per the PRD, with click and keyboard results, and required failures and recovery are demonstrated; a screenshot or declared destination alone is insufficient.
- Product menus and tabs are declared on native `button` elements in product DOM. A menu button carries `data-product-menu`, `aria-controls`, and `aria-expanded`; a tab button carries `data-product-tab`, `aria-controls`, and `aria-selected`. Each `aria-controls` value identifies exactly one distinct panel strictly inside that button's own `data-ui-surface`; a reviewer panel, another product surface, the button itself, or a duplicate ID cannot serve. Controls and panels are live DOM nodes outside `<template>` and `<noscript>`; an ordinary hidden product state panel is allowed. Runtime and receipts cover click, Enter/Space, Arrow/Home/End where applicable, selected/expanded state, panel visibility, Escape and focus return. Menu-open state survives width-only resize and review-canvas geometry changes.
- Version-3 source pages have `fieldset[data-hifi-state-controls]` with one real button `data-hifi-state-control="<state>"` and `data-hifi-state-surface="UI-*"` for each applicable state on that page. Each product surface provides visible content variants marked `data-hifi-state-view="<state>"` and `data-responsive-target="<target>"` for its state/target matrix. The runtime toggles those variants and the controls' pressed state; a changed button label or `data-state` alone does not prove the state rendered.
- Tokens remain candidate values until the conditional formal design-system pair is compiled; native HTML remains a design projection. On small changes preserve unaffected pages, IDs and approved decisions; reopen only affected approvals and update their evidence.

Group actual tokens into color, typography, dimensions/spacing, border/radius, shadow, gradient and motion (duration/easing) when used. Show color swatches, type samples, measured spacing and styled border/shadow examples beside their source-derived values; show motion with reduced-motion handling. Buttons and forms are component specimens consuming tokens, not tokens. See the [DTCG glossary](https://www.designtokens.org/glossary/) for token types and [Carbon spacing](https://carbondesignsystem.com/elements/spacing/overview/) for intra-component and layout spacing examples.

For new observations, `ui-output/3` retains the applicable offline transcript and adds exactly one `reviewer` object containing exactly `defaultSurface`, `defaultVisible: true`, `overviewInitiallyHidden: true`, `overview`, `viewport` and `specimens`; `hifi_reviewer.py` derives the required rows from current DOM and manifest bytes. `overview` matches surface/route/state/target coverage. `viewport` records each page/surface/target with numeric `measuredProductWidth` equal to the requested target, `containerQueryApplied: true`, `hostMediaQueryApplied: false`, and the one visible surface, all as browser measurements, not `data-*` labels. A product receipt does not repeat sidebar views, page navigation, recovery or retention (the shared shell's browser tests prove them); the checker accepts and ignores `views`, `navigation`, `recovery` and `retention` rows from earlier runs.

Every specimen records its exact DOM identity including `sourcePage`, `sharedGroup`, real `element` and visible `marker`, plus nonempty equal `sourceValue`, `specimenValue` and `displayValue`, measured in the browser on that source page for that variant/state. Reusing the entry-page value for a child page is not evidence; compare the child measurement with the entry specimen and displayed value. All members of a shared group have equal triples; grouping never removes page coverage. Restore the default product view after review.

Assemble with `scripts/assemble_ui_review.py` and its documented CLI flags. The assembler derives `packageId` from the manifest and resolved output location; the version-3 reviewer stores each selection under `hifi-reviewer:<selection>:<packageId>:<platform>:<page>`, so equal manifests in different output directories do not share state, and an unknown stored selection recovers to the first valid target for the current page. `--overwrite` remains an explicit replacement boundary; assembly never grants publication or human approval.

Record only observed results in `ui-output/3` and assemble `ui-evidence/3` as described in `review-evidence.md`; synthetic fixture rows test validators but are never real browser, native, auth or service evidence. Retain the exact source hashes and renew evidence after changes. Browser and semantic review, not static checks, prove visibility, aesthetics, selector validity and arbitrary JavaScript behavior.

### Render fingerprint carry-forward

A case's `render fingerprint` is the lowercase SHA-256 over two browser measurements of that surface × state × target: the DOM geometry probe output (product-surface element rects, scroll versus client size, horizontal overflow), a computed-style digest of the product surface, and the identity of every rendered media input (image sources and srcsets, video posters, SVG fill and stroke, CSS background, mask and border images). A probe that could not cover every element records the fingerprint as incomplete, and an incomplete fingerprint never carries.

After a repair, observe again every case whose fingerprint differs from the one recorded under the last PASS receipt. A case with an equal fingerprint may carry forward into the new receipt with its original capture and verdict, whatever its page bytes. The receipt records each carried row's source receipt, source page SHA-256 and fingerprint; the defect ledger names each carried row's source receipt and page SHA-256.

A fingerprint shows a case renders as it did when judged. It cannot prove text readability, colour or a layer's usability, so first-wave judgment of those still happens once, on the original capture.

## Human Review Presentation

Before the consolidated Visual Approval, follow `stages/ui-design.md#workflow` step 8: link the complete HiFi candidate and affected `ui-design.md` scope at final repository paths on the task branch, never `.ui-staging` paths. Tool-only output, a hidden panel, a screenshot, or a plain path cannot replace the links; a changed candidate reopens the affected decision.

## Token specimen completeness

For tokens, the `sourceValue`, `specimenValue` and `displayValue` triple records the raw custom-property value. Also record `sourceComputedValue` and `specimenComputedValue`: nonempty, equal browser-computed values of `previewProperty`. Normalize the source token through a probe on its source page with the same element, inherited/root font, containing-block dimensions, constraints and responsive target as the specimen, and read the applied property on the actual specimen separately. Preserve both forms: `#243447` may render as `rgb(36, 52, 71)`, `1.5rem` as `24px`, and `normal` as `400`. Never compare raw token text with the applied property or substitute a second custom-property read for applied-value evidence. Shared groups agree on both forms across pages. Component and pattern records keep the three value fields.

Every declared and used product token needs a named purpose, its source value and a visible specimen applying that value. A list of CSS variables alone does not prove reusable values were tokenized or component states designed.

Each HiFi token specimen adds `data-token-preview` naming the CSS property that consumes its token in the source page, directly or through declared token aliases. Dimension and background/transition shorthands retain their normal CSS meaning. Supported properties are color, background-color, background-image (gradients only), font-family, font-size, font-weight, line-height, letter-spacing, width, height, gap, padding, border-radius, border-width, box-shadow, opacity, z-index, transition-duration and transition-timing-function. The canonical reviewer applies `var(--token)` to the real specimen element and displays its computed token value. Preserve each source page's actual styles in its scoped specimen; never fetch/import styles at runtime. Unsupported required categories need a bounded renderer extension and tests, not a fabricated sample. Motion previews are user-triggered and respect reduced motion. Browser observations bind `previewProperty` along with the existing token identity.

## `ui-design.md`

Use these exact headings and this marker for a current `ui-design.md`:

```markdown
# UI Design Contract

UI contract: ui-design/2

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

`three comparable directions` is the default for `ui-design/3` and `ui-design/2`. `one recommended direction` requires a separate explicit owner instruction, recorded by this intake's human `Decision owner` and `Decided on`; continuing intake uncertainty or silence does not supply it. Enhancement scope with an existing accepted direction keeps the package's contract and records that retained direction (for `ui-design/3`, the approved round's studies and selection) instead of restarting selection.

### Design Brief

Extend the Visual Preference Brief here for new or changed design scope. Existing historical artifacts stay valid, with no backfill or separate approval.

- Purpose and scope: [link the approved PRD page, audience, primary job and non-goals; do not duplicate product requirements]
- Page-purpose mapping: [affected UI IDs by page purpose/profile, with the constraints that bind them, typography/headline, density, motion intent, justified exceptions, and the choices left to the design author; existing accepted decisions may be linked. Point to the PRD UI Surface Contract instead of repeating its per-page requirements.]
- Reference response: [owner answer and source/date; supplied / explicitly none / not supplied; name any unavailable material separately]
- Reference lessons: [source URL/file/product and relevant page/region; useful composition/typography/motion role, what to learn, what to avoid and affected UI IDs; an avoid example needs a concrete reason; link inspected REF-* and proposed/confirmed RP-* records]
- Visual constraints and avoid rules: [concrete layout/spacing, typography/language (chosen font pairing, avoided default faces and why), color/theme, imagery/icon and motion constraints; distinguish owner decisions, agent proposals and unresolved items]
- Detailed decisions: [link Style Integration/selected VD-* and applicable MM-* records as they become available; identify concrete visual features from the selected study and their capture/region, plus the existing font/asset sources; link the confirmed journey set and `journeys.html` @ sha256; do not create another token table or motion specification]

Populate this brief as decisions mature. It does not require a final palette before direction studies, turn a proposal into approval, or make an unavailable source visual evidence.

## Motion And Media Intent

Motion direction: [not_required / functional_only / expressive] — [owner or accepted recommendation]

| Intent ID | UI scope / region | Treatment | Purpose | Trigger | Draft prompt | Source | Static / reduced-motion fallback | Generation route | Status | Generation status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MM-001 | [UI-* / region] | [none / image / motion / image + motion] | [purpose] | [trigger] | [draft prompt] | [owner decision or source] | [fallback] | [none / existing asset / CSS-WAAPI / Motion / GSAP / Three.js / native-framework / authorized provider] | [approved / deferred] | deferred |

### Frontend Design Usage

Frontend Design source: docs/design/<folder>/SKILL.md @ sha256:[observed source digest]

| Stage | Skill | Artifact | Application |
| --- | --- | --- | --- |
| direction | frontend-design @ sha256:[observed source digest] | docs/design/directions/round/primary.png @ sha256:[capture digest] | [alternatives and concrete design choices] |
| hifi | frontend-design @ sha256:[observed source digest] | docs/design/ui-references/round/index.html @ sha256:[candidate digest] | [typography, palette, layout and self-review applied] |

Historical packages may retain a `wireframe` row and `## Wireframe Validation` under their legacy headings. A `ui-design/2` package does not add either.

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

The active table contains exactly one or three direction IDs as selected in `Direction mode`; each covers both `primary` and `stress` scenarios, compared like for like. Every tuple belongs to the approved surface scope; a stress scenario may use bounded dense content in an existing state. Cover every platform with its own cases. `Selected direction` starts with one of these exact `VD-R<round>-<number>` IDs. Screenshots are repository-relative PNG, JPEG, or WebP paths under `docs/design/directions/` with lowercase SHA-256 values; record only inspected captures and retain the authorized files. Visual distinction, Design Brief conformance and content fidelity remain human judgments. These records may stay draft before Visual Approval, but no missing or stale comparison passes final validation. Never backfill an old approval: missing evidence requires renewed affected direction and Visual Approval.

For `ui-design/3`, Style Integration adds:

```markdown
### Direction studies

| Direction | Study | Author | Self-check by | Self-check |
| --- | --- | --- | --- | --- |
| VD-R1-01 | docs/design/directions/round-1/vd-01.html @ sha256:[hash] | [frontend author identity] | [same identity] | pass |
```

Each compared direction has one distinct self-contained rendered HTML study with the HiFi CSP rules, all in one existing `docs/design/directions/<round>/` folder; the study rows match the compared directions exactly (three by default, one under the explicit owner choice). One frontend author produces and self-checks every study; a different checker, a failed self-check or a stale hash blocks. The owner may select, mix or modify (`Direction decision: mixed-and-approved` or `modified-and-approved`). A mix or modification adds one revised study of the selected direction to the same round folder under a new `VD-R<round>-<number>` ID. It replaces the selected direction's rows in both tables, and its rationale names the base direction and the requested changes. Assemble it alone with a one-direction profile; the other studies keep their bytes and rows, and the earlier study file stays retained. A rejection starts a new round with a complete set.

#### Direction Review Assembly

New studies use the shared reviewer through `scripts/assemble_ui_review.py --mode direction`; the default `--mode hifi` and its `ui-hifi/2` contract do not change. The frontend author writes one product page per direction.

```json
{
  "schema": "ui-direction-review/1",
  "round": "round-1",
  "directions": [{"id": "VD-R1-01", "file": "vd-01.html", "sourceSha256": "[author source hash]"}],
  "cases": [
    {"id": "primary", "surface": "UI-001", "platform": "web", "targetFamily": "viewports", "widths": {"390": 390, "1200": 1200}},
    {"id": "stress", "surface": "UI-004", "platform": "ios", "targetFamily": "sizeClasses", "widths": {"compact": 390, "regular": 820}}
  ]
}
```

- The profile is closed. `directions` lists three studies, or one under the explicit owner choice or for a revised study, each row naming the direction ID, study filename and author source SHA-256.
- Each case declares its own `surface`, `platform`, `targetFamily` and ordered `widths` map. A `viewports` target equals its integer pixel width; a `sizeClasses` target is a name with a finite positive pixel width.
- `web` cases use `viewports`; `ios` and `android` cases use `sizeClasses`. One profile may mix web and native cases.
- Each author source provides one `[data-hifi-canvas]` and one `[data-direction-case-view="<case id>"]` per case. It contains no reviewer chrome.
- Each source carries the local-page CSP: the HiFi policy with `navigate-to 'self'`. Its only file links are the profile's study filenames.
- Pass one `--source <file>=<path>` per study. No `index.html`, Overview, Design Tokens panel or state matrix is required before selection.

The confirmed journey map (`journeys.html`) uses the same tool as a one-direction profile: the selected direction's ID, `journeys.html` as its file, and one case per journey with its entry surface. It is not a compared direction, so it has no row in the Direction studies or Direction comparison tables; record it in the Design Brief.

The assembler keeps existing output unless `--overwrite` is given. Equal inputs produce equal bytes, so record each assembled study's hash in the Direction studies table.

The sidebar links studies by actual filename; a selected case shows only its approved targets at the mapped width and carries to the other studies.

`ui_design_v3.direction_review_findings` applies the strict profile to a study that embeds one (`has_direction_review_profile` detects it); earlier approved studies keep the existing study checks. A reviewer control never proves a product interaction, and a browser-rendered study is not native or real-login evidence.

A pre-selection study may include a bounded local motion demonstration, as [Intent Before Assets](motion-and-media-routing.md#intent-before-assets) allows. It is a selection aid only, never Required motion evidence, native proof, an approval, or permission to call a generation provider.

### Platform rules

| Platform | Navigation and input | Typography | Icons | Density and layout | Feedback and motion | Native proof | Sources |
| --- | --- | --- | --- | --- | --- | --- | --- |
| web | [navigation, keyboard, focus, hover] | [roles, loading, CJK fallback] | [selected family and fallback] | [task density and responsive layout] | [approved functional feedback] | not_applicable | [official URLs and inspection dates] |
| ios | [native navigation, back, sheets, keyboard] | [system text styles and Dynamic Type reasoning] | [SF Symbols or reasoned alternative] | [safe areas and touch density] | [system feedback and reduced motion] | required before expansion | [official URLs, inspection dates, OS range] |

Include exactly the platforms present in Approved target `stackSemantics.platform`; omit inapplicable example rows. Every column holds a concrete rule or scoped reason. The iOS typography and icon columns address system text styles, Dynamic Type and SF Symbols without forcing custom brands to abandon their fonts or symbols. Web libraries are not default native foundations. Other native/desktop rows also use `required before expansion`. `Review medium` stays the exact HTML projection value; platform proof belongs to the first approved implementation slice and final Harness evidence.

Each connected HiFi page must pass the generic self-contained surface check: no active external resources, network or executable APIs, remote forms, base/meta refresh navigation, CSS imports, or external scripts. Each schema-2 page contains exactly one CSP meta, first in its head, with this exact policy:

`default-src 'none'; base-uri 'none'; connect-src 'none'; form-action 'none'; frame-src 'none'; object-src 'none'; navigate-to 'self'; img-src data:; media-src data:; font-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'`

The browser must separately enforce the exact local-page allowlist; same-origin CSP alone is insufficient. This check does not apply the wireframe schema or canonical reviewer shell. Legacy `ui-hifi/1` single-file references remain inspection-only with the prior `navigate-to 'none'` policy and `ui-output/1`. Every current Visual Approval, compiler preflight and Harness visual join requires schema 2, even when the legacy bytes are unchanged; no caller-supplied age or version field grants an exception.

The entry contains exactly one `<script id="ui-hifi-manifest" type="application/json">` with `schema: "ui-hifi/2"` and exactly `surfaces`, `pages`, and `interactions`. Child pages contain no manifest. `pages` lists `{ "path": "details.html", "sha256": "<64 lowercase hex>" }` rows for every child; the entry is implicitly `index.html`, hashed by the Approved target field. Filenames are unique ignoring case and match `[A-Za-z0-9][A-Za-z0-9_-]*.html`, with no directories, URL schemes, query strings, escapes, symlinks, or reparse points. Each page embeds all non-HTML resources, and changing any child invalidates the entry's approved package identity.

The entry also contains exactly one `<script id="ui-hifi-copy" type="application/json">` for copy provenance, with schema `ui-hifi-copy/1` and closed top-level shape `{ "schema", "locale", "surfaces" }`. Each surface has exactly `{ "id", "copyStatus", "items" }`, each item exactly `{ "id", "copy" }`. `locale` is the primary BCP 47 locale. `copy` is the existing typed copy record, including static text or the dynamic display contract, never flattened into display-only text. `id` values are stable and unique within the copy record. The inventory is provenance only and adds no product scope.

Product DOM that carries inventoried copy declares both `data-copy-id` and `data-copy-locale`: the ID matches one copy-record item and the locale matches the rendered BCP 47 language. For paired languages, the corresponding visible or assistive variants carry the same copy ID with distinct locale values. Serialization, hash and completeness validation belong to the UI checker; do not relabel a reviewer note as copy provenance.

Every typed `copy` has `kind: static | dynamic`, a nonempty `role` and `source`, and `status: draft | approved`. Static copy supplies exact `text`. Dynamic copy supplies a representative `example` plus a `contract` with nonempty `source`, `order`, `format`, `count`, `length` and `fallback`. Optional `locale`, `direction: ltr | rtl | auto`, and one to three `parallel` copies preserve bilingual display; each names a distinct locale and the same role/kind, with no nested parallel list. Approved surface copy requires approved items. PRD responsibility and source truth still require semantic review.

Inside `## Style Integration`, every `motion` or `image + motion` intent also has exactly one row in:

### Required motion evidence

| Intent ID | UI scope / region | Trigger observed | End state observed | Normal-motion evidence | Reduced-motion evidence | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| MM-001 | UI-001 / hero | Entry transition visible and interruptible | Data-flow overlay ends in the approved resting state | PASS — evidence=docs/evidence/motion-normal.json @ sha256:[hash] | PASS — evidence=docs/evidence/motion-reduced.json @ sha256:[hash] | PASS |

The rows exactly cover motion intents, including a deferred intent that remains in scope. Both evidence cells use `ui-evidence/3` observation receipts for the current HiFi projection. Old contracts remain inspectable without approval flags; every new Visual Approval requires these records. The MM record's intent-time `deferred` generation status is not edited to claim completion; completed assets and their authorization, output and review are recorded here. A missing required generated asset blocks approval.

Each surface has exactly `id`, `page`, `route`, `states`, `responsive`, `navigation`, and `controls`. `page` names the entry or a listed child; the other fields keep the schema-1 surface/DOM contract. Every page renders exactly its assigned product surfaces, with one container per surface across the package, and the complete surface set equals the approved scope. Navigation/control IDs bind actual interactive elements inside that surface via `data-navigation-id` or `data-control-id`.

Each interaction has exactly `id`, `source`, `control`, `kind`, and `destination`. Both endpoints are `{ "surface": "UI-001", "state": "ready" }` and exist in the approved scope. IDs are unique. `kind: "navigate"` binds a real anchor whose `href` exactly equals the destination surface's page filename; `kind: "state"` changes to a different declared state on the same page, including feedback and overlays. Every page is reachable from index.html through product navigation, and every declared and rendered product control has an interaction. Derive transitions from the approved PRD UI Surface Contract and its operations; discrepancies return upstream rather than inventing a journey.

For `ui-design/2`, each interaction ID equals its PRD operation ID. Match its source surface/state, control and destination exactly; `presentation: page` maps to `kind: navigate`, other supported presentations to `kind: state`. Legacy packages keep their original operation join.

Current schema-2 HiFi surface checks require `ui-output/3`; historical checks keep their `ui-output/2` meaning. It retains all existing offline output fields and adds `interactions`. Its exact sandbox is `{ "network":"disabled", "topNavigation":"allowlisted-local-pages", "popups":"blocked", "forms":"blocked" }`. Each interaction runs at every source responsive target with both `trigger: "click"` and `trigger: "keyboard"`. Each output row contains exactly `id`, `target` (string), `trigger`, `source`, `destination`, `control`, `visible: true`, `focusCorrect: true`, and `result: "PASS"`; endpoints and control match the manifest. `navigation` records exactly one `{ "id", "target", "trigger", "from", "to" }` event per navigate case, with sibling page filenames. Missing, duplicate, or extra results/events fail. Retain blocked attempts; never remove them to pass. Non-document network requests, console errors, popups, and forms still fail.

A console row may keep native channel metadata. The only exempt row has `source: security` (or `params.entry.source`), `level: error` and the exact message `Unrecognized Content-Security-Policy directive 'navigate-to'.`; any other console error fails. The browser setup and real click/key procedure are in `ui-design-pass.md`.

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

`ui-design/3` also records `Intermediate width check: PASS — evidence=[path] @ sha256:[hash]`. The evidence is an ordinary `ui-evidence/3` receipt built by `scripts/review_evidence.py` from an actual `ui-output/3` observation of the Approved target, with the same check, tool/method, sandbox transcript, execution identities and current inputs as the `HiFi surface check`. Only its case matrix differs: each case names an approved web surface and state at a `target` width strictly between two adjacent approved viewports, and every adjacent pair of each web surface is covered. All results must be PASS; a hand-written summary or boolean record is not evidence. These observations add to, and never replace, the checks at every approved width.

When the validated Approved target has no adjacent web viewport widths, record exactly `Intermediate width check: not_applicable — no adjacent approved web viewport widths`. Native and desktop size classes have no web interval; in a mixed package inspect every per-surface target, since any web interval still requires the observed PASS receipt. Missing or invalid scope cannot claim this exception. Ordinary HiFi evidence and all approved size-class checks remain required.

For retained historical approvals only, each PASS evidence file is a `ui-evidence/2` human-attested JSON receipt with exactly `schema`, `check`, `result`, `reviewedArtifact`, `receipt`, `attestation`, and `owner`. `check` is platform-specific (for example `wireframe-browser`, `wireframe-browser-grading`, `wireframe-extension`, `wireframe-native`, `wireframe-desktop`, and corresponding HiFi checks); `reviewedArtifact` carries the exact current path and SHA-256; `receipt.matrix` is `{ "cases": [{"surface":"UI-*","state":"...","target":"..."}] }` derived per surface state × responsive target, `receipt.results` repeats those exact cases with `result: PASS`, and `receipt` carries a closed tool/method, a transcript/output artifact path+hash, and a past timezone-aware `executedAt`; `owner` names a human. Every `hifi-*` surface check uses method `sandboxed-offline-browser` with its platform tool. The receipt records attestation, not approval; human Visual Approval remains required.

For new work, agents may assemble `ui-evidence/3` from actual observations but never invent a human owner, attestation or Visual Approval. Historical `ui-evidence/2` attestation remains the owner's record and cannot be relabeled.

Current grading, critique and audit assessments bind each matrix case to its own hashed screenshot, DOM or native capture, separate from the reviewed subject and execution input source files; a source hash or synthetic case label alone is not capture evidence. See `review-evidence.md` for allowed capture formats and the limits of hash proof.

### Typed motion transcript

For each required motion intent, retain separate normal and reduced-motion `ui-evidence/3` receipts with `check: motion-preview`, using `playwright` or `chrome-devtools` and `sandboxed-offline-browser` for every platform; the reviewed artifact is the current connected HiFi projection, never native execution. The receipt/output matrix uses the intent surface, one representative responsive target, and evidence-mode state `normal` or `reduced-motion`, which are not product states. [Motion Evidence Per Intent](motion-and-media-routing.md#motion-evidence-per-intent) names that target and the frames and check each receipt holds.

The retained `ui-output/3` is an offline receipt of that one intent at its representative target, not the HiFi surface check: the offline transcript fields plus one `motion` object with `intent`, exact `scope` (`UI-* / region`), `mode` (`normal` or `reduced`) and `asset`, and no `interactions`, declared-navigation or `reviewer` object. Its sandbox is the fully blocked shape or the `allowlisted-local-pages` shape, and a `navigation` row (`from`, `to`) may only move between pages of the HiFi package; any other navigation, request, popup, form attempt or console error fails. The reviewer records what the browser showed for the declared trigger, region, end state and fallback in the inspected captures, and the evidence-table trigger repeats the approved Motion And Media Intent trigger exactly. The H6 block and human inspection, not the checker, grade the frames; an agent cannot manufacture those attestations.

Use `asset: null` only for code-only motion; every `image + motion` treatment requires an asset even when CSS or GSAP animates it. Generated or reused media requires `asset` with exactly `path`, `sha256`, structured `authorization`, and `review: approved`; the retained file must match that hash. Authorization has exactly `decision: approved`, human `owner`, observed `provider`, `action` (`generate` or `reuse`), and the same asset `path` and `sha256`. The `existing asset` route requires `action: reuse` and records the actual asset library or source as `provider`. The template phrase `authorized provider` is unresolved and cannot pass publication; name the observed provider. For a media-provider generation route, `provider` must match that approved route (case-insensitive); code-only motion routes may accompany separately authorized reused/generated imagery. This records the separately authorized provider action and reviewed output; it grants no provider invocation or approval, and pending or denied prose cannot substitute. A pending asset does not complete an effect, and every required motion intent needs status `approved` before Visual Approval.

## Visual Approval

Decision: [approved / revision_requested / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Approved target: [repo-relative path @ sha256:<lowercase sha256>; scope=surfaces=[{"id":"UI-001","route":"/path","states":["ready"]}]|routes=["/path"]|states=["ready"]|responsive={"kind":"viewports","targets":[390,768,1200]}|tolerance="exact"|allowedDeviations=[]|captureMode=hosted-browser]

For a hybrid target, each surface object additionally records `releaseSurface`, `surfaceClass`, `captureMode`, and its own `responsive` object. Use `captureMode=mixed` only with complete per-surface fields; a global mode or responsive set never substitutes for a surface's platform contract. A surface whose PRD entry declares `derivedStates` records the identical object as `derivedStates` in its surface object; the checker rejects a mismatch. The matrix of the HiFi Review receipts (Impeccable critique and audit, UI grading, HiFi surface check) then holds each derived state once, at that surface's smallest responsive target.

## Design System Need Gate

Decision: [required / not_required / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

Reason: [product-specific reason]

Existing design-system pair disposition: [none|retain|retire — reason; owner=<human>; decided=<YYYY-MM-DD>]

Replacement visual contract when not_required: target=[path @ sha256:hash]; ui-design=[path @ sha256:canonical-ui-approval-digest]; prd=[path @ sha256:hash]

Compiled design system pair: [markdown path @ sha256:<lowercase sha256> and json path @ sha256:<lowercase sha256>]


A `ui-design/3` gate is always `Decision: required` and adds `Package action: compile|update|reuse`. `compile` creates a new package (disposition `none` or `retire`); `update` revises the existing `design-system/4` package (disposition `retain`); `reuse` keeps an existing complete Markdown/JSON/HTML package byte-for-byte (disposition `retain`) and publication rejects any change or missing file. The action and disposition lines are workflow linkage outside the `ui-design/3` approval digest, so switching an unchanged package to `reuse` keeps its `uiDesign` binding current; any other approval edit makes the reused package stale and needs `update`. A `design-system/3` pair lacks the full HTML package and cannot be reused.

Use `Compiled design system pair` only for `required` and the replacement field only for retained `not_required` decisions. The compiled package consumes the approved UI contract and complete `ui-hifi/2` identities; the exact value `pending — design-system-compiler` is allowed only during the compiler preflight, and normal publication rejects it. Legacy `design-system/2` does not acquire the marker. For `not_required`, the disposition is machine-bound: `none` forbids canonical pair files, `retain` requires both pair files, and `retire` requires the pair to be archived before publication. `blocked` cannot pass publication.
```

Impeccable's heuristic scores and audit scores are diagnostic. A current `ui-design/2` package uses only the `H1`–`H9` thresholds in `ui-grading-rubric.md` to decide readiness. `W1`–`W5` and the wireframe evidence rows apply only to legacy inspection and validation.
