# Parent-Retained Agent Receipts

Applies to role-bound RUN-v11 assignments pinned to 0.58 or later. Older pinned runs retain their result protocol. The parent reserves the assignment before invoking the native host or bridge, records the actual launch through `record-launch-observation`, and retains the terminal host response outside the checkout. Neither a requested model nor a worker's identity echo proves actual execution.

## Trust Boundary

The global `--session-id <parent>` belongs before the transition subcommand and holds the RUN lock. `record-launch-observation --worker-session-id <child>` records the independently observed native worker session. Both are required for launch recording; they are different identities. The old launch-local `--session-id` spelling is ambiguous and rejected. Stored launch records keep their existing `session_id` field.

The parent reads the terminal response through the reserved host handle. Its adapter retains a normalized JSON envelope with exactly `schema_version: 1`, `session_id` from host metadata, and `payload` extracted from that response. Never take the session from child prose or manufacture an envelope from a different worker's output. Retain the original host response alongside it for review. The source envelope is limited to 8 MiB.

The receipt binds retained bytes; it is not a signature or independent authentication of the parent adapter. A compromised or fabricated parent observation is outside this local validator's trust boundary. Keep the source readable for subsequent validation and archive verification. Do not put secrets in retained task evidence.

## Returned Results

Pass `--result-receipt <json-path>` to `record-worker-result` or `record-review-attempt`. The receipt has exactly these fields:

```json
{
  "kind": "returned_result",
  "session_id": "actual-host-session",
  "source_ref": "/absolute/task-evidence/normalized-host-response.json",
  "source_sha256": "<lowercase SHA-256 of retained source bytes>",
  "payload_sha256": "<lowercase SHA-256 of canonical payload JSON>"
}
```

Canonical payload JSON uses sorted keys, UTF-8, no ASCII escaping, compact comma/colon separators and no non-finite numbers. Use `agent_result_receipts.payload_digest`; do not hash a pretty-printed approximation. Source bytes and extracted payload are independently checked. Identity comes from the containing reservation and its exact launch session, not from a caller-selected assignment.

- A passing mission's payload is its existing `WORKER_RESULT` object. A returned non-passing mission's payload is its existing node-result object.
- A review payload has `outcome`, `findings`, `security_result` and `contract_adoption_check`. The last two are null when inapplicable. A security review's findings are the existing structured-result summaries.
- Reordered valid upstream Product Definition results still join by assignment/attempt/input identity through their parent launch records; they do not use this managed RUN receipt format.

All returned outcomes need provenance, not only PASS. A mismatch refuses the transition without changing RUN. The reservation stores `result_receipt`. Subsequent manifest validation rechecks its retained bytes, session and accepted head/outcome. Missing or changed evidence is not a PASS.

## Rejected Ingestion Of A Passing Result

`reconcile-worker-ingestion` covers only the sole inherited mission-head rejection of an original passing result. It requires the original RUN snapshot and SHA-256, original returned-result receipt, matching node and Markdown worker reports, and actual verifier files. The original wave must be closed. The current reservation, candidate, PLAN, failed dispatch and graph must remain unchanged, with surviving `run_complete` authorization.

The command validates the candidate through ordinary admission against its proven original contract adoption. It preserves the current adoption, closed wave, failed dispatch and all attempt counts. A separate audit receipt binds original bytes, launch, adoption and verifier identities. Manifest validation rechecks those joins and retained source bytes. The mission returns to `worker_passed`; its graph node remains `running` until normal review and integration. This command launches no worker and grants no retry, fallback or acceptance waiver. Missing evidence, other failures, downstream effects and replay fail without mutation.

## Parent-Observed Failures

Do not invent a successful launch when invocation failed before a session existed. Use `reject-worker-result --failure-receipt <json-path>` or a non-passing `record-review-attempt --failure-receipt <json-path>`. A failure receipt uses the same fields, with `kind: launch_failed` and null `session_id` before launch, or `kind: runtime_failed` and the exact recorded session after launch. Never supply both a returned-result receipt and a failure receipt for one response.

Its normalized envelope's payload contains exactly:

- `worker_id`, `attempt_id`: the reserved predecessor;
- `failure_classification`, `error_code`, `observed_error`: the actual explicit host failure;
- `stopped: true`, `termination_evidence`: confirmed termination, not a polling timeout;
- `partial_work`: `{ "status": "none" | "reconciled", "evidence": "<inspection and remaining work>" }`.

The parent adapter maps only an explicit model/provider availability error to `failure_classification: model_provider_unavailable` and one of `model_not_found`, `model_unavailable`, `provider_unavailable`, `model_not_supported`. Preserve the actual error text and original response. Quota, quiet streams, timeouts, test failures, missing tools and permission denials never map to those codes. Other failure codes may record a stopped failure, but cannot authorize fallback.

## Recovery

For 0.59+ role-bound delegated missions, `reconcile-interrupted --failure-receipt <path>` verifies the stopped predecessor and inspected partial work before changing phases. The selector and `lease-worker` recheck that retained receipt before admitting a retry. Missing or changed stop evidence blocks retry, including an older interruption marker in a current RUN. Unknown liveness uses pause and host observation. Cancellation or timeout with confirmed termination can permit a fresh same-role attempt; it never permits a model fallback. This bounded check does not change pre-0.59 pins, parent/non-role assignments, or the separate review fan-out reconciliation protocol.

For either `lease-worker` or `reserve-review-dispatch`, pass the existing `--fallback-record` evidence. It must name the configured primary-to-fallback mapping, exact stopped predecessor and a fresh attempt. Its error, termination and partial-work evidence must match the retained failure. The logical role remains unchanged; `resolved_role` records the fallback implementation. Recompute the fallback's capabilities, required tools, action grants, capacity and isolation before reserving it. The same review/mission retry budget still applies. Fallback cannot chain from a fallback.

Record the fallback's actual launch with the same fallback evidence. A failed start has a failure receipt, not a fabricated predecessor launch. A runtime failure has both its original launch and failure receipt. Neither receipt grants an action or lets an ineligible UI/reviewer node become parent work.


## Role-Policy Boundaries

An owner-authorized [role-policy update](runtime-adapters.md#host-role-policy-updates) preserves each captured reservation, launch and receipt. Historical fallback provenance uses that reservation's exact archived policy view. A fresh fallback still resolves the current mapping and requires explicit availability failure, stopped predecessor and partial-work evidence. Updating policy grants no fallback or retry and changes no result admission rule.
