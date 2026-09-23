"""Synthetic observations exercise consistency; none represent a product browser run."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review_evidence as evidence
import check_ui_design_contract as ui
from test_ui_design_contract import contract


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        artifact = self.root / "candidate.html"
        artifact.write_text("<h1>Synthetic fixture</h1>", encoding="utf-8")
        self.subject = {"path": "candidate.html", "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}
        capture = self.root / "capture.json"
        capture.write_text(json.dumps({"syntheticFixture": True, "case": "UI-001/ready/390"}), encoding="utf-8")
        self.capture = {"path": "capture.json", "sha256": hashlib.sha256(capture.read_bytes()).hexdigest()}
        self.cases = [{"surface": "UI-001", "state": "ready", "target": "390"}]
        self.output = {
            "schema": "ui-output/3", "check": "wireframe-browser", "subject": self.subject,
            "matrix": {"cases": self.cases}, "results": [dict(self.cases[0], result="PASS")],
            "execution": {"startedAt": "2020-01-01T00:00:00Z", "finishedAt": "2020-01-01T00:00:01Z",
                          "tool": "playwright", "method": "browser-matrix",
                          "environment": {"runtime": "synthetic test fixture"},
                          "artifacts": [self.subject]},
        }

    def write_output(self):
        (self.root / "output.json").write_text(json.dumps(self.output), encoding="utf-8")

    def test_aggregate_does_not_fill_missing_or_failed_results(self):
        self.assertEqual("PASS", evidence.observed_result(self.output))
        for result in ("FAIL", "BLOCKED", "MISSING"):
            self.output["results"][0]["result"] = result
            self.assertEqual(result, evidence.observed_result(self.output))
        self.output["results"] = []
        self.assertEqual("MISSING", evidence.observed_result(self.output))

    def test_receipt_preserves_actual_time_tool_environment_and_has_no_human_fields(self):
        self.write_output()
        receipt = evidence.build_receipt(self.root, "output.json")
        self.assertEqual("ui-evidence/3", receipt["schema"])
        self.assertNotIn("owner", receipt)
        self.assertNotIn("attestation", receipt)
        self.assertEqual("2020-01-01T00:00:01Z", receipt["receipt"]["executedAt"])
        self.assertEqual(self.output["results"], receipt["receipt"]["results"])

    def test_changed_input_cannot_rebind_old_output(self):
        self.write_output()
        (self.root / "candidate.html").write_text("New candidate", encoding="utf-8")
        with self.assertRaises(ValueError):
            evidence.build_receipt(self.root, "output.json")

    def test_future_missing_environment_and_wrong_time_fail(self):
        for mutation in (
            lambda out: out["execution"].update(finishedAt="2999-01-01T00:00:00Z"),
            lambda out: out["execution"].update(environment={}),
            lambda out: out["execution"].update(artifacts=[]),
        ):
            output = copy.deepcopy(self.output)
            mutation(output)
            receipt = {"executedAt": output["execution"]["finishedAt"], "tool": "playwright", "method": "browser-matrix"}
            self.assertTrue(evidence.execution_findings(self.root, output, receipt, self.subject))

    def test_duplicate_cases_and_traversal_fail(self):
        self.output["results"] *= 2
        with self.assertRaises(ValueError):
            evidence.observed_result(self.output)
        for value in ("../candidate.html", "/candidate.html", "C:/candidate.html", "sub/../candidate.html"):
            with self.assertRaises(ValueError):
                evidence.safe_path(self.root, value)

    def test_assessment_needs_observation_artifacts_and_actual_scores(self):
        self.output["check"] = "wireframe-browser-grading"
        self.output["assessment"] = {"scores": {f"W{n}": 90 for n in range(1, 6)}, "blocks": [],
                                    "observations": [dict(self.cases[0], finding="Synthetic observed layout for validation.",
                                                          evidence=[self.capture])]}
        self.assertEqual([], evidence.assessment_findings(self.root, self.output))
        self.output["assessment"]["observations"][0]["evidence"] = [self.subject]
        self.assertIn("separate from", "\n".join(evidence.assessment_findings(self.root, self.output)))
        source = self.root / "source.json"
        source.write_text(json.dumps({"syntheticFixture": True, "input": "product source"}), encoding="utf-8")
        source_binding = {"path": "source.json", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        self.output["execution"]["artifacts"].append(source_binding)
        self.output["assessment"]["observations"][0]["evidence"] = [source_binding]
        self.assertIn("separate from", "\n".join(evidence.assessment_findings(self.root, self.output)))
        self.output["assessment"]["observations"][0]["evidence"] = [self.capture]
        self.assertEqual([], evidence.score_findings(self.output, {"Wireframe score": 90, "Wireframe lowest dimension": 90, "W5 score": 90}))
        self.assertTrue(evidence.score_findings(self.output, {"Wireframe score": 100}))
        self.output["assessment"]["observations"] = []
        self.assertTrue(evidence.assessment_findings(self.root, self.output))


def modern_contract():
    text = contract().replace("## Wireframe Approval", "## Wireframe Validation")
    start = text.index("## Wireframe Validation")
    end = text.index("## Style Integration")
    before = text[start:end]
    for line in ("Copy Freeze: approved\n", "Copy owner: Product owner\n", "Copy approved on: 2026-09-13\n",
                 "Decision: approved\n", "Decision owner: Product owner\n", "Decided on: 2026-09-13\n"):
        before = before.replace(line, "")
    before += ("Structure validation: validated\n\n### Frontend Design Usage\n\n"
               f"Frontend Design source: docs/design/frontend-design-source/SKILL.md @ sha256:{'a' * 64}\n\n"
               "| Stage | Skill | Artifact | Application |\n| --- | --- | --- | --- |\n")
    for stage in ("wireframe", "direction", "hifi"):
        before += f"| {stage} | frontend-design @ sha256:{'a' * 64} | docs/design/example.html @ sha256:{'b' * 64} | Applied concrete hierarchy and responsive layout choices. |\n"
    return text[:start] + before + "\n" + text[end:]


class StructureGateTests(unittest.TestCase):
    def test_structure_gate_does_not_ask_for_human_wireframe_or_copy_freeze(self):
        text = modern_contract()
        self.assertEqual([], ui.validate_text(text, require_filled=True, require_structure_validated=True))
        self.assertTrue(ui.parse_ui_contract_view(text)[0]["structure_review"])

    def test_frontend_design_is_required_and_taste_cannot_replace_it(self):
        text = modern_contract().replace("frontend-design @", "design-taste-frontend @")
        self.assertIn("frontend-design", "\n".join(ui.validate_text(text, require_structure_validated=True)))

    def test_frontend_digest_must_match_observed_snapshot(self):
        text = modern_contract().replace("frontend-design @ sha256:" + "a" * 64,
                                         "frontend-design @ sha256:" + "b" * 64)
        self.assertIn("differs from the observed source snapshot", "\n".join(
            ui.validate_text(text, require_structure_validated=True)))

    def test_legacy_and_new_gates_do_not_impersonate_each_other(self):
        self.assertTrue(ui.validate_text(contract(), require_structure_validated=True))
        self.assertTrue(ui.validate_text(modern_contract(), require_wireframe_approved=True))
        self.assertEqual([], ui.validate_text(contract(), require_wireframe_approved=True))

    def test_structure_cannot_fabricate_old_human_fields(self):
        text = modern_contract().replace("Structure validation: validated", "Structure validation: validated\nCopy owner: Agent")
        self.assertTrue(ui.validate_text(text, require_structure_validated=True))

    def test_visual_decision_remains_human_and_required(self):
        text = modern_contract()
        start = text.index("## Visual Approval")
        text = text[:start] + text[start:].replace("Decision: approved", "Decision: draft", 1)
        self.assertIn("Visual Approval Decision must be approved", "\n".join(ui.validate_text(text, require_visual_approved=True)))

    def test_frontend_usage_rows_inside_a_code_sample_do_not_count(self):
        text = modern_contract()
        table = text[text.index("| Stage | Skill | Artifact | Application |"):
                     text.index("## Style Integration")]
        text = text.replace(table, "```markdown\n" + table + "```\n\n")
        self.assertIn("Frontend Design Usage is missing stages", "\n".join(
            ui.validate_text(text, require_structure_validated=True)))




class MachineGateTests(EvidenceTests):
    def test_new_receipt_resolves_without_human_attestation(self):
        self.write_output()
        receipt = evidence.build_receipt(self.root, "output.json")
        target = self.root / "receipt.json"
        target.write_text(json.dumps(receipt), encoding="utf-8")
        problems = []
        ui._resolve_evidence("PASS — evidence=receipt.json @ sha256:" + hashlib.sha256(target.read_bytes()).hexdigest(),
                             repo_root=self.root, label="Responsive surface check", problems=problems,
                             expected_artifact="candidate.html", expected_check="wireframe-browser",
                             expected_matrix={"cases": self.cases}, require_machine=True)
        self.assertEqual([], problems)

    def test_human_attestation_fields_are_not_accepted_in_machine_schema(self):
        self.write_output()
        receipt = evidence.build_receipt(self.root, "output.json")
        receipt["owner"] = "Invented owner"
        receipt["attestation"] = "human-attested"
        target = self.root / "receipt.json"
        target.write_text(json.dumps(receipt), encoding="utf-8")
        problems = []
        ui._resolve_evidence("PASS — evidence=receipt.json @ sha256:" + hashlib.sha256(target.read_bytes()).hexdigest(),
                             repo_root=self.root, label="Responsive surface check", problems=problems,
                             expected_check="wireframe-browser", require_machine=True)
        self.assertTrue(problems)


if __name__ == "__main__":
    unittest.main()
