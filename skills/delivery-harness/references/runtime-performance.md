# Runtime Performance Contract

Use this contract for every PLAN-v6/RUN-v11 execution on any host.

Remove repeated work and measure the result. This contract carries no percentage target. Set one only against a measured, comparable baseline; never split missions or skip gates to meet an unsupported target.

Repeated work, in the order it usually costs the most:

1. The scripted write path removes the hand-authored RUN edits between selection and integration: one `record-observation` replaces transcribing `harness_step.py`'s printed snapshot, one `accept-wave` plus one `lease-worker` per mission replace the wave/lease hand edits, `record-integration` closes each mission, and `close-wave` retires the finished wave with its tombstone in one write. Each is a single validated atomic write, so parent output stays flat instead of growing with RUN history. `reserve-review-dispatch --packet-out <path>` renders the reviewer packet from the in-memory reserved run in the same command, removing the separate render pass and its repeated validation; the selector accepts `manifest_already_validated` from callers that just validated the identical pair.

2. Re-dispatching a reviewer against a commit an earlier review already passed.
3. Re-running a deterministic local verifier whose inputs did not change.
4. Serializing verifiers that never contend for a resource.
5. Making a finished mission wait on a slower sibling before it can integrate.
6. Re-reading state the parent could have read once.
7. Re-capturing evidence for a surface the merge did not touch.

Each has a rule below or in `verification-gates.md`.

Performance work never weakens authorization, isolation, scope, exact-SHA review, integration, evidence, or final validation.

## Shared Fast Path

A section is not a worker boundary. Freeze shared interfaces first, then assign independent frontend, backend and integration outcomes to isolated checkout owners. Every shared token, router, package/lockfile, schema and migration path has one owner; dependent packets deny writes to those paths. Split executable tasks into verified atomic commits inside each coherent mission, not a fresh worker per task. Keep coupled same-file work with one writer.

Count reviewers and writers against observed runtime capacity and exclusive resources. Under `per_mission`, a completed mission may enter review while siblings run. The current wave barrier still prevents new writer dispatch until the wave closes; do not describe streaming review as rolling writer scheduling. Measure critical-path delay before proposing a new scheduler contract.

Retain input precondition validation and final mutated-state validation. Reuse is limited to an identical immutable in-memory snapshot before any mutation, with fresh external-state checks where required. A matching PLAN identity alone, a changed batch base, or a caller-supplied boolean cannot justify skipping a new state check. Do not extend the existing internal validation fast paths without focused mutation and stale-state regression evidence.

The managed runtime uses the same four invariants:

1. Launch each mission or review with a fresh bounded context capsule. Keep automatic repository instruction discovery enabled, but do not replay the parent transcript or copy full PLAN/RUN manifests.
2. Consume host terminal events. Prefer a subscription, cursor wait, workflow result, or child completion event over repeated status reads. Poll only when the host has no wait/event surface, and record that fallback.
3. Record each terminal mission with `record-worker-result`. Under `per_mission`, as soon as one active-wave mission reaches `worker_passed`, reserve its dependency-ready read-only pre-integration review in RUN, dispatch only from that receipt, and integrate that mission once the same reserved attempt PASSes. Under `final_candidate` a mission integrates after `worker_passed` and the Worker Result Gate. Integration stays serial: at most one mission is `integrating` at a time. Do not launch another writer, and do not run batch gates, until every selected worker result is recorded and the wave closes.
4. Run local-command verifiers through `scripts/verifier_runtime.py` as a resource-safe batch. Host verifiers require `execution.parallel_safe: false` and run serially within that runner. Independent workers can still run host checks concurrently in separate worktrees. Use batch mode at the task and worker gates too, not only the batch gate.

## Parent Turn Boundaries

Keep mutating actions in their required order. Batch independent reads and preparation when no intervening evidence decision is needed.

Batch into one turn:

- the pre-launch re-observation list, plus authorization recheck, plus node selection — one `scripts/harness_step.py` call;
- validating and recording a returned mission result — one `scripts/harness_transition.py ... record-worker-result` call; use `scripts/validate_result.py` only for read-only preflight;
- the selector re-run that a terminal result triggers, folded into the same turn that validated that result;
- serial merges of several already-review-PASSed missions — several Git operations, one parent decision.

These stay their own stop, because the parent must look at new evidence before deciding:

- a worker result recorded against parent-observed Git facts;
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

Route references by the stage that names them. A worker packet names the result contract but does not paste it; load that contract only while preparing the terminal result. A review packet keeps its exact base/head, scope, evidence requirements, tools, acceptance, and finding lineage, but does not repeat paths already present in its untruncated diff. Only a byte-truncated diff repeats the changed-path list so truncation cannot hide scope.

Every NEW parent launch carries an explicit observed or task `max_message_bytes`.
The parent checks the complete packet with `scripts/check_launch_packet.py` before dispatch.
A child's later packet check verifies local facts but never replaces that launch check.
Use fresh host-native context without the parent transcript, and keep the selected role bridge intact.
The byte guard does not observe host-injected content, so total host token use stays unknown.

## Resource-Safe Verifier Batches

A verifier that binds a shared resource declares it:

```json
{
  "execution": {
    "parallel_safe": false,
    "isolation": "host",
    "resources": [
      {"key": "database:test", "access": "shared_read"},
      {"key": "port:4173", "access": "exclusive"}
    ]
  }
}
```

Host verifiers are serialized even when the runner has free slots, and run fresh with no result reuse. Current declarations require an explicit execution mode; a missing block is invalid, not permission for parallel host execution. Container verifiers in older pins follow `legacy-pins.md#container-verifiers-before-066`.

Declare resources for shared caches, generated clients, databases, ports, browsers, and external state. Exclusive claims serialize operations that conflict outside a checkout. Host execution is serial within the runner, but does not coordinate unrelated processes or grant permission to mutate external systems. Audit shared state before authorizing the command.

## Host Mapping

- Use a fresh bounded native task or child, then subscribe to terminal events or cursor waits when observed. Use bounded polling only when events are unavailable and record that fallback. Preserve installed role and model settings and the configured role bridge.

Process each terminal result immediately. Under `per_mission`, streaming review may overlap remaining workers; serial integration may overlap them under either policy. RUN remains parent-owned. A failed integration follows the existing integration-failure route.

Record the product container's actual computed CSS width with each screenshot. A verifier's exit code 0 proves that the process ended; acceptance still requires the gate's current evidence.
