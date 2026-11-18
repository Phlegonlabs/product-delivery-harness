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

    def test_growth_review_admits_demand_research_and_routes_to_the_template(self) -> None:
        entry = (GROWTH / "SKILL.md").read_text(encoding="utf-8")
        stage = (GROWTH / "references/stages/growth-review.md").read_text(encoding="utf-8")
        self.assertIn("assets/templates/KEYWORD_MAP.template.md", entry)
        self.assertIn("references/stages/growth-review.md#demand-research", entry)
        self.assertIn("- `demand_research`:", stage)
        self.assertRegex(stage, r"(?m)^## Demand Research$")
        self.assertIn("docs/product/keyword-map.md", stage)
        self.assertIn("a required dependency of that requested skill workflow", entry)

    def test_readback_returns_two_lists_and_prelaunch_starts_from_the_map(self) -> None:
        method = (GROWTH / "references/review-method.md").read_text(encoding="utf-8")
        stage = (GROWTH / "references/stages/growth-review.md").read_text(encoding="utf-8")
        self.assertRegex(method, r"(?m)^## Keyword Map Readback$")
        self.assertIn("Content-field rewrites.", method)
        self.assertIn("Structural candidates.", method)
        self.assertIn("review-method.md#keyword-map-readback", stage)
        self.assertIn("do not plan the clusters again", stage)
        self.assertIn("every surface outside the map are still planned", stage)


if __name__ == "__main__":
    unittest.main()
