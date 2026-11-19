"""Approved research-backed messaging must keep current, specific support."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_claims import research_claim_findings


MESSAGING = "docs/gtm/MESSAGING.md"
ASSESSMENT = "docs/product/research-assessment.md"
STUDY = "docs/research/discovery/2026-11-18/DISCOVERY.md"

MESSAGE_TEXT = """# Messaging Record
## Proof Points
| # | Proof point | Source | Date |
| --- | --- | --- | --- |
| 1 | A separate unresolved idea | RA-002 | 2026-11-18 |
## Approved Public Claims
| Claim | Evidence | Check date |
| --- | --- | --- |
| C01: Three operators reconstructed enquiry status | RA-001 / S-01 | 2026-11-18 |
Owner approval source and approved revision: historical MSG-1.
## Claims Not Allowed
RA-002 is not validated.
## Change Log
| Revision | Date | Changed sections | Source of change |
| --- | --- | --- | --- |
| MSG-1 | 2026-11-18 | Initial approval | RA-001 |
"""

ASSESSMENT_TEXT = """# Research Assessment
## Findings
| RA ID | Finding | Confidence | Sources |
| --- | --- | --- | --- |
| RA-001 | 3 operators reconstructed enquiry status | sourced | S-01; P01 2026-11-18; P02 2026-11-18; P03 2026-11-18 |
| RA-002 | 1 renter preferred phone confirmation | UNVALIDATED; next renter round | S-01; P04 2026-11-18 |
## Sources
| Source ID | Publisher | Title | URL | Retrieved | Type |
| --- | --- | --- | --- | --- | --- |
| S-01 | customer-discovery | Enquiry study | docs/research/discovery/2026-11-18/DISCOVERY.md | 2026-11-18 | primary |
"""

STUDY_TEXT = """# Discovery Study
## Evidence Table
| Participant code | Segment | Observation or quote (redacted) | Hypothesis supported or contradicted | Strength | Date |
| --- | --- | --- | --- | --- | --- |
| P04 | Renter | Preferred phone confirmation | H-02 contradicted | observed | 2026-11-18 |
| P01 | Operator | Checked two chats | H-01 supported | observed | 2026-11-18 |
| P02 | Operator | Checked a spreadsheet | H-01 supported | observed | 2026-11-18 |
| P03 | Operator | Reconstructed enquiry status | H-01 supported | observed | 2026-11-18 |
## Findings
Hypothesis RA-002 remains unresolved. Observed RA-001 has three independent operators.
## RA-* Candidates
| RA ID | Finding | Confidence | Sources | Decision it informs |
| --- | --- | --- | --- | --- |
| RA-001 | 3 operators reconstructed enquiry status (observed) | sourced | S-01; P01 2026-11-18; P02 2026-11-18; P03 2026-11-18 | Whether enquiry state belongs in v1 |
| RA-002 | 1 renter preferred phone confirmation (hypothesis) | UNVALIDATED; next renter round | S-01; P04 2026-11-18 | Whether confirmation is automatic |
"""


def documents():
    return {MESSAGING: MESSAGE_TEXT, ASSESSMENT: ASSESSMENT_TEXT, STUDY: STUDY_TEXT}


class ResearchClaimTests(unittest.TestCase):
    def assert_conflict(self, docs, reason, evidence_path=ASSESSMENT):
        findings = research_claim_findings(docs)
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual(findings[0], {
            "kind": "approved_claim_research_conflict", "path": MESSAGING,
            "line": 9,
            "research_id": "RA-001", "evidence_path": evidence_path, "reason": reason,
        })

    def test_positive_and_unrelated_hypothesis(self):
        docs = documents()
        before = docs.copy()
        self.assertEqual(research_claim_findings(docs), [])
        self.assertEqual(docs, before)

    def test_two_remaining_operators_cannot_support_approved_claim(self):
        docs = documents()
        docs[ASSESSMENT] = docs[ASSESSMENT].replace(
            "3 operators reconstructed enquiry status | sourced",
            "2 operators reconstructed enquiry status | UNVALIDATED; next operator round")
        self.assert_conflict(docs, "unvalidated")
        # Repeated observations, including after a caller's snapshot refresh,
        # cannot bless content that still conflicts.
        self.assert_conflict(dict(docs), "unvalidated")

    def test_current_linked_candidate_overrides_stale_assessment_support(self):
        docs = documents()
        docs[STUDY] = docs[STUDY].replace(
            "3 operators reconstructed enquiry status (observed) | sourced",
            "2 operators reconstructed enquiry status (hypothesis) | UNVALIDATED; next operator round")
        self.assert_conflict(docs, "unvalidated", STUDY)

    def test_retained_withdrawn_observation_cannot_be_blessed_by_stale_candidate(self):
        docs = documents()
        docs[STUDY] = docs[STUDY].replace(
            "Reconstructed enquiry status | H-01 supported | observed",
            "Withdrawn; observation cannot be reused | H-01 unresolved | hypothesis")
        self.assert_conflict(docs, "withdrawn_observation", STUDY)
        self.assert_conflict(dict(docs), "withdrawn_observation", STUDY)

    def test_duplicate_participant_quotes_do_not_make_three_independent_participants(self):
        docs = documents()
        docs[STUDY] = docs[STUDY].replace("| P03 | Operator", "| P02 | Operator")
        self.assert_conflict(docs, "insufficient_observations", STUDY)

    def test_unrelated_withdrawn_participant_does_not_weaken_claim(self):
        docs = documents()
        docs[STUDY] = docs[STUDY].replace("Preferred phone confirmation", "Withdrawn")
        self.assertEqual(research_claim_findings(docs), [])

    def test_honest_restoration_passes(self):
        docs = documents()
        docs[ASSESSMENT] = docs[ASSESSMENT].replace("| sourced |", "| UNVALIDATED |")
        self.assert_conflict(docs, "unvalidated")
        docs[ASSESSMENT] = ASSESSMENT_TEXT
        self.assertEqual(research_claim_findings(docs), [])

    def test_global_inventory_rejects_missing_evidence_after_refresh(self):
        for missing, reason in ((ASSESSMENT, "missing_finding"), (STUDY, "missing_study")):
            with self.subTest(missing=missing):
                docs = documents()
                del docs[missing]
                self.assertEqual([], research_claim_findings(docs))
                findings = research_claim_findings(docs, full_inventory=True)
                self.assertEqual([reason], [item["reason"] for item in findings])

    def test_removing_the_entire_evidence_table_does_not_restore_support(self):
        docs = documents()
        docs[STUDY] = "## RA-* Candidates" + docs[STUDY].split("## RA-* Candidates", 1)[1]
        self.assert_conflict(docs, "insufficient_observations", STUDY)

    def test_withdrawn_claim_retained_in_history_is_not_approved(self):
        docs = documents()
        docs[MESSAGING] = docs[MESSAGING].replace(
            "| C01: Three operators reconstructed enquiry status | RA-001 / S-01 | 2026-11-18 |", "")
        docs[MESSAGING] += "\n| MSG-2 | 2026-11-18 | C01 withdrawn | RA-001 |\n"
        docs[ASSESSMENT] = docs[ASSESSMENT].replace("| sourced |", "| UNVALIDATED |")
        self.assertEqual(research_claim_findings(docs), [])

    def test_missing_unknown_and_withdrawn_research(self):
        for value, reason in (("UNVALIDATED; next round", "unvalidated"),
                              ("high", "unknown_confidence"), ("", "unknown_confidence"),
                              ("withdrawn", "withdrawn"), ("sourced; withdrawn", "withdrawn")):
            with self.subTest(value=value):
                docs = documents()
                docs[ASSESSMENT] = docs[ASSESSMENT].replace("| sourced |", f"| {value} |")
                self.assert_conflict(docs, reason)
        docs = documents()
        docs[ASSESSMENT] = docs[ASSESSMENT].replace("| RA-001 |", "| RA-003 |")
        self.assert_conflict(docs, "missing_finding")

    def test_research_first_reported_category_is_valid_outside_discovery(self):
        docs = documents()
        docs[ASSESSMENT] = docs[ASSESSMENT].replace("| sourced |", "| reported |")
        docs.pop(STUDY)
        self.assertEqual(research_claim_findings(docs), [])

    def test_explicit_missing_source_or_candidate_fails(self):
        docs = documents()
        docs[ASSESSMENT] = docs[ASSESSMENT].replace("| S-01 | customer-discovery", "| S-02 | customer-discovery")
        self.assert_conflict(docs, "unknown_source")
        docs = documents()
        docs[STUDY] = docs[STUDY].replace("| RA-001 |", "| RA-003 |")
        self.assert_conflict(docs, "missing_candidate", STUDY)

    def test_ambiguous_research_and_withdrawn_source_are_not_support(self):
        docs = documents()
        row = "| RA-001 | Contradictory duplicate | sourced | S-01 |\n"
        docs[ASSESSMENT] = docs[ASSESSMENT].replace("## Sources", row + "## Sources")
        self.assert_conflict(docs, "ambiguous_finding")
        docs = documents()
        docs[ASSESSMENT] = docs[ASSESSMENT].replace("| Enquiry study |", "| Withdrawn study |")
        self.assert_conflict(docs, "withdrawn_source")

    def test_claim_can_cite_several_ra_findings(self):
        docs = documents()
        docs[MESSAGING] = docs[MESSAGING].replace("RA-001 / S-01", "RA-001, RA-002")
        findings = research_claim_findings(docs)
        self.assertEqual([(row["research_id"], row["reason"]) for row in findings],
                         [("RA-002", "unvalidated")])

    def test_reference_in_claim_text_is_still_checked(self):
        docs = documents()
        docs[MESSAGING] = docs[MESSAGING].replace("C01: Three operators", "C01 (RA-003): Three operators")
        findings = research_claim_findings(docs)
        self.assertEqual([(row["research_id"], row["reason"]) for row in findings],
                         [("RA-003", "missing_finding")])

    def test_discovery_cannot_use_research_first_secondary_confidence(self):
        docs = documents()
        docs[STUDY] = docs[STUDY].replace("| sourced |", "| reported |")
        self.assert_conflict(docs, "unknown_confidence", STUDY)

    def test_only_jointly_inventoried_paths_are_used(self):
        for docs in ({MESSAGING: MESSAGE_TEXT}, {ASSESSMENT: ASSESSMENT_TEXT},
                     {"guidance/MESSAGING.md": MESSAGE_TEXT, ASSESSMENT: ASSESSMENT_TEXT},
                     {MESSAGING: MESSAGE_TEXT, "history/research-assessment.md": ASSESSMENT_TEXT}):
            self.assertEqual(research_claim_findings(docs), [])
        docs = documents()
        docs.pop(STUDY)
        self.assertEqual(research_claim_findings(docs), [])
        # An unrelated inventoried study is not evidence for the claim.
        docs["docs/research/discovery/other/DISCOVERY.md"] = STUDY_TEXT.replace("| sourced |", "| withdrawn |")
        self.assertEqual(research_claim_findings(docs), [])

    def test_markdown_source_link_resolves_only_to_supplied_study(self):
        docs = documents()
        docs[ASSESSMENT] = docs[ASSESSMENT].replace(
            STUDY, "[study](../research/discovery/2026-11-18/DISCOVERY.md#findings)")
        docs[STUDY] = docs[STUDY].replace("| sourced |", "| UNVALIDATED |")
        self.assert_conflict(docs, "unvalidated", STUDY)

    def test_guidance_fences_and_nested_history_are_not_claim_tables(self):
        docs = documents()
        docs[MESSAGING] = "# Guide\n```markdown\n" + MESSAGE_TEXT + "```\n"
        self.assertEqual(research_claim_findings(docs), [])
        docs[MESSAGING] = MESSAGE_TEXT.replace("## Approved Public Claims", "### Approved Public Claims")
        self.assertEqual(research_claim_findings(docs), [])

    def test_unreadable_claim_rows_are_refused_not_skipped(self):
        row = "| C01: Three operators reconstructed enquiry status | RA-001 / S-01 | 2026-11-18 |"
        header = "| Claim | Evidence | Check date |\n| --- | --- | --- |\n"
        for label, old, new in (
                ("extra cell", row, row + " extra |"),
                ("missing cell", row, "| C01: Three operators reconstructed enquiry status | RA-001 / S-01 |"),
                ("no separator", header, "| Claim | Evidence | Check date |\n"),
                ("renamed claim column", "| Claim | Evidence | Check date |", "| Statement | Evidence | Check date |")):
            with self.subTest(label):
                docs = documents()
                docs[ASSESSMENT] = docs[ASSESSMENT].replace("| sourced |", "| UNVALIDATED |", 1)
                docs[MESSAGING] = docs[MESSAGING].replace(old, new)
                findings = research_claim_findings(docs, full_inventory=True)
                self.assertEqual([("RA-001", "malformed_claim_row")],
                                 [(item["research_id"], item["reason"]) for item in findings])

    def test_emphasized_headers_stay_readable_and_findings_name_the_live_row(self):
        for header in ("| *Claim* |", "| _Claim_ |", "| **Claim** |", "| `Claim` |"):
            with self.subTest(header):
                docs = documents()
                docs[MESSAGING] = docs[MESSAGING].replace("| Claim |", header)
                self.assertEqual([], research_claim_findings(docs, full_inventory=True))
        row = "| C01: Three operators reconstructed enquiry status | RA-001 / S-01 | 2026-11-18 |"
        bad = row + " extra |"
        docs = documents()
        docs[MESSAGING] = docs[MESSAGING].replace(row, bad).replace(
            "# Messaging Record\n", "# Messaging Record\n```text\n" + bad + "\n```\n")
        live = [number for number, text in enumerate(docs[MESSAGING].splitlines(), 1) if text == bad][-1]
        findings = research_claim_findings(docs, full_inventory=True)
        self.assertEqual([(live, "malformed_claim_row")], [(item["line"], item["reason"]) for item in findings])

    def test_unreadable_support_rows_are_refused(self):
        cases = (
            (ASSESSMENT, "| RA-001 | 3 operators reconstructed enquiry status | sourced |",
             "| RA-001 | 3 operators reconstructed enquiry status | sourced | extra |", "malformed_finding"),
            (ASSESSMENT, "| S-01 | customer-discovery |", "| S-01 | customer-discovery | extra |", "malformed_source"),
            (STUDY, "| RA-001 | 3 operators reconstructed enquiry status (observed) |",
             "| RA-001 | extra | 3 operators reconstructed enquiry status (observed) |", "malformed_candidate"),
            (STUDY, "| P01 | Operator | Checked two chats |", "| P01 | Operator | extra | Checked two chats |",
             "malformed_evidence"),
        )
        for name, old, new, reason in cases:
            with self.subTest(reason):
                docs = documents()
                self.assertEqual(1, docs[name].count(old))
                docs[name] = docs[name].replace(old, new)
                findings = research_claim_findings(docs, full_inventory=True)
                self.assertEqual([reason], [item["reason"] for item in findings])

    def test_candidate_without_participant_codes_has_no_observations(self):
        docs = documents()
        docs[STUDY] = docs[STUDY].replace(
            "| sourced | S-01; P01 2026-11-18; P02 2026-11-18; P03 2026-11-18 | Whether", "| sourced | S-01 | Whether")
        docs[STUDY] = "## RA-* Candidates" + docs[STUDY].split("## RA-* Candidates", 1)[1]
        self.assert_conflict(docs, "insufficient_observations", STUDY)

    def test_study_reference_outside_the_repository_is_refused(self):
        for target in ("../../outside/DISCOVERY.md", "C:/outside/DISCOVERY.md", "/outside/DISCOVERY.md",
                       "[study](../../../outside/DISCOVERY.md)"):
            with self.subTest(target):
                docs = documents()
                docs[ASSESSMENT] = docs[ASSESSMENT].replace(f"| {STUDY} |", f"| {target} |")
                docs.pop(STUDY)
                findings = research_claim_findings(docs, full_inventory=True)
                self.assertEqual(["unsafe_study_path"], [item["reason"] for item in findings])
        # A public URL is not a local study and stays outside this check.
        docs = documents()
        docs[ASSESSMENT] = docs[ASSESSMENT].replace(f"| {STUDY} |", "| https://example.com/study |")
        docs.pop(STUDY)
        self.assertEqual([], research_claim_findings(docs, full_inventory=True))

    def test_inline_markup_and_escaped_pipe_preserve_claim_line(self):
        docs = documents()
        docs[MESSAGING] = docs[MESSAGING].replace("RA-001 / S-01", "**RA-001** / S-01")
        docs[ASSESSMENT] = docs[ASSESSMENT].replace("3 operators reconstructed enquiry status", r"3 operators reconstructed \| enquiry status")
        self.assertEqual(research_claim_findings(docs), [])


if __name__ == "__main__":
    unittest.main()
