#!/usr/bin/env python3
"""Tests for harness_contract.contract_digest's normalization rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_contract import contract_digest  # noqa: E402


class ContractDigestTests(unittest.TestCase):
    @staticmethod
    def build_tree(directory: Path, ending: str) -> None:
        skills = directory / "skills" / "delivery-harness"
        skills.mkdir(parents=True)
        (skills / "SKILL.md").write_bytes(
            b"# contract\n" + ending.encode() + b"line two\n"
        )
        (skills / "reference.md").write_bytes(
            b"same bytes everywhere" + ending.encode()
        )

    def test_line_endings_do_not_change_the_digest(self) -> None:
        # The digest gates dispatch; a Windows checkout (CRLF) and its packaged
        # copy (LF) must identify the same contract.
        import tempfile

        with tempfile.TemporaryDirectory() as lf_dir, tempfile.TemporaryDirectory() as crlf_dir:
            lf_root, crlf_root = Path(lf_dir), Path(crlf_dir)
            self.build_tree(lf_root, "\n")
            self.build_tree(crlf_root, "\r\n")
            self.assertEqual(
                contract_digest(lf_root / "skills"),
                contract_digest(crlf_root / "skills"),
            )

    def test_tests_and_caches_are_ignored_but_real_files_are_not(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skills = root / "skills" / "delivery-harness"
            skills.mkdir(parents=True)
            (skills / "SKILL.md").write_text("# contract\n", encoding="utf-8")
            skills_root = root / "skills"
            before = contract_digest(skills_root)
            ignored_test = skills / "scripts" / "tests" / "test_new.py"
            ignored_test.parent.mkdir(parents=True, exist_ok=True)
            ignored_test.write_text("x = 1\n", encoding="utf-8")
            ignored_cache = skills / "scripts" / "__pycache__" / "mod.pyc"
            ignored_cache.parent.mkdir(parents=True)
            ignored_cache.write_bytes(b"junk")
            self.assertEqual(contract_digest(skills_root), before)
            runtime_file = skills / "scripts" / "harness_step.py"
            runtime_file.parent.mkdir(parents=True, exist_ok=True)
            runtime_file.write_text("# new runtime file\n", encoding="utf-8")
            self.assertNotEqual(contract_digest(skills_root), before)

    def test_product_activation_is_part_of_the_runtime_contract_digest(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            harness = root / "skills" / "delivery-harness"
            harness.mkdir(parents=True)
            (harness / "SKILL.md").write_text("# harness\n", encoding="utf-8")
            activation = root / "skills" / "product-activation"
            activation.mkdir(parents=True)
            (activation / "SKILL.md").write_text("# activation\n", encoding="utf-8")
            skills_root = root / "skills"
            before = contract_digest(skills_root)
            (activation / "SKILL.md").write_text("# activation changed\n", encoding="utf-8")
            self.assertNotEqual(contract_digest(skills_root), before)


if __name__ == "__main__":
    unittest.main()
