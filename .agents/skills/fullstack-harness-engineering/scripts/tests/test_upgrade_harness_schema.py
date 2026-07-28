#!/usr/bin/env python3
"""Tests for upgrade_harness_schema.py (CLI level and direct validation)."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import (  # noqa: E402
    AUTHORIZATION_KEYS_V2,
    authorization_covers,
    load_plan,
    load_run,
    plan_digest,
    validate_plan,
    validate_run,
)
from harness_schema import ACTION_TARGET_CONTRACT  # noqa: E402
from manifest_fixtures import manifest_markdown  # noqa: E402
from test_harness_manifest import cloudflare_release, valid_plan, valid_run  # noqa: E402

import upgrade_harness_schema as upgrade  # noqa: E402


UPGRADE_SCRIPT = SCRIPTS_DIR / "upgrade_harness_schema.py"


def upgradeable_plan() -> dict[str, object]:
    plan = valid_plan()
    counter = 1
    for current_mission in plan["missions"]:
        for current_task in current_mission["tasks"]:
            current_task["acceptance_matrix"] = [
                f"TEST-UPGRADE-{counter:03d}: {current_task['id']} passes"
            ]
            counter += 1
    return plan


def downgrade_run_to_v2(run: dict[str, object]) -> dict[str, object]:
    """Strip every post-v2 addition to produce a valid schema-v2 RUN."""

    run = copy.deepcopy(run)
    run["schema_version"] = 2
    run["runtime_capabilities"].pop("runtime_adapter", None)
    run.pop("landing", None)
    run.pop("post_merge_cleanup", None)
    run["observed"]["git"].pop("parent_worktree_path", None)
    run["authorizations"] = {
        key: run["authorizations"][key] for key in AUTHORIZATION_KEYS_V2
    }
    return run


def safe_v4_plan_and_v9_run(repo_root: Path) -> tuple[dict[str, object], dict[str, object]]:
    """Build a valid inactive v4/v9 pair with an exact retained PR branch."""

    plan = upgradeable_plan()
    upgrade._PLAN_STEPS[2](plan, repo_root)
    upgrade._PLAN_STEPS[3](plan, repo_root)
    run = valid_run(plan)
    upgrade._RUN_STEPS[6](run, plan)
    upgrade._RUN_STEPS[7](run, plan)
    upgrade._RUN_STEPS[8](run, plan)
    return plan, run


def current_plan_and_run(
    repo_root: Path,
    *,
    strict_action_targets: bool = True,
) -> tuple[dict[str, object], dict[str, object]]:
    """Build a valid direct PLAN-v5/RUN-v10 fixture."""

    plan, run = safe_v4_plan_and_v9_run(repo_root)
    upgrade._PLAN_STEPS[4](plan, repo_root)
    if strict_action_targets:
        plan["action_target_contract"] = ACTION_TARGET_CONTRACT
    run["plan"] = {
        "id": plan["plan_id"],
        "revision": plan["revision"],
        "digest_sha256": plan_digest(plan),
    }
    upgrade._RUN_STEPS[9](run, plan)
    if strict_action_targets:
        run["action_target_contract"] = ACTION_TARGET_CONTRACT
    return plan, run


def current_release_plan_and_run(
    repo_root: Path, trigger: str
) -> tuple[dict[str, object], dict[str, object]]:
    """Build a valid PLAN-v5/RUN-v10 release fixture for one PASS target."""

    plan = upgradeable_plan()
    plan["release"] = cloudflare_release()
    upgrade._PLAN_STEPS[2](plan, repo_root)
    upgrade._PLAN_STEPS[3](plan, repo_root)
    run = valid_run(plan)
    upgrade._RUN_STEPS[6](run, plan)
    upgrade._RUN_STEPS[7](run, plan)
    upgrade._RUN_STEPS[8](run, plan)
    upgrade._PLAN_STEPS[4](plan, repo_root)
    plan["action_target_contract"] = ACTION_TARGET_CONTRACT

    target = plan["release"]["targets"][0]
    target.update(
        {
            "source": "integration_head",
            "artifact_kind": "static_bundle",
            "requires_signing": False,
            "channel": "development",
            "trigger": trigger,
            "migration_classification": "not_applicable",
        }
    )
    if trigger == "merge":
        target["commands"]["publish"] = None

    run["plan"] = {
        "id": plan["plan_id"],
        "revision": plan["revision"],
        "digest_sha256": plan_digest(plan),
    }
    upgrade._RUN_STEPS[9](run, plan)
    run["action_target_contract"] = ACTION_TARGET_CONTRACT
    run["integration"]["retention"] = "persistent"
    evidence_sha256 = "e" * 64
    retained = {
        "subject": "development release",
        "retained_reference": "artifact://development",
        "evidence_sha256": evidence_sha256,
    }
    run["targets"]["development"].update(
        {
            "status": "PASS",
            "source_sha": run["integration"]["integration_head_sha"],
            "authorized_head_sha": run["integration"]["integration_head_sha"],
            "artifact": {
                **retained,
                "build_id": "build-development-1",
                "version": "1",
                "signing_status": "not_required",
            },
            "channel": {**retained, "name": "development"},
            "promotion": {**retained, "status": "PASS"},
            "availability": {**retained, "status": "PASS"},
            "migration_status": "not_required",
            "verification_status": "PASS",
        }
    )
    return plan, run


def retained_batch_execution(
    plan: dict[str, object], run: dict[str, object]
) -> dict[str, object]:
    declaration = plan["batch_verifiers"][0]
    changed_files: list[str] = []
    context = {
        "run_id": run["run_id"],
        "plan_revision": run["plan"]["revision"],
        "plan_digest_sha256": run["plan"]["digest_sha256"],
        "graph_revision": run["graph_state"]["graph_revision"],
        "batch_base_sha": run["integration"]["batch_base_sha"],
        "head_sha": run["integration"]["integration_head_sha"],
        "changed_files": changed_files,
        "trust_domain": "parent_local",
        "checkout_role": "integration",
        "checkout_dirty": False,
        "cache_safe": False,
        "layer": "batch",
        "mission_id": None,
        "task_id": None,
        "attempt_id": None,
        "lease_id": None,
    }
    normalized_verifier = {
        "id": declaration["id"],
        "cwd": declaration["cwd"],
        "argv": declaration["argv"],
        "pass_signal": declaration["pass_signal"],
        "cache": {"mode": "disabled", "environment_keys": []},
    }
    key_document = {
        "protocol": "harness-verifier-execution-v1",
        "verifier_id": declaration["id"],
        "layer": context["layer"],
        "mission_id": context["mission_id"],
        "task_id": context["task_id"],
        "attempt_id": context["attempt_id"],
        "lease_id": context["lease_id"],
        "run_id": context["run_id"],
        "plan_revision": context["plan_revision"],
        "plan_digest_sha256": context["plan_digest_sha256"],
        "graph_revision": context["graph_revision"],
        "batch_base_sha": context["batch_base_sha"],
        "head_sha": context["head_sha"],
        "changed_files_digest": hashlib.sha256(b"[]").hexdigest(),
        "trust_domain": context["trust_domain"],
        "checkout_role": context["checkout_role"],
        "checkout_dirty": context["checkout_dirty"],
        "cache_safe": context["cache_safe"],
        "cwd": normalized_verifier["cwd"],
        "argv": normalized_verifier["argv"],
        "pass_signal": normalized_verifier["pass_signal"],
        "cache_mode": normalized_verifier["cache"]["mode"],
        "environment_keys": normalized_verifier["cache"]["environment_keys"],
        "platform": {"system": "test", "machine": "test"},
        "executable_identity": {
            "path": "C:/python",
            "size": 1,
            "mtime_ns": 1,
            "device": 1,
            "inode": 1,
        },
        "environment_digests": {},
    }
    execution_key = hashlib.sha256(
        json.dumps(
            key_document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    empty_digest = hashlib.sha256(b"").hexdigest()
    return {
        "execution_id": "VX-001",
        "verifier_id": declaration["id"],
        "layer": "batch",
        "mission_id": None,
        "task_id": None,
        "attempt_id": None,
        "lease_id": None,
        "protocol": "harness-verifier-execution-v1",
        "execution_key": execution_key,
        "evidence_key": execution_key,
        "key_document": key_document,
        "verifier": normalized_verifier,
        "context": context,
        "status": "PASS",
        "exit_code": 0,
        "cache_status": "bypassed",
        "cache_reason": "cache_disabled",
        "duration_ms": 1,
        "metrics": {"executed": 1, "reused": 0},
        "stdout_sha256": empty_digest,
        "stderr_sha256": empty_digest,
        "evidence_paths": [],
    }


class UpgradeHelpers:
    def _seed_repo(self) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "docs" / "product").mkdir(parents=True)
        # upgradeable_plan() sources point at docs/product/prd.md and docs/product/architecture.md;
        # real files let the v4 upgrade freeze a real content_sha256.
        (root / "docs" / "product" / "prd.md").write_text("product requirements", encoding="utf-8")
        (root / "docs" / "product" / "architecture.md").write_text("architecture", encoding="utf-8")
        return root

    def _write_plan(self, root: Path, plan: dict[str, object]) -> Path:
        path = root / "PLAN.md"
        path.write_text(
            manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
            encoding="utf-8",
        )
        return path

    def _write_run(self, root: Path, run: dict[str, object]) -> Path:
        path = root / "RUN.md"
        path.write_text(
            manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )
        return path

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(UPGRADE_SCRIPT), *args]
        return subprocess.run(command, check=False, capture_output=True, text=True)


class PlanUpgradeTests(UpgradeHelpers, unittest.TestCase):
    def test_plan_v2_to_v4_result_passes_validate_plan(self) -> None:
        root = self._seed_repo()
        plan_path = self._write_plan(root, upgradeable_plan())

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(0, result.returncode, result.stderr)
        upgraded = load_plan(plan_path)
        self.assertEqual(5, upgraded["schema_version"])
        self.assertEqual([], validate_plan(upgraded))

    def test_plan_only_upgrade_refuses_an_existing_paired_old_run(self) -> None:
        root = self._seed_repo()
        plan = upgradeable_plan()
        run = downgrade_run_to_v2(valid_run(plan))
        run["plan"]["digest_sha256"] = plan_digest(plan)
        plan_path = self._write_plan(root, plan)
        run_path = self._write_run(root, run)
        plan_before = plan_path.read_bytes()
        run_before = run_path.read_bytes()

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(1, result.returncode)
        self.assertIn("refusing PLAN-only upgrade", result.stderr)
        self.assertIn(f"Pass --run {run_path}", result.stderr)
        self.assertEqual(plan_before, plan_path.read_bytes())
        self.assertEqual(run_before, run_path.read_bytes())

    def test_plan_v4_graph_projects_dependencies_without_fabrication(self) -> None:
        root = self._seed_repo()
        plan_path = self._write_plan(root, upgradeable_plan())

        self._run_cli("--plan", str(plan_path), "--repo-root", str(root))
        upgraded = load_plan(plan_path)

        # M2 depends_on M1 in the source plan -> exactly one dependency edge.
        self.assertEqual([], upgraded["required_reviews"])
        node_refs = {node["ref"] for node in upgraded["graph"]["nodes"]}
        self.assertEqual({"M1", "M2"}, node_refs)
        dependency_edges = [
            edge for edge in upgraded["graph"]["edges"] if edge["kind"] == "dependency"
        ]
        self.assertEqual(1, len(dependency_edges))
        # depends_on must be gone from every mission at v4.
        self.assertTrue(all("depends_on" not in m for m in upgraded["missions"]))
        # Frozen provenance is a real hash, source_revision stays null (not invented).
        for source in upgraded["sources"]:
            self.assertRegex(source["content_sha256"], r"^[0-9a-f]{64}$")
            self.assertIsNone(source["source_revision"])

    def test_unreadable_source_aborts_without_writing(self) -> None:
        # No source files on disk -> v4 freeze cannot compute a real hash.
        root = Path(tempfile.mkdtemp())
        plan_path = self._write_plan(root, upgradeable_plan())
        before = plan_path.read_bytes()

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(1, result.returncode)
        self.assertIn("cannot freeze source", result.stderr)
        self.assertEqual(before, plan_path.read_bytes())

    def test_invalid_plan_is_rejected_and_not_written(self) -> None:
        root = self._seed_repo()
        broken = upgradeable_plan()
        broken["missions"] = []  # structurally invalid
        plan_path = self._write_plan(root, broken)
        before = plan_path.read_bytes()

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(1, result.returncode)
        self.assertIn("refusing to upgrade", result.stderr)
        self.assertEqual(before, plan_path.read_bytes())

    def test_ambiguous_acceptance_aborts_plan_and_run_atomically(self) -> None:
        root = self._seed_repo()
        plan = upgradeable_plan()
        plan["missions"][0]["tasks"][0]["acceptance_matrix"] = ["passes somehow"]
        run = downgrade_run_to_v2(valid_run(plan))
        run["plan"]["digest_sha256"] = plan_digest(plan)
        plan_path = self._write_plan(root, plan)
        run_path = self._write_run(root, run)
        plan_before = plan_path.read_bytes()
        run_before = run_path.read_bytes()

        result = self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("must already name an exact TEST-* ID", result.stderr)
        self.assertEqual(plan_before, plan_path.read_bytes())
        self.assertEqual(run_before, run_path.read_bytes())

    def test_v5_upgrade_preserves_named_test_ids_and_adds_unknowns_as_null(self) -> None:
        root = self._seed_repo()
        plan_path = self._write_plan(root, upgradeable_plan())

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(0, result.returncode, result.stderr)
        upgraded = load_plan(plan_path)
        first_task = upgraded["missions"][0]["tasks"][0]
        self.assertEqual("TEST-UPGRADE-001", first_task["acceptance_matrix"][0]["test_id"])
        self.assertEqual(first_task["trace_ids"], first_task["acceptance_matrix"][0]["trace_ids"])
        self.assertTrue(all(source["staged_revision"] is None for source in upgraded["sources"]))

    def test_v4_upgrade_refuses_product_staging_source_atomically(self) -> None:
        root = self._seed_repo()
        plan, _ = safe_v4_plan_and_v9_run(root)
        plan["sources"][0]["location"] = "docs/product/.prd-staging/candidate/PRD.md"
        plan_path = self._write_plan(root, plan)
        before = plan_path.read_bytes()

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(1, result.returncode)
        self.assertIn("publish staged product input first", result.stderr)
        self.assertEqual(before, plan_path.read_bytes())


class RunUpgradeTests(UpgradeHelpers, unittest.TestCase):
    def test_safe_run_v9_with_plan_upgrade_passes_validate_run(self) -> None:
        root = self._seed_repo()
        plan, run = safe_v4_plan_and_v9_run(root)
        plan_path = self._write_plan(root, plan)
        run_path = self._write_run(root, run)

        result = self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )

        self.assertEqual(0, result.returncode, result.stderr)
        upgraded_plan = load_plan(plan_path)
        upgraded_run = load_run(run_path)
        self.assertEqual(5, upgraded_plan["schema_version"])
        self.assertEqual(10, upgraded_run["schema_version"])
        self.assertEqual([], validate_run(upgraded_plan, upgraded_run))
        self.assertEqual(
            plan_digest(upgraded_plan), upgraded_run["plan"]["digest_sha256"]
        )

    def test_paired_rewrite_staging_failures_preserve_exact_original_bytes(self) -> None:
        for failing_call in (1, 3):
            with self.subTest(failing_call=failing_call):
                root = self._seed_repo()
                plan, run = safe_v4_plan_and_v9_run(root)
                plan_path = self._write_plan(root, plan)
                run_path = self._write_run(root, run)
                plan_before = plan_path.read_bytes()
                run_before = run_path.read_bytes()
                real_stage = upgrade._stage_sibling
                call_count = 0

                def fail_stage(
                    path: Path, content: bytes, label: str
                ) -> Path:
                    nonlocal call_count
                    call_count += 1
                    if call_count == failing_call:
                        raise OSError("injected staging failure")
                    return real_stage(path, content, label)

                rewrites = [
                    (plan_path, "## Harness Plan Manifest", "harness_plan", plan),
                    (run_path, "## Harness Run State", "harness_run", run),
                ]
                with mock.patch.object(
                    upgrade, "_stage_sibling", side_effect=fail_stage
                ):
                    with self.assertRaisesRegex(
                        upgrade.UpgradeError, "failed to write upgraded manifests"
                    ):
                        upgrade._rewrite_manifests_atomically(rewrites)

                self.assertEqual(plan_before, plan_path.read_bytes())
                self.assertEqual(run_before, run_path.read_bytes())

    def test_paired_rewrite_replace_failures_preserve_exact_original_bytes(self) -> None:
        for failing_call in (1, 2):
            with self.subTest(failing_call=failing_call):
                root = self._seed_repo()
                plan, run = safe_v4_plan_and_v9_run(root)
                plan_path = self._write_plan(root, plan)
                run_path = self._write_run(root, run)
                plan_before = plan_path.read_bytes()
                run_before = run_path.read_bytes()
                real_replace = upgrade.os.replace
                call_count = 0

                def fail_replace(source: Path, target: Path) -> None:
                    nonlocal call_count
                    call_count += 1
                    if call_count == failing_call:
                        raise OSError("injected replacement failure")
                    real_replace(source, target)

                rewrites = [
                    (plan_path, "## Harness Plan Manifest", "harness_plan", plan),
                    (run_path, "## Harness Run State", "harness_run", run),
                ]
                with mock.patch.object(
                    upgrade.os, "replace", side_effect=fail_replace
                ):
                    with self.assertRaisesRegex(
                        upgrade.UpgradeError, "failed to write upgraded manifests"
                    ):
                        upgrade._rewrite_manifests_atomically(rewrites)

                self.assertEqual(plan_before, plan_path.read_bytes())
                self.assertEqual(run_before, run_path.read_bytes())

    def test_run_v2_upgrade_refuses_missing_retained_branch_atomically(self) -> None:
        root = self._seed_repo()
        plan = upgradeable_plan()
        run = downgrade_run_to_v2(valid_run(plan))
        run["plan"]["digest_sha256"] = plan_digest(plan)
        plan_path = self._write_plan(root, plan)
        run_path = self._write_run(root, run)
        before_plan = plan_path.read_bytes()
        before_run = run_path.read_bytes()

        result = self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("without an exact distinct retained branch", result.stderr)
        self.assertEqual(before_plan, plan_path.read_bytes())
        self.assertEqual(before_run, run_path.read_bytes())

    def test_run_upgrade_lands_neutral_defaults(self) -> None:
        root = self._seed_repo()
        plan, run = safe_v4_plan_and_v9_run(root)
        plan_path = self._write_plan(root, plan)
        run_path = self._write_run(root, run)

        result = self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )
        self.assertEqual(0, result.returncode, result.stderr)
        upgraded_run = load_run(run_path)

        self.assertEqual("not_created", upgraded_run["landing"]["pr_state"])
        self.assertFalse(upgraded_run["landing"]["auto_merge_requested"])
        for action in (
            "invoke_external_runtime",
            "trigger_remote_ci",
            "provision_cloud_resources",
        ):
            self.assertEqual(
                {"authorized": False, "source": None},
                upgraded_run["authorizations"][action],
            )
        for state in upgraded_run["graph_state"]["node_states"].values():
            self.assertEqual("dormant", state["phase"])
            self.assertEqual(0, state["attempts"])
            self.assertIsNone(state["last_outcome"])
        for gate in (
            upgraded_run["batch_gate_results"] + upgraded_run["final_gate_results"]
        ):
            self.assertEqual("planned", gate["status"])
            self.assertIsNone(gate["head_sha"])
            self.assertEqual([], gate["evidence"])
        self.assertEqual([], upgraded_run["ui_evidence"])
        self.assertEqual([], upgraded_run["review_workers"])
        self.assertEqual([], upgraded_run["workflow_runs"])
        self.assertEqual([], upgraded_run["verifier_executions"])

    def test_run_v9_upgrade_refuses_active_authorization(self) -> None:
        root = self._seed_repo()
        plan, run = safe_v4_plan_and_v9_run(root)
        run["authorizations"]["push"] = {
            "authorized": True,
            "source": "user: push this head",
            "scope": {
                "run_id": run["run_id"],
                "mission_ids": ["*"],
                "targets": ["remote:origin"],
            },
            "expires_when": "run_complete",
        }
        plan_path = self._write_plan(root, plan)
        run_path = self._write_run(root, run)
        before = run_path.read_bytes()

        result = self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("without explicit plan-bound reaffirmation", result.stderr)
        self.assertEqual(before, run_path.read_bytes())

    def test_run_v9_upgrade_refuses_completed_history(self) -> None:
        root = self._seed_repo()
        plan, run = safe_v4_plan_and_v9_run(root)
        run["status"] = "complete"
        before = copy.deepcopy(run)

        with self.assertRaisesRegex(upgrade.UpgradeError, "remains readable historical state"):
            upgrade._upgrade_run_v9_to_v10(run, plan)

        self.assertEqual(before, run)


class RunV10ContractTests(UpgradeHelpers, unittest.TestCase):
    def _authorize(
        self,
        run: dict[str, object],
        action: str,
        target: str,
    ) -> None:
        run["authorizations"][action] = {
            "authorized": True,
            "source": f"user: authorize {action}",
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": run["plan"]["revision"],
                "plan_digest_sha256": run["plan"]["digest_sha256"],
                "mission_ids": ["M1"],
                "targets": [target],
            },
            "expires_when": "run_complete",
        }

    def _authorize_release(
        self,
        run: dict[str, object],
        action: str,
        target_id: str = "development",
    ) -> None:
        target = f"release:{target_id}"
        entry: dict[str, object] = {
            "authorized": True,
            "source": f"user: authorize {action} for {target_id}",
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": run["plan"]["revision"],
                "plan_digest_sha256": run["plan"]["digest_sha256"],
                "mission_ids": list(run["mission_states"]),
                "targets": [target],
            },
            "expires_when": "run_complete",
            "authorized_head_sha": run["targets"][target_id]["authorized_head_sha"],
        }
        if action == "merge_pr" and str(run["landing"]["base_branch"]).removeprefix(
            "refs/heads/"
        ) == "main":
            entry["target_sources"] = {
                target: "user: separately authorize this main-bound merge consequence"
            }
        run["authorizations"][action] = entry

    def test_plan_v5_verifier_ids_are_globally_unique_across_layers(self) -> None:
        root = self._seed_repo()
        plan, _ = current_plan_and_run(root)
        plan["missions"][0]["tasks"][0]["verifiers"][0]["id"] = plan[
            "batch_verifiers"
        ][0]["id"]

        errors = validate_plan(plan)

        self.assertTrue(any("must be globally unique" in error for error in errors))

    def _grant(
        self,
        run: dict[str, object],
        action: str,
        targets: list[str],
        source: str = "user said: build it",
        target_sources: dict[str, str] | None = None,
        head: str | None = None,
    ) -> None:
        entry: dict[str, object] = {
            "authorized": True,
            "source": source,
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": run["plan"]["revision"],
                "plan_digest_sha256": run["plan"]["digest_sha256"],
                "mission_ids": list(run["mission_states"]),
                "targets": targets,
            },
            "expires_when": "run_complete",
            "authorized_head_sha": head or "a" * 40,
        }
        if target_sources is not None:
            entry["target_sources"] = target_sources
        run["authorizations"][action] = entry

    def _target_source_errors(self, plan: dict, run: dict) -> list[str]:
        return [error for error in validate_run(plan, run) if "target_sources" in error]

    def test_failed_rollback_keeps_the_only_remaining_original(self) -> None:
        """A double fault must not delete the backup the error points at.

        The forward replace already overwrote the canonical file; if the
        rollback replace also fails, that backup is the only copy of the
        original content left on disk.
        """
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        first = self._write_plan(root, plan)
        second = self._write_run(root, run)
        first_original = first.read_text(encoding="utf-8")

        rewrites = [
            (first, "## Harness Plan Manifest", "harness_plan", plan),
            (second, "## Harness Run State", "harness_run", run),
        ]

        real_replace = os.replace
        calls: list[int] = []

        def failing_replace(src, dst):
            calls.append(1)
            # Let the first forward replace land, fail the second forward
            # replace, then fail the rollback of the first.
            if len(calls) in (2, 3):
                raise OSError("simulated filesystem failure")
            return real_replace(src, dst)

        with mock.patch.object(upgrade.os, "replace", failing_replace):
            with self.assertRaises(upgrade.UpgradeError) as caught:
                upgrade._rewrite_manifests_atomically(rewrites)

        message = str(caught.exception)
        self.assertIn("rollback failed for", message)
        self.assertIn("original retained at", message)

        retained = [path for path in root.iterdir() if ".backup." in path.name]
        self.assertEqual(1, len(retained), f"expected one retained backup, found {retained}")
        self.assertEqual(first_original, retained[0].read_text(encoding="utf-8"))
        self.assertEqual([], [path for path in root.iterdir() if ".new." in path.name])

    def test_execution_intent_cannot_reach_the_protected_branch_or_production(self) -> None:
        """One 'build it' must not silently cover an out-of-scope target.

        The ledger keeps one `source` per action for a whole target list, so
        without a per-target record a grouped instruction reads as authorizing
        every target on the entry - including a push to the protected branch, a
        production deploy, and the promotion merge.
        """
        root = self._seed_repo()
        plan, base = current_release_plan_and_run(root, "manual")
        branch = base["integration"]["branch"]

        in_scope = copy.deepcopy(base)
        self._grant(in_scope, "push", [f"branch:{branch}"])
        self.assertEqual([], self._target_source_errors(plan, in_scope))

        out_of_scope = copy.deepcopy(base)
        self._grant(out_of_scope, "push", ["branch:production"])
        self.assertTrue(
            any(
                "outside what one execution-intent instruction covers for push" in error
                for error in self._target_source_errors(plan, out_of_scope)
            )
        )

        mixed = copy.deepcopy(base)
        self._grant(mixed, "push", [f"branch:{branch}", "branch:production"])
        self.assertTrue(self._target_source_errors(plan, mixed))

        deploy_both = copy.deepcopy(base)
        self._grant(deploy_both, "deploy", ["release:development", "release:production"])
        self.assertTrue(
            any(
                "release:production" in error
                for error in self._target_source_errors(plan, deploy_both)
            )
        )

        promotion = copy.deepcopy(base)
        self._grant(
            promotion,
            "merge_pr",
            ["future-pr:acme/app:base=production:head=development"],
        )
        self.assertTrue(self._target_source_errors(plan, promotion))

        loop_merge = copy.deepcopy(base)
        loop_merge["landing"].update(
            {
                "pr_url": "https://github.com/acme/app/pull/1",
                "base_branch": branch,
                "head_branch": "feature",
            }
        )
        self._grant(loop_merge, "merge_pr", [f"future-pr:acme/app:base={branch}:head=feature"])
        self.assertEqual([], self._target_source_errors(plan, loop_merge))

    def test_target_sources_records_the_separate_instruction(self) -> None:
        root = self._seed_repo()
        plan, base = current_release_plan_and_run(root, "manual")
        branch = base["integration"]["branch"]

        recorded = copy.deepcopy(base)
        self._grant(
            recorded,
            "push",
            ["branch:production"],
            target_sources={"branch:production": "user: yes, push production too"},
        )
        self.assertEqual([], self._target_source_errors(plan, recorded))

        laundered = copy.deepcopy(base)
        self._grant(
            laundered,
            "push",
            ["branch:production"],
            target_sources={"branch:production": "user said: build it"},
        )
        self.assertTrue(
            any(
                "not repeat the entry source" in error
                for error in self._target_source_errors(plan, laundered)
            )
        )

        orphan = copy.deepcopy(base)
        self._grant(
            orphan,
            "push",
            [f"branch:{branch}"],
            target_sources={"branch:production": "user: separate ask"},
        )
        self.assertTrue(
            any(
                "is not listed in scope.targets" in error
                for error in self._target_source_errors(plan, orphan)
            )
        )

        empty = copy.deepcopy(base)
        self._grant(
            empty,
            "push",
            ["branch:production"],
            target_sources={"branch:production": "   "},
        )
        self.assertTrue(self._target_source_errors(plan, empty))

    def test_target_sources_is_rejected_on_unscoped_actions(self) -> None:
        root = self._seed_repo()
        plan, run = current_release_plan_and_run(root, "manual")
        self._grant(
            run,
            "create_pr",
            ["pr:https://github.com/acme/app/pull/1"],
            target_sources={"pr:https://github.com/acme/app/pull/1": "user: open it"},
        )

        errors = validate_run(plan, run)

        self.assertTrue(any("unknown keys" in error for error in errors))

    def test_merge_triggered_release_requires_merge_and_deploy_authorization(self) -> None:
        root = self._seed_repo()
        plan, merge_only = current_release_plan_and_run(root, "merge")
        self._authorize_release(merge_only, "merge_pr")

        merge_only_errors = validate_run(plan, merge_only)
        self.assertFalse(any("exact merge_pr authorization" in error for error in merge_only_errors))
        self.assertTrue(any("exact deploy authorization" in error for error in merge_only_errors))

        deploy_only = copy.deepcopy(merge_only)
        deploy_only["authorizations"]["merge_pr"] = {
            "authorized": False,
            "source": None,
        }
        self._authorize_release(deploy_only, "deploy")

        deploy_only_errors = validate_run(plan, deploy_only)
        self.assertTrue(any("exact merge_pr authorization" in error for error in deploy_only_errors))
        self.assertFalse(any("exact deploy authorization" in error for error in deploy_only_errors))

        both = copy.deepcopy(deploy_only)
        self._authorize_release(both, "merge_pr")
        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, both))

        stale_merge = copy.deepcopy(both)
        stale_merge["authorizations"]["merge_pr"]["authorized_head_sha"] = "0" * 40
        self.assertTrue(
            any(
                "exact merge_pr authorization" in error
                for error in validate_run(plan, stale_merge)
            )
        )

        stale_deploy = copy.deepcopy(both)
        stale_deploy["authorizations"]["deploy"]["authorized_head_sha"] = "0" * 40
        self.assertTrue(
            any(
                "exact deploy authorization" in error
                for error in validate_run(plan, stale_deploy)
            )
        )

        partial_deploy = copy.deepcopy(both)
        partial_deploy["authorizations"]["deploy"]["scope"]["mission_ids"] = ["M1"]
        self.assertTrue(
            any(
                "exact deploy authorization" in error
                for error in validate_run(plan, partial_deploy)
            )
        )

    def test_manual_release_requires_only_deploy_authorization(self) -> None:
        root = self._seed_repo()
        plan, deploy_only = current_release_plan_and_run(root, "manual")
        self._authorize_release(deploy_only, "deploy")

        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, deploy_only))

        merge_only = copy.deepcopy(deploy_only)
        merge_only["authorizations"]["deploy"] = {
            "authorized": False,
            "source": None,
        }
        self._authorize_release(merge_only, "merge_pr")
        errors = validate_run(plan, merge_only)
        self.assertTrue(any("exact deploy authorization" in error for error in errors))
        self.assertFalse(any("exact merge_pr authorization" in error for error in errors))

    def test_manual_release_authorization_must_match_source_sha(self) -> None:
        root = self._seed_repo()
        plan, run = current_release_plan_and_run(root, "manual")
        run["targets"]["development"]["authorized_head_sha"] = "b" * 40
        self._authorize_release(run, "deploy")

        errors = validate_run(plan, run)

        self.assertTrue(
            any("must bind the exact manual source head" in error for error in errors)
        )

    def test_merge_release_can_authorize_pr_head_and_publish_merged_sha(self) -> None:
        root = self._seed_repo()
        plan, run = current_release_plan_and_run(root, "merge")
        pr_head = run["integration"]["integration_head_sha"]
        merged_sha = "c" * 40
        plan["release"]["targets"][0]["source"] = "merged_main"
        run["plan"]["digest_sha256"] = plan_digest(plan)
        run["landing"].update(
            {
                "pushed_head_sha": pr_head,
                "pr_number": 21,
                "pr_url": "https://github.com/example/repo/pull/21",
                "pr_state": "merged",
                "pr_head_sha": pr_head,
                "checks_status": "PASS",
                "checks_head_sha": pr_head,
                "review_status": "PASS",
                "review_head_sha": pr_head,
                "blocking_findings": 0,
                "unresolved_threads": 0,
                "merge_status": "merged",
                "merged_sha": merged_sha,
            }
        )
        run["targets"]["development"].update(
            {
                "source_sha": merged_sha,
                "authorized_head_sha": pr_head,
            }
        )
        self._authorize_release(run, "merge_pr")
        self._authorize_release(run, "deploy")
        exact_pr = f"pr:{run['landing']['pr_url']}"
        future_pr = (
            "future-pr:example/repo:"
            f"base={run['landing']['base_branch']}:"
            f"head={run['landing']['head_branch']}"
        )
        merge_entry = run["authorizations"]["merge_pr"]
        merge_entry["scope"]["targets"].extend([future_pr, exact_pr])
        merge_entry["target_sources"].update(
            {
                future_pr: "user: start this exact protected-base promotion",
                exact_pr: "user: merge this exact protected-base PR",
            }
        )

        self.assertEqual([], validate_run(plan, run))

    def test_unresolved_migration_classification_blocks_readiness_and_closeout(
        self,
    ) -> None:
        root = self._seed_repo()
        plan, run = current_release_plan_and_run(root, "manual")
        plan["release"]["targets"][0]["migration_classification"] = None
        run["plan"]["digest_sha256"] = plan_digest(plan)
        run["plan_readiness"] = "ready"

        errors = validate_run(plan, run)

        self.assertTrue(
            any("ready or executable RUN has unresolved release semantics" in error for error in errors)
        )
        self.assertTrue(
            any(
                "target execution cannot start with unresolved migration_classification"
                in error
                for error in errors
            )
        )

    def test_v10_continuity_binds_exact_branch_and_lifecycle_head(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        integration_head = run["integration"]["integration_head_sha"]
        run["landing"]["mode"] = "local_only"
        run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/codex/test",
            "head_sha": None,
            "reason": None,
        }
        self.assertEqual([], validate_run(plan, run))

        wrong_branch = copy.deepcopy(run)
        wrong_branch["landing"]["continuity"]["branch_ref"] = "refs/heads/other"
        self.assertTrue(
            any(
                "must equal the exact retained integration branch ref" in error
                for error in validate_run(plan, wrong_branch)
            )
        )

        premature_head = copy.deepcopy(run)
        premature_head["landing"]["continuity"]["head_sha"] = integration_head
        self.assertTrue(
            any(
                "must be null while continuity is planned" in error
                for error in validate_run(plan, premature_head)
            )
        )

        preserved = copy.deepcopy(run)
        preserved["landing"]["continuity"].update(
            {"status": "preserved", "head_sha": integration_head}
        )
        self.assertEqual([], validate_run(plan, preserved))
        preserved["landing"]["continuity"]["head_sha"] = "b" * 40
        self.assertTrue(
            any(
                "must match the current integration head when recorded" in error
                for error in validate_run(plan, preserved)
            )
        )

    def test_v10_pr_and_final_pass_evidence_must_match_current_heads(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        current_head = run["integration"]["integration_head_sha"]
        stale_head = "b" * 40
        run["landing"].update(
            {
                "pushed_head_sha": current_head,
                "pr_number": 21,
                "pr_url": "https://github.com/example/repo/pull/21",
                "pr_state": "open",
                "pr_head_sha": current_head,
                "checks_status": "PASS",
                "checks_head_sha": stale_head,
                "review_status": "PASS",
                "review_head_sha": stale_head,
                "blocking_findings": 0,
                "unresolved_threads": 0,
            }
        )
        run["final_gate_results"][0].update(
            {
                "status": "PASS",
                "head_sha": stale_head,
                "evidence": ["stale-final-evidence"],
            }
        )

        errors = validate_run(plan, run)

        self.assertTrue(
            any("PASS checks must bind to a created PR's current head" in error for error in errors)
        )
        self.assertTrue(
            any("PASS review must bind to a created PR's current head" in error for error in errors)
        )
        self.assertTrue(
            any("PASS final gate must match integration_head_sha" in error for error in errors)
        )

    def test_v10_non_auto_merge_authorization_must_match_current_pr_head(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        pr_head = run["integration"]["integration_head_sha"]
        run["status"] = "complete"
        run["landing"].update(
            {
                "pushed_head_sha": pr_head,
                "pr_number": 21,
                "pr_url": "https://github.com/example/repo/pull/21",
                "pr_state": "merged",
                "pr_head_sha": pr_head,
                "checks_status": "PASS",
                "checks_head_sha": pr_head,
                "review_status": "PASS",
                "review_head_sha": pr_head,
                "blocking_findings": 0,
                "unresolved_threads": 0,
                "merge_status": "merged",
                "merged_sha": "c" * 40,
                "auto_merge_requested": False,
                "auto_merge_head_sha": None,
            }
        )
        run["authorizations"]["merge_pr"] = {
            "authorized": True,
            "source": "user: merge pull request",
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": run["plan"]["revision"],
                "plan_digest_sha256": run["plan"]["digest_sha256"],
                "mission_ids": list(run["mission_states"]),
                "targets": [run["landing"]["pr_url"]],
            },
            "expires_when": "run_complete",
            "authorized_head_sha": "b" * 40,
        }

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                "merged pull-request landing requires merge authorization for the "
                "exact PR, current PR head, and every mission"
                in error
                for error in errors
            )
        )

    def test_direct_v5_v10_fixture_has_exact_19_action_ledger(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)

        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, run))
        self.assertEqual(19, len(run["authorizations"]))
        self.assertIn("trigger_remote_ci", run["authorizations"])
        self.assertIn("provision_cloud_resources", run["authorizations"])
        self.assertEqual([], run["verifier_executions"])

    def test_v5_rejects_product_staging_location_as_published_source(self) -> None:
        root = self._seed_repo()
        plan, _ = current_plan_and_run(root)
        plan["sources"][0]["location"] = "docs/product/.prd-staging/candidate/PRD.md"

        errors = validate_plan(plan)

        self.assertTrue(
            any("published PLAN sources cannot use product staging paths" in error for error in errors)
        )

    def test_v10_ready_run_rejects_revision_staged_source(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        source = plan["sources"][0]
        source["status"] = "revision staged"
        source["staged_revision"] = {
            "content_sha256": "f" * 64,
            "source_revision": None,
            "notes": "Candidate product revision awaiting publication.",
        }
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["active_wave"]["plan_digest_sha256"] = digest
        run["plan_readiness"] = "ready"

        self.assertEqual([], validate_plan(plan))
        errors = validate_run(plan, run)

        self.assertTrue(
            any("ready or executable RUN requires a frozen or delta_accepted source" in error for error in errors)
        )

    def test_v10_rejects_missing_and_unknown_authorization_actions(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        del run["authorizations"]["trigger_remote_ci"]
        run["authorizations"]["unknown_action"] = {
            "authorized": False,
            "source": None,
        }

        errors = validate_run(plan, run)

        self.assertTrue(
            any("missing keys: trigger_remote_ci" in error for error in errors)
        )
        self.assertTrue(any("unknown keys: unknown_action" in error for error in errors))

    def test_v10_authorization_is_bound_to_plan_action_and_target(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        self._authorize(run, "trigger_remote_ci", "workflow:github-actions:ci")

        self.assertEqual([], validate_run(plan, run))
        self.assertTrue(
            authorization_covers(run, "trigger_remote_ci", "M1", "workflow:github-actions:ci")
        )
        self.assertFalse(
            authorization_covers(run, "provision_cloud_resources", "M1", "workflow:github-actions:ci")
        )
        self.assertFalse(
            authorization_covers(run, "trigger_remote_ci", "M1", "workflow:github-actions:release")
        )

        run["authorizations"]["trigger_remote_ci"]["scope"]["plan_revision"] += 1
        self.assertFalse(
            authorization_covers(run, "trigger_remote_ci", "M1", "workflow:github-actions:ci")
        )
        self.assertTrue(
            any("scope.plan_revision: must match run.plan.revision" in error for error in validate_run(plan, run))
        )

    def test_v10_integration_pull_request_can_target_the_integration_branch(
        self,
    ) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        integration_branch = run["integration"]["branch"]
        integration_branch_ref = (
            integration_branch
            if integration_branch.startswith("refs/heads/")
            else f"refs/heads/{integration_branch}"
        )
        run["landing"].update(
            {
                "mode": "integration_pull_request",
                "head_branch": "refs/heads/codex/feature",
                "base_branch": integration_branch,
                "continuity": {
                    "status": "planned",
                    "branch_ref": integration_branch_ref,
                    "head_sha": None,
                    "reason": "Merge the reviewed feature into the retained integration branch",
                },
            }
        )

        self.assertEqual([], validate_run(plan, run))

    def test_v10_remote_ci_and_cloud_actions_require_exact_target_kinds(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        self._authorize(run, "trigger_remote_ci", "runtime:github-actions")
        self._authorize(run, "provision_cloud_resources", "environment:development")

        errors = validate_run(plan, run)

        self.assertTrue(
            any("trigger_remote_ci requires workflow:<identity> targets" in error for error in errors)
        )
        self.assertTrue(
            any("provision_cloud_resources requires cloud-resource:" in error for error in errors)
        )

    def test_existing_v10_without_contract_keeps_generic_exact_targets(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root, strict_action_targets=False)
        target = "remote:origin/development"
        self._authorize(run, "push", target)
        run["authorizations"]["push"].update(
            {
                "authorized_head_sha": run["integration"]["integration_head_sha"],
                "target_sources": {
                    target: "user: separately authorize this exact remote target"
                },
            }
        )

        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, run))

    def test_v10_head_bound_actions_reject_wrong_target_kinds(self) -> None:
        for action, target in (
            ("push", "release:development"),
            ("create_pr", "workflow:github-actions:ci"),
            ("manage_pr_review", "branch:development"),
            ("merge_pr", "branch:development"),
            ("deploy", "pr:https://github.com/acme/app/pull/1"),
        ):
            with self.subTest(action=action, target=target):
                root = self._seed_repo()
                plan, run = current_plan_and_run(root)
                entry: dict[str, object] = {
                    "authorized": True,
                    "source": f"user: authorize {action}",
                    "authorized_head_sha": "a" * 40,
                    "scope": {
                        "run_id": run["run_id"],
                        "plan_revision": run["plan"]["revision"],
                        "plan_digest_sha256": run["plan"]["digest_sha256"],
                        "mission_ids": list(run["mission_states"]),
                        "targets": [target],
                    },
                    "expires_when": "run_complete",
                }
                if action in {"push", "merge_pr", "deploy"}:
                    entry["target_sources"] = {
                        target: f"user: separately authorize {target}"
                    }
                run["authorizations"][action] = entry

                errors = validate_run(plan, run)

                self.assertTrue(
                    any("target kind" in error for error in errors),
                    f"expected {action} to reject {target!r}: {errors!r}",
                )

    def test_v10_unauthorized_scoped_actions_reject_target_sources(self) -> None:
        for action in ("push", "merge_pr", "deploy"):
            with self.subTest(action=action):
                root = self._seed_repo()
                plan, run = current_plan_and_run(root)
                run["authorizations"][action] = {
                    "authorized": False,
                    "source": None,
                    "target_sources": {
                        "branch:production": "user: stale authorization source"
                    },
                }

                errors = validate_run(plan, run)

                self.assertTrue(
                    any(
                        f"run.authorizations.{action}.target_sources" in error
                        and "must be omitted when unauthorized" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_v10_remote_ci_and_cloud_actions_reject_wildcard_targets(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        self._authorize(run, "trigger_remote_ci", "*")
        self._authorize(run, "provision_cloud_resources", "*")

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                "trigger_remote_ci requires exact targets, not *" in error
                for error in errors
            )
        )
        self.assertTrue(
            any(
                "provision_cloud_resources requires exact targets, not *" in error
                for error in errors
            )
        )

    def test_v10_cloud_resource_target_accepts_exact_four_part_identity(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        target = "cloud-resource:aws:development:s3:asset-bucket"
        self._authorize(run, "provision_cloud_resources", target)

        self.assertEqual([], validate_run(plan, run))
        self.assertTrue(authorization_covers(run, "provision_cloud_resources", "M1", target))

    def test_v10_accepts_parent_retained_verifier_execution(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        execution = retained_batch_execution(plan, run)
        run["verifier_executions"] = [execution]

        self.assertEqual(
            run["integration"]["batch_base_sha"],
            execution["context"]["batch_base_sha"],
        )
        self.assertEqual(
            run["integration"]["integration_head_sha"],
            execution["context"]["head_sha"],
        )
        self.assertEqual([], validate_run(plan, run))

    def test_v10_gate_requires_later_exact_pass_after_failed_history(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        passed = retained_batch_execution(plan, run)
        failed = copy.deepcopy(passed)
        failed["execution_id"] = "VX-FAILED"
        failed["status"] = "FAIL"
        failed["exit_code"] = 1
        run["verifier_executions"] = [failed]
        run["batch_gate_results"][0].update(
            {
                "status": "PASS",
                "head_sha": run["integration"]["integration_head_sha"],
                "evidence": [passed["evidence_key"]],
            }
        )

        errors = validate_run(plan, run)
        self.assertTrue(
            any("requires exact PASS/exit-0 verifier execution evidence" in error for error in errors)
        )

        run["verifier_executions"].append(passed)
        self.assertEqual([], validate_run(plan, run))

    def test_v10_rejects_hashed_substitutes_for_integration_git_shas(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        execution = retained_batch_execution(plan, run)
        execution["context"]["batch_base_sha"] = hashlib.sha256(
            run["integration"]["batch_base_sha"].encode("ascii")
        ).hexdigest()
        execution["context"]["head_sha"] = hashlib.sha256(
            run["integration"]["integration_head_sha"].encode("ascii")
        ).hexdigest()
        execution["key_document"]["batch_base_sha"] = execution["context"][
            "batch_base_sha"
        ]
        execution["key_document"]["head_sha"] = execution["context"]["head_sha"]
        execution_key = hashlib.sha256(
            json.dumps(
                execution["key_document"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        execution["execution_key"] = execution_key
        execution["evidence_key"] = execution_key
        run["verifier_executions"] = [execution]

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                "context.batch_base_sha: must match run.integration.batch_base_sha"
                in error
                for error in errors
            )
        )
        self.assertTrue(
            any(
                "context.head_sha: must match run.integration.integration_head_sha"
                in error
                for error in errors
            )
        )

    def test_v10_accepts_parent_retained_release_smoke_execution(self) -> None:
        root = self._seed_repo()
        plan, run = current_release_plan_and_run(root, "manual")
        self._authorize_release(run, "deploy")
        declaration = plan["release"]["targets"][0]["smoke_verifiers"][0]
        execution = retained_batch_execution(plan, run)
        execution["verifier_id"] = declaration["id"]
        execution["layer"] = "release"
        execution["verifier"]["id"] = declaration["id"]
        execution["verifier"]["cwd"] = declaration["cwd"]
        execution["verifier"]["argv"] = declaration["argv"]
        execution["verifier"]["pass_signal"] = declaration["pass_signal"]
        execution["key_document"]["verifier_id"] = declaration["id"]
        execution["key_document"]["layer"] = "release"
        execution["key_document"]["cwd"] = declaration["cwd"]
        execution["key_document"]["argv"] = declaration["argv"]
        execution["key_document"]["pass_signal"] = declaration["pass_signal"]
        execution["context"]["layer"] = "release"
        execution_key = hashlib.sha256(
            json.dumps(
                execution["key_document"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        execution["execution_key"] = execution_key
        execution["evidence_key"] = execution_key
        run["verifier_executions"] = [execution]

        self.assertEqual([], validate_run(plan, run))

    def test_v10_rejects_forged_verifier_key_metadata_and_result(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        execution = retained_batch_execution(plan, run)
        execution["execution_key"] = "f" * 64
        execution["verifier"]["argv"] = ["python", "unexpected.py"]
        execution["status"] = "FAIL"
        execution["exit_code"] = 1
        execution["metrics"] = {"executed": 1, "reused": 1}
        run["verifier_executions"] = [execution]

        errors = validate_run(plan, run)

        self.assertTrue(any("execution_key: must match key_document" in error for error in errors))
        self.assertTrue(any("must exactly match the PLAN verifier declaration" in error for error in errors))
        self.assertFalse(any("must be PASS with exit_code 0" in error for error in errors))
        self.assertTrue(any("must record exactly one execution or exact cache reuse" in error for error in errors))

    def test_v10_rejects_non_runtime_verifier_document_and_cache_shape(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        execution = retained_batch_execution(plan, run)
        execution["key_document"]["unexpected"] = True
        execution["verifier"]["cache"] = {
            "mode": "unsafe_global",
            "environment_keys": ["PATH", "PATH"],
        }
        run["verifier_executions"] = [execution]

        errors = validate_run(plan, run)

        self.assertTrue(any("key_document: unknown keys: unexpected" in error for error in errors))
        self.assertTrue(any("verifier.cache.mode: has an unsupported value" in error for error in errors))
        self.assertTrue(any("verifier.cache.environment_keys: must be unique" in error for error in errors))

    def test_v10_rejects_stale_verifier_plan_context(self) -> None:
        root = self._seed_repo()
        plan, run = current_plan_and_run(root)
        execution = retained_batch_execution(plan, run)
        execution["context"]["plan_revision"] += 1
        run["verifier_executions"] = [execution]

        errors = validate_run(plan, run)

        self.assertTrue(
            any("context.plan_revision: must match run.plan.revision" in error for error in errors)
        )
        self.assertTrue(
            any("key_document.plan_revision: must match context" in error for error in errors)
        )


class NoOpAndDryRunTests(UpgradeHelpers, unittest.TestCase):
    def _upgrade_to_current(self, root: Path) -> tuple[Path, Path]:
        plan, run = safe_v4_plan_and_v9_run(root)
        plan_path = self._write_plan(root, plan)
        run_path = self._write_run(root, run)
        result = self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return plan_path, run_path

    def test_already_current_is_a_no_op(self) -> None:
        root = self._seed_repo()
        plan_path, run_path = self._upgrade_to_current(root)
        plan_before = plan_path.read_bytes()
        run_before = run_path.read_bytes()

        result = self._run_cli(
            "--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(root)
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("already current", result.stdout)
        self.assertEqual(plan_before, plan_path.read_bytes())
        self.assertEqual(run_before, run_path.read_bytes())

    def test_dry_run_writes_nothing(self) -> None:
        root = self._seed_repo()
        plan = upgradeable_plan()
        plan_path = self._write_plan(root, plan)
        before = plan_path.read_bytes()

        result = self._run_cli(
            "--plan", str(plan_path), "--repo-root", str(root), "--dry-run"
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("[dry-run]", result.stdout)
        self.assertIn("schema 2 -> 5", result.stdout)
        self.assertEqual(before, plan_path.read_bytes())


class SurroundingMarkdownTests(UpgradeHelpers, unittest.TestCase):
    def test_only_fenced_json_block_changes(self) -> None:
        root = self._seed_repo()
        plan = upgradeable_plan()
        body = json.dumps({"harness_plan": plan}, indent=2)
        document = (
            "# Plan: fixture\r\n"
            "\r\n"
            "Intro prose that must survive untouched.\r\n"
            "\r\n"
            "## Harness Plan Manifest\r\n"
            "\r\n"
            "```json\r\n"
            + body.replace("\n", "\r\n")
            + "\r\n```\r\n"
            "\r\n"
            "## Source Map\r\n"
            "\r\n"
            "| Source | Path |\r\n"
            "|---|---|\r\n"
            "| PRD | docs/prd.md |\r\n"
        )
        plan_path = root / "PLAN.md"
        plan_path.write_bytes(document.encode("utf-8"))

        result = self._run_cli("--plan", str(plan_path), "--repo-root", str(root))

        self.assertEqual(0, result.returncode, result.stderr)
        rewritten = plan_path.read_bytes().decode("utf-8")
        # Every prose/heading/table line outside the fence is byte-identical.
        for line in (
            "# Plan: fixture",
            "Intro prose that must survive untouched.",
            "## Source Map",
            "| Source | Path |",
            "| PRD | docs/prd.md |",
        ):
            self.assertIn(line + "\r\n", rewritten)
        # Line endings stay CRLF only.
        self.assertNotIn("\n", rewritten.replace("\r\n", ""))
        self.assertEqual(5, load_plan(plan_path)["schema_version"])


if __name__ == "__main__":
    unittest.main()
