# EPIC-ui-motion-and-libraries: motion has a place in the stack decision, two more routes and a recipe for generated media

Status: in_progress; candidate 0.82.0 on local branch `ui-motion-and-libraries`, verified at `1ffd7cd7` and reviewed once, stacked on the unpublished 0.81.0 branch `ui-reference-driven-design`; not pushed, not installed
Design workflow: enhancement
UI impact: none (stack-decision rules, motion routing rules, one route allowlist entry in the UI checker, the option catalog and documentation; no product UI).

## Problem And Baseline

The owner asked how animation plugs into the UI flow, how the connected Higgsfield MCP fits, and which UI libraries the option catalog lacks. Reading the suite showed:

- The stack is approved in Product Definition before UI design asks about motion, and Motion, GSAP and Three.js need stack approval. An expressive motion choice sent the round back upstream.
- Lottie and Rive were in the motion catalog, and no `MM-*` row could name them as a route.
- A HiFi approximation of a library that cannot run in the closed page is what the owner approves; nothing put it next to the real behavior in implementation.
- The suite said a generation provider "may create an asset" and gave no recipe.
- The catalog had one chart entry, no table entry, no platform motion, no named native motion, and listed GSAP's commercial license as unverified.

Baseline: `ui-reference-driven-design` `b733a50b` (0.81.0 candidate), itself on `main` `7e1f1af4` (v0.80.0).

## Accepted Scope

Owner instruction 2026-11-15: run this as a separate round with multiple agents.

- An optional `motion` row in the stack decision: a ceiling drawn from `CSS/WAAPI`, `Motion`, `GSAP`, `Three.js`, `Lottie`, `Rive`, approved with the rest of the stack. A package without the row keeps the old rule.
- `Lottie` and `Rive` as motion routes; the UI checker's route allowlist accepts them.
- The stack rule for motion libraries is stated once and cites the `motion` layer. The View Transitions API and CSS scroll-driven animations need no stack entry and are progressive enhancement.
- `## Generated Clips And Models`: what a provider gives and does not give, order, seamless loop, 3D model, preparation, record fields, failure.
- `## Motion Approximation Comparison`: the first implementation slice puts a HiFi approximation beside the real library's frames with `capture_sheet.py`.
- Catalog: charts, tables, platform motion with a browser table, dotLottie, Rive license, GSAP Standard License terms, four animated component sources, native motion, Ark UI, a rule for component-source tools.

Kept unchanged: gates, approvals, owner turns, thresholds, provider authorization rules, every approved package.

Dropped on inspection: a scripted comparison of observed animation timing with the motion notes. The capture driver sees only animations running at load.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| UML-1 | A stack decision passes with a `motion` row and without one; a duplicate or `Recommended` row is rejected by the existing row rules | `test_product_package_checker.py` (150 tests), `test_native_stack_styling.py`, `test_skill_contract.py` (product-definition-builder) |
| UML-2 | An `MM-*` row may name `Lottie` or `Rive` without a provider authorization; an unknown route still needs one; existing fixtures pass unchanged | `test_ui_design_contract.py` (69 tests) |
| UML-3 | The stack rule, the generated-media recipe and the approximation comparison are each stated once and linked | `test_skill_contract.py` (ui-design-builder), `test_reference_library.py`, link check over the changed files |
| UML-4 | Every catalog candidate carries an official source registered in `sources.md` and a check date | `test_reference_library.py` (13 tests) |
| UML-5 | READMEs carry the 0.82.0 entry in four languages; release surfaces agree | `prepare_release.py --check` |

## Document Impact

| Changed source | Affected live artifact | Required recheck |
| --- | --- | --- |
| `frontend-stack-selection.md`, `mobile-stack-selection.md`, `output-contract.md` (product-definition-builder) | Next Stack Decision Checkpoint | None for approved packages |
| `motion-and-media-routing.md`, `stages/ui-design.md`, `ui-design-pass.md`, `enhancement-recommendations.md`, `UI_DESIGN.template.md`, `ui-grading-rubric.md` | Motion routing in the next UI round | None for approved packages |
| `ui-implementation-contract.md` | First implementation slice of a product with an approximation row | Comparison sheet in that slice |
| `check_ui_design_contract.py` route allowlist | Five-skill bundle bytes | Consumers re-pin after a release install |
| `option-library/` | Reference only | None |

## Execution Record

Three Sonnet 5.5 writers (`claude-t3-direct` / `claude-sonnet-5-5`, effort high) through `delegate_task`, one T3 worktree each from `c6e0c47c`, disjoint file ownership. Briefs: `task/ui-motion-and-libraries/COMMON.md` and `M1.md` to `M3.md`. The parent (Claude Fable 5.2) read each diff and cherry-picked onto `b733a50b`.

- M2 `1f085281`: the `motion` layer in both stack-selection guides and the output contract; the checker already accepted an extra layer row, so only tests were added.
- M3 `f486879b`: routes, stack rule, generated-media recipe, approximation comparison, one allowlist entry in the checker, tests. No provider was called and no credits were spent.
- M1 `0fb2fb64`: catalog, with every candidate checked against its official source on 2026-11-15. The link test in `test_reference_library.py` now also allows the one link to `frontend-stack-selection.md`.

Parent commits: `Lottie` and `Rive` in the enhancement guide's route sentence (`e73c11ed`); version surfaces (`95b0d60f`).

### Review And Repair

Review of `95b0d60f` against `b733a50b`: three parallel protected read-only reviews (`run_gpt_review.py`, gpt-6.1-sol, effort high, git-free packet from `review_input.py`).

- Stack motion layer: pass, no finding. The reviewer noted the committed tests covered the Frontend section only; a Mobile/Desktop test was added (`f1ee4b5b`).
- Motion routes and generated media: pass, no finding.
- Catalog: one blocking finding, three linked URLs not registered in `sources.md`; registered (`1ffd7cd7`).

The first matrix, at `95b0d60f`, failed one step: `test_native_stack_styling.py` in the design-system suite required the stack template's Mobile/Desktop layers to equal the checker's required layers, and the template now shows the optional `Motion` row. The writers' focused checks did not run that suite. The test now allows the optional row and the required set is unchanged (`0050dd6b`).

The three follow-up commits were not re-reviewed: two test files and three registry lines.

M1 could not read the client-rendered sites of Recharts, visx, TanStack Table and Ark UI or the LottieFiles Developer Portal and used their repositories and npm metadata; the catalog says so. Rive and LottieFiles plan costs, the Compose animation license and per-API SwiftUI OS versions are listed as unverified in the catalog.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Motion layer, routes, generated media, catalog (0.82.0 candidate) | Accepted Scope above | `b733a50b..1ffd7cd7`, 13 commits on `ui-motion-and-libraries` | Matrix at `1ffd7cd7`: all nine steps exit 0 (`task/ui-motion-and-libraries/matrix-1ffd7cd7/summary.txt`). An earlier run at `95b0d60f` failed the design-system step; see Review And Repair. Push, PR, tag, install and consumer re-pin remain |

## Results And Remaining Work

Matrix at `1ffd7cd7` against base `7e1f1af4` (`python skills/delivery-harness/scripts/ci_test_shards.py matrix --base 7e1f1af4 --log-dir task/ui-motion-and-libraries/matrix-1ffd7cd7 --workers 8`, with `PDH_REQUIRE_BROWSER_TESTS=1`): skill spec, pyflakes, docs weight, harness (646 s), golden path, product (467 tests), ui (602 tests), design-system (222 tests) and the diff check all exit 0; result `pass`. The base is `main`, so the run covers both stacked rounds. The summary's `dirty: yes` is the untracked `task/` directory. The run was local; CI has not run because nothing is pushed.

The run at `95b0d60f` is kept at `task/ui-motion-and-libraries/matrix-95b0d60f/`: eight steps exit 0 and design-system exit 1, result `fail`.

Docs weight against v0.80.0 at `1ffd7cd7`, both rounds together: `ui-design-builder` +2,238 words, `delivery-harness` +1,763, `product-definition-builder` +462, total +4,463. Of that, 0.81.0 accounts for +1,989. The ratchet is visibility only.

Open:

- This branch stacks on `ui-reference-driven-design`, which is not published. It lands after 0.81.0 or together with it.
- No product has used the `motion` row, a `Lottie` or `Rive` route, or the generated-media recipe yet.
- The recipe names the Higgsfield MCP from its tool list as read on 2026-11-15; no asset was generated to test it.
- `fix/agentkiosk-ui-compiler-contract` (`31edbcf4`) is still local and unmerged and also edits `check_ui_design_contract.py`, in a different place.
- Three worker worktrees of this round under `~/.t3/worktrees/product-delivery-harness/` hold only commits already on this branch. Removal waits for the owner.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / ui-motion-and-libraries / 1ffd7cd7 plus this record commit / task/ untracked
Stage and skill: source maintenance, direct route (no PLAN/RUN)
Inputs consumed (path + hash or revision): ui-reference-driven-design b733a50b; task/ui-motion-and-libraries briefs; Higgsfield MCP model list read 2026-11-15; official sources registered in option-library/sources.md
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): not run; this source repository omits the consumer template sections by design, and no Harness skill workflow was invoked
Approvals in force (gate, owner, date, candidate): owner instruction 2026-11-15 to run this as a separate multi-agent round; local commits only
Done and verified (command, exit code): ci_test_shards.py matrix --base 7e1f1af4 at 1ffd7cd7 (exit 0, result pass); prepare_release.py --check (exit 0)
Remaining: publish 0.81.0 first or both together; push and PR to main; tags v0.81.0 and v0.82.0; install; consumer re-pin
Blocked / waiting (gate name or owner decision): owner decision to publish 0.81.0 and this branch
Next action (one command or one owner decision): owner names the SHAs and how far to publish
Next owner (skill or human): human
```
