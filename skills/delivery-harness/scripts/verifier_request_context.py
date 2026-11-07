"""The verifier context that request builders and validators must share."""

from __future__ import annotations

from typing import Any


def verifier_context(
    *,
    layer: str,
    run: dict[str, Any],
    plan_revision: Any,
    plan_digest_sha256: Any,
    batch_base_sha: Any,
    head_sha: Any,
    changed_files: Any,
    checkout_role: str,
    checkout_dirty: Any,
    cache_safe: bool,
    mission_id: Any,
    task_id: Any,
    attempt_id: Any,
    lease_id: Any,
) -> dict[str, Any]:
    """Return the full protocol-v2 context for one verifier route.

    Task verifiers bind the task's own head and its own commit files; worker
    verifiers bind the lease's base..head files; mission integration verifiers
    bind the batch_base..integrated files with checkout_role "integration" and
    cache_safe false. Builders and validators must derive every field through
    this function so the routes cannot drift.
    """

    return {
        "run_id": run.get("run_id"),
        "plan_revision": plan_revision,
        "plan_digest_sha256": plan_digest_sha256,
        "graph_revision": run.get("graph_state", {}).get("graph_revision"),
        "batch_base_sha": batch_base_sha,
        "head_sha": head_sha,
        "changed_files": sorted(changed_files),
        "trust_domain": "parent_local",
        "checkout_role": checkout_role,
        "checkout_dirty": checkout_dirty,
        "cache_safe": cache_safe,
        "layer": layer,
        "mission_id": mission_id,
        "task_id": task_id,
        "attempt_id": attempt_id,
        "lease_id": lease_id,
    }
