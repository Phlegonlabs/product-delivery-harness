#!/usr/bin/env python3
"""Deterministic temporary-directory tests for the bash skill installer."""

from __future__ import annotations

import os
import subprocess
import time
import unittest
from pathlib import Path

from install_script_fixture import (
    BASH,
    INSTALL_TIMEOUT,
    POWERSHELL,
    REPO_ROOT,
    InstallScriptCase,
    bash_path,
)


class InstallScriptBashTests(InstallScriptCase):
    def test_bash_foreign_race_target_is_never_deleted(self) -> None:
        self.destination.mkdir(parents=True)
        result = self.run_bash(
            {
                "SKILL_BACKUP_ROOT": str(self.backup_root),
                "PDH_INSTALL_TEST_CREATE_FOREIGN_TARGET": "product-definition-builder",
            }
        )
        self.assertNotEqual(0, result.returncode)
        sentinel = self.destination / "product-definition-builder" / "keep.txt"
        self.assertEqual("foreign sentinel\n", sentinel.read_text(encoding="utf-8"))
        self.assertFalse((self.destination / "delivery-harness").exists())

    def test_bash_marker_failures_restore_and_release_the_lock(self) -> None:
        self.seed_managed_copies()
        result = self.run_bash(
            {
                "SKILL_BACKUP_ROOT": str(self.backup_root),
                "PDH_INSTALL_TEST_FAIL_OWNER_MARKER": "product-definition-builder",
            }
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("induced target owner marker failure", result.stderr)
        self.assert_old_copies_restored()
        self.assertFalse((self.destination / ".pdh-install.lock").exists())

        empty_destination = self.home / "empty-skills"
        result = subprocess.run(
            [BASH, str(REPO_ROOT / "install.sh"), bash_path(empty_destination)],
            capture_output=True,
            text=True,
            cwd=self.home,
            timeout=INSTALL_TIMEOUT,
            env={
                **os.environ,
                "HOME": bash_path(self.home),
                "SKILL_BACKUP_ROOT": bash_path(self.backup_root),
                "PDH_INSTALL_TEST_FAIL_LOCK_OWNER": "1",
            },
        )
        self.assertNotEqual(0, result.returncode)
        self.assertFalse((empty_destination / ".pdh-install.lock").exists())

    def test_bash_destination_lock_serializes_installers(self) -> None:
        if BASH is None:
            self.skipTest("no usable bash is available")
        git_root = Path(BASH).resolve().parents[1]
        env = {
            **os.environ,
            "HOME": bash_path(self.home),
            "PATH": str(git_root / "usr" / "bin") + os.pathsep + os.environ.get("PATH", ""),
            "SKILL_BACKUP_ROOT": bash_path(self.backup_root),
            "PDH_INSTALL_TEST_HOLD_LOCK_SECONDS": "2",
        }
        first = subprocess.Popen(
            [BASH, str(REPO_ROOT / "install.sh"), bash_path(self.destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=self.home,
        )
        lock = self.destination / ".pdh-install.lock"
        # Git Bash needs many seconds of pre-lock source checks before it takes
        # the lock, and it holds the lock for the whole install, so wait until
        # the lock appears or the first installer exits.
        deadline = time.monotonic() + INSTALL_TIMEOUT
        while (
            not lock.exists()
            and first.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.05)
        if not lock.exists():
            first.kill()
            first_stdout, first_stderr = first.communicate()
            self.fail(f"first installer never acquired the lock: {first_stderr or first_stdout}")
        second = self.run_bash({"SKILL_BACKUP_ROOT": str(self.backup_root)})
        first_stdout, first_stderr = first.communicate(timeout=INSTALL_TIMEOUT)
        self.assertEqual(0, first.returncode, first_stderr or first_stdout)
        self.assertNotEqual(0, second.returncode)
        self.assertIn("another install owns destination lock", second.stderr)
        self.assertFalse(lock.exists())

    def test_installers_refuse_ignored_secret_like_source_files(self) -> None:
        source = self.make_minimal_repo()
        (source / ".gitignore").write_text(".env\n.dev.vars\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=source, check=True)
        subprocess.run(["git", "commit", "-qm", "ignore secrets"], cwd=source, check=True)
        (source / "skills" / "delivery-harness" / ".env").write_text(
            "placeholder-only\n", encoding="utf-8"
        )

        if BASH is not None:
            result = subprocess.run(
                [BASH, str(source / "install.sh"), bash_path(self.destination)],
                capture_output=True,
                text=True,
                cwd=self.home,
                timeout=INSTALL_TIMEOUT,
                env={
                    **os.environ,
                    "HOME": bash_path(self.home),
                    "SKILL_BACKUP_ROOT": bash_path(self.backup_root),
                },
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("ignored source artifact is not installable", result.stderr)
        if POWERSHELL is not None:
            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(source / "install.ps1"),
                    "-Destination",
                    str(self.destination),
                    "-BackupRoot",
                    str(self.backup_root),
                ],
                capture_output=True,
                text=True,
                cwd=self.home,
                timeout=INSTALL_TIMEOUT,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("untracked or ignored source artifact is not installable", result.stderr + result.stdout)

    @unittest.skipIf(BASH is None, "no usable bash is available")
    def test_bash_keeps_an_existing_source_receipt(self) -> None:
        source = self.make_minimal_repo()
        self.assert_planted_receipt_preserved(
            lambda: self.run_bash(
                {"SKILL_BACKUP_ROOT": str(self.backup_root)}, installer=source / "install.sh"
            )
        )

    @unittest.skipIf(BASH is None, "no usable bash is available")
    def test_bash_prints_and_records_source_commit_and_dirty_state(self) -> None:
        source = self.make_minimal_repo()
        self.assert_source_line_recorded(
            source,
            lambda: self.run_bash(
                {"SKILL_BACKUP_ROOT": str(self.backup_root)}, installer=source / "install.sh"
            ),
        )


if __name__ == "__main__":
    unittest.main()
