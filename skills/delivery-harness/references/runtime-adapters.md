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
An explicit request for those tasks blocks until the owner changes the request or selects its [pinned bundle](legacy/legacy-pins.md).
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

Check each launch packet's bytes under [Bounded Context Capsule](runtime-performance.md#bounded-context-capsule).

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
4. Bind the real worker identity and assigned checkout through `lease-worker`.
5. With `--packet-out <new-path> --max-message-bytes <n>`, the same `lease-worker` call also renders `../assets/templates/WORKER_GOAL.template.md` from the leased run. Repeat `--context-path` for each ordered source; pass `--host-file` for the facts only the host holds. The call size-checks the packet before the RUN write and creates it after.
6. Launch all selected siblings before waiting; run a blocking bridge asynchronously.
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
Probe the reviewer route's own browser once per host session and route, and record the receipt in the existing attempt record.
Later reviews on that session and route reuse it.
Re-prove capability only when the route or session changed, or a browser failure voided the receipt.

Give each reviewer one bounded packet with exact SHA, scope, diff, acceptance, required tools and unresolved findings.
A reviewer whose sandbox cannot run git receives the `review_input.py` output (a detached clone with `review-input/`: per-scope diffs, `HEAD.txt`, `parent-status.txt`, `tracked-files.sha256`). It proves identity and cleanliness from that manifest as the parent's attestation ([Security Review](security-review.md#required-inputs)).
A changed-code candidate needs fresh security review. Only the documented non-security tree-identity skip may reuse a review.
For architecture-bearing reviews, apply [Architecture Method](architecture-method.md) to the affected boundaries.

When one review node's packet exceeds the reviewer route's caps, the parent dispatches that review as several scoped calls before launch.
Size a browser review by its sample under Verify-Then-Sample Review, not by its full matrix; split by page group when that sample still exceeds the wall-clock cap.
Each call covers one disjoint path group of the same exact SHA.
Each call carries the full finding contract and the lenses its paths need.
Trust-boundary paths stay in one group so the security lens sees them together.
The parent merges the returned sets into one consolidated finding set and records it as one review attempt.
A path group that no call inspected blocks PASS.
This is one review point, not the multi-reviewer fan-out that needs an owner request.

### Verify-Then-Sample Review

The reviewer of a machine-produced browser matrix verifies it. The reviewer does not re-judge it.

1. Read the checker output. Confirm the receipt binds the exact candidate hashes and the matrix is complete.
2. Inspect every automated FAIL and every row flagged as changed from the prior reviewed candidate.
3. Spot-check PASS rows: per page, the `ready` state and the densest state at the smallest and largest target.
4. Add a fixed random sample of at most 20 further PASS rows. Record the seed and the sampled rows in the review.

Never re-click every operation or re-open every capture.

## Version, Handoff And Failure

Recover an unchanged PLAN in its existing RUN. Reconcile current Git, workers and relevant workspaces before dispatch.
Do not replay integrated missions or create a RUN merely to escape a failed gate or exhausted budget.
Retain original attempts and evidence at their original identities.

Follow `runtime-upgrades.md` for loaded/installed digest drift, restart and pinned-bundle handling.
A historical `adopted` status never authorizes current dispatch.
Provider changes require explicit replanning, never an inferred bridge.
This adapter adds no alternate state or handoff rules.
Serialized host handoff follows `execution-state-model.md`; a shared path alone is not portable evidence transport.
