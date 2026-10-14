"""Harness loader cleanup must not strand the UI checker's own imports."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class HarnessContractJoinLoaderTests(unittest.TestCase):
    def run_loader(self, loader: str) -> subprocess.CompletedProcess[str]:
        """Run one loader in exact code with no inherited path or module cache."""

        harness_scripts = SCRIPTS_DIR.resolve()
        child = f"""
import sys
sys.path.insert(0, {str(harness_scripts)!r})
import harness_contract_join as join
loader = getattr(join, {loader!r})
loader(join.sibling_ui_design_scripts_dir())
checker = sys.modules["check_ui_design_contract"]
ui3 = checker.ui_design_v3
print(ui3.has_direction_review_profile("<html></html>"))
"""
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        return subprocess.run(
            [sys.executable, "-I", "-B", "-c", child],
            capture_output=True,
            cwd=Path(__file__).resolve().parents[3],
            env=environment,
            text=True,
            timeout=30,
        )

    def test_full_ui_checker_loader_retains_call_time_import_path(self):
        result = self.run_loader("_load_full_ui_design_checker")
        self.assertEqual(
            0,
            result.returncode,
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertEqual("False\n", result.stdout)

    def test_ui_contract_view_loader_retains_call_time_import_path(self):
        result = self.run_loader("_load_ui_contract_view")
        self.assertEqual(
            0,
            result.returncode,
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertEqual("False\n", result.stdout)


if __name__ == "__main__":
    unittest.main()
