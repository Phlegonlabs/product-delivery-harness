#!/usr/bin/env python3
"""Deterministic temporary-directory tests for the PowerShell skill installer."""

from __future__ import annotations

import os
import subprocess
import unittest
import re
from pathlib import Path

from install_script_fixture import (
    INSTALL_TIMEOUT,
    POWERSHELL,
    REPO_ROOT,
    InstallScriptCase,
)


class InstallScriptPowerShellTests(InstallScriptCase):
    @unittest.skipIf(POWERSHELL is None, "neither pwsh nor powershell is available")
    def test_powershell_rejects_tracked_symlink_mode_before_mutation(self) -> None:
        source = self.make_minimal_repo()
        relative = "skills/delivery-harness/tracked-link"
        (source / relative).write_text("ordinary working-tree bytes\n", encoding="utf-8")
        blob = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=source,
            input="SKILL.md",
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "update-index", "--add", "--cacheinfo", f"120000,{blob},{relative}"],
            cwd=source,
            check=True,
        )
        result = subprocess.run(
            [
                POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(source / "install.ps1"), "-Destination", str(self.destination),
                "-BackupRoot", str(self.backup_root),
            ],
            capture_output=True,
            text=True,
            cwd=self.home,
            timeout=INSTALL_TIMEOUT,
        )
        self.assertNotEqual(0, result.returncode)
        # pwsh on Linux colors the error record and wraps it with "|" gutters.
        output = re.sub(r"\x1b\[[0-9;]*m", "", result.stderr + result.stdout)
        output = re.sub(r"\s*\n\s*\|\s*", " ", output)
        self.assertIn(
            f"non-regular tracked source entry is not installable: mode=120000 path={relative}",
            output,
        )
        self.assertFalse(self.destination.exists())

    @unittest.skipIf(POWERSHELL is None, "neither pwsh nor powershell is available")
    def test_powershell_keeps_an_existing_source_receipt(self) -> None:
        source = self.make_minimal_repo()
        self.assert_planted_receipt_preserved(
            lambda: subprocess.run(
                [
                    POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(source / "install.ps1"), "-Destination", str(self.destination),
                    "-BackupRoot", str(self.backup_root),
                ],
                capture_output=True, text=True, cwd=self.home, timeout=INSTALL_TIMEOUT,
            )
        )

    @unittest.skipIf(POWERSHELL is None, "neither pwsh nor powershell is available")
    def test_powershell_prints_and_records_source_commit_and_dirty_state(self) -> None:
        source = self.make_minimal_repo()
        command = [
            POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(source / "install.ps1"), "-Destination", str(self.destination),
            "-BackupRoot", str(self.backup_root),
        ]
        self.assert_source_line_recorded(
            source,
            lambda: subprocess.run(
                command, capture_output=True, text=True, cwd=self.home, timeout=INSTALL_TIMEOUT
            ),
        )

    @unittest.skipIf(POWERSHELL is None, "neither pwsh nor powershell is available")
    def test_powershell_has_migration_rollback_and_complete_install_parity(self) -> None:
        self.seed_managed_copies()
        common = [
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "install.ps1"),
            "-Destination",
            str(self.destination),
            "-BackupRoot",
            str(self.backup_root),
        ]
        failed = subprocess.run(
            [POWERSHELL, *common],
            capture_output=True,
            text=True,
            cwd=self.home,
            timeout=INSTALL_TIMEOUT,
            env={**os.environ, "PDH_INSTALL_FAIL_AFTER": "delivery-harness"},
        )
        self.assertNotEqual(0, failed.returncode, failed.stderr or failed.stdout)
        self.assertIn(
            "induced failure after installing delivery-harness",
            failed.stderr + failed.stdout,
        )
        self.assert_old_copies_restored()
        self.assertEqual([], list(self.backup_root.iterdir()))

        succeeded = subprocess.run(
            [POWERSHELL, *common],
            capture_output=True,
            text=True,
            cwd=self.home,
            timeout=INSTALL_TIMEOUT,
            env={**os.environ, "PDH_INSTALL_FAIL_AFTER": ""},
        )
        self.assertEqual(0, succeeded.returncode, succeeded.stderr or succeeded.stdout)
        self.assert_full_install()
        backups = [child for child in self.backup_root.iterdir() if child.is_dir()]
        self.assertEqual(1, len(backups))
        self.assertEqual(
            set(self.MANAGED_SKILLS),
            {child.name for child in backups[0].iterdir()},
        )

    @unittest.skipIf(POWERSHELL is None, "neither pwsh nor powershell is available")
    @unittest.skipIf(os.name != "nt", "GetShortPathNameW 8.3 aliases are Windows-only")
    def test_powershell_short_alias_normalizes_stage_manifest_and_rollback(self) -> None:
        """Exercise Get-Item FullName normalization through an 8.3 alias."""

        import ctypes

        self.seed_managed_copies()
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetShortPathNameW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        kernel32.GetShortPathNameW.restype = ctypes.c_uint32

        def short_path(path: Path) -> Path:
            buffer = ctypes.create_unicode_buffer(32768)
            length = kernel32.GetShortPathNameW(str(path), buffer, len(buffer))
            if not length or buffer.value.casefold() == str(path).casefold():
                self.skipTest("8.3 short-name generation is disabled on this filesystem")
            return Path(buffer.value)

        destination_alias = short_path(self.destination)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        backup_alias = short_path(self.backup_root)
        common = [
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(REPO_ROOT / "install.ps1"), "-Destination", str(destination_alias),
            "-BackupRoot", str(backup_alias),
        ]
        failed = subprocess.run(
            [POWERSHELL, *common], capture_output=True, text=True,
            cwd=self.home, timeout=INSTALL_TIMEOUT,
            env={**os.environ, "PDH_INSTALL_FAIL_AFTER": "delivery-harness"},
        )
        self.assertNotEqual(0, failed.returncode, failed.stderr or failed.stdout)
        self.assert_old_copies_restored()

        succeeded = subprocess.run(
            [POWERSHELL, *common], capture_output=True, text=True,
            cwd=self.home, timeout=INSTALL_TIMEOUT,
            env={**os.environ, "PDH_INSTALL_FAIL_AFTER": ""},
        )
        self.assertEqual(0, succeeded.returncode, succeeded.stderr or succeeded.stdout)
        self.assert_full_install()
        backups = [child for child in self.backup_root.iterdir() if child.is_dir()]
        self.assertEqual(1, len(backups))

    @unittest.skipIf(POWERSHELL is None, "neither pwsh nor powershell is available")
    def test_powershell_rejects_destination_and_backup_junctions_before_mutation(self) -> None:
        command_prefix = [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "install.ps1"),
        ]
        for label in ("destination", "backup"):
            with self.subTest(label=label):
                protected = self.home / f"protected-{label}"
                protected.mkdir()
                sentinel = protected / "keep.txt"
                sentinel.write_text("preserve\n", encoding="utf-8")
                alias = self.home / f"{label}-junction"
                self.make_junction(alias, protected)
                destination = alias if label == "destination" else self.home / "plain-skills"
                backup = alias if label == "backup" else self.home / "plain-backups"
                result = subprocess.run(
                    [
                        *command_prefix,
                        "-Destination",
                        str(destination),
                        "-BackupRoot",
                        str(backup),
                    ],
                    capture_output=True,
                    text=True,
                    cwd=self.home,
                    timeout=INSTALL_TIMEOUT,
                )
                self.assertNotEqual(0, result.returncode)
                self.assertIn(
                    "reparse-point path component is forbidden",
                    result.stderr + result.stdout,
                )
                self.assertEqual("preserve\n", sentinel.read_text(encoding="utf-8"))
                self.assertFalse((protected / ".pdh-install.lock").exists())
                self.assertFalse(
                    any(
                        child.name.startswith(".pdh-install-stage-")
                        for child in protected.iterdir()
                    )
                )

    @unittest.skipIf(POWERSHELL is None, "neither pwsh nor powershell is available")
    def test_powershell_foreign_race_target_is_never_deleted(self) -> None:
        self.destination.mkdir(parents=True)
        result = subprocess.run(
            [
                POWERSHELL,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "install.ps1"),
                "-Destination",
                str(self.destination),
                "-BackupRoot",
                str(self.backup_root),
            ],
            capture_output=True,
            text=True,
            cwd=self.home,
            timeout=INSTALL_TIMEOUT,
            env={
                **os.environ,
                "PDH_INSTALL_TEST_CREATE_FOREIGN_TARGET": "product-definition-builder",
            },
        )
        self.assertNotEqual(0, result.returncode)
        sentinel = self.destination / "product-definition-builder" / "keep.txt"
        self.assertEqual("foreign sentinel\n", sentinel.read_text(encoding="utf-8"))
        self.assertFalse((self.destination / "delivery-harness").exists())

    @unittest.skipIf(POWERSHELL is None, "neither pwsh nor powershell is available")
    def test_powershell_marker_failures_restore_and_release_the_lock(self) -> None:
        self.seed_managed_copies()
        command = [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO_ROOT / "install.ps1"),
            "-Destination",
            str(self.destination),
            "-BackupRoot",
            str(self.backup_root),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=self.home,
            timeout=INSTALL_TIMEOUT,
            env={
                **os.environ,
                "PDH_INSTALL_TEST_FAIL_OWNER_MARKER": "product-definition-builder",
            },
        )
        self.assertNotEqual(0, result.returncode)
        self.assert_old_copies_restored()
        self.assertFalse((self.destination / ".pdh-install.lock").exists())

        empty_destination = self.home / "empty-ps-skills"
        result = subprocess.run(
            [
                *command[:7],
                str(empty_destination),
                "-BackupRoot",
                str(self.backup_root),
            ],
            capture_output=True,
            text=True,
            cwd=self.home,
            timeout=INSTALL_TIMEOUT,
            env={**os.environ, "PDH_INSTALL_TEST_FAIL_LOCK_OWNER": "1"},
        )
        self.assertNotEqual(0, result.returncode)
        self.assertFalse((empty_destination / ".pdh-install.lock").exists())


if __name__ == "__main__":
    unittest.main()
