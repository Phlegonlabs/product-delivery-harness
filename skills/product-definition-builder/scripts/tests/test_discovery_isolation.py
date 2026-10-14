#!/usr/bin/env python3
"""Keep cross-skill fixture loading from changing unittest discovery."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
OUTCOME_PATH = TESTS_DIR / "test_outcome_review.py"


class DiscoveryIsolationTests(unittest.TestCase):
    def test_outcome_fixture_loader_preserves_product_test_origin(self) -> None:
        probe = """
import sys
from pathlib import Path
import importlib.util

tests_dir = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tests_dir))
path = tests_dir / "test_outcome_review.py"
spec = importlib.util.spec_from_file_location("_outcome_under_test", path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
import test_skill_contract

origin = Path(test_skill_contract.__file__).resolve()
if origin.parent != tests_dir:
    raise AssertionError(f"test_skill_contract loaded from {origin}")
print(origin)
"""
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        result = subprocess.run(
            [sys.executable, "-c", probe, str(TESTS_DIR)],
            env=environment,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(
            0,
            result.returncode,
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
