"""Real CLI/verifier fixtures for stale-head ingestion reconciliation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
PRODUCT_TESTS_DIR = ROOT / "skills/product-definition-builder/scripts/tests"
for entry in (str(TESTS_DIR), str(SCRIPTS_DIR), str(PRODUCT_TESTS_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import manifest_fixtures as mf  # noqa: E402
import contract_package_fixture  # noqa: E402
import role_contract_fixtures as role_fixtures  # noqa: E402
import verifier_runtime  # noqa: E402
from test_host_verifier_runtime import host_verifier  # noqa: E402
from test_role_dispatch_integration import launch_arguments  # noqa: E402
from harness_core import plan_digest  # noqa: E402
from harness_manifest import load_run  # noqa: E402
__import__("test_product_package_checker")  # cached for manifest_fixtures' lazy import

# Another skill's tests directory stays on sys.path only for the imports above;
# left there, discovery imports that skill's test_skill_contract instead.
while str(PRODUCT_TESTS_DIR) in sys.path:
    sys.path.remove(str(PRODUCT_TESTS_DIR))


def cli(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-X", "utf8", str(script), *arguments],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=60,
    )


def transition(*arguments: str, script: Path | None = None) -> subprocess.CompletedProcess[str]:
    return cli(script or (SCRIPTS_DIR / "harness_transition.py"), *arguments)


def make_skill_copy(destination: Path, marker: str | None = None) -> Path:
    shutil.copytree(ROOT / "skills", destination)
    if marker is not None:
        (destination / "delivery-harness/CONTRACT-FIXTURE.txt").write_text(marker + "\n", encoding="utf-8")
    return destination


def _sync_digest(plan, run):
    digest = plan_digest(plan)
    run["plan"]["digest_sha256"] = digest
    run["execution_authorization_scope"]["plan_digest_sha256"] = digest
    for authorization in run["authorizations"].values():
        if isinstance(authorization, dict) and isinstance(authorization.get("scope"), dict):
            authorization["scope"]["plan_digest_sha256"] = digest


def _configure(plan, run):
    """Bind runtime policy without changing the genuine package graph."""
    run["runtime_capabilities"].update(
        {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 2,
            "runtime_adapter": {
                "provider": "claude_code",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "observed",
                "capability_probe": role_fixtures.native_capability_probe(subagents=True),
                "role_bindings": {
                    "contract_writer": role_fixtures.bridge_binding(),
                    "backend_worker": role_fixtures.native_writer_binding(),
                    "reviewer": role_fixtures.native_reviewer_binding(),
                },
                "version_gate": run["runtime_capabilities"]["runtime_adapter"]["version_gate"],
            },
        }
    )
    run["observed"]["runtime"].update(
        {"available_worker_slots": 2, "isolation_capacity": 2}
    )
    run["runtime_capabilities"]["permission_boundary"] = {
        "selected_mode": "full_access",
        "profile_name": None,
        "approval_policy": "never",
        "filesystem_scope": "unrestricted",
        "network_scope": "open",
        "local_binding": "allowed",
        "worker_inheritance": "inherited",
        "status": "ready",
    }
    for node in plan["graph"]["nodes"]:
        if node.get("executor") != "runtime_worker":
            continue
        node.setdefault("runtime", {})["worker_role"] = (
            "reviewer" if node.get("kind") == "verifier" else "contract_writer"
        )


def _bind_runtime(plan, run):
    _configure(plan, run)
    role_fixtures.authorize_selection(run)
    run["observed"]["sandbox"] = mf.sandbox_observation(plan)

def _make_host(declaration, source):
    replacement = host_verifier(source)
    replacement["id"] = declaration["id"]
    if "acceptance_test_ids" in declaration:
        replacement["acceptance_test_ids"] = declaration["acceptance_test_ids"]
    return replacement


def adopt_contract(root: Path, skills_root: Path, run_path: Path, digest: str, session: str):
    script = skills_root / "delivery-harness/scripts/harness_transition.py"
    return transition(
        "--plan", str(root / "docs/goal/PLAN.md"),
        "--run", str(run_path),
        "--repo-root", str(root),
        "--session-id", session,
        "adopt-runtime-contract",
        "--owner-source", "synthetic fixture owner authorization",
        "--reading-evidence", "read the synthetic fixture contract",
        "--expected-contract-digest", digest,
        script=script,
    )


def build_reserved_worker():
    temp = tempfile.TemporaryDirectory()
    outer = Path(temp.name)
    root = outer / 'checkout'
    root.mkdir(parents=True)
    skills_temp = tempfile.TemporaryDirectory(prefix="ingestion005-skills-")
    with mf.eval_exempt_product_fixture():
        package = contract_package_fixture.current_package(
            root, pin=(SCRIPTS_DIR.parent / "VERSION").read_text(encoding="utf-8").strip()
        )
    mf.git(root, "branch", "-m", "master", "main")
    mf.git(root, "branch", "integration")
    mf.git(root, "checkout", "-q", "integration")
    plan = package["plan"]
    for mission in plan["missions"]:
        for task in mission["tasks"]:
            task["verifiers"] = [_make_host(task["verifiers"][0], f"print('task {task['id']}')")]
        mission["worker_verifiers"] = [_make_host(mission["worker_verifiers"][0], f"print('worker {mission['id']}')")]
        mission["integration_verifiers"] = [_make_host(mission["integration_verifiers"][0], f"print('integration {mission['id']}')")]
    mission = next(item for item in plan["missions"] if item["id"] == "M1")
    plan["batch_verifiers"] = [_make_host(plan["batch_verifiers"][0], "print('batch')")]
    plan["final_gates"] = [_make_host(plan["final_gates"][0], "print('final')")]
    _configure(plan, package["run"])
    for source in plan["sources"]:
        path = root / source["location"]
        source["content_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (root / "docs/goal").mkdir(parents=True, exist_ok=True)
    plan_path = root / "docs/goal/PLAN.md"
    plan_path.write_text(mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", plan), encoding="utf-8")
    generated = cli(
        SCRIPTS_DIR / "new_run.py", "--plan", str(plan_path), "--run-id", "RUN-INGESTION",
        "--branch", "refs/heads/integration", "--repo-root", str(root), "--out", str(root / "docs/goal/RUN.md"),
    )
    if generated.returncode:
        temp.cleanup()
        raise AssertionError(generated.stderr)
    run = load_run(root / "docs/goal/RUN.md")
    _bind_runtime(plan, run)
    (root / "docs/goal/RUN.md").write_text(
        mf.manifest_markdown("## Harness Run State", "harness_run", run), encoding="utf-8"
    )
    mf.git(root, "add", "docs/goal/PLAN.md", "docs/goal/RUN.md", "docs/tasks.md")
    mf.git(root, "commit", "-qm", "fixture plan and run")

    skills_base = Path(skills_temp.name)
    skills_s3 = make_skill_copy(skills_base / "skills-s3", "S3")
    skills_s4 = make_skill_copy(skills_base / "skills-s4", "S4")
    from harness_contract import contract_digest
    digest_s3 = contract_digest(skills_s3)
    digest_s4 = contract_digest(skills_s4)
    active_script = skills_s3 / "delivery-harness/scripts/harness_transition.py"
    locked = transition(
        "--plan", str(plan_path), "--run", str(root / "docs/goal/RUN.md"), "--repo-root", str(root),
        "--session-id", "parent-session",
        "acquire-run-lock",
        script=active_script,
    )
    if locked.returncode:
        temp.cleanup()
        raise AssertionError(locked.stderr + locked.stdout)
    adopted = adopt_contract(root, skills_s3, root / "docs/goal/RUN.md", digest_s3, "parent-session")
    released = transition(
        "--plan", str(plan_path), "--run", str(root / "docs/goal/RUN.md"), "--repo-root", str(root),
        "--session-id", "parent-session",
        "release-run-lock",
        script=active_script,
    )
    if adopted.returncode or released.returncode:
        temp.cleanup()
        raise AssertionError(adopted.stderr + adopted.stdout + released.stderr + released.stdout)
    parent_locked = transition(
        "--plan", str(plan_path), "--run", str(root / "docs/goal/RUN.md"), "--repo-root", str(root),
        "--session-id", "parent-session", "acquire-run-lock",
        script=active_script,
    )
    if parent_locked.returncode:
        temp.cleanup()
        raise AssertionError(parent_locked.stderr + parent_locked.stdout)

    base = mf.git(root, "rev-parse", "HEAD")
    worker_root = outer / "worker-m1"
    mf.git(root, "worktree", "add", "-q", "-b", "feature/m1", str(worker_root), base)
    observed = transition(
        "--plan", str(plan_path), "--run", str(root / "docs/goal/RUN.md"), "--repo-root", str(root),
        "--session-id", "parent-session", "record-observation",
        script=active_script,
    )
    if observed.returncode:
        temp.cleanup()
        raise AssertionError(observed.stderr + observed.stdout)
    accepted = transition(
        "--plan", str(plan_path), "--run", str(root / "docs/goal/RUN.md"), "--repo-root", str(root),
        "--session-id", "parent-session", "accept-wave", "--wave-id", "WAVE-001",
        "--mission-id", "M1", "--batch-base-sha", base,
        script=active_script,
    )
    if accepted.returncode:
        debug_run = load_run(root / "docs/goal/RUN.md")
        print("SANDBOX_DEBUG " + json.dumps(debug_run["observed"].get("sandbox"), ensure_ascii=False))
        print("HOST_DEBUG " + json.dumps(debug_run["observed"].get("host_runtime"), ensure_ascii=False))
        temp.cleanup()
        raise AssertionError(accepted.stderr + accepted.stdout)

    leased = transition(
        "--plan", str(plan_path), "--run", str(root / "docs/goal/RUN.md"), "--repo-root", str(root),
        "--session-id", "parent-session", "lease-worker", "--mission-id", "M1",
        "--node-id", "N-M1", "--worker-id", "W-M01-001", "--lease-id", "L-M01-001",
        "--attempt-id", "A-M01-001", "--branch-ref", "refs/heads/feature/m1",
        "--worktree-path", worker_root.as_posix(), "--provider", "claude_code",
        "--driver", "external_bridge", "--model", "claude-opus-5-5",
        "--reasoning-effort", "high", "--worker-runtime", "subagent",
        "--workspace-mode", "parent_managed_worktree", "--completion-channel", "agent_result",
        script=active_script,
    )
    if leased.returncode:
        debug_run = load_run(root / "docs/goal/RUN.md")
        print("WORKTREE_DEBUG " + json.dumps(debug_run["observed"]["git"]["worktrees"], ensure_ascii=False))
        temp.cleanup()
        raise AssertionError(leased.stderr + leased.stdout)

    launch = launch_arguments()
    launch.assignment_id = "L-M01-001"
    launch.worker_id = "W-M01-001"
    launch.attempt_id = "A-M01-001"
    launched = transition(
        "--plan", str(plan_path), "--run", str(root / "docs/goal/RUN.md"), "--repo-root", str(root),
        "--session-id", "parent-session", "record-launch-observation",
        "--assignment-id", "L-M01-001",
        "--node-id", "N-M1",
        "--worker-id", "W-M01-001",
        "--attempt-id", "A-M01-001",
        "--assignment-kind", launch.assignment_kind,
        "--assignment-id", launch.assignment_id,
        "--node-id", launch.node_id,
        "--worker-id", launch.worker_id,
        "--attempt-id", launch.attempt_id,
        "--model-provider", launch.model_provider,
        "--model", launch.model,
        "--reasoning-effort", launch.reasoning_effort,
        "--worker-session-id", launch.worker_session_id,
        "--launch-observation", launch.launch_observation,
        "--host-observation", launch.host_observation,
        script=active_script,
    )
    if launched.returncode:
        if os.environ.get("INGESTION005_PRESERVE_FAILURE"):
            return SimpleNamespace(
                root=root, outer=outer, plan=plan, plan_path=plan_path,
                run_path=root / "docs/goal/RUN.md", run=run, launch_arguments=launch,
            )
        temp.cleanup()
        raise AssertionError(launched.stderr + launched.stdout)
    return SimpleNamespace(
        temp=temp, skills_temp=skills_temp, root=root, plan=plan, plan_path=plan_path,
        run_path=root / "docs/goal/RUN.md", worker_root=worker_root, base=base,
        skills_s3=skills_s3, skills_s4=skills_s4,
        digest_s3=digest_s3, digest_s4=digest_s4,
        launch_arguments=launch, active_script=active_script, outer=outer,
    )


def _command(fixture, command, *arguments):
    result = transition(
        "--plan", str(fixture.plan_path), "--run", str(fixture.run_path),
        "--repo-root", str(fixture.root), "--session-id", "parent-session",
        command, *arguments, script=fixture.active_script,
    )
    if result.returncode:
        raise AssertionError(result.stderr + result.stdout)
    return result


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _node(fixture, attempt, outcome, worker_result=None):
    run = load_run(fixture.run_path)
    return {
        "run_id": run["run_id"], "plan_id": fixture.plan["plan_id"],
        "plan_revision": fixture.plan["revision"], "plan_digest_sha256": plan_digest(fixture.plan),
        "graph_revision": run["graph_state"]["graph_revision"], "node_id": "N-M1",
        "attempt_id": attempt, "batch_base_sha": fixture.base,
        "status": "succeeded" if outcome == "pass" else "failed", "outcome": outcome,
        "worker_result": worker_result, "refinement_request": None, "evidence_paths": [],
    }


def _receipt_files(fixture, payload, session, label):
    from agent_result_receipts import payload_digest
    source = _write_json(fixture.evidence / (label + "-host.json"), {
        "schema_version": 1, "session_id": session, "payload": payload,
    })
    receipt = {
        "kind": "returned_result", "session_id": session, "source_ref": source.as_posix(),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "payload_sha256": payload_digest(payload),
    }
    return _write_json(fixture.evidence / (label + "-receipt.json"), receipt)


def _check(fixture, declaration, layer, task_id, head):
    run = load_run(fixture.run_path)
    preflight = next(row for row in run["observed"]["host_runtime"]["entries"]
                     if row["argv0"] == declaration["argv"][0])
    context = {
        "run_id": run["run_id"], "plan_revision": fixture.plan["revision"],
        "plan_digest_sha256": plan_digest(fixture.plan),
        "graph_revision": run["graph_state"]["graph_revision"],
        "batch_base_sha": fixture.base, "head_sha": head,
        "changed_files": ["docs/README.md"], "trust_domain": "parent_local",
        "checkout_role": "worker", "checkout_dirty": False, "cache_safe": False,
        "layer": layer, "mission_id": "M1", "task_id": task_id,
        "attempt_id": "CHECK-" + declaration["id"], "lease_id": "L-M01-002",
    }
    result = verifier_runtime.run_verifier(
        declaration, context, checkout_root=fixture.worker_root,
        git_guard={"expected_branch": "refs/heads/feature/m1", "expected_head_sha": head,
                   "ignored_paths": []}, host_preflight=preflight, timeout_seconds=20,
    )
    if result["status"] != "PASS":
        raise AssertionError(result)
    output = _write_json(fixture.evidence / (declaration["id"] + ".json"), result)
    return result, output


def build_original_failure():
    """Exercise two real reservations and reproduce only the old head error."""
    fixture = build_reserved_worker()
    fixture.evidence = fixture.outer / "evidence"
    fixture.evidence.mkdir()
    # The first fixture child returns a real protocol failure, not a model call.
    first = _node(fixture, "A-M01-001", "retryable_failure")
    first_path = _write_json(fixture.evidence / "first-node.json", {"node_result": first})
    first_receipt = _receipt_files(fixture, first, "host-session-1", "first")
    _command(fixture, "record-worker-result", "--node-result", str(first_path),
             "--result-receipt", str(first_receipt))
    _command(fixture, "lease-worker", "--mission-id", "M1", "--node-id", "N-M1",
             "--worker-id", "W-M01-002", "--lease-id", "L-M01-002",
             "--attempt-id", "A-M01-002", "--branch-ref", "refs/heads/feature/m1",
             "--worktree-path", fixture.worker_root.as_posix())
    launch = fixture.launch_arguments
    _command(fixture, "record-launch-observation", "--assignment-kind", "mission",
             "--assignment-id", "L-M01-002", "--node-id", "N-M1",
             "--worker-id", "W-M01-002", "--attempt-id", "A-M01-002",
             "--model-provider", launch.model_provider, "--model", launch.model,
             "--reasoning-effort", launch.reasoning_effort,
             "--worker-session-id", "host-session-2",
             "--launch-observation", "synthetic second child; no real model call",
             "--host-observation", "test-owned host fixture")
    mission = next(row for row in fixture.plan["missions"] if row["id"] == "M1")
    tasks, verifiers, paths, commits = [], [], [], []
    for index, task in enumerate(mission["tasks"], 1):
        target = fixture.worker_root / "docs/README.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        previous = target.read_text(encoding="utf-8") if target.exists() else ""
        target.write_text(previous + f"\nFixture task {index}.\n",
                          encoding="utf-8")
        declaration = task["verifiers"][0]
        subprocess.run(declaration["argv"], cwd=fixture.worker_root, check=True,
                       capture_output=True, timeout=20)
        mf.git(fixture.worker_root, "add", "docs/README.md")
        message = (f"docs(fixture): complete task {index}\n\nTask: {task['id']}\n"
                   f"Trace: {', '.join(task['trace_ids'])}\n"
                   "Verified: synthetic host check (exit 0)")
        mf.git(fixture.worker_root, "commit", "-qm", message)
        head = mf.git(fixture.worker_root, "rev-parse", "HEAD")
        checked, checked_path = _check(fixture, declaration, "task", task["id"], head)
        verifiers.append(checked)
        paths.append(checked_path)
        commits.append(head)
        tasks.append({"task_id": task["id"], "status": "worker_passed", "head_sha": head,
                      "verifier_ids": [declaration["id"]], "commits": [head],
                      "evidence_paths": [checked_path.as_posix()]})
    checked, checked_path = _check(fixture, mission["worker_verifiers"][0], "worker", None, head)
    verifiers.append(checked)
    paths.append(checked_path)
    result = {
        "type": "WORKER_RESULT", "run_id": "RUN-INGESTION", "plan_id": fixture.plan["plan_id"],
        "mission_id": "M1", "lease_id": "L-M01-002", "status": "worker_passed",
        "current_task_id": None, "plan_revision": fixture.plan["revision"],
        "plan_digest_sha256": plan_digest(fixture.plan), "base_sha": fixture.base,
        "head_sha": head, "diff_summary": "Synthetic docs fixture; no real model execution.",
        "changed_files": ["docs/README.md"], "task_results": tasks, "commits": commits,
        "verifiers": [{"id": row["verifier_id"], "status": row["status"],
                       "evidence": row["execution_key"]} for row in verifiers],
        "evidence_paths": [path.as_posix() for path in paths], "blockers": [],
        "residual_risks": [], "integration_notes": "Synthetic controlled fixture.",
        "subagent_activity": {"status": "not_applicable", "children": [],
                              "skip_reason": "flat synthetic fixture, no delegation"},
        "contract_adoption_check": {"digest": fixture.digest_s3, "matched": True,
                                    "reading_evidence": ["Synthetic child reads its S3 fixture sources."]},
    }
    node = _node(fixture, "A-M01-002", "pass", result)
    node_path = _write_json(fixture.evidence / "second-node.json", {"node_result": node})
    report_path = fixture.evidence / "second-worker.md"
    report_path.write_text(mf.manifest_markdown("## Worker Result Manifest", "worker_result", result),
                           encoding="utf-8")
    receipt_path = _receipt_files(fixture, result, "host-session-2", "second")
    run = load_run(fixture.run_path)
    run["mission_states"]["M1"]["head_sha"] = fixture.base
    fixture.run_path.write_text(mf.manifest_markdown("## Harness Run State", "harness_run", run),
                                encoding="utf-8")
    flags = ["--node-result", str(node_path), "--worker-result", str(report_path),
             "--result-receipt", str(receipt_path)]
    for path in paths:
        flags.extend(["--verifier-result", str(path)])
    _command(fixture, "record-worker-result", *flags)
    run = load_run(fixture.run_path)
    expected = "observed_head_mismatch: worker_result.head_sha: does not match mission state"
    if run["mission_states"]["M1"]["blockers"] != [expected]:
        raise AssertionError(run["mission_states"]["M1"])
    original = fixture.evidence / "original-run.md"
    original.write_bytes(fixture.run_path.read_bytes())
    fixture.run = run
    fixture.worker_result, fixture.node_result = result, node
    fixture.node_path, fixture.report_path, fixture.receipt_path = node_path, report_path, receipt_path
    fixture.verifier_paths = paths
    fixture.original_run_path = original
    fixture.original_run_sha256 = hashlib.sha256(original.read_bytes()).hexdigest()
    fixture.head = head
    return fixture


def prepare_recovery(fixture):
    _command(fixture, "close-wave", "--source", "synthetic stopped worker boundary")
    fixture.active_script = fixture.skills_s4 / "delivery-harness/scripts/harness_transition.py"
    result = adopt_contract(fixture.root, fixture.skills_s4, fixture.run_path,
                            fixture.digest_s4, "parent-session")
    if result.returncode:
        raise AssertionError(result.stderr + result.stdout)
    return load_run(fixture.run_path)


def recovery_flags(fixture):
    flags = ["--node-result", str(fixture.node_path), "--worker-result", str(fixture.report_path),
             "--result-receipt", str(fixture.receipt_path), "--original-run", str(fixture.original_run_path),
             "--expected-original-run-sha256", fixture.original_run_sha256,
             "--reconciliation-id", "RECOVERY-M1-001", "--source", "synthetic owner accepted original candidate"]
    for path in fixture.verifier_paths:
        flags.extend(["--verifier-result", str(path)])
    return flags
