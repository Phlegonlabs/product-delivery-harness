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

    def test_regular_file_named_tests_is_kept_but_tests_directory_is_not(self) -> None:
        # Installers and hash_skill treat a directory component named "tests"
        # as development-only, while a regular file named "tests" is shipped
        # content that must reach the digest.
        with tempfile.TemporaryDirectory() as file_dir, tempfile.TemporaryDirectory() as dir_dir:
            file_root, dir_root = Path(file_dir), Path(dir_dir)
            create_required_skills(file_root)
            create_required_skills(dir_root)
            file_scripts = file_root / "skills" / "delivery-harness" / "scripts"
            file_scripts.mkdir(parents=True, exist_ok=True)
            before = contract_digest(file_root / "skills")
            named_tests = file_scripts / "tests"
            named_tests.write_text("RUNTIME = 1\n", encoding="utf-8", newline="\n")
            with_file = contract_digest(file_root / "skills")
            self.assertNotEqual(with_file, before)
            named_tests.write_text("RUNTIME = 2\n", encoding="utf-8", newline="\n")
            self.assertNotEqual(contract_digest(file_root / "skills"), with_file)
            dir_scripts = dir_root / "skills" / "delivery-harness" / "scripts"
            dir_before = contract_digest(dir_root / "skills")
            dev_only = dir_scripts / "tests" / "test_new.py"
            dev_only.parent.mkdir(parents=True, exist_ok=True)
            dev_only.write_text("x = 1\n", encoding="utf-8")
            self.assertEqual(contract_digest(dir_root / "skills"), dir_before)

    def test_pytest_cache_directory_does_not_change_the_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_required_skills(root)
            skills_root = root / "skills"
            before = contract_digest(skills_root)
            cache = root / "skills" / "delivery-harness" / "scripts" / ".pytest_cache"
            (cache / "v" / "cache").mkdir(parents=True)
            (cache / "CACHEDIR.TAG").write_bytes(b"junk")
            (cache / "v" / "cache" / "nodeids").write_bytes(b"[]")
            self.assertEqual(contract_digest(skills_root), before)

    def test_cache_names_and_suffixes_match_the_installers_in_the_digest(self) -> None:
        # The cache rule matches whole path parts case-sensitively and only the
        # .pyc/.pyo suffix in any letter case over the file name, exactly like
        # the installers and hash_skill: regular files named exactly
        # __pycache__ or .pytest_cache, a module.PYC file, and a file named
        # exactly .pyc change nothing, while foo__pycache__/ and __PYCACHE__/
        # lookalikes and a directory named module.PYC are runtime content. The
        # case variants live in different skills because Windows file systems
        # ignore case, so both spellings could not sit in one directory.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_required_skills(root)
            skills_root = root / "skills"
            scripts = root / "skills" / "delivery-harness" / "scripts"
            scripts.mkdir()
            for name in (".pytest_cache", "__pycache__", "module.PYC", ".pyc"):
                before = contract_digest(skills_root)
                path = scripts / name
                if path.suffix:
                    path.write_bytes(b"\x00\x01cache bytes\n")
                else:
                    path.write_text("cache data\n", encoding="utf-8", newline="\n")
                self.assertEqual(contract_digest(skills_root), before)
            runtime_scripts = root / "skills" / "product-definition-builder" / "scripts"
            for relative in ("foo__pycache__/runtime.py", "__PYCACHE__/runtime.py"):
                before = contract_digest(skills_root)
                path = runtime_scripts / relative
                path.parent.mkdir(parents=True)
                path.write_text("value = 1\n", encoding="utf-8", newline="\n")
                self.assertNotEqual(contract_digest(skills_root), before)
            compiled_scripts = root / "skills" / "design-system-compiler" / "scripts"
            before = contract_digest(skills_root)
            runtime = compiled_scripts / "module.PYC" / "runtime.py"
            runtime.parent.mkdir(parents=True)
            runtime.write_text("value = 2\n", encoding="utf-8", newline="\n")
            self.assertNotEqual(contract_digest(skills_root), before)

    def test_ci_data_files_do_not_change_the_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_required_skills(root)
            skills_root = root / "skills"
            before = contract_digest(skills_root)
            harness = root / "skills" / "delivery-harness"
            timings = harness / "ci-test-timings.json"
            requirements = harness / "requirements-test.txt"
            timings.write_text('{"ci": {}}\n', encoding="utf-8", newline="\n")
            requirements.write_text("pytest\n", encoding="utf-8", newline="\n")
            self.assertEqual(contract_digest(skills_root), before)
            timings.write_text('{"ci": {"changed": true}}\n', encoding="utf-8", newline="\n")
            requirements.write_text("pytest>=8\n", encoding="utf-8", newline="\n")
            self.assertEqual(contract_digest(skills_root), before)

    def test_directories_named_like_ci_files_are_still_walked(self) -> None:
        # Installers ship ci-test-timings.json and requirements-test.txt as
        # files. A directory with one of those names is ordinary content, so
        # its files must still contribute to the digest.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_required_skills(root)
            skills_root = root / "skills"
            harness = root / "skills" / "delivery-harness"
            timings_runtime = harness / "ci-test-timings.json" / "runtime.py"
            requirements_runtime = harness / "requirements-test.txt" / "runtime.py"
            for path in (timings_runtime, requirements_runtime):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("VERSION = 1\n", encoding="utf-8", newline="\n")
            before = contract_digest(skills_root)
            requirements_runtime.write_text("VERSION = 2\n", encoding="utf-8", newline="\n")
            after_requirements = contract_digest(skills_root)
            self.assertNotEqual(after_requirements, before)
            timings_runtime.write_text("VERSION = 2\n", encoding="utf-8", newline="\n")
            self.assertNotEqual(contract_digest(skills_root), after_requirements)

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
