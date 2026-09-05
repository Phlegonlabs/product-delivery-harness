#!/usr/bin/env python3
"""check_skill_spec.py enforces the Agent Skills open-specification rules."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_skill_spec  # noqa: E402


def write_skill(root: Path, name: str, frontmatter: str, body: str = "# Skill\n") -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\n{frontmatter}\n---\n{body}", encoding="utf-8"
    )


class SkillSpecTests(unittest.TestCase):
    def test_checker_accepts_a_conforming_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_skill(
                root,
                "good-skill",
                'name: good-skill\ndescription: "Does one thing well."',
            )
            self.assertEqual([], check_skill_spec.check_skills_root(root))

    def test_checker_rejects_spec_violations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_skill(
                root,
                "renamed",
                'name: original\ndescription: "x"\nvendor-key: y',
            )
            write_skill(root, "no-description", "name: no-description")
            write_skill(
                root,
                "long-description",
                'name: long-description\ndescription: "' + "x" * 1025 + '"',
            )
            write_skill(
                root,
                "long-body",
                "name: long-body\ndescription: 'x'",
                body="# Body\n" + "line\n" * 501,
            )
            (root / "not-a-skill").mkdir()
            (root / "not-a-skill" / "README.md").write_text("x", encoding="utf-8")

            findings = check_skill_spec.check_skills_root(root)

            joined = "\n".join(findings)
            self.assertIn("does not match directory name", joined)
            self.assertIn("frontmatter keys outside the spec", joined)
            self.assertIn("frontmatter has no description", joined)
            self.assertIn("description exceeds 1024 characters", joined)
            self.assertIn("over the 500-line guidance", joined)
            self.assertIn("missing SKILL.md", joined)


if __name__ == "__main__":
    unittest.main()
