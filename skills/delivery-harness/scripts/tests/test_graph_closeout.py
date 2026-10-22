#!/usr/bin/env python3
"""RUN closeout accepts the graph state that real transitions leave behind.

Transitions mark only the route edges they take. Dependency edges, routes
whose outcome never happened, and repair nodes behind those routes stay
dormant, and closeout must accept that without hand-edited graph state.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_transition  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
import verifier_runtime as vr  # noqa: E402
from harness_manifest import load_run, validate_run  # noqa: E402


NODE_ERROR = "complete graph run requires every node to succeed, skip, or be superseded"
EDGE_ERROR = "complete graph run requires every edge to be terminal"
MISSION_ERROR = "complete run requires every mission to be integrated or superseded"


def add_repair_approval(plan: dict) -> None:
    """A bounded fix_required repair loop on M1's review that a clean pass skips."""

    plan["graph"]["nodes"].append(
        {
            "id": "N-FIX",
            "kind": "approval",
            "ref": "fix-m1",
            "executor": "human",
            "allowed_outcomes": ["pass", "blocked"],
            "max_attempts": 1,
            "runtime": None,
        }
    )
    plan["graph"]["edges"].extend(
        [
            {
                "id": "E-REVIEW-M1-FIX",
                "kind": "route",
                "from": "N-REVIEW-M1",
                "to": "N-FIX",
                "on_outcomes": ["fix_required"],
                "max_traversals": 1,
            },
            {
                "id": "E-FIX-REREVIEW",
                "kind": "route",
                "from": "N-FIX",
                "to": "N-REVIEW-M1",
                "on_outcomes": ["pass"],
                "max_traversals": 1,
            },
        ]
    )


def dormant_edge() -> dict:
    return {"status": "dormant", "traversals": 0, "source_attempt_id": None}


class CloseoutRuleTests(unittest.TestCase):
    def complete_pair(self, fix_dependency: bool = False) -> tuple[dict, dict]:
        plan = mf.valid_plan()
        add_repair_approval(plan)
        if fix_dependency:
            # The repair node also waits on a node that ran.
            plan["graph"]["edges"].append(
                {"id": "E-M1-FIX", "kind": "dependency", "from": "N-M1", "to": "N-FIX"}
            )
        run = mf.valid_closeout_run(plan)
        mf.mark_complete(plan, run)
        # Undo what mark_complete writes but no transition does.
        run["graph_state"]["node_states"]["N-FIX"].update(
            {
                "phase": "dormant",
                "attempts": 0,
                "last_attempt_id": None,
                "last_outcome": None,
                "bound_worker_id": None,
            }
        )
        for edge in plan["graph"]["edges"]:
            if edge["kind"] == "dependency" or "N-FIX" in (edge["from"], edge["to"]):
                run["graph_state"]["edge_states"][edge["id"]] = dormant_edge()
        return plan, run

    def test_dormant_dependencies_and_an_unused_repair_loop_close(self) -> None:
        plan, run = self.complete_pair()
        self.assertEqual([], validate_run(plan, run))

    def test_a_dependency_does_not_activate_an_untaken_repair_route(self) -> None:
        plan, run = self.complete_pair(fix_dependency=True)
        # Its fix_required route never fired, so closeout must not wait for it.
        self.assertEqual([], validate_run(plan, run))

    def test_a_pending_node_on_the_taken_path_still_blocks(self) -> None:
        plan, run = self.complete_pair()
        run["graph_state"]["node_states"]["N-FINAL"].update(
            {"phase": "ready", "last_attempt_id": None, "last_outcome": None}
        )
        self.assertTrue(
            any(NODE_ERROR in error for error in validate_run(plan, run))
        )

    def test_a_touched_repair_node_still_blocks(self) -> None:
        plan, run = self.complete_pair()
        run["graph_state"]["node_states"]["N-FIX"]["phase"] = "ready"
        self.assertTrue(
            any(NODE_ERROR in error for error in validate_run(plan, run))
        )

    def test_a_matched_route_left_untraversed_still_blocks(self) -> None:
        plan, run = self.complete_pair()
        # The review passed, so its pass route must have been taken.
        run["graph_state"]["edge_states"]["E-M1-REVIEW-PASS"] = dormant_edge()
        self.assertTrue(
            any(EDGE_ERROR in error for error in validate_run(plan, run))
        )

    def test_an_untraversed_route_from_an_unfinished_source_still_blocks(self) -> None:
        plan, run = self.complete_pair()
        run["graph_state"]["node_states"]["N-REVIEW-M1"].update(
            {"phase": "running", "last_outcome": None}
        )
        errors = validate_run(plan, run)
        self.assertTrue(any(EDGE_ERROR in error for error in errors), errors)
        self.assertTrue(any(NODE_ERROR in error for error in errors), errors)

    def test_a_queued_mission_on_the_taken_path_still_blocks(self) -> None:
        plan, run = self.complete_pair()
        run["mission_states"]["M2"]["phase"] = "queued"
        self.assertTrue(
            any(MISSION_ERROR in error for error in validate_run(plan, run))
        )


SESSION = "closeout-walk"


def host_gate(identifier: str) -> dict:
    return {
        "id": identifier,
        "cwd": ".",
        "argv": [sys.executable, "-c", "print('gate ok')"],
        "pass_signal": "exit 0",
        "execution": {"isolation": "host", "parallel_safe": False, "resources": []},
    }


def walk_plan() -> dict:
    """One mission, its review and gates, plus a repair mission a pass skips."""

    plan = mf.valid_plan()
    m1 = plan["missions"][0]
    repair = mf.mission(
        "M3",
        "REQ-001",
        "src/a/**",
        [mf.task("M3", 1, "REQ-001", "src/a/one.py")],
        priority=70,
        merge_rank=30,
    )
    plan["missions"] = [m1, repair]
    plan["traces"] = [trace for trace in plan["traces"] if trace["id"] == "REQ-001"]
    plan["max_parallel_workers"] = 1
    plan["batch_verifiers"] = [host_gate("batch")]
    plan["final_gates"] = [host_gate("final")]
    plan["graph"] = mf.graph_for(m1)
    repair_review = mf.graph_node(
        "N-REVIEW-M3",
        "verifier",
        "batch",
        "runtime_worker",
        ["pass", "fix_required", "retryable_failure", "blocked", "contract_gap"],
    )
    repair_review["review"] = {
        "type": "backend_code",
        "lineage_id": "REVIEW-M3",
        "mission_ids": ["M3"],
        "scope": ["src/a/**"],
        "required_evidence": ["reviewed_sha", "findings"],
    }
    plan["graph"]["nodes"].extend(
        [
            mf.graph_node(
                "N-M3",
                "mission",
                "M3",
                "runtime_worker",
                ["pass", "retryable_failure", "blocked", "contract_gap"],
            ),
            repair_review,
        ]
    )
    plan["graph"]["edges"].extend(
        [
            {
                "id": "E-REVIEW-M1-REPAIR",
                "kind": "route",
                "from": "N-REVIEW-M1",
                "to": "N-M3",
                "on_outcomes": ["fix_required"],
                "max_traversals": 1,
            },
            {
                "id": "E-M3-REVIEW",
                "kind": "dependency",
                "from": "N-M3",
                "to": "N-REVIEW-M3",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            },
            {
                "id": "E-REPAIR-REREVIEW",
                "kind": "route",
                "from": "N-REVIEW-M3",
                "to": "N-REVIEW-M1",
                "on_outcomes": ["pass"],
                "max_traversals": 1,
            },
        ]
    )
    return plan


class CliCloseoutWalkTests(unittest.TestCase):
    """Drive graph state to closeout with real transitions only."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.gitroot = self.root / "git"
        self.gitroot.mkdir(parents=True)
        self.plan = walk_plan()
        mf.materialize_plan_sources(self.gitroot, self.plan)
        mf.init_repo(self.gitroot, "file.txt")
        mf.git(self.gitroot, "checkout", "-qb", "integration")
        (self.gitroot / "file.txt").write_text("work\n", encoding="utf-8")
        mf.git(self.gitroot, "add", ".")
        mf.git(self.gitroot, "commit", "-qm", "work")
        self.head = mf.git(self.gitroot, "rev-parse", "HEAD")
        self.wt1 = (self.root / "wt-m1").as_posix()

        run = mf.valid_run(self.plan)
        missions = ["M1", "M3"]
        mf.authorize_execution(run, missions)
        mf.authorize_action(
            run, "spawn_subagents", missions, ["*", "worker:W-M1-A", "worker:RW-1"]
        )
        mf.authorize_action(
            run, "create_local_worktrees", missions, ["*", f"worktree:{self.wt1}"]
        )
        for action in ("create_local_branches", "create_local_commits"):
            mf.authorize_action(
                run, action, missions, ["*", "branch:refs/heads/wt/m1"]
            )
        mf.authorize_action(run, "integrate_locally", ["M1"], ["branch:integration"])
        run["integration"]["branch"] = "integration"
        run["integration"]["integration_head_sha"] = None
        run["landing"]["continuity"]["branch_ref"] = "refs/heads/integration"
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter["available_drivers"] = ["subagents", "sequential_parent"]
        adapter["detection_source"] = "observed"
        adapter["capability_probe"] = mf.native_capability_probe(subagents=True)
        run["runtime_capabilities"]["worker_runtime"] = "subagent"
        run["runtime_capabilities"]["max_parallel_workers"] = 1
        self.plan_path = self.root / "PLAN.md"
        self.run_path = self.root / "RUN.md"
        self.plan_path.write_text(
            mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", self.plan),
            encoding="utf-8",
        )
        self.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )
        self.step("acquire-run-lock")
        self.observe()

    def step(self, *args: str, repo_root: bool = False) -> None:
        common = ["--plan", str(self.plan_path), "--run", str(self.run_path)]
        if repo_root:
            common += ["--repo-root", str(self.gitroot)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = harness_transition.main(
                [*common, "--session-id", SESSION, *args]
            )
        self.assertEqual(0, code, output.getvalue())

    def edit_run(self) -> dict:
        return load_run(self.run_path)

    def save_run(self, run: dict) -> None:
        self.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )

    def observe(self) -> None:
        self.step("record-observation", repo_root=True)
        # Container verifiers are never run here; seed their exact probe.
        live = self.edit_run()
        live["observed"]["sandbox"] = mf.sandbox_observation(self.plan)
        live["observed"]["sandbox"]["captured_at"] = live["observed"].get("captured_at")
        self.save_run(live)

    def run_gate(self, node_id: str) -> None:
        request_path = self.root / f"{node_id}-request.json"
        result_path = self.root / f"{node_id}-result.json"
        self.step(
            "reserve-node-attempt",
            "--node-id",
            node_id,
            "--attempt-id",
            f"ATT-{node_id}",
            "--request-out",
            str(request_path),
            repo_root=True,
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = vr.main(["--request", str(request_path)])
        self.assertEqual(0, code, output.getvalue())
        self.assertEqual("PASS", json.loads(output.getvalue())["status"])
        result_path.write_text(output.getvalue(), encoding="utf-8")
        self.step(
            "record-node-result",
            "--node-id",
            node_id,
            "--attempt-id",
            f"ATT-{node_id}",
            "--outcome",
            "pass",
            "--evidence",
            "gate exited 0",
            "--verifier-result",
            str(result_path),
            repo_root=True,
        )

    def test_transitions_alone_reach_a_valid_closeout(self) -> None:
        self.step(
            "accept-wave", "--wave-id", "W-1", "--mission-id", "M1",
            "--batch-base-sha", self.head, repo_root=True,
        )
        mf.git(self.gitroot, "worktree", "add", "-b", "wt/m1", self.wt1, self.head)
        self.observe()
        self.step(
            "lease-worker",
            "--mission-id", "M1", "--node-id", "N-M1",
            "--worker-id", "W-M1-A", "--lease-id", "L-M1",
            "--attempt-id", "A-M1", "--branch-ref", "refs/heads/wt/m1",
            "--worktree-path", self.wt1,
            "--provider", "codex", "--driver", "subagents",
        )
        # The worker payload is recorded as test_close_wave does; it touches
        # mission, worker and verifier records, never graph_state.
        live = self.edit_run()
        live["mission_states"]["M1"].update(
            {"phase": "worker_passed", "head_sha": self.head}
        )
        worker = next(w for w in live["workers"] if w["worker_id"] == "W-M1-A")
        worker.update({"phase": "worker_passed", "worker_head_sha": self.head})
        live["attempt_log"].append(
            {
                "attempt_id": "A-M1-RESULT",
                "mission_id": "M1",
                "task_id": None,
                "lease_id": "L-M1",
                "kind": "worker",
                "result": "pass",
                "evidence": ["worker passed"],
                "review_lineage_id": None,
                "failure_family_ids": [],
            }
        )
        mission = self.plan["missions"][0]
        live["verifier_executions"] = [
            mf.retained_gate_execution(
                self.plan, live, mission["worker_verifiers"][0],
                layer="worker", execution_id="EXEC-W-M1", mission_id="M1",
                attempt_id="A-M1-RESULT", lease_id="L-M1", head_sha=self.head,
                checkout_role="worker",
            ),
            mf.retained_gate_execution(
                self.plan, live, mission["integration_verifiers"][0],
                layer="mission_integration", execution_id="EXEC-I-M1",
                mission_id="M1", attempt_id=None, lease_id=None,
                head_sha=self.head,
            ),
        ]
        for task in mission["tasks"]:
            task_attempt = f"A-{task['id'].replace('/', '-')}"
            live["task_states"][task["id"]].update(
                {
                    "phase": "mission_recorded",
                    "verifier_status": "PASS",
                    "commit_sha": self.head,
                }
            )
            live["attempt_log"].append(
                {
                    "attempt_id": task_attempt,
                    "mission_id": "M1",
                    "task_id": task["id"],
                    "lease_id": "L-M1",
                    "kind": "task_verifier",
                    "result": "PASS",
                    "evidence": [],
                }
            )
            live["verifier_executions"].append(
                mf.retained_gate_execution(
                    self.plan, live, task["verifiers"][0],
                    layer="task", execution_id=f"EXEC-{task_attempt}",
                    mission_id="M1", task_id=task["id"],
                    attempt_id=task_attempt, lease_id="L-M1",
                    head_sha=self.head, checkout_role="worker",
                )
            )
        self.save_run(live)

        self.step(
            "reserve-review-dispatch", "--node-id", "N-REVIEW-M1",
            "--worker-id", "RW-1", "--attempt-id", "RA-1", repo_root=True,
        )
        self.step(
            "record-review-attempt", "--lineage", "REVIEW-M1",
            "--attempt-id", "RA-1", "--worker-id", "RW-1",
            "--mission-id", "M1", "--result", "pass", "--evidence", "reviewed",
        )
        self.step(
            "record-integration", "--mission-id", "M1",
            "--integrated-sha", self.head, repo_root=True,
        )
        self.step("close-wave", "--source", "wave W-1 fully resolved")
        self.run_gate("N-REVIEW-PASS-M1")
        self.run_gate("N-FINAL")

        run = self.edit_run()
        edges = run["graph_state"]["edge_states"]
        nodes = run["graph_state"]["node_states"]
        # No transition marks these, and closeout must not need it to.
        for edge_id in (
            "E-M1-REVIEW",
            "E-M1-REVIEW-PASS-FINAL",
            "E-REVIEW-M1-REPAIR",
            "E-REPAIR-REREVIEW",
        ):
            self.assertEqual("dormant", edges[edge_id]["status"], edge_id)
        self.assertEqual("traversed", edges["E-M1-REVIEW-PASS"]["status"])
        self.assertEqual("dormant", nodes["N-M3"]["phase"])
        self.assertEqual("queued", run["mission_states"]["M3"]["phase"])

        # Parent-owned closeout bookkeeping; graph_state stays as recorded.
        run["landing"]["continuity"].update(
            {"status": "preserved", "head_sha": self.head}
        )
        run["status"] = "complete"
        self.assertEqual([], validate_run(self.plan, run))


if __name__ == "__main__":
    unittest.main()
