#!/usr/bin/env python3
"""The growth-review keyword map template keeps the five fixed sections."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[3]
GROWTH = SKILLS_ROOT / "growth-review"
TEMPLATE = GROWTH / "assets/templates/KEYWORD_MAP.template.md"
SECTIONS = ["Scope", "Clusters", "Not pursued", "Content fields", "Change log"]


class KeywordMapTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = TEMPLATE.read_text(encoding="utf-8")

    def test_has_exactly_the_five_sections_in_order(self) -> None:
        headings = re.findall(r"^## (.+)$", self.text, re.MULTILINE)
        self.assertEqual(headings, SECTIONS)

    def test_cluster_table_carries_the_fields_of_one_row(self) -> None:
        header = next(
            line for line in self.text.splitlines() if line.startswith("| ID |")
        )
        for column in (
            "Cluster", "Intent", "Queries", "Demand evidence",
            "Ranks now", "Mapped page", "Priority",
        ):
            self.assertIn(column, header)

    def test_example_rows_are_marked_and_use_a_stable_kw_id(self) -> None:
        rows = [line for line in self.text.splitlines() if "(example)" in line]
        self.assertEqual(len(rows), 4)
        self.assertRegex(rows[0], r"\| KW-001 \(example\) \|")
        table_ids = re.findall(r"^\| (KW-\d+)", self.text, re.MULTILINE)
        self.assertEqual(table_ids, ["KW-001"])

    def test_content_fields_and_change_log_columns(self) -> None:
        for column in ("Current title", "Title limit", "Current meta description",
                       "Description limit", "Serves"):
            self.assertIn(column, self.text)
        for column in ("Date", "KW", "Field", "Before", "After", "Evidence", "Readback"):
            self.assertIn(f"| {column} ", self.text)

    def test_uses_the_existing_evidence_labels_only(self) -> None:
        self.assertIn("observed, estimated or hypothesis", self.text)
        self.assertNotIn("measured", self.text)


if __name__ == "__main__":
    unittest.main()
