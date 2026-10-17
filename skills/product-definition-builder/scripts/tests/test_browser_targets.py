from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from browser_targets import (  # noqa: E402
    ENGINE_ORDER,
    BrowserTargets,
    engine_label,
    parse_browser_targets,
    requires_cross_browser,
)


SECTION_HEADING = "### Browser Targets"
CONTRACT_MARKER = "Browser targets contract: browser-targets/1"
TABLE_HEADER = "| Release target | Browser | Platform | Smoke TEST ID |"
TABLE_DELIMITER = "| --- | --- | --- | --- |"
THREE_ROW_BODY = "\n".join(
    [
        TABLE_HEADER,
        TABLE_DELIMITER,
        "| web-production | chrome | desktop | TEST-WEB-SMOKE |",
        "| web-production | firefox | desktop | TEST-WEB-SMOKE |",
        "| web-production | safari | ios | TEST-WEB-SMOKE |",
    ]
)
THREE_ROW_PRD = f"# PRD: Fixture\n\n{SECTION_HEADING}\n\n{CONTRACT_MARKER}\n\n{THREE_ROW_BODY}\n"
DECLARED_JSON = '{"declared":true,"engines":["chromium","firefox","webkit"]}'


def declaration(body: str, *, heading: bool = True, marker: bool = True) -> str:
    parts = ["# PRD: Fixture"]
    if heading:
        parts.append(SECTION_HEADING)
    if marker:
        parts.append(CONTRACT_MARKER)
    parts.append(body)
    return "\n\n".join(parts) + "\n"


class BrowserTargetParsingTests(unittest.TestCase):
    def assertErrors(self, prd_text: str, *fragments: str) -> BrowserTargets:
        result = parse_browser_targets(prd_text)
        self.assertTrue(result.declared)
        self.assertEqual((), result.targets)
        self.assertEqual((), result.engines)
        self.assertEqual((), result.coverage)
        for fragment in fragments:
            self.assertTrue(
                any(fragment in error for error in result.errors),
                f"expected {fragment!r} in {result.errors}",
            )
        return result

    def test_undeclared_prd_defaults_to_chromium_without_errors(self):
        result = parse_browser_targets("# PRD: Fixture\n\nSome prose.\n")
        self.assertFalse(result.declared)
        self.assertEqual(("chromium",), result.engines)
        self.assertEqual((), result.targets)
        self.assertEqual((), result.coverage)
        self.assertEqual((), result.errors)

    def test_three_row_example_declares_three_engines_and_coverage(self):
        result = parse_browser_targets(THREE_ROW_PRD)
        self.assertTrue(result.declared)
        self.assertEqual((), result.errors)
        self.assertEqual(("chromium", "firefox", "webkit"), result.engines)
        self.assertEqual(3, len(result.targets))
        self.assertEqual(
            (
                ("web-production", "TEST-WEB-SMOKE", "chromium"),
                ("web-production", "TEST-WEB-SMOKE", "firefox"),
                ("web-production", "TEST-WEB-SMOKE", "webkit"),
            ),
            result.coverage,
        )
        self.assertEqual(
            (("web-production", "chrome", "desktop"),),
            tuple(
                (target.release_target, target.browser, target.platform)
                for target in result.targets
                if target.browser == "chrome"
            ),
        )

    def test_chrome_and_edge_collapse_to_one_chromium_coverage_tuple(self):
        prd = declaration(
            "\n".join(
                [
                    TABLE_HEADER,
                    TABLE_DELIMITER,
                    "| web-production | chrome | desktop | TEST-WEB-SMOKE |",
                    "| web-production | edge | desktop | TEST-WEB-SMOKE |",
                ]
            )
        )
        result = parse_browser_targets(prd)
        self.assertTrue(result.declared)
        self.assertEqual((), result.errors)
        self.assertEqual(("chromium",), result.engines)
        self.assertEqual(2, len(result.targets))
        self.assertEqual(
            (("web-production", "TEST-WEB-SMOKE", "chromium"),), result.coverage
        )

    def test_coverage_is_sorted_by_release_target_engine_then_test_id(self):
        prd = declaration(
            "\n".join(
                [
                    TABLE_HEADER,
                    TABLE_DELIMITER,
                    "| web-production | safari | ios | TEST-WEB-B |",
                    "| web-beta | chrome | desktop | TEST-WEB-A |",
                    "| web-production | chrome | desktop | TEST-WEB-A |",
                ]
            )
        )
        result = parse_browser_targets(prd)
        self.assertEqual(
            (
                ("web-beta", "TEST-WEB-A", "chromium"),
                ("web-production", "TEST-WEB-A", "chromium"),
                ("web-production", "TEST-WEB-B", "webkit"),
            ),
            result.coverage,
        )

    def test_heading_without_marker_is_an_error(self):
        self.assertErrors(
            declaration(THREE_ROW_BODY, marker=False), "expected exactly one"
        )

    def test_marker_without_heading_is_an_error(self):
        self.assertErrors(
            declaration(THREE_ROW_BODY, heading=False), "expected exactly one"
        )

    def test_more_than_one_heading_is_an_error(self):
        prd = declaration(THREE_ROW_BODY) + f"\n{SECTION_HEADING}\n\nLater prose.\n"
        self.assertErrors(prd, f"expected exactly one '{SECTION_HEADING}' heading")

    def test_more_than_one_marker_is_an_error(self):
        prd = declaration(THREE_ROW_BODY) + f"\n{CONTRACT_MARKER}\n"
        self.assertErrors(prd, f"expected exactly one '{CONTRACT_MARKER}' marker")

    def test_marker_outside_the_section_is_an_error(self):
        prd = (
            f"# PRD: Fixture\n\n{CONTRACT_MARKER}\n\n"
            f"{SECTION_HEADING}\n\n{THREE_ROW_BODY}\n"
        )
        self.assertErrors(prd, "must appear inside the")

    def test_marker_after_the_table_is_an_error(self):
        prd = declaration(f"{THREE_ROW_BODY}\n\n{CONTRACT_MARKER}", marker=False)
        self.assertErrors(prd, "must appear before the targets table")

    def test_missing_table_header_is_an_error(self):
        self.assertErrors(declaration("No table at all."), "missing table header")

    def test_wrong_table_header_is_an_error(self):
        self.assertErrors(
            declaration(
                "\n".join(
                    [
                        "| Release target | Browser | Platform | Test ID |",
                        TABLE_DELIMITER,
                        "| web-production | chrome | desktop | TEST-WEB-SMOKE |",
                    ]
                )
            ),
            "missing table header",
        )

    def test_table_without_data_rows_is_an_error(self):
        self.assertErrors(
            declaration(f"{TABLE_HEADER}\n{TABLE_DELIMITER}"), "no data rows"
        )

    def test_row_with_wrong_cell_count_is_an_error(self):
        self.assertErrors(
            declaration(
                "\n".join(
                    [
                        TABLE_HEADER,
                        TABLE_DELIMITER,
                        "| web-production | chrome | desktop |",
                    ]
                )
            ),
            "has 3 cells, expected 4",
        )

    def test_duplicate_release_target_browser_platform_row_is_an_error(self):
        self.assertErrors(
            declaration(
                "\n".join(
                    [
                        TABLE_HEADER,
                        TABLE_DELIMITER,
                        "| web-production | chrome | desktop | TEST-WEB-SMOKE |",
                        "| web-production | chrome | desktop | TEST-WEB-SMOKE |",
                    ]
                )
            ),
            "duplicate target row",
        )

    def test_release_target_must_be_lower_kebab_case(self):
        self.assertErrors(
            declaration(
                "\n".join(
                    [
                        TABLE_HEADER,
                        TABLE_DELIMITER,
                        "| Web Production | chrome | desktop | TEST-WEB-SMOKE |",
                    ]
                )
            ),
            "must be lowercase kebab-case",
        )

    def test_smoke_test_id_must_match_the_contract_pattern(self):
        self.assertErrors(
            declaration(
                "\n".join(
                    [
                        TABLE_HEADER,
                        TABLE_DELIMITER,
                        "| web-production | chrome | desktop | test-web-smoke |",
                    ]
                )
            ),
            "Smoke TEST ID 'test-web-smoke' must match TEST-[A-Z0-9-]+",
        )

    def test_unknown_browser_is_an_error(self):
        self.assertErrors(
            declaration(
                "\n".join(
                    [
                        TABLE_HEADER,
                        TABLE_DELIMITER,
                        "| web-production | opera | desktop | TEST-WEB-SMOKE |",
                    ]
                )
            ),
            "unknown browser 'opera'",
        )

    def test_unsupported_browser_platform_pair_is_an_error(self):
        self.assertErrors(
            declaration(
                "\n".join(
                    [
                        TABLE_HEADER,
                        TABLE_DELIMITER,
                        "| web-production | chrome | ios | TEST-WEB-SMOKE |",
                    ]
                )
            ),
            "unsupported browser and platform pair 'chrome' on 'ios'",
        )

    def test_every_android_and_macos_pair_maps_to_expected_engines(self):
        prd = declaration(
            "\n".join(
                [
                    TABLE_HEADER,
                    TABLE_DELIMITER,
                    "| web-android | chrome | android | TEST-WEB-SMOKE |",
                    "| web-macos | safari | macos | TEST-WEB-SMOKE |",
                ]
            )
        )
        result = parse_browser_targets(prd)
        self.assertEqual((), result.errors)
        self.assertEqual(("chromium", "webkit"), result.engines)

    def test_declaration_inside_fenced_code_block_is_ignored(self):
        prd = f"# PRD: Fixture\n\n```\n{SECTION_HEADING}\n{CONTRACT_MARKER}\n{THREE_ROW_BODY}\n```\n"
        result = parse_browser_targets(prd)
        self.assertFalse(result.declared)
        self.assertEqual(("chromium",), result.engines)
        self.assertEqual((), result.errors)

    def test_declaration_inside_html_comment_is_ignored(self):
        prd = (
            f"# PRD: Fixture\n\n<!--\n{SECTION_HEADING}\n{CONTRACT_MARKER}\n"
            f"{THREE_ROW_BODY}\n-->\n"
        )
        result = parse_browser_targets(prd)
        self.assertFalse(result.declared)
        self.assertEqual(("chromium",), result.engines)
        self.assertEqual((), result.errors)

    def test_level_four_heading_does_not_end_the_section(self):
        prd = declaration(
            "#### Notes\n\nSmoke runs follow the release checklist.\n\n" + THREE_ROW_BODY
        )
        result = parse_browser_targets(prd)
        self.assertTrue(result.declared)
        self.assertEqual(("chromium", "firefox", "webkit"), result.engines)

    def test_level_two_heading_ends_the_section(self):
        prd = (
            declaration(THREE_ROW_BODY)
            + "\n## Next Section\n\n"
            + "\n".join(
                [
                    TABLE_HEADER,
                    TABLE_DELIMITER,
                    "| web-production | opera | desktop | TEST-WEB-SMOKE |",
                ]
            )
            + "\n"
        )
        result = parse_browser_targets(prd)
        self.assertTrue(result.declared)
        self.assertEqual(("chromium", "firefox", "webkit"), result.engines)


class BrowserTargetHelperTests(unittest.TestCase):
    def test_engine_order_and_labels(self):
        self.assertEqual(("chromium", "firefox", "webkit"), ENGINE_ORDER)
        self.assertEqual("Chromium engine", engine_label("chromium"))
        self.assertEqual("Playwright Firefox", engine_label("firefox"))
        self.assertEqual("WebKit approximation of Safari", engine_label("webkit"))

    def test_requires_cross_browser(self):
        self.assertFalse(requires_cross_browser(parse_browser_targets("# PRD\n")))
        self.assertFalse(
            requires_cross_browser(
                parse_browser_targets(
                    declaration(
                        "\n".join(
                            [
                                TABLE_HEADER,
                                TABLE_DELIMITER,
                                "| web-production | chrome | desktop | TEST-WEB-SMOKE |",
                            ]
                        )
                    )
                )
            )
        )
        self.assertTrue(requires_cross_browser(parse_browser_targets(THREE_ROW_PRD)))
        self.assertFalse(
            requires_cross_browser(
                parse_browser_targets(declaration(THREE_ROW_BODY, marker=False))
            )
        )


class BrowserTargetsCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_cli(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "browser_targets.py"), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
            cwd=cwd,
        )

    def test_cli_prints_compact_json_and_exits_zero(self):
        prd = self.root / "PRD.md"
        prd.write_text(THREE_ROW_PRD, encoding="utf-8")
        result = self.run_cli("--prd", str(prd))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(DECLARED_JSON, result.stdout.strip())

    def test_cli_undeclared_prd_prints_default_chromium_engines(self):
        prd = self.root / "PRD.md"
        prd.write_text("# PRD: Fixture\n", encoding="utf-8")
        result = self.run_cli("--prd", str(prd))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('{"declared":false,"engines":["chromium"]}', result.stdout.strip())

    def test_cli_appends_github_output_lines(self):
        prd = self.root / "PRD.md"
        prd.write_text(THREE_ROW_PRD, encoding="utf-8")
        output = self.root / "github_output.txt"
        result = self.run_cli("--prd", str(prd), "--github-output", str(output))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            "declared=true\nengines=[\"chromium\",\"firefox\",\"webkit\"]\n",
            output.read_text(encoding="utf-8"),
        )

        prd.write_text("# PRD: Fixture\n", encoding="utf-8")
        output.write_text("", encoding="utf-8")
        result = self.run_cli("--prd", str(prd), "--github-output", str(output))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            "declared=false\nengines=[\"chromium\"]\n",
            output.read_text(encoding="utf-8"),
        )

    def test_cli_reports_declaration_errors_and_exits_one(self):
        prd = self.root / "PRD.md"
        prd.write_text(declaration(THREE_ROW_BODY, marker=False), encoding="utf-8")
        result = self.run_cli("--prd", str(prd))
        self.assertEqual(1, result.returncode)
        self.assertIn("expected exactly one", result.stderr)
        self.assertEqual("", result.stdout)

    def test_cli_reports_unreadable_prd_and_exits_two(self):
        missing = self.root / "missing.md"
        result = self.run_cli("--prd", str(missing))
        self.assertEqual(2, result.returncode)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("cannot read", result.stderr)

    def test_cli_runs_from_a_copy_of_the_two_scripts_alone(self):
        portable = self.root / "portable"
        portable.mkdir()
        for name in ("browser_targets.py", "markdown_contract.py"):
            shutil.copyfile(SCRIPTS_DIR / name, portable / name)
        prd = portable / "PRD.md"
        prd.write_text(THREE_ROW_PRD, encoding="utf-8")
        output = portable / "github_output.txt"
        result = self.run_cli(
            "--prd", str(prd), "--github-output", str(output), cwd=portable
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(DECLARED_JSON, result.stdout.strip())
        self.assertEqual(
            "declared=true\nengines=[\"chromium\",\"firefox\",\"webkit\"]\n",
            output.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
