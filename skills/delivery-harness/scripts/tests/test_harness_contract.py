#!/usr/bin/env python3
"""Tests for harness_contract.contract_digest's normalization rules."""

from __future__ import annotations

import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_contract import SKILL_NAMES, contract_digest  # noqa: E402


def create_required_skills(root: Path) -> None:
    skills_root = root / "skills"
    for name in SKILL_NAMES:
        skill = skills_root / name
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8", newline="\n")


class ContractDigestTests(unittest.TestCase):
    def test_oversized_skill_file_and_bundle_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_required_skills(root)
            with patch("harness_contract.MAX_FILE_BYTES", 1), self.assertRaises(ValueError):
                contract_digest(root / "skills")
            with patch("harness_contract.MAX_BUNDLE_BYTES", 1), self.assertRaises(ValueError):
                contract_digest(root / "skills")

    def test_reparse_guard_rejects_before_read(self):
        from types import SimpleNamespace
        from harness_contract import _plain_stat
        import stat
        with patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFREG,
                                                                     st_file_attributes=0x400)):
            with self.assertRaises(ValueError):
                _plain_stat(Path("linked"))

    def test_linked_skill_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_required_skills(root)
            link = root / "skills/delivery-harness/linked.md"
            try:
                link.symlink_to(root / "skills/delivery-harness/SKILL.md")
            except OSError:
                self.skipTest("symlink privilege unavailable; reparse guard tested separately")
            with self.assertRaises(ValueError):
                contract_digest(root / "skills")

    def test_line_endings_do_not_change_the_digest(self) -> None:
        # The digest gates dispatch; a Windows checkout (CRLF) and its packaged
        # copy (LF) must identify the same contract.
        with tempfile.TemporaryDirectory() as lf_dir, tempfile.TemporaryDirectory() as crlf_dir:
            lf_root, crlf_root = Path(lf_dir), Path(crlf_dir)
            create_required_skills(lf_root)
            create_required_skills(crlf_root)
            harness_lf = lf_root / "skills" / "delivery-harness"
            harness_crlf = crlf_root / "skills" / "delivery-harness"
            for path in harness_lf.rglob("*"):
                if path.is_file():
                    relative = path.relative_to(harness_lf)
                    target = harness_crlf / relative
                    target.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
            self.assertEqual(
                contract_digest(lf_root / "skills"),
                contract_digest(crlf_root / "skills"),
            )

    def test_tests_and_caches_are_ignored_but_real_files_are_not(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_required_skills(root)
            skills = root / "skills" / "delivery-harness"
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

    def test_each_bundled_runtime_skill_is_part_of_the_digest(self) -> None:
        for skill_name in SKILL_NAMES:
            with self.subTest(skill=skill_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                create_required_skills(root)
                skills_root = root / "skills"
                before = contract_digest(skills_root)
                skill_file = skills_root / skill_name / "SKILL.md"
                skill_file.write_text(
                    f"# {skill_name} changed\n", encoding="utf-8", newline="\n"
                )
                self.assertNotEqual(contract_digest(skills_root), before)

    def test_missing_required_skill_fails_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_required_skills(root)
            missing = root / "skills" / "product-activation"
            shutil.rmtree(missing)
            with self.assertRaises(FileNotFoundError) as raised:
                contract_digest(root / "skills")
            self.assertEqual(
                f"required bundled skill directory is absent: {missing}",
                str(raised.exception),
            )


if __name__ == "__main__":
    unittest.main()
