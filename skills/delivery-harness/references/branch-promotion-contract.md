# Candidate Preview And Main Promotion Contract

Use this contract after a direct change or managed RUN has produced one fixed, locally verified candidate SHA. For a Harness 0.38+ managed RUN, closeout candidate C is local-only; archive-only child A becomes the release candidate. The archived RUN remains immutable at C. Publishing A to its run branch and promoting A to `main` are separate post-RUN actions with separate action-time authorization.

New delivery uses two branch roles: a temporary candidate branch and protected production `main`.
PR or branch Preview supplies internal acceptance before main landing. No permanent `development` branch is required.
The `development` release stage names a non-production target, not a Git branch.
Existing `development` branches remain untouched and protected from generic RUN cleanup.

Do not edit or commit directly on protected branches. Promote an exact already-committed candidate.
Every fetch, branch creation, ref update, merge, push, external test, and branch deletion keeps its ordinary authorization boundary.

## Delivery Kind And Base

Classify delivery as `initial_delivery`, `enhancement`, or `needs_owner_decision`.
Harness 0.63+ PLANs use `branch_policy.protocol: main-preview/1` and architecture marker `Release source policy: main-preview/1`.
Both `ordinary` and `hotfix` freeze the observed remote `refs/remotes/<remote>/main` head and its full SHA.
Cut the owner-resolved temporary branch from that base. Never advance the frozen base between waves.
Record unresolved earlier candidates; never substitute a stale local main ref for the observed remote head.

Plan-only validation checks an explicit policy and matching active architecture marker before RUN creation.
An absent RUN is not a historical version pin or execution authority.

## Pinned Historical Delivery

RUNs pinned from 0.59 through 0.62 retain `dual-branch/1` without migration.
Ordinary work freezes remote `development`, lands verified A there, verifies landing SHA S, then separately promotes S to main.
A hotfix freezes main, releases A there, then separately forward-integrates A into current development without losing unrelated work.
Verify the resulting development SHA T and retain its read-back.
Pre-0.59 pins retain their recorded candidate/main contract. Malformed pins never establish historical compatibility.
Historical corrections retain their original runtime pin and frozen policy; a new correction source cannot authorize a protocol downgrade.
Never delete existing main or development branches through a RUN cleanup grant.

## Managed RUN Archive Before Promotion

At RUN close, candidate C is complete local work only. On that same resolved run branch, the parent reviews the dry run and applies `scripts/archive_run.py` with `--expected-main <full SHA>` and `--main-ref refs/heads/main` or `refs/remotes/<remote>/main`. `--apply` refuses missing or mismatched bindings, protected or detached branches, and a branch that does not match the RUN integration branch. It moves the coordination set without deleting it; it does not authorize a commit, push, promotion, or cleanup.

For Harness 0.38+, `archive_run.py --apply` also requires absolute external `--anchor-out`. It writes closed `ARCHIVE_RECEIPT.json` in the archive and a matching immutable anchor outside the checkout, binding every pre-move source, C, branch, and observed `main`; failure rolls back. Empty optional directories are deliberately skipped because the receipt inventory is regular-file-only. An interrupted apply leaves a durable `.ARCHIVE_TRANSACTION.json`; its moves are restricted to the closed PLAN/RUN/optional coordination allowlist and receipt-derived destination mapping before recovery opens a source. A transaction-wide DOCUMENTS destination lock and inode/content version token serialize compliant writers, while the platform exchange/backup primitive validates displaced bytes and restores or retains recovery artifacts on mismatch. Run `python "<delivery-harness-skill-root>/scripts/archive_run.py" --repo-root <checkout> --recover <archive>` before retrying, and recovery preserves any path whose identity or content is no longer transaction-owned. Commit only repository bookkeeping as A. Revalidate the archived PLAN/RUN, receipt, anchor, destinations, deterministic `docs/DOCUMENTS.md`, absent live sources, and unchanged outside paths. If separately authorized, `push_archived_candidate.py` uses `--archive-anchor <same path>` and keeps its request, pre-side-effect attempt, receipt, and trusted-host execution evidence outside the checkout as one closed lifecycle (the request, pre-side-effect attempt, and receipt outside the checkout). The request binds the exact canonical non-secret push URL, the machine-installed policy ID/hash/principal, and an OS-managed verifier path/hash; it returns `PENDING_TRUSTED_HOST_PUBLICATION` with a URL-only no-force argv before the receipt is written. It never treats caller-supplied prose or a ticket/ref string as authority and never invokes `git push`. A trusted host must independently reload the immutable request, revalidate authorization and endpoint immediately before the side effect with sanitized config, execute the exact URL, and write detached signed execution evidence. Recovery verifies that evidence and the exact A read-back before closing the receipt. Agents and the local executor must not run the emitted argv without that trusted boundary. The archived RUN grants nothing.

## Candidate Gate

Archive read-back uses a fresh non-repository Git process with system/global config disabled. Private endpoints that need credential helpers remain a trusted-host responsibility.

The archive anchor deterministically names the v3 publication receipt as `<anchor-stem>-publication-receipt.json`; correction lineage treats that receipt and its signed execution evidence as the objective publication state.

The external authorization names the administrator-installed machine policy ID/hash/principal (HKLM `SOFTWARE\ProductDeliveryHarness\ArchivePushAllowedSigners` on Windows or `/etc/product-delivery-harness/archive-push.allowed_signers` on POSIX) and the OS-managed verifier hash. If the policy is absent, install it through host administration; the local agent cannot choose a fake verifier or trust policy.

Candidate gates start only after the candidate SHA (A for a managed RUN; the fixed commit for a direct change) has passed every applicable task, integration, build/typecheck/test, E2E, UI, migration, security, and complete-diff gate. The checkout must be clean and the candidate must descend from the frozen PLAN base. A dirty checkout, uncommitted fix, missing required result, stale review, SHA mismatch, or non-fast-forward ancestry blocks promotion. Candidate-preview evidence binds its own immutable candidate SHA; it never substitutes for protected-branch evidence or advances the PLAN base.

Harness 0.38+ RUNs never use `integration_push`; that RUN state remains legacy read compatibility only. A post-archive branch receipt proves only exact A at the run ref. Archival grants no push, and the receipt grants no `main` update.

When the product needs internal deployed verification before production, deploy or expose an isolated non-production environment from the exact candidate branch or immutable candidate SHA. Use separate URLs, resources, data, secrets, auth, and payment modes. Record the deployed candidate SHA and run the required smoke, migration, integration, responsive, accessibility, and visual checks there. A preview build start, successful upload, green check from another SHA, or owner statement is not a PASS.

A repair creates a new committed candidate and invalidates the prior candidate, security, deployment, and UI evidence. Repeat archival bookkeeping if the repair changes the live coordination set, then repeat the complete candidate gate and any candidate-environment verification on the new exact SHA.

## Post-A Candidate Or Preview Failure

Once A is archived or published, its history and evidence are immutable. A failed candidate gate, preview deployment, smoke check, or other post-A result never amends A, rewrites the run branch, or edits the archived RUN. Record the failure and use the correction-continuation exception: on the same non-default run branch, create a fresh PLAN/RUN from exact A, import the prior verified scope plus the bounded repair, retain the required branch policy and original frozen provenance, and require new execution/action grants. The new PLAN carries exactly one frozen `prior archive candidate` source: its location is A's archived `ARCHIVE_RECEIPT.json`, `source_revision` is exact A, and `content_sha256` matches that blob; retain the external anchor and failed-gate evidence as historical inputs. The existing archive and publication validators—not a PLAN row alone—prove the receipt, anchor, publication state, exact A parentage, and A-to-C2 ancestry. Execute and review the repair until replacement closeout candidate C2 passes; archive C2 on that continuation branch with a new stamp and external anchor as archive-only A2. If A was published, A2 publication accepts only a freshly observed remote pre-state equal to A; if A was not published, the pre-state must remain absent. Revalidate A2, then repeat the trusted-host publication, candidate gates, and exact-SHA promotion path. A2 is a new lineage; it never reuses A's anchor, request, attempt, receipt, or history. This exception changes the continuation base; it does not waive the branch policy, architecture marker, or protected-branch rules.

## Promote To Main

Archive and publication prove candidate ancestry from the frozen PLAN base.
Archive creation also binds its separately observed main SHA; later main movement requires fresh promotion reconciliation.
Run-branch publication and protected-main landing are separate actions. Publication is required only when Preview builds from the remote branch.
Retain trusted-host publication receipts and signed evidence; they never authorize protected-main landing.

Promotion to main requires all these conditions:

1. The fixed candidate passes every required local, security and applicable isolated Preview gate at its exact SHA.
2. Preview evidence records the PR or branch, immutable deployment identity, observed URL, deployed SHA and acceptance result.
3. Fresh remote observation matches the recorded main pre-state and proves candidate ancestry from the frozen base.
4. Separate action-time authorization names main, remote and exact candidate SHA. Preview or run-branch authority never covers production.
5. Use the required PR or merge-queue mechanism. A direct authorized update must be a fast-forward to that exact SHA.
6. Fetch and read back main. If the server creates SHA S, require its tree to equal the verified candidate tree.
7. Run the complete required suite and fresh security review on any server-created exact SHA before promotion or release completion.
8. Verify the production deployment and required smoke against the actual main SHA, independently of Preview acceptance.

A moving branch Preview URL is not immutable evidence. Record the fixed deployment URL or identity alongside the Git SHA.
A new candidate, merge, rebase, squash or conflict repair invalidates earlier exact-SHA evidence.
Repair a failed landing through a new candidate and reviewed PR; never force-push or rewrite protected history.
Hosted-browser production uses `parity_capture.py`; native, extension and desktop targets use their platform evidence.
Activation readiness, outcome review and SEO keep their separate post-production gates and authorization.
Separately authorized Activation preparation cannot claim release readiness.

## Protected Branches

Main is the permanent protected production branch. New flow neither creates nor requires development.
Existing development branches remain protected from RUN integration, publication and cleanup, including old or wildcard grants.
Removing a policy requirement does not authorize deleting branches or their data.

## Outcome And Required Evidence

A completed new release has a reviewed candidate, exact-version Preview acceptance when applicable, verified main landing and separate production read-back.
For a managed RUN, candidate A remains the archive-only child of C. Report:

- delivery kind, temporary branch, protocol, frozen base and candidate SHA;
- local checks, independent review and Preview deployment identity, URL, SHA and acceptance;
- main pre-state, authorization, ancestry, landing SHA and read-back;
- production build/SHA, smoke and any activation or outcome handoff;
- for historical dual-branch flow, development landing S or forward-integration SHA T and read-back.

Unexpected remote movement, divergence, failed gates or mismatched deployments stop dependent operations.
Preserve evidence and reconcile explicitly; never force-push or silently rewrite history.
