#!/usr/bin/env python3
"""check_skill_bindings.py pins exact bound skills against installed content."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
REPO_ROOT = SCRIPTS_DIR.parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_skill_bindings  # noqa: E402


AGENTS_TEMPLATE = """# Project Rules

## Skill Bindings

Words here.

| Slot | Stage | Bound skill | Pinned SHA-256 |
| --- | --- | --- | --- |
| ui_design | UI pass | {direction} | {direction_pin} |
| style_integration | style pass | {direction} | {direction_pin} |
| design_compilation | pair | `compiler-skill` | {compiler_pin} |
| frontend_implementation | missions | {frontend} | {frontend_pin} |
| ui_quality_verification | quality | {direction} | {direction_pin} |
| code_security_verification | security | `compiler-skill` | {compiler_pin} |

## After
"""


class SkillBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.skills = self.root / "skills"
        for name, body in (
            ("taste-skill", "# Taste one\n"),
            ("compiler-skill", "# Compiler one\n"),
            ("front-skill", "# Front one\n"),
        ):
            skill_dir = self.skills / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(body, encoding="utf-8", newline="\n")
        self.agents = self.root / "AGENTS.md"

    def tearDown(self) -> None:
        self._temp.cleanup()

    def write_agents(
        self,
        direction: str,
        direction_pin: str,
        frontend: str,
        frontend_pin: str,
        compiler_pin: str | None = None,
    ) -> None:
        self.agents.write_text(
            AGENTS_TEMPLATE.format(
                direction=direction,
                direction_pin=direction_pin,
                compiler_pin=compiler_pin
                or check_skill_bindings.hash_skill(
                    self.skills / "compiler-skill" / "SKILL.md"
                ),
                frontend=frontend,
                frontend_pin=frontend_pin,
            ),
            encoding="utf-8",
        )

    def test_pinned_unchanged_skills_pass(self) -> None:
        self.write_agents(
            "`taste-skill`",
            check_skill_bindings.hash_skill(self.skills / "taste-skill" / "SKILL.md"),
            "`front-skill`",
            check_skill_bindings.hash_skill(self.skills / "front-skill" / "SKILL.md"),
        )
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        self.assertEqual([], findings)

    def test_unpinned_changed_or_missing_skills_fail(self) -> None:
        pinned = check_skill_bindings.hash_skill(
            self.skills / "taste-skill" / "SKILL.md"
        )
        self.write_agents("`taste-skill`", pinned, "`front-skill`", "")
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        joined = "\n".join(findings)
        self.assertIn("bound without a pinned full-tree hash", joined)

        (self.skills / "taste-skill" / "SKILL.md").write_text(
            "# Taste two\n", encoding="utf-8", newline="\n"
        )
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        joined = "\n".join(findings)
        self.assertIn("does not match the installed skill", joined)

        self.write_agents("`taste-skill`", pinned, "`ghost-skill`", "0" * 64)
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        joined = "\n".join(findings)
        self.assertIn("not found under any skill directory", joined)

    def test_prose_compound_and_placeholder_bindings_fail(self) -> None:
        self.write_agents(
            "<bundled taste pass, or your own>",
            "0" * 64,
            "`compiler-skill` + `front-skill`",
            "0" * 64,
        )
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        joined = "\n".join(findings)
        self.assertEqual(4, joined.count("must bind exactly one skill name"))

    def test_project_template_keeps_slots_unresolved_until_owner_confirmation(self) -> None:
        template_path = (
            REPO_ROOT
            / "skills"
            / "delivery-harness"
            / "assets"
            / "templates"
            / "PROJECT_AGENTS.template.md"
        )
        rows = check_skill_bindings.parse_binding_rows(
            template_path.read_text(encoding="utf-8")
        )
        self.assertEqual(check_skill_bindings.REQUIRED_SLOTS, {slot for slot, _, _, _ in rows})
        for _slot, cell, pin, _ in rows:
            self.assertIsNone(check_skill_bindings.bound_skill_name(cell))
            self.assertNotRegex(pin, re.compile(r"^[0-9a-f]{64}$"))

    def test_fenced_missing_duplicate_and_malformed_contracts_fail(self) -> None:
        valid = AGENTS_TEMPLATE.format(
            direction="`taste-skill`",
            direction_pin=check_skill_bindings.hash_skill(self.skills / "taste-skill"),
            compiler_pin=check_skill_bindings.hash_skill(self.skills / "compiler-skill"),
            frontend="`front-skill`",
            frontend_pin=check_skill_bindings.hash_skill(self.skills / "front-skill"),
        )
        compact = valid.replace("\n\n", "\n")
        cases = {
            "fenced": "```markdown\n" + valid + "\n```\n",
            "short backtick closer": "````markdown\nexample\n```\n" + valid + "\n````\n",
            "short tilde closer": "~~~~markdown\nexample\n~~~\n" + valid + "\n~~~~\n",
            "trailing backtick text": "```markdown\n```not-a-close\n" + valid + "\n```\n",
            "trailing tilde text": "~~~markdown\n~~~not-a-close\n" + valid + "\n~~~\n",
            "raw script block": "<script>\n" + valid + "\n</script>\n",
            "raw style block": "<style>\n" + valid + "\n</style>\n",
            "raw pre block": "<pre>\n" + valid + "\n</pre>\n",
            "raw div block": "<div>\n" + compact + "\n</div>\n\n",
            "raw CDATA block": "<![CDATA[\n" + valid + "\n]]>\n",
            "raw processing instruction": "<?xml version='1.0'\n" + valid + "\n?>\n",
            "raw textarea block": "<textarea>\n" + valid + "\n</textarea>\n",
            "raw custom block": "<x-widget>\n" + compact + "\n</x-widget>\n\n",
            "raw closing div block": "</div>\n" + compact + "\n\n",
            "raw closing custom block": "</x-widget>\n" + compact + "\n\n",
            "missing": valid.replace("## Skill Bindings", "## Other Bindings"),
            "duplicate": valid.replace(
                "## After", "## Skill Bindings\n\n| bad | row |\n\n## After"
            ),
            "malformed": valid.replace(
                "| ui_design | UI pass | `taste-skill` |",
                "| ui_design | UI pass | extra | `taste-skill` |",
            ),
        }
        for label, text in cases.items():
            with self.subTest(case=label):
                self.agents.write_text(text, encoding="utf-8")
                findings, _ = check_skill_bindings.check_bindings(
                    self.agents, [self.skills]
                )
                self.assertTrue(findings)


if __name__ == "__main__":
    unittest.main()
