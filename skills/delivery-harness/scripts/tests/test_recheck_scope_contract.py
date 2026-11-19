#!/usr/bin/env python3
"""Re-reviews close the repair; they do not search again.

A re-check, a scoped isolated-repair review and the UI closure re-review judge
the earlier findings and the repaired content. A defect already present in
unchanged content is a note for the owner's next round. Only a regression the
repair caused or a high or critical security finding blocks. A visual review
is never split by page group.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[3]
GATES = "delivery-harness/references/verification-gates.md"
RUBRIC = "ui-design-builder/references/ui-grading-rubric.md"
NOTE_RULE = (
    "A defect it notices in content the repair did not change, already"
    " present at the prior reviewed head, is a note for the next round, which"
    " the owner decides on: it never blocks this round and never joins this"
    " round's repair."
)
EXCEPTIONS = (
    "Two kinds of new finding still block: a regression the repair caused, in changed"
    " content or in a consumer of a changed source; and a validated high or"
    " critical security finding under `security-review.md`."
)


def read(relative: str) -> str:
    return (SKILLS_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def paragraph(text: str, lead: str) -> str:
    start = text.index(lead)
    end = text.find("\n\n", start)
    return text[start:] if end == -1 else text[start:end]


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
    def test_pre_existing_defect_in_a_re_check_is_a_note(self) -> None:
        scope = paragraph(read(GATES), "Re-check scope.")
        self.assertIn("judges only the repair range and its direct consumers", scope)
        self.assertIn(NOTE_RULE, scope)
        self.assertNotIn("anything else is a note unless", scope)

    def test_the_two_exceptions_are_stated_once(self) -> None:
        scope = paragraph(read(GATES), "Re-check scope.")
        self.assertIn(EXCEPTIONS, scope)
        holders = [
            path.relative_to(SKILLS_ROOT).as_posix()
            for path in reference_docs()
            if "a regression the repair caused, in changed content"
            in path.read_text(encoding="utf-8")
        ]
        self.assertEqual([GATES], holders)

    def test_every_re_review_points_to_the_one_scope(self) -> None:
        gates = read(GATES)
        scope = paragraph(gates, "Re-check scope.")
        self.assertIn(
            "The same scope binds every scoped review in the Isolated Repair"
            " Protocol and the UI closure re-review",
            scope,
        )
        self.assertIn("(../../ui-design-builder/references/ui-grading-rubric.md#repair-re-review-scope)", scope)
        protocol = gates.split("## Isolated Repair Protocol", 1)[1].split("\n## ", 1)[0]
        self.assertIn("and judges them under Re-check scope above", protocol)
        self.assertIn("a new one that blocks under Re-check scope above", protocol)
        self.assertNotIn("newly found defect", gates)
        rubric = read(RUBRIC)
        self.assertIn(
            "under [Re-check scope](../../delivery-harness/references/verification-gates.md#review-topology)",
            rubric,
        )
        brief = read("delivery-harness/assets/templates/DIRECT_REVIEW_BRIEF.template.md")
        self.assertIn("under Re-check scope in `delivery-harness/references/verification-gates.md`", brief)
        self.assertNotIn("validated security finding or a correctness defect", brief)

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
