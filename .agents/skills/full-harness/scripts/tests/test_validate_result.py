#!/usr/bin/env python3
"""Tests for the merged validate_result.py entrypoint."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_manifest  # noqa: E402
import validate_result  # noqa: E402
from test_graph_orchestration import valid_graph_plan, valid_graph_run  # noqa: E402
from test_validate_node_result import running_result  # noqa: E402


HEADINGS = {"PLAN.md": "## Harness Plan Manifest", "RUN.md": "## Harness Run State"}


def write(directory: Path, name: str, payload: object) -> Path:
    path = directory / name
    if name in HEADINGS:
        body = (
            f"{HEADINGS[name]}\n\n```json\n"
            + json.dumps(payload, indent=2)
            + "\n```\n"
        )
        path.write_text(body, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class ValidateResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.plan = valid_graph_plan()
        self.run = valid_graph_run(self.plan)
        self.result = running_result(self.plan, self.run)
        self.plan_path = write(self.dir, "PLAN.md", {"harness_plan": self.plan})
        self.run_path = write(self.dir, "RUN.md", {"harness_run": self.run})

    def run_cli(self, *extra: str) -> tuple[int, dict]:
        argv = ["--plan", str(self.plan_path), "--run", str(self.run_path), *extra]
        from io import StringIO
        from contextlib import redirect_stdout

        buffer = StringIO()
        with redirect_stdout(buffer):
            code = validate_result.main(argv)
        return code, json.loads(buffer.getvalue())

    def test_node_result_passes_through_merged_cli(self) -> None:
        node_path = write(self.dir, "node.json", {"node_result": self.result})
        code, payload = self.run_cli("--node-result", str(node_path))

        self.assertEqual(0, code)
        self.assertEqual("PASS", payload["status"])
        self.assertEqual([], payload["errors"])

    def test_node_result_errors_are_reported(self) -> None:
        broken = dict(self.result)
        broken["attempt_id"] = "ATT-STALE"
        node_path = write(self.dir, "node.json", {"node_result": broken})
        code, payload = self.run_cli("--node-result", str(node_path))

        self.assertEqual(2, code)
        self.assertTrue(any("active attempt" in error for error in payload["errors"]))

    def test_requires_at_least_one_result(self) -> None:
        code, payload = self.run_cli()

        self.assertEqual(2, code)
        self.assertIn(
            "give at least one of --node-result or --worker-result", payload["errors"]
        )

    def test_manifest_pair_is_validated_once(self) -> None:
        node_path = write(self.dir, "node.json", {"node_result": self.result})
        real = harness_manifest.validate_current_plan_run
        with patch.object(
            validate_result, "validate_current_plan_run", side_effect=real
        ) as spy:
            code, payload = self.run_cli("--node-result", str(node_path))

        self.assertEqual(0, code)
        self.assertEqual("PASS", payload["status"])
        self.assertEqual(1, spy.call_count)


if __name__ == "__main__":
    unittest.main()
