"""Navigation order must not manufacture a repair wave."""

from copy import deepcopy
from itertools import permutations
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hifi_reviewer


class DiagnosticNavigationTests(unittest.TestCase):
    def expected(self):
        rows = [{"from": "index.html", "to": destination, "target": "390",
                 "trigger": "click", "destinationTarget": "390", "visible": True,
                 "productVisible": True, "visibleSurfaces": [surface],
                 "focusCorrect": True, "result": "PASS"}
                for destination, surface in (("index.html", "UI-001"), ("child.html", "UI-002"))]
        return {"overview": {}, "defaultSurface": "UI-001", "defaultVisible": True,
                "overviewInitiallyHidden": True, "navigation": rows,
                "views": [], "recovery": [], "viewport": [], "retention": [], "specimens": []}

    def test_clean_destinations_pass_in_every_observation_order(self):
        expected = self.expected()
        for rows in permutations(expected["navigation"]):
            with self.subTest(destinations=[row["to"] for row in rows]):
                actual = deepcopy(expected)
                actual["navigation"] = list(rows)
                self.assertEqual(([], []), hifi_reviewer.reviewer_diagnostic_coverage_findings(actual, expected))

    def test_wrong_destination_and_duplicate_destination_remain_defects(self):
        expected = self.expected()
        for destination in ("unexpected.html", "child.html"):
            with self.subTest(destination=destination):
                actual = deepcopy(expected)
                actual["navigation"][0]["to"] = destination
                structural, defects = hifi_reviewer.reviewer_diagnostic_coverage_findings(actual, expected)
                self.assertEqual([], structural)
                self.assertTrue(defects)
                self.assertIn("to", " ".join(defects))

    def test_unobserved_navigation_still_blocks_completeness(self):
        expected = self.expected()
        actual = deepcopy(expected)
        actual["navigation"][0]["result"] = "MISSING"
        structural, _ = hifi_reviewer.reviewer_diagnostic_coverage_findings(actual, expected)
        self.assertTrue(structural)


if __name__ == "__main__":
    unittest.main()
