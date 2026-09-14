"""Focused archive-first push protocol tests."""

from __future__ import annotations

import json
import hashlib
import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
TESTS = SCRIPTS / "tests"
PDB_TESTS = SCRIPTS.parent.parent / "product-definition-builder" / "scripts" / "tests"
import sys

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))
if str(PDB_TESTS) not in sys.path:
    sys.path.insert(0, str(PDB_TESTS))

import push_archived_candidate as subject  # noqa: E402
import archive_run  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
from harness_schema import archive_first_required, parse_harness_version  # noqa: E402
from push_integration_branch import push_authorized_head  # noqa: E402
from harness_core import ManifestError  # noqa: E402
from test_product_package_checker import release_architecture, valid_prd, valid_stack  # noqa: E402

while str(PDB_TESTS) in sys.path:
    sys.path.remove(str(PDB_TESTS))


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def manifest(heading: str, wrapper: str, value: dict) -> str:
    return f"# Fixture\n\n{heading}\n\n```json\n{json.dumps({wrapper: value}, indent=2)}\n```\n"


class ArchiveFirstPushTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temps: list[tempfile.TemporaryDirectory[str]] = []
        self._anchors: list[Path] = []

    def tearDown(self) -> None:
        for anchor in self._anchors:
            if anchor.exists():
                anchor.unlink()
        for item in self._temps:
            item.cleanup()

    def _fixture(self) -> dict[str, Path | str]:
        """Create one real archive A with a bare remote and closed receipt."""
        from manifest_fixtures import git as fixture_git, manifest_markdown, mark_complete, valid_plan, valid_run
        holder = tempfile.TemporaryDirectory()
        self._temps.append(holder)
        root = Path(holder.name)
        remote = root.parent / f"archive-remote-{root.name}.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        root.mkdir(exist_ok=True)
        product = root / "docs/product"
        product.mkdir(parents=True)
        files = {
            "PRD.md": valid_prd(),
            "architecture.md": release_architecture(),
            "stack-decisions.md": valid_stack(),
        }
        for name, text in files.items():
            (product / name).write_text(text, encoding="utf-8")
        plan = valid_plan()
        plan["security_review"] = {"status": "not_applicable", "skill_slot": "code_security_verification", "reason": "documentation-only fixture"}
        plan["sources"] = []
        for index, (kind, name) in enumerate((("prd", "PRD.md"), ("architecture", "architecture.md"), ("stack decisions", "stack-decisions.md")), start=1):
            path = product / name
            plan["sources"].append({"id": f"SRC-{index:03d}", "kind": kind, "location": f"docs/product/{name}", "owner": "fixture", "status": "frozen", "content_sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(), "source_revision": None, "staged_revision": None, "notes": "fixture"})
        for trace in plan["traces"]:
            trace["source_ids"] = ["SRC-001"]
        for mission in plan["missions"]:
            mission["write_scope"] = ["docs/README.md"]
            for task in mission["tasks"]:
                task["write_scope"] = ["docs/README.md"]
        from harness_manifest import plan_digest as fixture_plan_digest
        run = valid_run(plan)
        run["plan"]["digest_sha256"] = fixture_plan_digest(plan)
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"] = {
            "host_version": "test-current", "minimum_host_version": None,
            "harness_version": "0.38.0", "required_harness_version": "0.38.0",
            "session_id": "test-session", "loaded_contract_digest": "a" * 64,
            "installed_contract_digest": "a" * 64, "status": "current", "evidence": "fixture",
        }
        docs = root / "docs"
        (docs / "goal").mkdir(parents=True)
        (docs / "DOCUMENTS.md").write_text("# Documents\n", encoding="utf-8")
        fixture_git(root, "init", "-q", "-b", "main")
        fixture_git(root, "config", "user.email", "test@example.com")
        fixture_git(root, "config", "user.name", "Harness Test")
        fixture_git(root, "add", "docs/product", "docs/DOCUMENTS.md")
        fixture_git(root, "commit", "-qm", "freeze sources")
        expected_main = fixture_git(root, "rev-parse", "HEAD")
        fixture_git(root, "branch", "codex/test", expected_main)
        fixture_git(root, "checkout", "-q", "codex/test")
        run["integration"].update({"branch": "codex/test", "batch_base_sha": expected_main, "integration_head_sha": expected_main})
        run["observed"]["git"].update({"parent_worktree_path": root.as_posix(), "parent_branch": "main", "parent_head_sha": expected_main, "parent_dirty": False})
        mark_complete(plan, run)
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"] = {
            "host_version": "test-current", "minimum_host_version": None,
            "harness_version": "0.38.0", "required_harness_version": "0.38.0",
            "session_id": "test-session", "loaded_contract_digest": "a" * 64,
            "installed_contract_digest": "a" * 64, "status": "current", "evidence": "fixture",
        }
        run["integration"].update({"branch": "codex/test", "batch_base_sha": expected_main, "integration_head_sha": expected_main})
        run["landing"]["continuity"].update({"branch_ref": "refs/heads/codex/test", "head_sha": expected_main})
        (docs / "goal" / "PLAN.md").write_text(manifest_markdown("## Harness Plan Manifest", "harness_plan", plan), encoding="utf-8")
        (docs / "goal" / "RUN.md").write_text(manifest_markdown("## Harness Run State", "harness_run", run), encoding="utf-8")
        anchor = root.parent / f"archive-anchor-{root.name}.json"
        self._anchors.append(anchor)
        result = subprocess.run([
            sys.executable, str(SCRIPTS / "archive_run.py"), "--repo-root", str(root), "--apply",
            "--stamp", "20260913-000000", "--expected-main", expected_main,
            "--main-ref", "refs/heads/main", "--anchor-out", str(anchor),
        ], capture_output=True, text=True)
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)
        archive_run_path = next((root / "docs/goal/archived").iterdir())
        fixture_git(root, "add", ".")
        fixture_git(root, "commit", "-qm", "archive A")
        candidate_a = fixture_git(root, "rev-parse", "HEAD")
        fixture_git(root, "remote", "add", "origin", str(remote))
        return {"root": root, "remote": remote, "request": root.parent / f"request-{root.name}.json", "attempt": root.parent / f"attempt-{root.name}.json", "receipt": root.parent / f"receipt-{root.name}.json", "archive": archive_run_path, "anchor": anchor, "candidate_c": expected_main, "candidate_a": candidate_a}

    def _prepare(self, fixture: dict[str, Path | str]) -> dict[str, object]:
        return subject.prepare(
            Path(fixture["root"]),
            archive_path=Path(fixture["archive"]),
            remote="origin",
            request_path=Path(fixture["request"]),
            attempt_path=Path(fixture["attempt"]),
            receipt_path=Path(fixture["receipt"]),
            archive_anchor=Path(fixture["anchor"]),
        )

    def test_real_bare_remote_archive_push_happy_path(self) -> None:
        fixture = self._fixture()
        request_value = self._prepare(fixture)
        self.assertEqual(fixture["candidate_a"], request_value["candidate_a"])
        handoff = subject.begin_handoff(Path(fixture["root"]), request_path=Path(fixture["request"]))
        self.assertEqual(subject.PENDING_TRUSTED_HOST_STATUS, handoff["status"])
        self.assertEqual(
            [
                "git", "--no-replace-objects", "push", "--", "origin",
                f"{fixture['candidate_a']}:refs/heads/codex/test",
            ],
            handoff["push_argv"],
        )
        git(Path(fixture["root"]), "--no-replace-objects", "push", "--", "origin", f"{fixture['candidate_a']}:refs/heads/codex/test")
        subject.recover_uncertain(Path(fixture["root"]), request_path=Path(fixture["request"]))
        self.assertEqual(
            fixture["candidate_a"],
            git(Path(fixture["root"]), "ls-remote", str(fixture["remote"]), "refs/heads/codex/test").split()[0],
        )
        subject.verify_receipt(Path(fixture["root"]), request_path=Path(fixture["request"]))

    def test_real_archive_run_dirty_plan_and_run_produce_receipt_accepted_by_verifier(self) -> None:
        fixture = self._fixture()
        verified = subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=str(fixture["candidate_a"]))
        self.assertEqual(fixture["candidate_c"], verified["candidate_c"])
        self.assertEqual(fixture["candidate_a"], verified["candidate_a"])

    def test_caller_supplied_prose_or_ref_is_rejected_before_request_creation(self) -> None:
        fixture = self._fixture()
        with self.assertRaisesRegex(ManifestError, "caller-supplied authorization"):
            subject.prepare(
                Path(fixture["root"]),
                archive_path=Path(fixture["archive"]),
                remote="origin",
                authorization_source="approve and push this exact candidate",
                authorization_ref="ticket:ATTACKER",
                request_path=Path(fixture["request"]),
                attempt_path=Path(fixture["attempt"]),
                receipt_path=Path(fixture["receipt"]),
                archive_anchor=Path(fixture["anchor"]),
            )

    def test_begin_handoff_never_invokes_local_git_push(self) -> None:
        fixture = self._fixture()
        self._prepare(fixture)
        original_git = subject._git
        calls: list[tuple[str, ...]] = []

        def record(root: Path, *args: str, **kwargs: object):
            calls.append(args)
            self.assertNotEqual("push", args[0] if args else None)
            return original_git(root, *args, **kwargs)

        with patch.object(subject, "_git", side_effect=record):
            handoff = subject.begin_handoff(Path(fixture["root"]), request_path=Path(fixture["request"]))
        self.assertEqual(subject.PENDING_TRUSTED_HOST_STATUS, handoff["status"])
        self.assertFalse(any(args and args[0] == "push" for args in calls))

    def test_receipt_move_type_tamper_is_rejected_even_with_recomputed_digest(self) -> None:
        fixture = self._fixture()
        receipt_path = Path(fixture["archive"]) / "ARCHIVE_RECEIPT.json"
        value = json.loads(receipt_path.read_text(encoding="utf-8"))
        value["moves"][0]["type"] = "directory"
        unsigned = {key: item for key, item in value.items() if key != "receipt_sha256"}
        value["receipt_sha256"] = subject._digest(unsigned)
        receipt_path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        git(Path(fixture["root"]), "add", ".")
        git(Path(fixture["root"]), "commit", "--amend", "-qm", "tampered archive A")
        candidate_a = git(Path(fixture["root"]), "rev-parse", "HEAD")
        with self.assertRaisesRegex(ManifestError, "type must be file|invalid fields"):
            subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=candidate_a)

    def test_recomputed_request_semantic_edit_and_copied_request_are_rejected(self) -> None:
        fixture = self._fixture()
        request = self._prepare(fixture)
        request["plan_id"] = "PLAN-TAMPERED"
        request["request_sha256"] = subject._digest({key: value for key, value in request.items() if key != "request_sha256"})
        Path(fixture["request"]).write_text(json.dumps(request, indent=2), encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "authority mismatch"):
            subject.execute(Path(fixture["root"]), request_path=Path(fixture["request"]))
        copied = Path(fixture["root"]).parent / "copied-request.json"
        shutil.copy2(fixture["request"], copied)
        with self.assertRaisesRegex(ManifestError, "copied or moved"):
            subject.execute(Path(fixture["root"]), request_path=copied)

    def test_full_branch_ref_and_protected_case_variants_are_handled(self) -> None:
        fixture = self._fixture()
        receipt_path = Path(fixture["archive"]) / "ARCHIVE_RECEIPT.json"
        value = json.loads(receipt_path.read_text(encoding="utf-8"))
        value["branch"] = "refs/heads/codex/test"
        value["branch_ref"] = "refs/heads/codex/test"
        value["receipt_sha256"] = subject._digest({key: item for key, item in value.items() if key != "receipt_sha256"})
        receipt_path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        anchor_path = Path(fixture["anchor"])
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        anchor["branch"] = "refs/heads/codex/test"
        anchor["receipt_sha256"] = value["receipt_sha256"]
        anchor["anchor_sha256"] = archive_run._anchor_digest(anchor)
        anchor_path.write_text(json.dumps(anchor, indent=2), encoding="utf-8")
        git(Path(fixture["root"]), "add", ".")
        git(Path(fixture["root"]), "commit", "--amend", "-qm", "full branch ref")
        candidate_a = git(Path(fixture["root"]), "rev-parse", "HEAD")
        self.assertEqual("codex/test", subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=candidate_a)["run_branch"])

    def test_recovery_requires_attempt_and_never_calls_push(self) -> None:
        fixture = self._fixture()
        self._prepare(fixture)
        with self.assertRaisesRegex(ManifestError, "immutable artifact"):
            subject.recover_uncertain(Path(fixture["root"]), request_path=Path(fixture["request"]))
        # A completed trusted-host publication leaves an attempt but no local
        # receipt until recovery closes it, so recovery must never invoke push.
        subject.begin_handoff(Path(fixture["root"]), request_path=Path(fixture["request"]))
        git(Path(fixture["root"]), "--no-replace-objects", "push", "--", "origin", f"{fixture['candidate_a']}:refs/heads/codex/test")
        original_git = subject._git

        def reject_push(root: Path, *args: str, **kwargs: object):
            if args and args[0] == "push":
                raise AssertionError("recovery must never invoke git push")
            return original_git(root, *args, **kwargs)

        with patch.object(subject, "_git", side_effect=reject_push):
            recovered = subject.recover_uncertain(Path(fixture["root"]), request_path=Path(fixture["request"]))
        self.assertEqual("PASS", recovered["status"] if "status" in recovered else "PASS")

    def test_endpoint_retarget_and_execute_replay_are_rejected(self) -> None:
        fixture = self._fixture()
        self._prepare(fixture)
        subject.begin_handoff(Path(fixture["root"]), request_path=Path(fixture["request"]))
        with self.assertRaisesRegex(ManifestError, "attempt already exists|replay"):
            subject.begin_handoff(Path(fixture["root"]), request_path=Path(fixture["request"]))
        alternate = Path(fixture["root"]).parent / "alternate.git"
        subprocess.run(["git", "init", "--bare", "-q", str(alternate)], check=True)
        git(Path(fixture["root"]), "--no-replace-objects", "push", "--", "origin", f"{fixture['candidate_a']}:refs/heads/codex/test")
        subject.recover_uncertain(Path(fixture["root"]), request_path=Path(fixture["request"]))
        git(Path(fixture["root"]), "remote", "set-url", "--push", "origin", str(alternate))
        with self.assertRaisesRegex(ManifestError, "endpoint|configured push"):
            subject.verify_receipt(Path(fixture["root"]), request_path=Path(fixture["request"]))

    def test_post_attempt_dirty_drift_is_rechecked_before_push(self) -> None:
        fixture = self._fixture()
        self._prepare(fixture)
        original_recheck = subject._pre_push_recheck

        def drift(root: Path, request: dict[str, object], authority: dict[str, object]):
            (root / "drift.txt").write_text("drift\n", encoding="utf-8")
            return original_recheck(root, request, authority)

        with patch.object(subject, "_pre_push_recheck", side_effect=drift):
            with self.assertRaisesRegex(ManifestError, "dirty|clean"):
                subject.execute(Path(fixture["root"]), request_path=Path(fixture["request"]))
        self.assertIsNone(subject._remote_state(Path(fixture["root"]), "origin", "refs/heads/codex/test"))

    def test_archive_anchor_inside_checkout_and_existing_path_are_rejected(self) -> None:
        fixture = self._fixture()
        inside = Path(fixture["root"]) / "anchor.json"
        with self.assertRaisesRegex(ManifestError, "anchor|external"):
            subject.prepare(
                Path(fixture["root"]), archive_path=Path(fixture["archive"]), remote="origin",
                request_path=Path(fixture["request"]), attempt_path=Path(fixture["attempt"]),
                receipt_path=Path(fixture["receipt"]), archive_anchor=inside,
            )
        with self.assertRaises(FileExistsError):
            archive_run._write_closed_anchor(Path(fixture["anchor"]), {}, Path(fixture["root"]))

    def test_external_anchor_tamper_and_optional_move_rewrite_are_rejected(self) -> None:
        fixture = self._fixture()
        anchor_path = Path(fixture["anchor"])
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        anchor["anchor_nonce"] = "0" * 64
        anchor["anchor_sha256"] = archive_run._anchor_digest(anchor)
        anchor_path.write_text(json.dumps(anchor, indent=2), encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "anchor"):
            subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=str(fixture["candidate_a"]))

        fixture = self._fixture()
        receipt_path = Path(fixture["archive"]) / "ARCHIVE_RECEIPT.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["moves"].append({"source": "docs/tasks.md", "destination": f"{receipt['archive_path']}/tasks.md", "type": "file", "sha256": "0" * 64})
        receipt["receipt_sha256"] = subject._digest({key: value for key, value in receipt.items() if key != "receipt_sha256"})
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        anchor_path = Path(fixture["anchor"])
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        anchor["receipt_sha256"] = receipt["receipt_sha256"]
        anchor["source_inventory"] = receipt["moves"]
        anchor["moves_sha256"] = subject._digest(receipt["moves"])
        anchor["anchor_sha256"] = archive_run._anchor_digest(anchor)
        anchor_path.write_text(json.dumps(anchor, indent=2), encoding="utf-8")
        git(Path(fixture["root"]), "add", ".")
        git(Path(fixture["root"]), "commit", "--amend", "-qm", "optional move tamper")
        candidate_a = git(Path(fixture["root"]), "rev-parse", "HEAD")
        with self.assertRaisesRegex(ManifestError, "extra or missing|receipt move"):
            subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=candidate_a)

    def test_autocrlf_png_filter_preserves_binary_archive_bytes(self) -> None:
        fixture = self._fixture()
        png = Path(fixture["root"]) / "binary.png"
        payload = b"\x89PNG\r\n\x1a\n\x00\xff\r\n"
        png.write_bytes(payload)
        filtered = archive_run._git_filtered_bytes(Path(fixture["root"]), Path(fixture["root"]) / "docs/goal/archived/binary.png", source=png)
        self.assertEqual(payload, filtered)

    def test_self_consistent_but_invalid_archived_plan_pair_is_rejected(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        archive = Path(fixture["archive"])
        plan_path = archive / "PLAN.md"
        lines = plan_path.read_text(encoding="utf-8").splitlines()
        start = next(index for index, line in enumerate(lines) if line.strip() == "```json") + 1
        end = next(index for index in range(start, len(lines)) if lines[index].strip() == "```")
        plan_doc = json.loads("\n".join(lines[start:end]))
        plan_doc["harness_plan"]["objective"] = None
        lines[start:end] = json.dumps(plan_doc, indent=2).splitlines()
        plan_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        receipt_path = archive / "ARCHIVE_RECEIPT.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["moves"][0]["sha256"] = hashlib.sha256(archive_run._git_filtered_bytes(root, plan_path, source=plan_path)).hexdigest()
        receipt["plan_digest_sha256"] = subject.plan_digest(plan_doc["harness_plan"])
        receipt["receipt_sha256"] = subject._digest({key: value for key, value in receipt.items() if key != "receipt_sha256"})
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        anchor_path = Path(fixture["anchor"])
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        anchor["plan_digest_sha256"] = receipt["plan_digest_sha256"]
        anchor["receipt_sha256"] = receipt["receipt_sha256"]
        anchor["source_inventory"] = receipt["moves"]
        anchor["moves_sha256"] = subject._digest(receipt["moves"])
        anchor["anchor_sha256"] = archive_run._anchor_digest(anchor)
        anchor_path.write_text(json.dumps(anchor, indent=2), encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "--amend", "-qm", "invalid but self-consistent pair")
        candidate_a = git(root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ManifestError, "validation failed|objective"):
            subject.verify_archive_candidate(root, archive_path=archive, candidate_a=candidate_a)

    def test_receipt_null_main_authority_and_stamp_path_mismatch_are_rejected(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        archive = Path(fixture["archive"])
        receipt_path = archive / "ARCHIVE_RECEIPT.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["expected_main"] = None
        receipt["main_ref"] = None
        receipt["receipt_sha256"] = subject._digest({key: value for key, value in receipt.items() if key != "receipt_sha256"})
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        anchor_path = Path(fixture["anchor"])
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        anchor["expected_main"] = None
        anchor["main_ref"] = None
        anchor["receipt_sha256"] = receipt["receipt_sha256"]
        anchor["anchor_sha256"] = archive_run._anchor_digest(anchor)
        anchor_path.write_text(json.dumps(anchor, indent=2), encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "--amend", "-qm", "null archive authority")
        candidate_a = git(root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ManifestError, "expected_main|main_ref"):
            subject.verify_archive_candidate(root, archive_path=archive, candidate_a=candidate_a)
        fixture = self._fixture()
        root = Path(fixture["root"])
        archive = Path(fixture["archive"])
        receipt_path = archive / "ARCHIVE_RECEIPT.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["stamp"] = "20260101-000000"
        receipt["receipt_sha256"] = subject._digest({key: value for key, value in receipt.items() if key != "receipt_sha256"})
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        anchor_path = Path(fixture["anchor"])
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        anchor["stamp"] = receipt["stamp"]
        anchor["receipt_sha256"] = receipt["receipt_sha256"]
        anchor["anchor_sha256"] = archive_run._anchor_digest(anchor)
        anchor_path.write_text(json.dumps(anchor, indent=2), encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "--amend", "-qm", "stamp path mismatch")
        candidate_a = git(root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ManifestError, "stamp"):
            subject.verify_archive_candidate(root, archive_path=archive, candidate_a=candidate_a)

    def test_archive_first_threshold_is_strict_and_missing_pins_are_not_current(self) -> None:
        self.assertEqual((0, 38, 0), parse_harness_version("0.38.0"))
        self.assertEqual((0, 38, 0), parse_harness_version("0.38.0-rc.1"))
        self.assertEqual((0, 38, 0), parse_harness_version("0.38.0+build.7"))
        self.assertIsNone(parse_harness_version("0.38"))
        self.assertTrue(
            archive_first_required(
                {"runtime_capabilities": {"runtime_adapter": {"version_gate": {"required_harness_version": "0.38.0"}}}}
            )
        )
        self.assertTrue(
            archive_first_required(
                {"runtime_capabilities": {"runtime_adapter": {"version_gate": {"required_harness_version": "0.38.0-rc.1"}}}}
            )
        )
        self.assertFalse(archive_first_required({"runtime_capabilities": {}}))

    def test_legacy_push_rejects_archive_first_pin_before_git_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            git(root, "init", "-q", "-b", "codex/test")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Harness Test")
            (root / "file.txt").write_text("x\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-qm", "base")
            run = {
                "schema_version": 11,
                "runtime_capabilities": {"runtime_adapter": {"version_gate": {"required_harness_version": "0.38.0"}}},
                "authorizations": {"push": {"authorized_head_sha": git(root, "rev-parse", "HEAD")}},
            }
            with self.assertRaisesRegex(ManifestError, "archive-first"):
                push_authorized_head({}, run, root, "origin")

    def test_archive_verifier_rejects_merge_archive_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            git(root, "init", "-q", "-b", "codex/test")
            git(root, "config", "user.email", "test@example.com")
            git(root, "config", "user.name", "Harness Test")
            (root / "docs/goal").mkdir(parents=True)
            (root / "docs/product").mkdir(parents=True)
            plan = {"schema_version": 6, "plan_id": "PLAN-1", "revision": 1, "sources": [], "missions": []}
            run = {"schema_version": 11, "run_id": "RUN-1", "status": "complete", "plan": {"id": "PLAN-1", "revision": 1, "digest_sha256": "0" * 64}, "integration": {"integration_head_sha": ""}}
            (root / "docs/goal/PLAN.md").write_text(manifest("## Harness Plan Manifest", "harness_plan", plan), encoding="utf-8")
            (root / "docs/goal/RUN.md").write_text(manifest("## Harness Run State", "harness_run", run), encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-qm", "candidate C")
            (root / "docs/goal/archived/20260913-run-1").mkdir(parents=True)
            for name in ("PLAN.md", "RUN.md"):
                (root / "docs/goal/archived/20260913-run-1" / name).write_bytes((root / "docs/goal" / name).read_bytes())
            git(root, "add", ".")
            git(root, "commit", "-qm", "archive A")
            a = git(root, "rev-parse", "HEAD")
            with self.assertRaisesRegex(ManifestError, "ARCHIVE_RECEIPT|archived RUN|direct non-merge"):
                subject.verify_archive_candidate(root, archive_path=root / "docs/goal/archived/20260913-run-1", candidate_a=a)

    def test_push_verifier_rejects_git_replace_refs_before_authority_reads(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        git(root, "update-ref", f"refs/replace/{fixture['candidate_a']}", str(fixture["candidate_c"]))
        with self.assertRaisesRegex(ManifestError, "replacement refs"):
            subject.verify_archive_candidate(root, archive_path=Path(fixture["archive"]), candidate_a=str(fixture["candidate_a"]))

    def test_published_a_preview_failure_uses_replacement_c2_a2_lineage(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        candidate_a = str(fixture["candidate_a"])
        git(root, "--no-replace-objects", "push", "--", "origin", f"{candidate_a}:refs/heads/codex/test")

        def read_manifest(path: Path, wrapper: str) -> dict[str, object]:
            lines = path.read_text(encoding="utf-8").splitlines()
            start = next(index for index, line in enumerate(lines) if line.strip() == "```json") + 1
            end = next(index for index in range(start, len(lines)) if lines[index].strip() == "```")
            return json.loads("\n".join(lines[start:end]))[wrapper]

        from manifest_fixtures import manifest_markdown

        archive = Path(fixture["archive"])
        plan = read_manifest(archive / "PLAN.md", "harness_plan")
        plan = copy.deepcopy(plan)
        plan["plan_id"] = "PLAN-REPLACEMENT-001"
        plan["revision"] = 1
        prior_receipt = archive / "ARCHIVE_RECEIPT.json"
        plan["sources"].append(
            {
                "id": "SRC-PRIOR-ARCHIVE-A",
                "kind": "prior archive candidate",
                "location": prior_receipt.relative_to(root).as_posix(),
                "owner": "fixture",
                "status": "frozen",
                "content_sha256": hashlib.sha256(prior_receipt.read_bytes()).hexdigest(),
                "source_revision": candidate_a,
                "staged_revision": None,
                "notes": "failed preview correction lineage",
            }
        )
        goal = root / "docs" / "goal"
        (root / "repair.txt").write_text("preview repair\n", encoding="utf-8")
        git(root, "add", "repair.txt")
        git(root, "commit", "-qm", "replacement repair C2")
        repair_head = git(root, "rev-parse", "HEAD")
        run = mf.valid_run(plan)
        run["run_id"] = "RUN-REPLACEMENT-001"
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"].update(
            {"harness_version": "0.38.0", "required_harness_version": "0.38.0"}
        )
        run["integration"].update(
            {
                "branch": "codex/test",
                "batch_base_sha": candidate_a,
                "integration_head_sha": repair_head,
            }
        )
        mf.mark_complete(plan, run)
        run["observed"]["git"].update(
            {
                "parent_head_sha": repair_head,
                "parent_branch": "codex/test",
                "parent_dirty": False,
            }
        )
        (goal / "PLAN.md").write_text(manifest_markdown("## Harness Plan Manifest", "harness_plan", plan), encoding="utf-8")
        (goal / "RUN.md").write_text(manifest_markdown("## Harness Run State", "harness_run", run), encoding="utf-8")
        c2 = repair_head
        self.assertEqual(c2, repair_head)
        anchor2 = root.parent / f"archive-anchor-replacement-{root.name}.json"
        self._anchors.append(anchor2)
        archive_result = subprocess.run([
            sys.executable, str(SCRIPTS / "archive_run.py"), "--repo-root", str(root), "--apply",
            "--stamp", "20260913-000001", "--expected-main", str(fixture["candidate_c"]),
            "--main-ref", "refs/heads/main", "--anchor-out", str(anchor2),
        ], capture_output=True, text=True)
        if archive_result.returncode != 0:
            self.fail(archive_result.stdout + archive_result.stderr)
        archive2 = next(path for path in (root / "docs/goal/archived").iterdir() if path.name.startswith("20260913-000001"))
        git(root, "add", ".")
        git(root, "commit", "-qm", "archive replacement A2")
        a2 = git(root, "rev-parse", "HEAD")
        request = root.parent / f"replacement-request-{root.name}.json"
        attempt = root.parent / f"replacement-attempt-{root.name}.json"
        receipt = root.parent / f"replacement-receipt-{root.name}.json"
        prepared = subject.prepare(root, archive_path=archive2, remote="origin", request_path=request, attempt_path=attempt, receipt_path=receipt, archive_anchor=anchor2)
        self.assertEqual(candidate_a, prepared["replacement_base"])
        self.assertEqual(candidate_a, prepared["remote_pre_push_head"])
        subject.begin_handoff(root, request_path=request)
        git(root, "--no-replace-objects", "push", "--", "origin", f"{a2}:refs/heads/codex/test")
        completed = subject.recover_uncertain(root, request_path=request)
        self.assertEqual("PASS", completed["status"])
        self.assertEqual(a2, completed["candidate_a"])

        # A non-ancestor/incorrect continuation pre-state is rejected even
        # though the archive and anchor themselves remain valid.
        wrong = root.parent / f"replacement-wrong-request-{root.name}.json"
        wrong_attempt = root.parent / f"replacement-wrong-attempt-{root.name}.json"
        wrong_receipt = root.parent / f"replacement-wrong-receipt-{root.name}.json"
        git(root, "--no-replace-objects", "push", "--force", "--", "origin", f"{fixture['candidate_c']}:refs/heads/codex/test")
        with self.assertRaisesRegex(ManifestError, "remote pre-state"):
            subject.prepare(root, archive_path=archive2, remote="origin", request_path=wrong, attempt_path=wrong_attempt, receipt_path=wrong_receipt, archive_anchor=anchor2)


if __name__ == "__main__":
    unittest.main()
