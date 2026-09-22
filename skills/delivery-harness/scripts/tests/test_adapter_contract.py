import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from harness_core import resolve_runtime_options, route_runtime_driver
from harness_manifest import validate_run
from harness_schema import RUNTIME_DRIVERS
from manifest_fixtures import native_capability_probe, valid_plan, valid_run

HOSTS = ("generic", "codex", "claude_code", "pi", "zcode", "new_host")


class AdapterContractTests(unittest.TestCase):
    def delegated_run(self, host, driver="subagents"):
        plan = valid_plan()
        run = valid_run(plan)
        run["status"] = "running"
        runtime = run["runtime_capabilities"]
        runtime.update({
            "worker_runtime": "app_task" if driver == "app_threads" else "subagent",
            "workspace_mode": "app_managed_worktree" if driver == "app_threads" else "parent_managed_worktree",
            "completion_channel": "thread_poll" if driver == "app_threads" else "agent_result",
        })
        runtime["runtime_adapter"].update({
            "provider": host,
            "available_drivers": [driver, "sequential_parent"],
            "detection_source": "observed",
            "capability_probe": native_capability_probe(
                app_threads=driver == "app_threads", subagents=driver == "subagents"),
        })
        return plan, run

    def test_every_host_accepts_the_same_native_capabilities(self):
        for host in HOSTS:
            for driver in ("subagents", "app_threads"):
                with self.subTest(host=host, driver=driver):
                    plan, run = self.delegated_run(host, driver)
                    self.assertEqual([], validate_run(plan, run))
                    self.assertEqual(driver, route_runtime_driver(run["runtime_capabilities"]))

    def test_host_identity_never_selects_a_model(self):
        for host in HOSTS:
            with self.subTest(host=host):
                options = resolve_runtime_options({}, host)
                self.assertIsNone(options["model"])
                self.assertIsNone(options["reasoning_effort"])
                explicit = {"provider_options": {host: {"model": "chosen-model", "reasoning_effort": "high"}}}
                self.assertEqual("chosen-model", resolve_runtime_options(explicit, host)["model"])
                self.assertEqual("high", resolve_runtime_options(explicit, host)["reasoning_effort"])

    def test_observed_order_not_provider_priority_selects_driver(self):
        for host in HOSTS:
            for drivers in (["subagents", "app_threads", "sequential_parent"], ["app_threads", "subagents", "sequential_parent"]):
                runtime = {"runtime_adapter": {"provider": host, "available_drivers": drivers}}
                self.assertEqual(drivers[0], route_runtime_driver(runtime))

    def test_missing_capability_never_becomes_a_delegated_route(self):
        for host in HOSTS:
            for source in ("observed", "explicit", "fallback"):
                with self.subTest(host=host, source=source):
                    plan, run = self.delegated_run(host)
                    adapter = run["runtime_capabilities"]["runtime_adapter"]
                    adapter.pop("capability_probe")
                    adapter["detection_source"] = source
                    self.assertTrue(any("capability_snapshot_incomplete" in e for e in validate_run(plan, run)))

    def test_unavailable_or_unobserved_result_surface_blocks(self):
        for status in ("unavailable", "unobserved"):
            plan, run = self.delegated_run("new_host")
            run["runtime_capabilities"]["runtime_adapter"]["capability_probe"]["direct_agent_result"]["status"] = status
            self.assertTrue(any("capability_snapshot_incomplete" in e for e in validate_run(plan, run)))

    def test_unrelated_surfaces_do_not_need_an_inventory(self):
        plan, run = self.delegated_run("new_host")
        probe = run["runtime_capabilities"]["runtime_adapter"]["capability_probe"]
        for key in list(probe):
            if key.startswith("app_"):
                del probe[key]
        self.assertEqual([], validate_run(plan, run))

    def test_browser_probe_accepts_observed_surface_for_any_host(self):
        for host in HOSTS:
            plan, run = self.delegated_run(host)
            capability = {"status": "available", "provider": host, "driver": "subagents",
                          "surface": "native_browser", "probe_scope": "reviewer_session",
                          "session_id": "reviewer-1", "evidence": "reviewer inspected target and returned expected title"}
            run["runtime_capabilities"]["reviewer_tools"] = {"chrome_devtools": capability}
            self.assertEqual([], validate_run(plan, run))
            for invalid in ("none", "unknown", "unobserved"):
                capability["surface"] = invalid
                self.assertTrue(any("observed browser surface" in e for e in validate_run(plan, run)))
            capability["surface"] = "native_browser"
            capability["probe_scope"] = "parent_session"
            self.assertTrue(any("reviewer_session probe" in e for e in validate_run(plan, run)))

    def test_invalid_driver_order_cannot_hide_delegated_capabilities(self):
        for drivers in (["sequential_parent", "subagents"], ["subagents", "subagents", "sequential_parent"]):
            plan, run = self.delegated_run("new_host")
            run["runtime_capabilities"]["runtime_adapter"]["available_drivers"] = drivers
            self.assertTrue(any("available_drivers" in e for e in validate_run(plan, run)))

    def test_retired_native_driver_and_state_are_rejected(self):
        self.assertNotIn("dynamic_workflow", RUNTIME_DRIVERS)
        plan, run = self.delegated_run("claude_code")
        run["runtime_capabilities"]["runtime_adapter"]["available_drivers"] = ["dynamic_workflow", "sequential_parent"]
        self.assertTrue(any("unsupported drivers" in e for e in validate_run(plan, run)))
        plan, run = self.delegated_run("claude_code")
        run["workflow_runs"] = []
        self.assertTrue(any("unknown keys: workflow_runs" in e for e in validate_run(plan, run)))

    def test_generic_contract_preserves_boundaries_without_provider_sections(self):
        text = (SKILL_ROOT / "references/runtime-adapters.md").read_text(encoding="utf-8")
        self.assertNotIn("## Provider:", text)
        for phrase in ("dispatchable_nodes[].required_actions", "Never infer extra authorization",
                       "No worker or reviewer spawns another agent", "Never run parallel writers in `shared_checkout`",
                       "exact unified integration SHA", "reserve-review-dispatch", "reviewer_session",
                       "Serialized Same-Repository Host Handoff", "never automatically create a duplicate",
                       "cannot satisfy a fresh independent review", "installed defaults"):
            self.assertIn(phrase, text)

    def test_removed_native_templates_are_absent(self):
        paths = [SKILL_ROOT / "assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js",
                 SKILL_ROOT / "assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js",
                 SKILL_ROOT.parent / "product-definition-builder/assets/templates/CLAUDE_PRD_WORKFLOW.template.js"]
        for path in paths:
            self.assertFalse(path.exists(), path)


if __name__ == "__main__":
    unittest.main()
