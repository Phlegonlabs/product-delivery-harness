#!/usr/bin/env python3
"""Focused delivery-acceptance CLI fixtures."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_delivery_acceptance as checker  # noqa: E402


CANDIDATE = "a" * 40
CONFIG = "b" * 64
EVIDENCE = b"synthetic delivery evidence\n"
EVIDENCE_SHA = hashlib.sha256(EVIDENCE).hexdigest()

PRD = """# PRD: Fixture

## Test Obligations

| Test ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-001 | Verify required fixture journeys | integration | Yes | PRD-001 | Exact scenario evidence passes |
| TEST-002 | Optional diagnostic | reliability | No | PRD-001 | Optional rows do not establish coverage |
"""


def contract() -> dict[str, Any]:
    return {
        "schema": "delivery-acceptance/1",
        "prd_sha256": "",
        "tests": [
            {
                "test_id": "TEST-001",
                "scenarios": [
                    {
                        "id": "web-mock",
                        "execution": execution(),
                        "platform": "web",
                        "auth_mode": "mock",
                        "environment": "local",
                        "build": {"build_id": "fixture-web-1", "config_digest": CONFIG},
                        "fixtures": [
                            {
                                "namespace": "synthetic-delivery-0001",
                                "setup_authority": "test environment operator",
                                "cleanup_authority": "test environment operator",
                                "owned_resources": ["owned:delivery-0001/user"],
                                "production": False,
                                "auth_bypass": False,
                            }
                        ],
                    },
                    {
                        "id": "api-real",
                        "execution": execution(),
                        "platform": "api",
                        "auth_mode": "real",
                        "environment": "test",
                        "build": {"build_id": "fixture-api-1", "config_digest": CONFIG},
                        "fixtures": [],
                    },
                ],
            }
        ],
    }


def execution() -> dict[str, Any]:
    return {"target": "local synthetic test server", "device": "desktop browser",
            "os": "test OS image 1", "persona": {"role": "member", "tenant": "synthetic-a",
            "account_state": "active synthetic account"}, "initial_data": "empty tenant",
            "actions": ["sign in", "create item"], "assertions": {"A1": "item persisted in own tenant"},
            "expected_side_effects": "one local database item; no external sends",
            "dependency_mode": "sandbox authentication, deterministic adapters"}


def results() -> dict[str, Any]:
    rows = [
        {
            "test_id": "TEST-001",
            "scenario_id": "web-mock",
            "execution": execution(), "assertion_results": {"A1": "pass"}, "fixture_cleanup": "cleaned",
            "platform": "web",
            "auth_mode": "mock",
            "environment": "local",
            "build": {"build_id": "fixture-web-1", "config_digest": CONFIG},
            "status": "pass",
            "evidence": {"path": "evidence/web.txt", "sha256": EVIDENCE_SHA},
        },
        {
            "test_id": "TEST-001",
            "scenario_id": "api-real",
            "execution": execution(), "assertion_results": {"A1": "pass"}, "fixture_cleanup": "not_required",
            "platform": "api",
            "auth_mode": "real",
            "environment": "test",
            "build": {"build_id": "fixture-api-1", "config_digest": CONFIG},
            "status": "pass",
            "evidence": {"path": "evidence/api.txt", "sha256": EVIDENCE_SHA},
        },
    ]
    return {"schema": "delivery-results/1", "candidate_sha": CANDIDATE, "results": rows}


def invoke(
    contract_value: dict[str, Any] | None = None,
    result_value: dict[str, Any] | None = None,
    *,
    contract_bytes: bytes | None = None,
    prd_text: str = PRD,
    expected_hash: str | None = None,
) -> tuple[int, dict[str, Any]]:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        evidence_dir = root / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "web.txt").write_bytes(EVIDENCE)
        (evidence_dir / "api.txt").write_bytes(EVIDENCE)
        prd = root / "PRD.md"
        prd.write_text(prd_text, encoding="utf-8")
        value = contract() if contract_value is None else contract_value
        value["prd_sha256"] = hashlib.sha256(prd.read_bytes()).hexdigest()
        raw_contract = (
            json.dumps(value, sort_keys=True).encode("utf-8")
            if contract_bytes is None
            else contract_bytes
        )
        contract_path = root / "contract.json"
        results_path = root / "results.json"
        contract_path.write_bytes(raw_contract)
        results_path.write_text(
            json.dumps(results() if result_value is None else result_value),
            encoding="utf-8",
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = checker.main(
                [
                    "--repo-root",
                    str(root),
                    "--prd",
                    str(prd),
                    "--contract",
                    str(contract_path),
                    "--contract-sha256",
                    expected_hash or hashlib.sha256(raw_contract).hexdigest(),
                    "--results",
                    str(results_path),
                    "--candidate-sha",
                    CANDIDATE,
                ]
            )
        return status, json.loads(output.getvalue())


class DeliveryAcceptanceTests(unittest.TestCase):
    def test_unauthenticated_scenario_does_not_require_invented_login(self):
        value = contract()
        observed = results()
        value["tests"][0]["scenarios"][1]["auth_mode"] = "none"
        observed["results"][1]["auth_mode"] = "none"
        self.assertEqual(0, invoke(value, observed)[0])

    def test_legitimate_todo_and_pending_domain_text_is_allowed(self):
        for text in ("TEST-TODO-001", "pending invitation awaiting verification",
                     "todo-api-build-2026.09", "evidence/pending-orders.txt", "owned:todo-item/1",
                     "latency < 200 ms"):
            errors = []
            self.assertEqual(text, checker._string(text, "domain text", errors))
            self.assertEqual([], errors)
        value = contract()
        observed = results()
        for record in (value["tests"][0]["scenarios"][0], observed["results"][0]):
            record["build"]["build_id"] = "todo-api-build-2026.09"
            record["execution"]["persona"]["account_state"] = "pending invitation awaiting verification"
        self.assertEqual(0, invoke(value, observed)[0])

    def test_placeholder_build_authority_ids_and_resource_handles_fail(self):
        for field in ("build_id", "setup_authority", "cleanup_authority", "id", "owned_resources"):
            value = contract()
            scenario = value["tests"][0]["scenarios"][0]
            if field == "build_id":
                scenario["build"][field] = "TBD"
            elif field == "id":
                scenario[field] = "<scenario>"
            elif field == "owned_resources":
                scenario["fixtures"][0][field] = ["owned:TBD"]
            else:
                scenario["fixtures"][0][field] = "<grant>"
            with self.subTest(field=field):
                self.assertEqual(1, invoke(value)[0])

    def test_vacuous_build_exception_fails(self):
        value = contract()
        value["tests"][0]["scenarios"][0]["build"] = {"not_applicable_reason": "not applicable"}
        self.assertEqual(1, invoke(value)[0])

    def test_parent_frozen_hash_cannot_be_replaced_by_results(self):
        status, payload = invoke(expected_hash="f" * 64)
        self.assertEqual(1, status)
        self.assertIn("contract bytes do not match", " ".join(payload["errors"]))

    def test_link_guard_does_not_need_symlink_privilege(self):
        with patch.object(Path, "is_symlink", return_value=True):
            self.assertEqual(1, invoke()[0])

    def test_optional_failure_is_not_a_required_failure_but_must_be_honest(self):
        frozen = contract()
        frozen["tests"].append(dict(frozen["tests"][0], test_id="TEST-002"))
        value = results()
        value["results"].append(dict(value["results"][0], test_id="TEST-002", status="fail",
                                     assertion_results={"A1": "fail"}, fixture_cleanup="cleaned"))
        self.assertEqual(0, invoke(frozen, value)[0])

    def test_optional_results_still_need_well_formed_observations(self):
        frozen = contract()
        frozen["tests"].append(dict(frozen["tests"][0], test_id="TEST-002"))
        value = results()
        row = dict(value["results"][0], test_id="TEST-002", assertion_results={})
        value["results"].append(row)
        self.assertEqual(1, invoke(frozen, value)[0])

    def test_placeholder_context_rejected(self):
        for placeholder in ("TBD", "TODO", "pending", "placeholder", "n/a"):
            value = contract()
            value["tests"][0]["scenarios"][0]["execution"]["device"] = placeholder
            self.assertEqual(1, invoke(value)[0])

    def test_deep_json_and_oversized_integer_fail_as_json(self):
        for raw in (b'{"x":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}',
                    b'{"x":' + b'1' * 5000 + b'}'):
            status, payload = invoke(contract_bytes=raw)
            self.assertEqual(1, status)
            self.assertEqual("FAIL", payload["status"])

    def test_empty_results_never_cover_required_scenarios(self):
        value = results()
        value["results"] = []
        status, payload = invoke(result_value=value)
        self.assertEqual(1, status)
        self.assertIn("has no exact passing evidence", " ".join(payload["errors"]))

    def test_context_assertions_cleanup_and_required_status_fail_closed(self):
        for field, replacement in (("execution", dict(execution(), os="different OS")),
                                   ("assertion_results", {}), ("assertion_results", {"A1": "fail"}),
                                   ("fixture_cleanup", "failed"), ("status", "blocked"),
                                   ("status", "skipped"), ("status", "unvalidated")):
            with self.subTest(field=field, value=replacement):
                value = results()
                value["results"][0][field] = replacement
                self.assertEqual(1, invoke(result_value=value)[0])

    def test_missing_native_scenario_cannot_pass(self):
        value = contract()
        native = dict(value["tests"][0]["scenarios"][1], id="ios-real", platform="ios")
        value["tests"][0]["scenarios"].append(native)
        status, payload = invoke(value)
        self.assertEqual(1, status)
        self.assertIn("TEST-001/ios-real", " ".join(payload["errors"]))

    def test_malformed_execution_fails_without_traceback(self):
        for replacement in (None, [], {}, dict(execution(), assertions=[]), dict(execution(), persona=None)):
            with self.subTest(value=replacement):
                value = contract()
                value["tests"][0]["scenarios"][0]["execution"] = replacement
                self.assertEqual(1, invoke(value)[0])

    def test_other_section_cannot_supply_missing_obligation_table(self):
        self.assertEqual(1, invoke(prd_text=PRD.replace("| Test ID", "## Other\n\n| Test ID"))[0])

    def test_exact_frozen_contract_and_matching_passes_pass(self) -> None:
        status, payload = invoke()
        self.assertEqual(0, status)
        self.assertEqual("PASS", payload["status"])
        self.assertEqual(["TEST-001"], payload["required_tests"])
        self.assertEqual(2, len(payload["matched_scenarios"]))

    def test_missing_stale_mock_native_production_and_malformed_fail(self) -> None:
        missing = results()
        missing["results"].pop()

        stale = results()
        stale["candidate_sha"] = "c" * 40

        mock = results()
        mock["results"][1]["auth_mode"] = "mock"

        native = contract()
        native["tests"][0]["scenarios"][1]["platform"] = "ios"
        native["tests"][0]["scenarios"][1]["build"] = {
            "not_applicable_reason": "no installed native artifact is available"
        }
        native_results = results()
        native_results["results"][1]["platform"] = "ios"
        native_results["results"][1]["build"] = {
            "not_applicable_reason": "no installed native artifact is available"
        }

        production = contract()
        production["tests"][0]["scenarios"][0]["fixtures"][0]["production"] = True

        cases = (
            ("missing", None, missing, "has no exact passing evidence"),
            ("stale", None, stale, "does not match the expected candidate"),
            ("mock", None, mock, "identity does not match frozen scenario"),
            ("native", native, native_results, "identity is required for native"),
            ("production", production, None, "production must be false"),
            (
                "malformed",
                None,
                None,
                "duplicate JSON key",
            ),
        )
        for label, contract_value, result_value, expected in cases:
            with self.subTest(label):
                raw = b'{"schema":"duplicate","schema":"duplicate"}'
                status, payload = invoke(
                    contract_value,
                    result_value,
                    contract_bytes=raw if label == "malformed" else None,
                )
                self.assertEqual(1, status)
                self.assertEqual("FAIL", payload["status"])
                self.assertIn(expected, " ".join(payload["errors"]))

    def test_duplicate_prd_required_rows_fail(self) -> None:
        row = "| TEST-001 | Verify required fixture journeys | integration | Yes | PRD-001 | Exact scenario evidence passes |"
        status, payload = invoke(prd_text=PRD.replace(row, row + "\n" + row))
        self.assertEqual(1, status)
        self.assertIn("duplicates TEST-001", " ".join(payload["errors"]))

    def test_required_prd_id_cannot_be_removed_from_the_contract(self) -> None:
        stale = contract()
        stale["tests"].clear()
        status, payload = invoke(stale)
        self.assertEqual(1, status)
        self.assertIn(
            "required TEST-001 is absent from the frozen contract",
            " ".join(payload["errors"]),
        )

    def test_evidence_paths_and_artifacts_are_strictly_bounded(self) -> None:
        traversal = results()
        traversal["results"][0]["evidence"]["path"] = "../../outside.txt"

        secret = results()
        secret["results"][0]["evidence"]["path"] = "evidence/token.json"

        stale_hash = results()
        stale_hash["results"][0]["evidence"]["sha256"] = "d" * 64

        cases = (
            ("traversal", traversal, "cannot be read safely"),
            ("secret-name", secret, "cannot be read safely"),
            ("stale-hash", stale_hash, "does not match the evidence artifact"),
        )
        for label, value, expected in cases:
            with self.subTest(label):
                status, payload = invoke(result_value=value)
                self.assertEqual(1, status)
                self.assertIn(expected, " ".join(payload["errors"]))


if __name__ == "__main__":
    unittest.main()
