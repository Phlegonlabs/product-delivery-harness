# PRD Refinement Across Delivery

Keep one current PRD package. Use this rule after the first coherent candidate exists, before Product Definition Approval, and when new evidence appears at existing design, implementation, validation or outcome checkpoints. Review the delta; do not restart discovery or add a gate, recurring review, parallel specification or mandatory artifact.

English `PRD.md` remains product authority. Preserve unaffected decisions and stable IDs. Reconcile accepted changes into English first, then refresh the complete Chinese review copies under `bilingual-review.md`. Use `artifact-lifecycle.md` for staging and separately authorized publication. Historical approvals and evidence remain intact.

## First Delivery: Review The Whole Journey

Review the same candidate from two perspectives before its existing approval checkpoint:

- **UI perspective:** the `requirements` role follows each intended user's entry and first use through an observable useful result. Check cross-screen handoffs, content responsibilities, empty/loading/error/permission states, cancellation and recovery, accessibility, locales and supported responsive targets. Product Definition reviews required behavior; it does not invoke `ui-design-builder`, create wireframes or choose visual style. A headless product reviews caller/operator journeys without inventing screens or login.
- **Technical perspective:** `architecture`, with applicable `backend` and `frontend-platform` roles, follows those journeys through data ownership and lifecycle, permission boundaries, integration contracts, retries and duplicate effects, migrations, release availability, monitoring, recovery ownership and testability. Propose unresolved technology choices through the existing Stack Decision Checkpoint.

Check the joins between features, not only individual requirement rows. Can the intended user reach value with the first release's actual data, permissions, integrations and operational setup? A page inventory or plausible architecture alone cannot answer this. Record applicable gaps and non-applicability with reasons; do not add every feature common to the product category.

Distinguish required-now coverage, explicitly deferred scope and owner decisions using existing priorities and release targets. Required-now findings must trace to an accepted need, Must requirement, applicable NFR or release obligation. A newly discovered essential need without an owner decision becomes a blocking Open Question. Deferral cannot hide a dependency of required work or downgrade an accepted Must. The parent reconciles both perspectives and existing trace/consistency review against the same candidate before approval. Use authorized read-only lanes or perform the roles sequentially; this rule grants no delegation.

## Return New Evidence At Existing Checkpoints

| Checkpoint | New evidence to reconcile |
| --- | --- |
| Discovery and candidate review | User needs, constraints, conflicting answers, unsupported assumptions and missing journey steps |
| Wireframe validation and HiFi review | Missing transitions, states, content, accessibility or responsive behavior; distinguish design defects from product gaps |
| Implementation and integration | Actual data rules, permission boundaries, integration limits, side effects and failure recovery |
| Acceptance and release readiness | Negative, boundary and recovery scenarios; setup, migration, availability and operational obligations |
| Activation and requested outcome review | Verified measurement sources, actual outcomes and operational gaps, preserving original targets and measurement windows |

For each material finding, record the source/build or document revision, affected IDs, observed gap, proposed requirement or acceptance wording, owner, disposition and dependent work. Use the existing Epic/task evidence or refinement backlog; use the candidate PRD's existing Open Questions fields when a product decision is unresolved. Do not duplicate closed findings or create a separate ledger. Reuse known answers and group only unresolved business decisions for the existing owner checkpoint.

## Improve Wording Without Changing Authority

When refining a requirement, name the actor, trigger and preconditions, rule or data boundary, observable outcome, applicable denial/failure/recovery behavior and linked `TEST-*` signal. Replace vague promises with measurable acceptance. Put implementation mechanics in architecture; omit irrelevant cases instead of inflating every requirement into boilerplate.

- **Draft, accepted meaning:** fill supported omissions in the same candidate, synchronize affected architecture/UI-surface/test traces and review copies. Assumptions remain labeled; evidence is not permission for new scope.
- **Clear requirement, faulty implementation:** repair implementation and test the existing obligation. Never weaken the PRD to match code.
- **New or changed product/stack decision:** retain the proposal and evidence for the owning Product Definition flow. Reuse valid decisions; a substantive revision needs the existing owner approval and affected downstream revalidation.
- **Approved or frozen inputs:** capture discoveries in the existing change record until a valid revision can be consumed. Do not silently edit the frozen PRD, an active RUN binding or historical receipt. Even an authorized wording correction must satisfy existing exact-byte approval checks; a hash refresh is not approval. If valid continuation cannot be represented, keep dependent work unvalidated and use the existing next-round handoff. Finish independent work.

At closeout, reconcile applied, deferred and unresolved findings with the current PRD and actual evidence. An unresolved required gap remains a blocker, not a completed delivery. Outcome observations use the existing `no_change`, `enhancement` or `incident` route; they never silently lower a target.
