#!/usr/bin/env python3
"""Focused tests for the read-only approved-stack option-map renderer."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import render_stack_option_map  # noqa: E402
from check_product_package import (  # noqa: E402
    _parse_approved_option_map,
    validate_texts,
)
from contract_utils import finalize_approval_digests  # noqa: E402
from test_product_package_checker import (  # noqa: E402
    commercial_option_package,
    release_architecture,
    strictize_approved_package,
    valid_prd,
    valid_stack,
)


class StackOptionMapTests(unittest.TestCase):
    def bind_generated_map(self) -> tuple[str, str, str]:
        prd, architecture, approved_stack = strictize_approved_package(
            valid_prd(), release_architecture(), valid_stack()
        )
        generated = render_stack_option_map.candidate_option_map(approved_stack)
        approved_stack = re.sub(
            r"- Approved option map:.*",
            f"- Approved option map: {generated}",
            approved_stack,
            count=1,
        )
        return finalize_approval_digests(prd, architecture, approved_stack)

    def test_generated_map_roundtrips_through_parser_and_checker(self) -> None:
        stack = valid_stack()
        generated = render_stack_option_map.candidate_option_map(stack)
        parsed, findings = _parse_approved_option_map(generated)
        self.assertEqual([], findings)
        self.assertEqual({"OPT-FE-01"}, set(parsed))

        prd, architecture, bound = self.bind_generated_map()
        self.assertEqual([], validate_texts(
            prd, architecture, bound, require_filled=True, require_approved=True,
        ))

    def test_multiple_commercial_maps_survive_commas_and_match_checker(self) -> None:
        _prd, _architecture, approved_stack = commercial_option_package()
        current_map = re.search(
            r"- Approved option map: (\|\|.+\|\|)", approved_stack
        ).group(1)
        self.assertEqual(
            current_map,
            render_stack_option_map.candidate_option_map(approved_stack),
        )
        self.assertIn(", ", current_map)

    def test_recommended_and_rejected_options_are_not_approved(self) -> None:
        stack = valid_stack()
        generated = render_stack_option_map.candidate_option_map(stack)
        self.assertIn("OPT-FE-01", generated)
        self.assertNotIn("OPT-FE-02", generated)

        unapproved = stack.replace(
            "| OPT-FE-01 | Frontend | React Router bundle | Interactive app "
            "| Team owns source | approved |",
            "| OPT-FE-01 | Frontend | React Router bundle | Interactive app "
            "| Team owns source | recommended |",
            1,
        )
        with self.assertRaisesRegex(
            render_stack_option_map.OptionMapError, "cannot mint an approval"
        ):
            render_stack_option_map.candidate_option_map(unapproved)

    def test_selected_and_required_rows_are_included_without_status_changes(self) -> None:
        stack = valid_stack().replace(
            "| Language | TypeScript | Approved |",
            "| Language | TypeScript | Selected |",
            1,
        ).replace(
            "| Framework | React Router | Approved |",
            "| Framework | React Router | Required |",
            1,
        )
        generated = render_stack_option_map.candidate_option_map(stack)
        parsed, findings = _parse_approved_option_map(generated)
        self.assertEqual([], findings)
        self.assertEqual("TypeScript", parsed["OPT-FE-01"]["language"])
        self.assertEqual("React Router", parsed["OPT-FE-01"]["framework"])

    def test_ambiguous_or_duplicate_rows_are_refused(self) -> None:
        duplicate_option = valid_stack().replace(
            "| OPT-FE-02 |",
            "| OPT-FE-01 |",
            1,
        )
        framework_row = (
            "| Framework | React Router | Approved | Owner decision | "
            "Fits the app | None |\n"
        )
        duplicate_layer = valid_stack().replace(
            framework_row,
            framework_row
            + "| framework | React Router | Approved | Owner decision | "
            "Fits the app | None |\n",
            1,
        )
        reserved_pair = valid_stack().replace(
            framework_row,
            "| Framework | React;Router | Approved | Owner decision | "
            "Fits the app | None |\n",
            1,
        )
        reserved_arrow = valid_stack().replace(
            framework_row,
            "| Framework | React=>Router | Approved | Owner decision | "
            "Fits the app | None |\n",
            1,
        )
        cases = {
            duplicate_option: "duplicate option ID",
            duplicate_layer: "duplicate layer",
            reserved_pair: "reserved map separator",
            reserved_arrow: "reserved map separator",
        }
        for candidate, expected in cases.items():
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(
                    render_stack_option_map.OptionMapError, expected
                ):
                    render_stack_option_map.candidate_option_map(candidate)

        with self.assertRaisesRegex(
            render_stack_option_map.OptionMapError, "reserved map separator"
        ):
            render_stack_option_map._reject_reserved("Alpha||Beta", label="selection")

    def test_rejects_duplicate_sections_tables_and_unresolved_layers(self) -> None:
        stack = valid_stack()
        cases = [
            stack + "\n## Frontend Technology Decision\nDuplicate content\n",
            stack + "\n### Coherent Options Presented\n| Option ID | Area | Complete bundle | Best fit | Tradeoffs / ownership | Disposition |\n| --- | --- | --- | --- | --- | --- |\n",
            stack.replace("| Framework | React Router | Approved |", "| Framework | React Router | Recommended |", 1),
            stack.replace("| OPT-FE-01 |", "| OPT-FE-01 extra |", 1),
        ]
        for candidate in cases:
            with self.subTest(candidate=candidate[-100:]):
                with self.assertRaises(render_stack_option_map.OptionMapError):
                    render_stack_option_map.candidate_option_map(candidate)

    def test_cli_reads_only_and_defaults_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "stack-decisions.md"
            original = valid_stack()
            source.write_text(original, encoding="utf-8", newline="\n")

            result = render_stack_option_map.main(["--stack-decisions", str(source)])

            self.assertEqual(0, result)
            self.assertEqual(original, source.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
