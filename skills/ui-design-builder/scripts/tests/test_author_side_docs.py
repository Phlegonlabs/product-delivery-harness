"""Pin the author-side UI rules: three layers, kit and pilot, craft floor, checks per journey."""

import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
HARNESS_ROOT = SKILL_ROOT.parent / "delivery-harness"


def read(relative: str) -> str:
    return " ".join((SKILL_ROOT / relative).read_text(encoding="utf-8").split())


class AuthorSideDocsTests(unittest.TestCase):
    def test_intake_asks_for_impeccable_authorization_once(self):
        intake = read("references/ui-design-intake.md")
        self.assertIn("whether the Impeccable `critique` and `audit` may run on the HiFi", intake)
        self.assertIn("Impeccable workflow authorization: granted | declined", intake)
        self.assertIn("a declined answer leaves the wave `blocked`", intake)


if __name__ == "__main__":
    unittest.main()
