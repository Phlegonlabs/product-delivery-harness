#!/usr/bin/env python3
"""lease-worker --packet-out renders the worker goal packet from the leased RUN."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import manifest_fixtures as mf  # noqa: E402


SESSION = "lease-packet-tests"

HOST_VALUES = {
    "Worker contract": "references/runtime-adapters.md",
    "Parent launch identity": "session parent-1; wave W-1 accepted attempt A-M1",
    "Route caps": "time 900 / turns 40 / max_message_bytes 14000",
    "Permissions": "mode default; worktree writes only; approval never",
}


def load_run_block(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    start = text.find("```json\n") + len("```json\n")
    end = text.find("\n```", start)
    return json.loads(text[start:end])["harness_run"]


def save_run_block(path: Path, run: dict) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.find("```json\n")
    end = text.find("\n```", start)
    body = json.dumps({"harness_run": run}, indent=2, ensure_ascii=False)
    path.write_text(text[: start + len("```json\n")] + body + text[end:], encoding="utf-8")


def packet_block(packet: str) -> str:
    start = packet.find("```text\n") + len("```text\n")
    end = packet.find("\n```", start)
    return packet[start:end]


class LeasePacketCli(unittest.TestCase):
    """Drive the real CLI through acquire-run-lock, accept-wave, and lease-worker."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.gitroot = self.root / "git"
        self.gitroot.mkdir()
        self.base = mf.init_repo(self.gitroot, "file.txt")
        mf.git(self.gitroot, "checkout", "-qb", "integration")
        (self.gitroot / "file.txt").write_text("work\n", encoding="utf-8")
        mf.git(self.gitroot, "add", ".")
        mf.git(self.gitroot, "commit", "-qm", "work")
        self.head = mf.git(self.gitroot, "rev-parse", "HEAD")
        self.wt1 = (self.root / "wt-m1").as_posix()
        self.packet_path = self.root / "M1-worker-goal.md"
        self.host_path = self.root / "host.json"

        self.plan = mf.valid_plan()
        mf.materialize_plan_sources(self.gitroot, self.plan)
        context_dir = self.gitroot / "docs" / "context"
        context_dir.mkdir(parents=True)
        self.context_paths = ["docs/context/AGENTS.md", "docs/context/SKILLS.md"]
        for relative in self.context_paths:
            (self.gitroot / relative).write_text(
                f"ordered context: {relative}\n", encoding="utf-8"
            )
        mf.git(self.gitroot, "add", "docs/product", "docs/context")
        mf.git(self.gitroot, "commit", "-qm", "freeze contracts")
        self.head = mf.git(self.gitroot, "rev-parse", "HEAD")

        run = mf.valid_run(self.plan)
        mf.authorize_execution(run, ["M1", "M2"])
        mf.authorize_action(
            run, "spawn_subagents", ["M1", "M2"], ["*", "worker:W-M1-A", "worker:RW-1"]
        )
        mf.authorize_action(
            run, "create_local_worktrees", ["M1", "M2"], ["*", f"worktree:{self.wt1}"]
        )
        mf.authorize_action(
            run,
            "create_local_branches",
            ["M1", "M2"],
            ["*", "branch:refs/heads/wt/m1"],
        )
        mf.authorize_action(
            run,
            "create_local_commits",
            ["M1", "M2"],
            ["*", "branch:refs/heads/wt/m1"],
        )
        run["integration"]["branch"] = "integration"
        run["integration"]["integration_head_sha"] = None
        run["landing"]["continuity"]["branch_ref"] = "refs/heads/integration"
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter["available_drivers"] = ["subagents", "sequential_parent"]
        adapter["detection_source"] = "observed"
        adapter["capability_probe"] = mf.native_capability_probe(subagents=True)
        run["runtime_capabilities"]["worker_runtime"] = "subagent"
        run["runtime_capabilities"]["max_parallel_workers"] = 2

        self.plan_path = self.root / "PLAN.md"
        self.run_path = self.root / "RUN.md"
        self.plan_path.write_text(
            mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", self.plan),
            encoding="utf-8",
        )
        self.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )
        self.assertEqual(0, self.cli("--session-id", SESSION, "acquire-run-lock").returncode)
        self.assertEqual(0, self.cli("record-observation").returncode)
        self._seed_sandbox_observation()
        result = self.cli(
            "accept-wave", "--wave-id", "W-1", "--mission-id", "M1",
            "--batch-base-sha", self.head,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        mf.git(self.gitroot, "worktree", "add", "-b", "wt/m1", self.wt1, self.head)
        self.assertEqual(0, self.cli("record-observation").returncode)
        self._seed_sandbox_observation()

    def tearDown(self) -> None:
        self._temp.cleanup()

    def cli(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "harness_transition.py"),
                "--plan", str(self.plan_path),
                "--run", str(self.run_path),
                "--repo-root", str(self.gitroot),
                "--session-id", SESSION,
                *extra,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(self.gitroot),
        )

    def _seed_sandbox_observation(self) -> None:
        live = load_run_block(self.run_path)
        live["observed"]["sandbox"] = mf.sandbox_observation(self.plan)
        live["observed"]["sandbox"]["captured_at"] = live["observed"].get("captured_at")
        save_run_block(self.run_path, live)

    def write_host_file(self, values: dict[str, str]) -> None:
        self.host_path.write_text(
            json.dumps(values, indent=2) + "\n", encoding="utf-8"
        )

    def lease(self, *extra: str) -> subprocess.CompletedProcess:
        return self.cli(
            "lease-worker",
            "--mission-id", "M1", "--node-id", "N-M1",
            "--worker-id", "W-M1-A", "--lease-id", "L-M1",
            "--attempt-id", "A-M1", "--branch-ref", "refs/heads/wt/m1",
            "--worktree-path", self.wt1,
            "--provider", "codex", "--driver", "subagents",
            *extra,
        )

    def packet_arguments(self) -> list[str]:
        arguments = [
            "--packet-out", str(self.packet_path),
            "--max-message-bytes", "20000",
        ]
        for relative in self.context_paths:
            arguments.extend(["--context-path", relative])
        arguments.extend(["--host-file", str(self.host_path)])
        return arguments

    def test_packet_renders_the_leased_run_and_writes_exclusively(self) -> None:
        self.write_host_file(dict(HOST_VALUES))
        before = self.run_path.read_bytes()
        result = self.lease(*self.packet_arguments())
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotEqual(before, self.run_path.read_bytes())
        worker = next(
            item
            for item in load_run_block(self.run_path)["workers"]
            if item["worker_id"] == "W-M1-A"
        )
        self.assertEqual("L-M1", worker["lease_id"])
        packet = self.packet_path.read_text(encoding="utf-8")
        self.assertIn("# Worker Goal: M1 — Deliver M1", packet)
        self.assertIn("Complete M1 (Deliver M1) only.", packet)
        self.assertIn(f"- PLAN: {self.plan_path}; ID PLAN-TEST; revision 1; digest", packet)
        self.assertIn(f"- RUN snapshot: {self.run_path}", packet)
        self.assertIn("- Mission/tasks: M1: M1/T01, M1/T02", packet)
        self.assertIn("- Lease: L-M1", packet)
        self.assertIn(f"- Batch base: {self.head}", packet)
        self.assertIn("- required_skills: none", packet)
        self.assertIn("- Provider/driver: codex / subagents", packet)
        self.assertIn("- Worker/workspace/completion: subagent / parent_managed_worktree / agent_result", packet)
        self.assertIn(f"- Worktree and branch/ref: {self.wt1} / refs/heads/wt/m1", packet)
        self.assertIn("- Host-specific context: docs/context/AGENTS.md; docs/context/SKILLS.md", packet)
        self.assertIn("- Worker contract: references/runtime-adapters.md", packet)
        self.assertIn("- Parent launch identity: session parent-1; wave W-1 accepted attempt A-M1", packet)
        self.assertIn("- Handoff: this packet; max_message_bytes 20000", packet)
        self.assertIn("- Route caps: time 900 / turns 40 / max_message_bytes 14000", packet)
        for relative in self.context_paths:
            digest = hashlib.sha256((self.gitroot / relative).read_bytes()).hexdigest()
            self.assertIn(f"{relative} sha256:{digest}", packet)
        self.assertIn("- Result contract: ", packet)
        self.assertIn("- Permissions: mode default; worktree writes only; approval never", packet)
        self.assertIn(
            "- Resource claims: port:3000 (exclusive); db:test (shared_read); "
            "migration:primary (serialized); fixture:users (serialized)",
            packet,
        )
        self.assertIn("- Write: src/a/**", packet)
        self.assertIn(
            "- Deny: docs/goal/PLAN.md, docs/goal/RUN.md, PLAN.md, RUN.md, "
            "frozen contracts, and unrelated files",
            packet,
        )
        self.assertIn(
            "- Objective and stop conditions: Deliver M1 — stop when: Stop on contract conflict",
            packet,
        )
        self.assertIn("- Verifiers: worker-m1; verify-m1-1; verify-m1-2; platform none", packet)
        self.assertIn("- Security requirements: PRD-003/TEST-003", packet)
        self.assertIn(
            "- Commit authorization: true (user requested lifecycle action)", packet
        )
        self.assertNotIn("Visual inputs", packet)
        self.assertNotIn("Repair context", packet)
        self.assertNotIn("<", packet_block(packet))

    def test_existing_packet_path_refuses_before_the_run_write(self) -> None:
        self.write_host_file(dict(HOST_VALUES))
        self.packet_path.write_text("earlier packet\n", encoding="utf-8")
        before = self.run_path.read_bytes()
        result = self.lease(*self.packet_arguments())
        self.assertEqual(2, result.returncode)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(before, self.run_path.read_bytes())
        self.assertEqual("earlier packet\n", self.packet_path.read_text(encoding="utf-8"))

    def test_unfilled_placeholders_refuse_before_the_run_write(self) -> None:
        before = self.run_path.read_bytes()
        arguments = ["--packet-out", str(self.packet_path), "--max-message-bytes", "20000"]
        for relative in self.context_paths:
            arguments.extend(["--context-path", relative])
        result = self.lease(*arguments)
        self.assertEqual(2, result.returncode)
        self.assertIn("unfilled placeholders", result.stderr)
        self.assertIn("Permissions", result.stderr)
        self.assertEqual(before, self.run_path.read_bytes())
        self.assertFalse(self.packet_path.exists())

    def test_oversized_packet_refuses_and_writes_nothing(self) -> None:
        self.write_host_file(dict(HOST_VALUES))
        before = self.run_path.read_bytes()
        result = self.lease(
            "--packet-out", str(self.packet_path),
            "--max-message-bytes", "10",
            "--host-file", str(self.host_path),
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("exceeds the message budget", result.stderr)
        self.assertEqual(before, self.run_path.read_bytes())
        self.assertFalse(self.packet_path.exists())

    def test_packet_flags_require_packet_out_and_budget(self) -> None:
        before = self.run_path.read_bytes()
        result = self.lease("--context-path", self.context_paths[0])
        self.assertEqual(2, result.returncode)
        self.assertIn("--context-path and --host-file require --packet-out", result.stderr)
        result = self.lease("--host-file", str(self.host_path))
        self.assertEqual(2, result.returncode)
        self.assertIn("--context-path and --host-file require --packet-out", result.stderr)
        result = self.lease("--packet-out", str(self.packet_path))
        self.assertEqual(2, result.returncode)
        self.assertIn("--packet-out requires --max-message-bytes", result.stderr)
        result = self.lease(
            "--packet-out", str(self.packet_path), "--max-message-bytes", "0"
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("invalid packet message budget", result.stderr)
        self.assertEqual(before, self.run_path.read_bytes())
        self.assertFalse(self.packet_path.exists())

    def test_host_file_repairs_fill_the_repair_context(self) -> None:
        values = dict(HOST_VALUES)
        values.update(
            {
                "Root-cause families": "state-desync; lease bookkeeping",
                "Known variants and acceptance matrix": "variant A denied; variant B denied",
                "Rejected narrow approach": "do not repeat the stale-head retry",
                "Review lineage": "M1 backend_code; 1 of 2 attempts used",
            }
        )
        self.write_host_file(values)
        result = self.lease(*self.packet_arguments())
        self.assertEqual(0, result.returncode, result.stderr)
        packet = self.packet_path.read_text(encoding="utf-8")
        self.assertIn(
            "Repair context (omit for an initial implementation)", packet
        )
        self.assertIn("- Root-cause families: state-desync; lease bookkeeping", packet)
        self.assertIn(
            "- Known variants and acceptance matrix: variant A denied; variant B denied",
            packet,
        )
        self.assertIn(
            "- Rejected narrow approach: do not repeat the stale-head retry", packet
        )
        self.assertIn("- Review lineage: M1 backend_code; 1 of 2 attempts used", packet)

    def test_unknown_host_file_key_is_refused(self) -> None:
        self.write_host_file({**HOST_VALUES, "Lease": "hand-supplied lease"})
        before = self.run_path.read_bytes()
        result = self.lease(*self.packet_arguments())
        self.assertEqual(2, result.returncode)
        self.assertIn("unknown placeholder names Lease", result.stderr)
        self.assertEqual(before, self.run_path.read_bytes())
        self.assertFalse(self.packet_path.exists())


if __name__ == "__main__":
    unittest.main()
