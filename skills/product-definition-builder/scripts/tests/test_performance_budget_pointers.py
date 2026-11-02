import unittest
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[2] / "references/output-contract.md"
TARGET = "../../delivery-harness/references/performance-and-cost-budget.md"


class PerformanceBudgetPointerTests(unittest.TestCase):
    def test_nfr_scaling_and_observability_sections_point_at_the_budget_reference(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        for heading, following in (
            ("## Non-Functional Requirements", "## UX Requirements"),
            ("## Observability", "## Scaling and Reliability"),
            ("## Scaling and Reliability", "## Technical Risks and Tradeoffs"),
        ):
            section = text.split(heading, 1)[1].split(following, 1)[0]
            self.assertIn(f"]({TARGET})", section, heading)

    def test_pointer_target_exists(self) -> None:
        self.assertTrue((CONTRACT.parent / TARGET).resolve().is_file())


if __name__ == "__main__":
    unittest.main()
