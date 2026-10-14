"""Diagnostic completeness joins existing receipts; fixtures are not browser proof."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from types import SimpleNamespace
from unittest.mock import patch
import check_ui_diagnostic_wave as diagnostic_cli
import hifi_review_fixture as fixture
import review_evidence as evidence

SCRIPT = Path(__file__).resolve().parents[1] / "check_ui_diagnostic_wave.py"
CASE = [{"surface": "UI-001", "state": "ready", "target": "390"}]
SCORES = {f"H{index}": 90 for index in range(1, 10)}


class DiagnosticWaveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.child = self.root / "child.html"
        self.child.write_text("<h1>Child</h1>", encoding="utf-8", newline="")
        self.child_bytes = self.child.read_bytes()
        index_surface = {
            "id": "UI-001", "page": "index.html", "route": "/home", "states": ["ready"],
            "responsive": {"kind": "viewports", "targets": [390]},
            "navigation": [], "controls": [],
        }
        child_surface = dict(index_surface, id="UI-002", page="child.html", route="/detail")
        self.manifest = {
            "schema": "ui-hifi/2", "surfaces": [index_surface, child_surface],
            "pages": [{"path": "child.html", "sha256": self.sha(self.child)}],
            "interactions": [],
        }
        index_source = fixture.add_shell(fixture._source_html(index_surface, component_types=("button",), version=3),
                                         self.manifest, component_types=("button",), version=3)
        child_source = fixture.add_shell(fixture._source_html(child_surface, component_types=("button",), version=3),
                                         self.manifest, page="child.html", component_types=("button",), version=3)
        self.child.write_text(child_source, encoding="utf-8", newline="")
        self.child_bytes = self.child.read_bytes()
        self.manifest["pages"] = [{"path": "child.html", "sha256": self.sha(self.child)}]
        manifest_script = ('<script id="ui-hifi-manifest" type="application/json">'
                           + json.dumps(self.manifest) + "</script>")
        subject = self.root / "index.html"
        subject.write_text(manifest_script + index_source, encoding="utf-8", newline="")
        self.subject = self.binding(subject)
        self.prd = self.root / "PRD.md"
        self.prd.write_text("# Frozen PRD", encoding="utf-8", newline="")
        self.prd_bytes = self.prd.read_bytes()
        self.prd_binding = self.binding(self.prd)
        self.capture = self.root / "capture.json"
        self.capture.write_text(json.dumps({"observed": "synthetic fixture"}), encoding="utf-8")
        self.capture_binding = self.binding(self.capture)

    def sha(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def binding(self, path: Path) -> dict[str, str]:
        return {"path": path.relative_to(self.root).as_posix(), "sha256": self.sha(path)}

    def write(self, path: Path, payload: object) -> dict[str, str]:
        path.write_text(json.dumps(payload), encoding="utf-8", newline="")
        return self.binding(path)

    def observation(self, *, result: str = "PASS", h5: int = 90) -> dict:
        output = {
            "schema": "ui-output/3", "check": "hifi-browser", "subject": self.subject,
            "matrix": {"cases": CASE},
            "results": [dict(CASE[0], result=result)],
            "execution": {
                "startedAt": "2026-01-01T00:00:00Z", "finishedAt": "2026-01-01T00:00:01Z",
                "tool": "playwright", "method": "browser-matrix",
                "environment": {"runtime": "synthetic test fixture"},
                "artifacts": [self.prd_binding, self.subject, self.binding(self.child)],
            },
        }
        return output

    def browser_output(self, result: str = "PASS") -> dict:
        output = self.observation(result=result)
        output.update({
            "sandbox": {"network": "disabled", "topNavigation": "allowlisted-local-pages",
                        "popups": "blocked", "forms": "blocked"},
            "console": [], "network": [], "navigation": [], "popups": [], "forms": [],
            "popupAttempts": 0, "formAttempts": 0, "interactions": [],
            "reviewer": fixture.observations(self.manifest, component_types=("button",), version=3),
        })
        return output

    def build(self, *, browser_result: str = "PASS", h5: int = 90) -> dict:
        evidence_dir = self.root / "docs/evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        observations: dict[str, dict[str, str]] = {}
        for role, check in evidence.DIAGNOSTIC_CHECKS.items():
            output = self.browser_output(browser_result) if role == "browser" else self.observation()
            output["check"] = check
            if role != "browser":
                output["assessment"] = {
                    "scores": dict(SCORES, H5=h5), "blocks": [],
                    "observations": [dict(CASE[0], finding="Concrete synthetic rendering observation.",
                                          evidence=[self.capture_binding])],
                }
            output_path = evidence_dir / f"{role}-output.json"
            output_binding = self.write(output_path, output)
            receipt = evidence.build_receipt(self.root, output_binding["path"])
            observations[role] = self.write(evidence_dir / f"{role}.json", receipt)
        return {
            "schema": evidence.DIAGNOSTIC_REQUEST_SCHEMA, "subject": self.subject,
            "frozenInputs": {"prd": self.prd_binding, "manifest": self.subject},
            "requiredCases": CASE, "observations": observations,
        }

    def rebind(self, request: dict, role: str) -> None:
        output_path = self.root / "docs/evidence" / f"{role}-output.json"
        receipt = evidence.build_receipt(self.root, output_path.relative_to(self.root).as_posix())
        request["observations"][role] = self.write(
            self.root / "docs/evidence" / f"{role}.json", receipt)

    def test_browser_uses_the_existing_offline_and_reviewer_contract(self) -> None:
        request = self.build()
        self.assertEqual([], evidence.diagnostic_wave_findings(self.root, request))
        output_path = self.root / "docs/evidence/browser-output.json"
        output = json.loads(output_path.read_text(encoding="utf-8"))
        output.pop("sandbox")
        output_path.write_text(json.dumps(output), encoding="utf-8", newline="")
        self.rebind(request, "browser")
        findings = evidence.diagnostic_wave_findings(self.root, request)
        self.assertIn("invalid ui-output/3 key set", " ".join(findings))

    def test_complete_design_fail_with_concrete_blocks_is_repair_eligible(self) -> None:
        request = self.build(browser_result="FAIL", h5=79)
        for role in ("critique", "audit", "grading"):
            output_path = self.root / "docs/evidence" / f"{role}-output.json"
            output = json.loads(output_path.read_text(encoding="utf-8"))
            output["results"][0]["result"] = "FAIL"
            output["assessment"]["blocks"] = ["Concrete observed hierarchy defect"]
            output_path.write_text(json.dumps(output), encoding="utf-8", newline="")
            self.rebind(request, role)
        report = evidence.diagnostic_wave_report(self.root, request)
        self.assertTrue(report["complete"])
        self.assertTrue(report["repairEligible"])
        self.assertIn("critique observed block: Concrete observed hierarchy defect",
                      report["findings"])

    def test_missing_or_blocked_case_blocks_despite_an_observed_fail(self) -> None:
        request = self.build(browser_result="FAIL")
        request["requiredCases"] = [CASE[0], dict(CASE[0], surface="UI-002")]
        output_path = self.root / "docs/evidence/browser-output.json"
        output = json.loads(output_path.read_text(encoding="utf-8"))
        output["matrix"]["cases"].append(dict(CASE[0], surface="UI-002"))
        output["results"] = [dict(CASE[0], result="FAIL"), dict(CASE[0], surface="UI-002", result="BLOCKED")]
        output_path.write_text(json.dumps(output), encoding="utf-8", newline="")
        self.rebind(request, "browser")
        findings = " ".join(evidence.diagnostic_wave_findings(self.root, request))
        self.assertIn("browser required case is unscorable: UI-002/ready/390", findings)
        self.assertFalse(evidence.diagnostic_wave_report(self.root, request)["complete"])

    def test_unscorable_blocks_block_even_when_scores_exist(self) -> None:
        request = self.build()
        output_path = self.root / "docs/evidence/grading-output.json"
        output = json.loads(output_path.read_text(encoding="utf-8"))
        output["assessment"]["blocks"] = [123]
        output_path.write_text(json.dumps(output), encoding="utf-8", newline="")
        self.rebind(request, "grading")
        findings = " ".join(evidence.diagnostic_wave_findings(self.root, request))
        self.assertIn("review blocks must contain concrete findings", findings)
        self.assertFalse(evidence.diagnostic_wave_report(self.root, request)["complete"])

    def test_complete_fail_and_low_score_are_eligible_findings(self) -> None:
        request = self.build(browser_result="FAIL", h5=79)
        report = evidence.diagnostic_wave_report(self.root, request)
        self.assertTrue(report["complete"])
        self.assertTrue(report["repairEligible"])
        self.assertEqual("findings", report["status"])
        self.assertIn("browser observed FAIL", report["findings"])
        self.assertIn("grading H5 score 79 is below the accepted threshold", report["findings"])

    def test_negative_drift_missing_cases_and_partial_wave_block_handoff(self) -> None:
        request = self.build()
        self.assertEqual([], evidence.diagnostic_wave_findings(self.root, request))

        request["requiredCases"] = [dict(CASE[0], surface="UI-002")]
        self.assertIn("browser case matrix", " ".join(
            evidence.diagnostic_wave_findings(self.root, request)))
        request = self.build()
        request["observations"].pop("audit")
        with self.assertRaises(ValueError):
            evidence.diagnostic_wave_findings(self.root, request)

        request = self.build()
        self.prd.write_text("# Changed PRD", encoding="utf-8", newline="")
        with self.assertRaises(ValueError):
            evidence.diagnostic_wave_findings(self.root, request)
        self.prd.write_bytes(self.prd_bytes)
        request = self.build()
        self.child.write_text("<h1>Changed</h1>", encoding="utf-8", newline="")
        self.assertIn("artifact identity is stale: child.html", " ".join(
            evidence.diagnostic_wave_findings(self.root, request)))
        self.child.write_bytes(self.child_bytes)

        request = self.build()
        output = self.root / "docs/evidence/browser-output.json"
        output.unlink()
        self.assertIn("browser:", " ".join(evidence.diagnostic_wave_findings(self.root, request)))

    def test_blocked_and_missing_observations_are_not_repair_eligible(self) -> None:
        for result, expected in (("BLOCKED", "blocked"), ("MISSING", "incomplete")):
            request = self.build(browser_result=result)
            findings = evidence.diagnostic_wave_findings(self.root, request)
            self.assertIn("browser observations are incomplete or blocked", " ".join(findings))
            report = evidence.diagnostic_wave_report(self.root, request)
            self.assertFalse(report["complete"])
            self.assertFalse(report["repairEligible"])

    def test_missing_review_capture_blocks_even_when_scores_are_present(self) -> None:
        request = self.build()
        grading = self.root / "docs/evidence/grading-output.json"
        payload = json.loads(grading.read_text(encoding="utf-8"))
        payload["assessment"]["observations"][0]["evidence"] = []
        grading.write_text(json.dumps(payload), encoding="utf-8", newline="")
        receipt_path = self.root / "docs/evidence/grading.json"
        canonical = evidence.build_receipt(self.root, "docs/evidence/grading-output.json")
        self.assertEqual("BLOCKED", canonical["result"])
        receipt_path.write_text(json.dumps(canonical), encoding="utf-8", newline="")
        request["observations"]["grading"] = self.binding(receipt_path)
        report = evidence.diagnostic_wave_report(self.root, request)
        self.assertFalse(report["complete"])

    def test_cli_enforces_the_independent_read_ack_and_writes_nothing(self) -> None:
        request = self.build(browser_result="FAIL", h5=79)
        path = self.root / "diagnostic-request.json"
        path.write_text(json.dumps(request), encoding="utf-8", newline="")
        digest = self.sha(path)
        before = sorted(str(item.relative_to(self.root)) for item in self.root.rglob("*") if item.is_file())
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(self.root), "--request", str(path),
             "--request-sha256", digest], capture_output=True, text=True, timeout=15, check=True)
        report = json.loads(result.stdout)
        self.assertTrue(report["complete"])
        after = sorted(str(item.relative_to(self.root)) for item in self.root.rglob("*") if item.is_file())
        self.assertEqual(before, after)
        bad = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo-root", str(self.root), "--request", str(path),
             "--request-sha256", "0" * 64], capture_output=True, text=True, timeout=15)
        self.assertEqual(2, bad.returncode)
        self.assertIn("changed after", bad.stdout)

    def test_cli_bounds_the_request_read(self) -> None:
        path = self.root / "huge-request.json"
        path.write_text("{}", encoding="utf-8", newline="")
        fake_stat = lambda item: SimpleNamespace(st_size=evidence.MAX_BYTES + 1)
        with patch.object(Path, "stat", fake_stat):
            blocked = diagnostic_cli.main([
                "--repo-root", str(self.root), "--request", str(path),
                "--request-sha256", self.sha(path),
            ])
        self.assertEqual(2, blocked)


if __name__ == "__main__":
    unittest.main()
