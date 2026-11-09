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
import manifest_fixtures as mf  # noqa: E402


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
    extra: tuple[str, ...] = (),
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
                    *extra,
                ]
            )
        return status, json.loads(output.getvalue())


def production_scenario(name: str) -> dict[str, Any]:
    return {
        "id": name,
        "execution": execution(),
        "platform": "web",
        "auth_mode": "real",
        "environment": "production",
        "build": {"build_id": "fixture-prod-1", "config_digest": CONFIG},
        "fixtures": [],
    }


def production_row(name: str, status: str = "blocked", test_id: str = "TEST-001") -> dict[str, Any]:
    return {
        "test_id": test_id,
        "scenario_id": name,
        "execution": execution(),
        "assertion_results": {"A1": "pass" if status == "pass" else status},
        "fixture_cleanup": "not_required",
        "platform": "web",
        "auth_mode": "real",
        "environment": "production",
        "build": {"build_id": "fixture-prod-1", "config_digest": CONFIG},
        "status": status,
        "evidence": {"path": "evidence/web.txt", "sha256": EVIDENCE_SHA},
    }


def with_production(*rows: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """The base register plus a production scenario for each row, in row order."""

    frozen = contract()
    observed = results()
    for row in rows:
        frozen["tests"][0]["scenarios"].append(production_scenario(row["scenario_id"]))
        observed["results"].append(row)
    return frozen, observed


class DeliveryAcceptanceTests(unittest.TestCase):
    def test_full_stack_required_assertions_cannot_be_replaced_by_mock_or_summary(self):
        frozen = contract()
        observed = results()
        expected = {"AUTH": "real sandbox login", "DENY": "other tenant rejected",
                    "DATA": "saved data survives a separate read", "RETRY": "retry creates exactly one item"}
        for scenario in frozen["tests"][0]["scenarios"]:
            scenario["execution"]["assertions"] = expected.copy()
        for row in observed["results"]:
            row["execution"]["assertions"] = expected.copy()
            row["assertion_results"] = {key: "pass" for key in expected}
        self.assertEqual(0, invoke(frozen, observed)[0])
        for change in ("summary", "mock", "stale", "skipped", "missing"):
            import copy
            mutated = copy.deepcopy(observed)
            row = mutated["results"][1]
            if change == "summary":
                row["assertion_results"] = {"SUMMARY": "pass"}
            elif change == "mock":
                row["auth_mode"] = "mock"
            elif change == "stale":
                mutated["candidate_sha"] = "c" * 40
            elif change == "skipped":
                row["status"] = "skipped"
            else:
                row["assertion_results"].pop("DATA")
            with self.subTest(change=change):
                self.assertEqual(1, invoke(frozen, mutated)[0])

    def test_embedded_placeholders_cannot_claim_concrete_identity(self):
        for value in ('release-<build-id>', 'Chrome <version>', 'grant <id>',
                      'owned:run/<resource>', 'prefix <actual device> suffix'):
            with self.subTest(value=value):
                self.assertFalse(checker.concrete_text(value))
        frozen = contract()
        observed = results()
        for record in (frozen['tests'][0]['scenarios'][0], observed['results'][0]):
            record['build']['build_id'] = 'release-<build-id>'
        self.assertEqual(1, invoke(frozen, observed)[0])

    def test_evidence_is_relative_but_cli_inputs_may_be_absolute(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'evidence').mkdir()
            artifact = root / 'evidence' / 'run.txt'
            artifact.write_bytes(EVIDENCE)
            errors = []
            self.assertFalse(checker._evidence(root, {
                'path': str(artifact), 'sha256': EVIDENCE_SHA}, 'evidence', errors, 'evidence'))
            self.assertTrue(errors)
            self.assertTrue(checker._evidence(root, {
                'path': 'evidence/run.txt', 'sha256': EVIDENCE_SHA}, 'evidence', [], 'evidence'))
        self.assertEqual(0, invoke()[0])

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

    def test_desktop_platforms_need_a_build_identity(self):
        for platform in ("windows", "linux"):
            with self.subTest(platform=platform):
                value = contract()
                value["tests"][0]["scenarios"][1]["platform"] = platform
                value["tests"][0]["scenarios"][1]["build"] = {
                    "not_applicable_reason": "no installed native artifact is available"
                }
                status, payload = invoke(value)
                self.assertEqual(1, status)
                errors = " ".join(payload["errors"])
                self.assertIn("identity is required for native", errors)
                self.assertNotIn("platform must be", errors)

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

        # A readable, hash-matching file outside the evidence root still fails.
        outside = results()
        outside["results"][0]["evidence"]["path"] = "PRD.md"
        outside["results"][0]["evidence"]["sha256"] = hashlib.sha256(
            PRD.encode("utf-8")).hexdigest()

        cases = (
            ("outside-root", outside, "PRD.md must be under evidence/"),
            ("traversal", traversal, "cannot be read safely"),
            ("secret-name", secret, "cannot be read safely"),
            ("stale-hash", stale_hash, "does not match the evidence artifact"),
        )
        for label, value, expected in cases:
            with self.subTest(label):
                status, payload = invoke(result_value=value)
                self.assertEqual(1, status)
                self.assertIn(expected, " ".join(payload["errors"]))


class ProductionSmokeTests(unittest.TestCase):
    """Production scenarios run after landing: deferred before, required after."""

    COMPLETE = ("--production-smoke-complete",)

    def test_nothing_deferred_reports_an_empty_list(self) -> None:
        status, payload = invoke()
        self.assertEqual(0, status)
        self.assertEqual([], payload["production_smoke_deferred"])
        status, payload = invoke(extra=self.COMPLETE)
        self.assertEqual(0, status)
        self.assertEqual([], payload["production_smoke_deferred"])

    def test_blocked_production_row_is_deferred_before_landing(self) -> None:
        frozen, observed = with_production(production_row("prod-smoke"))
        status, payload = invoke(frozen, observed)
        self.assertEqual((0, "PASS", []), (status, payload["status"], payload["errors"]))
        self.assertEqual(["TEST-001/prod-smoke"], payload["production_smoke_deferred"])
        self.assertEqual(["TEST-001/api-real", "TEST-001/web-mock"], payload["matched_scenarios"])
        self.assertIn("TEST-001/prod-smoke", payload["required_scenarios"])

    def test_post_landing_run_refuses_the_blocked_production_row(self) -> None:
        frozen, observed = with_production(production_row("prod-smoke"))
        status, payload = invoke(frozen, observed, extra=self.COMPLETE)
        self.assertEqual(1, status)
        self.assertIn("required TEST-001/prod-smoke status must be pass", payload["errors"])
        self.assertEqual([], payload["production_smoke_deferred"])

    def test_missing_production_row_is_never_deferred(self) -> None:
        frozen, observed = with_production(production_row("prod-smoke"))
        observed["results"].pop()
        for extra in ((), self.COMPLETE):
            with self.subTest(extra=extra):
                status, payload = invoke(frozen, observed, extra=extra)
                self.assertEqual(1, status)
                self.assertIn("required TEST-001/prod-smoke has no exact passing evidence",
                              payload["errors"])
                self.assertEqual([], payload["production_smoke_deferred"])

    def test_other_production_statuses_still_fail_before_landing(self) -> None:
        for state in ("fail", "skipped", "unvalidated"):
            with self.subTest(status=state):
                frozen, observed = with_production(production_row("prod-smoke", state))
                status, payload = invoke(frozen, observed)
                self.assertEqual(1, status)
                self.assertIn("required TEST-001/prod-smoke status must be pass", payload["errors"])
                self.assertEqual([], payload["production_smoke_deferred"])

    def test_blocked_non_production_row_still_fails(self) -> None:
        frozen, observed = with_production(production_row("prod-smoke"))
        for scenario_id, position in (("web-mock", 0), ("api-real", 1)):
            with self.subTest(scenario=scenario_id):
                changed = json.loads(json.dumps(observed))
                changed["results"][position]["status"] = "blocked"
                changed["results"][position]["assertion_results"] = {"A1": "blocked"}
                status, payload = invoke(frozen, changed)
                self.assertEqual(1, status)
                text = " ".join(payload["errors"])
                self.assertIn(f"required TEST-001/{scenario_id} status must be pass", text)
                self.assertNotIn("TEST-001/prod-smoke status", text)

    def test_blocked_production_row_still_needs_its_evidence_file(self) -> None:
        frozen, observed = with_production(production_row("prod-smoke"))
        observed["results"][2]["evidence"]["sha256"] = "d" * 64
        status, payload = invoke(frozen, observed)
        self.assertEqual(1, status)
        self.assertIn("does not match the evidence artifact", " ".join(payload["errors"]))

    def test_optional_blocked_production_row_is_not_listed(self) -> None:
        frozen, observed = with_production(production_row("prod-smoke", "pass"))
        frozen["tests"].append({"test_id": "TEST-002", "scenarios": [production_scenario("optional-smoke")]})
        observed["results"].append(production_row("optional-smoke", "blocked", "TEST-002"))
        status, payload = invoke(frozen, observed)
        self.assertEqual((0, []), (status, payload["production_smoke_deferred"]))

    def test_passing_production_row_is_checked_with_exact_evidence(self) -> None:
        frozen, observed = with_production(production_row("prod-smoke", "pass"))
        for extra in ((), self.COMPLETE):
            with self.subTest(extra=extra):
                status, payload = invoke(frozen, observed, extra=extra)
                self.assertEqual((0, []), (status, payload["production_smoke_deferred"]))
                self.assertIn("TEST-001/prod-smoke", payload["matched_scenarios"])
        for label, change in (("hash", {"sha256": "d" * 64}), ("path", {"path": "../outside.txt"})):
            with self.subTest(evidence=label):
                broken = json.loads(json.dumps(observed))
                broken["results"][2]["evidence"].update(change)
                for extra in ((), self.COMPLETE):
                    self.assertEqual(1, invoke(frozen, broken, extra=extra)[0])

    def test_deferred_list_is_sorted(self) -> None:
        frozen, observed = with_production(
            production_row("zeta-smoke"), production_row("alpha-smoke"), production_row("mid-smoke"))
        status, payload = invoke(frozen, observed)
        self.assertEqual(0, status)
        self.assertEqual(
            ["TEST-001/alpha-smoke", "TEST-001/mid-smoke", "TEST-001/zeta-smoke"],
            payload["production_smoke_deferred"],
        )

    def test_results_check_without_a_deferred_list_stays_strict(self) -> None:
        # check_eval_acceptance.py calls _results() and relies on the strict default.
        frozen, observed = with_production(production_row("prod-smoke"))
        scenarios, errors = checker._contract(frozen, {"TEST-001"}, {"TEST-001"})
        self.assertEqual([], errors)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "evidence").mkdir()
            (root / "evidence" / "web.txt").write_bytes(EVIDENCE)
            (root / "evidence" / "api.txt").write_bytes(EVIDENCE)
            args = (observed, scenarios, {"TEST-001"}, CANDIDATE, root, "evidence", {})
            self.assertIn("required TEST-001/prod-smoke status must be pass", checker._results(*args)[1])
            deferred: list[str] = []
            self.assertEqual([], checker._results(*args, deferred)[1])
            self.assertEqual(["TEST-001/prod-smoke"], deferred)


class CandidateTreeTests(unittest.TestCase):
    """In a Git checkout the register's candidate must carry HEAD's product tree."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name).resolve()
        mf.init_repo(self.root, "PRD.md")
        (self.root / "PRD.md").write_bytes(PRD.encode("utf-8"))
        value = contract()
        value["prd_sha256"] = hashlib.sha256(PRD.encode("utf-8")).hexdigest()
        self.contract_bytes = json.dumps(value, sort_keys=True).encode("utf-8")
        (self.root / "contract.json").write_bytes(self.contract_bytes)
        self.write("src/example/foo.py", "x = 1\n")
        # H1: the product candidate the scenarios ran against.
        self.h1 = self.commit("last mission")

    def write(self, path: str, text: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def commit(self, message: str) -> str:
        mf.git(self.root, "add", "-A")
        mf.git(self.root, "commit", "-qm", message)
        return mf.git(self.root, "rev-parse", "HEAD")

    def commit_register(self, candidate: str, *extra: str) -> str:
        (self.root / "evidence").mkdir(exist_ok=True)
        (self.root / "evidence" / "web.txt").write_bytes(EVIDENCE)
        (self.root / "evidence" / "api.txt").write_bytes(EVIDENCE)
        value = results()
        value["candidate_sha"] = candidate
        self.write("results.json", json.dumps(value))
        for path in extra:
            self.write(path, "changed with the register\n")
        return self.commit("acceptance register")

    def check(self, *candidate: str) -> tuple[int, dict[str, Any]]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = checker.main([
                "--repo-root", str(self.root),
                "--prd", "PRD.md",
                "--contract", "contract.json",
                "--contract-sha256", hashlib.sha256(self.contract_bytes).hexdigest(),
                "--results", "results.json",
                *candidate,
            ])
        return status, json.loads(output.getvalue())

    def test_register_only_commit_passes_at_the_register_head(self) -> None:
        self.commit_register(self.h1)

        status, payload = self.check("--candidate-from-head")
        self.assertEqual((0, []), (status, payload["errors"]))
        self.assertEqual(self.h1, payload["candidate_sha"])
        self.assertEqual(0, self.check("--candidate-sha", self.h1)[0])

    def test_head_comparison_uses_the_validated_evidence_bytes(self) -> None:
        self.commit_register(self.h1)
        with patch.object(checker, "_read_bytes", wraps=checker._read_bytes) as read:
            status, payload = self.check("--candidate-from-head")
        self.assertEqual((0, []), (status, payload["errors"]))
        evidence_reads = [call for call in read.call_args_list if call.args[1] == "evidence"]
        self.assertEqual(2, len(evidence_reads))

    def test_git_queries_use_one_immutable_head_sha(self) -> None:
        self.commit_register(self.h1)
        head_sha = mf.git(self.root, "rev-parse", "HEAD")
        with patch.object(checker, "run_git", wraps=checker.run_git) as git:
            status, payload = self.check("--candidate-from-head")
        self.assertEqual((0, []), (status, payload["errors"]))
        checked = [
            call.args for call in git.call_args_list
            if len(call.args) > 1 and call.args[1] in {"ls-tree", "merge-base", "diff"}
        ]
        self.assertTrue(checked)
        for arguments in checked:
            self.assertIn(head_sha, arguments)
            self.assertNotIn("HEAD", arguments)

    def test_head_move_during_check_cannot_combine_two_commits(self) -> None:
        register_head = self.commit_register(self.h1)
        original_register = (self.root / "results.json").read_bytes()
        changed = b"later evidence bytes\n"
        (self.root / "evidence" / "web.txt").write_bytes(changed)
        value = json.loads(original_register)
        value["results"][0]["evidence"]["sha256"] = hashlib.sha256(changed).hexdigest()
        self.write("results.json", json.dumps(value))
        later_head = self.commit("later register and evidence")
        mf.git(self.root, "update-ref", "HEAD", register_head, later_head)
        mf.git(self.root, "read-tree", register_head)
        (self.root / "results.json").write_bytes(original_register)
        (self.root / "evidence" / "web.txt").write_bytes(EVIDENCE)
        self.assertEqual("", mf.git(self.root, "status", "--porcelain"))
        original_git = checker.run_git
        moved = False

        def moving_git(root: Path, *arguments: str, **options: Any) -> Any:
            nonlocal moved
            if arguments[:3] == ("cat-file", "-t", self.h1) and not moved:
                mf.git(self.root, "update-ref", "HEAD", later_head, register_head)
                moved = True
            return original_git(root, *arguments, **options)

        with patch.object(checker, "run_git", side_effect=moving_git):
            status, payload = self.check("--candidate-from-head")
        self.assertTrue(moved)
        self.assertEqual(1, status)
        self.assertIn("HEAD changed during acceptance check", " ".join(payload["errors"]))

    def test_crlf_register_needs_byte_preserving_git_attributes(self) -> None:
        mf.git(self.root, "config", "core.autocrlf", "true")
        self.commit_register(self.h1)
        value = json.loads((self.root / "results.json").read_text(encoding="utf-8"))
        (self.root / "results.json").write_bytes(
            json.dumps(value, indent=2).replace("\n", "\r\n").encode("utf-8")
        )
        self.commit("format register with CRLF")
        self.assertEqual("", mf.git(self.root, "status", "--porcelain"))

        status, payload = self.check("--candidate-from-head")
        self.assertEqual(1, status)
        self.assertIn("line-ending or Git filter conversion", " ".join(payload["errors"]))

    def test_byte_preserving_git_attributes_allow_crlf_register(self) -> None:
        self.write(".gitattributes", "results.json -text -filter\nevidence/** -text -filter\n")
        candidate = self.commit("keep acceptance bytes unchanged")
        mf.git(self.root, "config", "core.autocrlf", "true")
        self.commit_register(candidate)
        value = json.loads((self.root / "results.json").read_text(encoding="utf-8"))
        (self.root / "results.json").write_bytes(
            json.dumps(value, indent=2).replace("\n", "\r\n").encode("utf-8")
        )
        self.commit("format byte-preserved register with CRLF")

        status, payload = self.check("--candidate-from-head")
        self.assertEqual((0, []), (status, payload["errors"]))

    def test_reused_evidence_path_must_not_change_between_rows(self) -> None:
        candidate = self.commit_register(self.h1)
        changed = b"alternate synthetic evidence\n"
        value = results()
        value["candidate_sha"] = candidate
        value["results"][0]["evidence"] = {
            "path": "evidence/web.txt", "sha256": hashlib.sha256(changed).hexdigest()
        }
        value["results"][1]["evidence"] = {
            "path": "evidence/web.txt", "sha256": EVIDENCE_SHA
        }
        self.write("results.json", json.dumps(value))
        self.commit("reuse evidence path")
        original_read = checker._read_bytes
        reads = 0

        def changing_read(path: Path, label: str, root: Path) -> bytes:
            nonlocal reads
            if label == "evidence" and Path(path).as_posix() == "evidence/web.txt":
                reads += 1
                return changed if reads == 1 else EVIDENCE
            return original_read(path, label, root)

        with patch.object(checker, "_read_bytes", side_effect=changing_read):
            status, payload = self.check("--candidate-from-head")
        self.assertEqual(1, status)
        self.assertIn("changed between result rows", " ".join(payload["errors"]))

    def test_ignored_evidence_cannot_satisfy_committed_head(self) -> None:
        self.write(".gitignore", "*.log\n")
        candidate = self.commit("ignore logs")
        (self.root / "evidence").mkdir(exist_ok=True)
        (self.root / "evidence" / "run.log").write_bytes(EVIDENCE)
        value = results()
        value["candidate_sha"] = candidate
        for row in value["results"]:
            row["evidence"] = {"path": "evidence/run.log", "sha256": EVIDENCE_SHA}
        self.write("results.json", json.dumps(value))
        self.commit("ignored evidence register")

        status, payload = self.check("--candidate-from-head")
        self.assertEqual(1, status)
        self.assertIn("evidence/run.log", " ".join(payload["errors"]))

    def test_uncommitted_register_bytes_cannot_satisfy_head(self) -> None:
        self.commit_register(self.h1)
        with (self.root / "results.json").open("a", encoding="utf-8") as stream:
            stream.write("\n")

        status, payload = self.check("--candidate-from-head")
        self.assertEqual(1, status)
        self.assertIn("results.json", " ".join(payload["errors"]))

    def test_uncommitted_evidence_bytes_cannot_satisfy_head(self) -> None:
        self.commit_register(self.h1)
        changed = b"different synthetic evidence\n"
        (self.root / "evidence" / "web.txt").write_bytes(changed)
        value = json.loads((self.root / "results.json").read_text(encoding="utf-8"))
        value["results"][0]["evidence"]["sha256"] = hashlib.sha256(changed).hexdigest()
        self.write("results.json", json.dumps(value))

        status, payload = self.check("--candidate-from-head")
        self.assertEqual(1, status)
        self.assertIn("evidence/web.txt", " ".join(payload["errors"]))

    def test_run_coordination_commit_after_the_register_passes(self) -> None:
        self.commit_register(self.h1)
        self.write("docs/goal/RUN.md", "# RUN\n")
        self.commit("coordination checkpoint")

        self.assertEqual(0, self.check("--candidate-from-head")[0])

    def test_product_file_in_the_register_commit_fails(self) -> None:
        # record-integration accepts this when the file is inside the last
        # mission's scope; the acceptance gate is what refuses it.
        self.commit_register(self.h1, "src/example/foo.py")

        for candidate in (["--candidate-from-head"], ["--candidate-sha", self.h1]):
            with self.subTest(candidate=candidate[0]):
                status, payload = self.check(*candidate)
                self.assertEqual(1, status)
                self.assertIn("src/example/foo.py", " ".join(payload["errors"]))

    def test_submodule_change_cannot_be_hidden_by_git_diff_config(self) -> None:
        self.commit_register(self.h1)
        mf.git(
            self.root, "update-index", "--add", "--cacheinfo",
            f"160000,{self.h1},vendor",
        )
        mf.git(self.root, "commit", "-qm", "add vendor gitlink")
        mf.git(self.root, "config", "diff.ignoreSubmodules", "all")

        status, payload = self.check("--candidate-from-head")
        self.assertEqual(1, status)
        self.assertIn("vendor", " ".join(payload["errors"]))

    def test_product_file_listed_as_evidence_cannot_exempt_itself(self) -> None:
        # The register must not exempt a product or test file that changed
        # after H1 by naming it as a row's evidence.
        self.write("src/example/foo.py", "x = 2\n")
        self.write("tests/test_foo.py", "assert True\n")
        self.commit_register(self.h1)
        value = json.loads((self.root / "results.json").read_text(encoding="utf-8"))
        for index, path in enumerate(("src/example/foo.py", "tests/test_foo.py")):
            value["results"][index]["evidence"] = {
                "path": path,
                "sha256": hashlib.sha256((self.root / path).read_bytes()).hexdigest(),
            }
        self.write("results.json", json.dumps(value))
        self.commit("register names product files as evidence")

        for candidate in (["--candidate-from-head"], ["--candidate-sha", self.h1]):
            with self.subTest(candidate=candidate[0]):
                status, payload = self.check(*candidate)
                self.assertEqual(1, status)
                text = " ".join(payload["errors"])
                self.assertIn("must be under evidence/", text)
                self.assertIn("src/example/foo.py, tests/test_foo.py", text)

    def test_evidence_root_sits_next_to_the_register(self) -> None:
        register = "docs/verification/delivery-results.json"
        (self.root / "docs/verification/evidence").mkdir(parents=True)
        (self.root / "docs/verification/evidence/web.txt").write_bytes(EVIDENCE)
        value = results()
        value["candidate_sha"] = self.h1
        for row in value["results"]:
            row["evidence"]["path"] = "docs/verification/evidence/web.txt"
        self.write(register, json.dumps(value))
        self.commit("acceptance register")
        self.assertEqual((0, []), self.check_register(register))

        # Root-level evidence/ is not this register's evidence root.
        (self.root / "evidence").mkdir()
        (self.root / "evidence" / "web.txt").write_bytes(EVIDENCE)
        for row in value["results"]:
            row["evidence"]["path"] = "evidence/web.txt"
        self.write(register, json.dumps(value))
        self.commit("evidence outside the register's root")
        status, errors = self.check_register(register)
        self.assertEqual(1, status)
        self.assertIn("must be under docs/verification/evidence/", " ".join(errors))
        self.assertIn("evidence: docs/verification/evidence/web.txt, evidence/web.txt",
                      " ".join(errors))

    def check_register(self, register: str) -> tuple[int, list[str]]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = checker.main([
                "--repo-root", str(self.root),
                "--prd", "PRD.md",
                "--contract", "contract.json",
                "--contract-sha256", hashlib.sha256(self.contract_bytes).hexdigest(),
                "--results", register,
                "--candidate-from-head",
            ])
        return status, json.loads(output.getvalue())["errors"]

    def test_unlisted_evidence_file_in_the_register_commit_fails(self) -> None:
        self.commit_register(self.h1, "evidence/unlisted.txt")

        status, payload = self.check("--candidate-from-head")
        self.assertEqual(1, status)
        self.assertIn("evidence/unlisted.txt", " ".join(payload["errors"]))

    def test_stale_register_after_a_product_repair_fails(self) -> None:
        self.commit_register(self.h1)
        self.write("src/example/foo.py", "x = 2\n")
        self.commit("security repair")

        for candidate in (["--candidate-from-head"], ["--candidate-sha", self.h1]):
            with self.subTest(candidate=candidate[0]):
                status, payload = self.check(*candidate)
                self.assertEqual(1, status)
                self.assertIn("src/example/foo.py", " ".join(payload["errors"]))

    def test_candidate_must_be_an_ancestor_commit_of_head(self) -> None:
        mf.git(self.root, "checkout", "-q", "-b", "side")
        self.write("src/example/side.py", "y = 1\n")
        side = self.commit("side branch")
        mf.git(self.root, "checkout", "-q", "main")
        cases = ((side, "is not an ancestor of HEAD"), (CANDIDATE, "is not a commit"))
        for candidate, expected in cases:
            mf.git(self.root, "reset", "-q", "--hard", self.h1)
            self.commit_register(candidate)
            for flags in (["--candidate-from-head"], ["--candidate-sha", candidate]):
                with self.subTest(expected=expected, flag=flags[0]):
                    status, payload = self.check(*flags)
                    self.assertEqual(1, status)
                    self.assertIn(expected, " ".join(payload["errors"]))

    def test_candidate_from_head_needs_a_git_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "PRD.md").write_text(PRD, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = checker.main([
                    "--repo-root", str(root), "--prd", "PRD.md",
                    "--contract", "PRD.md", "--contract-sha256", "f" * 64,
                    "--results", "PRD.md", "--candidate-from-head",
                ])
        self.assertEqual(1, status)
        self.assertIn("Git checkout", " ".join(json.loads(output.getvalue())["errors"]))

    def test_candidate_sha_and_from_head_are_exclusive(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            self.check("--candidate-sha", self.h1, "--candidate-from-head")
        self.assertEqual(2, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
