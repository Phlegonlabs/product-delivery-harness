# Runtime Performance Contract

Use this contract for every PLAN-v6/RUN-v11 execution on Codex, Claude Code, or Pi.

The goal is to stop paying for the same work twice, not to hit a number. This file carries no percentage target, and one must not be added back without a measurement behind it. An earlier revision carried invented reduction figures that had never been measured against anything, and chasing a made-up number is how a run ends up slicing missions too small or skipping a gate to make the arithmetic work. Remove repeated work, then measure what that bought.

Repeated work, in the order it usually costs the most:

1. Re-dispatching a reviewer against a commit an earlier review already passed.
2. Re-running a deterministic local verifier whose inputs did not change.
3. Serializing verifiers that never contend for a resource.
4. Making a finished mission wait on a slower sibling before it can integrate.
5. Re-reading state the parent could have read once.
6. Re-capturing evidence for a surface the merge did not touch.

Each has a rule below or in `verification-gates.md`. None of them weakens authorization, isolation, exact-SHA review, evidence, or final validation.

Performance work never weakens authorization, isolation, scope, exact-SHA review, integration, evidence, or final validation.

## Shared Fast Path

All three adapters use the same four invariants:

1. Launch each mission or review with a fresh bounded context capsule. Keep automatic repository instruction discovery enabled, but do not replay the parent transcript or copy full PLAN/RUN manifests.
2. Consume host terminal events. Prefer a subscription, cursor wait, workflow result, or child completion event over repeated status reads. Poll only when the host has no wait/event surface, and record that fallback.
3. As soon as one active-wave mission reaches `worker_passed`, dispatch its dependency-ready read-only pre-integration review, and integrate that mission once the review PASSes. Integration stays serial: at most one mission is `integrating` at a time. Do not launch another writer, and do not run batch gates, until every selected worker result is validated and the wave closes.
4. Run independent local-command verifiers through `scripts/verifier_runtime.py` as a resource-safe batch. Batching is the default: a verifier that declares no resource cannot contend with another that declares none. Serialization is opt-in, through a resource claim or an explicit `execution.parallel_safe: false`. Use batch mode at the task and worker gates too, not only the batch gate.

## Parent Turn Boundaries

The contract fixes the order of mutating actions. It does not fix how many parent turns those actions take, and reading it one command at a time inflated a three-mission run to roughly thirty parent round-trips when about half that is enough.

Batch into one turn:

- the pre-launch re-observation list, plus authorization recheck, plus node selection — one `scripts/harness_step.py` call;
- validating a returned node result and worker result — one `scripts/validate_result.py` call;
- the selector re-run that a terminal result triggers, folded into the same turn that validated that result;
- serial merges of several already-review-PASSed missions — several Git operations, one parent decision.

These stay their own stop, because the parent must look at new evidence before deciding:

- a worker result checked against live Git facts;
- a review verdict, PASS or `fix_required`;
- each gate result.

Batching reads never merges two mutations, skips a target recheck, or lets a script write PLAN, RUN, or Git.

## Bounded Context Capsule

The parent renders one bounded context packet per node containing:

- PLAN/RUN identity, revision, digest, graph revision, batch base, node, attempt, and lease;
- ordered repository instruction paths;
- exact write/deny or review scope, acceptance rows, unresolved findings, skills, resources, permission boundary, verifier declarations, and result contract; and
- the mission-specific delta after the stable shared prefix.

The child treats that packet as its complete live task. It opens PLAN/RUN only for a named field the packet cannot safely supply. Fresh context does not disable host-native repository context discovery.

Do not compute a `capsule_sha256` or `context_bytes` for the packet. No gate, selector, or validator reads them; the bounded-context rule above is what produces the speedup.

## Resource-Safe Verifier Batches

A verifier that binds a shared resource declares it:

```json
{
  "execution": {
    "parallel_safe": true,
    "resources": [
      {"key": "database:test", "access": "shared_read"},
      {"key": "port:4173", "access": "exclusive"}
    ]
  }
}
```

Two verifiers may share a wave when neither sets `execution.parallel_safe: false` and no shared resource key has `exclusive` access. A missing `execution` block means no resource claim and no contention, so those verifiers batch. `execution.parallel_safe: false` or a conflicting exclusive resource serializes the verifier.

Declare a resource for anything that binds a port, mutates a database, drives a browser, or otherwise cannot run twice at once. That includes a file two verifiers in the same checkout both write: a test-runner cache, an incremental build manifest, a coverage database, a lockfile. Those are easy to miss because nothing about the command looks shared, and two of them in one wave corrupt each other and fail nondeterministically. Claim the file as an `exclusive` resource key. An undeclared verifier that secretly needs one is a declaration bug, and the fix is the declaration, not a global serial default. Note the migration risk this creates: a verifier authored before batching became the default has no `execution` block, so it is now eligible to run concurrently. Audit existing declarations for shared-file contention once, rather than assuming silence meant safety. This changes scheduling only; session cache rules and gate ownership stay unchanged.

## Machine Telemetry

RUN-v11 may include `runtime_metrics`. It is observational and never grants authorization or satisfies a gate.

Record one append-only event for queue, context render, dispatch, wait, execute, review, verify, and integrate transitions when applicable. Each event records provider, node/attempt identity, phase, terminal status, timestamps, duration, wait time, input/output/cached tokens, and context bytes. Unknown values remain `null`; do not estimate them.

At closeout record `run_wall_time_ms` and `critical_path_ms`. Record `baseline_wall_time_ms` only when a comparable earlier run was actually measured; otherwise leave it null rather than inventing one.

`target_reduction_percent` is optional and carries no default. Set it only when a specific run has a specific agreed goal. Report any reduction as `(baseline - actual) / baseline`, and if workload, hardware, provider, model tier, or validation scope changed materially, label the comparison non-comparable and collect a new baseline.

## Host Mapping

- Codex: create a fresh top-level app task or fresh direct sibling, then use cursor-based `wait_threads` / App Server status events.
- Claude Code: each Workflow or direct Agent is a fresh sibling; consume `pipeline()` / `agent_result` terminal results.
- Pi: keep explicit `context: "fresh"`; subscribe or block on terminal child events.

Process each terminal result immediately. Streaming review and streaming serial integration may overlap remaining workers; RUN remains parent-owned and integration remains serial throughout. A mission integrated early that later fails its integration verifier is reverted or superseded like any other integration failure — that rare rollback is the cost of not making every finished mission wait for the slowest one.
