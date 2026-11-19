"""The UI review matrix and repair-loop rules are written once, in the rubric."""

import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
RUBRIC = "references/ui-grading-rubric.md"
POINTERS = ("references/ui-design-pass.md", "references/stages/ui-design.md")


def read(relative):
    return (SKILL_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def section(text, heading):
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


class ReviewMatrixDocsTests(unittest.TestCase):
    def test_sampling_rule_lives_in_the_rubric_axes_and_is_only_pointed_at(self):
        axes = section(read(RUBRIC), "## First-Wave Audit Axes")
        for phrase in (
            "every non-`n/a`, non-derived state",
            "A derived state (PRD `derivedStates`) is captured once, at its surface's smallest responsive target",
            "its densest non-derived state, each at the smallest and largest approved target",
            "Run reduced motion only on pages with a motion region or a required motion intent",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, axes)
        for source in POINTERS:
            with self.subTest(source=source):
                text = read(source)
                self.assertIn("ui-grading-rubric.md#first-wave-audit-axes", text)
                self.assertNotIn("densest", text)
                self.assertNotIn("smallest and largest", text)

    def test_repair_loop_is_a_closure_check_with_one_fix_exchange(self):
        rubric = read(RUBRIC)
        scope = section(rubric, "## Repair Re-review Scope")
        for phrase in (
            "closure check, not a second search",
            "Repair gate:",
            "an after-capture for every ledger row",
            "one verdict per ledger row",
            "a render fingerprint does not see behaviour",
            "starts no fresh critique or audit of unchanged pages",
            "late finding for the owner's follow-up list",
            "[Render fingerprint carry-forward]",
            "[Diff-first re-review]",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope)
        for gone in ("scoped re-review", "two scoped", "isolated repair", "Cap:", "next-round advisory",
                     "Run Impeccable critique and audit again"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, rubric)
        for source in POINTERS:
            with self.subTest(source=source):
                self.assertIn("ui-grading-rubric.md#repair-re-review-scope", read(source))

    def test_budget_table_is_stated_once_and_the_re_review_continues_the_wave(self):
        rubric = read(RUBRIC)
        budget = section(rubric, "## Review Budget")
        for row in ("| Full matrix captures per candidate | 1 |", "| Pilot diagnosis (pilot pages only) | 1 |",
                    "| Independent reviews of the package | 2 |", "| Fix exchanges | 1 |",
                    "| Evidence-only rounds | 0 |"):
            with self.subTest(row=row):
                self.assertEqual(1, rubric.count(row))
                self.assertIn(row, budget)
        for phrase in ("leaves the candidate `blocked`", "starts a named new revision cycle or stops",
                       "No third review, whole-HiFi re-grade, or owner-granted extra round exists inside a cycle"):
            self.assertIn(phrase, budget)
        capability = section(rubric, "## Capability And Authorization")
        self.assertIn("continued in their sessions when the host can continue an agent", capability)
        self.assertIn("a fresh reviewer gets the re-review packet", capability)

    def test_block_proof_is_defined_once_and_linked(self):
        rubric = read(RUBRIC)
        proof = section(rubric, "### Block Proof")
        self.assertEqual(1, rubric.count("A finding blocks only with all three"))
        for part in ("a reproduced failure with its capture",
                     "the frozen requirement, approved UI decision or rubric block rule it breaks",
                     "observable closure criteria", "must name at least one such finding"):
            self.assertIn(part, proof)
        self.assertGreaterEqual(rubric.count("(#block-proof)"), 3)

    def test_capture_proof_and_return_check_rules(self):
        rubric = read(RUBRIC)
        capability = section(rubric, "## Capability And Authorization")
        for phrase in ("Pilot diagnosis:", "return findings only", "It has no receipts and no score gate",
                       "Reviewers never run the matrix driver", "equal the frozen candidate",
                       "builds the browser receipt from that output with `review_evidence.py`",
                       "`a11y` measurements and the author's dispositions"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, capability)
        evidence = read("references/review-evidence.md")
        self.assertEqual(1, evidence.count("## Return Check"))
        returns = section(evidence, "## Return Check")
        for phrase in ("checks the packet's obligation list against the output", "to the same reviewer session",
                       "No evidence-only, receipt-only or inspection-completion round exists after a verdict"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, returns)
        self.assertIn("nobody captures those bytes again", evidence)
        self.assertIn("A candidate gets one full matrix capture", read("references/review-workflow.md"))
        self.assertIn("one repair batch of the kit and composition approach", read("references/review-workflow.md"))

    def test_wave_is_two_reviewers_and_never_split_for_size_or_time(self):
        rubric = read(RUBRIC)
        capability = section(rubric, "## Capability And Authorization")
        self.assertIn("The wave is exactly two fresh reviewers, whatever the package size", capability)
        self.assertIn("never splits the wave into page-group calls and never adds a grader", capability)
        self.assertIn("a reviewer who needs longer gets a longer deadline", capability)
        self.assertNotIn("Unless agent policy sets another topology", rubric)
        self.assertNotIn("smaller scoped calls", rubric)
        self.assertIn("the same reviewer finishes it with a longer deadline", section(rubric, "## Reporting And Reconciliation"))
        self.assertNotIn("page group", read("references/stages/ui-design.md"))

    def test_inspection_set_is_the_reviewers_complete_visual_coverage(self):
        rubric = read(RUBRIC)
        procedure = rubric.split("### Browser Inspection Procedure", 1)[1].split("\n### ", 1)[0]
        for phrase in (
            "checks every capture by machine: the DOM geometry scan, console errors and the `--measure-a11y` measurements",
            "- each page at its smallest approved target, in its default state;",
            "- every case those machine results flag; and",
            "- the stress-axis sample of [First-Wave Audit Axes](#first-wave-audit-axes).",
            "it does not open every capture",
            "Skipping any case of the set is not coverage",
            "MISSING/BLOCKED, never PASS",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, procedure)
        self.assertNotIn("Render every required base-matrix case", rubric)
        self.assertNotIn("in the retained all-screens HTML", rubric)
        self.assertEqual(1, rubric.count("MISSING/BLOCKED"))
        for dimension in ("- `H2 Layout safety`:", "- `H4 Responsive and edge states`:"):
            line = rubric.split(dimension, 1)[1].split("\n", 1)[0]
            with self.subTest(dimension=dimension):
                self.assertIn("(#browser-inspection-procedure)", line)
        evidence = read("references/review-evidence.md")
        self.assertNotIn("inspect every case", evidence)
        self.assertIn("ui-grading-rubric.md#browser-inspection-procedure", evidence)


if __name__ == "__main__":
    unittest.main()
