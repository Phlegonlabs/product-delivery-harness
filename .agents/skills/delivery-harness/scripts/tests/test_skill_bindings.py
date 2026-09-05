#!/usr/bin/env python3
"""check_skill_bindings.py pins bound skills against their installed content."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_skill_bindings  # noqa: E402


AGENTS_TEMPLATE = """# Project Rules

## Skill Bindings

Words here.

| Slot | Stage | Bound skill | Pinned SHA-256 |
| --- | --- | --- | --- |
| design_direction | UI pass | {direction} | {direction_pin} |
| design_compilation | pair | <bundled `design-system-compiler` + `frontend-design`> | n/a |
| frontend_implementation | missions | {frontend} | {frontend_pin} |

## After
"""


def sha256_of(path: Path) -> str:
    return check_skill_bindings.hash_skill(path)


class SkillBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.skills = self.root / "skills"
        for name, body in (
            ("taste-skill", "# Taste one\n"),
            ("front-skill", "# Front one\n"),
        ):
            skill_dir = self.skills / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
        self.agents = self.root / "AGENTS.md"

    def tearDown(self) -> None:
        self._temp.cleanup()

    def write_agents(self, direction: str, direction_pin: str, frontend: str, frontend_pin: str) -> None:
        self.agents.write_text(
            AGENTS_TEMPLATE.format(
                direction=direction,
                direction_pin=direction_pin,
                frontend=frontend,
                frontend_pin=frontend_pin,
            ),
            encoding="utf-8",
        )

    def test_pinned_unchanged_skills_pass(self) -> None:
        self.write_agents(
            "`taste-skill`",
            sha256_of(self.skills / "taste-skill" / "SKILL.md"),
            "`front-skill`",
            sha256_of(self.skills / "front-skill" / "SKILL.md"),
        )
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        self.assertEqual([], findings)

    def test_unpinned_or_changed_or_missing_skills_fail(self) -> None:
        pinned = sha256_of(self.skills / "taste-skill" / "SKILL.md")
        self.write_agents("`taste-skill`", pinned, "`front-skill`", "")
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        joined = "\n".join(findings)
        self.assertIn("bound without a pinned SKILL.md hash", joined)

        (self.skills / "taste-skill" / "SKILL.md").write_text(
            "# Taste two\n", encoding="utf-8"
        )
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        joined = "\n".join(findings)
        self.assertIn("does not match the installed skill", joined)

        self.write_agents(
            "`taste-skill`", pinned, "`ghost-skill`", "0" * 64
        )
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        joined = "\n".join(findings)
        self.assertIn("not found under any skill directory", joined)

    def test_placeholders_and_defaults_are_ignored(self) -> None:
        self.write_agents(
            "<bundled Taste-aware pass>", "n/a", "<or your own>", ""
        )
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
