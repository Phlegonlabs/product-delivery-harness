#!/usr/bin/env python3
"""Tests for check_prd_delta_scope.py and the PRD-delta PLAN schema additions."""

from __future__ import annotations

import contextlib
import hashlib
import io
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

from check_document_sync import default_inventory  # noqa: E402
from check_prd_delta_scope import main as delta_scope_main  # noqa: E402
from harness_manifest import validate_plan  # noqa: E402
from manifest_fixtures import manifest_markdown, valid_plan  # noqa: E402


DELTA_LOCATION = "docs/product/deltas/PRD-DELTA-EPIC-7.md"

DELTA_TEXT = """# PRD-DELTA-EPIC-7

| Field | Value |
| --- | --- |
| Epic | docs/epics/EPIC-7-round.md |
| Baseline PRD | sha256:%s |
| Result PRD | pending |
| Status | draft |
| Ambition rung | 1 - one round outcome |

## Changed Requirements

| ID | Change | Before | After | TEST IDs |
| --- | --- | --- | --- | --- |
| PRD-101 | new | - | Round outcome | TEST-201 (Required: Yes) |
| PRD-102 | revised | Old copy | New copy | TEST-202 |
| PRD-103 | retired | Old behavior | - | - |

## Ambition

Range rows marked `review lens` feed the combined review.
"""


def delta_source(content_sha256: str | None) -> dict[str, object]:
    return {
        "id": "SRC-DELTA",
        "kind": "prd-delta",
        "location": DELTA_LOCATION,
        "owner": "human",
        "status": "delta_accepted",
        "content_sha256": content_sha256,
        "source_revision": None,
        "staged_revision": None,
        "notes": "round delta",
    }


def mission(trace_ids: list[str], task_trace_ids: list[list[str]]) -> dict[str, object]:
    return {
        "id": "M1",
        "objective": "Deliver the round",
        "trace_ids": list(trace_ids),
        "write_scope": ["src/**"],
        "tasks": [
            {
                "id": f"M1/T{index:02d}",
                "objective": "One step",
                "trace_ids": list(task_ids),
                "acceptance_matrix": [],
                "verifiers": [],
            }
            for index, task_ids in enumerate(task_trace_ids, start=1)
        ],
    }


class PrdDeltaScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.delta_path = self.root / DELTA_LOCATION
        self.delta_path.parent.mkdir(parents=True)
        self.delta_bytes = (DELTA_TEXT % ("f" * 64)).encode("utf-8")
        self.delta_sha = hashlib.sha256(self.delta_bytes).hexdigest()
        self.delta_path.write_bytes(self.delta_bytes)

    def write_plan(self, plan: dict[str, object]) -> None:
        self.plan_path = self.root / "PLAN.md"
        self.plan_path.write_text(
            manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
            encoding="utf-8",
        )

    def write_outside_delta(self) -> Path:
        outside = self.root.parent / "prd-delta-escape.md"
        outside.write_bytes(self.delta_bytes)
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        return outside

    def plan_with_location(self, location: str) -> dict[str, object]:
        plan = self.bound_plan()
        source = delta_source(self.delta_sha)
        source["location"] = location
        plan["sources"] = [source]
        return plan

    def run_checker(self) -> tuple[int, str]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = delta_scope_main(
                ["--plan", str(self.plan_path), "--repo-root", str(self.root)]
            )
        return code, buffer.getvalue()

    def bound_plan(
        self,
        *,
        mission_trace_ids: list[str] | None = None,
        task_trace_ids: list[list[str]] | None = None,
        foundation: list[str] | None = None,
        content_sha256: str | None = None,
    ) -> dict[str, object]:
        plan = {
            "schema_version": 6,
            "plan_id": "PLAN-DELTA",
            "revision": 1,
            "objective": "Deliver the round outcome",
            "max_parallel_workers": 1,
            "sources": [delta_source(content_sha256 or self.delta_sha)],
            "traces": [],
            "missions": [
                mission(
                    ["PRD-101"] if mission_trace_ids is None else mission_trace_ids,
                    [["PRD-101"], ["PRD-102"]] if task_trace_ids is None else task_trace_ids,
                )
            ],
        }
        if foundation is not None:
            plan["foundation_trace_ids"] = foundation
        return plan

    def test_delta_bound_traces_and_foundation_pass(self) -> None:
        self.write_plan(
            self.bound_plan(
                mission_trace_ids=["PRD-101"],
                task_trace_ids=[["PRD-101"], ["PRD-102"], ["PRD-900"]],
                foundation=["PRD-900"],
            )
        )
        code, output = self.run_checker()
        self.assertEqual(0, code, output)
        self.assertIn("scope ok", output)
        self.assertIn("1 new, 1 revised, 1 retired", output)

    def test_retired_trace_fails(self) -> None:
        self.write_plan(
            self.bound_plan(task_trace_ids=[["PRD-101"], ["PRD-103"]])
        )
        code, output = self.run_checker()
        self.assertEqual(1, code, output)
        self.assertIn("retired by the bound PRD delta", output)

    def test_unknown_trace_fails(self) -> None:
        self.write_plan(
            self.bound_plan(task_trace_ids=[["PRD-101"], ["PRD-999"]])
        )
        code, output = self.run_checker()
        self.assertEqual(1, code, output)
        self.assertIn("PRD-999", output)
        self.assertIn("foundation_trace_ids", output)

    def test_required_yes_delta_id_without_task_fails(self) -> None:
        self.write_plan(
            self.bound_plan(
                mission_trace_ids=["PRD-101"],
                task_trace_ids=[["PRD-102"]],
            )
        )
        code, output = self.run_checker()
        self.assertEqual(1, code, output)
        self.assertIn("PRD-101", output)
        self.assertIn("has no task", output)

    def test_delta_location_parent_traversal_fails(self) -> None:
        self.write_outside_delta()
        self.write_plan(self.plan_with_location("../prd-delta-escape.md"))
        code, output = self.run_checker()
        self.assertEqual(1, code, output)
        self.assertIn("inside the repository root", output)

    def test_delta_location_absolute_path_fails(self) -> None:
        outside = self.write_outside_delta()
        self.write_plan(self.plan_with_location(str(outside)))
        code, output = self.run_checker()
        self.assertEqual(1, code, output)
        self.assertIn("inside the repository root", output)

    def test_content_sha256_mismatch_fails(self) -> None:
        self.write_plan(self.bound_plan(content_sha256="a" * 64))
        code, output = self.run_checker()
        self.assertEqual(1, code, output)
        self.assertIn("content_sha256", output)

    def test_legacy_plan_without_delta_source_passes(self) -> None:
        plan = self.bound_plan()
        plan["sources"] = []
        self.write_plan(plan)
        code, output = self.run_checker()
        self.assertEqual(0, code, output)
        self.assertIn("no prd-delta source", output)

    def test_plan_validation_accepts_prd_delta_source_and_foundation(self) -> None:
        plan = valid_plan()
        plan["sources"].append(delta_source(self.delta_sha))
        plan["foundation_trace_ids"] = ["REQ-000"]

        self.assertEqual([], validate_plan(plan))

        plan["foundation_trace_ids"] = ["REQ-000", "REQ-000"]
        errors = validate_plan(plan)
        self.assertTrue(
            any("must not contain duplicates" in error for error in errors), errors
        )


class DocumentSyncDeltaInventoryTests(unittest.TestCase):
    def test_default_inventory_includes_prd_deltas_when_directory_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "AGENTS.md").write_text("Owner rule.\n", encoding="utf-8")
            deltas = root / "docs/product/deltas"
            deltas.mkdir(parents=True)
            delta = deltas / "PRD-DELTA-EPIC-7.md"
            delta.write_text("# PRD-DELTA-EPIC-7\n", encoding="utf-8")
            (deltas / "notes.txt").write_text("ignored", encoding="utf-8")
            (deltas / "nested").mkdir()
            (deltas / "nested" / "old.md").write_text("history", encoding="utf-8")

            paths = default_inventory(root)
            self.assertIn(DELTA_LOCATION, paths)
            self.assertNotIn("docs/product/deltas/notes.txt", paths)
            self.assertNotIn("docs/product/deltas/nested/old.md", paths)

            delta.unlink()
            self.assertNotIn(DELTA_LOCATION, default_inventory(root))


if __name__ == "__main__":
    unittest.main()
