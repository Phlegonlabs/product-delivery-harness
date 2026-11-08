"""The frozen package join checks the approved feature files like the checker's own CLI."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
PDB_TESTS_DIR = Path(__file__).resolve().parents[3] / "product-definition-builder" / "scripts" / "tests"
for candidate in (SCRIPTS_DIR, PDB_TESTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from harness_contract_join import full_product_package_checker_errors  # noqa: E402
import test_product_package_checker as checker_tests  # noqa: E402
from test_product_package_checker import (  # noqa: E402
    bdd_stack,
    bind_features,
    release_architecture,
    strictize_approved_package,
    valid_prd,
    valid_stack,
)

while str(PDB_TESTS_DIR) in sys.path:
    sys.path.remove(str(PDB_TESTS_DIR))

FEATURE = checker_tests.FeaturesFlagTests.FEATURE
POINTER = "Scenarios for these rows live in `docs/product/features/product.feature`.\n"
LAST_ROW = "| TEST-003 | Deny untrusted fixture input before any write |"
STALE = ["prd approval: Feature files digest does not match the approved feature files"]


def prd_with_pointer() -> str:
    prd = valid_prd()
    row_end = prd.index("\n", prd.index(LAST_ROW)) + 1
    return prd[:row_end] + "\n" + POINTER + prd[row_end:]


class JoinFeatureBindingTests(unittest.TestCase):
    def join(self, root: Path, texts: tuple[str, str, str]) -> list[str]:
        prd, architecture, stack = (text.encode("utf-8") for text in texts)
        return full_product_package_checker_errors(prd, architecture, stack, repo_root=root)

    def write_features(self, root: Path, text: str = FEATURE) -> Path:
        features = root / "docs" / "product" / "features"
        features.mkdir(parents=True, exist_ok=True)
        (features / "product.feature").write_text(text, encoding="utf-8")
        return features

    def bound_package(self, root: Path) -> tuple[str, str, str]:
        prd, architecture, stack = strictize_approved_package(
            prd_with_pointer(), release_architecture(), bdd_stack()
        )
        return bind_features(prd, self.write_features(root)), architecture, stack

    def test_approved_feature_files_pass_the_join(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual([], self.join(root, self.bound_package(root)))

    def test_scenario_changed_after_approval_fails_the_join(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            texts = self.bound_package(root)
            self.write_features(root, FEATURE.replace("completion is observed", "nothing is observed", 1))
            self.assertEqual(STALE, self.join(root, texts))

    def test_declared_feature_directory_that_is_missing_fails_the_join(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            texts = self.bound_package(root)
            (root / "docs" / "product" / "features" / "product.feature").unlink()
            (root / "docs" / "product" / "features").rmdir()
            errors = self.join(root, texts)
            self.assertTrue(any("features directory not found" in error for error in errors), errors)

    def test_package_without_a_feature_pointer_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_features(root, FEATURE.replace("completion is observed", "nothing is observed", 1))
            texts = strictize_approved_package(valid_prd(), release_architecture(), valid_stack())
            self.assertEqual([], self.join(root, texts))


if __name__ == "__main__":
    unittest.main()
