#!/usr/bin/env python3
"""Opt-in golden-path E2E: the real CLI spine over one frozen product package.

CI enables this test explicitly. Run it locally with:

    HARNESS_GOLDEN_PATH=1 python -m unittest discover \
        -s skills/delivery-harness/scripts/tests \
        -p "test_golden_path.py" -v

The per-component suites can stay green while the six skills drift apart;
this test walks the documented spine in order against one synthetic package —
`new_run.py` generating RUN from PLAN, `validate_harness_plan.py` re-running
the frozen source joins including the sibling skills' product, UI-design, and HiFi checkers,
and `validate_result.py` validating a returned graph payload with `--repo-root`
— so cross-skill contract drift surfaces here as one red test.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import load_run  # noqa: E402
from harness_contract_join import validate_frozen_contract_joins  # noqa: E402
from manifest_fixtures import (  # noqa: E402
    eval_exempt_product_fixture,
    git,
    manifest_markdown,
)
import contract_package_fixture  # noqa: E402
from test_validate_node_result import running_result  # noqa: E402


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@unittest.skipUnless(
    os.environ.get("HARNESS_GOLDEN_PATH"),
    "set HARNESS_GOLDEN_PATH=1 to run the golden-path E2E",
)
class GoldenPathTests(unittest.TestCase):
    def test_frozen_package_walks_the_real_cli_spine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with eval_exempt_product_fixture():
                package = contract_package_fixture.current_package(
                    root, pin=(SCRIPTS_DIR.parent / "VERSION").read_text(encoding="utf-8").strip()
                )
            plan = package["plan"]
            paths = package["paths"]
            prd_path = paths["prd"]
            design_markdown_path = paths["design_markdown"]
            design_json_path = paths["design_json"]
            head = git(root, "rev-parse", "HEAD")

            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown(
                    "## Harness Plan Manifest", "harness_plan", plan
                ),
                encoding="utf-8",
            )

            generated = run_cli(
                str(SCRIPTS_DIR / "new_run.py"),
                "--plan",
                str(plan_path),
                "--run-id",
                "RUN-GOLDEN",
                "--branch",
                "refs/heads/run/golden-path",
                "--repo-root",
                str(root),
                "--out",
                str(root / "RUN.md"),
            )
            self.assertEqual(0, generated.returncode, generated.stderr)
            run_path = root / "RUN.md"
            self.assertTrue(run_path.is_file())

            validated = run_cli(
                str(SCRIPTS_DIR / "validate_harness_plan.py"),
                "--plan",
                str(plan_path),
                "--run",
                str(run_path),
                "--repo-root",
                str(root),
                "--prd",
                str(prd_path),
                "--design-system-markdown",
                str(design_markdown_path),
                "--design-system",
                str(design_json_path),
            )
            self.assertEqual(
                0,
                validated.returncode,
                validated.stdout + validated.stderr,
            )
            self.assertEqual("PASS", json.loads(validated.stdout)["status"])

            plan_only = run_cli(str(SCRIPTS_DIR / "validate_harness_plan.py"),
                "--plan", str(plan_path), "--repo-root", str(root), "--prd", str(prd_path),
                "--design-system-markdown", str(design_markdown_path), "--design-system", str(design_json_path))
            # An explicit PLAN policy and architecture marker can be checked
            # before a RUN exists; this grants no execution or promotion.
            self.assertEqual(0, plan_only.returncode, plan_only.stdout)
            self.assertEqual("PASS", json.loads(plan_only.stdout)["status"])

            run = load_run(run_path)
            missing_ui_design = json.loads(json.dumps(plan))
            missing_ui_design["sources"] = [
                source
                for source in missing_ui_design["sources"]
                if source["kind"] != "ui design"
            ]
            self.assertTrue(
                any(
                    "requires exactly one frozen ui-design source" in error
                    for error in validate_frozen_contract_joins(
                        missing_ui_design, root, run=run
                    )
                )
            )
            run["integration"]["batch_base_sha"] = head
            node_result = running_result(plan, run)
            run_path.write_text(
                manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            node_path = root / "node-result.json"
            node_path.write_text(
                json.dumps({"node_result": node_result}), encoding="utf-8"
            )

            merged = run_cli(
                str(SCRIPTS_DIR / "validate_result.py"),
                "--plan",
                str(plan_path),
                "--run",
                str(run_path),
                "--node-result",
                str(node_path),
                "--repo-root",
                str(root),
            )
            self.assertEqual(0, merged.returncode, merged.stdout)
            payload = json.loads(merged.stdout)
            self.assertEqual("PASS", payload["status"])
            self.assertEqual([], payload["errors"])


if __name__ == "__main__":
    unittest.main()
