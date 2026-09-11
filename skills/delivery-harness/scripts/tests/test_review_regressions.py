#!/usr/bin/env python3
"""Regressions for defects a code review found in the runtime-performance work.

Each of these shipped green because the suite never fed a real
``run_verifier`` record through the manifest validator, never handed the
validator a malformed RUN, and never exercised the budget or streaming
guards at their edges.
"""

from __future__ import annotations

import copy
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

from harness_core import _keys  # noqa: E402
from harness_manifest import validate_run  # noqa: E402
from manifest_fixtures import (  # noqa: E402
    mark_complete,
    valid_plan as valid_current_plan,
    valid_run as valid_current_run,
)
import new_run  # noqa: E402
from new_run import _harness_version  # noqa: E402
from select_ready_nodes import _active_wave_allows_streaming_review  # noqa: E402
from test_graph_orchestration import valid_graph_plan, valid_graph_run  # noqa: E402
from verifier_runtime import CONTEXT_FIELDS, run_verifier  # noqa: E402


def real_verifier_record(**cache_extra):
    """Run a verifier for real and return the record the parent must retain."""

    root = Path(tempfile.mkdtemp())
    (root / "co").mkdir()
    verifier = {
        "id": "V1",
        "cwd": ".",
        "argv": [sys.executable, "-c", "raise SystemExit(0)"],
        "pass_signal": "exit 0",
        "cache": {"mode": "session_exact", "environment_keys": [], **cache_extra},
        "execution": {"parallel_safe": True, "resources": []},
    }
    supplied = {
        "run_id": "R",
        "plan_revision": 1,
        "plan_digest_sha256": "a" * 64,
        "graph_revision": 1,
        "batch_base_sha": "b" * 40,
        "head_sha": "c" * 40,
        "layer": "batch",
        "trust_domain": "local",
        "checkout_role": "parent",
        "checkout_dirty": False,
        "cache_safe": True,
        "changed_files": [],
    }
    context = {key: supplied.get(key) for key in CONTEXT_FIELDS}
    return run_verifier(
        verifier,
        context,
        checkout_root=root / "co",
        cache_root=root / "cache",
        environment={},
    )


class RetainedVerifierRecordTests(unittest.TestCase):
    """The record run_verifier emits must satisfy the validator that reads it.

    `execution` and `cache.deterministic_local` are copied into the retained
    record verbatim, so a run using either feature produced evidence its own
    validator rejected as unknown keys.
    """

    def assert_record_shape_accepted(self, record) -> None:
        errors: list[str] = []
        _keys(
            errors,
            "verifier",
            record["verifier"],
            {"id", "cwd", "argv", "pass_signal", "cache"},
            {"execution"},
        )
        _keys(
            errors,
            "verifier.cache",
            record["verifier"]["cache"],
            {"mode", "environment_keys"},
            {"deterministic_local"},
        )
        self.assertEqual([], errors)

    def test_execution_block_survives_the_retained_record(self) -> None:
        record = real_verifier_record()

        self.assertIn("execution", record["verifier"])
        self.assert_record_shape_accepted(record)

    def test_deterministic_local_survives_the_retained_record(self) -> None:
        record = real_verifier_record(deterministic_local=True)

        self.assertIn("deterministic_local", record["verifier"]["cache"])
        self.assert_record_shape_accepted(record)


class MalformedRunTests(unittest.TestCase):
    def test_non_dict_runtime_capabilities_returns_errors_instead_of_raising(self) -> None:
        # The platform_lifecycle guard sat outside the isinstance check, so a
        # malformed RUN crashed the validator. select_ready_nodes and
        # harness_step only catch GraphSelectionError, so the crash escaped.
        for malformed in (None, [], "runtime"):
            with self.subTest(value=malformed):
                plan = valid_graph_plan()
                run = valid_graph_run(plan)
                run["runtime_capabilities"] = malformed

                errors = validate_run(plan, run)

                self.assertIn("run.runtime_capabilities: must be an object", errors)


class StreamingGuardTests(unittest.TestCase):
    def state(self):
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        run["active_wave"] = {
            "wave_id": "W1",
            "status": "active",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": None,
            "batch_base_sha": None,
            "selected_missions": ["M1"],
            "deferred_missions": [],
            "conflict_edges": [],
        }
        return plan, run

    def test_a_deterministic_gate_still_waits_for_wave_close(self) -> None:
        # Route edges are ANY-matched, so allowing an unbound verifier node
        # through would fire a batch or integration gate the moment any
        # streamed review passed, with writers still live.
        _, run = self.state()
        gate = {"id": "N-GATE", "kind": "verifier", "executor": "local_command"}

        self.assertFalse(_active_wave_allows_streaming_review(gate, run))

    def test_an_approval_may_proceed_during_the_wave(self) -> None:
        _, run = self.state()
        approval = {"id": "N-APPROVAL", "kind": "approval", "executor": "human"}

        self.assertTrue(_active_wave_allows_streaming_review(approval, run))

    def test_a_writer_never_proceeds_during_the_wave(self) -> None:
        _, run = self.state()
        mission = {"id": "N-M2", "kind": "mission", "executor": "runtime_worker"}

        self.assertFalse(_active_wave_allows_streaming_review(mission, run))


class HarnessVersionTests(unittest.TestCase):
    def test_version_refuses_an_unrelated_package_json_without_skill_metadata(self) -> None:
        # A standalone skill install has no package.json above it. Walking on
        # would record whatever app owns the user's home directory into
        # version_gate.required_harness_version.
        import json
        import tempfile
        from pathlib import Path

        root = Path(tempfile.mkdtemp())
        (root / "package.json").write_text(
            json.dumps({"name": "unrelated", "version": "9.9.9"}), encoding="utf-8"
        )
        standalone = root / "agent" / "skills" / "harness" / "scripts"
        standalone.mkdir(parents=True)
        original = new_run.__file__
        try:
            new_run.__file__ = str(standalone / "new_run.py")
            with self.assertRaisesRegex(
                new_run.ManifestError, "install delivery-harness with its VERSION file"
            ):
                new_run._harness_version()
        finally:
            new_run.__file__ = original

    def test_version_resolves_from_skill_local_metadata(self) -> None:
        version = _harness_version()

        self.assertRegex(version, r"^\d+\.\d+\.\d+")

    def test_version_resolves_from_a_standalone_skill_copy(self) -> None:
        import tempfile
        from pathlib import Path

        root = Path(tempfile.mkdtemp())
        standalone = root / "agent" / "skills" / "delivery-harness"
        scripts = standalone / "scripts"
        scripts.mkdir(parents=True)
        (standalone / "VERSION").write_text("7.8.9\n", encoding="utf-8")
        original = new_run.__file__
        try:
            new_run.__file__ = str(scripts / "new_run.py")
            self.assertEqual("7.8.9", new_run._harness_version())
        finally:
            new_run.__file__ = original


class ManifestIdentityTests(unittest.TestCase):
    def test_attempt_ids_are_unique(self) -> None:
        plan = valid_current_plan()
        run = valid_current_run(plan)
        attempt = {
            "attempt_id": "ATT-DUPLICATE",
            "mission_id": None,
            "task_id": None,
            "lease_id": None,
            "kind": "closeout",
            "result": "PASS",
            "evidence": [],
            "review_lineage_id": None,
            "failure_family_ids": [],
        }
        run["attempt_log"] = [attempt, copy.deepcopy(attempt)]

        self.assertIn(
            "run.attempt_log[1].attempt_id: must be unique",
            validate_run(plan, run),
        )

    def test_worker_lease_ids_are_unique(self) -> None:
        plan = valid_current_plan()
        run = valid_current_run(plan)
        mark_complete(plan, run)
        duplicate = copy.deepcopy(run["workers"][0])
        duplicate["worker_id"] = "W-DUPLICATE-LEASE"
        run["workers"].append(duplicate)

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                error.startswith("run.workers[2].lease_id: must be unique across workers")
                for error in errors
            ),
            errors,
        )

    def test_lease_id_cannot_bind_two_missions(self) -> None:
        plan = valid_current_plan()
        run = valid_current_run(plan)
        mark_complete(plan, run)
        first_lease = run["mission_states"]["M1"]["lease_id"]
        run["mission_states"]["M2"]["lease_id"] = first_lease

        self.assertIn(
            "run.mission_states.M2.lease_id: "
            f"lease {first_lease!r} is already bound to mission 'M1'",
            validate_run(plan, run),
        )

    def test_review_worker_attempt_ids_are_unique(self) -> None:
        plan = valid_current_plan()
        run = valid_current_run(plan)
        mark_complete(plan, run)
        duplicate_index = len(run["review_workers"])
        duplicate = copy.deepcopy(run["review_workers"][0])
        duplicate["worker_id"] = "RW-DUPLICATE-ATTEMPT"
        run["review_workers"].append(duplicate)

        self.assertIn(
            f"run.review_workers[{duplicate_index}].attempt_id: "
            "must be unique across review workers",
            validate_run(plan, run),
        )

    def test_active_review_attempt_cannot_collide_with_attempt_log(self) -> None:
        plan = valid_current_plan()
        run = valid_current_run(plan)
        mark_complete(plan, run)
        worker = run["review_workers"][0]
        worker["phase"] = "worker_running"
        worker["outcome"] = None
        worker["findings"] = []
        node_state = run["graph_state"]["node_states"][worker["node_id"]]
        node_state["phase"] = "running"
        node_state["last_outcome"] = None
        run["attempt_log"].append(
            {
                "attempt_id": worker["attempt_id"],
                "mission_id": "M1",
                "task_id": None,
                "lease_id": run["mission_states"]["M1"]["lease_id"],
                "kind": "worker_verifier",
                "result": "PASS",
                "evidence": [],
                "review_lineage_id": None,
                "failure_family_ids": [],
            }
        )

        self.assertIn(
            "run.review_workers[0].attempt_id: "
            "active review attempt must not collide with attempt_log",
            validate_run(plan, run),
        )


if __name__ == "__main__":
    unittest.main()
