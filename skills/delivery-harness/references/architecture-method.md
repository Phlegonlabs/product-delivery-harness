# Architecture Method

Apply this method to initial architecture and scoped changes to state, trust, integration or migration boundaries.
For a repair with unchanged boundaries, reuse the accepted design and verify the affected behavior.

1. Start with a concrete caller example and its expected result.
2. Derive responsibilities and interfaces from that example.
3. For mutable state, name its owner, readers and permitted transitions.
4. State invariants, invalid states and trust boundaries.
5. For side effects, define repeat-call behavior and recovery after failure between steps.
6. Link those observable outcomes to existing acceptance checks and `TEST-*` obligations when available.

Product Definition records conceptual contracts in the existing architecture package.
Implementation design derives signatures and types inside the accepted write scope.
It does not select an unapproved stack or change product decisions.

When coupling, durability, trust or migration remains unresolved, compare the smallest viable structural alternatives.
Explain each alternative's effect on the caller, state ownership and failure recovery.
Do not require alternatives for every local fix.

When repeated failures challenge the design, recheck its premises before another repair.
Count the applicable actors, load and concurrent operations from evidence.
Classify tool and environment failures separately from design failures.
This review does not reset repair budgets, authorize a rewrite or replace existing owner decisions.
Code reviewers apply the same method only to the affected boundaries.
Use existing review outcomes and task evidence; do not create another gate or decision ledger.
