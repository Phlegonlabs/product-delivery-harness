#!/usr/bin/env python3
"""A visual review is never split by page group."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[3]
GATES = "delivery-harness/references/verification-gates.md"
RUBRIC = "ui-design-builder/references/ui-grading-rubric.md"


def read(relative: str) -> str:
    return (SKILLS_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def reference_docs() -> list[Path]:
    """Every current rule document; legacy pins and release notes are history."""

    return [
        path
        for path in sorted(SKILLS_ROOT.glob("*/**/*.md"))
        if "legacy" not in path.parts
        and path.name not in {"CHANGELOG.md"}
        and not path.name.startswith("README")
    ]


class RecheckScopeContractTests(unittest.TestCase):
    def test_no_visual_review_is_split_by_page_group(self) -> None:
        capability = read(RUBRIC).split("## Capability And Authorization", 1)[1].split("\n## ", 1)[0]
        self.assertIn("The wave is exactly two fresh reviewers, whatever the package size", capability)
        self.assertIn("never splits the wave into page-group calls and never adds a grader", capability)
        mentions = []
        for path in reference_docs():
            text = path.read_text(encoding="utf-8")
            for sentence in re.split(r"(?<=[.;])\s+", text):
                if re.search(r"page[ -]group", sentence):
                    mentions.append((path.relative_to(SKILLS_ROOT).as_posix(), sentence))
        self.assertGreaterEqual(len(mentions), 3)
        for source, sentence in mentions:
            with self.subTest(source=source, sentence=sentence[:80]):
                self.assertIn("never", sentence)
        self.assertNotIn("smaller scoped calls", read("delivery-harness/references/delegation-contract.md"))


if __name__ == "__main__":
    unittest.main()
