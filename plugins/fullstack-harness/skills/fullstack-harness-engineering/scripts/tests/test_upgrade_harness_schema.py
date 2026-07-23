#!/usr/bin/env python3
"""Tests for upgrade_harness_schema.py (CLI level and direct validation)."""

from __future__ import annotations

import copy
import json
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

from harness_manifest import (  # noqa: E402
    AUTHORIZATION_KEYS_V2,
    load_plan,
    load_run,
    plan_digest,
    validate_plan,
    validate_run,
)
from test_harness_manifest import valid_plan, valid_run  # noqa: E402
from test_select_parallel_missions import manifest_markdown  # noqa: E402

import upgrade_harness_schema as upgrade  # noqa: E402


UPGRADE_SCRIPT = SCRIPTS_DIR / "upgrade_harness_schema.py"


def downgrade_run_to_v2(run: dict[str, object]) -> dict[str, object]:
    """Strip every post-v2 addition to produce a valid schema-v2 RUN."""

    run = copy.deepcopy(run)
    run["schema_version"] = 2
    run["runtime_capabilities"].pop("runtime_adapter", None)
    run.pop("landing", None)
    run.pop("post_merge_cleanup", None)
    run["observed"]["git"].pop("parent_worktree_path", None)
    run["authorizations"] = {
        key: run["authorizations"][key] for key in AUTHORIZATION_KEYS_V2
    }
    return run


class UpgradeHelpers:
    def _seed_repo(self) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "docs" / "product").mkdir(parents=True)
        # valid_plan() sources point at docs/product/prd.md and docs/product/architecture.md;
        # real files let the v4 upgrade freeze a real content_sha256.
        (root / "docs" / "product" / "prd.md").write_text("product requirements", encoding="utf-8")
        (root / "docs" / "product" / "architecture.md").write_text("architecture", encoding="utf-8")
        return root

    def _write_plan(self, root: Path, plan: dict[str, object]) -> Path:
        path = root / "PLAN.md"
        path.write_text(
            manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
            encoding="utf-8",
        )
        return path

    def _write_run(self, root: Path, run: dict[str, object]) -> Path:
        path = root / "RUN.md"
        path.write_text(
            manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )
        return path

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(UPGRADE_SCRIPT), *args]
        return subprocess.run(command, check=False, capture_output=True, text=True)


class PlanUpgradeTests(UpgradeHelpers, unittest.TestCase):
    def test_plan_v2_to_v4_result_passes_validate_plan(self) -> None:
        root = self._seed_repo()
        plan_path = self._write_plan(root, valid_plan())

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(0, result.returncode, result.stderr)
        upgraded = load_plan(plan_path)
        self.assertEqual(4, upgraded["schema_version"])
        self.assertEqual([], validate_plan(upgraded))

    def test_plan_v4_graph_projects_dependencies_without_fabrication(self) -> None:
        root = self._seed_repo()
        plan_path = self._write_plan(root, valid_plan())

        self._run_cli("--plan", str(plan_path), "--repo-root", str(root))
        upgraded = load_plan(plan_path)

        # M2 depends_on M1 in the source plan -> exactly one dependency edge.
        self.assertEqual([], upgraded["required_reviews"])
        node_refs = {node["ref"] for node in upgraded["graph"]["nodes"]}
        self.assertEqual({"M1", "M2"}, node_refs)
        dependency_edges = [
            edge for edge in upgraded["graph"]["edges"] if edge["kind"] == "dependency"
        ]
        self.assertEqual(1, len(dependency_edges))
        # depends_on must be gone from every mission at v4.
        self.assertTrue(all("depends_on" not in m for m in upgraded["missions"]))
        # Frozen provenance is a real hash, source_revision stays null (not invented).
        for source in upgraded["sources"]:
            self.assertRegex(source["content_sha256"], r"^[0-9a-f]{64}$")
            self.assertIsNone(source["source_revision"])

    def test_unreadable_source_aborts_without_writing(self) -> None:
        # No source files on disk -> v4 freeze cannot compute a real hash.
        root = Path(tempfile.mkdtemp())
        plan_path = self._write_plan(root, valid_plan())
        before = plan_path.read_bytes()

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(1, result.returncode)
        self.assertIn("cannot freeze source", result.stderr)
        self.assertEqual(before, plan_path.read_bytes())

    def test_invalid_plan_is_rejected_and_not_written(self) -> None:
        root = self._seed_repo()
        broken = valid_plan()
        broken["missions"] = []  # structurally invalid
        plan_path = self._write_plan(root, broken)
        before = plan_path.read_bytes()

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(1, result.returncode)
        self.assertIn("refusing to upgrade", result.stderr)
        self.assertEqual(before, plan_path.read_bytes())


class RunUpgradeTests(UpgradeHelpers, unittest.TestCase):
    def test_run_v2_to_v9_with_plan_upgrade_passes_validate_run(self) -> None:
        root = self._seed_repo()
        plan = valid_plan()
        run = downgrade_run_to_v2(valid_run(plan))
        run["plan"]["digest_sha256"] = plan_digest(plan)
        plan_path = self._write_plan(root, plan)
        run_path = self._write_run(root, run)

        result = self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )

        self.assertEqual(0, result.returncode, result.stderr)
        upgraded_plan = load_plan(plan_path)
        upgraded_run = load_run(run_path)
        self.assertEqual(4, upgraded_plan["schema_version"])
        self.assertEqual(9, upgraded_run["schema_version"])
        self.assertEqual([], validate_run(upgraded_plan, upgraded_run))
        # digest re-synced to the upgraded PLAN.
        self.assertEqual(
            plan_digest(upgraded_plan), upgraded_run["plan"]["digest_sha256"]
        )

    def test_run_upgrade_lands_neutral_defaults(self) -> None:
        root = self._seed_repo()
        plan = valid_plan()
        run = downgrade_run_to_v2(valid_run(plan))
        run["plan"]["digest_sha256"] = plan_digest(plan)
        plan_path = self._write_plan(root, plan)
        run_path = self._write_run(root, run)

        self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )
        upgraded_run = load_run(run_path)

        # v3 landing / v4 auto-merge: no fabricated merge intent.
        self.assertEqual("not_created", upgraded_run["landing"]["pr_state"])
        self.assertFalse(upgraded_run["landing"]["auto_merge_requested"])
        # v8 authorization ledger 17th entry: never pre-authorized.
        self.assertEqual(
            {"authorized": False, "source": None},
            upgraded_run["authorizations"]["invoke_external_runtime"],
        )
        # v8 graph_state: every node dormant with no attempts/outcome.
        for state in upgraded_run["graph_state"]["node_states"].values():
            self.assertEqual("dormant", state["phase"])
            self.assertEqual(0, state["attempts"])
            self.assertIsNone(state["last_outcome"])
        # v9 gate results: planned, never a fabricated PASS.
        for gate in (
            upgraded_run["batch_gate_results"] + upgraded_run["final_gate_results"]
        ):
            self.assertEqual("planned", gate["status"])
            self.assertIsNone(gate["head_sha"])
            self.assertEqual([], gate["evidence"])
        self.assertEqual([], upgraded_run["ui_evidence"])
        self.assertEqual([], upgraded_run["review_workers"])
        self.assertEqual([], upgraded_run["workflow_runs"])


class NoOpAndDryRunTests(UpgradeHelpers, unittest.TestCase):
    def _upgrade_to_current(self, root: Path) -> tuple[Path, Path]:
        plan = valid_plan()
        run = downgrade_run_to_v2(valid_run(plan))
        run["plan"]["digest_sha256"] = plan_digest(plan)
        plan_path = self._write_plan(root, plan)
        run_path = self._write_run(root, run)
        result = self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return plan_path, run_path

    def test_already_current_is_a_no_op(self) -> None:
        root = self._seed_repo()
        plan_path, run_path = self._upgrade_to_current(root)
        plan_before = plan_path.read_bytes()
        run_before = run_path.read_bytes()

        result = self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("already current", result.stdout)
        self.assertEqual(plan_before, plan_path.read_bytes())
        self.assertEqual(run_before, run_path.read_bytes())

    def test_dry_run_writes_nothing(self) -> None:
        root = self._seed_repo()
        plan = valid_plan()
        plan_path = self._write_plan(root, plan)
        before = plan_path.read_bytes()

        result = self._run_cli(
            "--plan", str(plan_path), "--repo-root", str(root), "--dry-run"
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("[dry-run]", result.stdout)
        self.assertIn("schema 2 -> 4", result.stdout)
        self.assertEqual(before, plan_path.read_bytes())


class SurroundingMarkdownTests(UpgradeHelpers, unittest.TestCase):
    def test_only_fenced_json_block_changes(self) -> None:
        root = self._seed_repo()
        plan = valid_plan()
        body = json.dumps({"harness_plan": plan}, indent=2)
        document = (
            "# Plan: fixture\r\n"
            "\r\n"
            "Intro prose that must survive untouched.\r\n"
            "\r\n"
            "## Harness Plan Manifest\r\n"
            "\r\n"
            "```json\r\n"
            + body.replace("\n", "\r\n")
            + "\r\n```\r\n"
            "\r\n"
            "## Source Map\r\n"
            "\r\n"
            "| Source | Path |\r\n"
            "|---|---|\r\n"
            "| PRD | docs/prd.md |\r\n"
        )
        plan_path = root / "PLAN.md"
        plan_path.write_bytes(document.encode("utf-8"))

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(0, result.returncode, result.stderr)
        rewritten = plan_path.read_bytes().decode("utf-8")
        # Every prose/heading/table line outside the fence is byte-identical.
        for line in (
            "# Plan: fixture",
            "Intro prose that must survive untouched.",
            "## Source Map",
            "| Source | Path |",
            "| PRD | docs/prd.md |",
        ):
            self.assertIn(line + "\r\n", rewritten)
        # Line endings stay CRLF only.
        self.assertNotIn("\n", rewritten.replace("\r\n", ""))
        self.assertEqual(4, load_plan(plan_path)["schema_version"])


if __name__ == "__main__":
    unittest.main()
