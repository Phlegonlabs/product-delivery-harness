# Bounded Enhancement Delivery

Apply this policy after the owner accepts one enhancement scope. It applies to direct delivery and managed work without changing the managed RUN schema or granting new actions.

## One Scope Decision

Use one Epic under `docs/epics/` for a complete enhancement outcome and index its path/status in `docs/DOCUMENTS.md`. Start from `assets/templates/EPIC.template.md`. Small fixes append to the matching Epic, linking detailed direct-task evidence when useful; create a bounded Epic only when none fits, never an Epic, PLAN or RUN for every edit. The Epic describes why this round exists, its current-PRD baseline, stable requirement/TEST references, accepted scope, dependencies, affected documents and actual result. It does not duplicate the PRD, authorization ledger, task scheduler or evidence register. Keep unresolved Epic work visible when starting another session; do not infer completion from a closed conversation.

Derive a short execution summary from accepted sources: goal, PRD/TEST references, write scope, design source and UI impact, dependencies, valid action grants and verification commands. Keep it in the existing direct-task report or managed PLAN/RUN. It is a derived summary, not independently editable authority. Missing information produces a specific gap and blocks only dependent work. A change in source decisions routes to the owning skill; unchanged decisions and valid authorizations are reused.

Record the owner's instruction, affected requirement IDs, acceptance conditions, write boundaries, test environments, permitted actions, repair budget, and stopping condition once. Reuse that instruction for covered implementation, document synchronization, synthetic fixture preparation, repair, module replacement, and retesting. Do not ask the owner to approve the same decision after each failed test or technical hash refresh.

The default is at most two repair rounds per root-cause family, including a replacement strategy; a stricter graph or reviewer attempt limit wins. Record attempts across sessions and revisions. Never reset the counter by renaming the issue, changing workers, or opening another graph revision. A new task is not launched automatically.

Selecting a skill alone grants no writes. Preserve every action-specific authorization, exact target, runtime boundary, and host confirmation requirement. Spending, production data, external writes, publication, installation, branch/worktree deletion, or a new product requirement are not implied by local delivery authority. Check existing grants before asking again; do not repeat a still-valid authorization.

## Epic Selection And Change History

Classify the record before implementation, after the owner accepts the outcome:

- Create one Epic for a new feature or complete enhancement with its own goal and acceptance conditions. Index it in `docs/DOCUMENTS.md`; do not create a competing PRD.
- Extend the existing Epic when a small fix, test, copy correction or implementation repair serves the same accepted outcome. A new commit, session, worker or release number is not a new Epic.
- For an isolated small fix with no suitable Epic, create a concise bounded Epic; it may link detailed direct-task evidence rather than duplicate it.
- A follow-up to a closed Epic may append a dated fix record without rewriting its earlier result. A new outcome or changed acceptance criteria needs a linked new Epic; do not quietly broaden the closed one.

Keep a short Change Log in the chosen record: request or finding, reason, affected files/requirements and UI scope, exact commit or evidence, verification result and remaining work. Record each logical fix when it is made, including failed checks and later repairs. Group related edits; do not log every keystroke or duplicate PLAN/RUN state. Before handoff, reconcile the log with the actual diff and keep unresolved criteria visible. A documentation-only internal enhancement may reference its existing contract/tests instead of inventing a product PRD.

## Repository Change Checkpoints

Repository observations also happen outside this delivery flow. Follow the self-contained **Repository Change Checkpoints** in project `AGENTS.md` at task start, significant change boundaries and completion/handoff. Compare local HEAD/history and staged, unstaged and non-ignored untracked changes with prior Epic evidence. Missing or changed baselines stay explicit. Record meaningful external changes as observed/unverified until scope and evidence are known; never infer approval or rewrite historical results. An unchanged observation needs no log row. Read-only tasks report proposed updates instead of writing. This requires no PLAN/RUN, installed Harness tooling or background service.

## Repair Or Replace

For a frontend/mobile enhancement, classify UI impact before implementation and route affected recommendations through `../../ui-design-builder/references/enhancement-recommendations.md`. Preserve current brand/stack and unaffected screens. An explicit hero or animation request remains a required UI/MM acceptance item; a placeholder or a missing effect cannot close it. Do not impose a redesign on a small repair or reopen decisions already covered by the accepted scope.

Judge a module by the accepted requirements, not by the effort already invested in it. Choose a small repair when it is simpler; replace the module when its structure cannot satisfy the requirement or repeated patches obscure the invariant. A same-scope replacement needs no separate architecture approval.

Before replacing it, name the failing requirement, replacement boundary, affected consumers, retained interface/data obligations, recovery point, and regression checks. Preserve unaffected requirements, compatibility required by the product contract, and existing data. Replace implementation through a reviewable diff; never treat this as permission to erase uncommitted work, user data, production resources, or Git history. Update consumers and tests together, then rerun affected integration and security checks on the new candidate.

New scope, a different approved stack, weakened acceptance criteria, or changed product behavior is not an implementation repair. Record it for a later enhancement rather than expanding this round or repeatedly seeking approval mid-delivery. Stop only the unsafe or dependent work; finish independent work that remains inside the accepted scope.

## Document Changes Without Approval Loops

Each skill begins with the shared `document-sync-contract.md`. The product owner skill owns product decisions; UI and compiler ownership remains unchanged. For authorized pointer, command, index, or factual progress corrections that leave approved decisions unchanged, update only the affected live text and record the original instruction. Do not rewrite a whole owner-authored AGENTS.md or CLAUDE.md from a template.

Preserve current PRD content and stable IDs as the next round's baseline. Historical PRDs may explain earlier decisions but never override the current approved PRD. Closed RUNs, human receipts, archived approvals, and previous test results remain immutable.

Hash refresh is evidence bookkeeping, not a new human decision. It also is not proof that the meaning stayed unchanged. Review the semantic diff before refreshing derived bindings under existing authority; never modify an old approval or invent a human attestation. If a frozen product/UI decision actually changes, or the current schema cannot express a valid continuation without a new owner decision, leave that dependent work unvalidated and hand it to the next round. Do not disable a checker or label stale inputs approved.

## Finish The Round Honestly

Keep two outcomes separate: the work session ended, and the entire accepted scope passed. Only the latter permits a delivery PASS. A required failure, missing native runner, unavailable sandbox, stale proof, or unresolved security issue stays failed/blocked/unvalidated even after it is placed in the backlog. Do not remove a required test, loosen a threshold, shrink the platform matrix, or lower a requirement's priority to obtain green results.

When the repair budget is exhausted, stop that failure family. Retain its diff, commands, evidence, candidate identity, and failure count. Finish independent verifiable work. Return a compact report with verified scope, incomplete scope, and next-round handoffs; do not keep the session open waiting for unavailable infrastructure or repeat approval prompts.

For managed work, use the existing pause/reconciliation path for unfinished state; a handoff is not successful closeout, supersession, archive eligibility, or permission to publish. Never invent a new RUN lifecycle phase. A later task resumes preserved state or starts a new properly authorized initiative through the existing recovery rules.

Each handoff includes:

- original PRD/TEST IDs and platform or release target;
- observed failure, minimal reproduction, retained evidence, exact SHA/build and environment;
- attempts already spent and why this round stopped;
- dependent work blocked and independent work verified;
- smallest next action, required capability or decision, and unchanged acceptance condition;
- data/fixture cleanup disposition and any isolated resource still retained.

Use the existing refinement backlog or direct-task report; do not create a competing product specification, automatically create user-owned tasks, or convert an unresolved requirement to optional. Next-round work inherits the context, not an invented PASS or new authority.
