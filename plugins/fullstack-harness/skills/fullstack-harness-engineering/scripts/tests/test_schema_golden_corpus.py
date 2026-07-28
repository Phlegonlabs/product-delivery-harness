#!/usr/bin/env python3
"""Golden compatibility corpus for every supported RUN schema."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for location in (TESTS_DIR, SCRIPTS_DIR):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

from harness_manifest import validate_plan, validate_run
from test_harness_manifest import valid_plan, valid_run
from test_upgrade_harness_schema import current_plan_and_run, safe_v4_plan_and_v9_run


def legacy_pair(schema_version: int, repo_root: Path) -> tuple[dict, dict]:
    """Project the real legacy fixture to the exact historical RUN shape."""
    if schema_version in {8, 9}:
        plan, run = safe_v4_plan_and_v9_run(repo_root)
    else:
        plan = valid_plan()
        run = valid_run(plan)
    run = copy.deepcopy(run)
    run["schema_version"] = schema_version

    if schema_version < 8:
        run["authorizations"].pop("invoke_external_runtime", None)
        run.pop("batch_gate_results", None)
        run.pop("final_gate_results", None)
        run.pop("ui_evidence", None)
    elif schema_version == 8:
        run.pop("batch_gate_results", None)
        run.pop("final_gate_results", None)
        run.pop("ui_evidence", None)
    if schema_version < 6:
        run["runtime_capabilities"].pop("runtime_adapter", None)
    if schema_version < 5:
        run.pop("post_merge_cleanup", None)
        run["observed"]["git"].pop("parent_worktree_path", None)
    if schema_version < 4:
        run["landing"].pop("auto_merge_requested", None)
        run["landing"].pop("auto_merge_head_sha", None)
    if schema_version < 3:
        run.pop("landing", None)
        for action in ("configure_repository", "manage_pr_review", "merge_pr"):
            run["authorizations"].pop(action, None)
    return plan, run


class SchemaGoldenCorpusTests(unittest.TestCase):
    def test_every_supported_schema_accepts_its_real_artifact_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo_root = Path(temp)
            product_dir = repo_root / "docs" / "product"
            product_dir.mkdir(parents=True)
            (product_dir / "prd.md").write_text("# Product\n", encoding="utf-8")
            (product_dir / "architecture.md").write_text(
                "# Architecture\n", encoding="utf-8"
            )
            for schema_version in range(2, 10):
                with self.subTest(schema_version=schema_version):
                    plan, run = legacy_pair(schema_version, repo_root)
                    self.assertEqual([], validate_plan(plan))
                    self.assertEqual([], validate_run(plan, run))

            plan, run = current_plan_and_run(repo_root)
            self.assertEqual([], validate_plan(plan))
            self.assertEqual([], validate_run(plan, run))


if __name__ == "__main__":
    unittest.main()
