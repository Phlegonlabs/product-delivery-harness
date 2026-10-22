#!/usr/bin/env python3
"""Focused tests for the main-based PLAN policy and release-source marker."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from branch_policy import (  # noqa: E402
    archive_ancestry_base,
    validate_branch_policy_ancestry,
    validate_branch_policy_join,
    validate_branch_policy_shape,
)
from manifest_fixtures import valid_plan, valid_run  # noqa: E402
from harness_manifest import validate_run  # noqa: E402


ARCHITECTURE = "# Architecture\n\n## Release Targets\n\n" + "Release source policy: main-preview/1" + "\n"


def branch_policy(kind: str = "ordinary", base_sha: str = "a" * 40) -> dict[str, str]:
    return {
        "protocol": "main-preview/1",
        "kind": kind,
        "base_ref": "refs/remotes/origin/main",
        "base_sha": base_sha,
    }


def run_at(version: str) -> dict[str, object]:
    plan = valid_plan()
    run = valid_run(plan)
    gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]
    gate["required_harness_version"] = version
    return run


class BranchPolicyTests(unittest.TestCase):
    def test_plan_only_explicit_policy_and_marker_are_validated_together(self):
        plan = {"branch_policy": branch_policy()}
        self.assertEqual([], validate_branch_policy_join(plan, ARCHITECTURE, "."))
        self.assertEqual([], validate_branch_policy_join({}, "# Architecture\n", "."))
        cases = (
            (plan, "# Architecture\n", "require an active"),
            ({}, ARCHITECTURE, "requires a branch policy object"),
            ({"branch_policy": branch_policy("ordinary") | {"base_ref": "refs/remotes/origin/development"}},
             ARCHITECTURE, "must name refs/remotes/<remote>/main"),
            (plan, ARCHITECTURE + "Release source policy: main-preview/1" + "\n", "at most one active"),
            (plan, ARCHITECTURE.replace("main-preview/1", "main-preview/2"), "only supported"),
        )
        for candidate, architecture, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, "\n".join(validate_branch_policy_join(candidate, architecture, ".")))

    def test_archive_candidate_keeps_its_frozen_main_base_after_main_moves(self):
        from archive_run import _live_head_problems
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*arguments):
                return subprocess.check_output(["git", *arguments], cwd=root, text=True).strip()
            git("init", "-q", "-b", "main")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "Archive Base Test")
            git("commit", "--allow-empty", "-qm", "original main")
            base = git("rev-parse", "HEAD")
            git("checkout", "-q", "-b", "codex/candidate")
            git("commit", "--allow-empty", "-qm", "ordinary candidate")
            candidate = git("rev-parse", "HEAD")
            git("checkout", "-q", "main")
            git("commit", "--allow-empty", "-qm", "later main change")
            main = git("rev-parse", "HEAD")
            git("checkout", "-q", "codex/candidate")
            run = run_at("0.63.0")
            run["integration"].update(branch="codex/candidate", integration_head_sha=candidate)
            plan = {"branch_policy": branch_policy(base_sha=base)}
            self.assertEqual([], _live_head_problems(run, root, main, "refs/heads/main", [], plan))
            self.assertTrue(_live_head_problems(run, root, base, "refs/heads/main", [], plan))
            self.assertTrue(_live_head_problems(run, root, main, "refs/heads/main", [],
                {"branch_policy": branch_policy(base_sha=main)}))
            run["runtime_capabilities"]["runtime_adapter"]["version_gate"]["required_harness_version"] = "0.58.0"
            self.assertTrue(_live_head_problems(run, root, main, "refs/heads/main", [], plan))

    def test_archive_uses_frozen_base_and_keeps_legacy_main_rule(self):
        plan = {"branch_policy": branch_policy(base_sha="b" * 40)}
        self.assertEqual("b" * 40, archive_ancestry_base(plan, run_at("0.63.0"), "c" * 40))
        self.assertEqual("c" * 40, archive_ancestry_base(plan, run_at("0.58.0"), "c" * 40))
        from harness_core import ManifestError
        with self.assertRaises(ManifestError):
            archive_ancestry_base(None, run_at("0.63.0"), "c" * 40)

    def test_valid_historical_pins_do_not_require_policy_or_marker(self) -> None:
        plan = valid_plan()
        with tempfile.TemporaryDirectory() as directory:
            for version in ("0.58.0", "0.59.0", "0.62.3", "0.6.0"):
                run = valid_run(plan)
                gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]
                if version is None:
                    gate.pop("required_harness_version")
                else:
                    gate["required_harness_version"] = version
                self.assertEqual(
                    [],
                    validate_branch_policy_join(plan, "# Architecture\n", directory, run=run),
                )

    def test_current_join_requires_exact_shape_and_marker(self) -> None:
        plan = valid_plan()
        errors = validate_branch_policy_join(
            plan,
            "# Architecture\n",
            ".",
            run=run_at("0.63.0"),
        )
        self.assertTrue(any("active 'Release source policy: main-preview/1'" in item for item in errors), errors)
        self.assertTrue(any("requires a branch policy object" in item for item in errors), errors)

        plan["branch_policy"] = branch_policy("ordinary", "b" * 40)
        plan["branch_policy"]["base_ref"] = "refs/remotes/origin/development"
        errors = validate_branch_policy_join(
            plan, ARCHITECTURE, ".", run=run_at("0.63.0")
        )
        self.assertTrue(any("must name refs/remotes/<remote>/main" in item for item in errors), errors)

        for invalid in (
            {"protocol": "main-preview/2", "kind": "ordinary", "base_ref": "refs/remotes/origin/main", "base_sha": "a" * 40},
            {"protocol": "main-preview/1", "kind": "release", "base_ref": "refs/remotes/origin/main", "base_sha": "a" * 40},
            {"protocol": "main-preview/1", "kind": "ordinary", "base_ref": "refs/heads/main", "base_sha": "a" * 40},
            {"protocol": "main-preview/1", "kind": "ordinary", "base_ref": "refs/remotes/origin/development", "base_sha": "a" * 40},
            {"protocol": "main-preview/1", "kind": "ordinary", "base_ref": "refs/remotes/origin/main", "base_sha": "abc"},
            {"protocol": "main-preview/1", "kind": ["ordinary"], "base_ref": "refs/remotes/origin/main", "base_sha": "a" * 40},
            {"protocol": "main-preview/1", "kind": None, "base_ref": "refs/remotes/origin/main", "base_sha": "a" * 40},
            {"protocol": ["main-preview/1"], "kind": "ordinary", "base_ref": "refs/remotes/origin/main", "base_sha": "a" * 40},
        ):
            with self.subTest(policy=invalid):
                errors = validate_branch_policy_shape({"branch_policy": invalid})
                self.assertTrue(errors)

    def test_current_join_proves_local_frozen_base_ancestry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", "-b", "feature"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Branch Test"], cwd=root, check=True)
            (root / "base.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "base.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            (root / "candidate.txt").write_text("candidate\n", encoding="utf-8")
            subprocess.run(["git", "add", "candidate.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "candidate"], cwd=root, check=True)
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            subprocess.run(["git", "update-ref", "refs/remotes/origin/main", base], cwd=root, check=True)

            plan = valid_plan()
            plan["branch_policy"] = branch_policy(base_sha=base)
            run = run_at("0.63.0")
            run["integration"]["batch_base_sha"] = head
            run["integration"]["integration_head_sha"] = head
            self.assertEqual(
                [], validate_branch_policy_join(plan, ARCHITECTURE, root, run=run)
            )

            stale = branch_policy(base_sha="c" * 40)
            errors = validate_branch_policy_ancestry(
                {"branch_policy": stale}, root, run=run
            )
            self.assertTrue(any("is not an ancestor" in item for item in errors), errors)

            # A later wave may advance the integration head, but the frozen
            # PLAN base remains the original commit.
            run["integration"]["batch_base_sha"] = base
            self.assertEqual(
                [], validate_branch_policy_ancestry(plan, root, run=run)
            )

    def test_prior_archive_correction_still_binds_policy_and_marker(self) -> None:
        plan = valid_plan()
        source = {
            "id": "SRC-PRIOR-A",
            "kind": "prior archive candidate",
            "location": "archive/RUN/ARCHIVE_RECEIPT.json",
            "owner": "parent",
            "status": "frozen",
            "content_sha256": "f" * 64,
            "source_revision": "d" * 40,
            "staged_revision": None,
            "notes": "exact failed archive candidate",
        }
        plan["sources"].append(source)
        errors = validate_branch_policy_join(plan, "# Architecture\n", ".", run=run_at("0.63.0"))
        self.assertTrue(any("require an active" in item for item in errors), errors)
        self.assertTrue(any("requires a branch policy object" in item for item in errors), errors)

        source["source_revision"] = "not-a-sha"
        errors = validate_branch_policy_join(plan, "# Architecture\n", ".", run=run_at("0.63.0"))
        self.assertTrue(any("active 'Release source policy" in item for item in errors), errors)

    def test_marker_counts_and_version_compatibility_fail_closed(self) -> None:
        current = run_at("0.63.0")
        duplicate = ARCHITECTURE + "Release source policy: main-preview/1" + "\n"
        errors = validate_branch_policy_join(
            valid_plan(), duplicate, ".", run=current
        )
        self.assertTrue(any("at most one active" in item for item in errors), errors)

        unknown = ARCHITECTURE.replace(
            "Release source policy: main-preview/1", "Release source policy: main-preview/2"
        )
        errors = validate_branch_policy_join(
            valid_plan(), unknown, ".", run=current
        )
        self.assertTrue(any("only supported" in item for item in errors), errors)

        old = valid_run(valid_plan())
        gate = old["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        gate["required_harness_version"] = "0.58.0"
        errors = validate_branch_policy_join(
            valid_plan(), ARCHITECTURE, ".", run=old
        )
        self.assertEqual([], errors)

    def test_current_run_validation_requires_policy_without_repo_root(self) -> None:
        plan = valid_plan()
        run = run_at("0.63.0")
        errors = validate_run(plan, run)
        self.assertTrue(
            any("requires a branch policy object" in item for item in errors),
            errors,
        )
        plan["branch_policy"] = branch_policy()
        self.assertFalse(
            any("branch_policy" in item for item in validate_run(plan, run))
        )


if __name__ == "__main__":
    unittest.main()
