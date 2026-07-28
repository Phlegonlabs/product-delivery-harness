import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HARNESS_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = HARNESS_ROOT.parent


class PackagedSkillSmokeTests(unittest.TestCase):


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
