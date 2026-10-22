"""Run a bounded final review repair through real Git and host evidence."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

TESTS = Path(__file__).resolve().parent
for path in (TESTS, TESTS.parent):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import harness_transition as transition
import manifest_fixtures as mf
from harness_core import plan_digest
from harness_worker_result_transition import record_worker_result
from select_ready_nodes import select_ready_nodes
from test_security_review_result import valid_result
from verifier_runtime import observe_plan_host_runtimes, run_verifier


class ConditionalReviewJourneyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.container = Path(self.temp.name)
        self.root = self.container / "integration"
        self.root.mkdir()
        mf.init_repo(self.root, "README.md", default_branch="integration")
        self.plan = mf.conditional_final_candidate_plan()
        for mission in self.plan["missions"]:
            mission["tasks"] = mission["tasks"][:1]
            task = mission["tasks"][0]
            for declaration in [*task["verifiers"], *mission["worker_verifiers"], *mission["integration_verifiers"]]:
                declaration.update(argv=[sys.executable, "-c", "from pathlib import Path; assert Path('" + task["write_scope"][0] + "').is_file()"], read_only=True)
        mf.materialize_plan_sources(self.root, self.plan)
        mf.git(self.root, "add", "docs/product")
        mf.git(self.root, "commit", "-qm", "freeze approved sources")
        self.run = mf.valid_run(self.plan)
        mission_ids = [mission["id"] for mission in self.plan["missions"]]
        mf.authorize_execution(self.run, mission_ids)
        for action in ("spawn_subagents", "create_local_worktrees", "create_local_branches", "create_local_commits", "integrate_locally"):
            mf.authorize_action(self.run, action, mission_ids, ["*", "branch:integration"] if action == "integrate_locally" else ["*"])
        runtime = self.run["runtime_capabilities"]
        runtime.update(worker_runtime="subagent", max_parallel_workers=1)
        runtime["runtime_adapter"].update(available_drivers=["subagents", "sequential_parent"], detection_source="observed")
        self.run["integration"].update(branch="integration", batch_base_sha=None, integration_head_sha=None)
        self.run["landing"]["continuity"]["branch_ref"] = "refs/heads/integration"
        self.run["active_wave"].update(wave_id=None, status="idle", selected_missions=[], batch_base_sha=None)
        self.run["observed"]["captured_at"] = None
        self.run["observed"]["runtime"].update(available_worker_slots=1, isolation_capacity=1)

    def observe(self):
        transition._record_observation(self.plan, self.run, Namespace(repo_root=self.root))

    def integrate(self, mission_id):
        self.observe()
        base = mf.git(self.root, "rev-parse", "HEAD")
        transition._accept_wave(self.plan, self.run, Namespace(
            wave_id="WAVE-" + mission_id, mission_id=[mission_id], batch_base_sha=base, repo_root=self.root))
        checkout = self.container / mission_id
        branch = "worker-" + mission_id
        mf.git(self.root, "worktree", "add", "-qb", branch, str(checkout), base)
        lease, attempt, worker = "L-" + mission_id, "A-" + mission_id, "W-" + mission_id
        transition._lease_worker(self.plan, self.run, Namespace(
            mission_id=mission_id, node_id="N-" + mission_id, worker_id=worker,
            lease_id=lease, attempt_id=attempt, branch_ref="refs/heads/" + branch, worktree_path=checkout.as_posix(), report_path=None))
        mission = next(item for item in self.plan["missions"] if item["id"] == mission_id)
        task = mission["tasks"][0]
        relative = task["write_scope"][0]
        source = checkout / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("VALUE = 1\n", encoding="utf-8")
        mf.git(checkout, "add", relative)
        mf.git(checkout, "commit", "-qm", "implement " + mission_id)
        head = mf.git(checkout, "rev-parse", "HEAD")
        declaration = task["verifiers"][0]
        preflights, errors = observe_plan_host_runtimes({"final_gates": [declaration]}, checkout)
        self.assertEqual([], errors)
        context = {
            "run_id": self.run["run_id"], "plan_revision": self.plan["revision"],
            "plan_digest_sha256": plan_digest(self.plan), "graph_revision": self.run["graph_state"]["graph_revision"],
            "batch_base_sha": base, "head_sha": head, "changed_files": [relative],
            "trust_domain": "parent_local", "checkout_role": "worker", "checkout_dirty": False,
            "cache_safe": False, "layer": "task", "mission_id": mission_id,
            "task_id": task["id"], "attempt_id": "CHECK-" + mission_id, "lease_id": lease,
        }
        execution = run_verifier(declaration, context, checkout_root=checkout,
            timeout_seconds=15, host_preflight=preflights[0],
            git_guard={"expected_branch": branch, "expected_head_sha": head, "ignored_paths": []})
        self.assertEqual("PASS", execution["status"], execution["stderr"])
        worker_context = {**context, "layer": "worker", "task_id": None, "attempt_id": "WORKER-CHECK-" + mission_id}
        worker_declaration = mission["worker_verifiers"][0]
        worker_execution = run_verifier(worker_declaration, worker_context, checkout_root=checkout,
            timeout_seconds=15, host_preflight=preflights[0],
            git_guard={"expected_branch": branch, "expected_head_sha": head, "ignored_paths": []})
        self.assertEqual("PASS", worker_execution["status"], worker_execution["stderr"])
        result = {
            "type": "WORKER_RESULT", "run_id": self.run["run_id"], "plan_id": self.plan["plan_id"],
            "mission_id": mission_id, "lease_id": lease, "status": "worker_passed", "current_task_id": None,
            "plan_revision": self.plan["revision"], "plan_digest_sha256": plan_digest(self.plan),
            "base_sha": base, "head_sha": head, "diff_summary": "Implement the assigned file.",
            "changed_files": [relative], "commits": [head], "evidence_paths": [], "blockers": [],
            "residual_risks": [], "integration_notes": "",
            "task_results": [{"task_id": task["id"], "status": "worker_passed", "head_sha": head,
                "verifier_ids": [declaration["id"]], "commits": [head], "evidence_paths": []}],
            "verifiers": [{"id": item["verifier_id"], "status": "PASS", "evidence": item["execution_key"]} for item in (execution, worker_execution)],
        }
        node_result = {
            "run_id": self.run["run_id"], "plan_id": self.plan["plan_id"], "node_id": "N-" + mission_id,
            "attempt_id": attempt, "plan_revision": self.plan["revision"], "plan_digest_sha256": plan_digest(self.plan),
            "graph_revision": context["graph_revision"], "batch_base_sha": base,
            "status": "succeeded", "outcome": "pass", "worker_result": result,
            "refinement_request": None, "evidence_paths": [],
        }
        node_path, verifier_path = self.container / (mission_id + ".json"), self.container / (mission_id + "-execution.json")
        node_path.write_text(json.dumps({"node_result": node_result}), encoding="utf-8")
        verifier_path.write_text(json.dumps(execution), encoding="utf-8")
        worker_verifier_path = self.container / (mission_id + "-worker-execution.json")
        worker_verifier_path.write_text(json.dumps(worker_execution), encoding="utf-8")
        self.observe()
        record_worker_result(self.plan, self.run, Namespace(repo_root=self.root, node_result=node_path,
            worker_result=None, verifier_result=[verifier_path, worker_verifier_path]))
        self.assertEqual("worker_passed", self.run["mission_states"][mission_id]["phase"], self.run["mission_states"][mission_id])
        mf.git(self.root, "merge", "--ff-only", branch)
        self.observe()
        integration_context = {**context, "layer": "mission_integration", "checkout_role": "integration",
            "task_id": None, "attempt_id": None, "lease_id": None}
        integration_execution = run_verifier(mission["integration_verifiers"][0], integration_context,
            checkout_root=self.root, timeout_seconds=15, host_preflight=preflights[0],
            git_guard={"expected_branch": "integration", "expected_head_sha": head,
                "ignored_paths": sorted(transition._coordination_ignored_paths(self.root, None, self.run))})
        self.assertEqual("PASS", integration_execution["status"], integration_execution["stderr"])
        integration_path = self.container / (mission_id + "-integration-execution.json")
        integration_path.write_text(json.dumps(integration_execution), encoding="utf-8")
        transition._record_integration(self.plan, self.run, Namespace(
            mission_id=mission_id, integrated_sha=head, repo_root=self.root, verifier_result=[integration_path]))
        transition._close_wave(self.run, Namespace(source="test integration finished"))

    def review(self, attempt, outcome):
        self.observe()
        transition._reserve_review_dispatch(self.plan, self.run, Namespace(
            node_id="N-FINAL-REVIEW", worker_id="RW-" + attempt, attempt_id=attempt, report_path=None), repo_root=self.root)
        head = self.run["integration"]["integration_head_sha"]
        security = valid_result(head, self.run["integration"]["batch_base_sha"])
        security["scope"] = ["src/**"]
        path = self.container / (attempt + "-security.json")
        path.write_text(json.dumps(security), encoding="utf-8")
        transition._record_review_attempt(self.plan, self.run, Namespace(
            lineage="REVIEW-FINAL", attempt_id=attempt, worker_id="RW-" + attempt,
            result=outcome, security_result=path, repo_root=self.root, mission_id=None,
            finding=[] if outcome == "pass" else ["Consolidated backend repair is required."],
            evidence=["Synthetic reviewer inspected the exact toy candidate."], tree_sha=None))

    def test_first_pass_does_not_activate_repair(self):
        for mission in ("M1", "M3", "M2"):
            self.integrate(mission)
        self.review("REVIEW-1", "pass")
        self.assertEqual("queued", self.run["mission_states"]["M4"]["phase"])
        self.assertEqual("succeeded", self.run["graph_state"]["node_states"]["N-FINAL-REVIEW"]["phase"])
        self.assertEqual([], [item for item in select_ready_nodes(self.plan, self.run, repo_root=self.root)["dispatchable_nodes"] if item["node_id"] == "N-M4"])

    def test_one_repair_then_pass_and_failed_recheck_stops(self):
        for mission in ("M1", "M3", "M2"):
            self.integrate(mission)
        self.review("REVIEW-1", "fix_required")
        self.integrate("M4")
        repaired = copy.deepcopy(self.run)
        self.review("REVIEW-2", "pass")
        self.assertEqual("succeeded", self.run["graph_state"]["node_states"]["N-FINAL-REVIEW"]["phase"])
        self.run = repaired
        self.review("REVIEW-2-FAILED", "fix_required")
        selection = select_ready_nodes(self.plan, self.run, repo_root=self.root)
        self.assertFalse(any(item["node_id"] in {"N-M4", "N-FINAL-REVIEW"} for item in selection["dispatchable_nodes"]))
        self.assertEqual(2, self.run["graph_state"]["node_states"]["N-FINAL-REVIEW"]["attempts"])
        self.assertEqual("exhausted", self.run["graph_state"]["edge_states"]["E-FINAL-REPAIR"]["status"])


if __name__ == "__main__":
    unittest.main()
