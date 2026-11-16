#!/usr/bin/env python3
"""Dedicated tests for plan_width.py."""

from __future__ import annotations

import copy
import io
import json
import random
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import plan_width  # noqa: E402
from harness_schema import PLAN_HEADING  # noqa: E402
from manifest_fixtures import (  # noqa: E402
    conditional_final_candidate_plan,
    graph_for,
    graph_node,
    manifest_markdown,
    mission,
    task,
    valid_plan,
)
from test_graph_orchestration import detach_mission_edges  # noqa: E402


OUTCOMES = ["pass", "retryable_failure", "blocked", "contract_gap"]


def write_plan(root: Path, plan: dict[str, object]) -> Path:
    path = root / "PLAN.md"
    path.write_text(
        manifest_markdown(PLAN_HEADING, "harness_plan", plan), encoding="utf-8"
    )
    return path


def run_tool(plan: dict[str, object], *flags: str) -> tuple[int, str, str]:
    with tempfile.TemporaryDirectory() as directory:
        path = write_plan(Path(directory), plan)
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = plan_width.main(["--plan", str(path), *flags])
    return code, stdout.getvalue(), stderr.getvalue()


def json_result(plan: dict[str, object]) -> dict[str, object]:
    code, stdout, _ = run_tool(plan, "--json")
    assert code == 0, stdout
    return json.loads(stdout)


def scoped_mission(mission_id: str, scope: str) -> dict[str, object]:
    return mission(
        mission_id,
        f"REQ-{mission_id[1:]}",
        scope,
        [task(mission_id, 1, f"REQ-{mission_id[1:]}", f"src/{mission_id.lower()}/one.py")],
    )


def bare_graph(plan: dict[str, object], mission_ids: list[str]) -> None:
    plan["graph"] = {
        "entry_nodes": [f"N-{mission_id}" for mission_id in mission_ids],
        "nodes": [
            graph_node(f"N-{mission_id}", "mission", mission_id, "runtime_worker", OUTCOMES)
            for mission_id in mission_ids
        ],
        "edges": [],
    }


def diamond_plan() -> dict[str, object]:
    plan = valid_plan()
    plan["missions"] = [scoped_mission(f"M{index}", f"src/m{index}/**") for index in range(1, 5)]
    bare_graph(plan, ["M1", "M2", "M3", "M4"])
    plan["graph"]["edges"] = [
        {
            "id": f"E-{source}-{target}",
            "kind": "dependency",
            "from": f"N-{source}",
            "to": f"N-{target}",
            "on_outcomes": ["pass"],
            "max_traversals": None,
        }
        for source, target in (("M1", "M2"), ("M1", "M3"), ("M2", "M4"), ("M3", "M4"))
    ]
    return plan


class PlanWidthTests(unittest.TestCase):
    def test_chained_disjoint_missions_have_width_one_and_two_chain_findings(self) -> None:
        missions = [
            scoped_mission("M1", "src/a/**"),
            scoped_mission("M2", "src/b/**"),
            scoped_mission("M3", "src/c/**"),
        ]
        plan = valid_plan()
        plan["missions"] = missions
        plan["graph"] = graph_for(*missions)
        code, stdout, _ = run_tool(plan)
        self.assertEqual(0, code)
        self.assertEqual(
            "plan width: 1 (dependency width 1, 3 missions, budget 3)",
            stdout.splitlines()[0],
        )
        self.assertIn(
            "chain_without_conflict: M1, M2 — M2 waits for M1 although their scopes "
            "and resources do not conflict; keep the edge only if M2 consumes "
            "something M1 produces",
            stdout.splitlines(),
        )
        result = json_result(plan)
        self.assertEqual([["M1"], ["M2"], ["M3"]], result["levels"])
        self.assertEqual(1, result["width"])
        self.assertEqual(1, result["dependency_width"])
        self.assertEqual(["M1", "M2", "M3"], result["critical_path"])
        chains = [
            finding for finding in result["findings"]
            if finding["code"] == "chain_without_conflict"
        ]
        self.assertEqual([["M1", "M2"], ["M2", "M3"]], [item["missions"] for item in chains])

    def test_diamond_gives_width_two_and_three_levels(self) -> None:
        result = json_result(diamond_plan())
        self.assertEqual([["M1"], ["M2", "M3"], ["M4"]], result["levels"])
        self.assertEqual(2, result["width"])
        self.assertEqual(2, result["dependency_width"])
        self.assertEqual(["M1", "M2", "M4"], result["critical_path"])

    def test_same_level_scope_overlap_limits_width_and_reports_conflict(self) -> None:
        plan = valid_plan()
        plan["missions"] = [scoped_mission("M1", "src/a/**"), scoped_mission("M2", "src/a/two.py")]
        bare_graph(plan, ["M1", "M2"])
        result = json_result(plan)
        self.assertEqual(1, result["width"])
        conflicts = [
            finding for finding in result["findings"]
            if finding["code"] == "same_level_conflict"
        ]
        self.assertEqual(1, len(conflicts))
        self.assertEqual(["M1", "M2"], conflicts[0]["missions"])
        self.assertIn("share level 0 but conflict: scope_overlap", conflicts[0]["detail"])

    def test_three_missions_on_one_serialized_resource_are_reported(self) -> None:
        plan = valid_plan()
        missions = [scoped_mission(f"M{index}", f"src/m{index}/**") for index in range(1, 4)]
        for item in missions:
            item["serialized_resources"] = ["db:primary"]
        plan["missions"] = missions
        bare_graph(plan, ["M1", "M2", "M3"])
        result = json_result(plan)
        shared = [
            finding for finding in result["findings"]
            if finding["code"] == "shared_exclusive_resource"
        ]
        self.assertEqual(1, len(shared))
        self.assertEqual(["M1", "M2", "M3"], shared[0]["missions"])
        self.assertIn('"db:primary"', shared[0]["detail"])
        self.assertIn("a per-worktree port or database path removes the claim", shared[0]["detail"])
        self.assertEqual(1, result["width"])

    def test_budget_below_width_is_reported(self) -> None:
        plan = valid_plan()
        detach_mission_edges(plan)
        plan["max_parallel_workers"] = 1
        code, stdout, _ = run_tool(plan)
        self.assertEqual(0, code)
        self.assertEqual(
            "plan width: 2 (dependency width 2, 2 missions, budget 1)",
            stdout.splitlines()[0],
        )
        result = json_result(plan)
        budgets = [
            finding for finding in result["findings"]
            if finding["code"] == "budget_below_width"
        ]
        self.assertEqual(1, len(budgets))
        self.assertEqual([], budgets[0]["missions"])
        self.assertIn("max_parallel_workers 1 is below width 2", budgets[0]["detail"])

    def test_conditional_repair_loop_does_not_crash_or_invent_chains(self) -> None:
        plan = conditional_final_candidate_plan()
        code, stdout, _ = run_tool(plan)
        self.assertEqual(0, code)
        result = json_result(plan)
        self.assertEqual([["M1", "M3", "M4"], ["M2"]], result["levels"])
        self.assertEqual(2, result["width"])
        self.assertTrue(
            any(
                finding["code"] == "chain_without_conflict"
                and finding["missions"] == ["M1", "M2"]
                for finding in result["findings"]
            )
        )
        self.assertEqual(
            [],
            [
                finding
                for finding in result["findings"]
                if finding["code"] == "chain_without_conflict"
                and "M4" in finding["missions"]
            ],
        )

    def test_conflict_free_independent_missions_report_no_findings(self) -> None:
        plan = valid_plan()
        detach_mission_edges(plan)
        code, stdout, _ = run_tool(plan)
        self.assertEqual(0, code)
        self.assertEqual(
            "plan width: 2 (dependency width 2, 2 missions, budget 3)",
            stdout.splitlines()[0],
        )
        self.assertEqual("findings: none", stdout.splitlines()[-1])

    def test_shuffled_order_gives_identical_json_bytes(self) -> None:
        def varied_plan() -> dict[str, object]:
            plan = diamond_plan()
            extras = [scoped_mission(f"M{index}", f"src/x{index}/**") for index in (5, 6, 7)]
            for item in extras:
                item["serialized_resources"] = ["db:pool"]
            plan["missions"].extend(extras)
            plan["graph"]["nodes"].extend(
                graph_node(f"N-M{index}", "mission", f"M{index}", "runtime_worker", OUTCOMES)
                for index in (5, 6, 7)
            )
            plan["max_parallel_workers"] = 1
            return plan

        plan_a = varied_plan()
        plan_b = copy.deepcopy(plan_a)
        for plan, seed in ((plan_a, 11), (plan_b, 29)):
            random.Random(seed).shuffle(plan["missions"])
            random.Random(seed + 1).shuffle(plan["graph"]["nodes"])
            random.Random(seed + 2).shuffle(plan["graph"]["edges"])
        code_a, stdout_a, _ = run_tool(plan_a, "--json")
        code_b, stdout_b, _ = run_tool(plan_b, "--json")
        self.assertEqual(0, code_a)
        self.assertEqual(0, code_b)
        self.assertEqual(stdout_a.encode("utf-8"), stdout_b.encode("utf-8"))
        result = json.loads(stdout_a)
        self.assertEqual(
            {
                "plan_id",
                "revision",
                "missions",
                "configured_max_parallel_workers",
                "levels",
                "dependency_width",
                "width",
                "critical_path",
                "findings",
            },
            set(result),
        )
        codes = {finding["code"] for finding in result["findings"]}
        self.assertEqual(
            {
                "chain_without_conflict",
                "same_level_conflict",
                "shared_exclusive_resource",
                "budget_below_width",
            },
            codes,
        )

    def test_unreadable_plan_exits_two_with_one_error_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "PLAN.md"
            path.write_text("# No manifest here\n", encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = plan_width.main(["--plan", str(path)])
        self.assertEqual(2, code)
        self.assertEqual("", stdout.getvalue())
        self.assertEqual(1, len(stderr.getvalue().strip().splitlines()))

    def test_missing_plan_file_exits_two(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = plan_width.main(["--plan", "missing/PLAN.md"])
        self.assertEqual(2, code)
        self.assertEqual(1, len(stderr.getvalue().strip().splitlines()))

    def test_plan_without_required_keys_exits_two(self) -> None:
        plan = valid_plan()
        del plan["max_parallel_workers"]
        with tempfile.TemporaryDirectory() as directory:
            path = write_plan(Path(directory), plan)
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = plan_width.main(["--plan", str(path)])
        self.assertEqual(2, code)
        self.assertEqual(1, len(stderr.getvalue().strip().splitlines()))


if __name__ == "__main__":
    unittest.main()
