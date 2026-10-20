import sys
import unittest
import math
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_type_scale import (  # noqa: E402
    TypeScaleError,
    check_steps,
    line_height_ratio,
    main,
    parse_step_spec,
)


# These are the ten responsive rows supplied in AK-NUMERIC-PARSER-001.
SOURCE_EXPRESSION_ROWS = [
    (
        "display-hero,clamp(min(2.375rem, calc(9.75cqi * (1rem / 16px))), "
        "calc(5cqi * (1rem / 16px)), 4.625rem),.94,heading",
        0.94,
    ),
    (
        "display-page,clamp(min(2rem, calc(8.2cqi * (1rem / 16px))), "
        "calc(4.2cqi * (1rem / 16px)), 3.75rem),1,heading",
        1.0,
    ),
    (
        "display-notice,clamp(min(2rem, calc(8.2cqi * (1rem / 16px))), "
        "calc(4.6cqi * (1rem / 16px)), 4rem),1,heading",
        1.0,
    ),
    (
        "numeral-run,clamp(5.5rem, calc(13cqi * (1rem / 16px)), 11.25rem),"
        ".8,heading",
        0.8,
    ),
    (
        "numeral-layer,clamp(4rem, calc(8cqi * (1rem / 16px)), 7rem),"
        ".78,heading",
        0.78,
    ),
    (
        "heading-layer,clamp(1.875rem, calc(3.4cqi * (1rem / 16px)), "
        "2.75rem),1.05,heading",
        1.05,
    ),
    (
        "heading-section,clamp(1.75rem, calc(3cqi * (1rem / 16px)), "
        "2.5rem),1,heading",
        1.0,
    ),
    (
        "heading-gate,clamp(1.75rem, calc(2.4cqi * (1rem / 16px)), "
        "2rem),1,heading",
        1.0,
    ),
    (
        "lead,clamp(1.0625rem, calc(1.5cqi * (1rem / 16px)), 1.25rem),"
        "1.45,text",
        1.45,
    ),
    (
        "intro,clamp(1.0625rem, calc(1.5cqi * (1rem / 16px)), 1.1875rem),"
        "1.5,text",
        1.5,
    ),
]


class LineHeightRatioTests(unittest.TestCase):
    def test_unitless_line_height_is_used_directly(self) -> None:
        self.assertAlmostEqual(line_height_ratio("16px", "1.5"), 1.5, places=2)

    def test_px_line_height_divides_by_font_size(self) -> None:
        self.assertAlmostEqual(line_height_ratio("16", "24px"), 1.5, places=2)

    def test_font_size_without_px_suffix_is_accepted(self) -> None:
        self.assertAlmostEqual(line_height_ratio("16", "1.5"), 1.5, places=2)

    def test_rem_and_em_use_the_root_font_size(self) -> None:
        self.assertAlmostEqual(line_height_ratio("1rem", "1.5rem"), 1.5, places=2)
        self.assertAlmostEqual(line_height_ratio("1rem", "24px"), 1.5, places=2)
        self.assertAlmostEqual(line_height_ratio("2em", "1.5rem"), 0.75, places=2)
        self.assertAlmostEqual(line_height_ratio("1.25rem", "1.4em"), 1.4, places=2)
        self.assertAlmostEqual(line_height_ratio("1rem", "30px", 20.0), 1.5, places=2)

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

    def test_nested_commas_do_not_split_fields(self) -> None:
        spec = SOURCE_EXPRESSION_ROWS[0][0]
        parsed = parse_step_spec(spec)
        self.assertEqual(parsed[0], "display-hero")
        self.assertIn("clamp(min(2.375rem", parsed[1])
        self.assertEqual(parsed[2], ".94")
        self.assertEqual(parsed[3], "heading")

    def test_empty_expression_field_rejected(self) -> None:
        with self.assertRaises(TypeScaleError):
            parse_step_spec("Body,,1.5")

    def test_unbalanced_expression_rejected_before_calculation(self) -> None:
        with self.assertRaises(TypeScaleError):
            parse_step_spec("Body,clamp(1rem,2rem,3rem,.5")

    def test_excess_nesting_rejected(self) -> None:
        font_size = "clamp(" * 17 + "1px" + ")" * 17
        with self.assertRaises(TypeScaleError):
            parse_step_spec(f"Body,{font_size},1.5")

    def test_oversized_specification_rejected(self) -> None:
        spec = "Body,16px,1.5," + "x" * 2048
        with self.assertRaises(TypeScaleError):
            parse_step_spec(spec)


class SourceExpressionTests(unittest.TestCase):
    def test_all_source_rows_keep_exact_fields_and_ratios(self) -> None:
        parsed_rows = [parse_step_spec(spec) for spec, _ in SOURCE_EXPRESSION_ROWS]
        for parsed, (spec, expected_ratio) in zip(parsed_rows, SOURCE_EXPRESSION_ROWS):
            with self.subTest(spec=spec):
                self.assertAlmostEqual(
                    line_height_ratio(parsed[1], parsed[2]),
                    expected_ratio,
                    places=12,
                )

    def test_source_rows_use_expected_statuses(self) -> None:
        lines, all_pass = check_steps([spec for spec, _ in SOURCE_EXPRESSION_ROWS])
        self.assertFalse(all_pass)
        self.assertEqual(lines[0], "FAIL display-hero (heading): "
                                   "line-height ratio 0.94, needs >= 1.10")
        self.assertEqual(lines[-1], "PASS intro (text): line-height ratio 1.50, "
                                    "needs >= 1.50")
        self.assertEqual(main(["--step", SOURCE_EXPRESSION_ROWS[0][0]]), 1)
        self.assertEqual(main(["--step", SOURCE_EXPRESSION_ROWS[-1][0]]), 0)

    def test_expression_diagnostic_preserves_original_values(self) -> None:
        output = StringIO()
        spec = SOURCE_EXPRESSION_ROWS[0][0]
        with redirect_stdout(output):
            result = main(["--step", spec])
        self.assertEqual(result, 1)
        self.assertIn("display-hero", output.getvalue())
        self.assertIn("0.94", output.getvalue())

    def test_absolute_leading_with_expression_fails_closed(self) -> None:
        font_size = "clamp(1rem, calc(2cqi * (1rem / 16px)), 2rem)"
        with self.assertRaises(TypeScaleError):
            line_height_ratio(font_size, "24px")
        with self.assertRaises(TypeScaleError):
            line_height_ratio(font_size, "1.5rem")

    def test_expression_unitless_and_em_leading_supported(self) -> None:
        font_size = "clamp(1rem, calc(2cqi * (1rem / 16px)), 2rem)"
        self.assertAlmostEqual(line_height_ratio(font_size, "1.5"), 1.5, places=12)
        self.assertAlmostEqual(line_height_ratio(font_size, "1.2em"), 1.2, places=12)

    def test_invalid_css_algebra_rejected(self) -> None:
        invalid_font_sizes = [
            "min(1px, unknown(1px))",
            "clamp(1, 1px, 2px)",
            "calc(1px * 1px)",
            "calc(1px / 0px)",
            "calc(1px / 2cqi)",
            "clamp(1px)",
            "clamp(1px, 2px",
        ]
        for value in invalid_font_sizes:
            with self.subTest(value=value):
                with self.assertRaises(TypeScaleError):
                    line_height_ratio(value, "1.5")

    def test_nonfinite_and_nonpositive_expression_numbers_rejected(self) -> None:
        for value in ("calc(NaN)", "calc(Infinity)", "calc(0px)", "calc(-1px)"):
            with self.subTest(value=value):
                with self.assertRaises(TypeScaleError):
                    line_height_ratio(value, "1.5")

    def test_nonfinite_scalars_and_root_rejected(self) -> None:
        with self.assertRaises(TypeScaleError):
            line_height_ratio("NaN", "1.5")
        with self.assertRaises(TypeScaleError):
            line_height_ratio("Infinity", "1.5")
        with self.assertRaises(TypeScaleError):
            line_height_ratio("16px", "NaN")
        with self.assertRaises(TypeScaleError):
            line_height_ratio("16px", "-Infinity")
        with self.assertRaises(TypeScaleError):
            line_height_ratio("16px", "1.5", math.nan)

    def test_parent_fail_open_cases_rejected(self) -> None:
        parent_cases = [
            ("calc(1px+2px)", 16.0),
            ("calc(1px - 1px)", 16.0),
            ("calc(1px / (1 - 1))", 16.0),
            ("1e308rem", 16.0),
            ("calc(1px)", math.nan),
        ]
        for font_size, root_size in parent_cases:
            with self.subTest(font_size=font_size, root_size=root_size):
                with self.assertRaises(TypeScaleError):
                    line_height_ratio(font_size, "1.5", root_size)

    def test_invalid_css_operator_spacing_rejected(self) -> None:
        for value in ("calc(1px+2px)", "calc(1px -2px)", "calc(1px- 2px)"):
            with self.subTest(value=value):
                with self.assertRaises(TypeScaleError):
                    line_height_ratio(value, "1.5")

    def test_unary_chains_rejected(self) -> None:
        for value in ("calc(++1px)", "calc(--1px)", "calc(+-1px)"):
            with self.subTest(value=value):
                with self.assertRaises(TypeScaleError):
                    line_height_ratio(value, "1.5")

    def test_provable_zero_overflow_and_unknown_shape_rejected(self) -> None:
        with self.assertRaises(TypeScaleError):
            line_height_ratio("calc(1cqi * (1e-308px / 1e308px))", "1.5")
        with self.assertRaises(TypeScaleError):
            line_height_ratio("calc(1cqi * (1e308rem / .1px))", "1.5")
        with self.assertRaises(TypeScaleError):
            line_height_ratio("calc(1px - 2px)", "1.5")
        with self.assertRaises(TypeScaleError):
            line_height_ratio("1e-308px", "1e308px")
        with self.assertRaises(TypeScaleError):
            line_height_ratio("calc(1px)", "1.5", math.inf)

    def test_direct_expression_length_limit_rejected(self) -> None:
        with self.assertRaises(TypeScaleError):
            line_height_ratio("calc(" + "1px" * 700 + ")", "1.5")


class MainCliTests(unittest.TestCase):
    def test_body_text_at_house_floor_passes(self) -> None:
        self.assertEqual(main(["--step", "Body,16px,1.5,text"]), 0)

    def test_body_text_below_house_floor_fails(self) -> None:
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

    def test_text_floor_is_labeled_as_house_floor_not_wcag(self) -> None:
        import check_type_scale

        doc = check_type_scale.__doc__ or ""
        self.assertIn("house readability floors, not WCAG AA", doc)
        self.assertNotIn("WCAG 1.4.12 minimum", check_type_scale.build_parser().format_help())

    def test_malformed_size_exits_two(self) -> None:
        self.assertEqual(main(["--step", "Body,large,1.5,text"]), 2)
        self.assertEqual(main(["--step", "Body,1vw,1.5,text"]), 2)

    def test_rem_steps_and_declared_root_font_size(self) -> None:
        self.assertEqual(main(["--step", "Body,1rem,1.5,text"]), 0)
        self.assertEqual(main(["--step", "Body,1rem,1.25rem,text"]), 1)
        self.assertEqual(
            main(["--root-font-size", "20px", "--step", "Body,1rem,30px,text"]), 0
        )
        self.assertEqual(main(["--root-font-size", "big", "--step", "Body,1rem,1.5"]), 2)

    def test_malformed_step_spec_exits_two(self) -> None:
        self.assertEqual(main(["--step", "Body,16px"]), 2)


if __name__ == "__main__":
    unittest.main()
