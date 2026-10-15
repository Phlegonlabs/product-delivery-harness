"""Main-based Preview routing and pinned historical compatibility."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from branch_policy import (  # noqa: E402
    archive_ancestry_base,
    validate_branch_policy_join,
    validate_branch_policy_shape,
)
from harness_core import ManifestError  # noqa: E402
from harness_manifest import validate_run  # noqa: E402
from test_branch_policy import branch_policy, run_at  # noqa: E402


def preview_policy(kind="ordinary", base_sha="a" * 40):
    return branch_policy(kind, base_sha) | {
        "protocol": "main-preview/1", "base_ref": "refs/remotes/origin/main"
    }


def architecture(protocol="main-preview/1"):
    return "# Architecture\n\n## Release Targets\n\nRelease source policy: " + protocol + "\n"


class MainPreviewTests(unittest.TestCase):
    def test_both_kinds_use_main_and_require_current_protocol(self):
        for kind in ("ordinary", "hotfix"):
            plan = {"branch_policy": preview_policy(kind)}
            self.assertEqual([], validate_branch_policy_shape(plan, run=run_at("0.63.0")))
            self.assertEqual([], validate_branch_policy_join(plan, architecture(), "."))
            invalid = deepcopy(plan)
            invalid["branch_policy"]["base_ref"] = "refs/remotes/origin/development"
            self.assertTrue(validate_branch_policy_shape(invalid))
            for version in ("0.58.0", "0.59.0", "0.62.3", "broken", None):
                with self.subTest(kind=kind, version=version):
                    self.assertTrue(validate_branch_policy_shape(plan, run=run_at(version)))

    def test_pinned_dual_branch_contract_remains_valid_without_downgrade(self):
        for version in ("0.59.0", "0.62.3"):
            for kind in ("ordinary", "hotfix"):
                self.assertEqual([], validate_branch_policy_shape(
                    {"branch_policy": branch_policy(kind)}, run=run_at(version)))
        for kind in ("ordinary", "hotfix"):
            plan = {"branch_policy": branch_policy(kind)}
            self.assertTrue(validate_branch_policy_shape(plan, run=run_at("0.63.0")))
            with self.assertRaises(ManifestError):
                archive_ancestry_base(plan, run_at("0.63.0"), "b" * 40)

    def test_invalid_pins_fail_in_join_manifest_and_archive_without_repo(self):
        from manifest_fixtures import valid_plan
        for version in (None, "broken"):
            run = run_at(version)
            plan = valid_plan()
            plan["branch_policy"] = preview_policy()
            self.assertTrue(validate_branch_policy_join(plan, architecture(), ".", run=run))
            self.assertTrue(any("version pin" in item for item in validate_run(plan, run)))
            with self.assertRaises(ManifestError):
                archive_ancestry_base(plan, run, "b" * 40)

    def test_current_run_rejects_dual_policy_without_repository_join(self):
        from manifest_fixtures import valid_plan
        plan = valid_plan()
        plan["branch_policy"] = branch_policy()
        errors = validate_run(plan, run_at("0.63.0"))
        self.assertTrue(any("0.63+ requires" in item for item in errors), errors)

    def test_historical_schema_without_modern_version_gate_keeps_its_base(self):
        run = {"schema_version": 6}
        self.assertEqual("b" * 40, archive_ancestry_base(None, run, "b" * 40))
        self.assertEqual([], validate_branch_policy_join({}, "# Architecture\n", ".", run=run))

    def test_markers_must_match_and_remain_unique(self):
        plan = {"branch_policy": preview_policy()}
        for text in ("# Architecture\n", architecture("dual-branch/1"),
                     architecture() + "Release source policy: main-preview/1\n",
                     architecture() + "Release source policy: dual-branch/1\n",
                     architecture("main-preview/2")):
            self.assertTrue(validate_branch_policy_join(plan, text, "."), text)
        for ref in ("refs/heads/main", "origin/main", "refs/remotes/origin/MAIN"):
            self.assertTrue(validate_branch_policy_shape({
                "branch_policy": preview_policy() | {"base_ref": ref}}))
        for value in ([], None, "candidate/1"):
            self.assertTrue(validate_branch_policy_shape({
                "branch_policy": preview_policy() | {"protocol": value}}))

    def test_frozen_main_ancestry_survives_later_main_movement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*arguments):
                return subprocess.check_output(["git", *arguments], cwd=root, text=True).strip()
            git("init", "-q", "-b", "main")
            git("config", "user.email", "preview@example.invalid")
            git("config", "user.name", "Preview Test")
            git("commit", "--allow-empty", "-qm", "base")
            base = git("rev-parse", "HEAD")
            git("checkout", "-qb", "feature")
            git("commit", "--allow-empty", "-qm", "candidate")
            candidate = git("rev-parse", "HEAD")
            git("checkout", "-q", "main")
            git("commit", "--allow-empty", "-qm", "other work")
            moved = git("rev-parse", "HEAD")
            plan = {"branch_policy": preview_policy(base_sha=base)}
            run = run_at("0.63.0")
            run["integration"].update(integration_head_sha=candidate, batch_base_sha=candidate)
            self.assertEqual([], validate_branch_policy_join(plan, architecture(), root, run=run))
            self.assertEqual(base, archive_ancestry_base(plan, run, moved))
            plan["branch_policy"]["base_sha"] = moved
            self.assertTrue(validate_branch_policy_join(plan, architecture(), root, run=run))


if __name__ == "__main__":
    unittest.main()
