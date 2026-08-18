# Runtime Performance Contract

Use this contract for every PLAN-v5/RUN-v10 execution on Codex, Claude Code, or Pi. The minimum target is 75% less wall time than a comparable recorded baseline; the stretch target is 85%. A target is not a result. Claim it only after a comparable RUN records both baseline and actual wall time.

Performance work never weakens authorization, isolation, scope, exact-SHA review, integration, evidence, or final validation.

## Shared Fast Path

All three adapters use the same four invariants:

1. Launch each mission or review with a fresh bounded context capsule. Keep automatic repository instruction discovery enabled, but do not replay the parent transcript or copy full PLAN/RUN manifests.
2. Consume host terminal events. Prefer a subscription, cursor wait, workflow result, or child completion event over repeated status reads. Poll only when the host has no wait/event surface, and record that fallback.
3. As soon as one active-wave mission reaches `worker_passed`, dispatch its dependency-ready read-only pre-integration review. Do not launch another writer or integrate until every selected worker result is validated and the wave closes.
4. Run independent local-command verifiers through `scripts/verifier_runtime.py` as a resource-safe batch. Parallel execution is opt-in; an unmarked verifier is serial.

## Bounded Context Capsule

The parent renders one stable capsule per node with:

- `capsule_sha256` and `context_bytes`;
- PLAN/RUN identity, revision, digest, graph revision, batch base, node, attempt, and lease;
- ordered repository instruction paths and content digests;
- exact write/deny or review scope, acceptance rows, unresolved findings, skills, resources, permission boundary, verifier declarations, and result contract; and
- the mission-specific delta after the stable shared prefix.

The child treats that capsule as its complete live task. It opens PLAN/RUN only for a named field the capsule cannot safely supply. A changed capsule gets a new digest. Fresh context does not disable host-native repository context discovery.

## Resource-Safe Verifier Batches

An opted-in verifier declares `execution.parallel_safe` and its resource claims:

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

Two verifiers may share a wave only when both declare `parallel_safe: true` and no shared resource key has `exclusive` access. Missing execution metadata, `parallel_safe: false`, or a conflicting exclusive resource serializes the verifier. This changes scheduling only; session cache rules and gate ownership stay unchanged.

## Machine Telemetry

RUN-v10 may include `runtime_metrics`. It is observational and never grants authorization or satisfies a gate.

Record one append-only event for queue, context render, dispatch, wait, execute, review, verify, and integrate transitions when applicable. Each event records provider, node/attempt identity, phase, terminal status, timestamps, duration, wait time, input/output/cached tokens, and context bytes. Unknown values remain `null`; do not estimate them.

At closeout record:

- comparable `baseline_wall_time_ms`;
- actual `run_wall_time_ms`;
- `critical_path_ms`; and
- target `{ "minimum": 75, "stretch": 85 }`.

Report the measured reduction as `(baseline - actual) / baseline`. If workload, hardware, provider, model tier, or validation scope changed materially, label the comparison non-comparable and collect a new baseline.

## Host Mapping

- Codex: create a fresh top-level app task or fresh direct sibling, then use cursor-based `wait_threads` / App Server status events.
- Claude Code: each Workflow or direct Agent is a fresh sibling; consume `pipeline()` / `agent_result` terminal results.
- Pi: keep explicit `context: "fresh"`; subscribe or block on terminal child events.

Process each terminal result immediately. Streaming review may overlap remaining workers, but RUN remains parent-owned and integration remains serial after wave close.
