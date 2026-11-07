#!/usr/bin/env python3
"""Tests for render_delivery_acceptance.py."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_delivery_acceptance as checker  # noqa: E402
from render_delivery_acceptance import main as render_main  # noqa: E402


CANDIDATE = "a" * 40
EVIDENCE = b"synthetic delivery evidence\n"

PRD = """# PRD: Fixture

## Test Obligations

| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-001 | Receive stock against an order | E2E | Yes | PRD-001 | stock on hand matches the receipt |
| TEST-002 | Over-receipt is refused | integration | Yes | PRD-001 | refusal shown, order unchanged |
| TEST-003 | Optional receipt report | unit | No | PRD-001 | report lists receipts |
"""

FEATURE = """Feature: Receive stock

  Background:
    Given a warehouse clerk
    And an open purchase order PO-7 with 10 units

  @TEST-001
  Scenario: Receive the full quantity
    When the clerk receives 10 units against PO-7
    Then PO-7 is closed
    And stock on hand shows 10 units

  @TEST-002 @auth:real @env:staging
  Scenario: Over-receipt is refused
    When the clerk receives 11 units against PO-7
    Then the receipt is refused with "exceeds ordered quantity"
    But PO-7 stays open
"""

PROFILE = {
    "schema": "acceptance-profile/1",
    "platform": "web",
    "auth_mode": "mock",
    "environment": "test",
    "build": {"build_id": "fixture-web-1", "config_digest": "b" * 64},
    "execution": {
        "target": "synthetic test server",
        "device": "Chromium 131 desktop",
        "os": "Ubuntu 24.04",
        "persona": {"tenant": "synthetic-acme", "account_state": "active synthetic account"},
        "initial_data": "empty tenant with no orders",
        "expected_side_effects": "local database rows only; no external sends",
        "dependency_mode": "deterministic adapters",
    },
    "fixtures": [
        {
            "namespace": "synthetic-receive-0001",
            "setup_authority": "test environment operator grant",
            "cleanup_authority": "test environment operator grant",
            "owned_resources": ["owned:receive-0001/clerk"],
            "production": False,
            "auth_bypass": False,
        }
    ],
}


class RenderDeliveryAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.prd = self.root / "PRD.md"
        self.prd.write_text(PRD, encoding="utf-8")
        self.features = self.root / "features"
        self.features.mkdir()
        (self.features / "product.feature").write_text(FEATURE, encoding="utf-8")
        self.profile = self.root / "acceptance-profile.json"
        self.write_profile(PROFILE)
        self.out = self.root / "verification" / "delivery-acceptance.json"

    def write_profile(self, value: dict) -> None:
        self.profile.write_text(json.dumps(value), encoding="utf-8")

    def render(self) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = render_main([
                "--prd", str(self.prd), "--features", str(self.features),
                "--profile", str(self.profile), "--out", str(self.out),
            ])
        return code, output.getvalue()

    def check_register(self) -> tuple[int, dict]:
        """Run the unchanged acceptance CLI on the rendered register."""
        register = json.loads(self.out.read_text(encoding="utf-8"))
        evidence = self.root / "verification" / "evidence" / "run.txt"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_bytes(EVIDENCE)
        rows = []
        for test in register["tests"]:
            for scenario in test["scenarios"]:
                rows.append({
                    "test_id": test["test_id"], "scenario_id": scenario["id"],
                    "platform": scenario["platform"], "auth_mode": scenario["auth_mode"],
                    "environment": scenario["environment"], "build": scenario["build"],
                    "execution": scenario["execution"], "status": "pass",
                    "assertion_results": {key: "pass" for key in scenario["execution"]["assertions"]},
                    "fixture_cleanup": "cleaned" if scenario["fixtures"] else "not_required",
                    "evidence": {"path": "verification/evidence/run.txt",
                                 "sha256": hashlib.sha256(EVIDENCE).hexdigest()},
                })
        results = self.root / "verification" / "delivery-results.json"
        results.write_text(json.dumps({"schema": "delivery-results/1", "candidate_sha": CANDIDATE,
                                       "results": rows}), encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = checker.main([
                "--repo-root", str(self.root), "--prd", str(self.prd),
                "--contract", str(self.out),
                "--contract-sha256", hashlib.sha256(self.out.read_bytes()).hexdigest(),
                "--results", str(results), "--candidate-sha", CANDIDATE,
            ])
        return code, json.loads(output.getvalue())

    def test_rendered_register_passes_the_acceptance_check(self) -> None:
        code, output = self.render()
        self.assertEqual(0, code, output)
        self.assertIn("rendered 2 scenarios under 2 TEST IDs", output)
        status, payload = self.check_register()
        self.assertEqual(0, status, payload)
        # The checker prints `<test_id>/<scenario id>`; a scenario id already starts with its TEST ID.
        self.assertEqual(["TEST-001/TEST-001/receive-the-full-quantity",
                          "TEST-002/TEST-002/over-receipt-is-refused"], payload["matched_scenarios"])

    def test_steps_map_to_persona_data_actions_and_assertions(self) -> None:
        self.assertEqual(0, self.render()[0])
        register = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(self.prd.read_bytes()).hexdigest(), register["prd_sha256"])
        self.assertEqual(["TEST-001", "TEST-002"], [test["test_id"] for test in register["tests"]])
        scenario = register["tests"][1]["scenarios"][0]
        self.assertEqual("TEST-002/over-receipt-is-refused", scenario["id"])
        execution = scenario["execution"]
        self.assertEqual({"role": "a warehouse clerk", "tenant": "synthetic-acme",
                          "account_state": "active synthetic account"}, execution["persona"])
        self.assertEqual("an open purchase order PO-7 with 10 units", execution["initial_data"])
        self.assertEqual(["the clerk receives 11 units against PO-7"], execution["actions"])
        self.assertEqual({"ASSERT-001": 'the receipt is refused with "exceeds ordered quantity"',
                          "ASSERT-002": "PO-7 stays open"}, execution["assertions"])

    def test_profile_tags_override_the_run_defaults(self) -> None:
        self.assertEqual(0, self.render()[0])
        register = json.loads(self.out.read_text(encoding="utf-8"))
        tagged = register["tests"][1]["scenarios"][0]
        untagged = register["tests"][0]["scenarios"][0]
        self.assertEqual(("web", "real", "staging"),
                         (tagged["platform"], tagged["auth_mode"], tagged["environment"]))
        self.assertEqual(("web", "mock", "test"),
                         (untagged["platform"], untagged["auth_mode"], untagged["environment"]))

    def test_no_seed_given_uses_the_profile_initial_data(self) -> None:
        (self.features / "product.feature").write_text(
            FEATURE.replace("    And an open purchase order PO-7 with 10 units\n", ""), encoding="utf-8")
        self.assertEqual(0, self.render()[0])
        register = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual("empty tenant with no orders",
                         register["tests"][0]["scenarios"][0]["execution"]["initial_data"])

    def test_output_is_deterministic_json(self) -> None:
        self.assertEqual(0, self.render()[0])
        first = self.out.read_bytes()
        self.assertEqual(0, self.render()[0])
        self.assertEqual(first, self.out.read_bytes())
        self.assertTrue(first.endswith(b"}\n"))
        self.assertNotIn(b"\r\n", first)
        value = json.loads(first)
        self.assertEqual(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                         first.decode("utf-8"))

    def test_profile_template_placeholders_are_findings(self) -> None:
        template = SCRIPTS_DIR.parent / "assets/templates/ACCEPTANCE_PROFILE.template.json"
        self.profile.write_bytes(template.read_bytes())
        code, output = self.render()
        self.assertEqual(1, code, output)
        self.assertIn("profile.build.build_id must be concrete", output)
        self.assertIn("profile.execution.device must be concrete", output)
        self.assertIn("profile.execution.persona.tenant must be concrete", output)
        self.assertFalse(self.out.exists())

    def test_findings_name_the_feature_line(self) -> None:
        cases = {
            "unknown TEST": (FEATURE.replace("@TEST-002 ", "@TEST-009 "), "TEST-009 is not a TEST ID in the PRD"),
            "required TEST without scenario": (
                FEATURE.split("  @TEST-002", 1)[0], "required TEST-002 has no scenario"),
            "bad override": (FEATURE.replace("@env:staging", "@env:moon"), "@env:moon must be one of"),
            "placeholder step": (FEATURE.replace("PO-7 stays open", "<order> stays open"), "product.feature:17:"),
            "reader rejection": (FEATURE.replace("  Scenario: Receive", "  Scenario Outline: Receive"),
                                 "Scenario Outline is not supported"),
        }
        for label, (text, fragment) in cases.items():
            with self.subTest(label):
                (self.features / "product.feature").write_text(text, encoding="utf-8")
                code, output = self.render()
                self.assertEqual(1, code, output)
                self.assertIn(fragment, output)
                self.assertFalse(self.out.exists())

    def test_override_that_breaks_the_contract_is_a_finding(self) -> None:
        profile = copy.deepcopy(PROFILE)
        (self.features / "product.feature").write_text(
            FEATURE.replace("@env:staging", "@env:production").replace("@auth:real", "@auth:mock"),
            encoding="utf-8")
        self.write_profile(profile)
        code, output = self.render()
        self.assertEqual(1, code, output)
        self.assertIn("cannot use mock authentication in production", output)
        self.assertIn("cannot declare synthetic fixtures for a production scenario", output)

    def check(self) -> tuple[int, str]:
        """Run --check and prove it wrote nothing."""
        before = sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*"))
        saved = self.out.read_bytes() if self.out.exists() else None
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = render_main([
                "--prd", str(self.prd), "--features", str(self.features),
                "--profile", str(self.profile), "--out", str(self.out), "--check",
            ])
        self.assertEqual(before, sorted(path.relative_to(self.root).as_posix() for path in self.root.rglob("*")))
        self.assertEqual(saved, self.out.read_bytes() if self.out.exists() else None)
        return code, output.getvalue()

    def test_check_passes_on_the_rendered_register(self) -> None:
        self.assertEqual(0, self.render()[0])
        code, output = self.check()
        self.assertEqual(0, code, output)
        self.assertIn("matches the 2 scenarios rendered from the feature files", output)

    def test_check_names_the_first_drifted_scenario_and_its_feature_line(self) -> None:
        feature = (self.features / "product.feature").as_posix()
        self.assertEqual(0, self.render()[0])
        rendered = self.out.read_bytes()
        register = json.loads(rendered)
        register["tests"][1]["scenarios"][0]["execution"]["assertions"]["ASSERT-002"] = "PO-7 is closed"
        hand_edited = json.dumps(register, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        extra = copy.deepcopy(json.loads(rendered))
        extra["tests"][0]["scenarios"].append(dict(extra["tests"][0]["scenarios"][0], id="TEST-001/hand-added"))
        cases = {
            "hand-edited register": (
                None, hand_edited.encode("utf-8"),
                f"scenario TEST-002/over-receipt-is-refused ({feature}:14) differs from its feature file"),
            "feature edited without a re-render": (
                FEATURE.replace("Then PO-7 is closed", "Then PO-7 is marked closed"), rendered,
                f"scenario TEST-001/receive-the-full-quantity ({feature}:8) differs from its feature file"),
            "scenario added without a re-render": (
                FEATURE + "\n  @TEST-001\n  Scenario: Receive in two parts\n"
                "    When the clerk receives 4 units against PO-7\n    Then PO-7 stays open\n", rendered,
                f"scenario TEST-001/receive-in-two-parts ({feature}:20) is missing"),
            "scenario only in the register": (
                None, (json.dumps(extra, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"),
                "scenario TEST-001/hand-added is in no feature file"),
            "line endings converted": (
                None, rendered.replace(b"\n", b"\r\n"), "differs only in line endings"),
            "reformatted register": (
                None, (json.dumps(json.loads(rendered), indent=4, sort_keys=True) + "\n").encode("utf-8"),
                "differs from the rendered bytes"),
        }
        for label, (feature_text, register_bytes, fragment) in cases.items():
            with self.subTest(label):
                (self.features / "product.feature").write_text(feature_text or FEATURE, encoding="utf-8")
                self.out.write_bytes(register_bytes)
                code, output = self.check()
                self.assertEqual(1, code, output)
                self.assertIn(fragment, output)
                self.assertEqual(1, len(output.splitlines()), output)

    def test_check_reports_a_prd_change_and_a_missing_register(self) -> None:
        self.assertEqual(0, self.render()[0])
        self.prd.write_text(PRD + "\nA later note.\n", encoding="utf-8")
        code, output = self.check()
        self.assertEqual(1, code, output)
        self.assertIn("prd_sha256 differs from the rendered register", output)
        self.out.unlink()
        code, output = self.check()
        self.assertEqual(1, code, output)
        self.assertIn("cannot read", output)
        self.assertFalse(self.out.exists())

    def test_check_still_reports_render_findings(self) -> None:
        (self.features / "product.feature").write_text(FEATURE.replace("@TEST-002 ", "@TEST-009 "), encoding="utf-8")
        code, output = self.check()
        self.assertEqual(1, code, output)
        self.assertIn("TEST-009 is not a TEST ID in the PRD", output)

    def test_bad_arguments_exit_2(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as missing_flag:
                render_main(["--prd", str(self.prd)])
            with self.assertRaises(SystemExit) as missing_dir:
                render_main(["--prd", str(self.prd), "--features", str(self.root / "absent"),
                             "--profile", str(self.profile), "--out", str(self.out)])
        self.assertEqual(2, missing_flag.exception.code)
        self.assertEqual(2, missing_dir.exception.code)


if __name__ == "__main__":
    unittest.main()
