# EPIC-keyword-map: research search demand before the PRD and let page titles change without a PRD delta

Status: implemented and verified on local branch `keyword-map` (2026-11-17); not pushed, no version bump, not installed
Design workflow: enhancement
UI impact: none.

## Problem And Baseline

The owner (2026-11-17) wants keyword and search-ranking research done before the PRD, and wants to keep rewriting copy against tracked keywords afterwards. The order was reversed:

- The PRD required each route's `<title>` and meta description and listed discovery surfaces, with no demand research before they were written.
- `growth-review` planned query clusters only in `pre_launch` mode, after a launch window was approved, and sent new pages back as PRD deltas.
- A title or description rewrite counted as a PRD wording change, which also reached the UI review.

The owner chose a document produced by `growth-review` over a sixth skill. Baseline: `main` `d1e25594` (v0.87.0).

## Accepted Scope

- K1 `growth-review` mode `demand_research`, run before the Product Definition is drafted, for a product with a public search surface (public web pages or a store listing).
- K2 Its one output, `docs/product/keyword-map.md`, from `KEYWORD_MAP.template.md`: Scope, Clusters with stable `KW-*` IDs, Not pursued, Content fields, Change log.
- K3 Evidence before a site exists: labels `observed`, `estimated`, `hypothesis`; no invented volume, rank or competitor fact; account-bound providers only with recorded access.
- K4 The Product Definition runs the mode as a required dependency before the page list is drafted; Discovery Surface rows and `SEO metadata` lines cite `KW-*`; `Keyword map: n/a` or `not run` is recorded with its reason. No approval gate.
- K5 A route's `<title>` and meta description are content fields. The PRD keeps the launch values and limits; the map holds the current values. A rewrite inside the limits that keeps the cluster is a content change with no PRD delta and no UI review.
- K6 The Day 7 and Day 30 readbacks compare each `KW-*` with data and return content-field rewrites and structural PRD delta candidates as two lists.

Not done, for a later round: continuous rank tracking, automatic rewrite proposals, provider integrations, rewriting headings or body copy. The README sections and version entries belong to the release change.

## Execution Record

Two bounded writers on Claude Sonnet 5.5 (claude-t3-direct, effort high) in separate worktrees; the parent (Claude Fable 5.2, high) wrote the spec, integrated by cherry-pick and reviewed the unified diff.

- K1 writer `222d2d82`: the mode, the evidence rules, the readback, the template and its test. It kept the existing label `observed` where the spec said `measured`.
- K2 writer `e0796c36`: the Product Definition step, the output contract, the content-change boundary.

## Review And Repairs

One parent review of the unified diff. Repairs, all by the parent:

- The delivery rules compared the rendered title with the PRD record and classed any wording change as a structure delta. They now compare with the map's current value when the map lists the route, and a rewrite logged there is a content change (`ui-implementation-contract.md`, `verification-gates.md`, `design-input-updates.md`).
- `artifact-lifecycle.md` lists the keyword map among the published product documents; `MODULE_PRD.template.md` carries the limits and `KW-*` on its `SEO metadata` line.
- Product Definition Approval links the keyword map only when one exists.
- Two links added by the parent pointed at an anchor inside the PRD template block; the harness suite caught them and they now point at the PRD refinement reference.

Left as is: `PROGRAM_PRD.template.md` and `PRD_DELTA.template.md` carry no `KW-*` example; the `DOCUMENTS` template has no row for the map, as it has none for `market-research.md`.

## Verification

Logs under `task/keyword-map/verify/`:

- `product-definition-builder` suite: 467 tests passed.
- `ci_test_shards.py run --suite harness --workers 4` on `7f106504`: 128 of 129 modules passed; `test_markdown_anchor_links.py` failed on the two links above. After the repair that module and the document-pinning modules passed on `c82d3f51`.
- `check_skill_spec.py` and `git diff --check`: clean.

The full matrix command and CI have not run; they belong to the release candidate.

## Handoff

Nothing is pushed. This branch and `ui-review-one-pass` both start from `d1e25594`, change no file in common and merge cleanly, so they can be published separately in either order. A project uses the mode on its next Product Definition or PRD delta that adds public pages.
