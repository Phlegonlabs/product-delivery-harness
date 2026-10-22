"""Current validator contract after retiring execution ceremony."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import load_plan, plan_digest, validate_plan, validate_run
from harness_schema import AUTHORIZATION_KEYS
from harness_graph import _validate_graph, unactivated_review_repairs
from manifest_fixtures import valid_plan, valid_run, container_execution, conditional_final_candidate_plan


class ValidatorDietTests(unittest.TestCase):
    def test_retained_ceremony_keys_are_opaque(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run.update(launch_records={"old": "record"}, role_binding_updates=["old"],
                   runtime_metrics="history", review_lineages=None)
        runtime = run["runtime_capabilities"]
        runtime.update(permission_boundary="history", reviewer_tools=None,
                       nested_subagents=["history"], platform_lifecycle="history")
        adapter = runtime["runtime_adapter"]
        adapter.update(role_bindings="history", capability_probe=None)
        run["observed"].update(sandbox="history", host_runtime=None)
        self.assertEqual([], validate_run(plan, run))
        self.assertEqual(plan_digest(plan), run["plan"]["digest_sha256"])

    def test_optional_ceremony_keys_can_be_absent(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run.pop("review_lineages", None)
        run["observed"].pop("sandbox", None)
        run["runtime_capabilities"].pop("platform_lifecycle", None)
        self.assertEqual([], validate_run(plan, run))

    def test_container_declaration_reports_one_clear_error(self) -> None:
        plan = valid_plan()
        plan["missions"][0]["worker_verifiers"][0]["execution"] = container_execution()
        errors = validate_plan(plan)
        self.assertEqual(1, len(errors), errors)
        self.assertIn("must equal host", errors[0])

    def test_host_cannot_claim_parallel_execution_or_container_policy(self) -> None:
        for update, expected in (({"parallel_safe": True}, "must be false"),
                                 ({"sandbox": {}}, "must omit sandbox")):
            with self.subTest(update=update):
                plan = valid_plan()
                plan["final_gates"][0]["execution"].update(update)
                self.assertTrue(any(expected in error for error in validate_plan(plan)))

    def test_old_schema_pairs_require_their_pinned_bundle(self) -> None:
        for plan_version in (2, 3, 4, 5):
            plan = valid_plan()
            plan["schema_version"] = plan_version
            self.assertIn("pinned bundle", validate_plan(plan)[0])
        for run_version in range(2, 11):
            plan = valid_plan()
            run = valid_run(plan)
            run["schema_version"] = run_version
            self.assertIn("pinned bundle", validate_run(plan, run)[0])

    def test_run_retains_all_twelve_authorization_actions(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        self.assertEqual(12, len(AUTHORIZATION_KEYS))
        for key in AUTHORIZATION_KEYS:
            malformed = copy.deepcopy(run)
            malformed["authorizations"].pop(key)
            self.assertTrue(any("exactly match" in error or "missing keys" in error
                                for error in validate_run(plan, malformed)), key)

    def test_adopted_status_is_retained_history_only_on_old_pins(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        gate["status"] = "adopted"
        self.assertEqual([], validate_run(plan, run))
        gate["required_harness_version"] = "0.66.0"
        self.assertTrue(any("adopted is retained history only" in error for error in validate_run(plan, run)))

    def test_old_adopted_history_defers_current_dispatch(self) -> None:
        from test_select_ready_nodes import current_preintegration_review_state
        from select_ready_nodes import select_ready_nodes
        plan, run = current_preintegration_review_state()
        gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        gate.update(status="adopted", loaded_contract_digest=None)
        selected = select_ready_nodes(plan, run)
        self.assertEqual([], selected["dispatchable_nodes"])
        self.assertTrue(any("pinned_bundle_or_restart_required" in item["reason_codes"]
                            for item in selected["deferred_nodes"]))

    def test_digest_drift_still_requires_restart(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        gate.update(status="current", loaded_contract_digest="a" * 64,
                    installed_contract_digest="b" * 64)
        self.assertTrue(any("restart_required" in error for error in validate_run(plan, run)))
        gate["status"] = "restart_required"
        self.assertEqual([], validate_run(plan, run))


    def test_template_final_review_accepts_only_the_bounded_repair_budget(self) -> None:
        plan = load_plan(SCRIPTS_DIR.parent / "assets/templates/HARNESS_PLAN.template.md")
        review = next(node for node in plan["graph"]["nodes"] if node["id"] == "N-SECURITY-REVIEW")
        self.assertIn("fix_required", review["allowed_outcomes"])
        missions = {mission["id"]: mission for mission in plan["missions"]}
        verifier_ids = {verifier["id"] for verifier in [*plan["final_gates"], *missions["M1"]["worker_verifiers"]]}
        for attempts in (2, 1, 3):
            with self.subTest(attempts=attempts):
                review["max_attempts"] = attempts
                errors: list[str] = []
                _validate_graph(errors, plan["graph"], missions, verifier_ids,
                                require_bounded_review_repair=True, require_review_lineage=True)
                self.assertEqual(attempts == 2, not errors, errors)

    def test_conditional_final_review_has_one_consolidated_repair(self) -> None:
        plan = conditional_final_candidate_plan()
        self.assertEqual([], validate_plan(plan))
        run = valid_run(plan)
        review = next(node for node in plan["graph"]["nodes"] if node["id"] == "N-FINAL-REVIEW")
        self.assertEqual({"M4"}, unactivated_review_repairs(plan, review, run))
        run["graph_state"]["edge_states"]["E-FINAL-REPAIR"].update(status="traversed", traversals=1)
        self.assertEqual(set(), unactivated_review_repairs(plan, review, run))

    def test_conditional_repair_cannot_hide_an_active_or_unbounded_mission(self) -> None:
        for mutate in (
            lambda plan, run: run["mission_states"]["M4"].update(phase="ready"),
            lambda plan, run: run["graph_state"]["node_states"]["N-M4"].update(attempts=1),
            lambda plan, run: plan["graph"]["edges"][-2].update(max_traversals=2),
            lambda plan, run: plan.pop("review_policy"),
        ):
            plan = conditional_final_candidate_plan()
            run = valid_run(plan)
            mutate(plan, run)
            review = next(node for node in plan["graph"]["nodes"] if node["id"] == "N-FINAL-REVIEW")
            self.assertEqual(set(), unactivated_review_repairs(plan, review, run))

    def test_final_candidate_rejects_an_extra_repair_or_review_attempt(self) -> None:
        for attempts in (1, 3):
            plan = conditional_final_candidate_plan()
            review = next(node for node in plan["graph"]["nodes"] if node["id"] == "N-FINAL-REVIEW")
            review["max_attempts"] = attempts
            self.assertTrue(any("2 attempts" in error or "at most 2" in error for error in validate_plan(plan)))
        plan = conditional_final_candidate_plan()
        plan["graph"]["edges"][-2]["max_traversals"] = 2
        self.assertTrue(any("one bounded repair" in error for error in validate_plan(plan)))


if __name__ == "__main__":
    unittest.main()
