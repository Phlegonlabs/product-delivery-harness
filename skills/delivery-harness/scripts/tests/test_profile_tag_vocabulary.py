"""The feature-file reader and the acceptance renderer accept the same profile tag values."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import render_delivery_acceptance as rda  # noqa: E402


class ProfileTagVocabularyTests(unittest.TestCase):
    def test_reader_and_renderer_share_the_profile_values(self) -> None:
        reader = rda.load_feature_reader()
        renderer_values = {tag: set(values) for tag, (_, values) in rda.TAG_FIELDS.items()}
        reader_values = {tag: set(values) for tag, values in reader.PROFILE_VALUES.items()}
        self.assertEqual(renderer_values, reader_values)


if __name__ == "__main__":
    unittest.main()
