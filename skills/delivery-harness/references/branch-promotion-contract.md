# Main-Only Promotion Contract

Use this contract after a direct change or managed RUN has produced one fixed, locally verified candidate SHA. For a Harness 0.38 managed RUN, closeout candidate C is local-only; archive-only child A becomes the release candidate. The archived RUN remains immutable at C. Publishing A to its run branch and promoting A to `main` are separate post-RUN actions with separate action-time authorization.

The repository has two branch roles:

- a non-default run or feature branch holds one candidate and remains the managed RUN integration branch; and
- `main` is the only persistent protected branch and the production branch.

The retired branch name `development` is not a release source or integration target. Do not create or restore it as part of ordinary delivery. Non-production environments, including a platform environment named `development`, build from the exact candidate branch or immutable candidate SHA and remain separate from production resources.

Do not edit or commit directly on `main`. Promote an exact already-committed SHA. Every fetch, branch creation, ref update, merge, push, external test, and branch deletion keeps its ordinary authorization boundary.

## Delivery Kind And Base

Classify the work as `initial_delivery`, `enhancement`, or `needs_owner_decision` for product and release semantics. Both initial delivery and enhancements fetch and start their non-default run branch from the current observed remote `main` head. Record the classification, observed `main` SHA, complete run-branch name, and any unresolved earlier candidate. Never use a stale local default branch or a retired `development` ref as the base.

## Managed RUN Archive Before Promotion

At RUN close, candidate C is complete local work only. On that same resolved run branch, the parent reviews the dry run and applies `scripts/archive_run.py` with `--expected-main <full SHA>` and `--main-ref refs/heads/main` or `refs/remotes/<remote>/main`. `--apply` refuses missing or mismatched bindings, protected or detached branches, and a branch that does not match the RUN integration branch. It moves the coordination set without deleting it; it does not authorize a commit, push, promotion, or cleanup.

For Harness 0.38, `archive_run.py --apply` also requires absolute external `--anchor-out`. It writes closed `ARCHIVE_RECEIPT.json` in the archive and a matching immutable anchor outside the checkout, binding every pre-move source, C, branch, and observed `main`; failure rolls back. Empty optional directories are deliberately skipped because the receipt inventory is regular-file-only. An interrupted apply leaves a durable `.ARCHIVE_TRANSACTION.json`; its moves are restricted to the closed PLAN/RUN/optional coordination allowlist and receipt-derived destination mapping before recovery opens a source. A transaction-wide DOCUMENTS destination lock and inode/content version token serialize compliant writers, while the platform exchange/backup primitive validates displaced bytes and restores or retains recovery artifacts on mismatch. Run `python skills/delivery-harness/scripts/archive_run.py --repo-root <checkout> --recover <archive>` before retrying, and recovery preserves any path whose identity or content is no longer transaction-owned. Commit only repository bookkeeping as A. Revalidate the archived PLAN/RUN, receipt, anchor, destinations, deterministic `docs/DOCUMENTS.md`, absent live sources, and unchanged outside paths. If separately authorized, `push_archived_candidate.py` uses `--archive-anchor <same path>` and keeps its request, pre-side-effect attempt, receipt, and trusted-host execution evidence outside the checkout as one closed lifecycle (the request, pre-side-effect attempt, and receipt outside the checkout). The request binds the exact canonical non-secret push URL, the machine-installed policy ID/hash/principal, and an OS-managed verifier path/hash; it returns `PENDING_TRUSTED_HOST_PUBLICATION` with a URL-only no-force argv before the receipt is written. It never treats caller-supplied prose or a ticket/ref string as authority and never invokes `git push`. A trusted host must independently reload the immutable request, revalidate authorization and endpoint immediately before the side effect with sanitized config, execute the exact URL, and write detached signed execution evidence. Recovery verifies that evidence and the exact A read-back before closing the receipt. Agents and the local executor must not run the emitted argv without that trusted boundary. The archived RUN grants nothing.

## Candidate Gate

Archive read-back uses a fresh non-repository Git process with system/global config disabled. Private endpoints that need credential helpers remain a trusted-host responsibility.

The archive anchor deterministically names the v3 publication receipt as `<anchor-stem>-publication-receipt.json`; correction lineage treats that receipt and its signed execution evidence as the objective publication state.

The external authorization names the administrator-installed machine policy ID/hash/principal (HKLM `SOFTWARE\ProductDeliveryHarness\ArchivePushAllowedSigners` on Windows or `/etc/product-delivery-harness/archive-push.allowed_signers` on POSIX) and the OS-managed verifier hash. If the policy is absent, install it through host administration; the local agent cannot choose a fake verifier or trust policy.

Promotion starts only after the candidate SHA (A for a managed RUN; the fixed commit for a direct change) has passed every applicable task, integration, build/typecheck/test, E2E, UI, migration, security, and complete-diff gate. The checkout must be clean and the candidate must descend from the recorded remote `main` base. A dirty checkout, uncommitted fix, missing required result, stale review, SHA mismatch, or non-fast-forward ancestry blocks promotion.

Harness 0.38 RUNs never use `integration_push`; that RUN state remains legacy read compatibility only. A post-archive branch receipt proves only exact A at the run ref. Archival grants no push, and the receipt grants no `main` update.

When the product needs internal deployed verification before production, deploy or expose an isolated non-production environment from the exact candidate branch or immutable candidate SHA. Use separate URLs, resources, data, secrets, auth, and payment modes. Record the deployed candidate SHA and run the required smoke, migration, integration, responsive, accessibility, and visual checks there. A preview build start, successful upload, green check from another SHA, or owner statement is not a PASS.

A repair creates a new committed candidate and invalidates the prior candidate, security, deployment, and UI evidence. Repeat archival bookkeeping if the repair changes the live coordination set, then repeat the complete candidate gate and any candidate-environment verification on the new exact SHA.

## Post-A Candidate Or Preview Failure

Once A is archived or published, its history and evidence are immutable. A failed candidate gate, preview deployment, smoke check, or other post-A result never amends A, rewrites the run branch, or edits the archived RUN. Record the failure and use the correction-continuation exception: on the same non-default run branch, create a fresh PLAN/RUN from exact A, import the prior verified scope plus the bounded repair, and require new execution/action grants. The new PLAN carries exactly one frozen `prior archive candidate` source: its location is A's archived `ARCHIVE_RECEIPT.json`, `source_revision` is exact A, and `content_sha256` matches that blob; retain the external anchor and failed-gate evidence as historical inputs. Execute and review the repair until replacement closeout candidate C2 passes; archive C2 on that continuation branch with a new stamp and external anchor as archive-only A2. If A was published, A2 publication accepts only a freshly observed remote pre-state equal to A; if A was not published, the pre-state must remain absent. Revalidate A2, then repeat the trusted-host publication, candidate gates, and exact-SHA promotion path. A2 is a new lineage; it never reuses A's anchor, request, attempt, receipt, or history. This exception is not a normal initial/enhancement branch cut from `main`.

## Promote To Main

Promotion to `main` is allowed only when all of these are true:

1. A fresh fetch proves the remote `main` head still equals the recorded candidate base.
2. The candidate intended for production descends from that exact remote `main` head.
3. Every required local and candidate-environment gate passes on the exact candidate SHA.
4. The `main` update is a fast-forward to that exact SHA. A merge, rebase, squash, conflict repair, generated-file change, or server-created commit changes the candidate and invalidates earlier exact-SHA evidence.
5. Separate action-time authorization names `main`, the remote, and the exact candidate SHA. Authorization for the run branch, deployment, or a future conditional push does not cover it.
6. Push without force, fetch/read back remote `main`, and require it to equal the authorized candidate SHA.
7. Verify production read-only against exact A and run the surface-specific smoke. Hosted-browser UI uses `parity_capture.py` against the production URL. Browser extensions use extension automation; native and desktop targets use platform UI tests or labeled manual device captures. Every capture binds the typed target, artifact, SHA, authority hashes, and production evidence separately from candidate PASS. Only after production verification may `product-activation`, outcome review, and SEO run under their own gates.

If branch protection requires a pull request, merge queue, or server-created commit and cannot preserve the candidate SHA, follow that mechanism only under its own authorization after the candidate gate passes. Fetch the resulting remote `main` SHA immediately, require its tree to equal the verified candidate tree, and treat that server-created SHA as the release candidate. Rerun the complete required suite and fresh security review on that exact remote `main` SHA before tagging, publishing a release, deleting the retired branch, or claiming completion. A failure is repaired by a new candidate branch and PR; never force-push or rewrite `main` to erase the failed landing.

## Retired Development Branch

An existing local or remote `development` branch is historical cleanup, not part of promotion. Removing it requires a separate explicit deletion instruction naming the exact ref. Before deletion, verify that its head is an ancestor of the promoted `main` SHA and that no open RUN, worktree, deployment source, or unresolved candidate still depends on it. Delete without force, read back that the ref is absent, and preserve the final SHA in the delivery evidence. Never delete a diverged or still-referenced branch to make the repository appear main-only.

## Outcome And Required Evidence

A completed initial delivery or enhancement leaves the exact verified candidate at remote `main`; for a managed RUN, that candidate is archive-only commit A. Any non-production environment evidence names the candidate branch/SHA rather than another persistent branch. Report:

- delivery kind, run branch, candidate SHA, and candidate-gate results;
- observed remote `main` before and after promotion;
- candidate-environment deployment SHA and smoke results when applicable;
- `main` authorization source, fast-forward/ancestry proof, push, and read-back;
- production deployment SHA and smoke result when applicable;
- post-production activation, outcome-review, and SEO readiness/evidence results when applicable;
- any separately authorized retired-branch deletion with its final ancestor SHA and absent-ref read-back.

Unexpected remote movement, failed ancestry, non-fast-forward state, different server-created SHA, failed gate, or referenced retired branch stops the operation. Preserve the evidence and ask for an explicit reconciliation plan; never force-push or silently rewrite history.
