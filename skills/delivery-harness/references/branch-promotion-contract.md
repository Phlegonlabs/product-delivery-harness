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
RUNs pinned before 0.63 follow [legacy pins](legacy-pins.md#branch-protocols-before-063).

## Managed RUN Archive Before Promotion

At RUN close, candidate C is complete local work only. On that same resolved run branch, the parent reviews the dry run and applies `scripts/archive_run.py` with `--expected-main <full SHA>` and `--main-ref refs/heads/main` or `refs/remotes/<remote>/main`. `--apply` refuses missing or mismatched bindings, protected or detached branches, and a branch that does not match the RUN integration branch. It moves the coordination set without deleting it and never moves anything under `docs/product/`; it does not authorize a commit, push, promotion, or cleanup.

For Harness 0.38+, `archive_run.py --apply` writes closed `ARCHIVE_RECEIPT.json` in the archive.
The receipt binds every pre-move source, C, branch, and observed `main`.
A failure preserves partial moves for parent-led recovery.
Empty optional directories are skipped because the receipt inventories regular files only.
Commit only repository bookkeeping as A.
Revalidate the archived PLAN/RUN, receipt, destinations, deterministic `docs/DOCUMENTS.md`, absent live sources, and unchanged outside paths.
For separately authorized publication, follow [Archive publication](trusted-host-publication.md).
The parent pushes A only after the owner's exact instruction naming the SHA and branch.
Never use force.
Read back the remote ref and record it in the Epic.
The archived RUN grants nothing.

A inherits C's review, security and gate evidence only after exact receipt-bound C..A archive verification passes.
Only receipt-listed coordination/evidence moves, optional generated `docs/tasks.md`, the deterministic `docs/DOCUMENTS.md` update and `ARCHIVE_RECEIPT.json` may differ.
Every destination must match its receipt hash; preserved evidence must match C, and all other paths stay unchanged.
`push_archived_candidate.py prepare` proves direct C-to-A parentage, inventories, hashes and this allowlist.
Any product-path change or other difference makes A a new candidate.
Retain C's exact reviewed SHA and each result's original execution origin beside the archive proof.
Inherited evidence is never a fresh review, security execution or CI run at A.

## Candidate Gate

Archive read-back uses a fresh non-repository Git process. A private endpoint uses the machine's own credential helper.

Candidate gates start only after the candidate SHA (A for a managed RUN; the fixed commit for a direct change) has passed every applicable task, integration, build/typecheck/test, E2E, UI, migration, security, and complete-diff gate. The checkout must be clean and the candidate must descend from the frozen PLAN base. A dirty checkout, uncommitted fix, missing required result, stale review, SHA mismatch, or non-fast-forward ancestry blocks promotion. Candidate-preview evidence binds its own immutable candidate SHA; it never substitutes for protected-branch evidence or advances the PLAN base.

Harness 0.38+ RUNs never use `integration_push`; that RUN state remains legacy read compatibility only. A post-archive read-back proves only exact A at the run ref. Archival grants no push, and the read-back grants no `main` update.

When the product needs internal deployed verification before production, deploy or expose an isolated non-production environment from the exact candidate branch or immutable candidate SHA. Use separate URLs, resources, data, secrets, auth, and payment modes. Preview acceptance is deployed-SHA readback plus migration and the smoke of the primary journey. Record the deployed candidate SHA and run those checks there. Responsive, accessibility and visual evidence binds by SHA from the candidate review; do not recapture it in the preview. A preview build start, successful upload, green check from another SHA, or owner statement is not a PASS.

A repair creates a new committed candidate and invalidates the prior candidate, security, deployment, and UI evidence. Repeat archival bookkeeping if the repair changes the live coordination set. Verify the new exact SHA with the checks the repair invalidated.

## Post-A Candidate Or Preview Failure

Once A is archived or published, its history and evidence are immutable. A failed candidate gate, preview deployment, smoke check, or other post-A result never amends A, rewrites the run branch, or edits the archived RUN. Record the failure and use the correction-continuation exception: on the same non-default run branch, create a fresh PLAN/RUN from exact A, import the prior verified scope plus the bounded repair, retain the required branch policy and original frozen provenance, and require new execution/action grants. The new PLAN carries exactly one frozen `prior archive candidate` source: its location is A's archived `ARCHIVE_RECEIPT.json`, `source_revision` is exact A, and `content_sha256` matches that blob; retain the failed-gate evidence as a historical input. The archive validator—not a PLAN row alone—proves the receipt, exact A parentage, and A-to-C2 ancestry. Execute and review the repair until replacement closeout candidate C2 passes; archive C2 on that continuation branch with a new stamp as archive-only A2. Revalidate A2, then repeat publication, candidate gates, and exact-SHA promotion path. A2 is a new lineage; it never reuses A's request or history. This exception changes the continuation base; it does not waive the branch policy, architecture marker, or protected-branch rules.

## Promote To Main

Archive and publication prove candidate ancestry from the frozen PLAN base.
Archive creation also binds its separately observed main SHA; later main movement requires fresh promotion reconciliation.
Run-branch publication and protected-main landing are separate actions. Publication is required only when Preview builds from the remote branch.
Retain the publication read-back record; it never authorizes protected-main landing.

One owner release instruction may name archive, publication, preview, exact-SHA promotion and deployment together. Record each grant from that statement and do not re-ask; stop only on drift or a failed gate. Deletion and cleanup stay separate grants.

Promotion to main requires all these conditions:

1. The fixed candidate passes every required local, security and applicable isolated Preview gate at its exact SHA.
2. Before deployable push/CI connection or main promotion, observe actual protection for the exact repository and ref.
   The non-secret readback names the host capability, ruleset/review policy, required checks, checked time, and evidence. The word `protected` in a source document is not setup proof.
   Do not push, force, or delete a protected branch to test protection, and never claim that this source edit configured it.
3. Preview evidence records the PR or branch, immutable deployment identity, observed URL, deployed SHA and acceptance result.
4. Fresh remote observation matches the recorded main pre-state and proves candidate ancestry from the frozen base.
5. Separate action-time authorization names main, remote and exact candidate SHA. Preview or run-branch authority never covers production.
6. Use the required PR or merge-queue mechanism. A direct authorized update must be a fast-forward to that exact SHA.
7. Fetch and read back main. If the server creates SHA S, require its tree to equal the verified candidate tree; S then inherits the candidate's evidence with its original origin.
8. A different tree is a new candidate: verify it as an exact SHA before promotion or release completion.
9. Verify the production deployment and required smoke against the actual main SHA, independently of Preview acceptance.

A moving branch Preview URL is not immutable evidence. Record the fixed deployment URL or identity alongside the Git SHA.
A changed tree, repaired code or configuration invalidates earlier exact-SHA evidence.
Only receipt-verified archive A and provider-created tree-equal main S use the inheritance exceptions defined here.
Record S's observed SHA, exact tree-equality proof and original candidate/result identities.
Do not repeat the full suite or security review solely because the server assigned tree-equal S a new SHA.
Never relabel inherited candidate, security or CI results as fresh executions at S.
A different tree is a new candidate and needs fresh applicable checks and exact-SHA security review.
Repair a failed landing through a new candidate and reviewed PR; never force-push or rewrite protected history.
Hosted-browser production verifies deployed SHA and smoke; parity capture there is optional. Native, extension and desktop targets use their platform evidence.
Activation readiness, outcome review and SEO keep their separate post-production gates and authorization.
Separately authorized Activation preparation cannot claim release readiness.

## Protected Branches

Main is the permanent protected production branch. New flow neither creates nor requires development.
Existing development branches remain protected from RUN integration, publication and cleanup, including old or wildcard grants.
Before a deployable remote connection or landing, prepare actual protection and read it back as condition 2 of Promote To Main requires. A written intention does not prove that the host enforces it.
Removing a policy requirement does not authorize deleting branches or their data.

## Outcome And Required Evidence

A completed new release has a reviewed candidate, exact-version Preview acceptance when applicable, verified main landing and separate production read-back.
For a managed RUN, candidate A remains the archive-only child of C. Report:

- delivery kind, temporary branch, protocol, frozen base and candidate SHA;
- local checks, independent review and Preview deployment identity, URL, SHA and acceptance;
- main pre-state, authorization, ancestry, landing SHA and read-back;
- production build/SHA, smoke and any activation or outcome handoff.

Unexpected remote movement, divergence, failed gates or mismatched deployments stop dependent operations.
Preserve evidence and reconcile explicitly; never force-push or silently rewrite history.
