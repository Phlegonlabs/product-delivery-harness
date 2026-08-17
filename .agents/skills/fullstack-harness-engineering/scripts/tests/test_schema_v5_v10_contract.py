import copy
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = SKILL_ROOT.parent
REPO_ROOT = next(
    candidate
    for candidate in (SKILL_ROOT, *SKILL_ROOT.parents)
    if (candidate / "README.md").is_file()
    and (candidate / "scripts" / "sync_plugin_skills.py").is_file()
)
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import load_plan, load_run  # noqa: E402
from harness_manifest import validate_plan, validate_run  # noqa: E402


class SchemaV5V10ContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def read_sibling_skill(self, name: str) -> str:
        return (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")

    def canonical_manifest(self, relative_path: str, key: str) -> dict:
        path = SKILL_ROOT / relative_path
        if key == "harness_plan":
            return load_plan(path)
        if key == "harness_run":
            return load_run(path)
        self.fail(f"unsupported canonical manifest key: {key}")

    def test_current_schema_versions_and_backward_readability(self) -> None:
        skill = self.read("SKILL.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        run = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        for content in (skill, plan):
            self.assertIn("PLAN schema v5", content)
        for content in (skill, run):
            self.assertIn("RUN schema v10", content)
        self.assertIn('"schema_version": 5', plan)
        self.assertIn('"schema_version": 10', run)
        self.assertIn("Older PLAN schemas remain readable", plan)
        self.assertIn("Older RUN schemas remain readable", run)
        for stale in ("current-v4", "current-v9"):
            self.assertNotIn(stale, skill)
            self.assertNotIn(stale, plan)
            self.assertNotIn(stale, run)


    def test_plan_v5_examples_freeze_sources_and_acceptance_rows(self) -> None:
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")

        self.assertIn('"staged_revision": null', plan)
        self.assertIn("not an executable publication", plan)
        self.assertIn('"test_id": "TEST-M1-T01-001"', plan)
        self.assertIn('"trace_ids": [', plan)
        self.assertIn('"criterion":', plan)
        self.assertIn("Publish the accepted revision to the canonical source location", plan)
        self.assertIn("immutable bytes", plan)
        self.assertIn("URLs are never fetched", plan)





    def test_neutral_single_mission_managed_sequential_graph(self) -> None:
        plan = self.canonical_manifest(
            "assets/templates/HARNESS_PLAN.template.md", "harness_plan"
        )
        nodes = {node["id"]: node for node in plan["graph"]["nodes"]}
        edges = {edge["id"]: edge for edge in plan["graph"]["edges"]}
        missions = {mission["id"]: mission for mission in plan["missions"]}

        self.assertEqual(["M1"], list(missions))
        self.assertEqual(1, plan["max_parallel_workers"])
        self.assertEqual([], plan["batch_verifiers"])
        self.assertEqual("mission", nodes["N-M1"]["kind"])
        self.assertEqual("preintegration", nodes["N-M1-REVIEW"]["review"]["stage"])
        self.assertEqual(["M1"], nodes["N-M1-REVIEW"]["review"]["mission_ids"])
        self.assertEqual("backend_code", nodes["N-M1-REVIEW"]["review"]["type"])
        for node_id in ("N-M1", "N-M1-REVIEW"):
            runtime = nodes[node_id]["runtime"]
            self.assertIsNone(runtime["preferred_provider"])
            self.assertEqual(
                {"codex", "claude_code", "pi", "generic"},
                set(runtime["allowed_providers"]),
            )
            self.assertEqual(
                {"model": None, "reasoning_effort": None},
                runtime["provider_options"]["pi"],
            )
            self.assertEqual(
                {"model": None, "reasoning_effort": None},
                runtime["provider_options"]["generic"],
            )
        self.assertEqual("N-M1-REVIEW", edges["E-M1-REVIEW"]["to"])
        self.assertEqual("N-FINAL-GATE", edges["E-M1-REVIEW-FINAL"]["to"])
        self.assertEqual("N-CLOSEOUT-GATE", edges["E-FINAL-CLOSEOUT"]["to"])
        self.assertNotIn("execution_route", plan)
        self.assertTrue(missions["M1"]["tasks"][0]["acceptance_matrix"])




    def test_lazy_pillow_and_readme_current_outputs_are_documented(self) -> None:
        verification = self.read("references/verification-gates.md")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("Pillow is imported lazily", verification)
        self.assertIn("targeted UI-evidence decoding error", verification)
        self.assertIn("without preventing non-UI CLIs from starting", verification)
        self.assertIn("accepted Git `head_sha`", verification)
        self.assertIn("PLAN v5", readme)
        self.assertIn("RUN v10", readme)
        self.assertIn("`design-system.md`, `design-system.json`", readme)


if __name__ == "__main__":
    unittest.main()
