from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ci_test_shards import (
    CommandError,
    balance_files,
    check_aggregate,
    discover_files,
    load_timings,
)


SCRIPT = SCRIPTS_DIR / "ci_test_shards.py"


class CITestShardTests(unittest.TestCase):
    def test_plan_balances_measured_files_without_overlap(self) -> None:
        files = ["fast.py", "medium.py", "slow.py"]
        timings = {"fast.py": 1.0, "medium.py": 2.0, "slow.py": 4.0}
        shards = balance_files(files, timings, 2)
        self.assertEqual(files, sorted(name for shard in shards for name in shard))
        self.assertEqual(["slow.py"], shards[0])
        self.assertEqual(["fast.py", "medium.py"], shards[1])

    def test_timing_manifest_must_cover_exact_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            test_dir = root / "skills/delivery-harness/scripts/tests"
            test_dir.mkdir(parents=True)
            (test_dir / "test_one.py").write_text("", encoding="utf-8")
            (test_dir / "test_two.py").write_text("", encoding="utf-8")
            manifest = root / "timings.json"
            manifest.write_text(
                json.dumps(
                    {"version": 1, "timings": {"skills/delivery-harness/scripts/tests/test_one.py": 1}}
                ),
                encoding="utf-8",
            )
            args = type("Args", (), {"timings": str(manifest)})()
            discovered = discover_files(root, "harness")
            with self.assertRaises(CommandError) as context:
                load_timings(root, args, discovered)
        self.assertIn("unmeasured", str(context.exception))

    def test_duplicate_timing_keys_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            test_dir = root / "skills/delivery-harness/scripts/tests"
            test_dir.mkdir(parents=True)
            (test_dir / "test_one.py").write_text("", encoding="utf-8")
            manifest = root / "timings.json"
            duplicate_json = (
                '{"version":1,"timings":{"skills/delivery-harness/scripts/tests/test_one.py":1,'
                '"skills/delivery-harness/scripts/tests/test_one.py":2}}'
            )
            manifest.write_text(duplicate_json, encoding="utf-8")
            args = type("Args", (), {"timings": str(manifest), "allow_unmeasured": False})()
            with self.assertRaises(CommandError) as context:
                load_timings(root, args, discover_files(root, "harness"))
        self.assertIn("duplicate timing key", str(context.exception))

    def test_zero_shards_are_rejected(self) -> None:
        timings = {"fast.py": 1.0}
        with self.assertRaises(CommandError):
            balance_files(["fast.py"], timings, 0)

    def test_aggregate_requires_every_result_to_succeed(self) -> None:
        self.assertTrue(check_aggregate(["success", "success"]))
        for bad_result in ("skipped", "failure", "cancelled", "timed_out"):
            with self.subTest(result=bad_result):
                self.assertFalse(check_aggregate(["success", bad_result]))
                self.assertFalse(check_aggregate([]))

    def test_gate_cli_accepts_all_required_successes(self) -> None:
        command = [sys.executable, str(SCRIPT), "gate"]
        for _ in range(9):
            command.extend(("--result", "success"))
        result = subprocess.run(
            command,
            cwd=SCRIPTS_DIR.parents[2], capture_output=True, text=True,
            timeout=15, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("all required matrix jobs succeeded", result.stdout)

    def test_gate_cli_rejects_each_unsuccessful_required_result(self) -> None:
        for status in ("failure", "skipped", "cancelled", "timed_out", "", "unknown"):
            with self.subTest(status=status):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "gate", "--result", "success", "--result", status],
                    cwd=SCRIPTS_DIR.parents[2], capture_output=True, text=True, encoding="utf-8",
                    timeout=15, check=False,
                )
                self.assertEqual(2, result.returncode, result.stderr)
                self.assertIn("a required matrix job did not succeed", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_gate_cli_requires_results(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "gate"],
            cwd=SCRIPTS_DIR.parents[2], capture_output=True, text=True, encoding="utf-8",
            timeout=15, check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("--result", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_profile_command_writes_finite_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            test_dir = root / "skills/delivery-harness/scripts/tests"
            test_dir.mkdir(parents=True)
            (test_dir / "test_one.py").write_text(
                "import unittest\n"
                "class One(unittest.TestCase):\n"
                "    def test_passes(self) -> None:\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            stdout_path = root / "profile-stdout.log"
            stderr_path = root / "profile-stderr.log"
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--repo-root",
                        str(root),
                        "profile",
                        "--suite",
                        "harness",
                        "--source",
                        "test fixture",
                        "--manifest-out",
                        str(root / "timings.json"),
                    ],
                    stdout=stdout,
                    stderr=stderr,
                    cwd=root,
                    timeout=30,
                    check=False,
                )
            self.assertEqual(0, result.returncode, stderr_path.read_text(encoding="utf-8"))
            manifest = json.loads((root / "timings.json").read_text(encoding="utf-8"))
            self.assertEqual(1, manifest["version"])
            self.assertGreater(
                manifest["timings"]["skills/delivery-harness/scripts/tests/test_one.py"], 0
            )

    def test_profile_timeout_saves_partial_file_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            test_dir = root / "skills/delivery-harness/scripts/tests"
            test_dir.mkdir(parents=True)
            (test_dir / "test_one.py").write_text(
                "import unittest\n"
                "class One(unittest.TestCase):\n"
                "    def test_passes(self) -> None:\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            results_path = root / "partial-results.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo-root",
                    str(root),
                    "profile",
                    "--suite",
                    "harness",
                    "--timeout-seconds",
                    "0",
                    "--manifest-out",
                    str(root / "partial-timings.json"),
                    "--results-out",
                    str(results_path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                cwd=root,
                timeout=30,
                check=False,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("timed out", result.stderr)
            payload = json.loads(results_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["timeout"])
            self.assertEqual({}, payload["file_results"])
            self.assertEqual({}, payload["timings"])
            self.assertEqual(0, payload["counts"]["tests"])

    def test_profile_deadline_stops_a_hanging_import_or_test_and_its_child(self) -> None:
        for phase in ("import", "test"):
            with self.subTest(phase), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                test_dir = root / "skills/delivery-harness/scripts/tests"
                test_dir.mkdir(parents=True)
                (test_dir / "test_a_fast.py").write_text(
                    "import unittest, sys\n"
                    "class Fast(unittest.TestCase):\n"
                    "    def test_pass(self):\n"
                    "        print('profile stdout reaches the caller')\n"
                    "        print('profile stderr reaches the caller', file=sys.stderr)\n",
                    encoding="utf-8",
                )
                hang = (
                    "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                    "Path('owned-child.pid').write_text(str(child.pid))\n"
                    "time.sleep(60)\n"
                )
                source = "import subprocess, sys, time, unittest\nfrom pathlib import Path\n"
                source += (hang if phase == "import" else
                           "class Hang(unittest.TestCase):\n    def test_hang(self):\n" +
                           "".join("        " + line + "\n" for line in hang.splitlines()))
                (test_dir / "test_b_hang.py").write_text(source, encoding="utf-8")
                with (root / "stdout.log").open("wb") as stdout, (root / "stderr.log").open("wb") as stderr:
                    started = time.monotonic()
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), "--repo-root", str(root), "profile",
                         "--timeout-seconds", "3", "--manifest-out", str(root / "timings.json"),
                         "--results-out", str(root / "results.json")],
                        cwd=root, stdout=stdout, stderr=stderr, timeout=15, check=False,
                    )
                self.assertLess(time.monotonic() - started, 10)
                self.assertEqual(2, result.returncode)
                payload = json.loads((root / "results.json").read_text(encoding="utf-8"))
                self.assertTrue(payload["timeout"])
                self.assertTrue(payload["incomplete"])
                fast = "skills/delivery-harness/scripts/tests/test_a_fast.py"
                hung = "skills/delivery-harness/scripts/tests/test_b_hang.py"
                self.assertEqual("passed", payload["file_results"][fast]["status"])
                self.assertEqual("timed_out", payload["file_results"][hung]["status"])
                self.assertEqual([fast], list(payload["timings"]))
                self.assertIn("profile stdout reaches the caller", (root / "stdout.log").read_text(encoding="utf-8"))
                self.assertIn("profile stderr reaches the caller", (root / "stderr.log").read_text(encoding="utf-8"))
                process_id = int((root / "owned-child.pid").read_text(encoding="utf-8"))
                if os.name == "nt":
                    import ctypes
                    from ctypes import wintypes
                    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
                    kernel.OpenProcess.restype = wintypes.HANDLE
                    kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
                    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
                    handle = kernel.OpenProcess(0x1000, False, process_id)
                    if handle:
                        try:
                            exit_code = wintypes.DWORD()
                            self.assertTrue(kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code)))
                            self.assertNotEqual(259, exit_code.value)
                        finally:
                            kernel.CloseHandle(handle)
                else:
                    inspection = subprocess.run(["/bin/ps", "-o", "stat=", "-p", str(process_id)],
                                                capture_output=True, text=True, timeout=2, check=False)
                    self.assertTrue(not inspection.stdout.strip() or inspection.stdout.strip().startswith("Z"))

    def test_profile_rejects_nonfinite_and_negative_deadlines(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "skills").mkdir()
            for deadline in ("-1", "nan", "inf"):
                with self.subTest(deadline):
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), "--repo-root", str(root), "profile",
                         "--timeout-seconds", deadline, "--manifest-out", str(root / "timings.json")],
                        cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=15, check=False,
                    )
                    self.assertEqual(2, result.returncode)
                    self.assertIn("finite nonnegative", result.stderr)
                    self.assertFalse((root / "timings.json").exists())

    def test_profile_records_import_errors_empty_files_and_fail_fast(self) -> None:
        for source in ("raise RuntimeError('fixture import fails')\n", "",
                       "import unittest\nclass Broken(unittest.TestCase):\n    def test_fail(self): self.fail('fixture failure')\n"):
            with self.subTest(source), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                test_dir = root / "skills/delivery-harness/scripts/tests"
                test_dir.mkdir(parents=True)
                (test_dir / "test_a_bad.py").write_text(source, encoding="utf-8")
                (test_dir / "test_b_unreached.py").write_text("raise RuntimeError('must not run')\n", encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--repo-root", str(root), "profile", "--fail-fast",
                     "--manifest-out", str(root / "timings.json"), "--results-out", str(root / "results.json")],
                    cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=15, check=False,
                )
                self.assertEqual(2, result.returncode)
                payload = json.loads((root / "results.json").read_text(encoding="utf-8"))
                self.assertTrue(payload["incomplete"])
                self.assertEqual(["skills/delivery-harness/scripts/tests/test_a_bad.py"], list(payload["file_results"]))
                self.assertEqual("failed", next(iter(payload["file_results"].values()))["status"])


if __name__ == "__main__":
    unittest.main()
