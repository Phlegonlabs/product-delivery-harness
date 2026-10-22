"""Harness loader cleanup must not strand the UI checker's own imports."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class HarnessContractJoinLoaderTests(unittest.TestCase):
    def run_loader(self, loader: str) -> subprocess.CompletedProcess[str]:
        """Run one loader in exact code with no inherited path or module cache."""

        harness_scripts = SCRIPTS_DIR.resolve()
        child = f"""
import sys
sys.path.insert(0, {str(harness_scripts)!r})
import harness_contract_join as join
loader = getattr(join, {loader!r})
loader(join.sibling_ui_design_scripts_dir())
checker = sys.modules["check_ui_design_contract"]
ui3 = checker.ui_design_v3
print(ui3.has_direction_review_profile("<html></html>"))
"""
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        return subprocess.run(
            [sys.executable, "-I", "-B", "-c", child],
            capture_output=True,
            cwd=Path(__file__).resolve().parents[3],
            env=environment,
            text=True,
            timeout=30,
        )

    def test_full_ui_checker_loader_retains_call_time_import_path(self):
        result = self.run_loader("_load_full_ui_design_checker")
        self.assertEqual(
            0,
            result.returncode,
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertEqual("False\n", result.stdout)

    def test_ui_contract_view_loader_retains_call_time_import_path(self):
        result = self.run_loader("_load_ui_contract_view")
        self.assertEqual(
            0,
            result.returncode,
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertEqual("False\n", result.stdout)

    def test_csp_helper_survives_saved_path_for_strict_and_diagnostic_evidence(self):
        harness_scripts = SCRIPTS_DIR.resolve()
        ui_scripts = harness_scripts.parents[1] / "ui-design-builder" / "scripts"
        ui_tests = ui_scripts / "tests"
        child = f"""
import json
import sys
from pathlib import Path

harness_scripts = {str(harness_scripts)!r}
sys.path.insert(0, harness_scripts)
import harness_contract_join as join

baseline = sys.path[:]
join._load_full_ui_design_checker(join.sibling_ui_design_scripts_dir())
checker = sys.modules["check_ui_design_contract"]
assert "native_csp_diagnostic" in sys.modules

sys.path.insert(0, {str(ui_tests)!r})
from test_native_csp_diagnostic import NativeCspDiagnosticTests
import review_evidence as evidence

import_baseline = sys.path[:]
case = NativeCspDiagnosticTests()
case.setUp()
try:
    native = case.native_event()
    runtime_error = case.downgraded_runtime_event(kind="error")

    def binding(path):
        return case.binding(path)

    def resolve(name, output, expected_motion=None):
        output_path = case.root / "docs/evidence" / (name + "-output.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_identity = case.write(output_path, output)
        receipt = evidence.build_receipt(case.root, output_identity["path"])
        receipt_path = output_path.with_name(name + "-receipt.json")
        receipt_identity = case.write(receipt_path, receipt)
        problems = []
        checker._resolve_evidence(
            "PASS — evidence=" + receipt_identity["path"] + " @ sha256:" + receipt_identity["sha256"],
            repo_root=case.root,
            label="HiFi surface check",
            problems=problems,
            expected_artifact=case.subject["path"],
            expected_check=output["check"],
            expected_matrix=output["matrix"],
            require_machine=True,
            expected_motion=expected_motion,
        )
        return problems

    raw = case.write_raw([native])
    browser = case.output([case.console_record(native)], raw)
    motion = json.loads(json.dumps(browser))
    motion["check"] = "motion-preview"
    motion["matrix"] = {{"cases": [{{"surface": "UI-001", "state": "normal", "target": "390"}}]}}
    motion["results"] = [dict(motion["matrix"]["cases"][0], result="PASS")]
    motion["motion"] = {{
        "intent": "MM-001", "scope": "UI-001 / hero", "mode": "normal",
        "reducedMotion": False, "asset": None,
        "observations": [{{
            "target": "390", "state": "ready", "trigger": "on entry",
            "endState": "Resting state shown", "fallbackObserved": False,
            "samples": [{{"atMs": 0, "values": {{"opacity": "0"}}}},
                        {{"atMs": 100, "values": {{"opacity": "0.5"}}}},
                        {{"atMs": 200, "values": {{"opacity": "1"}}}}],
        }}],
    }}

    case.root.mkdir(parents=True, exist_ok=True)
    scores = {{f"H{{index}}": 90 for index in range(1, 10)}}
    # The request must cover every frozen manifest case, each with its own capture.
    observed_cases = [{{"surface": surface, "state": "ready", "target": "390"}} for surface in ("UI-001", "UI-002")]
    second_capture = case.root / "docs/evidence/capture-ui-002.png"
    second_capture.parent.mkdir(parents=True, exist_ok=True)
    second_capture.write_bytes(b"second synthetic capture")
    captures = {{"UI-001": case.capture_binding, "UI-002": case.binding(second_capture)}}
    observations = {{}}
    evidence_dir = case.root / "docs/evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for role, check in evidence.DIAGNOSTIC_CHECKS.items():
        if role == "browser":
            output = case.output([case.console_record(native)], raw)
            output.update(matrix={{"cases": observed_cases}}, results=[dict(row, result="PASS") for row in observed_cases])
        else:
            output = {{
                "schema": "ui-output/3", "check": check, "subject": case.subject,
                "matrix": {{"cases": observed_cases}},
                "results": [dict(row, result="PASS") for row in observed_cases],
                "execution": {{
                    "startedAt": "2026-01-01T00:00:00Z", "finishedAt": "2026-01-01T00:00:01Z",
                    "tool": "synthetic", "method": "browser-matrix",
                    "environment": {{"runtime": "synthetic test fixture"}},
                    "artifacts": [case.binding(case.prd), case.subject, case.binding(case.child)],
                }},
                "assessment": {{
                    "scores": scores, "blocks": [],
                    "observations": [dict(row, finding="Concrete synthetic rendering observation.", evidence=[captures[row["surface"]]]) for row in observed_cases],
                }},
            }}
        output_path = evidence_dir / (role + "-output.json")
        output_identity = case.write(output_path, output)
        receipt = evidence.build_receipt(case.root, output_identity["path"])
        observations[role] = case.write(evidence_dir / (role + ".json"), receipt)
    request = {{
        "schema": evidence.DIAGNOSTIC_REQUEST_SCHEMA, "subject": case.subject,
        "frozenInputs": {{"prd": case.binding(case.prd), "manifest": case.subject}},
        "requiredCases": observed_cases, "observations": observations,
    }}
    request_identity = case.write(case.root / "diagnostic-request.json", request)

    assert "native_csp_diagnostic" in sys.modules
    sys.path[:] = baseline

    assert resolve("browser-positive", browser) == []
    expected_motion = {{
        "intent": "MM-001", "scope": "UI-001 / hero", "mode": "normal",
        "trigger": "on entry", "endState": "Resting state shown",
        "states": ["ready"], "targets": ["390"], "assetRequired": False,
    }}
    assert resolve("motion-positive", motion, expected_motion) == []
    request_data = json.loads((case.root / request_identity["path"]).read_text("utf-8"))
    assert evidence.diagnostic_wave_findings(case.root, request_data) == []

    bad_raw = case.write_raw([native, runtime_error])
    negative = case.output([
        case.console_record(native),
        case.console_record(runtime_error, message="benign"),
    ], bad_raw)
    problems = resolve("runtime-error-negative", negative)
    assert any("contains a console error" in item for item in problems)
    assert any("provenance is incomplete" in item for item in problems)
finally:
    case.doCleanups()
"""
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", child],
            capture_output=True,
            cwd=harness_scripts.parents[2],
            env=environment,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            0,
            result.returncode,
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
