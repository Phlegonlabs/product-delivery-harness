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
                "fullstack-harness-codex",
                "SKILL.md",
                "# Full-Stack Harness: Codex Runtime Adapter",
            ),
            (
                "fullstack-harness-claude-code",
                "SKILL.md",
                "# Full-Stack Harness: Claude Code Runtime Adapter",
            ),
            (
                "fullstack-harness-github-landing",
                "SKILL.md",
                "# Full-Stack Harness: GitHub Landing Adapter",
            ),
            (
                "prd-builder",
                "assets/templates/DESIGN_SYSTEM.template.md",
                "# Design System:",
            ),
            (
                "prd-builder",
                "assets/templates/DESIGN_SYSTEM.template.json",
                "\"schema\": \"design-system/1\"",
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

    def test_adapters_resolve_the_shared_core_without_duplicate_assets(self) -> None:
        core = SKILLS_ROOT / "fullstack-harness-engineering"
        self.assertTrue((core / "scripts" / "validate_harness_plan.py").is_file())

        for skill_name in (
            "fullstack-harness-codex",
            "fullstack-harness-claude-code",
            "fullstack-harness-github-landing",
        ):
            adapter = SKILLS_ROOT / skill_name
            self.assertFalse((adapter / "scripts").exists())
            self.assertFalse((adapter / "assets").exists())

    def test_harness_module_imports_from_skill_scripts(self) -> None:
        module_path = HARNESS_ROOT / "scripts" / "harness_manifest.py"
        scripts_dir = str(module_path.parent)
        # harness_manifest.py imports sibling modules (harness_schema, harness_core,
        # etc.) by bare name; a real invocation always has its own directory on
        # sys.path (python script.py adds it automatically), so this manual loader
        # must add it too to faithfully simulate that, not to bypass it.
        path_inserted = scripts_dir not in sys.path
        if path_inserted:
            sys.path.insert(0, scripts_dir)
        try:
            spec = importlib.util.spec_from_file_location(
                "packaged_harness_manifest", module_path
            )
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            if path_inserted:
                sys.path.remove(scripts_dir)

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
