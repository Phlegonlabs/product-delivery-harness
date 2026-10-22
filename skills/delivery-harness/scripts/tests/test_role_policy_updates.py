"""Role-policy boundaries with synthetic host envelopes and real CLI/Git."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parent))

import worker_ingestion_fixture as fixture
import harness_transition
from agent_role_bindings import resolve_runtime_binding, validate_execution_binding
from agent_role_policy_updates import (
    HISTORY_KEY, load_policy_patch, policy_digest, runtime_for_reservation,
    update_role_bindings, validate_policy_history,
)
from harness_manifest import ManifestError, load_run, validate_current_plan_run, validate_run
from role_contract_fixtures import native_writer_binding, configure_role_run, authorize_selection
from manifest_fixtures import valid_plan, valid_run
from test_agent_failure_receipts import failed_attempt
from role_contract_fixtures import retain_failure
from agent_role_recovery import resolve_fallback_reservation
from agent_launch_records import validate_launch_record


def sol_binding():
    binding = native_writer_binding()
    binding.update(native_agent_type="default", model="gpt-6.1-sol", reasoning_effort="xhigh")
    return binding


class RolePolicyUnitTests(unittest.TestCase):
    def test_new_lease_and_launch_cannot_request_the_archived_model(self):
        plan = valid_plan()
        run = configure_role_run(plan, valid_run(plan))
        authorize_selection(run)
        run["active_wave"]["status"] = "closed"
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "policy.json"
            policy.write_text(json.dumps({"contract_writer": sol_binding()}), encoding="utf-8")
            update_role_bindings(plan, run, SimpleNamespace(
                policy=policy, expected_role_bindings_sha256=policy_digest(run["runtime_capabilities"]["runtime_adapter"]["role_bindings"]),
                update_id="NEW-LEASE", owner_source="synthetic owner", session_id="parent", repo_root=Path(directory) / "checkout"))
        run["active_wave"].update(wave_id="W1", status="active", batch_base_sha="a" * 40, selected_missions=["M1"])
        run["integration"]["batch_base_sha"] = "a" * 40
        run["mission_states"]["M1"].update(phase="ready", base_sha="a" * 40)
        arguments = SimpleNamespace(mission_id="M1", node_id="N-M1", worker_id="new-worker", lease_id="new-lease",
            attempt_id="new-attempt", branch_ref="refs/heads/codex/m1", worktree_path="C:/repo/worktrees/m1",
            provider="codex", driver="external_bridge", model="claude-opus-5-5", reasoning_effort="high",
            worker_runtime="subagent", workspace_mode="parent_managed_worktree", completion_channel="agent_result",
            task_thread_id=None, report_path=None, fallback_record=None)
        before = copy.deepcopy(run)
        with self.assertRaises(ManifestError):
            harness_transition._lease_worker(plan, run, arguments)
        self.assertEqual(before, run)
        arguments.driver, arguments.model, arguments.reasoning_effort = "subagents", "gpt-6.1-sol", "xhigh"
        harness_transition._lease_worker(plan, run, arguments)
        self.assertEqual("gpt-6.1-sol", run["workers"][-1]["runtime_binding"]["model"])
        for observed in ("glm-5.3", "claude-opus-5-5"):
            launch = SimpleNamespace(assignment_kind="mission", assignment_id="new-lease", node_id="N-M1",
                worker_id="new-worker", attempt_id="new-attempt", model_provider="codex", model=observed,
                reasoning_effort="xhigh", worker_session_id="new-session", launch_observation="synthetic start",
                host_observation="test-owned host envelope", fallback_record=None)
            before = copy.deepcopy(run)
            with self.assertRaises(ManifestError):
                harness_transition._record_launch_observation(plan, run, launch)
            self.assertEqual(before, run)

    def test_review_history_requires_the_exact_review_join(self):
        plan = valid_plan()
        run = configure_role_run(plan, valid_run(plan))
        authorize_selection(run)
        node = next(row for row in plan["graph"]["nodes"] if row["id"] == "N-REVIEW-M1")
        old = {"node_id": node["id"], "worker_id": "review-old", "attempt_id": "review-attempt",
               "phase": "worker_failed", "reviewed_sha": "a" * 40, "base_sha": "a" * 40,
               "runtime_binding": resolve_runtime_binding(node, run["runtime_capabilities"])}
        run["review_workers"] = [old]
        run["active_wave"]["status"] = "closed"
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "review-policy.json"
            replacement = sol_binding()
            replacement["workspace_mode"] = "shared_checkout"
            policy.write_text(json.dumps({"reviewer": replacement}), encoding="utf-8")
            update_role_bindings(plan, run, SimpleNamespace(
                policy=policy, expected_role_bindings_sha256=policy_digest(run["runtime_capabilities"]["runtime_adapter"]["role_bindings"]),
                update_id="REVIEW-POLICY", owner_source="synthetic owner review policy", session_id="parent", repo_root=Path(directory) / "checkout"))
        self.assertEqual([], validate_policy_history(plan, run))
        self.assertEqual([], validate_execution_binding("old", old["runtime_binding"], node,
                         runtime_for_reservation(run, "review", old, node["id"])))
        for key in ("node_id", "worker_id", "attempt_id"):
            altered = {**old, key: "OTHER"}
            self.assertTrue(validate_execution_binding("old", old["runtime_binding"], node,
                            runtime_for_reservation(run, "review", altered, altered["node_id"])), key)
        self.assertTrue(validate_execution_binding("old", old["runtime_binding"], node,
                        runtime_for_reservation(run, "mission", old, node["id"])))

    def test_historical_fallback_uses_exact_policy_and_fresh_fallback_uses_current(self):
        with tempfile.TemporaryDirectory() as directory:
            plan = valid_plan()
            configure_role_run(plan, valid_run(plan))
            run, node, primary, evidence = failed_attempt("mission")
            authorize_selection(run)
            primary["failure_receipt"] = retain_failure(directory, primary, evidence)
            binding, errors = resolve_fallback_reservation(node, run, evidence, "fallback-attempt")
            self.assertEqual([], errors)
            fallback = {"mission_id": "M1", "lease_id": "fallback-lease", "worker_id": "fallback-worker",
                        "attempt_id": "fallback-attempt", "phase": "worker_running",
                        "batch_base_sha": "a" * 40, "runtime_binding": binding}
            run["workers"].append(fallback)
            fallback_path = Path(directory) / "fallback.json"
            fallback_path.write_text(json.dumps(evidence), encoding="utf-8")
            harness_transition._record_launch_observation(plan, run, SimpleNamespace(
                assignment_kind="mission", assignment_id="fallback-lease", node_id=node["id"],
                worker_id="fallback-worker", attempt_id="fallback-attempt", model_provider="codex",
                model="gpt-6-sol", reasoning_effort="high", worker_session_id="fallback-session",
                launch_observation="synthetic fallback start", host_observation="test-owned host envelope",
                fallback_record=fallback_path))
            fallback["phase"] = "worker_failed"
            run["active_wave"]["status"] = "closed"
            policy_path = Path(directory) / "policy.json"
            policy_path.write_text(json.dumps({"contract_writer": sol_binding(), "backend_worker": sol_binding()}), encoding="utf-8")
            update_role_bindings(plan, run, SimpleNamespace(
                policy=policy_path, expected_role_bindings_sha256=policy_digest(run["runtime_capabilities"]["runtime_adapter"]["role_bindings"]),
                update_id="FALLBACK-POLICY", owner_source="synthetic owner policy", session_id="parent", repo_root=Path(directory) / "checkout"))
            self.assertEqual([], validate_policy_history(plan, run))
            self.assertEqual([], validate_launch_record(run, assignment_kind="mission", assignment_id="fallback-lease",
                node_id=node["id"], attempt_id="fallback-attempt", worker_id="fallback-worker",
                worker_role_expected="contract_writer", reserved=fallback))
            self.assertTrue(resolve_fallback_reservation(node, run, evidence, "fresh-current")[1])
            run["runtime_capabilities"]["runtime_adapter"]["role_bindings"]["contract_writer"]["fallback_role"] = "backend_worker"
            self.assertTrue(resolve_fallback_reservation(node, run, evidence, "fresh-current")[1])
            current = copy.deepcopy(evidence)
            current["configured_fallback"].update(model="gpt-6.1-sol", reasoning_effort="xhigh")
            self.assertEqual([], resolve_fallback_reservation(node, run, current, "fresh-current")[1])

    def test_bounded_duplicate_and_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            for raw in ('{"x":{},"x":{}}', '{"x":{"model":NaN}}',
                        '{"x":{"model":1e999}}', '{"x":{"model":-1e999}}',
                        '[]', '{}', 'x' * (1024 * 1024 + 1)):
                path.write_text(raw, encoding="utf-8")
                with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                    load_policy_patch(path)

    def test_current_sol_for_each_logical_author_and_plan_options_stay_binding(self):
        plan = valid_plan()
        run = configure_role_run(plan, valid_run(plan))
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        for role in ("frontend_worker", "backend_worker", "implementer"):
            adapter["role_bindings"][role] = sol_binding()
            node = copy.deepcopy(plan["graph"]["nodes"][0])
            node["runtime"]["worker_role"] = role
            resolved = resolve_runtime_binding(node, run["runtime_capabilities"])
            self.assertEqual((role, "default", "codex", "gpt-6.1-sol", "xhigh"),
                             tuple(resolved[key] for key in ("worker_role", "native_agent_type", "model_provider", "model", "reasoning_effort")))
            for model in ("glm-5.3", "claude-opus-5-5"):
                tampered = {**resolved, "model": model}
                self.assertTrue(validate_execution_binding("binding", tampered, node, run["runtime_capabilities"]))
            node["runtime"].setdefault("provider_options", {})[adapter["provider"]] = {"model": "claude-opus-5-5", "reasoning_effort": None}
            self.assertIsNone(resolve_runtime_binding(node, run["runtime_capabilities"]))


class RolePolicyCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = fixture.build_original_failure()
        fixture.prepare_recovery(cls.fx)
        cls.baseline = cls.fx.run_path.read_bytes()
        cls.tasks = (cls.fx.root / "docs/tasks.md").read_bytes()
        cls.plan_bytes = cls.fx.plan_path.read_bytes()
        cls.policy_path = cls.fx.evidence / "role-policy.json"
        cls.policy_path.write_text(json.dumps({"contract_writer": sol_binding(), "backend_worker": sol_binding()}), encoding="utf-8")
        cls.expected = policy_digest(load_run(cls.fx.run_path)["runtime_capabilities"]["runtime_adapter"]["role_bindings"])

    @classmethod
    def tearDownClass(cls):
        cls.fx.skills_temp.cleanup()
        cls.fx.temp.cleanup()

    def setUp(self):
        self.fx.run_path.write_bytes(self.baseline)
        (self.fx.root / "docs/tasks.md").write_bytes(self.tasks)
        self.fx.plan_path.write_bytes(self.plan_bytes)

    def invoke(self, *, expected=None, update_id="OWNER-SOL-001", session="parent-session", policy=None, owner="synthetic owner Sol instruction"):
        return fixture.transition(
            "--plan", str(self.fx.plan_path), "--run", str(self.fx.run_path),
            "--repo-root", str(self.fx.root), "--session-id", session,
            "update-role-bindings", "--policy", str(policy or self.policy_path),
            "--expected-role-bindings-sha256", expected or self.expected,
            "--update-id", update_id, "--owner-source", owner, script=self.fx.active_script)

    def test_real_update_preserves_original_attempts_and_replay_bytes(self):
        before = load_run(self.fx.run_path)
        result = self.invoke()
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        after = load_run(self.fx.run_path)
        self.assertEqual([], validate_current_plan_run(self.fx.plan, after, repo_root=self.fx.root))
        for key in ("workers", "review_workers", "launch_records", "mission_states", "task_states", "graph_state", "authorizations", "plan", "attempt_log"):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(self.plan_bytes, self.fx.plan_path.read_bytes())
        self.assertEqual(self.tasks, (self.fx.root / "docs/tasks.md").read_bytes())
        rows = after[HISTORY_KEY]["updates"][0]["reservations"]
        self.assertEqual(2, len(rows))
        self.assertTrue(all(row["runtime_binding"]["model"] == "claude-opus-5-5" for row in rows))
        node = next(n for n in self.fx.plan["graph"]["nodes"] if n["id"] == "N-M1")
        fresh = resolve_runtime_binding(node, after["runtime_capabilities"])
        self.assertEqual("gpt-6.1-sol", fresh["model"])
        old = after["workers"][0]
        self.assertEqual([], validate_execution_binding("old", old["runtime_binding"], node,
                         runtime_for_reservation(after, "mission", old, "N-M1")))
        new = {**old, "lease_id": "L-NEW", "worker_id": "W-NEW", "attempt_id": "A-NEW"}
        self.assertTrue(validate_execution_binding("new", old["runtime_binding"], node,
                        runtime_for_reservation(after, "mission", new, "N-M1")))
        saved = self.fx.run_path.read_bytes()
        replay = self.invoke()
        self.assertEqual(0, replay.returncode, replay.stderr)
        self.assertFalse(json.loads(replay.stdout)["recorded"])
        self.assertEqual(saved, self.fx.run_path.read_bytes())
        conflict = self.invoke(owner="different owner evidence")
        self.assertNotEqual(0, conflict.returncode)
        self.assertEqual(saved, self.fx.run_path.read_bytes())

    def test_negative_inputs_preserve_run_and_tasks(self):
        before = load_run(self.fx.run_path)
        mutations = {
            "foreign lock": lambda r: r["run_lock"].update(session_id="another-parent"),
            "active wave": lambda r: r["active_wave"].update(status="active"),
            "proposed wave": lambda r: r["active_wave"].update(status="proposed"),
            "live worker": lambda r: r["workers"][-1].update(phase="worker_running"),
            "live reviewer": lambda r: r["review_workers"].append({"phase": "leased"}),
            "running graph": lambda r: r["graph_state"]["node_states"]["N-M1"].update(phase="running"),
            "reserved node": lambda r: r["attempt_log"].append({"kind": "node_attempt", "result": "reserved"}),
            "no authority": lambda r: r.update(execution_authorized=False),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                state = copy.deepcopy(before)
                mutate(state)
                self.fx.run_path.write_text(fixture.mf.manifest_markdown("## Harness Run State", "harness_run", state), encoding="utf-8")
                saved = self.fx.run_path.read_bytes()
                result = self.invoke()
                self.assertNotEqual(0, result.returncode, result.stdout)
                self.assertEqual(saved, self.fx.run_path.read_bytes())
                self.assertEqual(self.tasks, (self.fx.root / "docs/tasks.md").read_bytes())
        self.fx.run_path.write_bytes(self.baseline)
        self.assertNotEqual(0, self.invoke(expected="0" * 64).returncode)
        self.assertEqual(self.baseline, self.fx.run_path.read_bytes())
        self.assertNotEqual(0, self.invoke(session="another-parent").returncode)
        self.assertEqual(self.baseline, self.fx.run_path.read_bytes())
        for label, policy in (
            ("unknown", {"unknown_role": sol_binding()}),
            ("unknown field", {"contract_writer": {**sol_binding(), "bypass": True}}),
            ("unavailable", {"contract_writer": {**sol_binding(), "capability_probe": {"direct_subagent_spawn": {"status": "unavailable", "evidence": "no tool", "probe_id": "no"}}}}),
        ):
            with self.subTest(policy=label):
                path = self.fx.evidence / (label.replace(" ", "-") + ".json")
                path.write_text(json.dumps(policy), encoding="utf-8")
                result = self.invoke(policy=path)
                self.assertNotEqual(0, result.returncode, result.stdout)
                self.assertEqual(self.baseline, self.fx.run_path.read_bytes())

    def test_history_chain_identity_and_first_boundary_reject_tampering(self):
        self.assertEqual(0, self.invoke().returncode)
        run = load_run(self.fx.run_path)
        for key in ("lease_id", "worker_id", "attempt_id", "mission_id"):
            changed = copy.deepcopy(run)
            changed["workers"][0][key] = "OTHER"
            self.assertTrue(validate_policy_history(self.fx.plan, changed), key)
        for key in ("model", "reasoning_effort", "model_provider", "native_agent_type", "worker_role", "completion_channel", "capability_probe"):
            changed = copy.deepcopy(run)
            changed["workers"][0]["runtime_binding"][key] = "OTHER"
            self.assertTrue(validate_policy_history(self.fx.plan, changed), key)
        for key in ("session_id", "model", "reasoning_effort"):
            changed = copy.deepcopy(run)
            changed["launch_records"][0][key] = "OTHER"
            self.assertTrue(validate_run(self.fx.plan, changed), key)
        for key in ("worker_head_sha", "batch_base_sha", "branch_ref", "worktree_path"):
            changed = copy.deepcopy(run)
            changed["workers"][-1][key] = "OTHER"
            self.assertTrue(validate_policy_history(self.fx.plan, changed), key)
        args = SimpleNamespace(policy=self.policy_path, expected_role_bindings_sha256=policy_digest(run["runtime_capabilities"]["runtime_adapter"]["role_bindings"]),
                               update_id="OWNER-SOL-002", owner_source="second synthetic policy", session_id="parent-session", repo_root=self.fx.root)
        second_path = self.fx.evidence / "second-policy.json"
        second_path.write_text(json.dumps({"backend_worker": {**sol_binding(), "model": "another-explicit-model"}}), encoding="utf-8")
        args.policy = second_path
        update_role_bindings(self.fx.plan, run, args)
        self.assertEqual([], validate_policy_history(self.fx.plan, run))
        self.assertEqual([], run[HISTORY_KEY]["updates"][1]["reservations"])
        changed = copy.deepcopy(run)
        changed[HISTORY_KEY]["updates"][1]["reservations"] = changed[HISTORY_KEY]["updates"][0]["reservations"]
        changed[HISTORY_KEY]["updates"][0]["reservations"] = []
        self.assertTrue(validate_policy_history(self.fx.plan, changed))
        changed = copy.deepcopy(run)
        changed[HISTORY_KEY]["updates"][1]["before"] = changed[HISTORY_KEY]["updates"][0]["before"]
        self.assertTrue(validate_policy_history(self.fx.plan, changed))

    def test_plan_run_cas_still_guard_update(self):
        parsed = harness_transition.build_parser().parse_args([
            "--plan", str(self.fx.plan_path), "--run", str(self.fx.run_path), "--repo-root", str(self.fx.root),
            "--session-id", "parent-session", "update-role-bindings", "--policy", str(self.policy_path),
            "--expected-role-bindings-sha256", self.expected, "--update-id", "RACE", "--owner-source", "synthetic owner"])
        real = harness_transition._ensure_plan_unchanged

        def race(path, expected):
            self.fx.plan_path.write_bytes(self.plan_bytes + b"\nconcurrent note\n")
            real(path, expected)

        with patch.object(harness_transition, "_ensure_plan_unchanged", race), self.assertRaises(ManifestError):
            harness_transition._transition_under_lock(parsed, self.fx.plan,
                expected_plan_text=self.fx.plan_path.read_text(encoding="utf-8"))
        self.assertEqual(self.baseline, self.fx.run_path.read_bytes())
        self.fx.plan_path.write_bytes(self.plan_bytes)
        replace = harness_transition._replace_run_document

        def run_race(path, run, **kwargs):
            self.fx.run_path.write_bytes(self.baseline + b"\nconcurrent run note\n")
            replace(path, run, **kwargs)

        with patch.object(harness_transition, "_replace_run_document", run_race), self.assertRaises(ManifestError):
            harness_transition._transition_under_lock(parsed, self.fx.plan,
                expected_plan_text=self.fx.plan_path.read_text(encoding="utf-8"))
        self.assertEqual(self.baseline + b"\nconcurrent run note\n", self.fx.run_path.read_bytes())

    def test_ingestion_reconciliation_remains_valid_after_policy_update(self):
        self.assertEqual(0, self.invoke().returncode)
        result = fixture.transition(
            "--plan", str(self.fx.plan_path), "--run", str(self.fx.run_path), "--repo-root", str(self.fx.root),
            "--session-id", "parent-session", "reconcile-worker-ingestion", *fixture.recovery_flags(self.fx),
            script=self.fx.active_script)
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertEqual([], validate_current_plan_run(self.fx.plan, load_run(self.fx.run_path), repo_root=self.fx.root))


if __name__ == "__main__":
    unittest.main()
