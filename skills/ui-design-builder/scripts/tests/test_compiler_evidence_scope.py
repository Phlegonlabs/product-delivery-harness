"""Compiler regressions for declared n/a states and intermediate-width receipts.

All files are synthetic validator fixtures, not browser observations.
"""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from test_structure_publication import build_receipt, checker, digest
from test_ui_design_v3 import preflight, v3_publication


class CompilerEvidenceScopeTests(unittest.TestCase):
    def test_matrix_omits_na_but_keeps_derived_and_per_surface_targets(self):
        scope = {
            "responsive": {"kind": "per-surface", "targets": []},
            "surfaces": [
                {"id": "UI-001", "states": ["ready", "not_found:n/a", "feedback"],
                 "derivedStates": {"feedback": "ready"},
                 "responsive": {"kind": "viewports", "targets": [1440, 390, 768]}},
                {"id": "UI-002", "states": ["ready", "unavailable"],
                 "responsive": {"kind": "sizeClasses", "targets": ["compact", "regular"]}},
            ],
        }
        expected = [
            {"surface": surface, "state": state, "target": target}
            for surface, state, targets in (
                ("UI-001", "ready", ["1440", "390", "768"]),
                ("UI-001", "feedback", ["390"]),
                ("UI-002", "ready", ["compact", "regular"]),
                ("UI-002", "unavailable", ["compact", "regular"]),
            ) for target in targets
        ]
        self.assertEqual({"cases": expected}, checker._evidence_matrix(scope))

    def test_intermediate_measurements_do_not_replace_ordinary_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            baseline = ui.read_text(encoding="utf-8")
            self.assertEqual([], preflight(ui, root, prd, hifi))
            for label in ("Intermediate width check", "HiFi surface check"):
                with self.subTest(label=label):
                    match = re.search(r"^" + label + r": PASS — evidence=(\S+) @ sha256:([0-9a-f]{64})", baseline, re.M)
                    receipt_path = root / match.group(1)
                    original_receipt = receipt_path.read_bytes()
                    receipt = json.loads(original_receipt)
                    output_path = root / receipt["receipt"]["outputArtifact"]["path"]
                    original_output = output_path.read_bytes()
                    output = json.loads(original_output)
                    # The intermediate collector leaves approved-width reviewer
                    # values unmeasured. Ordinary surface evidence must measure them.
                    output["reviewer"] = {}
                    output_path.write_text(json.dumps(output), encoding="utf-8")
                    receipt_path.write_text(json.dumps(build_receipt(root, output_path.relative_to(root).as_posix())), encoding="utf-8")
                    ui.write_text(baseline.replace(match.group(0), match.group(0).replace(match.group(2), digest(receipt_path))), encoding="utf-8")
                    findings = preflight(ui, root, prd, hifi)
                    if label == "Intermediate width check":
                        self.assertEqual([], findings)
                    else:
                        self.assertTrue(any("reviewer" in item for item in findings), findings)
                    output_path.write_bytes(original_output)
                    receipt_path.write_bytes(original_receipt)
                    ui.write_text(baseline, encoding="utf-8")

    def test_an_intermediate_receipt_from_an_earlier_driver_keeps_its_interaction_rows(self):
        # Approvals made before the sweep stopped repeating interactions stay valid in later delivery checkouts.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            baseline = ui.read_text(encoding="utf-8")

            def output_of(label):
                match = re.search(r"^" + label + r": PASS — evidence=(\S+) @ sha256:([0-9a-f]{64})", baseline, re.M)
                receipt_path = root / match.group(1)
                return match, receipt_path, root / json.loads(receipt_path.read_bytes())["receipt"]["outputArtifact"]["path"]

            surface = json.loads(output_of("HiFi surface check")[2].read_bytes())
            match, receipt_path, output_path = output_of("Intermediate width check")
            output = json.loads(output_path.read_bytes())
            self.assertEqual([], output["interactions"])
            output["interactions"], output["navigation"] = surface["interactions"], surface["navigation"]
            self.assertTrue(output["interactions"])
            output_path.write_text(json.dumps(output), encoding="utf-8")
            receipt_path.write_text(json.dumps(build_receipt(root, output_path.relative_to(root).as_posix())), encoding="utf-8")
            ui.write_text(baseline.replace(match.group(2), digest(receipt_path)), encoding="utf-8")
            self.assertEqual([], preflight(ui, root, prd, hifi))

    def test_intermediate_still_rejects_missing_schema_and_browser_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = v3_publication(root)
            baseline = ui.read_text(encoding="utf-8")
            match = re.search(r"^Intermediate width check: PASS — evidence=(\S+) @ sha256:([0-9a-f]{64})", baseline, re.M)
            receipt_path = root / match.group(1)
            receipt = json.loads(receipt_path.read_bytes())
            output_path = root / receipt["receipt"]["outputArtifact"]["path"]
            original_output = json.loads(output_path.read_bytes())
            for defect in ("missing reviewer", "missing interactions", "interaction rows", "open sandbox", "stale output"):
                with self.subTest(defect=defect):
                    output = copy.deepcopy(original_output)
                    if defect == "missing reviewer":
                        del output["reviewer"]
                    elif defect == "missing interactions":
                        del output["interactions"]
                    elif defect == "interaction rows":      # they belong to the HiFi surface check's receipt
                        output["interactions"] = [{"id": "UI-001-to-details", "target": "390", "trigger": "click",
                                                   "result": "PASS"}]
                    elif defect == "open sandbox":
                        output["sandbox"]["network"] = "enabled"
                    output_path.write_text(json.dumps(output), encoding="utf-8")
                    receipt_path.write_text(json.dumps(build_receipt(root, output_path.relative_to(root).as_posix())), encoding="utf-8")
                    ui.write_text(baseline.replace(match.group(2), digest(receipt_path)), encoding="utf-8")
                    if defect == "stale output":
                        output_path.write_text(json.dumps(output) + "\n", encoding="utf-8")
                    self.assertTrue(preflight(ui, root, prd, hifi), defect)


if __name__ == "__main__":
    unittest.main()
