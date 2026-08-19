#!/usr/bin/env python3
"""Regressions for defects a code review found in the runtime-performance work.

Each of these shipped green because the suite never fed a real
``run_verifier`` record through the manifest validator, never handed the
validator a malformed RUN, and never exercised the budget or streaming
guards at their edges.
"""

from __future__ import annotations

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
    def test_version_resolves_from_the_nearest_package_json(self) -> None:
        # A fixed parent depth resolved correctly only in the canonical tree;
        # the shipped plugin copy silently recorded "0.0.0" in the very field
        # the runtime upgrade gate checks.
        version = _harness_version()

        self.assertNotEqual("0.0.0", version)
        self.assertRegex(version, r"^\d+\.\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
