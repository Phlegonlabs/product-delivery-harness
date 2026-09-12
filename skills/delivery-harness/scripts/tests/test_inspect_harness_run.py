import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import inspect_harness_run


class InspectHarnessRunTests(unittest.TestCase):
    def test_summary_flags_live_head_and_dirty_worktree_drift(self) -> None:
        recorded_m1 = "a" * 40
        recorded_m2 = "b" * 40
        live_m2 = "c" * 40
        run = {
            "schema_version": 10,
            "run_id": "RUN-1",
            "status": "running",
            "active_wave": {
                "wave_id": "W1",
                "status": "active",
                "selected_missions": ["M1", "M2"],
            },
            "integration": {"integration_head_sha": recorded_m1},
            "mission_states": {
                "M1": {"phase": "integrated", "head_sha": recorded_m1},
                "M2": {"phase": "worker_running", "head_sha": recorded_m2},
            },
            "workers": [
                {"mission_id": "M1", "worktree_path": "m1"},
                {"mission_id": "M2", "worktree_path": "m2"},
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "m1").mkdir()
            (root / "m2").mkdir()

            def fake_git(worktree: Path, *args: str) -> str:
                if args == ("rev-parse", "HEAD"):
                    return recorded_m1 if worktree.name == "m1" else live_m2
                if args == ("status", "--porcelain"):
                    return "" if worktree.name == "m1" else " M src/file.ts"
                raise AssertionError(args)

            with patch.object(inspect_harness_run, "_git", side_effect=fake_git):
                summary = inspect_harness_run.summarize_run(root, run)

        self.assertFalse(summary["missions"][0]["needs_reconciliation"])
        self.assertTrue(summary["missions"][1]["needs_reconciliation"])
        self.assertEqual(
            summary["warnings"],
            ["M2: head advanced or diverged, worktree dirty"],
        )
        self.assertEqual(summary["runtime_process_state"], "not inspected")
        self.assertIn("RECONCILE", inspect_harness_run.render_text(summary))

    def test_clean_recorded_worker_is_aligned(self) -> None:
        head = "d" * 40
        run = {
            "schema_version": 10,
            "run_id": "RUN-2",
            "status": "running",
            "active_wave": None,
            "integration": {},
            "mission_states": {
                "M1": {"phase": "worker_running", "head_sha": head},
            },
            "workers": [{"mission_id": "M1", "worktree_path": "m1"}],
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "m1").mkdir()
            with patch.object(
                inspect_harness_run,
                "_git",
                side_effect=[head, ""],
            ):
                summary = inspect_harness_run.summarize_run(root, run)

        self.assertEqual(summary["warnings"], [])
        self.assertFalse(summary["missions"][0]["live_dirty"])

    def test_summary_surfaces_the_recorded_runtime_version_gate(self) -> None:
        run = {
            "schema_version": 10,
            "run_id": "RUN-VERSION",
            "status": "running",
            "runtime_capabilities": {
                "runtime_adapter": {
                    "version_gate": {
                        "host_version": "0.146.0",
                        "harness_version": "0.5.0",
                        "required_harness_version": "0.6.0",
                        "status": "upgrade_required",
                    }
                }
            },
            "active_wave": None,
            "integration": {},
            "mission_states": {},
            "workers": [],
        }

        summary = inspect_harness_run.summarize_run(Path.cwd(), run)

        self.assertEqual("upgrade_required", summary["runtime_version_gate"]["status"])
        rendered = inspect_harness_run.render_text(summary)
        self.assertIn("Runtime version gate: upgrade_required", rendered)
        self.assertIn("required=0.6.0", rendered)

    def test_summary_counts_attested_ui_records_and_names_gaps(self) -> None:
        run = {
            "schema_version": 11,
            "run_id": "RUN-ATTEST",
            "status": "complete",
            "active_wave": None,
            "integration": {},
            "mission_states": {},
            "workers": [],
            "runtime_capabilities": {
                "runtime_adapter": {
                    "version_gate": {"required_harness_version": "0.35.0"}
                }
            },
            "ui_evidence": [
                {
                    "surface_id": "S1",
                    "route": "/",
                    "breakpoint": "1280",
                    "state": "ready",
                    "layout_check": "pass",
                },
                {
                    "surface_id": "S1",
                    "route": "/",
                    "breakpoint": "375",
                    "state": "ready",
                    "layout_check": "fail — .card",
                },
                {"surface_id": "S1", "route": "/", "breakpoint": "768", "state": "ready"},
            ],
            "deviation_ledger": [
                {
                    "surface_id": "S1",
                    "route": "/",
                    "breakpoint": "375",
                    "state": "ready",
                    "difference": "8px corner radius",
                    "citation": "PRD UI-1 allowed deviations: radius",
                },
                {
                    "surface_id": "S1",
                    "route": "/",
                    "breakpoint": "375",
                    "state": "error",
                    "difference": "shadow strength",
                },
            ],
            "ui_impact_summary": [
                {"mission_id": "M1", "impact": "none"},
                {"mission_id": "M2", "impact": "structure"},
            ],
        }

        summary = inspect_harness_run.summarize_run(Path.cwd(), run)
        attestations = summary["attestations"]

        self.assertEqual(3, attestations["ui_evidence_rows"])
        self.assertEqual(
            ["S1///375/ready", "S1///768/ready"],
            attestations["layout_check_failing_or_missing"],
        )
        self.assertEqual(2, attestations["deviation_ledger_rows"])
        self.assertEqual(
            ["S1///375/error"], attestations["ledger_rows_missing_citation"]
        )
        self.assertEqual(2, attestations["ui_impact_summary_rows"])
        self.assertEqual(["M2"], attestations["impact_rows_missing_doc_delta"])

        rendered = inspect_harness_run.render_text(summary)
        self.assertIn("UI attestations: evidence=3 | ledger=2 | impact=2", rendered)
        self.assertIn(
            "- layout_check failing/missing: S1///375/ready, S1///768/ready", rendered
        )
        self.assertIn("- ledger rows missing citation: S1///375/error", rendered)
        self.assertIn("- impact rows missing doc_delta: M2", rendered)

    def test_running_worker_without_a_worktree_requires_reconciliation(self) -> None:
        run = {
            "schema_version": 10,
            "run_id": "RUN-3",
            "status": "running",
            "active_wave": None,
            "integration": {},
            "mission_states": {
                "M1": {"phase": "worker_running", "head_sha": "e" * 40},
                "M2": {"phase": "queued", "head_sha": None},
            },
            "workers": [],
        }

        summary = inspect_harness_run.summarize_run(Path.cwd(), run)

        self.assertTrue(summary["missions"][0]["needs_reconciliation"])
        self.assertFalse(summary["missions"][1]["needs_reconciliation"])
        self.assertEqual(summary["warnings"], ["M1: worktree unavailable"])


if __name__ == "__main__":
    unittest.main()
