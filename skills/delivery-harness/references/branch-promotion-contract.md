# Candidate Preview And Main Promotion Contract

Use this contract after a direct change or managed RUN has produced one fixed, locally verified candidate SHA. For a Harness 0.38+ managed RUN, closeout candidate C is local-only; archive-only child A becomes the release candidate. The archived RUN remains immutable at C. Publishing A to its run branch and promoting A to `main` are separate post-RUN actions with separate action-time authorization.

New delivery uses two branch roles: a temporary candidate branch and protected production `main`.
PR or branch Preview supplies internal acceptance before main landing, except for an `initial_delivery`. No permanent `development` branch is required.
The `development` release stage names a non-production target, not a Git branch.

Do not edit or commit directly on protected branches. Promote an exact already-committed candidate.
Every fetch, branch creation, ref update, merge, push, external test, and branch deletion keeps its ordinary authorization boundary.

## Delivery Kind And Base

Classify delivery as `initial_delivery`, `enhancement`, or `needs_owner_decision`.
`initial_delivery` is a product that has never been deployed; its architecture declares `Initial delivery: production-first/1` under `## Release Targets` and may declare only production targets.
`enhancement` is every later delivery; it requires the development target and preview acceptance.
Harness 0.63+ PLANs use `branch_policy.protocol: main-preview/1` and architecture marker `Release source policy: main-preview/1`.
Both `ordinary` and `hotfix` freeze the observed remote `refs/remotes/<remote>/main` head and its full SHA.
Cut the owner-resolved temporary branch from that base. Never advance the frozen base between waves.
Record unresolved earlier candidates; never substitute a stale local main ref for the observed remote head.

Plan-only validation checks an explicit policy and matching active architecture marker before RUN creation.
An absent RUN is not a historical version pin or execution authority.
RUNs pinned before 0.63 follow [legacy pins](legacy/legacy-pins.md#branch-protocols-before-063).

## Managed RUN Archive Before Promotion

At RUN close, candidate C is complete local work only. On that same resolved run branch, the parent reviews the dry run and applies `scripts/archive_run.py` with `--expected-main <full SHA>` and `--main-ref refs/heads/main` or `refs/remotes/<remote>/main`. `--apply` refuses missing or mismatched bindings, protected or detached branches, and a branch that does not match the RUN integration branch. It moves the coordination set without deleting it and never moves anything under `docs/product/`; it does not authorize a commit, push, promotion, or cleanup.

For Harness 0.38+, `archive_run.py --apply` writes closed `ARCHIVE_RECEIPT.json` in the archive.
The receipt binds every pre-move source, C, branch, and observed `main`.
A failure preserves partial moves for parent-led recovery.
Empty optional directories are skipped because the receipt inventories regular files only.
Commit only repository bookkeeping as A.
Revalidate the archived PLAN/RUN, receipt, destinations, deterministic `docs/DOCUMENTS.md`, absent live sources, and unchanged outside paths.
For separately authorized publication, follow [Archive publication](trusted-host-publication.md).
The parent pushes A only after the owner's exact instruction naming the SHA and branch, or a passing check under an [Epic Landing Grant](#epic-landing-grant).
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

One owner release instruction may name archive, publication, preview, exact-SHA promotion and deployment together. Record each grant from that statement and do not re-ask; stop only on drift or a failed gate. Deletion and cleanup stay separate grants, unless an Epic Landing Grant names `cleanup`.

For `initial_delivery`, the Preview gate in condition 1 and condition 3 do not apply; condition 9, the production deploy and smoke of the actual main SHA, is the deployed verification. Every other condition applies unchanged.

Promotion to main requires all these conditions:

1. The fixed candidate passes every required local, security and applicable isolated Preview gate at its exact SHA.
2. Before deployable push/CI connection or main promotion, observe actual protection for the exact repository and ref.
   The non-secret readback names the host capability, ruleset/review policy, required checks, checked time, and evidence. The word `protected` in a source document is not setup proof.
   Do not push, force, or delete a protected branch to test protection, and never claim that this source edit configured it.
   If the host refuses the protection or ruleset read, for example HTTP 403 on a private plan, record `unavailable` with the HTTP status and message. Condition 2 then stays unmet: landing waits for a recorded owner decision that names its scope, and every other condition still applies.
3. Preview evidence records the PR or branch, immutable deployment identity, observed URL, deployed SHA and acceptance result.
4. Fresh remote observation matches the recorded main pre-state and proves candidate ancestry from the frozen base. Run `promotion_readback.py pre` to read remote `refs/heads/main` once and record its JSON.
5. Separate action-time authorization names main, remote and exact candidate SHA, or `landing_gate.py check --action merge` passes for that SHA under an [Epic Landing Grant](#epic-landing-grant). Preview or run-branch authority never covers production.
6. Use the required PR or merge-queue mechanism. A direct authorized update must be a fast-forward to that exact SHA.
7. Fetch and read back main. After the separately authorized fetch, `promotion_readback.py post` proves main ancestry and tree equality. If the server creates SHA S, require its tree to equal the verified candidate tree; S then inherits the candidate's evidence with its original origin.
8. A different tree is a new candidate: verify it as an exact SHA before promotion or release completion.
9. Verify the production deployment and required smoke against the actual main SHA, independently of Preview acceptance.

A moving branch Preview URL is not immutable evidence. Record the fixed deployment URL or identity alongside the Git SHA.
A changed tree, repaired code or configuration invalidates earlier exact-SHA evidence.
Only receipt-verified archive A and provider-created tree-equal main S use the inheritance exceptions defined here.
Record S's observed SHA, the `post` JSON and original candidate/result identities.
Do not repeat the full suite or security review solely because the server assigned tree-equal S a new SHA.
Never relabel inherited candidate, security or CI results as fresh executions at S.
A different tree is a new candidate and needs fresh applicable checks and exact-SHA security review.
Repair a failed landing through a new candidate and reviewed PR; never force-push or rewrite protected history.
Hosted-browser production verifies deployed SHA and smoke; parity capture there is optional. Native, extension and desktop targets use their platform evidence.
For a store-reviewed production target, the promotion pass ends after the main-SHA artifact and submission read-back, with its Release Target Status row `pending`. Report availability as pending the store decision; do not wait for review. A later read-only check of the same artifact moves the row to PASS without a new promotion; a changed artifact is a new candidate.
External setup read-back, the growth review and the outcome review keep their separate post-production gates and authorization.
Separately authorized fixed-build external setup cannot claim release readiness.

## Epic Landing Grant

The owner may approve the landing of one Epic before its candidate exists. The grant replaces the action-time instructions that name an exact SHA. It replaces no gate and moves no gate, and without it every rule in this contract applies as written.

Two things must both hold:

1. The repository is eligible. Its `AGENTS.md` on the frozen remote `main` base has exactly one `## Delivery Autonomy` section, written as that plain heading at the start of a line and above any code fence, with `Landing: epic_grant` and every other line filled: the required check names, the journey command, the production smoke command, the recovery step and the owner-only paths. The parent reads this section from the base commit, never from the candidate or the working tree. The owner sets it once per repository, after the journey command has failed on a known defect and passed on the intended behaviour, the required checks cover the affected behaviour, an independent reviewer route exists, and condition 2 of Promote To Main has a recorded protection read-back. Recheck eligibility when one of those inputs changes.
2. The Epic has a recorded grant. When the owner accepts the Epic's scope and says to land it, the parent runs `scripts/landing_gate.py record` with an output path outside the checkout, and writes only the grant's SHA-256 and a summary into the Epic. The grant names the repository, remote, Epic, work branch, frozen base, covered actions, expiry and repair budget. The frozen base is the remote `main` SHA the parent observed when it recorded the grant.

Before each covered action except `cleanup`, the parent runs `scripts/landing_gate.py check` for that action and the exact candidate. PASS is the authorization for that action at that SHA: it satisfies condition 5 of Promote To Main, the owner's exact instruction in [Archive publication](trusted-host-publication.md), and the push a direct task otherwise leaves to a separate instruction. REFUSED stops that action; report the reasons and continue work that does not depend on it.

The check decides from the grant, the base policy, the candidate's changed paths and an evidence file the parent writes outside the checkout; it refuses an evidence or read-back file inside the checkout, and a read-back whose label disagrees with the commits it names. It runs nothing itself. The parent still performs the review with its required lenses, the required checks, the journey command, Preview where the delivery kind requires it, each read-back and the production smoke, and reports what it observed. The evidence holds the review verdict and its SHA, the number of repair rounds so far, and for a landing also the required check results at the candidate, the acceptance result and the promotion read-back.

Grant actions:

- `push`: the work branch, never with force. The evidence needs a review PASS that binds the candidate.
- `pull_request`: open it. Same evidence as `push`.
- `review_threads`: fix a confirmed finding or post a concrete disproof, reply, resolve the thread, then read the thread state back. A required human approval still waits. A fix made for a thread is a repair round, so the evidence needs the repair-round count.
- `merge`: through the required PR or merge-queue mechanism. The evidence also needs every required check passing at the candidate and the acceptance result.
- `production_deploy`: the deployment a `main` landing triggers, plus condition 9's smoke. The evidence also needs a PASS promotion read-back for the candidate.
- `cleanup`: `scripts/landing_gate.py cleanup-plan` stands in for the check.

Order: atomic local commits, one review point on the exact candidate, push, pull request, the required checks on that candidate, Preview smoke where the delivery kind requires it, merge, `promotion_readback.py post`, production smoke, cleanup. Review comes before push, as on every direct task. A changed head needs fresh checks and a review that binds that exact SHA; no later commit inherits an earlier review, not even one that changes only the Epic record. The one inheritance is the archive child of a managed RUN under Managed RUN Archive Before Promotion: A keeps C's review when A's only parent is C and the parent reports the receipt-bound C-to-A verification as passed. A failed step stops the sequence: report it in product terms, and do not roll production back without the owner.

The repair budget is the number of repair rounds the grant allows after the first review. The parent counts them in the evidence, and the check refuses a count above the budget; the work then waits for the owner.

The check refuses a candidate that touches an owner-only path: an instruction file at any depth (`AGENTS.md`, `AGENTS.override.md`, `CLAUDE.md`), anything under `.github/`, the standard CI configuration of GitLab, CircleCI, Buildkite, Azure Pipelines, Bitbucket and Jenkins, and every path the Delivery Autonomy section lists. A repository whose required checks are defined anywhere else lists those files there. Owner-only changes land under the owner's own instruction, which is also how the section itself changes.

After a PASS read-back, `cleanup-plan` applies the same grant, repository and policy checks and then lists the work branch and its linked worktrees that are safe to remove: tip unchanged since landing, worktree clean, not the primary checkout, never `main` or `development` under any spelling. It prints commands only when every target is safe; one refused target leaves nothing to run. The parent runs only the printed commands of a PASS plan. A dirty, moved or unlisted branch or worktree stays and is reported.

Always the owner's: product scope and PRD changes, a changed visual direction, spending and paid resources, external console setup, destructive data operations and migrations, protection or ruleset exceptions, and any owner-only path. `scripts/landing_gate.py revoke` ends a grant, and so does its expiry. A grant never extends to another repository, Epic or branch.

A managed RUN keeps all 12 ledger keys, closes `local_only` at C with `push` false, and archives C as A. The grant covers only the post-close steps of stage Card 8, with A as the candidate and C's review inherited as stated above.

## Protected Branches

Main is the permanent protected production branch. New flow neither creates nor requires development.
Existing development branches remain untouched and protected from RUN integration, publication and cleanup, including old or wildcard grants.
Before a deployable remote connection or landing, prepare actual protection and read it back as condition 2 of Promote To Main requires. A written intention does not prove that the host enforces it.
Removing a policy requirement does not authorize deleting branches or their data.

## Outcome And Required Evidence

A completed new release has a reviewed candidate, exact-version Preview acceptance when applicable, verified main landing and separate production read-back.
For a managed RUN, candidate A remains the archive-only child of C. Report:

- delivery kind, temporary branch, protocol, frozen base and candidate SHA;
- local checks, independent review and Preview deployment identity, URL, SHA and acceptance (`not applicable: initial delivery` for an `initial_delivery`);
- main pre-state, authorization, ancestry, landing SHA and read-back;
- production build/SHA, smoke and any external setup or outcome handoff.

Unexpected remote movement, divergence, failed gates or mismatched deployments stop dependent operations.
Preserve evidence and reconcile explicitly; never force-push or silently rewrite history.
