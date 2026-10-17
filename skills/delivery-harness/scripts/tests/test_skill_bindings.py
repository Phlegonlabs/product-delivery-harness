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
| style_integration | style pass | `frontend-design` | {style_pin} |
| design_compilation | pair | `compiler-skill` | {compiler_pin} |
| frontend_implementation | missions | {frontend} | {frontend_pin} |
| ui_quality_verification | quality | {direction} | {direction_pin} |
| code_security_verification | security | `compiler-skill` | {compiler_pin} |

## After
"""


class SkillBindingTests(unittest.TestCase):
    def test_stage_deferral_and_required_pin_drift(self) -> None:
        pin = check_skill_bindings.hash_skill(self.skills / "compiler-skill" / "SKILL.md")
        text = "## Skill Bindings\n| Slot | Stage | Bound skill | Pinned SHA-256 |\n| --- | --- | --- | --- |\n"
        text += f"| code_security_verification | security | compiler-skill | {pin} |\n"
        text += "| ui_design | later | pending | pending |\n"
        self.agents.write_text(text, encoding="utf-8")
        self.assertEqual([], check_skill_bindings.check_bindings(self.agents, [self.skills], stage="backend")[0])
        self.assertEqual([], check_skill_bindings.check_bindings(self.agents, [self.skills], stage="product-definition")[0])
        self.assertTrue(check_skill_bindings.check_bindings(self.agents, [self.skills], stage="ui-design")[0])
        self.assertTrue(check_skill_bindings.check_bindings(self.agents, [self.skills])[0])
        self.agents.write_text(text.replace("pending | pending", "future-uninstalled | " + "f" * 64), encoding="utf-8")
        self.assertEqual([], check_skill_bindings.check_bindings(self.agents, [self.skills], stage="backend")[0])
        (self.skills / "compiler-skill" / "SKILL.md").write_text("changed", encoding="utf-8")
        self.assertTrue(check_skill_bindings.check_bindings(self.agents, [self.skills], stage="backend")[0])

    def test_deferred_stage_rejects_malformed_unknown_and_duplicate_rows(self) -> None:
        base = "## Skill Bindings\n| Slot | Stage | Bound skill | Pinned SHA-256 |\n| --- | --- | --- | --- |\n"
        for rows in ("| extra | future | pending | pending |\n",
                     "| ui_design | future | pending | pending |\n" * 2,
                     "| ui_design | malformed |\n",
                     "| ui_design | future | two skills | pending |\n"):
            self.agents.write_text(base + rows, encoding="utf-8")
            self.assertTrue(check_skill_bindings.check_bindings(self.agents, [self.skills], stage="product-definition")[0])

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.skills = self.root / "skills"
        for name, body in (
            ("taste-skill", "# Taste one\n"),
            ("frontend-design", "# Required author\n"),
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
                style_pin=check_skill_bindings.hash_skill(self.skills / "frontend-design" / "SKILL.md"),
                compiler_pin=compiler_pin
                or check_skill_bindings.hash_skill(
                    self.skills / "compiler-skill" / "SKILL.md"
                ),
                frontend=frontend,
                frontend_pin=frontend_pin,
            ),
            encoding="utf-8",
        )

    def test_taste_cannot_replace_frontend_design_in_ui_stage(self) -> None:
        self.write_agents("taste-skill", check_skill_bindings.hash_skill(self.skills / "taste-skill" / "SKILL.md"),
                          "front-skill", check_skill_bindings.hash_skill(self.skills / "front-skill" / "SKILL.md"))
        self.agents.write_text(self.agents.read_text(encoding="utf-8").replace(
            "| style_integration | style pass | `frontend-design`", "| style_integration | style pass | taste-skill"),
            encoding="utf-8")
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills], stage="ui-design")
        self.assertIn("style_integration requires frontend-design", "\n".join(findings))

    def test_pinned_unchanged_skills_pass(self) -> None:
        self.write_agents(
            "`taste-skill`",
            check_skill_bindings.hash_skill(self.skills / "taste-skill" / "SKILL.md"),
            "`front-skill`",
            check_skill_bindings.hash_skill(self.skills / "front-skill" / "SKILL.md"),
        )
        findings, _ = check_skill_bindings.check_bindings(self.agents, [self.skills])
        self.assertEqual([], findings)

    def test_development_only_files_do_not_change_the_skill_hash(self) -> None:
        # hash_skill covers the installed runtime tree, so development-only
        # files must never move a pin; a runtime script change still must.
        skill = self.skills / "taste-skill"
        pinned = check_skill_bindings.hash_skill(skill / "SKILL.md")
        tests_dir = skill / "scripts" / "tests"
        tests_dir.mkdir(parents=True)
        added = tests_dir / "test_new.py"
        added.write_text("x = 1\n", encoding="utf-8", newline="\n")
        timings = skill / "ci-test-timings.json"
        timings.write_text('{"ci": {}}\n', encoding="utf-8", newline="\n")
        requirements = skill / "requirements-test.txt"
        requirements.write_text("pytest\n", encoding="utf-8", newline="\n")
        self.assertEqual(pinned, check_skill_bindings.hash_skill(skill / "SKILL.md"))
        added.write_text("x = 2\n", encoding="utf-8", newline="\n")
        (tests_dir / "test_other.py").write_text("y = 1\n", encoding="utf-8", newline="\n")
        timings.write_text('{"ci": {"changed": true}}\n', encoding="utf-8", newline="\n")
        requirements.write_text("pytest>=8\n", encoding="utf-8", newline="\n")
        self.assertEqual(pinned, check_skill_bindings.hash_skill(skill / "SKILL.md"))
        (skill / "SKILL.md").write_text("# Taste two\n", encoding="utf-8", newline="\n")
        self.assertNotEqual(pinned, check_skill_bindings.hash_skill(skill / "SKILL.md"))

    def test_capital_tests_directory_is_part_of_the_skill_hash(self) -> None:
        # The development-only rule is case-sensitive, so scripts/Tests/ with
        # a capital T is runtime content: adding or changing one of its files
        # must move the pin.
        skill = self.skills / "taste-skill"
        before = check_skill_bindings.hash_skill(skill / "SKILL.md")
        runtime = skill / "scripts" / "Tests" / "runtime.py"
        runtime.parent.mkdir(parents=True)
        runtime.write_text("value = 1\n", encoding="utf-8", newline="\n")
        added = check_skill_bindings.hash_skill(skill / "SKILL.md")
        self.assertNotEqual(before, added)
        runtime.write_text("value = 2\n", encoding="utf-8", newline="\n")
        self.assertNotEqual(added, check_skill_bindings.hash_skill(skill / "SKILL.md"))

    def test_cache_names_and_suffixes_do_not_change_the_skill_hash(self) -> None:
        # The cache rule matches whole path parts case-sensitively and only the
        # .pyc/.pyo suffix in any letter case: regular files named exactly
        # __pycache__ or .pytest_cache and a module.PYC file never move a pin,
        # while foo__pycache__/ and __PYCACHE__/ lookalikes are runtime content.
        # The case variants live in different skills because Windows file
        # systems ignore case, so both spellings could not sit in one directory.
        cache_skill = self.skills / "taste-skill"
        runtime_skill = self.skills / "compiler-skill"
        before = check_skill_bindings.hash_skill(cache_skill / "SKILL.md")
        scripts = cache_skill / "scripts"
        scripts.mkdir()
        for name in (".pytest_cache", "__pycache__"):
            (scripts / name).write_text("cache data\n", encoding="utf-8", newline="\n")
            self.assertEqual(before, check_skill_bindings.hash_skill(cache_skill / "SKILL.md"))
        (scripts / "module.PYC").write_bytes(b"\x00\x01cache bytes\n")
        self.assertEqual(before, check_skill_bindings.hash_skill(cache_skill / "SKILL.md"))
        runtime_before = check_skill_bindings.hash_skill(runtime_skill / "SKILL.md")
        for relative in ("foo__pycache__/runtime.py", "__PYCACHE__/runtime.py"):
            path = runtime_skill / "scripts" / relative
            path.parent.mkdir(parents=True)
            path.write_text("value = 1\n", encoding="utf-8", newline="\n")
            self.assertNotEqual(
                runtime_before, check_skill_bindings.hash_skill(runtime_skill / "SKILL.md")
            )

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
        self.assertEqual(3, joined.count("must bind exactly one skill name"))

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
            style_pin=check_skill_bindings.hash_skill(self.skills / "frontend-design"),
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
