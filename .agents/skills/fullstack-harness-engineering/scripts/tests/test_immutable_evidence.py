from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import plan_digest, validate_current_plan_run  # noqa: E402
from test_graph_orchestration import valid_graph_plan, valid_graph_run  # noqa: E402


class CurrentPlanSourceBindingTests(unittest.TestCase):
    @staticmethod
    def refresh_digest(plan: dict[str, object], run: dict[str, object]) -> None:
        run["plan"]["digest_sha256"] = plan_digest(plan)

    @staticmethod
    def write_sources(root: Path, *, prd: bytes = b"prd\n", architecture: bytes = b"arch\n") -> None:
        for relative, contents in (
            ("docs/product/prd.md", prd),
            ("docs/product/architecture.md", architecture),
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)

    def bound_plan_and_run(self) -> tuple[dict[str, object], dict[str, object]]:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        return plan, run

    def bind_hashes(self, plan: dict[str, object], *, prd: bytes, architecture: bytes) -> None:
        plan["sources"][0]["content_sha256"] = hashlib.sha256(prd).hexdigest()
        plan["sources"][1]["content_sha256"] = hashlib.sha256(architecture).hexdigest()

    def test_current_validation_without_repo_root_remains_shape_only(self) -> None:
        plan, run = self.bound_plan_and_run()
        self.assertEqual([], validate_current_plan_run(plan, run))

    def test_current_validation_binds_local_source_bytes_to_repo_root(self) -> None:
        prd = b"frozen prd\n"
        architecture = b"frozen architecture\n"
        plan, run = self.bound_plan_and_run()
        self.bind_hashes(plan, prd=prd, architecture=architecture)
        self.refresh_digest(plan, run)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_sources(root, prd=prd, architecture=architecture)
            self.assertEqual([], validate_current_plan_run(plan, run, repo_root=root))

    def test_current_validation_reports_missing_escaped_and_mismatched_sources(self) -> None:
        prd = b"frozen prd\n"
        architecture = b"frozen architecture\n"
        plan, run = self.bound_plan_and_run()
        self.bind_hashes(plan, prd=prd, architecture=architecture)
        self.refresh_digest(plan, run)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_sources(root, prd=prd, architecture=architecture)

            missing = root / "docs/product/architecture.md"
            missing.unlink()
            errors = validate_current_plan_run(plan, run, repo_root=root)
            self.assertTrue(any("does not exist" in error for error in errors), errors)

            self.write_sources(root, prd=prd, architecture=architecture)
            plan["sources"][0]["location"] = "../outside.md"
            errors = validate_current_plan_run(plan, run, repo_root=root)
            self.assertTrue(any("outside --repo-root" in error for error in errors), errors)

            plan["sources"][0]["location"] = "docs/product/prd.md"
            (root / "docs/product/prd.md").write_bytes(b"changed\n")
            errors = validate_current_plan_run(plan, run, repo_root=root)
            self.assertTrue(any("does not match immutable bytes" in error for error in errors), errors)

    def test_source_revision_reads_committed_bytes_not_working_tree(self) -> None:
        committed = b"committed prd\n"
        architecture = b"frozen architecture\n"
        plan, run = self.bound_plan_and_run()
        self.bind_hashes(plan, prd=committed, architecture=architecture)
        self.refresh_digest(plan, run)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_sources(root, prd=committed, architecture=architecture)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Harness Test"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "harness@example.invalid"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "add", "docs"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "freeze sources"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            plan["sources"][0]["source_revision"] = revision
            self.refresh_digest(plan, run)

            (root / "docs/product/prd.md").write_bytes(b"mutated working tree\n")
            self.assertEqual([], validate_current_plan_run(plan, run, repo_root=root))

    def test_external_sources_are_not_fetched_without_an_immutable_revision(self) -> None:
        plan, run = self.bound_plan_and_run()
        plan["sources"][0]["location"] = "https://example.invalid/prd.md"
        self.refresh_digest(plan, run)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_sources(root)
            errors = validate_current_plan_run(plan, run, repo_root=root)

        self.assertTrue(any("external source is not fetched" in error for error in errors), errors)

    def test_external_source_revision_is_accepted_without_network_access(self) -> None:
        plan, run = self.bound_plan_and_run()
        plan["sources"][0]["location"] = "https://example.invalid/prd.md"
        plan["sources"][0]["content_sha256"] = None
        plan["sources"][0]["source_revision"] = "published-revision-1"
        architecture = b"arch\n"
        plan["sources"][1]["content_sha256"] = hashlib.sha256(architecture).hexdigest()
        self.refresh_digest(plan, run)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_sources(root, architecture=architecture)
            self.assertEqual([], validate_current_plan_run(plan, run, repo_root=root))


if __name__ == "__main__":
    unittest.main()
