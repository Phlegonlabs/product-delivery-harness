#!/usr/bin/env python3
"""Structured code-security reviewer result tests."""

from __future__ import annotations

import copy
import json
import sys
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from security_review_result import (  # noqa: E402
    SecurityReviewResultError,
    load_security_review_result,
    security_result_finding_summaries,
    validate_security_review_result,
)
import harness_transition  # noqa: E402
import new_run  # noqa: E402
from harness_manifest import (  # noqa: E402
    ManifestError,
    load_plan,
    plan_digest,
    validate_run,
)


HEAD = "a" * 40
BASE = "b" * 40
SCOPE = ["src/example/**"]
PLAN_TEMPLATE = (
    SCRIPTS_DIR.parent / "assets" / "templates" / "HARNESS_PLAN.template.md"
)


def valid_result(
    reviewed_sha: str = HEAD, base_sha: str = BASE
) -> dict[str, object]:
    return {
        "review_type": "security",
        "decision": "pass",
        "reviewed_sha": reviewed_sha,
        "base_sha": base_sha,
        "scope": SCOPE,
        "exclusions": [],
        "trust_boundaries": ["public input to privileged storage"],
        "tools": [
            {
                "name": "manual source review",
                "status": "passed",
                "evidence": "reviewed entry points and sensitive sinks",
            }
        ],
        "coverage": {
            "status": "complete",
            "reviewed": ["application source and configuration"],
            "gaps": [],
        },
        "findings": [],
        "evidence": [f"reviewed exact SHA {reviewed_sha}"],
    }


def validate(value: dict[str, object], **overrides: object) -> list[str]:
    return validate_security_review_result(
        value,
        expected_decision=overrides.get("expected_decision", "pass"),
        expected_reviewed_sha=overrides.get("expected_reviewed_sha", HEAD),
        expected_base_sha=overrides.get("expected_base_sha", BASE),
        expected_scope=overrides.get("expected_scope", SCOPE),
        required_tools=overrides.get("required_tools", []),
        allowed_decisions=overrides.get(
            "allowed_decisions",
            ["pass", "fix_required", "blocked", "contract_gap", "retryable_failure"],
        ),
    )


class SecurityReviewResultTests(unittest.TestCase):
    def test_complete_exact_sha_pass_is_valid(self) -> None:
        self.assertEqual([], validate(valid_result()))

    def test_wrong_sha_scope_and_partial_coverage_are_rejected(self) -> None:
        result = valid_result()
        result["reviewed_sha"] = "c" * 40
        result["scope"] = ["other/**"]
        result["coverage"] = {
            "status": "partial",
            "reviewed": ["application source"],
            "gaps": ["dependency advisories unavailable"],
        }

        errors = validate(result)

        self.assertTrue(any("reserved reviewed SHA" in item for item in errors))
        self.assertTrue(any("PLAN review scope" in item for item in errors))
        self.assertTrue(any("PASS requires complete" in item for item in errors))

    def test_required_tool_must_be_present_and_usable(self) -> None:
        result = valid_result()
        result["tools"] = [
            {
                "name": "dependency audit",
                "status": "unavailable",
                "evidence": "offline environment",
            }
        ]

        errors = validate(result, required_tools=["dependency audit"])

        self.assertTrue(any("required tools did not run" in item for item in errors))

    def test_high_finding_cannot_pass(self) -> None:
        result = valid_result()
        result["findings"] = [
            {
                "severity": "high",
                "confidence": "high",
                "cwe": "CWE-78",
                "location": "src/run.py:20",
                "summary": "Untrusted input reaches a shell",
                "source_to_sink": "request argument to subprocess shell",
                "preconditions": "attacker can call the endpoint",
                "impact": "arbitrary command execution",
                "counterevidence": "no allowlist or escaping",
                "remediation": "use an argv array and allowlisted command",
                "remediation_test": "metacharacters remain literal",
            }
        ]

        self.assertTrue(
            any("critical or high" in item for item in validate(result))
        )

    def test_exclusions_cannot_pass(self) -> None:
        result = valid_result()
        result["exclusions"] = ["generated artifacts"]

        self.assertTrue(
            any("PASS cannot retain exclusions" in item for item in validate(result))
        )

    def test_nonpass_result_produces_parent_finding_summaries(self) -> None:
        result = valid_result()
        result["decision"] = "blocked"
        result["coverage"] = {
            "status": "partial",
            "reviewed": ["application source"],
            "gaps": ["required dependency audit unavailable"],
        }

        errors = validate(result, expected_decision="blocked")

        self.assertEqual([], errors)
        self.assertEqual(
            ["required dependency audit unavailable"],
            security_result_finding_summaries(result),
        )

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            path.write_text('{"review_type":"security","review_type":"other"}')

            with self.assertRaises(SecurityReviewResultError):
                load_security_review_result(path)

    def test_decision_must_match_the_recorded_outcome(self) -> None:
        result = copy.deepcopy(valid_result())

        errors = validate(result, expected_decision="blocked")

        self.assertTrue(any("recorded review outcome" in item for item in errors))

    def test_malformed_scalars_return_errors_without_crashing(self) -> None:
        result = valid_result()
        result["decision"] = []
        result["tools"][0]["status"] = {}
        result["coverage"]["status"] = []
        result["findings"] = [
            {
                "severity": {},
                "confidence": [],
                "cwe": None,
                "location": "src/run.py:20",
                "summary": "invalid scalar fixture",
                "source_to_sink": "source to sink",
                "preconditions": "none",
                "impact": "unknown",
                "counterevidence": "none",
                "remediation": "validate types",
                "remediation_test": "malformed values return errors",
            }
        ]

        self.assertTrue(
            validate(result, required_tools=["manual source review"])
        )


class SecurityReviewTransitionTests(unittest.TestCase):
    def state(self) -> tuple[dict[str, object], dict[str, object]]:
        repo_temp = tempfile.TemporaryDirectory()
        self.addCleanup(repo_temp.cleanup)
        repo_root = Path(repo_temp.name)
        for command in (
            ["git", "init", "-q", "-b", "security-result"],
            ["git", "config", "user.email", "test@example.com"],
            ["git", "config", "user.name", "Harness Test"],
        ):
            subprocess.run(command, cwd=repo_root, check=True, capture_output=True, text=True)
        source = repo_root / "src" / "example" / "app.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("print('fixture')\n", encoding="utf-8")
        subprocess.run(["git", "add", "src/example/app.py"], cwd=repo_root, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "security fixture"],
            cwd=repo_root,
            check=True,
        )
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
        ).strip()
        self._security_repo_root = repo_root
        self._security_head = head
        plan = load_plan(PLAN_TEMPLATE)
        run = new_run.build_run(
            plan,
            run_id="RUN-security-result",
            branch="refs/heads/security-result",
        )
        node = next(
            item
            for item in plan["graph"]["nodes"]
            if item["id"] == "N-SECURITY-REVIEW"
        )
        run["integration"]["batch_base_sha"] = head
        run["integration"]["integration_head_sha"] = head
        run["observed"]["git"].update(
            {
                "parent_worktree_path": str(repo_root),
                "parent_branch": "security-result",
                "parent_head_sha": head,
                "parent_dirty": False,
            }
        )
        run["graph_state"]["node_states"][node["id"]].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-SECURITY",
                "last_outcome": None,
                "bound_worker_id": "RW-SECURITY",
                "blockers": [],
            }
        )
        run["review_workers"].append(
            {
                "worker_id": "RW-SECURITY",
                "node_id": node["id"],
                "attempt_id": "ATT-SECURITY",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": head,
                "base_sha": head,
                "review_path": str(repo_root),
                "worker_runtime": "subagent",
                "completion_channel": "agent_result",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "subagents",
                    "source": "host",
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "medium",
                    "option_source": "plan_provider_options",
                },
                "task_thread_id": None,
                "report_path": None,
                "phase": "leased",
                "outcome": None,
                "findings": [],
            }
        )
        return plan, run

    def args(self, path: Path | None) -> Namespace:
        return Namespace(
            lineage="REVIEW-SECURITY",
            attempt_id="ATT-SECURITY",
            worker_id="RW-SECURITY",
            mission_id=None,
            result="pass",
            evidence=["security reviewer completed"],
            finding=None,
            security_result=path,
            failure_family_id=None,
            failure_primitive=None,
            equivalence_class=None,
            strategy=None,
            tree_sha=None,
            repo_root=self._security_repo_root,
        )

    def write_result(self, directory: str, value: dict[str, object]) -> Path:
        path = Path(directory) / "security-result.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_record_requires_and_persists_exact_structured_result(self) -> None:
        plan, run = self.state()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_result(
                temp, valid_result(self._security_head, self._security_head)
            )

            harness_transition._record_review_attempt(
                plan, run, self.args(path)
            )

        worker = run["review_workers"][0]
        self.assertEqual("worker_passed", worker["phase"])
        self.assertEqual(self._security_head, worker["security_result"]["reviewed_sha"])
        self.assertTrue(
            any(
                item.startswith("security_result_sha256:")
                for item in run["attempt_log"][0]["evidence"]
            )
        )
        worker["security_result"]["reviewed_sha"] = "c" * 40
        self.assertTrue(
            any(
                "security_result" in item and "reserved reviewed SHA" in item
                for item in validate_run(plan, run)
            )
        )
        worker["security_result"]["reviewed_sha"] = self._security_head
        worker["security_result"]["base_sha"] = "d" * 40
        self.assertTrue(
            any(
                "security_result" in item and "dispatched base SHA" in item
                for item in validate_run(plan, run)
            )
        )

    def test_record_rejects_missing_or_wrong_sha_result(self) -> None:
        plan, run = self.state()
        with self.assertRaisesRegex(ManifestError, "--security-result"):
            harness_transition._record_review_attempt(
                plan, run, self.args(None)
            )

        plan, run = self.state()
        result = valid_result(self._security_head, self._security_head)
        result["reviewed_sha"] = "c" * 40
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_result(temp, result)
            with self.assertRaisesRegex(ManifestError, "reserved reviewed SHA"):
                harness_transition._record_review_attempt(
                    plan, run, self.args(path)
                )

    def test_record_rejects_pass_with_exclusions(self) -> None:
        plan, run = self.state()
        result = valid_result(self._security_head, self._security_head)
        result["exclusions"] = ["generated artifacts"]
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_result(temp, result)
            with self.assertRaisesRegex(ManifestError, "PASS cannot retain exclusions"):
                harness_transition._record_review_attempt(
                    plan, run, self.args(path)
                )

    def test_interrupted_security_review_reconciles_without_a_result(self) -> None:
        plan, run = self.state()

        harness_transition._reconcile_interrupted_reviews(
            plan,
            run,
            Namespace(
                worker_id=["RW-SECURITY"],
                reason="review process stopped before returning a result",
                source="user stopped review",
            ),
        )

        self.assertEqual([], validate_run(plan, run))
        worker = run["review_workers"][0]
        self.assertEqual("blocked", worker["phase"])
        self.assertNotIn("security_result", worker)
        attempt = run["attempt_log"][-1]
        self.assertIn(
            harness_transition.INTERRUPTED_REVIEW_RECEIPT,
            attempt["evidence"],
        )
        state = run["graph_state"]["node_states"]["N-SECURITY-REVIEW"]
        self.assertEqual("dormant", state["phase"])
        self.assertEqual("paused", run["control"]["desired_state"])

    def test_blocked_security_review_cannot_forge_interruption_without_receipt(self) -> None:
        plan, run = self.state()
        worker = run["review_workers"][0]
        worker["phase"] = "blocked"
        worker["outcome"] = "blocked"
        run["attempt_log"].append(
            {
                "attempt_id": worker["attempt_id"],
                "mission_id": None,
                "task_id": None,
                "lease_id": None,
                "kind": "review",
                "result": "blocked",
                "evidence": ["review returned blocked without a structured result"],
                "review_lineage_id": "REVIEW-SECURITY",
                "failure_family_ids": [],
            }
        )

        errors = validate_run(plan, run)

        self.assertTrue(
            any("terminal security review requires its structured result" in error for error in errors),
            errors,
        )


if __name__ == "__main__":
    unittest.main()
