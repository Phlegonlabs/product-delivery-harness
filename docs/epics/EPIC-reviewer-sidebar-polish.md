# Shared Reviewer Sidebar Polish

Design workflow: maintenance
UI impact: style

## Goal And Baseline

The owner asked to improve the left sidebar in both Wireframe and HiFi HTML, then accepted using frontend-design to implement the proposed polish on codex/reviewer-sidebar-polish. Base and observed origin/main are e6bbfea7e6481dd038041f5654defb2ae810b1e8 (0.54.2). The existing isolated checkout is reused; the original mixed working tree remains untouched.

Route: small direct maintenance with one GLM Flash frontend writer, as allowed by the owner. Parent owns this record, index and verification. This is shared reviewer chrome, not product UI authoring. No product PRD, stack decision, PLAN/RUN or new approval gate applies. Canonical skills and template contracts remain authority.

## Scope And Design

Refine the existing shared CSS and synchronize its embedded segments in Wireframe and HiFi templates. Retain the 236px sidebar, controls, IDs, target/state behavior, Shadow DOM boundary and product canvas. Use quieter navigation rows, a clear active state, compact typography, separated control groups and a two-column target grid. Preserve long-label wrapping, sidebar scrolling, visible focus and reduced motion. Four README descriptions remain aligned. No new asset, dependency, external font, schema or generated repository artifact is needed; existing ignore rules suffice.

## Acceptance

- Both reviewer sidebars share consistent visual hierarchy and control styling.
- Four numeric targets form a two-column grid without overlap or horizontal clipping; named native targets and long CJK labels remain usable.
- Page/state/target switching and keyboard focus remain functional; a short viewport retains scroll access.
- Product styles and exact canvas widths stay unchanged; product CSS cannot enter the reviewer shell.
- Inspect real before/after browser captures and run relevant integration, runtime and required browser checks, followed by repository-required verification.

## Change Log

- 2026-09-25: clean exact-main baseline observed. Created the owner-accepted named branch in the existing isolated checkout. GLM Flash frontend worker owns only canonical shared CSS, its two embedded template segments and four README descriptions; no worker commit, push, install, clone or cleanup is authorized. Parent retained baseline preview fixtures outside the checkout at C:/Users/mps19/AppData/Local/Temp/pdh-sidebar-preview-20260925-043345/. Implementation and visual verification pending.

- 2026-09-25 implementation: GLM Flash run 20260925-043627-4814b8b8c0094a13afcefe2e36f7fab6 reached the 900-second deadline after writing canonical shared CSS and synchronizing both embedded template segments. The wrapper inspected and terminated its owned process tree; parent confirmed the worker processes ended. No worker completion or test PASS is claimed. Parent reviewed the retained three-file diff and supplied the four-language descriptive documentation. Shadow DOM, sidebar width, shell markup, runtime and product CSS remain unchanged. Parent-owned Epic/index edits happened while the worker was running, so they are tracked separately from its three authored files.

- 2026-09-25 parent verification: all 281 UI tests (including required Chromium), 15 cross-skill tests, specification, docs weight and whitespace checks passed. Both templates differ only inside the exact shared CSS segment; markup, runtime and product styles are unchanged. Actual before/after captures and stress-evidence.json prove equal 2x2 target columns, working selection, 2px keyboard focus, zero transition duration for reduced motion and no sidebar horizontal overflow with enlarged long CJK/Latin labels at a 390x420 viewport. Parent read the full frontend-design skill and retained its snapshot in the external preview directory; the timed-out worker supplied no final read attestation. Parent's design critique accepts the quieter navigation and more compact hierarchy; no product-design quality or approval claim is made. Original source checkout remains untouched. Prior owner commit/push/merge/skill-update instructions continue for this refinement; prepare version 0.54.3 and exact-SHA CI before promotion.

- 2026-09-25 release metadata: style commit 0d683fb contains the verified shared-shell change. Parent synchronized package and lockfile versions, installed-skill VERSION, RUNBOOK default, pinned tests, and four README badges/history entries to 0.54.3. No dependency pin changed. Full exact-candidate CI, security review, protected-main promotion and official installation remain release checkpoints. Evidence stays in the existing external preview directory; no source history or earlier approvals are rewritten.

- 2026-09-25 PR follow-up: candidate e68c4b64 passed both full CI jobs and independent security review, but PR125 review required persistent sidebar regression coverage before merge. GLM Flash test run 20260925-050952-eb94e4a8c09e486dbdb3348ba72d2f12 reached its deadline with a test draft; no worker PASS is claimed. Parent repaired its fixtures, current-page counting, Shadow DOM focus, browser-evaluation scope and subpixel tolerance. Windows also exposed a UTF-8 stdin encoding failure; the shared browser runner now passes encoding explicitly. Task-owned timed-out processes were inspected and terminated. The new Chromium case uses both actual templates and checks equal two-column targets, no overlapping controls, active states, keyboard focus, reduced motion and enlarged CJK/Latin labels with short-viewport scrolling. Product and template bytes did not change in this follow-up. Focused browser checks passed; the replacement candidate requires fresh full CI and review. Release completion and exact-main verification are recorded in PR125 and the external release receipt, preserving this checkpoint as history.

- Browser timeout cleanup produced a checkout-root Chromium debug.log (GPU mailbox diagnostics). Its local bytes remain preserved; .gitignore now excludes this specific reproducible browser artifact. Source templates and test fixtures remain tracked.
