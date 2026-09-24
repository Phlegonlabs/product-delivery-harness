#!/usr/bin/env python3
"""Focused resume reconciliation tests for current and historical worktrees."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import resolve_runtime_options  # noqa: E402
from harness_manifest import plan_digest, validate_run  # noqa: E402
from select_ready_nodes import (  # noqa: E402
    _resume_reconciliation_reasons,
    select_ready_nodes,
)
from test_harness_manifest import authorize_action, authorize_execution  # noqa: E402
from test_select_ready_nodes import current_preintegration_review_state  # noqa: E402


PARENT_PATH = "C:/repo/integration"
PARENT_BRANCH = "codex/integration"
PARENT_HEAD = "a" * 40
WORKER_PATH = "C:/repo/worktrees/M1"
WORKER_BRANCH = "refs/heads/codex/m1"
WORKER_HEAD = "b" * 40


def parent_worktree() -> dict[str, object]:
    return {
        "path": PARENT_PATH,
        "branch_ref": f"refs/heads/{PARENT_BRANCH}",
        "head_sha": PARENT_HEAD,
        "managed_by": "parent",
        "dirty": False,
    }


def resume_run(*, status: str = "running") -> dict[str, object]:
    return {
        "status": status,
        "observed": {
            "git": {
                "parent_worktree_path": PARENT_PATH,
                "parent_branch": PARENT_BRANCH,
                "parent_head_sha": PARENT_HEAD,
                "parent_dirty": False,
                "worktrees": [parent_worktree()],
            }
        },
        "mission_states": {
            "M1": {"phase": "queued", "worker_id": None},
        },
        "graph_state": {
            "node_states": {
                "N-M1": {
                    "phase": "dormant",
                    "last_attempt_id": None,
                    "bound_worker_id": None,
                },
                "N-REVIEW-M1": {
                    "phase": "dormant",
                    "last_attempt_id": None,
                    "bound_worker_id": None,
                },
            }
        },
        "workers": [],
        "review_workers": [],
    }


def bind_passed_worker(run: dict[str, object], *, runtime: str = "subagent") -> None:
    run["mission_states"]["M1"].update(
        {"phase": "worker_passed", "worker_id": "W-M1", "head_sha": WORKER_HEAD}
    )
    run["graph_state"]["node_states"]["N-M1"].update(
        {
            "phase": "running",
            "last_attempt_id": "ATT-M1-1",
            "bound_worker_id": "W-M1",
        }
    )
    run["workers"] = [
        {
            "worker_id": "W-M1",
            "mission_id": "M1",
            "worker_runtime": runtime,
            "workspace_mode": "parent_managed_worktree",
            "worktree_path": WORKER_PATH,
            "branch_ref": WORKER_BRANCH,
            "phase": "worker_passed",
            "worker_head_sha": WORKER_HEAD,
        }
    ]
    run["observed"]["git"]["worktrees"].append(
        {
            "path": WORKER_PATH,
            "branch_ref": WORKER_BRANCH,
            "head_sha": WORKER_HEAD,
            "managed_by": "parent",
            "dirty": False,
        }
    )


def live_streaming_review_pair() -> tuple[dict[str, object], dict[str, object]]:
    plan, run = current_preintegration_review_state()
    digest = plan_digest(plan)
    authorize_execution(
        run,
        ["M1", "M3"],
        status="running",
        plan=plan,
        digest=digest,
    )
    run["active_wave"] = {
        "wave_id": "B-LIVE",
        "status": "active",
        "plan_revision": plan["revision"],
        "plan_digest_sha256": digest,
        "batch_base_sha": "a" * 40,
        "selected_missions": ["M1", "M3"],
        "deferred_missions": [],
        "conflict_edges": [],
    }
    run["integration"]["batch_base_sha"] = "a" * 40
    run["mission_states"]["M3"].update(
        {
            "phase": "worker_running",
            "lease_id": "LEASE-M3",
            "lease_plan_revision": plan["revision"],
            "lease_plan_digest_sha256": digest,
            "worker_id": "W-M3",
            "base_sha": "a" * 40,
            "head_sha": None,
            "integration_gate": "planned",
            "integrated_sha": None,
        }
    )
    run["graph_state"]["node_states"]["N-VISUAL-REPAIR"].update(
        {
            "phase": "running",
            "attempts": 1,
            "last_attempt_id": "ATT-M3",
            "last_outcome": None,
            "bound_worker_id": "W-M3",
            "blockers": [],
        }
    )
    mission_node = next(
        node
        for node in plan["graph"]["nodes"]
        if node["id"] == "N-VISUAL-REPAIR"
    )
    worker = copy.deepcopy(run["workers"][0])
    worker.update(
        {
            "worker_id": "W-M3",
            "mission_id": "M3",
            "lease_id": "LEASE-M3",
            "plan_digest_sha256": digest,
            "worktree_path": "C:/repo/worktrees/M3",
            "branch_ref": "refs/heads/codex/m3",
            "phase": "worker_running",
            "worker_head_sha": None,
            "runtime_binding": {
                "provider": "codex",
                "driver": "subagents",
                "source": "host",
                **resolve_runtime_options(mission_node["runtime"], "codex"),
            },
        }
    )
    run["workers"].append(worker)
    run["observed"]["git"]["worktrees"].append(
        {
            "path": "C:/repo/worktrees/M3",
            "branch_ref": "refs/heads/codex/m3",
            "head_sha": "a" * 40,
            "managed_by": "parent",
            "dirty": False,
        }
    )
    authorize_action(
        run,
        "spawn_subagents",
        ["M1", "M3"],
        ["*", "worker:W-M1", "worker:W-M3"],
    )
    authorize_action(
        run,
        "create_local_worktrees",
        ["M1", "M3"],
        ["worktree:C:/repo/worktrees/M1", "worktree:C:/repo/worktrees/M3"],
    )
    authorize_action(
        run,
        "create_local_branches",
        ["M1", "M3"],
        ["branch:refs/heads/codex/m1", "branch:refs/heads/codex/m3"],
    )
    authorize_action(
        run,
        "create_local_commits",
        ["M1", "M3"],
        ["branch:refs/heads/codex/m1", "branch:refs/heads/codex/m3"],
    )
    return plan, run


class RuntimeResumeWorktreeTests(unittest.TestCase):
    def test_live_sibling_does_not_block_streaming_preintegration_review(self) -> None:
        plan, run = live_streaming_review_pair()

        self.assertEqual([], validate_run(plan, run))
        self.assertEqual([], _resume_reconciliation_reasons(run))
        selected = select_ready_nodes(plan, run)
        self.assertIn(
            "N-FRONTEND-REVIEW",
            [item["node_id"] for item in selected["dispatchable_nodes"]],
        )

    def test_unrelated_and_historical_worktrees_do_not_block_resume(self) -> None:
        run = resume_run()
        run["workers"] = [
            {
                "worker_id": "W-OLD",
                "mission_id": "M1",
                "workspace_mode": "parent_managed_worktree",
                "worktree_path": "C:/repo/worktrees/old",
                "branch_ref": "refs/heads/codex/old",
                "phase": "worker_failed",
                "worker_head_sha": "c" * 40,
            }
        ]
        run["observed"]["git"]["worktrees"].extend(
            [
                {
                    "path": "C:/repo/worktrees/old",
                    "branch_ref": None,
                    "head_sha": "c" * 40,
                    "managed_by": "parent",
                    "dirty": True,
                },
                {
                    "path": "C:/repo/unrelated",
                    "branch_ref": None,
                    "head_sha": None,
                    "managed_by": "parent",
                    "dirty": None,
                },
            ]
        )

        self.assertEqual([], _resume_reconciliation_reasons(run))

    def test_current_worker_worktree_must_be_present_clean_and_exact_head(self) -> None:
        base = resume_run()
        bind_passed_worker(base)

        missing = copy.deepcopy(base)
        missing["observed"]["git"]["worktrees"].pop()
        self.assertIn(
            "worker_state_unreconciled", _resume_reconciliation_reasons(missing)
        )

        dirty = copy.deepcopy(base)
        dirty["observed"]["git"]["worktrees"][-1]["dirty"] = True
        self.assertIn(
            "worktree_state_unreconciled", _resume_reconciliation_reasons(dirty)
        )

        wrong_head = copy.deepcopy(base)
        wrong_head["observed"]["git"]["worktrees"][-1]["head_sha"] = "d" * 40
        self.assertIn(
            "worker_state_unreconciled", _resume_reconciliation_reasons(wrong_head)
        )

    def test_ready_run_with_clean_active_worker_or_review_is_reconciled(self) -> None:
        mission_run = resume_run(status="ready")
        bind_passed_worker(mission_run)
        mission_run["mission_states"]["M1"]["phase"] = "worker_running"
        mission_run["workers"][0].update(
            {"phase": "worker_running", "worker_head_sha": None}
        )
        self.assertEqual([], _resume_reconciliation_reasons(mission_run))

        review_run = resume_run(status="ready")
        review_run["graph_state"]["node_states"]["N-REVIEW-M1"].update(
            {
                "phase": "running",
                "last_attempt_id": "ATT-REVIEW-1",
                "bound_worker_id": "RW-M1",
            }
        )
        review_run["review_workers"] = [
            {
                "worker_id": "RW-M1",
                "attempt_id": "ATT-REVIEW-1",
                "review_path": PARENT_PATH,
                "reviewed_sha": PARENT_HEAD,
                "phase": "worker_running",
            }
        ]
        self.assertEqual([], _resume_reconciliation_reasons(review_run))

    def test_ready_run_with_active_work_still_rejects_observed_drift(self) -> None:
        mission_run = resume_run(status="ready")
        bind_passed_worker(mission_run)
        mission_run["mission_states"]["M1"]["phase"] = "worker_running"
        mission_run["workers"][0].update(
            {"phase": "worker_running", "worker_head_sha": None}
        )
        mission_run["observed"]["git"]["worktrees"][-1]["dirty"] = True
        self.assertIn(
            "worktree_state_unreconciled",
            _resume_reconciliation_reasons(mission_run),
        )

        review_run = resume_run(status="ready")
        review_run["graph_state"]["node_states"]["N-REVIEW-M1"].update(
            {
                "phase": "running",
                "last_attempt_id": "ATT-REVIEW-1",
                "bound_worker_id": "RW-M1",
            }
        )
        review_run["review_workers"] = [
            {
                "worker_id": "RW-M1",
                "attempt_id": "ATT-REVIEW-1",
                "review_path": PARENT_PATH,
                "reviewed_sha": "f" * 40,
                "phase": "worker_running",
            }
        ]
        self.assertIn(
            "worker_state_unreconciled",
            _resume_reconciliation_reasons(review_run),
        )

    def test_sequential_parent_passed_worker_uses_its_bound_worktree(self) -> None:
        run = resume_run()
        bind_passed_worker(run, runtime="parent")
        run["mission_states"]["M1"]["head_sha"] = PARENT_HEAD
        run["workers"][0].update(
            {
                "worktree_path": PARENT_PATH,
                "branch_ref": f"refs/heads/{PARENT_BRANCH}",
                "worker_head_sha": PARENT_HEAD,
            }
        )
        run["observed"]["git"]["worktrees"] = [parent_worktree()]
        run["observed"]["git"]["worktrees"].append(
            {
                "path": "C:/repo/historical-detached",
                "branch_ref": None,
                "head_sha": "e" * 40,
                "managed_by": "parent",
                "dirty": True,
            }
        )

        self.assertEqual([], _resume_reconciliation_reasons(run))

    def test_ready_run_without_bound_work_is_not_a_resume_snapshot(self) -> None:
        run = resume_run(status="ready")
        run["observed"]["git"]["worktrees"] = []

        self.assertEqual([], _resume_reconciliation_reasons(run))


if __name__ == "__main__":
    unittest.main()
