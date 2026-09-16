# Harness speed implementation note

Date: 2026-09-16  
Base: `98fa418a5bbed1fb73d0b90b30ccd24fb98758dd`  
UI impact: none.

## What changed

1. `docs_weight.py` now resolves a baseline ref to one commit, lists blob OIDs with NUL-delimited `ls-tree`, and reads those immutable OIDs with one `cat-file --batch`. Empty lists make no batch call. Header size, blob type, truncation, and malformed output fail closed. The outer object-substitution check and report text remain unchanged.
2. Verifier results may carry `timings` for end-to-end, setup, Git guard, cache lookup, snapshot, command, and postcheck intervals. Existing `duration_ms` still means command execution; a cache or reuse hit keeps its historical `duration_ms: 0`. The intervals are observational and are not gate evidence.
3. Review packets no longer repeat changed paths and diff-stat material when the full diff is present. If the diff is byte-truncated, the complete changed-path list remains so scope cannot disappear. Worker packets continue to name, not paste, the result contract; stage routing is explicit in the performance reference.
4. One verifier batch may reuse immutable archive bytes for the same normalized checkout path and exact SHA. Each verifier still extracts independently, checks members and traversal again, and receives its own temporary directory. The archive cache lives only for the batch call.
5. The verifier scheduler fills free slots with the first deterministic-order, non-conflicting job instead of waiting for an entire wave. Explicit opt-outs, exclusive resources, and `max_parallel` still serialize jobs; result order remains deterministic. The old `waves` metric remains as a compatible conflict/capacity grouping.
6. A container verifier may reuse only a deterministic opted-in PASS (`session_exact` plus `deterministic_local: true`) from the same runner invocation. The disk session cache stays disabled for containers. Reuse records its origin and execution key. Each consumer repeats the live Git guard and trusted-runtime/image checks without rerunning the verifier command and retains its own reservation, guard, and sandbox evidence. Retained validation binds the origin to exactly one stored PASS and rejects rebound output, sandbox identity, execution keys, or missing origins.

The runtime executable lock now covers trust preflight and executable binding, then releases during the container command. The executable remains descriptor/handle-bound through the command and is rehashed afterward. This removes a batch-wide serialization point without replacing path-binding checks.

## Measurement

Frozen research evidence remains unchanged: baseline `docs_weight.weights()` took a median 4853 ms with 57 `show` subprocesses; the research bulk path took a median 232 ms with one `ls-tree` and one `cat-file`. The implementation test pins the same two content Git calls and exact output parity, including spaces, Unicode, and empty files.

For an untruncated review-packet fixture, the rendered packet changed from 1220 bytes / 112 words to 1076 bytes / 98 words (-144 bytes / -14 words). Current skill-entry and reference text measures 132465 words across 57 files versus the frozen research baseline of 132175, an increase of 290 words for the new contracts and tests. No end-to-end model or production RUN timing was measured, so no percentage speedup is claimed.

## Verification

Focused commands run from the repository root:

- `python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_docs_weight.py" -v` — 8/9 passed in the sandbox; the pre-existing real-repository test hit Git dubious-ownership because this delegated session runs as a different local user. It does not fail in an owner-owned session.
- `python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_verifier_runtime.py" -v` — 39 passed, 2 platform-specific skips.
- `python -m unittest skills.delivery-harness.scripts.tests.test_harness_v11.HarnessV11Tests.test_review_packet_is_bounded -v` — 1 passed.
- `python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_validate_worker_result.py" -v` — 33 passed.
- `python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_harness_manifest.py" -v` — 114 passed.
- Focused pyflakes passed for every changed Python module and test.

The parent still needs the full required suite and review after return.

## Residual risk

- Container reuse is proven by deterministic fakes for sandbox execution and runtime identity; it is not proof of real Docker/Podman concurrency or wall-time gain.
- Equivalent concurrent requests may each execute; the first stored PASS is then eligible for later consumers. This avoids deadlocks but does not implement request coalescing.
- Real-repository documentation tests require ownership-safe Git access. This sandbox's different local user is an environment limitation, not a code failure.
