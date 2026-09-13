#!/usr/bin/env python3
"""Tests for the read-only external skill dependency checker."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
REPO_ROOT = SCRIPTS_DIR.parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_external_skill_dependencies as checker  # noqa: E402


class ExternalSkillDependencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.skills = self.root / "skills"
        for name in ("frontend-design", "impeccable"):
            skill_dir = self.skills / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"# {name}\n", encoding="utf-8", newline="\n"
            )
            (skill_dir / "reference.md").write_text(
                f"# {name} behavior\n", encoding="utf-8", newline="\n"
            )
        self.bundled = self.root / "bundled-skills"
        self.manifest_path = self.root / "dependencies.json"
        self.manifest = {
            "version": 2,
            "profiles": {
                "ui_design": {
                    "skills": [dependency("frontend-design", self.skills)]
                },
                "frontend_implementation": {
                    "skills": [dependency("frontend-design", self.skills)]
                },
                "authorized_ui_quality": {
                    "skills": [dependency("impeccable", self.skills)]
                },
            },
        }
        self.write_manifest()

    def tearDown(self) -> None:
        self._temp.cleanup()

    def write_manifest(self) -> None:
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2) + "\n", encoding="utf-8"
        )

    def test_all_present_and_unchanged_dependencies_pass_without_writes(self) -> None:
        before = {
            path.relative_to(self.root): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.root.rglob("*")
            if path.is_file()
        }
        findings = checker.check_dependencies(
            self.manifest,
            list(checker.REQUIRED_PROFILES),
            [self.skills],
            self.bundled,
        )
        self.assertEqual([], findings)
        after = {
            path.relative_to(self.root): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_missing_dependency_fails(self) -> None:
        (self.skills / "impeccable" / "SKILL.md").unlink()
        findings = checker.check_dependencies(
            self.manifest, ["authorized_ui_quality"], [self.skills], self.bundled
        )
        joined = "\n".join(findings)
        self.assertIn("required skill 'impeccable' is missing", joined)

    def test_drifted_dependency_fails(self) -> None:
        (self.skills / "frontend-design" / "SKILL.md").write_text(
            "# changed frontend\n", encoding="utf-8", newline="\n"
        )
        findings = checker.check_dependencies(
            self.manifest,
            ["ui_design", "frontend_implementation"],
            [self.skills],
            self.bundled,
        )
        joined = "\n".join(findings)
        self.assertEqual(2, joined.count("hash drifted"))

    def test_referenced_file_drift_changes_the_full_tree_pin(self) -> None:
        (self.skills / "impeccable" / "reference.md").write_text(
            "# changed behavior\n", encoding="utf-8"
        )
        findings = checker.check_dependencies(
            self.manifest, ["authorized_ui_quality"], [self.skills], self.bundled
        )
        self.assertTrue(any("hash drifted" in finding for finding in findings))

    def test_external_source_cannot_resolve_from_the_bundled_root(self) -> None:
        bundled_skill = self.bundled / "frontend-design"
        bundled_skill.mkdir(parents=True)
        (bundled_skill / "SKILL.md").write_text(
            "# local impostor\n", encoding="utf-8"
        )
        manifest = {
            **self.manifest,
            "profiles": {
                **self.manifest["profiles"],
                "ui_design": {
                    "skills": [dependency("frontend-design", self.bundled)]
                },
                "frontend_implementation": {
                    "skills": [dependency("frontend-design", self.bundled)]
                },
            },
        }
        findings = checker.check_dependencies(
            manifest,
            ["ui_design", "frontend_implementation"],
            [self.bundled],
            self.bundled,
        )
        self.assertEqual(2, sum("is missing" in finding for finding in findings))

    def test_profiles_cannot_swap_incompatible_skills(self) -> None:
        swapped = json.loads(json.dumps(self.manifest))
        swapped["profiles"]["ui_design"]["skills"], swapped["profiles"][
            "authorized_ui_quality"
        ]["skills"] = (
            swapped["profiles"]["authorized_ui_quality"]["skills"],
            swapped["profiles"]["ui_design"]["skills"],
        )
        findings = checker.validate_manifest(swapped)
        self.assertEqual(2, sum("must bind exactly" in item for item in findings))

    def test_manifest_records_real_capabilities_and_template_stays_unresolved(self) -> None:
        manifest_path = (
            REPO_ROOT
            / "skills"
            / "delivery-harness"
            / "assets"
            / "external-skill-dependencies.json"
        )
        template_path = (
            REPO_ROOT
            / "skills"
            / "delivery-harness"
            / "assets"
            / "templates"
            / "PROJECT_AGENTS.template.md"
        )
        manifest = checker.load_manifest(manifest_path)
        self.assertEqual([], checker.validate_manifest(manifest))
        template = template_path.read_text(encoding="utf-8")
        self.assertIn("intentionally unresolved", template)
        self.assertIn("not a Harness read-only reviewer", template)
        self.assertEqual(
            checker.REQUIRED_COMPATIBILITY["impeccable"],
            manifest["profiles"]["authorized_ui_quality"]["skills"][0]["compatibility"],
        )

    def test_cli_reports_missing_dependency_without_installing(self) -> None:
        (self.skills / "impeccable").rename(self.root / "saved-impeccable")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = checker.main(
                [
                    "--manifest",
                    str(self.manifest_path),
                    "--profile",
                    "authorized_ui_quality",
                    "--skill-dir",
                    str(self.skills),
                ]
            )
        self.assertEqual(1, status)
        self.assertIn("required skill 'impeccable' is missing", output.getvalue())
        self.assertFalse((self.skills / "impeccable").exists())


def dependency(name: str, skills: Path) -> dict[str, object]:
    path = skills / name
    return {
        "name": name,
        "source": "external",
        "sha256": checker.hash_skill(path),
        "compatibility": checker.REQUIRED_COMPATIBILITY[name],
    }


if __name__ == "__main__":
    unittest.main()
