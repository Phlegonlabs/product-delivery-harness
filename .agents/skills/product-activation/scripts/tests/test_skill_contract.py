from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class ProductActivationSkillContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (SKILL_ROOT / relative).read_text(encoding="utf-8")

    def test_identity_metadata_and_trigger_are_specific(self) -> None:
        skill = self.read("SKILL.md")
        metadata = self.read("agents/openai.yaml")
        self.assertIn("name: product-activation", skill)
        self.assertIn("post-delivery activation", skill)
        self.assertIn('display_name: "Product Activation"', metadata)
        self.assertIn("$product-activation", metadata)
        self.assertIn("allow_implicit_invocation: true", metadata)

    def test_skill_preserves_delivery_and_authorization_boundaries(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/activation-contract.md")
        for phrase in (
            "Never create, edit, reopen, or extend `docs/goal/PLAN.md`",
            "Capability and permission are separate facts",
            "After an unknown result, read back before any retry",
            "Never implement a missing product hook here",
            "never weakens the host policy",
        ):
            self.assertIn(phrase, skill)
        self.assertIn("Exact Action Digest", contract)
        self.assertIn("action_time_confirmation", contract)
        self.assertIn("user_handoff", contract)
        self.assertIn("A task cannot be ready until every dependency is `verified`", contract)
        self.assertIn("The mutation response cannot also be the read-back evidence", contract)

    def test_route_order_profiles_and_outcome_handoff_are_documented(self) -> None:
        skill = self.read("SKILL.md")
        profiles = self.read("references/profile-catalog.md")
        self.assertIn(
            "purpose-built connector, official API, official CLI, Browser, Computer Use, then manual handoff",
            skill,
        )
        for heading in ("## Core", "## Web", "## iOS", "## Browser Extension"):
            self.assertIn(heading, profiles)
        self.assertIn("verified `MS-*`", skill)
        self.assertIn("real measurement window closes", skill)

    def test_template_passes_structural_checker(self) -> None:
        template = SKILL_ROOT / "assets" / "templates" / "ACTIVATION.template.md"
        checker = SKILL_ROOT / "scripts" / "check_activation.py"
        result = subprocess.run(
            [sys.executable, str(checker), "--activation", str(template)],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
