# HiFi Matrix Capture

`scripts/hifi_matrix_capture.py` observes the surface × state × target matrix of an assembled `ui-hifi/2` package in one browser session, or on several at once with `--workers`. It replaces the per-project browser harness for the case matrix of the HiFi surface check.

    python "<ui-design-builder-skill-root>/scripts/hifi_matrix_capture.py" --repo-root . --package docs/design/ui-references/<run-id> --out docs/evidence/<run-id>/surface-1 --workers 4

Run it from the repository root. Each `--workers` browser is one headless Chromium, so lower the count on a loaded machine. Relative `--package`, `--out`, `--carry-from`, `--ui-design` and `--diff-against` paths are repo-root relative. `--package` and `--out` stay inside the repository, and `--out` must be new unless `--overwrite` is given. The browser is Node Playwright with Chromium (`npm ci`, `npx playwright install chromium`, or `PLAYWRIGHT_MODULE`).

## What a run does

Every manifest page path must be a plain file inside the package folder: `..`, absolute and drive paths, backslashes and links fail the run (exit 2) before anything is read. The package bytes are served from one closed same-origin context. Every other request, popup, form submit and download is blocked and recorded. The matrix pass clicks no product control, so any document request after its own page open is a navigation: a declared page is still served, but the transcript records it (`allowlisted: true`) and the case fails. CDP `Log` and `Runtime` are on before the first load and are never cleared.

A browser loads a page once for each run of cases on it and never reloads between cases; with `--workers` that is once per browser that runs cases on the page. Every interaction attempt and every reviewer pass starts from a fresh load, so no attempt depends on an earlier one. For every applicable case the tool clicks the target and state controls in the version-3 reviewer shell, waits for fonts and running transitions (read from the animations, capped at 2 s), probes the product surface and screenshots `[data-hifi-canvas]`. Finite animations are then finished and infinite ones frozen at their first frame, so reruns compare. A hung case is cut off (30 s per action, 40 s per case) and recorded FAIL; the browser restarts. A timed-out operation attempt spends that operation's three recovery restarts; any other timeout spends its page's three. A spent budget makes only the rest of that operation or page BLOCKED, with the limit as the reason, and all other work continues on a fresh browser. A recovery load failure stays local to its page, and a browser that cannot restart blocks only the rest of its page; the next page starts a fresh one.

States ending in `:n/a` need no product marker or state/target case. Overview still records their reason. A case fails on a console error (not the mandated `navigate-to` CSP row), external request, navigation attempt, popup, form attempt, missing control or state view, a target or state that does not apply, a measured canvas width more than 1 px from a numeric viewport target (a size class records `geometry.canvasWidth` only), horizontal overflow of the product surface, or a timeout. A page-load error fails every case on that page. Overlap pairs are recorded, not failed.

## Outputs

- `ui-output.json`: `ui-output/3`, check `hifi-browser`, tool `playwright`, method `sandboxed-offline-browser`. Matrix, results, transcript and an execution block with real timestamps, versions and path plus SHA-256 for the subject, every page, the sidecar and every capture. `review_evidence.py` builds the receipt from it.
- `matrix-capture.json`: `hifi-matrix-capture/1`. Per case: `renderFingerprint`, `fingerprintIncomplete`, `geometry`, `durationMs`, `startedAt`, `finishedAt`, `settle`, `capture`, `carriedFrom`, reasons. Result rows in `ui-output/3` are closed, so these live here.
- `<surface>-<state>-<target>-<hash>.png`: the canvas. `<hash>` is the first 10 hex characters of SHA-256 over the case tuple.

The render fingerprint is the SHA-256 over the geometry probe, a digest of every scanned element rect, a digest of computed styles (including `background-image`, `mask-image`, `border-image`, `fill`, `stroke`, `stroke-width`) and visible text, and a digest of image inputs: `img` `src`/`srcset`/`sizes`/`currentSrc`, `source`, `video` `src`/`poster`, inline `svg` markup and `use` targets.

The probe scans at most 400 elements; past that the case is marked `fingerprintIncomplete` in the sidecar and is never carried, so a fresh screenshot is taken and judged.

Exit codes: 0 every case PASS; 1 a FAIL or BLOCKED case or an axis failure; 2 unusable input; 3 the written output failed validation.

## Flags

| Flag | Effect |
| --- | --- |
| `--workers N` | Run on N browsers at once, 1 to 4 (default 1); a higher value exits 2. Each worker is one headless Chromium. The work is split before the run from the package alone, so the same package and N always give the same split and the same output order. Cases, interactions, axis rows and reviewer rows match a one-browser run; the transcript lists can hold more page-load rows. Restart budgets belong to pages and operations and survive phase changes. An operation's attempts always run in one browser. A page's cases can be split across browsers, each with the page's budget, so a page that hangs more than three times can end with more FAIL and fewer BLOCKED rows than a one-browser run. A spent budget never blocks other work in the same worker, and a browser that cannot restart for the next phase leaves its first page to start a fresh one. Never more browsers than work items: `run.workers` in `matrix-capture.json` records the count used, and the printed `restarts` totals all of them. |
| `--only UI-003,UI-004` | Only these surfaces. |
| `--carry-from <ui-output.json>` | Carry unchanged cases from an earlier output of this tool. |
| `--recapture-carried` | Screenshot carried cases too. |
| `--axes dark,reduced-motion,forced-colors,zoom-200,reflow-320` | Run a sample under each axis. |
| `--derived-once --ui-design <ui-design.md>` | Observe each derived state once, at its surface's smallest target. The derived states are the `derivedStates` keys in the Approved target scope of `<ui-design.md>`, read with the checker's own parser. |
| `--derived <json>` | With `--derived-once`: use this set instead of the `--ui-design` one. `<json>` maps surface ID to states: `{"UI-001": ["toast"]}`. |
| `--diff-against <earlier --out dir>` | Pixel diff against same-named earlier captures (Pillow): `identical` or `changed` with the changed-pixel ratio; a pixel is changed when any RGBA channel differs. |
| `--color-scheme dark` | Run the whole base matrix with the browser context at `colorScheme: dark`, from the first page load to the interaction pass. The dark run goes to its own `--out` as a separate `ui-output/3`. |
| `--intermediate` | Also capture each surface's axis-sample states ([Axes](#axes)) at the midpoint width between each adjacent pair of numeric viewport targets, into a second `ui-output/3` under `OUT/intermediate` (own sidecar and captures). It runs no interactions and no reviewer pass; those rows belong to the base output. A failing sweep case or coverage finding fails the run. |
| `--measure-a11y` | Also measure contrast, target size, text clip, text split, focus visibility and text growth into the sidecar's `a11y` object (see Measured accessibility). Off by default, and then the output is the same as without the flag. |
| `--overwrite` | Write into a non-empty `--out`. Refused (exit 2) with `--carry-from` when `--out` is, holds or sits inside the folder of the carry source or of a capture it carries. |

`--only` writes a smaller matrix than the Approved target scope, so its output is diagnostic. `--derived-once` does not: with `derivedStates` the checker expects exactly the reduced matrix it writes (derived states once, at the smallest target). The sidecar records the derived set and its source, `--ui-design` or `--derived`. After the matrix, the run clicks and Enter/Space-activates every manifest interaction at every source target and writes the `interactions` rows and `navigation` events; a failed attempt fails the run. It then measures the `reviewer` object (see below).

## Product interactions

Feedback interactions keep their source surface and state. The driver compares source DOM and form values before and after activation. Focus alone does not count. Each feedback row records different `observed.change.beforeSha256` and `afterSha256` values; an inert control fails.

For a text input or textarea, activation enters a short probe value. For a select, it chooses a different enabled option. Keyboard activation starts from focus and types or uses arrow keys. Disabled and read-only fields fail. Entry alone never waives the required destination, focus or source-change proof.

If clicking a field already applies its declared different destination, observe that arrival without entering more data into the hidden source.

An equal-endpoint `state` attempt fails. An unselected legacy row does not block a diagnostic `--only` run; full static validation still rejects it.

Empty navigation or control arrays create no interaction attempts. A PRD surface with `operations: none — <reason>` has both arrays empty and renders no product control. Its applicable state/target cases still run.

When no control instance is visible, the driver searches attached instances in DOM order for the first reachable instance. Every hidden ancestor must be a panel with exactly one declared same-surface opener. Inactive state or target variants and unrelated hiding make an instance unreachable. The driver opens that instance's menu, tab or disclosure panels from outermost to innermost. Openers may omit IDs and interactions. Each panel stays inside its opener's product surface and must become visible. `observed.openers` lists the clicked panel IDs.

After reviewer setup, the driver records every focus event inside any product surface. Required openers receive focus once in order, followed by the operation control once. Each preparatory opener may transfer focus once into its newly opened panel. After operation activation, allow either one layer entry or one focus return, directly after the operation-control event. No transfer is required. A layer entry targets the activated opener's panel or a destination dialog, hidden before activation and visible at entry and completion. A focus return targets a declared opener whose panel contained the control and was open before activation, then hidden at return and completion. If nested containing panels close together, the return may target any of their openers, checked innermost first. Any intervening focus or second transfer fails. `observed.focusEntry` or `observed.focusReturn` records that layer's unique ID.
Verified reviewer heading focus remains recorded as reviewer setup and does not count as product focus. Verification requires an exact accepted runtime body and its direct focus call location.

Supporting form fields use `data-control-for` with an existing control ID in the same surface. They need no separate manifest interaction. The driver activates the operation control; a feedback snapshot also includes current form values.

Repeated control IDs may appear on multiple rows. The driver prefers the first unselected visible instance. Selection uses `aria-pressed`, `aria-selected`, `aria-checked` and `aria-current`; all selected falls back to the first instance. `observed.instances` records the visible count and `observed.instanceIndex` records the zero-based chosen index. Every navigate instance remains an anchor to its declared destination. A missing or entirely hidden control still fails.

`state` may cross pages through an anchor to the exact destination page and encoded state fragment. The driver checks arrival page, surface, state and URL. Its navigation row names the page filename; any extra navigation fails.

`navigate` also accepts that exact state anchor, including on the same page. A bare page link is valid only for the destination surface's first applicable state. Every instance is checked. The driver observes arrival page, surface, state and URL. The reviewer applies the arrival fragment first; product navigation without one uses the destination default, independent of stored selections.

The reviewer saves the resolved arrival surface and state. Reload must retain that arrival rather than revive an older saved state.
Same-page fragment navigation clears its arrival marker, so later reviewer selections survive reload. Bare links still use document-arrival handling.

## Reviewer object

`hifi_reviewer.reviewer_contract` derives the expected viewport and specimen rows from the package bytes, and the run measures every row in that order. Each page is opened again from scratch (the reviewer's stored selections are cleared first), so the entry observations and the specimen source reads happen at the default target, surface and state. Only reviewer shell controls are clicked; the pass never touches a product control, and its fresh opens are not navigation attempts.

The `viewport` rows record the measured canvas width per surface and target, whether the container query is applied, whether a host viewport media query is applied, and the visible surfaces. The `specimens` rows take each specimen's identity from the contract and its values from the browser: the source value from the bound source page (plus the browser-normalized probe value for tokens), and the specimen and display values from the in-page specimen the HIFI_REVIEWER template renders, including its `output` text.

Rows are written as measured. `validate_output` applies the checker's own reviewer rule (`reviewer_evidence_findings`) to the written output, so a measured row that disagrees with the derived one fails the run (exit 3) with the checker's finding; the sidecar's `reviewer` records keep the per-page measurements and reasons. A `--only` run still measures the full reviewer pass.

## Carrying

The fingerprint also covers the canvas's own paint and every visible element inside the canvas outside the product surface, because the screenshot covers the whole canvas. A case is carried when its render fingerprint equals the earlier one (both complete), the earlier result was PASS, the new observation is clean and the earlier capture still matches its hash. Page bytes are not the test: a token edit that leaves a case's geometry and computed styles unchanged still carries (`output-contract.md#render-fingerprint-carry-forward`). Console, geometry and fingerprint are always fresh; only the screenshot is skipped. `carriedFrom` names the source capture, the source output (path and SHA-256) and the earlier page SHA-256 for the defect ledger.

## Axes

The sample, once per surface, is `ready` (or the first state) and the non-derived state with the most product DOM nodes, at the smallest and largest target; `--intermediate` sweeps the same states. A derived state takes no axis and no intermediate width. Dark, reduced motion and forced colors use media emulation. `zoom-200` sets CSS `zoom: 2` on the canvas and halves its CSS inline size. The rendered box keeps the target width, while container queries see half that width. `geometry.containerInlineSize` records the query-container width; reset restores the nominal width. `reflow-320` re-runs the same sampled states once each, driven from the surface's smallest target with the canvas overridden inline to 320 CSS px; a row fails on horizontal overflow or a canvas width more than 1 px from 320. The HiFi DOM marks no motion region or intent, so reduced motion runs on every page. Long and localized copy is judged from the authored copy of each surface ([ui-grading-rubric.md](ui-grading-rubric.md#reading-and-cross-screen-cases)), not from a flag.

Axis results stay in `matrix-capture.json`: no cases in the `ui-output/3` matrix, no events in its transcript, never carried. An axis failure still sets exit code 1. An axis that cannot be applied (setup error, a page that did not open, the restart limit) writes BLOCKED rows with the reason; it is never skipped.

Intermediate work inherits the base run's page and operation budgets, including when its items move to another worker. Exhausted pages and operations stay BLOCKED; other work continues.

## Measured accessibility

`--measure-a11y` adds a top-level `a11y` object to `matrix-capture.json`, measured inside the product surface on visible elements in the same page visit as each case's probe. A finding never changes a case result, the `ui-output/3` file or the exit code. The author fixes each failure or records a disposition with a reason; the lead grader reads both as H4/H8 evidence.

| Measurement | Runs on | Reports | Cannot prove |
| --- | --- | --- | --- |
| `contrast` | base cases; `dark` axis sample | Text under 4.5:1 against its nearest opaque ancestor background (3:1 for 24 px, or 18.66 px at weight 700). Input placeholders count; disabled controls are skipped. A background image or gradient, a translucent colour or a media element in between, or an opacity under 1 on the text or any ancestor, gives an `unmeasured` row with its reason. | Text over art or a gradient, and anything `unmeasured`. |
| `target-size` | base cases | Interactive boxes under 24 by 24 px. On targets under 600 px wide, boxes under 44 px are `note` rows. Links inside a run of text are skipped. | Spacing between targets, or a label that enlarges a small control. |
| `text-clip` | base cases; `zoom-200` axis sample | Text cut by its own box (`overflow` hidden or clip, ellipsis, line clamp) and placeholders wider than their input. | Text cut by an ancestor's `clip-path` or a mask. |
| `text-split` | base cases; `zoom-200` axis sample | A figure (digits with a currency symbol or code, sign, separators, decimals, percent or unit, or a date) drawn on more than one line, and a CJK word of 2 to 6 characters (`Intl.Segmenter` in the element's `lang`) split by a line break in a text of 24 characters or fewer. The row names the element, the `token` and its `lines`. Wrapping between words, longer CJK text and text that `text-clip` reports give no row. | That the split is unwanted: a forced break the design asked for, such as a `<br>` inside a figure, is still reported. It misses a figure split across separate blocks, cells or flex items, and number formats it does not know. |
| `focus-visible` | the axis sample in the base scheme; `forced-colors` axis sample | A focusable control with no outline and no change in border, box-shadow or background when keyboard-focused. Under forced colors only an outline or a border change counts. Focus is restored afterwards. | That the indicator is visible enough, or the tab order. |
| `text-growth` | `zoom-200` axis sample | Text, including the text of inputs, textareas and selects, whose rendered size grew less than 1.9 times against the same element in the same case without the axis. | Layout quality at 200%. |

Rows carry `measure`, `surface`, `state`, `target`, `axis` (`base` or the axis name), `selector`, `level` (`fail`, `note` or `unmeasured`), the values and the `limit`. Elements clipped to 1 px or less are skipped. The probe's 400-element cap applies: a cut scan is listed in `incomplete`. An axis measurement needs its axis in `--axes`; without it the measurement is listed once in `notRun` and in the printed `a11y` summary, and no axis is turned on for it. Carried cases are still measured, and `--workers` gives the same rows in the same order.

## What it does not prove

- Accessibility. The measurements find some defects; a clean `a11y` object is no WCAG conformance.
- Appearance. A fingerprint or pixel diff shows change, not correctness. A screenshot is evidence for a reviewer and grades nothing.
- Motion quality. Use the `motion-preview` check.
- Native, real-login or service behavior.
- Overlap and overflow are geometry heuristics: a pass can hide a defect, and an intentional overlay reads as an overlap.
