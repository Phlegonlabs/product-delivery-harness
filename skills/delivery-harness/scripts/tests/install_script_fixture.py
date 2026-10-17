"""Shared fixtures and base case for the installer tests in this package."""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
import tempfile
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
        # A cold pwsh start on CI runners can exceed 10 s; a probe timeout
        # must not break importing the whole module.
        try:
            probe = subprocess.run(
                [path, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.Major"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired:
            continue
        if probe.returncode == 0:
            return path
    return None


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
BASH = find_bash()
POWERSHELL = find_powershell()
# Git Bash starts each helper process slowly (~70 ms per cmp/stat), so one full
# install.sh run takes over a minute on Windows and more on a loaded machine.
# The deadline only bounds a hung installer; it is not a performance check.
INSTALL_TIMEOUT = 600


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


class InstallScriptCase(unittest.TestCase):
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
            timeout=INSTALL_TIMEOUT,
        )

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
