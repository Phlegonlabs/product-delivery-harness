# Development-To-Main Promotion Contract

Use this contract after a direct change or managed RUN has produced one fixed, locally verified candidate SHA. The RUN authorization ledger governs work through an optional push of its own integration branch. Branch promotion follows that RUN; it never inherits or reuses a RUN push grant.

The repository has three branch roles:

- the run branch holds one candidate and remains the managed RUN integration branch;
- `development` is the persistent internal integration and non-production release branch; and
- `main` is the production branch and repository default branch.

Do not edit or commit directly on `development` or `main`. Promote an exact already-committed SHA. Every fetch, branch creation, ref update, merge, push, or external test action keeps its ordinary authorization boundary.

## Delivery Kind

Classify the work before choosing its base:

- `initial_delivery`: the product has not completed its first production promotion. Start the run branch from the current observed `main` head. `development` may be absent; creating it at the candidate SHA needs exact authorization.
- `enhancement`: the product has completed an initial promotion. Fetch and start the run branch from the current observed `development` head. Before starting, require the last promoted `main` to be an ancestor of `development` and require no unresolved earlier development candidate.
- `needs_owner_decision`: repository history, PRD state, or remote refs do not prove which case applies. Stop before branch creation.

Record the classification and observed remote `main` and `development` SHAs. Never infer `initial_delivery` merely because a local branch is missing.

## Candidate Gate

Promotion starts only after the candidate SHA has passed every applicable local task, integration, E2E, UI, migration, and security gate and the complete diff review. A dirty checkout, uncommitted fix, missing required result, stale review, or SHA mismatch blocks promotion.

If the managed RUN uses `integration_push`, push only its own run branch under the existing exact RUN grant. That action does not authorize `development` or `main`.

## Promote To Development

1. Fetch the remote refs and read back the current `development` and `main` heads without changing them.
2. For `initial_delivery`, require `development` to be absent or to equal the recorded safe base. For `enhancement`, require the observed `development` head to equal the run's recorded base.
3. Require the candidate to descend from the allowed development base. If `development` exists, its update must be fast-forward. Never force-push.
4. Obtain separate action-time authorization naming `development`, the remote, and the exact candidate SHA. A general instruction to finish the project or a prior RUN push grant is insufficient.
5. Push the exact candidate SHA to `development`, then fetch/read back the remote ref and require it to equal that SHA.
6. Deploy or expose the development environment from that exact branch head when the product is deployable.

`development` may temporarily point at a failing candidate while internal verification runs. `main` stays unchanged. A repair creates a new committed candidate, repeats the development promotion and read-back, and restarts every stale internal gate on the new SHA.

## Internal Development Verification

Run the repository's complete internal suite against the exact remote `development` head, not merely the earlier run branch:

- required CI and build/typecheck/test suites;
- fresh code-security review when the candidate changed after the earlier review;
- development-environment migrations and rollback/forward-fix checks;
- deployed smoke and primary E2E journeys;
- browser/native responsive, state, accessibility, and visual evidence when UI is present; and
- external integration sandbox behavior and read-back when applicable.

Record the exact SHA, commands/checks, environment or URL, timestamps, evidence, and PASS/FAIL. A preview build start, successful upload, green check from another SHA, or owner statement is not a PASS.

## Promote To Main

Promotion to `main` is allowed only when all of these are true:

1. A fresh fetch proves remote `development` still equals the internally verified SHA.
2. The verified development SHA equals the candidate intended for production.
3. The current remote `main` head is the recorded expected head and is an ancestor of the verified development SHA.
4. The `main` update is fast-forward to that exact SHA. A merge, rebase, squash, conflict repair, generated-file change, or other operation that creates a different SHA invalidates the development evidence and returns to the development promotion and verification steps.
5. Separate action-time authorization names `main`, the remote, and the exact verified development SHA. Authorization for `development`, the run branch, deployment, or a future conditional push does not cover it.
6. Push without force, fetch/read back remote `main`, and require both remote `main` and `development` to equal the verified SHA.
7. Verify the production deployment read-only against that exact SHA and run the required production smoke. Production PASS is separate from the pre-promotion internal PASS.

If branch protection requires a pull request, merge queue, or server-created merge commit, follow that mechanism only under its own authorization. The resulting SHA must return through development and pass the same internal gates before it can become the production candidate; do not weaken the exact-SHA rule to accommodate the provider.

## First Delivery And Enhancement Outcomes

- A completed `initial_delivery` leaves remote `development` and `main` at the same internally verified SHA, followed by separate development and production environment read-backs.
- A completed `enhancement` first leaves `development` ahead while internal tests run, then fast-forwards `main` to the same verified SHA. At completion the two refs converge again.
- A failed development candidate leaves `main` untouched and remains preserved for diagnosis. Do not reset or delete it automatically.
- Diverged branches, unexpected remote movement, failed ancestry, or a non-fast-forward update stop the promotion. Preserve evidence and ask for an explicit reconciliation plan; never force-push or silently merge around drift.

## Required Evidence

Report:

- delivery kind;
- run branch, candidate SHA, and candidate gate results;
- observed before/after remote SHAs for `development` and `main`;
- development push authorization source and read-back;
- internal development verification bound to the exact SHA;
- main promotion authorization source and fast-forward/ancestry proof;
- main push and remote read-back; and
- development and production deployment SHAs and smoke results when deployable.

Do not claim the project or enhancement is fully delivered until the required branch and environment outcomes are complete, or report the exact pending authorization or failed gate.
