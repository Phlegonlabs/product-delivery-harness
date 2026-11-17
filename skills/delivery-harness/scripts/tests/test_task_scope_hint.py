"""A task commit may touch any path its mission's tasks list; a task's own
write_scope is a planning hint, not an isolation boundary."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import test_validate_worker_result as base  # noqa: E402


T01 = "M1/T01"
T02 = "M1/T02"
FIRST_SHA = "e" * 40
CHANGED = ["src/m1/two/shared.py"]


def two_task_plan():
    """T01 lists src/m1/one/**, T02 lists src/m1/two/**, the mission src/m1/**.
    Task verifiers bind to each task's own head and slice, so the fixture
    keeps only the mission verifier."""

    plan = base.make_plan()
    mission = plan["missions"][0]
    first = mission["tasks"][0]
    first.update(write_scope=["src/m1/one/**"], verifiers=[])
    second = copy.deepcopy(first)
    second.update(id=T02, alias="task-2", depends_on=[T01], write_scope=["src/m1/two/**"])
    second["acceptance_matrix"][0]["test_id"] = "TEST-M1-02"
    mission["tasks"].append(second)
    return plan


def validate(plan, t01_paths, *, reverse_tasks=False, amendments=None):
    run = base.make_run(plan)
    if amendments is not None:
        run["scope_amendments"] = amendments
    run["task_states"][T02] = copy.deepcopy(run["task_states"][T01])
    result = base.make_result(plan)
    result["changed_files"] = list(CHANGED)
    result["commits"] = [FIRST_SHA, base.HEAD_SHA]
    first = result["task_results"][0]
    first.update(head_sha=FIRST_SHA, commits=[FIRST_SHA], verifier_ids=[])
    second = dict(first, task_id=T02, head_sha=base.HEAD_SHA, commits=[base.HEAD_SHA])
    result["task_results"].append(second)
    if reverse_tasks:
        result["task_results"].reverse()
    result["verifiers"] = [
        {
            "id": "mission-focused",
            "status": "PASS",
            "evidence": base.retained_verifier_result("mission-focused", plan, CHANGED)[
                "execution_key"
            ],
        }
    ]
    return base.validate(
        plan,
        run,
        result,
        observed_files=list(CHANGED),
        observed_task_changed_files={T01: t01_paths, T02: list(CHANGED)},
    )


class TaskScopeHintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = two_task_plan()

    def test_task_commit_inside_its_own_scope_validates(self) -> None:
        self.assertEqual([], validate(self.plan, ["src/m1/one/a.py"]))

    def test_task_commit_may_touch_a_sibling_task_path(self) -> None:
        # T01's commit needs two lines in a file only T02's write_scope lists.
        self.assertEqual([], validate(self.plan, ["src/m1/two/shared.py"]))

    def test_path_outside_the_mission_scope_still_escapes(self) -> None:
        errors = validate(self.plan, ["src/outside/task.py"])
        self.assertEqual({"scope_escape"}, base.error_codes(errors))

    def test_mission_deny_scope_still_wins(self) -> None:
        self.plan["missions"][0]["deny_scope"] = ["src/m1/two/secret/**"]
        errors = validate(self.plan, ["src/m1/two/secret/key.py"])
        self.assertEqual({"denied_path"}, base.error_codes(errors))

    def test_task_deny_scope_still_wins(self) -> None:
        self.plan["missions"][0]["tasks"][0]["deny_scope"] = ["src/m1/two/**"]
        errors = validate(self.plan, ["src/m1/two/shared.py"])
        self.assertEqual({"task_denied_path"}, base.error_codes(errors))

    def test_parent_owned_file_still_fails(self) -> None:
        errors = validate(self.plan, ["docs/goal/RUN.md"])
        self.assertEqual({"task_parent_owned_file"}, base.error_codes(errors))

    def test_mission_path_no_task_lists_stays_parent_only(self) -> None:
        # The acceptance register sits in the last mission's scope for the
        # parent's commit. No task lists it, so a task commit touching it
        # fails even when a later commit reverts it out of the final diff.
        self.plan["missions"][0]["write_scope"].append("docs/verification/**")
        errors = validate(self.plan, ["docs/verification/delivery-results.json"])
        self.assertEqual({"task_scope_escape"}, base.error_codes(errors))

    def test_task_commit_may_touch_an_amended_path(self) -> None:
        # amend-scope adds a path no task lists; a task commit slice may use
        # it, and the same slice fails without the amendment.
        amendment = {
            "id": "SA-001",
            "mission_id": self.plan["missions"][0]["id"],
            "paths": ["src/shared/entry.py"],
            "reason": "wire the mission into the shared entry",
            "recorded_at": "2026-11-16T00:00:00Z",
        }
        self.assertEqual(
            [], validate(self.plan, ["src/shared/entry.py"], amendments=[amendment])
        )
        errors = validate(self.plan, ["src/shared/entry.py"])
        self.assertEqual({"scope_escape"}, base.error_codes(errors))

    def test_task_order_still_enforced(self) -> None:
        errors = validate(self.plan, ["src/m1/two/shared.py"], reverse_tasks=True)
        self.assertIn("task_order_mismatch", base.error_codes(errors))


if __name__ == "__main__":
    unittest.main()
