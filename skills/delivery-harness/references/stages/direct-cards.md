# Direct Route Cards

Use these cards on the direct route, after the System Review And Route records `Route: direct`. Every direct task runs Card D1. An `initial_delivery` adds Card D2. A task that changes UI adds Card D3. A card and the contracts it names are the required reading for that task; read another contract only when its trigger fires or a command fails. Cards add no rule. When a card and a contract disagree, the contract wins.

## Card D1: Direct Delivery

1. Inspect the bounded component and relevant instructions. Record the UI-impact classification; `none` needs no UI reading, and any other value adds Card D3.
2. For a `product-definition-builder` package, verify its Product Definition Approval and Stack Decision Checkpoint plus the applicable self-review and UI handoff under `references/pre-delivery-self-review.md`; then implement with one writer or a Direct Fan-Out (`references/direct-fan-out.md`), under `references/delegation-contract.md`. Agent policy designates the UI writer; preserve its complete design inputs, required skills and independent acceptance. When feature files exist, render the acceptance register (`scripts/render_delivery_acceptance.py`) and record its hash before implementing.
3. Probe the toolchain, browser and reviewer route once (a failed row is an `environment` block), then run focused checks selected from changed files, security tests included.
4. Review the complete diff and run `git diff --check`.
5. Create an authorized local commit when requested.
6. Dispatch one review point on that SHA: read-only calls launched together, one per lens the diff needs: code; security, with `references/security-review.md` loaded; visual, when UI changed, with a real browser and one Final UI Acceptance. The parent merges the results into one finding set of blocking findings and non-blocking notes. The security lens applies to every executable diff (`references/verification-gates.md#review-topology`); a docs-only diff records `security: not_applicable (<reason>)` with the changed path list, and an executable diff without it is `UNVALIDATED`, not PASS. Final validation may overlap it.
7. When the review returns blocking findings, make one consolidated repair, then present the focused verifier PASS at the new head before one targeted re-check of the prior blocking findings and the repair range (`references/gen-verify-correct.md`). After the re-check, every remaining defect enters the Isolated Repair Protocol (`references/verification-gates.md#isolated-repair-protocol`).
8. Perform only remaining authorized Git actions; for promotion, read `references/branch-promotion-contract.md#candidate-gate` and `references/branch-promotion-contract.md#promote-to-main`.

For unproven cross-layer dependencies, apply Early Journey And Engineering Evidence (`references/execution-task-decomposition.md#early-journey-and-engineering-evidence`) within existing tasks and checks.

## Card D2: Initial Product

Read `references/initial-product-foundations.md` and order prerequisites before dependent features. The Surface Catalog (`references/surface-catalog.md`) lists each surface class's required early missions.

Implement local hooks first; record fixed-build external setup as separately authorized action rows from `references/external-setup.md` in `docs/DEPLOYMENT.md`; deployment operations stay separate.

## Card D3: UI Change

Before any frontend dispatch, apply `references/frontend-visual-inputs.md` to the actual author task. Read `references/ui-implementation-contract.md` before UI implementation or review and obey it, including rule-8 UI-impact classification and same-change doc updates. The UI Implementation Contract section of `SKILL.md` summarises who owns compilation, conformance and Final UI Acceptance.

A text-only markup/style review cannot claim a visual PASS or close a required visual gate.
