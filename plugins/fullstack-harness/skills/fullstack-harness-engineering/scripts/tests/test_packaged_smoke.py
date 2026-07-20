import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HARNESS_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = HARNESS_ROOT.parent


class PackagedSkillSmokeTests(unittest.TestCase):
    def test_skill_files_and_templates_load_from_relative_roots(self) -> None:
        expected_files = (
            (
                "fullstack-harness-engineering",
                "assets/templates/HARNESS_PLAN.template.md",
                "## Harness Plan Manifest",
            ),
            (
                "design-package-builder",
                "assets/templates/DESIGN_SYSTEM.template.md",
                "# Design System:",
            ),
            (
                "prd-builder",
                "assets/templates/CLAUDE_PRD_WORKFLOW.template.js",
                "workflow",
            ),
        )

        for skill_name, template_path, marker in expected_files:
            with self.subTest(skill=skill_name):
                skill_root = SKILLS_ROOT / skill_name
                self.assertTrue((skill_root / "SKILL.md").is_file())
                template = (skill_root / template_path).read_text(encoding="utf-8")
                self.assertIn(marker, template)

    def test_harness_module_imports_from_skill_scripts(self) -> None:
        module_path = HARNESS_ROOT / "scripts" / "harness_manifest.py"
        spec = importlib.util.spec_from_file_location(
            "packaged_harness_manifest", module_path
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(module.PLAN_HEADING, "## Harness Plan Manifest")

    def test_validator_cli_starts_outside_the_repository_cwd(self) -> None:
        validator = HARNESS_ROOT / "scripts" / "validate_harness_plan.py"
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, str(validator), "--help"],
                cwd=temp,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--plan", result.stdout)
        self.assertIn("--repo-root", result.stdout)


if __name__ == "__main__":
    unittest.main()
