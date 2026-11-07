# HiFi Matrix Capture

`scripts/hifi_matrix_capture.py` observes the surface × state × target matrix of an assembled `ui-hifi/2` package in one browser session. It replaces the per-project browser harness for the case matrix of the HiFi surface check.

    python "<ui-design-builder-skill-root>/scripts/hifi_matrix_capture.py" --repo-root . --package docs/design/ui-references/<run-id> --out docs/evidence/<run-id>/surface-1

Run it from the repository root. Relative `--package`, `--out`, `--carry-from`, `--ui-design` and `--diff-against` paths are repo-root relative. `--package` and `--out` stay inside the repository, and `--out` must be new unless `--overwrite` is given. The browser is Node Playwright with Chromium (`npm ci`, `npx playwright install chromium`, or `PLAYWRIGHT_MODULE`).

## What a run does

Every manifest page path must be a plain file inside the package folder: `..`, absolute and drive paths, backslashes and links fail the run (exit 2) before anything is read. The package bytes are served from one closed same-origin context. Every other request, popup, form submit and download is blocked and recorded. The tool clicks no product control, so any document request after its own page open is a navigation: a declared page is still served, but the transcript records it (`allowlisted: true`) and the case fails. CDP `Log` and `Runtime` are on before the first load and are never cleared.

Each page loads once. For every applicable case the tool clicks the target and state controls in the version-3 reviewer shell, waits for fonts and running transitions (read from the animations, capped at 2 s), probes the product surface and screenshots `[data-hifi-canvas]`. Finite animations are then finished and infinite ones frozen at their first frame, so reruns compare. A hung case is cut off (30 s per action, 40 s per case) and recorded FAIL; the browser restarts. After three restarts the rest are BLOCKED.

`n/a` states are skipped. A case fails on a console error (not the mandated `navigate-to` CSP row), external request, navigation attempt, popup, form attempt, missing control or state view, a target or state that does not apply, a measured canvas width more than 1 px from a numeric viewport target (a size class records `geometry.canvasWidth` only), horizontal overflow of the product surface, or a timeout. A page-load error fails every case on that page. Overlap pairs are recorded, not failed.

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
| `--only UI-003,UI-004` | Only these surfaces. |
| `--carry-from <ui-output.json>` | Carry unchanged cases from an earlier output of this tool. |
| `--recapture-carried` | Screenshot carried cases too. |
| `--axes dark,reduced-motion,forced-colors,zoom-200` | Run a sample under each axis. |
| `--derived-once --ui-design <ui-design.md>` | Observe each derived state once, at its surface's smallest target. The derived states are the `derivedStates` keys in the Approved target scope of `<ui-design.md>`, read with the checker's own parser. |
| `--derived <json>` | With `--derived-once`: use this set instead of the `--ui-design` one. `<json>` maps surface ID to states: `{"UI-001": ["toast"]}`. |
| `--diff-against <earlier --out dir>` | Pixel diff against same-named earlier captures (Pillow): `identical` or `changed` with the changed-pixel ratio; a pixel is changed when any RGBA channel differs. |
| `--overwrite` | Write into a non-empty `--out`. Refused (exit 2) with `--carry-from` when `--out` is, holds or sits inside the folder of the carry source or of a capture it carries. |

`--only` writes a smaller matrix than the Approved target scope, so its output is diagnostic. `--derived-once` does not: with `derivedStates` the checker expects exactly the reduced matrix it writes (derived states once, at the smallest target). The sidecar records the derived set and its source, `--ui-design` or `--derived`. After the matrix, the run clicks and Enter/Space-activates every manifest interaction at every source target and writes the `interactions` rows and `navigation` events; a failed attempt fails the run. It then measures the `reviewer` object (see below).

## Reviewer object

`hifi_reviewer.reviewer_contract` derives the expected viewport and specimen rows from the package bytes, and the run measures every row in that order. Each page is opened again from scratch (the reviewer's stored selections are cleared first), so the entry observations and the specimen source reads happen at the default target, surface and state. Only reviewer shell controls are clicked; the pass never touches a product control, and its fresh opens are not navigation attempts.

The `viewport` rows record the measured canvas width per surface and target, whether the container query is applied, whether a host viewport media query is applied, and the visible surfaces. The `specimens` rows take each specimen's identity from the contract and its values from the browser: the source value from the bound source page (plus the browser-normalized probe value for tokens), and the specimen and display values from the in-page specimen the HIFI_REVIEWER template renders, including its `output` text.

Rows are written as measured. `validate_output` applies the checker's own reviewer rule (`reviewer_evidence_findings`) to the written output, so a measured row that disagrees with the derived one fails the run (exit 3) with the checker's finding; the sidecar's `reviewer` records keep the per-page measurements and reasons. A `--only` run still measures the full reviewer pass.

## Carrying

The fingerprint also covers the canvas's own paint and every visible element inside the canvas outside the product surface, because the screenshot covers the whole canvas. A case is carried when its render fingerprint equals the earlier one (both complete), the earlier result was PASS, the new observation is clean and the earlier capture still matches its hash. Page bytes are not the test: a token edit that leaves a case's geometry and computed styles unchanged still carries (`output-contract.md#render-fingerprint-carry-forward`). Console, geometry and fingerprint are always fresh; only the screenshot is skipped. `carriedFrom` names the source capture, the source output (path and SHA-256) and the earlier page SHA-256 for the defect ledger.

## Axes

The sample, once per page, is `ready` (or the first state) and the non-derived state with the most product DOM nodes, at the smallest and largest target. A derived state takes no axis. Dark, reduced motion and forced colors use media emulation. `zoom-200` sets CSS `zoom: 2` on the product surface: roughly 200% browser zoom at the same container width, with container queries still at the nominal target. The HiFi DOM marks no motion region or intent, so reduced motion runs on every page.

Axis results stay in `matrix-capture.json`: no cases in the `ui-output/3` matrix, no events in its transcript, never carried. An axis failure still sets exit code 1. An axis that cannot be applied (setup error, a page that did not open, the restart limit) writes BLOCKED rows with the reason; it is never skipped.

## What it does not prove

- Appearance. A fingerprint or pixel diff shows change, not correctness. A screenshot is evidence for a reviewer and grades nothing.
- Motion quality. Use the `motion-preview` check.
- Native, real-login or service behavior.
- Overlap and overflow are geometry heuristics: a pass can hide a defect, and an intentional overlay reads as an overlap.
