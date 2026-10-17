#!/usr/bin/env python3
"""Deterministic temporary-directory tests for both skill installers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import re
from pathlib import Path

from install_script_fixture import (
    BASH,
    REPO_ROOT,
    InstallScriptCase,
    tree_snapshot,
)


class InstallScriptTests(InstallScriptCase):
    @unittest.skipUnless(shutil.which("pwsh"), "pwsh is required for the GitHub shell")
    def test_ci_dependency_negative_check_exits_successfully(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/harness-ci.yml").read_text(
            encoding="utf-8"
        )
        step = workflow.split(
            "- name: Verify PowerShell installer syntax and dependency check route", 1
        )[1].split("run: |-", 1)[1]
        lines = []
        for line in step.splitlines()[1:]:
            if line.strip() and not line.startswith("          "):
                break
            lines.append(line[10:])
        # GitHub appends this native-command exit check to PowerShell scripts.
        script = "\n".join(lines) + (
            "\nif (Test-Path variable:\\LASTEXITCODE) { exit $LASTEXITCODE }\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            script_path = Path(temporary) / "ci-check.ps1"
            script_path.write_text(script, encoding="utf-8")
            result = subprocess.run(
                [shutil.which("pwsh"), "-NoProfile", "-File", str(script_path)],
                cwd=REPO_ROOT,
                env={**os.environ, "RUNNER_TEMP": temporary},
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ci_runs_installer_and_python_suites_on_windows(self) -> None:
        # The harness suite includes these installer tests, so Windows CI
        # covers install.ps1 parsing and the native dependency-check route.
        workflow = (REPO_ROOT / ".github/workflows/harness-ci.yml").read_text(
            encoding="utf-8"
        )
        harness = workflow.split("\n  windows-native:\n", 1)[1].split("\n  windows-other:\n", 1)[0]
        other = workflow.split("\n  windows-other:\n", 1)[1].split("\n  windows-installer:\n", 1)[0]
        for job in (harness, other):
            self.assertIn("runs-on: windows-latest", job)
            # Windows is the owner's platform, so its jobs block like the others.
            self.assertNotIn("continue-on-error", job)
            # The checked-out SHA must be verified natively before any step runs.
            self.assertIn('-ne $env:CANDIDATE_SHA', job)
        # The long Harness suite is measured and sharded; installer tests stay
        # in the discovered files and therefore retain Windows native coverage.
        # Workflow expands the index from the matrix, so assert the matrix and
        # its templated use rather than literal copies of one command.
        matrix = re.search(r"^\s*shard:\s*\[([^]]+)\]", harness, re.MULTILINE)
        self.assertIsNotNone(matrix)
        self.assertEqual(
            ["0", "1", "2", "3", "4", "5", "6", "7"],
            [item.strip() for item in matrix.group(1).split(",")],
        )
        self.assertIn("--platform windows --shard-count 8", harness)
        self.assertIn("--shard-index '${{ matrix.shard }}'", harness)
        self.assertIn("name: windows-native-${{ matrix.shard }}", harness)
        for skill in (
            "product-definition-builder",
            "ui-design-builder",
            "design-system-compiler",
            "product-activation",
            "seo-growth-review",
        ):
            self.assertIn(f"unittest discover -s skills/{skill}/scripts/tests -v", other)
        self.assertNotIn("PDH_REQUIRE_BROWSER_TESTS", other)

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

    def test_bash_installs_complete_manifest_and_migrates_legacy_copies(self) -> None:
        self.destination = self.home / "installed skills"
        self.seed_managed_copies()
        result = self.run_bash(
            {"SKILL_BACKUP_ROOT": str(self.backup_root)}
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assert_full_install()
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


if __name__ == "__main__":
    unittest.main()
