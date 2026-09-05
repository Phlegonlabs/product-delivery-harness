#!/usr/bin/env python3
"""Opt-in golden-path E2E: the real CLI spine over one frozen product package.

Not part of the default discovery verification. Run explicitly with:

    HARNESS_GOLDEN_PATH=1 python -m unittest discover \
        -s .agents/skills/delivery-harness/scripts/tests \
        -p "test_golden_path.py" -v

The per-component suites each stay green while the three skills drift apart;
this test walks the documented spine in order against one synthetic package —
`new_run.py` generating RUN from PLAN, `validate_harness_plan.py` re-running
the frozen source joins including the sibling skill's full wireframe checker,
and `validate_result.py` validating a returned graph payload with `--repo-root`
— so cross-skill contract drift surfaces here as one red test.
"""

from __future__ import annotations

import hashlib
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
from manifest_fixtures import (  # noqa: E402
    git,
    init_repo,
    manifest_markdown,
    wireframes_html,
)
from test_harness_manifest import valid_plan  # noqa: E402
from test_validate_node_result import running_result  # noqa: E402


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def frozen_source(
    identifier: str, kind: str, location: str, path: Path
) -> dict[str, object]:
    return {
        "id": identifier,
        "kind": kind,
        "location": location,
        "owner": "product",
        "status": "frozen",
        "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_revision": None,
        "staged_revision": None,
        "notes": "golden-path frozen source",
    }


@unittest.skipUnless(
    os.environ.get("HARNESS_GOLDEN_PATH"),
    "set HARNESS_GOLDEN_PATH=1 to run the golden-path E2E",
)
class GoldenPathTests(unittest.TestCase):
    def test_frozen_package_walks_the_real_cli_spine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repo(root, "README.md")

            product = root / "docs" / "product"
            product.mkdir(parents=True)
            prd_path = product / "PRD.md"
            prd_path.write_text(
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Home\n\n"
                "- `route`: /home\n"
                "- `states`: ready\n"
                "<!-- ui-surface-contract:end -->\n",
                encoding="utf-8",
            )
            wireframes_path = product / "wireframes.html"
            wireframes_path.write_text(
                wireframes_html(
                    [{"id": "UI-001", "route": "/home", "states": ["ready"]}]
                ),
                encoding="utf-8",
            )
            architecture_path = product / "architecture.md"
            architecture_path.write_text("# Architecture\n", encoding="utf-8")

            plan = valid_plan()
            plan["ui_surfaces"] = [
                {
                    "id": "UI-001",
                    "trace_ids": ["REQ-001"],
                    "route": "/home",
                    "breakpoints": ["390"],
                    "states": ["ready"],
                    "evidence_gate": "required",
                }
            ]
            plan["sources"] = [
                frozen_source(
                    "SRC-001", "prd", "docs/product/PRD.md", prd_path
                ),
                frozen_source(
                    "SRC-002",
                    "architecture",
                    "docs/product/architecture.md",
                    architecture_path,
                ),
                frozen_source(
                    "SRC-WIREFRAMES",
                    "wireframe",
                    "docs/product/wireframes.html",
                    wireframes_path,
                ),
            ]
            git(root, "add", "docs")
            git(root, "commit", "-qm", "freeze product package")
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
                "--wireframes",
                str(wireframes_path),
            )
            self.assertEqual(
                0,
                validated.returncode,
                validated.stdout + validated.stderr,
            )
            self.assertEqual("PASS", json.loads(validated.stdout)["status"])

            run = load_run(run_path)
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
