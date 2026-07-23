import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_type_scale import (  # noqa: E402
    TypeScaleError,
    line_height_ratio,
    main,
    parse_step_spec,
)


class LineHeightRatioTests(unittest.TestCase):
    def test_unitless_line_height_is_used_directly(self) -> None:
        self.assertAlmostEqual(line_height_ratio("16px", "1.5"), 1.5, places=2)

    def test_px_line_height_divides_by_font_size(self) -> None:
        self.assertAlmostEqual(line_height_ratio("16", "24px"), 1.5, places=2)

    def test_font_size_without_px_suffix_is_accepted(self) -> None:
        self.assertAlmostEqual(line_height_ratio("16", "1.5"), 1.5, places=2)

    def test_non_numeric_font_size_rejected(self) -> None:
        with self.assertRaises(TypeScaleError):
            line_height_ratio("large", "1.5")

    def test_non_positive_values_rejected(self) -> None:
        with self.assertRaises(TypeScaleError):
            line_height_ratio("0", "1.5")
        with self.assertRaises(TypeScaleError):
            line_height_ratio("16px", "0")
        with self.assertRaises(TypeScaleError):
            line_height_ratio("16px", "-1.5")


class ParseStepSpecTests(unittest.TestCase):
    def test_defaults_to_text_kind(self) -> None:
        self.assertEqual(
            parse_step_spec("Body,16px,1.5"), ("Body", "16px", "1.5", "text")
        )

    def test_explicit_kind_is_lowercased(self) -> None:
        self.assertEqual(
            parse_step_spec("Heading,32px,1.2,HEADING"),
            ("Heading", "32px", "1.2", "heading"),
        )

    def test_unknown_kind_rejected(self) -> None:
        with self.assertRaises(TypeScaleError):
            parse_step_spec("Body,16px,1.5,display")

    def test_missing_role_rejected(self) -> None:
        with self.assertRaises(TypeScaleError):
            parse_step_spec(",16px,1.5")

    def test_wrong_field_count_rejected(self) -> None:
        with self.assertRaises(TypeScaleError):
            parse_step_spec("Body,16px")
        with self.assertRaises(TypeScaleError):
            parse_step_spec("Body,16px,1.5,text,extra")


class MainCliTests(unittest.TestCase):
    def test_body_text_at_wcag_minimum_passes(self) -> None:
        self.assertEqual(main(["--step", "Body,16px,1.5,text"]), 0)

    def test_body_text_below_wcag_minimum_fails(self) -> None:
        self.assertEqual(main(["--step", "Cramped body,16px,1.2,text"]), 1)

    def test_heading_uses_lower_readability_floor(self) -> None:
        # 1.2 fails the 1.5 text minimum but clears the 1.1 heading floor.
        self.assertEqual(main(["--step", "Heading,32px,1.2,text"]), 1)
        self.assertEqual(main(["--step", "Heading,32px,1.2,heading"]), 0)

    def test_heading_below_readability_floor_fails(self) -> None:
        self.assertEqual(main(["--step", "Tight heading,32px,24px,heading"]), 1)

    def test_mixed_steps_exit_one_when_any_fails(self) -> None:
        self.assertEqual(
            main(
                [
                    "--step",
                    "Body,16px,1.5,text",
                    "--step",
                    "Cramped body,16px,1.2,text",
                ]
            ),
            1,
        )

    def test_malformed_size_exits_two(self) -> None:
        self.assertEqual(main(["--step", "Body,large,1.5,text"]), 2)

    def test_malformed_step_spec_exits_two(self) -> None:
        self.assertEqual(main(["--step", "Body,16px"]), 2)


if __name__ == "__main__":
    unittest.main()
