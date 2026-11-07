import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import feature_file as ff  # noqa: E402

TEMPLATE = SCRIPTS.parent / "assets" / "templates" / "FEATURE.template.feature"


class TemplateTests(unittest.TestCase):
    def test_template_parses_and_shows_every_convention(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        feature = ff.parse_feature_text(text, TEMPLATE.name)
        self.assertEqual(["@PRD-001"], feature.tags)
        self.assertTrue(feature.background)
        self.assertEqual(2, len(feature.scenarios))
        self.assertEqual({"TEST-001", "TEST-002"}, feature.test_ids())
        self.assertEqual([{"platform": "web", "auth": "mock"}, {}], [s.profile for s in feature.scenarios])
        comments = [line for line in text.splitlines() if line.lstrip().startswith("#")]
        self.assertLessEqual(len(comments), 6)
        for word in ("Given", "When", "Then", "@TEST", "<TEST-ID>/<slug"):
            self.assertIn(word, "\n".join(comments))


if __name__ == "__main__":
    unittest.main()
