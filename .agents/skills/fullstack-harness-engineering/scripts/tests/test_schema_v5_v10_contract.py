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

    def test_canonical_plan_and_run_manifests_are_aligned(self) -> None:
        plan = self.canonical_manifest(
            "assets/templates/HARNESS_PLAN.template.md", "harness_plan"
        )
        run = self.canonical_manifest(
            "assets/templates/MISSION_RUNBOOK.template.md", "harness_run"
        )

        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, run))
        self.assertEqual(5, plan["schema_version"])
        self.assertEqual(10, run["schema_version"])
        release_fields = {
            "id",
            "stage",
            "source",
            "artifact_kind",
            "requires_signing",
            "channel",
            "data_mode",
            "trigger",
            "migration_classification",
            "commands",
            "prerequisites",
            "smoke_verifiers",
        }
        targets = plan["release"]["targets"]
        self.assertTrue(all(set(target) == release_fields for target in targets))
        self.assertTrue(
            all(set(target["commands"]) == {"build", "migrate", "publish"} for target in targets)
        )
        self.assertEqual({"development", "production"}, {target["stage"] for target in targets})
        self.assertEqual({target["id"] for target in targets}, set(run["targets"]))

        acceptance = plan["missions"][0]["tasks"][0]["acceptance_matrix"][0]
        self.assertEqual({"test_id", "trace_ids", "criterion"}, set(acceptance))
        self.assertEqual(
            {node["id"] for node in plan["graph"]["nodes"]},
            set(run["graph_state"]["node_states"]),
        )
        self.assertEqual(
            {edge["id"] for edge in plan["graph"]["edges"]},
            set(run["graph_state"]["edge_states"]),
        )

    def test_plan_v5_examples_freeze_sources_and_acceptance_rows(self) -> None:
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")

        self.assertIn('"staged_revision": null', plan)
        self.assertIn("not an executable publication", plan)
        self.assertIn('"test_id": "TEST-M1-T01-001"', plan)
        self.assertIn('"trace_ids": [', plan)
        self.assertIn('"criterion":', plan)
        self.assertIn("Publish the accepted revision to the canonical source location", plan)

    def test_plan_release_targets_are_provider_neutral_and_complete(self) -> None:
        plan_text = self.read("assets/templates/HARNESS_PLAN.template.md")
        plan = self.canonical_manifest(
            "assets/templates/HARNESS_PLAN.template.md", "harness_plan"
        )

        for field in (
            '"id": "web-development"',
            '"id": "web-production"',
            '"stage": "development"',
            '"stage": "production"',
            '"source":',
            '"artifact_kind":',
            '"requires_signing":',
            '"channel":',
            '"data_mode":',
            '"trigger":',
            '"migration_classification":',
            '"commands":',
            '"prerequisites":',
            '"smoke_verifiers":',
        ):
            self.assertIn(field, plan_text)
        targets = {target["id"]: target for target in plan["release"]["targets"]}
        self.assertEqual("integration_head", targets["web-development"]["source"])
        self.assertEqual("production_head", targets["web-production"]["source"])
        self.assertIn("Stable target IDs are provider-neutral", plan_text)

    def test_run_v10_binds_plan_targets_authorization_and_evidence(self) -> None:
        run = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn('"web-development": {', run)
        self.assertIn('"web-production": {', run)
        self.assertIn("keys must exactly equal the PLAN `release.targets[].id` set", run)
        for field in (
            '"artifact":',
            '"channel":',
            '"promotion":',
            '"availability":',
            '"evidence_sha256":',
            '"build_id":',
            '"signing_status":',
        ):
            self.assertIn(field, run)
        self.assertIn('"plan_revision": 1', run)
        self.assertIn('"plan_digest_sha256":', run)
        self.assertIn('"trigger_remote_ci": {', run)
        self.assertIn('"provision_cloud_resources": {', run)
        self.assertIn("workflow:<identity>", run)
        self.assertIn(
            "cloud-resource:<provider>:<environment>:<kind>:<logical-name>", run
        )

    def test_run_v10_retains_verifier_executions_and_development_continuity(self) -> None:
        run = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn('"verifier_executions": [', run)
        self.assertIn('"protocol": "harness-verifier-execution-v1"', run)
        self.assertIn("append-only and parent-owned", run)
        self.assertIn('"continuity": {', run)
        self.assertIn('"status": "planned"', run)
        self.assertIn('"branch": "refs/heads/development"', run)
        self.assertIn('"base_branch": "production"', run)
        self.assertIn("Retain reviewed work on development", run)

    def test_review_repair_review_graph_is_bounded(self) -> None:
        plan = self.canonical_manifest(
            "assets/templates/HARNESS_PLAN.template.md", "harness_plan"
        )
        nodes = {node["id"]: node for node in plan["graph"]["nodes"]}
        edges = {edge["id"]: edge for edge in plan["graph"]["edges"]}
        missions = {mission["id"]: mission for mission in plan["missions"]}

        frontend = nodes["N-FRONTEND-REVIEW"]
        self.assertEqual(["M1"], frontend["review"]["mission_ids"])
        self.assertEqual(2, frontend["max_attempts"])
        self.assertNotIn("N-M1-REPAIR", nodes)
        self.assertNotIn("M2", missions)
        self.assertFalse(
            any(
                edge["from"] == "N-FRONTEND-REVIEW"
                and edge["on_outcomes"] == ["fix_required"]
                for edge in edges.values()
            )
        )

        repair = nodes["N-VISUAL-REPAIR"]
        mission = missions["M3"]
        self.assertEqual("mission", repair["kind"])
        self.assertEqual("runtime_worker", repair["executor"])
        self.assertEqual("M3", repair["ref"])
        self.assertTrue(mission["write_scope"])
        self.assertTrue(mission["tasks"][0]["acceptance_matrix"])
        self.assertTrue(mission["worker_verifiers"])
        self.assertTrue(mission["integration_verifiers"])
        review_to_repair = edges["E-VISUAL-REVIEW-REPAIR"]
        repair_review = nodes["N-VISUAL-REPAIR-CODE-REVIEW"]
        repair_to_code_review = edges["E-VISUAL-REPAIR-CODE-REVIEW"]
        repair_to_review = edges["E-VISUAL-REPAIR-REREVIEW"]
        review_to_final = edges["E-VISUAL-CLOSEOUT"]
        self.assertEqual(["M3"], repair_review["review"]["mission_ids"])
        self.assertEqual("frontend_code", repair_review["review"]["type"])
        self.assertEqual("N-VISUAL-REPAIR", repair_to_code_review["from"])
        self.assertEqual(
            "N-VISUAL-REPAIR-CODE-REVIEW",
            repair_to_code_review["to"],
        )
        self.assertEqual("dependency", repair_to_code_review["kind"])
        self.assertEqual(
            "N-VISUAL-REPAIR-CODE-REVIEW",
            repair_to_review["from"],
        )
        self.assertEqual(["fix_required"], review_to_repair["on_outcomes"])
        self.assertEqual(["pass"], repair_to_review["on_outcomes"])
        self.assertEqual(2, review_to_repair["max_traversals"])
        self.assertEqual(2, repair_to_review["max_traversals"])
        self.assertEqual(["pass"], review_to_final["on_outcomes"])
        self.assertIn(
            nodes["N-CLOSEOUT-GATE"]["executor"],
            {"harness_parent", "local_command"},
        )

    def test_native_merge_trigger_requires_landing_and_deployment_authorization(self) -> None:
        landing = self.read_sibling_skill("fullstack-harness-github-landing")

        self.assertIn("exact merge/landing authorization", landing)
        self.assertIn("exact deployment authorization", landing)
        self.assertIn("Never infer deployment authorization from merge authorization", landing)
        self.assertIn("authorized candidate head", landing)
        self.assertIn("resulting merged source SHA", landing)
        self.assertIn("release:<target-id>", landing)

    def test_cloudflare_current_contract_is_provider_neutral(self) -> None:
        lifecycle = self.read("references/cloudflare-deployment-lifecycle.md")
        guide = self.read("assets/templates/PROJECT_CLOUDFLARE_DEPLOYMENT_GUIDE.template.md")

        self.assertIn("PLAN schema v5", lifecycle)
        self.assertIn("RUN schema v10 `targets`", lifecycle)
        self.assertIn("migration_classification", lifecycle)
        self.assertIn("blocks execution", lifecycle)
        self.assertIn(
            "cloud-resource:<provider>:<environment>:<kind>:<logical-name>", lifecycle
        )
        self.assertIn("`workflow:<identity>`", lifecycle)
        self.assertIn("PLAN-v5 keeps provider-neutral release targets", guide)
        self.assertIn("<resolved-integration-branch>", guide)
        self.assertIn("<resolved-protected-base-branch>", guide)
        self.assertNotIn("watches branch: `development`", guide)
        self.assertNotIn("watches branch: `production`", guide)

    def test_lazy_pillow_and_readme_current_outputs_are_documented(self) -> None:
        skill = self.read("SKILL.md")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("Pillow is imported lazily", skill)
        self.assertIn("targeted UI-evidence decoding error", skill)
        self.assertIn("without preventing non-UI CLIs from starting", skill)
        self.assertIn("PLAN v5", readme)
        self.assertIn("RUN v10", readme)
        self.assertIn("`design-system.md`, `design-system.json`", readme)


if __name__ == "__main__":
    unittest.main()
