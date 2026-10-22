#!/usr/bin/env python3
"""Deterministic temporary-directory tests for the skill installer."""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
import tempfile
import time
import unittest
import re
import sys
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


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness_contract  # noqa: E402
BASH = find_bash()
# Git Bash starts each helper process slowly (~70 ms per cmp/stat), so one full
# install.sh run takes over a minute on Windows and more on a loaded machine.
# The deadline only bounds a hung installer; it is not a performance check.
INSTALL_TIMEOUT = 600


def is_cache_path(path: Path) -> bool:
    """Match what install.sh leaves out: caches and test suites."""
    return (
        "__pycache__" in path.parts
        or ".pytest_cache" in path.parts
        or path.suffix.lower() in {".pyc", ".pyo"}
        or any(pair == ("scripts", "tests") for pair in zip(path.parts, path.parts[1:]))
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
        if path.is_file() and not is_cache_path(path.relative_to(root))
    }


def installed_manifest(skill: str, destination: Path) -> dict[str, bytes]:
    root = destination / skill
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not is_cache_path(path.relative_to(root))
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
        # Resolve symlinked temp roots (macOS /var -> /private/var); the
        # installers correctly refuse symlinked path components.
        self.home = Path(self._temp.name).resolve()
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
                root = self.destination / skill
                self.assertFalse(
                    any(is_cache_path(path.relative_to(root)) for path in root.rglob("*"))
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
            timeout=INSTALL_TIMEOUT,
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
        target.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                if result.returncode != 0:
                    raise OSError(result.stderr.strip() or result.stdout.strip())
            else:
                os.symlink(target, link, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"directory junction creation is unavailable: {error}")

    def test_bash_installs_complete_manifest_and_migrates_legacy_copies(self) -> None:
        self.destination = self.home / "installed skills"
        self.seed_managed_copies()
        result = self.run_bash(
            {"SKILL_BACKUP_ROOT": str(self.backup_root)}
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assert_full_install()
        for skill in self.SKILLS:
            self.assertFalse(list((self.destination / skill).rglob("tests")), skill)
        self.assertEqual(
            harness_contract.contract_digest(REPO_ROOT / "skills"),
            harness_contract.contract_digest(self.destination),
        )
        target = self.home / "empty target project"
        target.mkdir()
        for skill, script in (
            ("delivery-harness", "check_skill_bindings.py"),
            ("product-definition-builder", "check_product_package.py"),
            ("ui-design-builder", "check_ui_publication.py"),
            ("design-system-compiler", "check_design_system_pair.py"),
            ("product-activation", "check_activation.py"),
            ("seo-growth-review", "check_seo_review.py"),
        ):
            result = subprocess.run([sys.executable, str(self.destination / skill / "scripts" / script), "--help"],
                                    cwd=target, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertFalse((target / "skills").exists())

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

    @unittest.skipIf(BASH is None, "no usable bash is available")
    def test_bash_refuses_ignored_secret_like_source_files(self) -> None:
        source = self.make_minimal_repo()
        (source / ".gitignore").write_text(".env\n.dev.vars\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=source, check=True)
        subprocess.run(["git", "commit", "-qm", "ignore secrets"], cwd=source, check=True)
        (source / "skills" / "delivery-harness" / ".env").write_text(
            "placeholder-only\n", encoding="utf-8"
        )

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

    def assert_source_line_recorded(self, source: Path, install) -> None:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=source, capture_output=True, text=True, check=True
        ).stdout.strip()
        # A clean first install makes no backup, so the line is only printed.
        first = install()
        self.assertEqual(0, first.returncode, first.stderr or first.stdout)
        self.assertIn(f"source commit {head}, uncommitted skills/ changes: no", first.stdout)
        self.assertFalse(self.backup_root.exists() and any(self.backup_root.iterdir()))

        # An uncommitted tracked edit is installed, reported, and recorded
        # next to the backup of the copy it replaced.
        (source / "skills" / "ui-design-builder" / "SKILL.md").write_text(
            "# dirty ui-design-builder\n", encoding="utf-8", newline="\n"
        )
        second = install()
        self.assertEqual(0, second.returncode, second.stderr or second.stdout)
        line = f"source commit {head}, uncommitted skills/ changes: yes"
        self.assertIn(line, second.stdout)
        backups = [child for child in self.backup_root.iterdir() if child.is_dir()]
        self.assertEqual(1, len(backups))
        record = backups[0].with_name(backups[0].name + ".source")
        self.assertEqual(line + "\n", record.read_text(encoding="utf-8"))
        self.assertEqual(
            "# dirty ui-design-builder\n",
            (self.destination / "ui-design-builder" / "SKILL.md").read_text(encoding="utf-8"),
        )

    def assert_planted_receipt_preserved(self, install) -> None:
        # A leftover or planted <stamp>.source must not be overwritten: the
        # backup name skips it and the receipt is created exclusively.
        self.seed_managed_copies()
        self.backup_root.mkdir(parents=True)
        start = datetime.datetime.now()
        planted = []
        for offset in range(-2, 60):
            stamp = (start + datetime.timedelta(seconds=offset)).strftime("%Y%m%d-%H%M%S")
            sidecar = self.backup_root / f"{stamp}.source"
            sidecar.write_text("unrelated\n", encoding="utf-8", newline="\n")
            planted.append(sidecar)
        result = install()
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        for sidecar in planted:
            self.assertEqual("unrelated\n", sidecar.read_text(encoding="utf-8"))
        backups = [child for child in self.backup_root.iterdir() if child.is_dir()]
        self.assertEqual(1, len(backups))
        record = backups[0].with_name(backups[0].name + ".source")
        self.assertIn("source commit", record.read_text(encoding="utf-8"))

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
