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

    def test_frontmatter_preserves_comments_blanks_folded_values_and_colons(self) -> None:
        parsed = check_skill_spec.parse_frontmatter(
            "---\n"
            "# keep this comment inert\n"
            "name: demo\n"
            "\n"
            "description: \"See https://example.test:8443/docs\n"
            "  for details\"\n"
            "---\n"
            "# body\n"
        )
        self.assertIsNotNone(parsed)
        fields, body_start = parsed
        self.assertEqual(fields["name"], "demo")
        self.assertEqual(
            fields["description"], "See https://example.test:8443/docs for details"
        )
        self.assertEqual(body_start, 7)

    def test_frontmatter_rejects_duplicate_keys(self) -> None:
        self.assertIsNone(
            check_skill_spec.parse_frontmatter(
                "---\nname: demo\nname: other\ndescription: x\n---\n"
            )
        )

    def test_frontmatter_rejects_malformed_top_level_lines_and_empty_keys(self) -> None:
        for line in ("not a key", "- key: value", ": empty", "   : empty"):
            with self.subTest(line=line):
                self.assertIsNone(
                    check_skill_spec.parse_frontmatter(
                        f"---\n{line}\n---\n"
                    )
                )

    def test_frontmatter_rejects_orphan_continuations(self) -> None:
        self.assertIsNone(
            check_skill_spec.parse_frontmatter("---\n  continuation\n---\n")
        )

    def test_frontmatter_rejects_unterminated_delimiter(self) -> None:
        self.assertIsNone(
            check_skill_spec.parse_frontmatter("---\nname: demo\ndescription: x\n")
        )

    def test_frontmatter_rejects_quoted_scalar_trailing_text(self) -> None:
        self.assertIsNone(
            check_skill_spec.parse_frontmatter(
                '---\nname: demo\ndescription: "valid" trailing\n---\n'
            )
        )

    def test_frontmatter_rejects_continuation_after_closed_quote(self) -> None:
        self.assertIsNone(
            check_skill_spec.parse_frontmatter(
                '---\nname: demo\ndescription: "valid"\n  trailing\n---\n'
            )
        )

    def test_frontmatter_keeps_first_character_after_quote_only_opening_line(self) -> None:
        parsed = check_skill_spec.parse_frontmatter(
            '---\nname: demo\ndescription: "\n  starts here"\n---\n'
        )
        self.assertIsNotNone(parsed)
        fields, _ = parsed
        self.assertEqual("starts here", fields["description"])

    def test_frontmatter_accepts_simple_block_scalar_and_list_subset(self) -> None:
        parsed = check_skill_spec.parse_frontmatter(
            "---\n"
            "name: demo\n"
            "description: |\n"
            "  first line\n"
            "  second line\n"
            "allowed-tools:\n"
            "  - browser\n"
            "  - terminal\n"
            "---\n"
        )
        self.assertIsNotNone(parsed)
        fields, _ = parsed
        self.assertEqual(fields["description"], "first line\nsecond line")
        self.assertEqual(fields["allowed-tools"], "- browser - terminal")

    def test_checker_reports_frontmatter_syntax_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = root / "demo"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: demo\nname: duplicate\ndescription: x\n---\n",
                encoding="utf-8",
            )
            findings = check_skill_spec.check_skills_root(root)
            self.assertIn("duplicate top-level key", "\n".join(findings))


if __name__ == "__main__":
    unittest.main()
