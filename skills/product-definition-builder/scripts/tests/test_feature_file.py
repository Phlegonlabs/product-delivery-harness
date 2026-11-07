import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import feature_file as ff

SAMPLE = """# Inventory receiving
@PRD-INV-001
Feature: Receive stock

  Background:
    Given a warehouse clerk of tenant acme
    And an open purchase order PO-7 with 10 units

  @TEST-INV-012 @platform:web @auth:mock
  Scenario: Receive the full quantity
    When the clerk receives 10 units against PO-7
    Then PO-7 is closed
    And stock on hand shows 10 units

  @TEST-INV-013
  Scenario: Over-receipt is refused
    When the clerk receives 11 units against PO-7
    Then the receipt is refused with "exceeds ordered quantity"
    But PO-7 stays open
"""


class ParseTests(unittest.TestCase):
    def test_parses_feature_background_tags_and_steps(self):
        feature = ff.parse_feature_text(SAMPLE, "inv.feature")
        self.assertEqual(feature.name, "Receive stock")
        self.assertEqual(feature.tags, ["@PRD-INV-001"])
        self.assertEqual([s.keyword for s in feature.background], ["Given", "Given"])
        self.assertEqual(feature.test_ids(), {"TEST-INV-012", "TEST-INV-013"})
        first, second = feature.scenarios
        self.assertEqual(first.scenario_id, "TEST-INV-012/receive-the-full-quantity")
        self.assertEqual(first.profile, {"platform": "web", "auth": "mock"})
        self.assertEqual([s.keyword for s in first.steps], ["Given", "Given", "When", "Then", "Then"])
        self.assertEqual(first.steps_for("Then")[1].text, "stock on hand shows 10 units")
        self.assertEqual(second.profile, {})
        self.assertEqual([s.keyword for s in second.steps], ["Given", "Given", "When", "Then", "Then"])
        self.assertEqual(second.steps[-1].text, "PO-7 stays open")

    def test_crlf_and_unscoped_ids(self):
        text = "Feature: F\r\n@TEST-001\r\nScenario: Do it\r\nWhen x\r\nThen y\r\n"
        feature = ff.parse_feature_text(text)
        self.assertEqual(feature.scenarios[0].scenario_id, "TEST-001/do-it")

    def test_slug(self):
        self.assertEqual(ff.slug("  Receive  the FULL quantity! "), "receive-the-full-quantity")
        with self.assertRaises(ff.FeatureError):
            ff.slug("***")


class RejectionTests(unittest.TestCase):
    def assert_rejects(self, text, fragment, line=None):
        with self.assertRaises(ff.FeatureError) as ctx:
            ff.parse_feature_text(text, "f.feature")
        self.assertIn(fragment, str(ctx.exception))
        if line is not None:
            self.assertTrue(str(ctx.exception).startswith(f"f.feature:{line}:"), str(ctx.exception))

    def test_scenario_needs_exactly_one_test_tag(self):
        self.assert_rejects("Feature: F\nScenario: S\nWhen x\nThen y\n", "exactly one @TEST", 2)
        self.assert_rejects("Feature: F\n@TEST-001 @TEST-002\nScenario: S\nWhen x\nThen y\n", "found 2", 3)

    def test_scenario_needs_when_and_then(self):
        self.assert_rejects("Feature: F\n@TEST-001\nScenario: S\nGiven a\nThen y\n", "at least one When", 3)
        self.assert_rejects("Feature: F\n@TEST-001\nScenario: S\nWhen x\n", "one Then", 3)

    def test_duplicate_scenario_id(self):
        text = "Feature: F\n@TEST-001\nScenario: Same\nWhen x\nThen y\n@TEST-001\nScenario: same!\nWhen x\nThen y\n"
        self.assert_rejects(text, "duplicate scenario id TEST-001/same", 7)

    def test_unsupported_gherkin(self):
        self.assert_rejects("Feature: F\n@TEST-001\nScenario Outline: S\nWhen <x>\nThen y\n", "Scenario Outline is not supported", 3)
        self.assert_rejects("Feature: F\n@TEST-001\nScenario: S\nWhen x\n| a | b |\nThen y\n", "data tables", 5)
        self.assert_rejects('Feature: F\n@TEST-001\nScenario: S\nWhen x\n"""\ntext\n"""\nThen y\n', "doc strings", 5)

    def test_structure_errors(self):
        self.assert_rejects("@TEST-001\nScenario: S\nWhen x\nThen y\n", "Feature: must come first", 2)
        self.assert_rejects("Feature: F\nWhen x\n", "must belong to a Scenario", 2)
        self.assert_rejects("Feature: F\nBackground:\nWhen x\n", "Given steps only", 3)
        self.assert_rejects("Feature: F\n@TEST-001\nScenario: S\nAnd x\nThen y\n", "no previous", 4)
        self.assert_rejects("Feature: F\n@TEST-001\nScenario: S\nWhen x\nThen y\n@TEST-002\n", "end of file", 0)
        self.assert_rejects("Feature: F\n@TEST-001 @platform:Web\nScenario: S\nWhen x\nThen y\n", "malformed profile tag", 3)
        self.assert_rejects("", "empty feature file", 0)


if __name__ == "__main__":
    unittest.main()
