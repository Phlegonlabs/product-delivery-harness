# UI Design Pass

Run this optional pass only after the human owner explicitly asks to continue beyond an approved `wireframes.html` and the market-research gap pass is resolved. It belongs to `product-definition-builder`: it turns the approved low-fidelity structure into a human-approved visual target before deciding whether a formal design-system pair is useful.

## Frozen Inputs

Every direction and preview uses the same:

- representative `UI-*` screens;
- approved `wireframes.html` page, section, element, action, state, and responsive projection, checked against `PRD.md`;
- exact copy or bounded display contracts;
- Builder UX Direction, brand, accessibility, platform, and performance constraints; and
- applicable `MR-*` market evidence and inspected `REF-*` visual evidence.

The pass may explore typography, color, composition, imagery, texture, and motion. It may not add, remove, reorder, or reinterpret product scope, content responsibility, actions, flows, states, or trace IDs. A structural finding returns to the PRD and wireframe flow and requires renewed wireframe approval.

## Taste Applicability Gate

The standard recipe is both skills, working from the approved PRD package: `design-taste-frontend` leads the overall design direction for the surfaces it covers, and `frontend-design` executes the surfaces Taste excludes. Decide the split first, then run the whole pass as one combined effort — Taste first for the overall direction, `frontend-design` filling its named surfaces. Neither skill reopens product scope; both start from the frozen inputs below.

Load `design-taste-frontend`, read its scope, and record one result:

- `applicable`: landing, portfolio, editorial, public marketing, or compatible redesign surfaces;
- `partially_applicable`: only the named compatible public surfaces use it; or
- `n/a: <reason>`: dense dashboards, data tables, multi-step operational UI, native mobile, or another exclusion declared by the skill.

When applicable, record its one-line Design Read plus explicit `DESIGN_VARIANCE`, `MOTION_INTENSITY`, and `VISUAL_DENSITY` values with product-specific reasons. When it is partially applicable or `n/a`, load `frontend-design` for the uncovered product surfaces and follow the selected platform or official design-system conventions. Do not force Taste rules onto a surface the skill excludes.

Do not load `gpt-taste` by default and never combine it with `design-taste-frontend`. It is an explicit owner-selected alternative only for a named high-motion experimental marketing surface; record the override and exact scope.

## Direction And UI Preview Gate

Ask the human owner once for desired character, disliked patterns, and any visual references. Inspect supplied or current public references before claiming their visible mechanics. Keep market evidence and visual evidence separate.

Default to one recommended product-specific direction. Produce three materially different directions only when the owner asks to compare alternatives or when a recorded visual conflict cannot be resolved with one recommendation. Every compared direction must use the same screens, content, states, and viewport or size class.

Record every inspected visual source as a `REF-*` record and every owner-confirmed `Adopt / Adapt / Avoid` principle as an `RP-*` record, using the formats in `../design-system-compiler/references/design-reference-guide.md`. Give every direction a `VD-*` ID under that guide's round versioning: a default single-direction pass records `VD-R1-01`, and each later revision round increments. Name the selected `VD-*` direction and its confirmed `REF-*` / `RP-*` IDs in the handoff so the design-system step can read the provenance without re-deriving it.

Choose iconography through an online lookup, not from memory. When the approved structure uses icons — navigation, actions, status, empty states — consider exactly four maintained icon libraries: Lucide, Phosphor, Heroicons, and Tabler. Pick the primary set and the named fallback from this closed candidate set by fit with the selected direction's character (outline versus solid, stroke weight, density), and verify each candidate's license, framework support, and maintenance status against its official source on the pass date. Record them in the handoff's `Iconography:` line with the cited official-source URLs and retrieval dates, and mark an unevidenced pick `UNVALIDATED` — the same rule as market research. Do not widen the candidate set with other libraries; a need these four genuinely do not cover is recorded as an open question for the owner rather than a silent substitution. Skip the lookup only when the product uses no icons or no web search or fetch tool is available, and record which reason applied; never silently default to a remembered library.

Choose typography through the same online-lookup discipline. Recommend a font pairing — display and body, which may be the same family — that fits the selected direction: search maintained families on Google Fonts or the family's official site, and verify on the pass date the license, the needed weights and optical sizes (variable fonts where they help), and Latin plus CJK coverage. For a Chinese-language product, record the CJK stack explicitly — a Noto Sans TC/SC class family or the platform system-font stack — with the fallback order and how the Latin and CJK faces combine. Record the pairing, the loading strategy (self-host versus CDN, subsetting, `font-display`), and the cited official-source URLs with retrieval dates in the handoff's `Typography:` line; an unevidenced pick is `UNVALIDATED`. Skip with a recorded reason only when the platform fixes the faces (for example a native app bound to system fonts) or no web tool is available.

Record the color decision in the handoff's `Color & dark mode:` line: how the palette derives from the brand or direction base (name the scale approach), whether dark mode is in scope for this pass or a named later scope, and the cited source for any palette system the derivation used. This line records the selection; contrast verification stays with `design-system-compiler`'s `check_color_contrast.py` at design-system compile time, and a palette that cannot pass contrast is revised there, not silently kept.

Choose the provider-neutral preview route whose approved artifact can serve directly as the Harness implementation reference:

1. rendered HTML or temporary React — the default route for every UI-bearing surface: web, native or cross-platform mobile, and desktop. Produce it with the already loaded design skill (`design-taste-frontend` when applicable, otherwise `frontend-design`). A web or cross-platform surface uses one self-contained high-fidelity file per representative `UI-*` screen because Harness implements each recorded route from its own approved reference. A native mobile or desktop surface uses one self-contained high-fidelity HTML containing every `UI-*` screen of that surface — the same single-file principle as `wireframes.html` — with a screen switcher, each screen mocked at its size class as a plain device-sized page, optionally inside a drawn device frame, so the owner reviews the whole app in one file. Record in the handoff that the native implementation translates the retained single-file reference within the recorded tolerance;
2. `imagegen-frontend-web` for a website section or page image when no HTML rendering capability exists;
3. `imagegen-frontend-mobile` for a native or cross-platform mobile screen image when HTML cannot represent the surface, such as platform chrome or native-only interaction; or
4. another named image-generation, design, or external provider.

This flow does not require Codex. Before generation, record the available tool and provider/model. If no suitable preview capability exists, return a complete reusable prompt package and pause until the resulting preview is supplied. Continue without a preview only when the human owner explicitly waives visual review and records why.

Optional `brandkit` exploration is allowed only when no approved brand system exists and the human owner explicitly authorizes brand exploration. Treat the board as non-canonical inspiration until its Adopt / Adapt / Avoid principles are confirmed.

Image generation may invent plausible controls or content. Treat an invented element as a failed preview, not permission to add it to the product.

## Evidence And Approval

For every retained preview, record:

- preview ID and direction ID;
- `UI-*` surface and state;
- viewport or size class;
- preview route and provider/model;
- complete prompt or source;
- seed when supported;
- local path and SHA-256;
- observed limitations, including unreadable text or non-observable interaction; and
- human decision: `approved`, `rejected`, `revision_requested`, or `waived` with reason.

Preview artifacts stay outside `docs/product/`. When an approved HTML preview will serve as the page-faithful implementation reference, request retention by default: disclose and obtain exact write approval for a path under `docs/design/ui-references/<run-id>/`, the dedicated UI references folder. Retain one file per recorded web or cross-platform screen, or one all-screens file per native mobile or desktop surface. Other previews are retained only when the owner requests it; otherwise use temporary storage and say that it will not publish with the package. When the owner declines retention and that preview is the approved page-faithful target, the handoff must record the target as temporary: the visual authority then reverts to `PRD.md` plus approved `wireframes.html` once the run ends, because the recorded path stops resolving. A durable target binding requires retention, and Harness cannot implement from an HTML reference whose recorded path is temporary.

When a later approved UI target supersedes retained UI references, archive the superseded files by moving them under `docs/design/archived/<YYYYMMDD-HHMMSS>-<run-id>/` — the same archive-not-delete discipline `references/artifact-lifecycle.md` applies to superseded product documents — and update the UI Design Handoff to the new live paths. Never delete a superseded reference file or leave a live handoff entry pointing at an archived path.

When a style-impacting enhancement updates a retained HTML reference, regenerate the affected screens' style layer from the current direction instead of appending to the previous file's CSS. Before presenting the updated reference for approval, check it for style blocks inherited from the superseded version — orphaned selectors, duplicate rules, and overrides the updated screens no longer use — and remove them; a reference that accumulates styles from previous versions is not approvable. Editing a retained reference file in place supersedes its previous content: refresh the handoff's recorded SHA-256 for that file in the same run and archive a copy of the pre-edit file under `docs/design/archived/`, exactly as a superseded reference set would be.

An approved preview becomes an implementation target only when `PRD.md` records its source path or immutable version, SHA-256, named routes and states, responsive scope, acceptance tolerance, and allowed deviations. This page-faithful target is visual authority for only that recorded scope. When the approved target is high-fidelity HTML, `delivery-harness` implements each recorded route from its approved HTML reference file within the recorded tolerance. Approval proves visual-direction conformance, not usability or production readiness.

## Design System Need Gate

After visual approval, record exactly one result in `PRD.md`:

- `required`: the owner requests a formal design system; an existing design-system pair is already canonical; or the product needs reusable shared tokens and closed component variants across multiple surfaces, themes, platforms, teams, or automated conformance checks;
- `not_required`: the approved work is a small or single-surface UI whose visual target, PRD behavior, and wireframes are sufficient for implementation; or
- `blocked`: the owner decision, source evidence, or approved preview needed to decide is missing.

Record the decision owner, reason, affected scope, and replacement visual contract. `not_required` is a normal outcome, not a waiver. When `required`, invoke `design-system-compiler` only after the UI target is approved; it compiles the approved direction into `design-system.md` and `design-system.json` without reopening visual direction by default. When `not_required`, pass the approved page-faithful target directly to Harness with `PRD.md` and the approved `wireframes.html` review projection; for a web pass that means the retained approved HTML reference files with their recorded hashes.
