"""RUN retains a digest of the tracked-file fingerprint, not the per-file map."""
import hashlib
import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness_worker_result_transition import _retained_execution  # noqa: E402


class CompactTrackedFilesRetentionTest(unittest.TestCase):
    def test_retained_record_keeps_digest_and_count_only(self) -> None:
        tracked = {
            f"src/file{i}.py": {"stat": [1, i, 10, 2, 3, 33188], "sha256": "0" * 64}
            for i in range(3)
        }
        attestation = {
            "checkout_root": "C:/wt",
            "git_guard": {"expected_branch": "m1", "expected_head_sha": "a" * 40, "ignored_paths": []},
            "isolation_mode": "host",
            "source_head_sha": "a" * 40,
            "tracked_files": tracked,
            "protected_path_sha256": {},
            "protected_path_stats": {},
            "host_execution_attestation": {"isolation": "host"},
        }
        retained = {
            "verifier_id": "M1-T01-focused-1",
            "execution_key": "b" * 64,
            "evidence_key": "b" * 64,
            "protocol": "harness-verifier-execution-v2",
            "stdout": "",
            "stderr": "",
            "context": {"layer": "task", "mission_id": "M1", "task_id": "M1/T01", "attempt_id": "A", "lease_id": "L"},
            "key_document": {},
            "verifier": {"id": "M1-T01-focused-1"},
            "status": "PASS",
            "exit_code": 0,
            "cache_status": "disabled",
            "cache_reason": "host",
            "duration_ms": 1,
            "metrics": {},
            "git_guard_attestation": attestation,
        }
        record = _retained_execution({"verifier_executions": []}, retained, [])
        compact = record["git_guard_attestation"]
        canonical = json.dumps(tracked, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual({}, compact["tracked_files"])
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), compact["tracked_files_sha256"])
        self.assertEqual(3, compact["tracked_files_count"])
        self.assertEqual(tracked, attestation["tracked_files"], "the external result is untouched")
        self.assertEqual(attestation["git_guard"], compact["git_guard"])


if __name__ == "__main__":
    unittest.main()
