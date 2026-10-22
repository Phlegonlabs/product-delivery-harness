# Generate, Verify And Correct

Use this shared stage-loop guide from Product Definition through an integrated
candidate. It applies the existing bounded-loop method; it adds no scheduler,
state store, approval database, verifier-confidence score, autonomy score, or
new retry budget.

## Stage Ownership

| Stage | Author and corrector | Verifier and feedback owner |
| --- | --- | --- |
| Product requirements and architecture | Product author | Product checker, focused review, and explicit owner approvals |
| UI direction and HiFi | Bound `frontend-design` author | Completeness, Impeccable, browser/grading, and Visual Approval owners |
| Design-system compilation | Compiler author | Pair, contrast, type-scale, package, and preview checks |
| Task and mission | Assigned writer | Focused verifier; exact-head reviewer under `per_mission` |
| Feature acceptance | Owning mission writer | Declared `PRD-*` acceptance gates at the current candidate |
| Platform handoff | Owning platform writer | Frozen platform order, dependencies, and completion verifier |
| Integrated candidate | Owning code mission | One combined review (code, security, visual) and final matrix |

The generating owner repairs accepted-scope defects. A contract defect returns to
`product-definition-builder`; a design-source defect returns to
`ui-design-builder`; a missing external action returns to `product-activation`.
A repair that changes code or approved inputs creates a new candidate.

Security, SEO, Activation, and Final UI Acceptance reviews stay read-only. They
never become the author, remediator, or external-target mutator. Return concrete
findings to the owning flow above.

## Loop

1. Freeze the target, accepted scope, input versions, verifier commands, pass
   signal, failure routes, and existing task attempt or time budget.
2. Generate the smallest change that satisfies the frozen target.
3. Run the shortest meaningful focused verifier at that exact candidate.
4. Broaden when affected behavior or unknown impact requires it; run the
   required mission/feature/platform/integration gates.
5. On PASS, record the exact candidate, command or decision, actual result, and
   evidence; then stop. Success does not require a minimum iteration count.
6. On failure, record expected result, actual result, exit or observation,
   artifact or trace, and input identity. Do not hide the concrete difference.
7. Wait for every required verifier and review result on the same candidate.
   Group the findings by root-cause family and send them to the owning
   corrector as one repair. Non-blocking suggestions go to the backlog.
8. Repair only accepted scope. Rerun the affected verifier and every downstream
   check invalidated by the new candidate. A re-review checks the original
   findings, the changed code and its direct consumers, not the whole scope again.
   This is the only repair budget; a second repair round needs an explicit owner
   decision.
9. Reuse exact unchanged-input evidence only when the existing contract permits
   that reuse. Preserve its origin and reject stale results.
10. Stop on PASS, exhausted budget, missing required capability, or a contract
    gap. A failed re-review stops at `blocked` and returns to the owner; it never
    starts another round on its own. Preserve history, candidate identity, and
    unresolved work.

Keep the record in the existing task report, Epic, PLAN acceptance row, or RUN
gate. Direct work does not create PLAN/RUN state to host this loop. Managed work
uses the existing verifier, review, and transition declarations.

Never weaken a gate, lower a required threshold, shrink a platform matrix, or
promise zero defects to make a loop pass. Missing capability, data, tooling, or
authority blocks the claim rather than inventing a PASS.

## Candidate And Gate Joins

Bind every PASS to the exact candidate SHA and declared inputs. A later change to
covered source, configuration, contract, toolchain, or external state invalidates
the affected result. Deterministic reuse follows `graph-orchestration.md`;
security review never reuses a prior candidate, tree identity, or reviewer skip.

Feature Must traces use existing `acceptance_gate_ids` and canonical Required-Yes
`TEST-*` obligations. Every contributing mission precedes each final gate through
pass-only dependencies, and the gate PASS covers the current unified candidate.

Platform order is fully specified and design-complete before implementation.
The architecture owns owner-selected whole-platform order, shared interfaces, and
required TEST IDs. PLAN dependencies route shared work first and each platform
through its completion mission. A retained handoff PASS proves the historical
stage start, not current platform health; final platform health needs fresh
regression at the unified candidate SHA.

Human decisions remain human. Direction selection, product approval, Visual
Approval, publication, external writes, protected-branch promotion, and accepted
deferrals require the existing explicit owner decision or exact action grant.
Record actual capability separately from permission; capability never grants an
action.

A handoff carries the accepted result, remaining defects, exact candidate
identity, next owning flow, and evidence the consumer may reuse. It does not
convert an earlier PASS into a downstream PASS or grant a new action.
