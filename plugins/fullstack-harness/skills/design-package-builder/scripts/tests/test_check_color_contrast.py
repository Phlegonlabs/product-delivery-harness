import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_color_contrast import (  # noqa: E402
    ColorContrastError,
    contrast_ratio,
    main,
    parse_hex_color,
    parse_pair_spec,
)


class ParseHexColorTests(unittest.TestCase):
    def test_six_digit_hex_with_hash(self) -> None:
        self.assertEqual(parse_hex_color("#111111"), (17, 17, 17))

    def test_six_digit_hex_without_hash(self) -> None:
        self.assertEqual(parse_hex_color("FFFFFF"), (255, 255, 255))

    def test_three_digit_hex_expands(self) -> None:
        self.assertEqual(parse_hex_color("#fff"), (255, 255, 255))
        self.assertEqual(parse_hex_color("#000"), (0, 0, 0))

    def test_malformed_value_rejected(self) -> None:
        for bad in ("red", "#12345", "#gggggg", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(ColorContrastError):
                    parse_hex_color(bad)


class ContrastRatioTests(unittest.TestCase):
    def test_black_on_white_is_maximum_ratio(self) -> None:
        self.assertAlmostEqual(contrast_ratio("#000000", "#FFFFFF"), 21.0, places=2)

    def test_identical_colors_is_minimum_ratio(self) -> None:
        self.assertAlmostEqual(contrast_ratio("#FFFFFF", "#FFFFFF"), 1.0, places=2)
        self.assertAlmostEqual(contrast_ratio("#336699", "#336699"), 1.0, places=2)

    def test_ratio_is_symmetric(self) -> None:
        self.assertAlmostEqual(
            contrast_ratio("#000000", "#FFFFFF"),
            contrast_ratio("#FFFFFF", "#000000"),
            places=6,
        )

    def test_known_wcag_reference_gray_is_at_aa_threshold(self) -> None:
        # #767676 on white is a commonly cited WCAG reference value that sits
        # right at the 4.5:1 AA threshold for normal text.
        self.assertAlmostEqual(contrast_ratio("#767676", "#FFFFFF"), 4.54, places=1)


class ParsePairSpecTests(unittest.TestCase):
    def test_defaults_to_normal_size(self) -> None:
        self.assertEqual(
            parse_pair_spec("#111111,#FFFFFF"), ("#111111", "#FFFFFF", "normal")
        )

    def test_explicit_size_is_lowercased(self) -> None:
        self.assertEqual(
            parse_pair_spec("#111111,#FFFFFF,LARGE"),
            ("#111111", "#FFFFFF", "large"),
        )

    def test_unknown_size_rejected(self) -> None:
        with self.assertRaises(ColorContrastError):
            parse_pair_spec("#111111,#FFFFFF,huge")

    def test_wrong_field_count_rejected(self) -> None:
        with self.assertRaises(ColorContrastError):
            parse_pair_spec("#111111")
        with self.assertRaises(ColorContrastError):
            parse_pair_spec("#111111,#FFFFFF,normal,extra")


class MainCliTests(unittest.TestCase):
    def test_passing_pair_exits_zero(self) -> None:
        self.assertEqual(main(["--pair", "#000000,#FFFFFF,normal"]), 0)

    def test_failing_pair_exits_one(self) -> None:
        self.assertEqual(main(["--pair", "#FFFFFF,#FFFFFF,normal"]), 1)

    def test_mixed_pairs_exit_one_when_any_fails(self) -> None:
        self.assertEqual(
            main(
                [
                    "--pair",
                    "#000000,#FFFFFF,normal",
                    "--pair",
                    "#FFFFFF,#FFFFFF,normal",
                ]
            ),
            1,
        )

    def test_large_text_uses_lower_threshold(self) -> None:
        # A ratio that fails normal text (4.5:1) but clears the large/UI
        # threshold (3:1) should pass only when checked as large/ui.
        self.assertEqual(main(["--pair", "#949494,#FFFFFF,normal"]), 1)
        self.assertEqual(main(["--pair", "#949494,#FFFFFF,large"]), 0)
        self.assertEqual(main(["--pair", "#949494,#FFFFFF,ui"]), 0)

    def test_malformed_color_exits_two(self) -> None:
        self.assertEqual(main(["--pair", "notacolor,#FFFFFF,normal"]), 2)

    def test_malformed_pair_spec_exits_two(self) -> None:
        self.assertEqual(main(["--pair", "#FFFFFF"]), 2)


if __name__ == "__main__":
    unittest.main()
