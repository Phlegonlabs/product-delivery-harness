# UI Design Output Contract

## Canonical Artifacts

- `docs/design/ui-design.md`: UI decisions, sources, gates, scores, and handoff.
- `docs/design/wireframes.html`: one approved structural projection of every PRD `UI-*` surface.
- `docs/design/ui-references/<run-id>/index.html` and its manifest-listed sibling HTML pages: the approved connected HiFi design-reference package when retention is authorized.
- `docs/design/design-system.md` and `docs/design/design-system.json`: present together only when the Design System Need Gate is `required`.

Legacy `docs/product/wireframes.html` and `docs/product/design-system.*` remain readable. New or revised artifacts publish under `docs/design/`; do not move an existing legacy artifact without exact owner authorization.

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
| --- | --- | --- | --- | --- | --- | --- |
| MM-001 | [UI-* / region] | [none / image / motion / image + motion] | [purpose and trigger] | [fallback] | [none / existing asset / CSS-WAAPI / GSAP / Higgsfield MCP / other owner-approved] | [approved / deferred] |

## Wireframe Approval

Wireframe: [repo-relative path @ sha256:<lowercase sha256>]

Frozen PRD basis: [repo-relative path @ sha256:<lowercase sha256>]

Copy Freeze: [approved / revision_requested / blocked]

Copy owner: [human owner]

Copy locale: [primary BCP 47 locale]

Copy approved on: [YYYY-MM-DD]

Responsive surface check: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

Wireframe references consulted: [sources and structural pattern adopted/rejected, or skip reason]

UI grading: PASS — evidence=[repo-relative evidence path] @ sha256:[lowercase sha256]

Wireframe score: [0-100]

Wireframe lowest dimension: [0-100]

Wireframe blocks: [none / named blocks]

Decision: [approved / revision_requested / blocked]

Decision owner: [human owner]

Decided on: [YYYY-MM-DD]

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

Each surface has exactly `id`, `page`, `route`, `states`, `responsive`, `navigation`, and `controls`. `page` names the entry or a listed child; the other fields keep the schema-1 surface/DOM contract. Every page renders exactly its assigned product surfaces, with one container per surface across the package, and the complete surface set equals the approved scope. Navigation/control IDs bind actual interactive elements inside that surface using `data-navigation-id` or `data-control-id`; a reviewer sidebar outside product surfaces is not interaction evidence.

Each interaction has exactly `id`, `source`, `control`, `kind`, and `destination`. Both endpoints are `{ "surface": "UI-001", "state": "ready" }` and must exist in the approved scope. IDs are unique. `kind: "navigate"` binds a real anchor whose `href` exactly equals the destination surface's page filename; `kind: "state"` changes to a different declared state on the same page, including feedback and overlays. Every page is reachable from index.html through product navigation. Every declared and rendered product control has an interaction. Derive these transitions from the approved PRD and wireframe actions; discrepancies return upstream, rather than inventing a new journey. Keep review-sidebar links to every page for capture setup, but verify product journeys through their own controls.

Schema-2 surface checks require `ui-output/2`. It retains all existing offline output fields and adds `interactions`. Its exact sandbox is `{ "network":"disabled", "topNavigation":"allowlisted-local-pages", "popups":"blocked", "forms":"blocked" }`. Each interaction runs at every source responsive target with both `trigger: "click"` and `trigger: "keyboard"`. Each output row contains exactly `id`, `target` (string), `trigger`, `source`, `destination`, `control`, `visible: true`, `focusCorrect: true`, and `result: "PASS"`; endpoints and control match the manifest. `navigation` records exactly one `{ "id", "target", "trigger", "from", "to" }` event per navigate case, with sibling page filenames. Missing, duplicate, or extra results/events fail. Retain blocked attempts too; never remove them to make the receipt pass. Non-document network requests, console errors, popups, and forms still fail. The browser setup and real click/key procedure are in `ui-design-pass.md`.

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

Each PASS evidence file is a `ui-evidence/2` human-attested JSON receipt with exactly `schema`, `check`, `result`, `reviewedArtifact`, `receipt`, `attestation`, and `owner`. `check` is platform-specific (for example `wireframe-browser`, `wireframe-browser-grading`, `wireframe-extension`, `wireframe-native`, `wireframe-desktop`, and corresponding HiFi checks); `reviewedArtifact` carries the exact current path and SHA-256; `receipt.matrix` is `{ "cases": [{"surface":"UI-*","state":"...","target":"..."}] }` derived per surface state × responsive target, `receipt.results` repeats those exact cases with `result: PASS`, and `receipt` carries a closed tool/method, a transcript/output artifact path+hash, and a past timezone-aware `executedAt`; `owner` names a human. Every `hifi-*` surface check uses method `sandboxed-offline-browser` with its platform tool. For legacy schema-1 HiFi, its retained `ui-output/1` output artifact additionally contains the exact `sandbox` object `{ "network":"disabled", "topNavigation":"blocked", "popups":"blocked", "forms":"blocked" }`, `console`, `network`, `navigation`, `popups`, and `forms` transcript arrays plus `popupAttempts` and `formAttempts` integer counts; any console error, request, navigation, popup, or form attempt fails. Legacy targets block all top navigation; schema-2 targets use the exact local-page allowlist and `ui-output/2` interaction contract above. The receipt is an attestation record, not an automatic approval—human Visual Approval remains required.

Agents may validate or draft a proposed receipt but cannot set `attestation: human-attested`, select `owner`, or approve a Wireframe/Visual gate. The owner performs or confirms the check and supplies the receipt.

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
