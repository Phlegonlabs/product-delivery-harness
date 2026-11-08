"""Customer-discovery RA-* candidate rows fit the research-assessment schema they are handed to."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SYNTHESIS = ROOT / "standalone-skills" / "customer-discovery" / "references" / "synthesis.md"
TEMPLATE = ROOT / "standalone-skills" / "customer-discovery" / "assets" / "templates" / "DISCOVERY.template.md"


class DiscoverySynthesisPins(unittest.TestCase):
    def test_candidate_rows_continue_ra_numbering_and_map_confidence(self) -> None:
        text = SYNTHESIS.read_text(encoding="utf-8")
        self.assertIn("the next `RA-*` after the highest in `docs/product/research-assessment.md`", text)
        self.assertIn("`sourced` for an `observed` finding, `UNVALIDATED` for a `hypothesis` finding", text)

    def test_template_note_says_the_same(self) -> None:
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("RA-", text)
        self.assertIn("UNVALIDATED", text)


if __name__ == "__main__":
    unittest.main()
