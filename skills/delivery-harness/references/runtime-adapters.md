# General Runtime Adapter

Use this contract when managed work needs native execution. Direct work needs no adapter preflight.
Host policy owns models and launch tools; this reference owns authorization, isolation, evidence and acceptance.

## Observe The Current Session

Inspect the current tool descriptions and effective repository instructions.
A host name, installed package or CLI binary does not prove a usable worker surface.
Do not probe another runtime as a substitute route.

Record the observed lowercase `runtime_adapter.provider`, or `generic` when unknown.
A node is eligible exactly when its `allowed_providers` includes that host.
`preferred_provider` is advisory among allowed hosts. A mismatch defers with `runtime_unavailable`.

Record supported `available_drivers` in preference order:

| Driver | Required observed capability | Runtime axes |
| --- | --- | --- |
| `subagents` | Launch a fresh child and receive its terminal result | `subagent` + `parent_managed_worktree` or read-only `shared_checkout` + `agent_result` or `report_file` |
| `sequential_parent` | The parent performs one assigned mission at a time | `parent` + `parent_managed_worktree` + `agent_result` |

Include `sequential_parent` last only when that route is available and permitted.
It cannot satisfy a fresh independent review node.
Current dispatch does not support user-owned app tasks.
An explicit request for those tasks blocks until the owner changes the request or selects its [pinned bundle](legacy-pins.md).
Never silently substitute subagents or parent execution.

Confirm fresh context, workspace binding, permissions, completion, cancellation and actual capacity before dispatch.
Record the host, driver and provider once in `runtime_adapter`, with concrete evidence in the existing attempt record.
Record each driver's observed route caps: wall-clock cap in seconds, tool-turn cap, and `max_message_bytes`.
Capability does not grant an action. A missing grant does not make an available capability unavailable.

## Models, Roles And Context

Effective agent configuration and AGENTS instructions own executor, model, effort and fallback choices.
Null PLAN options preserve host defaults. Unsupported explicit options block without substitution.
Record the actual model and effort; do not treat requested values as execution proof.
Never change provider credentials, installed roles or settings to make a route appear available.

Discover the effective instruction chain from repository root to the assigned checkout.
Include ordered paths and source hashes in a fresh bounded packet.
Keep automatic context discovery enabled; never replay the parent transcript or inject another host's instructions.
The child reads its named sources independently, verifies hashes, and reports its own reading evidence.
Unknown loaded identity stays unknown.

Every NEW parent launch carries an explicit observed or task `max_message_bytes`.
Check the complete parent-visible UTF-8 packet with `check_launch_packet.py` before dispatch.
Overflow means reduce optional context or defer. The guard does not measure host-injected tokens.

The parent records the actual session/model/result origin in attempt evidence.
Accept a result only from the session the parent launched.
Record a failed start as `blocked` with the actual host error.
Follow configured fallback rules only after confirmed predecessor termination and inspection of partial work.
A quiet stream, quota limit, timeout, test failure or permission denial does not prove model unavailability.

## Authorization And Dispatch

This adapter does not own shared state.
The parent owns authorization, PLAN/RUN, dispatch, leases, integration and lifecycle actions.
Follow every directive's `required_actions`; all 12 ledger keys remain in the schema.
Subagent dispatch requires `spawn_subagents`; an external provider process also requires `invoke_external_runtime`.
Worktree, branch, commit, integration and cleanup actions retain their separate grants.

1. Validate PLAN/RUN and accept the selected frontier.
2. Reserve runtime reviews with `reserve-review-dispatch` before launch; never reconstruct the reservation afterward.
3. Verify repository, branch, exact base and clean status before allocating an authorized isolated writer.
4. Render `../assets/templates/WORKER_GOAL.template.md` with scope, skills, permissions, verifier, result contract and exact input identity.
5. Launch all selected siblings before waiting; run a blocking bridge asynchronously.
6. Bind the real worker identity and assigned checkout through `lease-worker`.
7. Consume terminal events or waits; use bounded polling only when the host has neither.
8. Validate each result against its current reservation, live Git, scope, commits and verifier evidence.
9. Integrate serially after the gates required by `review_policy` pass.

One writer owns each checkout, including the parent.
Workers and reviewers never delegate, edit PLAN/RUN, integrate, push or clean up.
A prompt restriction alone does not prove read-only tool isolation.
Preserve failed starts, partial work, dirty files and interrupted evidence.
A result or native completion is a candidate, never a verification PASS.

Reserve non-runtime attempts with `reserve-node-attempt`, execute outside the RUN lock, then use `record-node-result`.
Transitions record lifecycle evidence; they do not perform lifecycle actions.

## Reviewer Tools

A visual reviewer must attach a real browser and report the inspected surface in its evidence.
The parent's browser session does not prove reviewer capability; missing required access blocks that review.

Give each reviewer one bounded packet with exact SHA, scope, diff, acceptance, required tools and unresolved findings.
A changed-code candidate needs fresh security review. Only the documented non-security tree-identity skip may reuse a review.
For architecture-bearing reviews, apply [Architecture Method](delegation-contract.md#architecture-method) to the affected boundaries.

When one review node's packet exceeds the reviewer route's caps, the parent dispatches that review as several scoped calls.
Each call covers one disjoint path group of the same exact SHA.
Each call carries the full finding contract and the lenses its paths need.
Trust-boundary paths stay in one group so the security lens sees them together.
The parent merges the returned sets into one consolidated finding set and records it as one review attempt.
A path group that no call inspected blocks PASS.
This is one review point, not the multi-reviewer fan-out that needs an owner request.

## Version, Handoff And Failure

Recover an unchanged PLAN in its existing RUN. Reconcile current Git, workers and relevant workspaces before dispatch.
Do not replay integrated missions or create a RUN merely to escape a failed gate or exhausted budget.
Retain original attempts and evidence at their original identities.

Follow `runtime-upgrades.md` for loaded/installed digest drift, restart and pinned-bundle handling.
A historical `adopted` status never authorizes current dispatch.
Provider changes require explicit replanning, never an inferred bridge.
This adapter adds no alternate state or handoff rules.
Serialized host handoff follows `execution-state-model.md`; a shared path alone is not portable evidence transport.
