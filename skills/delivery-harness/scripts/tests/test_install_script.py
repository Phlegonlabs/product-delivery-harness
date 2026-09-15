#!/usr/bin/env python3
"""Deterministic temporary-directory tests for both skill installers."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import unittest
import re
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / "skills" / "delivery-harness" / "SKILL.md").is_file() and (
            candidate / "package.json"
        ).is_file():
            return candidate
    return None


def find_bash() -> str | None:
    candidates = [
        Path(r"C:\Program Files\Git\bin\bash.exe"),
        Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
    ]
    candidates.extend(
        [Path(path) for path in (shutil.which("bash"),) if path is not None]
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        probe = subprocess.run(
            [str(candidate), "--version"], capture_output=True, timeout=10, check=False
        )
        if probe.returncode == 0:
            return str(candidate)
    return None


def find_powershell() -> str | None:
    for command in ("pwsh", "powershell"):
        path = shutil.which(command)
        if path is None:
            continue
        probe = subprocess.run(
            [path, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.Major"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if probe.returncode == 0:
            return path
    return None


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
BASH = find_bash()
POWERSHELL = find_powershell()


def is_cache_path(path: Path) -> bool:
    return (
        "__pycache__" in path.parts
        or ".pytest_cache" in path.parts
        or path.suffix.lower() in {".pyc", ".pyo"}
    )


def bash_path(path: Path, *, resolve: bool = True) -> str:
    resolved = path.resolve() if resolve else Path(os.path.abspath(path))
    parts = resolved.parts
    try:
        temp_index = len(parts) - 1 - parts[::-1].index("Temp")
        if (
            temp_index >= 3
            and parts[temp_index - 2].casefold() == "appdata"
            and parts[temp_index - 1].casefold() == "local"
        ):
            return "/tmp/" + "/".join(parts[temp_index + 1 :])
    except ValueError:
        pass
    value = resolved.as_posix()
    return re.sub(r"^([A-Za-z]):", lambda match: f"/{match.group(1).lower()}", value)


def source_manifest(skill: str) -> dict[str, bytes]:
    root = REPO_ROOT / "skills" / skill
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not is_cache_path(path)
    }


def installed_manifest(skill: str, destination: Path) -> dict[str, bytes]:
    root = destination / skill
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not is_cache_path(path)
    }


def tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class InstallScriptTests(unittest.TestCase):
    SKILLS = (
        "delivery-harness",
        "product-definition-builder",
        "ui-design-builder",
        "design-system-compiler",
        "code-security-review",
        "product-activation",
        "seo-growth-review",
    )
    LEGACY_SKILLS = ("full-harness", "prd-builder", "product-design-builder")
    MANAGED_SKILLS = SKILLS + LEGACY_SKILLS

    def setUp(self) -> None:
        if REPO_ROOT is None or not (REPO_ROOT / "install.sh").is_file():
            self.skipTest("no repository checkout with install.sh")
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.home = Path(self._temp.name)
        self.destination = self.home / "skills"
        self.backup_root = self.home / "backups"

    def seed_managed_copies(self) -> None:
        self.destination.mkdir(parents=True)
        for skill in self.MANAGED_SKILLS:
            old = self.destination / skill
            old.mkdir()
            (old / "SKILL.md").write_text(
                f"# old {skill}\n", encoding="utf-8", newline="\n"
            )
            (old / "old.txt").write_text(
                f"old data for {skill}\n", encoding="utf-8", newline="\n"
            )
        (self.destination / "unrelated-skill" / "SKILL.md").parent.mkdir(
            parents=True, exist_ok=True
        )
        (self.destination / "unrelated-skill" / "SKILL.md").write_text(
            "# unrelated\n", encoding="utf-8", newline="\n"
        )

    def assert_full_install(self) -> None:
        for skill in self.SKILLS:
            with self.subTest(skill=skill):
                self.assertEqual(source_manifest(skill), installed_manifest(skill, self.destination))
                self.assertFalse(
                    any(is_cache_path(path) for path in (self.destination / skill).rglob("*"))
                )
        for skill in self.LEGACY_SKILLS:
            self.assertFalse((self.destination / skill).exists())
        self.assertTrue((self.destination / "unrelated-skill" / "SKILL.md").is_file())

    def assert_old_copies_restored(self) -> None:
        for skill in self.MANAGED_SKILLS:
            with self.subTest(restored=skill):
                self.assertEqual(
                    f"# old {skill}\n",
                    (self.destination / skill / "SKILL.md").read_text(encoding="utf-8"),
                )
                self.assertEqual(
                    f"old data for {skill}\n",
                    (self.destination / skill / "old.txt").read_text(encoding="utf-8"),
                )
        self.assertTrue((self.destination / "unrelated-skill" / "SKILL.md").is_file())

    def run_bash(
        self,
        extra_env: dict[str, str] | None = None,
        *,
        installer: Path | None = None,
        destination: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if BASH is None:
            self.skipTest("no usable bash is available")
        git_root = Path(BASH).resolve().parents[1]
        env = {
            **os.environ,
            "HOME": bash_path(self.home),
            "PATH": str(git_root / "usr" / "bin") + os.pathsep + os.environ.get("PATH", ""),
            **(extra_env or {}),
        }
        for name, value in list(env.items()):
            if name == "SKILL_BACKUP_ROOT":
                env[name] = bash_path(Path(value), resolve=False)
        return subprocess.run(
            [
                BASH,
                str(installer or (REPO_ROOT / "install.sh")),
                bash_path(destination or self.destination, resolve=False),
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=self.home,
            timeout=120,
        )

    @unittest.skipIf(BASH is None, "no usable bash is available")
    def test_bash_rejects_destination_and_backup_junctions_before_mutation(self) -> None:
        for label in ("destination", "backup"):
            with self.subTest(label=label):
                protected = self.home / f"bash-protected-{label}"
                protected.mkdir()
                sentinel = protected / "keep.txt"
                sentinel.write_text("preserve\n", encoding="utf-8")
                alias = self.home / f"bash-{label}-junction"
                self.make_junction(alias, protected)
                destination = alias if label == "destination" else self.home / "bash-skills"
                backup = alias if label == "backup" else self.home / "bash-backups"
                result = self.run_bash(
                    {"SKILL_BACKUP_ROOT": str(backup)},
                    destination=destination,
                )
                self.assertNotEqual(0, result.returncode)
                self.assertIn(
                    "symlink/reparse path component is forbidden",
                    result.stderr + result.stdout,
                )
                self.assertEqual("preserve\n", sentinel.read_text(encoding="utf-8"))
                self.assertFalse((protected / ".pdh-install.lock").exists())

    @unittest.skipIf(BASH is None, "no usable bash is available")
    def test_bash_rejects_tracked_symlink_mode_before_mutation(self) -> None:
        source = self.make_minimal_repo()
        relative = "skills/delivery-harness/tracked-link"
        working_file = source / relative
        working_file.write_text("ordinary working-tree bytes\n", encoding="utf-8")
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
        result = self.run_bash(
            {"SKILL_BACKUP_ROOT": str(self.backup_root)},
            installer=source / "install.sh",
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            f"non-regular tracked source entry is not installable: mode=120000 path={relative}",
            result.stderr + result.stdout,
        )
        self.assertFalse(self.destination.exists())

    def make_minimal_repo(self) -> Path:
        source = self.home / "minimal-source"
        source.mkdir()
        shutil.copy2(REPO_ROOT / "install.sh", source / "install.sh")
        shutil.copy2(REPO_ROOT / "install.ps1", source / "install.ps1")
        for skill in self.SKILLS:
            skill_dir = source / "skills" / skill
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"# {skill}\n", encoding="utf-8", newline="\n"
            )
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=source, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=source, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Installer Test"], cwd=source, check=True
        )
        subprocess.run(["git", "add", "."], cwd=source, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=source, check=True)
        return source

    def make_junction(self, link: Path, target: Path) -> None:
        if POWERSHELL is None:
            self.skipTest("PowerShell is unavailable")
        target.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                POWERSHELL,
                "-NoProfile",
                "-Command",
                (
                    "New-Item -ItemType Junction -Path $env:PDH_TEST_JUNCTION "
                    "-Target $env:PDH_TEST_JUNCTION_TARGET "
                    "-ErrorAction Stop | Out-Null"
                ),
            ],
            capture_output=True,
            text=True,
            cwd=self.home,
            timeout=30,
            env={
                **os.environ,
                "PDH_TEST_JUNCTION": str(link),
                "PDH_TEST_JUNCTION_TARGET": str(target),
            },
        )
        if result.returncode != 0 or not link.exists():
            self.skipTest(
                "directory junction creation is unavailable: "
                + (result.stderr.strip() or result.stdout.strip())
            )

    def test_bash_installs_complete_manifest_and_migrates_legacy_copies(self) -> None:
        self.seed_managed_copies()
        result = self.run_bash(
            {"SKILL_BACKUP_ROOT": str(self.backup_root)}
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assert_full_install()

        backups = [child for child in self.backup_root.iterdir() if child.is_dir()]
        self.assertEqual(1, len(backups))
        self.assertEqual(
            set(self.MANAGED_SKILLS),
            {child.name for child in backups[0].iterdir()},
        )
        for skill in self.MANAGED_SKILLS:
            self.assertEqual(
                f"# old {skill}\n",
                (backups[0] / skill / "SKILL.md").read_text(encoding="utf-8"),
            )

    def test_bash_detects_non_skill_corruption_before_mutating_destination(self) -> None:
        self.seed_managed_copies()
        before = tree_snapshot(self.destination)
        result = self.run_bash(
            {
                "SKILL_BACKUP_ROOT": str(self.backup_root),
                "PDH_INSTALL_TEST_CORRUPT_STAGE": "delivery-harness/references/runtime-upgrades.md",
            }
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "delivery-harness file does not byte-match: references/runtime-upgrades.md",
            result.stderr,
        )
        self.assertEqual(before, tree_snapshot(self.destination))
        if self.backup_root.exists():
            self.assertEqual([], list(self.backup_root.iterdir()))

    def test_bash_mid_install_failure_restores_backup(self) -> None:
        self.seed_managed_copies()
        result = self.run_bash(
            {
                "SKILL_BACKUP_ROOT": str(self.backup_root),
                "PDH_INSTALL_FAIL_AFTER": "delivery-harness",
            }
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("induced failure after installing delivery-harness", result.stderr)
        self.assert_old_copies_restored()
        self.assertEqual([], list(self.backup_root.iterdir()))
        self.assertFalse(
            any(path.name.startswith(".pdh-install-stage-") for path in self.destination.iterdir())
        )

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
            timeout=120,
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
        deadline = time.monotonic() + 10
        while not lock.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(lock.exists(), "first installer never acquired the lock")
        second = self.run_bash({"SKILL_BACKUP_ROOT": str(self.backup_root)})
        first_stdout, first_stderr = first.communicate(timeout=120)
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
                timeout=120,
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
                timeout=120,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("untracked or ignored source artifact is not installable", result.stderr + result.stdout)

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
            timeout=180,
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
            timeout=180,
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
            cwd=self.home, timeout=180,
            env={**os.environ, "PDH_INSTALL_FAIL_AFTER": "delivery-harness"},
        )
        self.assertNotEqual(0, failed.returncode, failed.stderr or failed.stdout)
        self.assert_old_copies_restored()

        succeeded = subprocess.run(
            [POWERSHELL, *common], capture_output=True, text=True,
            cwd=self.home, timeout=180,
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
                    timeout=180,
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
            timeout=180,
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
            timeout=180,
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
            timeout=180,
            env={**os.environ, "PDH_INSTALL_TEST_FAIL_LOCK_OWNER": "1"},
        )
        self.assertNotEqual(0, result.returncode)
        self.assertFalse((empty_destination / ".pdh-install.lock").exists())


if __name__ == "__main__":
    unittest.main()
