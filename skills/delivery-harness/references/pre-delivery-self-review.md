# Self-Review Before Product Delivery

For a new product, complete these author checks in order: draft the Product Definition, reconcile post-draft market research, review the resulting PRD package, review UI structure and direction, then review the connected HiFi. Finish the existing owner decisions and required independent reviews before Harness execution. Earlier research-first assessment does not replace the post-draft market pass.

These are preparation checks inside the existing stage exits, not new human approval rounds, schemas or standalone artifacts. The parent remains responsible when a helper contributes findings. Self-review cannot supply an independent review, a human decision or permission to execute, publish, install or delegate.

Apply these new author handoff requirements to work adopting Harness 0.57.0 or later. Record the observed skill version/source identity in the existing task record; an unknown loaded identity remains unknown. Earlier pinned RUNs retain their recorded contracts until an authorized upgrade boundary.

When a new 0.57.0-or-later task consumes stages already approved without these checks, perform a present-day catch-up self-review at handoff only for approved scope whose bytes changed since approval, or when its UI contract version changed. Record the identity of each unchanged approval instead. Name each approval's identity and the actual review date and candidate; never claim the review happened before that historical approval. Unchanged owner decisions remain valid. Required findings block dependent execution; repairs that change approved content renew the affected decisions. A closed approval alone never exempts changed scope or the new task's own work from current self-review.

## Record The Reviewed Candidate

Use the existing Epic or direct-task record, linking the existing research, UI and review evidence. Record the stage, author, date, candidate paths and revision or SHA-256 values, affected requirement/UI/TEST IDs, checks actually performed, findings and repairs, unresolved blockers, and a conclusion of `pass` or `blocked`. An explicit no-finding conclusion still names the inspected scope and evidence.

Record the producer and self-checker worker/session identity separately enough to confirm they are the same producing agent.
Review the actual current artifacts. A substantive revision invalidates the affected self-review: inspect the delta and shared consumers, run the relevant checks again, and append the new result. Preserve earlier findings and approvals. A screenshot, score, checklist tick or validator success alone cannot establish a semantic or visual review.

## PRD Self-Review

After drafting and post-draft market reconciliation, the Product Definition producing agent performs one complete package self-review. Include accepted recommendation changes before this review. The same producing agent checks and repairs `PRD.md`, `architecture.md`, `stack-decisions.md` and the Chinese review copies together.

Bind the result to the exact candidate revision or SHA-256. After repairs or the Stack Decision Checkpoint, recheck changed decisions, affected requirements and shared consumers before presenting Product Definition Approval. When the checkpoint leaves the reviewed content unchanged, confirm its identity and retain the complete self-review evidence. This is one overall author review with affected-scope rechecks, not another independent review wave.

- Confirm that relevant `RA-*` and `MR-*` evidence agrees with the problem, audience, alternatives, differentiation, scope, metrics and risks. Keep facts, vendor claims and hypotheses distinct; include source dates and unresolved evidence gaps. Apply only owner-accepted product or stack changes.
- Walk the first useful journey, feature joins, denial/error/recovery paths, data and permission boundaries, operational setup and release obligations. A headless product reviews caller/operator journeys.
- Check that Must requirements and applicable NFRs have observable acceptance and `TEST-*` coverage; reconcile PRD, architecture, stack and Chinese review copies. Use the existing product-package, translation and output-contract checks at their applicable stages.
- Confirm that architecture assigns component responsibilities, mutable-state ownership, interfaces, trust boundaries and applicable failure recovery for each required journey. Check that unresolved feasibility questions name an owner, bounded investigation and pass/fail criteria; required blockers remain blocked.
- Connect applicable load, latency, cost, migration and recovery requirements to existing TEST obligations and responsible owners. Separate planned engineering checks from evidence already observed; a complete document does not prove implementation or operational readiness.
- Record skipped or unavailable market research with its existing permitted reason and impact. A research limitation is not evidence of market validation. An unresolved required fact, product decision or dependency keeps this self-review blocked; a permitted research skip never skips PRD self-review.

Use `../../product-definition-builder/references/prd-refinement.md` for findings and owner boundaries. Only a current passing self-review with no required unresolved gap is ready for the existing Product Definition Approval and downstream handoff.

## UI Structure And Direction Self-Review

The `frontend-design` author reviews each proposed direction before asking the owner to select it. Here “UI” means the PRD-to-design translation and representative direction studies; it does not add a Wireframe stage.

- Follow the approved page purposes, navigation, operations and entry/return paths, states, copy/data responsibilities and responsive targets through the representative primary and stress cases.
- Inspect the rendered studies on the applicable platforms. Check hierarchy, grouping, density, readability, control treatment, accessibility and motion intent against the brief and inspected references.
- Keep the approved responsive set. New Web packages default to four review widths: 390, 768, 1024 and 1440 CSS px; inspect intermediate widths too. These are review targets, not forced CSS breakpoints. Native and hybrid surfaces retain their own approved size classes/target families. Follow the existing platform stress cases in `../../ui-design-builder/references/modern-design-sources.md`; the 320 CSS-pixel reflow check is an accessibility stress case, not a fifth authored target.
- Confirm that directions use comparable cases, respect the approved stack and expose meaningful tradeoffs. Check required behavior rather than relying on reviewer-shell navigation.
- Repair design defects within the accepted scope. Route missing product decisions upstream and keep the dependent stage blocked.

Link the existing Direction comparison, captures and Frontend Design Usage records. After an owner-selected mix or a changed direction, recheck the revised study before the existing direction decision. Direction approval remains the owner's decision.

## HiFi Self-Review

After the connected candidate and cheap completeness preflight, the same producing agent checks and repairs the rendered HiFi/UI HTML at the exact candidate revision or SHA-256 before handing it to Impeccable and H1–H9 review or owner choice/approval. Any repair changes the candidate identity and requires the affected recheck.

- Follow the complete PRD page/target/state matrix and the selected direction. Check visible copy and provenance, content/data meaning, operations, menus, tabs, focus, overlays, failure/recovery, tokens and applicable motion.
- Inspect every approved responsive target, including all four default Web widths when that is the approved set. A desktop-only render cannot stand in for the smaller targets; the direction study's representative cases cannot stand in for the complete HiFi.
- Inspect actual browser renders and interactions, including long/localized copy, intermediate widths, overlap, clipping, overflow and reduced motion. Use the existing closed-browser restrictions. Record the inspected captures' hashes in the task record; the independent browser reviewer builds the complete matrix receipt once per candidate.
- Collect findings before repairing shared causes. A repair self-check covers the ledger rows, changed sources, direct consumers and the completeness preflight; it does not rerun the complete matrix. Missing browser evidence remains blocked or unvalidated; static checks do not establish a visual pass. Native HTML projections do not establish native implementation proof.

Reuse the current completeness, browser and review tooling. This author check neither consumes nor resets the existing independent diagnostic/repair budget. Follow the bounded-enhancement repair limits for author repairs and the existing HiFi review limits for independent review.

Impeccable critique/audit, H1–H9, Visual Approval and the conditional Design System Need Gate still follow. Any later repair invalidates the affected evidence and requires the applicable recheck before approval or handoff.

## Harness Entry

Before direct implementation or managed readiness, the parent checks the current self-review records alongside approved Product Definition/stack and applicable approved UI/HiFi sources. A UI-bearing initial delivery cannot enter execution with UI deferred, a missing self-review or an unresolved required finding. It returns to the owning stage; read-only inspection and planning may continue.

For enhancements, review the accepted delta and shared consumers, carry forward current evidence for unaffected scope, and renew only affected decisions. Routine maintenance follows `../../ui-design-builder/references/review-workflow.md`: it records the applicable author check against the accepted change and current product without regenerating historical HiFi. A headless product records UI and HiFi as not applicable with a reason.
This is a parent semantic handoff check. Existing validators still check their declared artifact, hash and approval contracts; they do not automatically prove that these author reviews occurred. Record missing evidence and stop dependent execution rather than treating a structural validator PASS as self-review.
