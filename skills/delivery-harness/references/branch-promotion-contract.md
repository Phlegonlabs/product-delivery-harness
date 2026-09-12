# Main-Only Promotion Contract

Use this contract after a direct change or managed RUN has produced one fixed, locally verified candidate SHA. The RUN authorization ledger governs work through an optional push of its own integration branch. Promotion to `main` follows that RUN; it never inherits or reuses a RUN push grant.

The repository has two branch roles:

- a non-default run or feature branch holds one candidate and remains the managed RUN integration branch; and
- `main` is the only persistent protected branch and the production branch.

The retired branch name `development` is not a release source or integration target. Do not create or restore it as part of ordinary delivery. Non-production environments, including a platform environment named `development`, build from the exact candidate branch or immutable candidate SHA and remain separate from production resources.

Do not edit or commit directly on `main`. Promote an exact already-committed SHA. Every fetch, branch creation, ref update, merge, push, external test, and branch deletion keeps its ordinary authorization boundary.

## Delivery Kind And Base

Classify the work as `initial_delivery`, `enhancement`, or `needs_owner_decision` for product and release semantics. Both initial delivery and enhancements fetch and start their non-default run branch from the current observed remote `main` head. Record the classification, observed `main` SHA, complete run-branch name, and any unresolved earlier candidate. Never use a stale local default branch or a retired `development` ref as the base.

## Candidate Gate

Promotion starts only after the candidate SHA has passed every applicable task, integration, build/typecheck/test, E2E, UI, migration, security, and complete-diff gate. The checkout must be clean and the candidate must descend from the recorded remote `main` base. A dirty checkout, uncommitted fix, missing required result, stale review, SHA mismatch, or non-fast-forward ancestry blocks promotion.

If the managed RUN uses `integration_push`, push only its own run branch under the existing exact RUN grant and read that branch back. That action does not authorize `main`.

When the product needs internal deployed verification before production, deploy or expose an isolated non-production environment from the exact candidate branch or immutable candidate SHA. Use separate URLs, resources, data, secrets, auth, and payment modes. Record the deployed candidate SHA and run the required smoke, migration, integration, responsive, accessibility, and visual checks there. A preview build start, successful upload, green check from another SHA, or owner statement is not a PASS.

A repair creates a new committed candidate and invalidates the prior candidate, security, deployment, and UI evidence. Repeat the complete candidate gate and any candidate-environment verification on the new SHA.

## Promote To Main

Promotion to `main` is allowed only when all of these are true:

1. A fresh fetch proves the remote `main` head still equals the recorded candidate base.
2. The candidate intended for production descends from that exact remote `main` head.
3. Every required local and candidate-environment gate passes on the exact candidate SHA.
4. The `main` update is a fast-forward to that exact SHA. A merge, rebase, squash, conflict repair, generated-file change, or server-created commit changes the candidate and invalidates earlier exact-SHA evidence.
5. Separate action-time authorization names `main`, the remote, and the exact candidate SHA. Authorization for the run branch, deployment, or a future conditional push does not cover it.
6. Push without force, fetch/read back remote `main`, and require it to equal the authorized candidate SHA.
7. Verify the production deployment read-only against that exact SHA and run the required production smoke. For a UI-bearing candidate the production smoke includes a parity re-capture: `scripts/parity_capture.py --plan <PLAN.md> --reference <approved design-reference HTML> --base-url <production URL> --out docs/goal/evidence/production`, judged against the same board and tolerance as the pre-merge loop, with its evidence recorded separately from candidate-environment PASS. Production PASS is separate from candidate-environment PASS.

If branch protection requires a pull request, merge queue, or server-created commit and cannot preserve the candidate SHA, follow that mechanism only under its own authorization after the candidate gate passes. Fetch the resulting remote `main` SHA immediately, require its tree to equal the verified candidate tree, and treat that server-created SHA as the release candidate. Rerun the complete required suite and fresh security review on that exact remote `main` SHA before tagging, publishing a release, deleting the retired branch, or claiming completion. A failure is repaired by a new candidate branch and PR; never force-push or rewrite `main` to erase the failed landing.

## Retired Development Branch

An existing local or remote `development` branch is historical cleanup, not part of promotion. Removing it requires a separate explicit deletion instruction naming the exact ref. Before deletion, verify that its head is an ancestor of the promoted `main` SHA and that no open RUN, worktree, deployment source, or unresolved candidate still depends on it. Delete without force, read back that the ref is absent, and preserve the final SHA in the delivery evidence. Never delete a diverged or still-referenced branch to make the repository appear main-only.

## Outcome And Required Evidence

A completed initial delivery or enhancement leaves the exact verified candidate at remote `main`; any non-production environment evidence names the candidate branch/SHA rather than another persistent branch. Report:

- delivery kind, run branch, candidate SHA, and candidate-gate results;
- observed remote `main` before and after promotion;
- candidate-environment deployment SHA and smoke results when applicable;
- `main` authorization source, fast-forward/ancestry proof, push, and read-back;
- production deployment SHA and smoke result when applicable; and
- any separately authorized retired-branch deletion with its final ancestor SHA and absent-ref read-back.

Unexpected remote movement, failed ancestry, non-fast-forward state, different server-created SHA, failed gate, or referenced retired branch stops the operation. Preserve the evidence and ask for an explicit reconciliation plan; never force-push or silently rewrite history.
