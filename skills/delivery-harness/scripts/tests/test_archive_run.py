"""Tests for archive_run.py: completed-run archival of the coordination set."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import archive_run  # noqa: E402
import manifest_fixtures as mf  # noqa: E402


def run_markdown(status: str = "complete", gates: object = None) -> str:
    payload = {
        "run_id": "RUN-20260911-demo",
        "status": status,
    }
    if gates is not None:
        payload["final_gate_results"] = gates
    return (
        "# Run\n\n## Harness Run State\n\n```json\n"
        + json.dumps({"harness_run": payload}, indent=2)
        + "\n```\n"
    )


class ArchiveRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.goal = self.root / "docs" / "goal"
        self.goal.mkdir(parents=True)

        product = b"fixture product contract\n"
        architecture = b"fixture architecture\n"
        for relative, contents in (
            ("docs/product/prd.md", product),
            ("docs/product/architecture.md", architecture),
        ):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)

        self.documents_original = (
            "# Documents\n\n| Path | Role | Owner |\n|---|---|---|\n"
            "| `docs/goal/PLAN.md` | static plan manifest | parent |\n"
        )
        (self.root / "docs" / "DOCUMENTS.md").write_text(
            self.documents_original, encoding="utf-8"
        )

        mf.git(self.root, "init", "-q", "-b", "main")
        mf.git(self.root, "config", "user.email", "test@example.com")
        mf.git(self.root, "config", "user.name", "Harness Test")
        mf.git(self.root, "add", "docs/product", "docs/DOCUMENTS.md")
        mf.git(self.root, "commit", "-qm", "freeze sources")
        self.expected_main = mf.git(self.root, "rev-parse", "HEAD")

        self.plan = mf.valid_plan()
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            product
        ).hexdigest()
        self.plan["sources"][1]["content_sha256"] = hashlib.sha256(
            architecture
        ).hexdigest()
        self.run = mf.valid_closeout_run(self.plan)
        self.run["run_id"] = "RUN-20260911-demo"
        self.run["observed"]["git"].update(
            {
                "parent_worktree_path": self.root.as_posix(),
                "parent_branch": "main",
                "parent_head_sha": self.expected_main,
                "parent_dirty": False,
            }
        )
        self.run["integration"].update(
            {
                "branch": "codex/test",
                "batch_base_sha": self.expected_main,
                "integration_head_sha": self.expected_main,
            }
        )
        mf.mark_complete(self.plan, self.run)
        mf.git(self.root, "branch", "codex/test", self.expected_main)

        self.plan_md = mf.manifest_markdown(
            "## Harness Plan Manifest", "harness_plan", self.plan
        )
        self.run_md = mf.manifest_markdown(
            "## Harness Run State", "harness_run", self.run
        )
        self.write_manifests()
        (self.goal / "DECISIONS.md").write_text("# Decisions\n", encoding="utf-8")
        evidence = self.goal / "evidence"
        evidence.mkdir()
        (evidence / "home-390-ready.png").write_bytes(b"png")
        (self.root / "docs" / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
        mf.git(self.root, "checkout", "-q", "codex/test")

    def write_manifests(self) -> None:
        (self.goal / "PLAN.md").write_text(self.plan_md, encoding="utf-8")
        (self.goal / "RUN.md").write_text(self.run_md, encoding="utf-8")

    def archive(self, *args: str) -> subprocess.CompletedProcess[str]:
        argv = [
            sys.executable,
            str(SCRIPTS_DIR / "archive_run.py"),
            "--repo-root",
            str(self.root),
            *args,
        ]
        if "--apply" in argv and "--expected-main" not in argv:
            argv.extend(["--expected-main", self.expected_main])
        if "--apply" in argv and "--main-ref" not in argv:
            argv.extend(["--main-ref", "refs/heads/main"])
        return subprocess.run(argv, capture_output=True, text=True)

    def archived_dir(self) -> Path:
        archived = self.goal / "archived"
        entries = list(archived.iterdir())
        self.assertEqual(1, len(entries), archived)
        return entries[0]

    def rebuild_run_at_head(self, head: str) -> None:
        self.run = mf.valid_closeout_run(self.plan)
        self.run["run_id"] = "RUN-20260911-demo"
        self.run["observed"]["git"].update(
            {
                "parent_worktree_path": self.root.as_posix(),
                "parent_branch": "main",
                "parent_head_sha": head,
                "parent_dirty": False,
            }
        )
        self.run["integration"].update(
            {
                "branch": "codex/test",
                "batch_base_sha": self.expected_main,
                "integration_head_sha": head,
            }
        )
        mf.mark_complete(self.plan, self.run)
        self.run_md = mf.manifest_markdown(
            "## Harness Run State", "harness_run", self.run
        )

    def test_incomplete_run_is_refused(self) -> None:
        (self.goal / "RUN.md").write_text(
            run_markdown(status="running"), encoding="utf-8"
        )
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("only a complete run", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_non_passing_final_gate_is_refused(self) -> None:
        (self.goal / "RUN.md").write_text(
            run_markdown(
                gates=[{"id": "final-closeout", "status": "planned"}]
            ),
            encoding="utf-8",
        )
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("final gate", result.stderr)

    def test_hand_edited_complete_run_fails_pair_validation(self) -> None:
        (self.goal / "RUN.md").write_text(run_markdown(), encoding="utf-8")
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("run validation failed", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())
        self.assertFalse((self.goal / "archived").exists())

    def test_unparseable_plan_is_refused(self) -> None:
        (self.goal / "PLAN.md").write_text("# Plan\n", encoding="utf-8")
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("cannot read PLAN manifest", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_missing_plan_is_refused(self) -> None:
        (self.goal / "PLAN.md").unlink()
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("required coordination file missing", result.stderr)

    def test_missing_frozen_source_is_refused_before_dry_run(self) -> None:
        (self.root / "docs/product/architecture.md").unlink()
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("source does not exist", result.stderr)
        self.assertFalse((self.goal / "archived").exists())

    def test_drifted_frozen_source_is_refused_before_dry_run(self) -> None:
        (self.root / "docs/product/prd.md").write_bytes(b"changed\n")
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("does not match immutable bytes", result.stderr)
        self.assertFalse((self.goal / "archived").exists())

    def test_stale_integration_head_is_refused(self) -> None:
        marker = self.root / "stale.txt"
        marker.write_text("new head\n", encoding="utf-8")
        mf.git(self.root, "add", "stale.txt")
        mf.git(self.root, "commit", "-qm", "move branch")
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("RUN.md is stale", result.stderr)
        self.assertFalse((self.goal / "archived").exists())

    def test_invalid_required_ui_evidence_is_refused(self) -> None:
        buffer = io.BytesIO()
        Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
        image = buffer.getvalue()
        artifact = self.goal / "evidence" / "dashboard-desktop-loaded.png"
        artifact.write_bytes(image)
        mf.git(self.root, "add", "docs/goal/evidence")
        mf.git(self.root, "commit", "-qm", "accept UI evidence")
        accepted_head = mf.git(self.root, "rev-parse", "HEAD")

        self.plan["ui_surfaces"] = [
            {
                "id": "UI-001",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        self.plan_md = mf.manifest_markdown(
            "## Harness Plan Manifest", "harness_plan", self.plan
        )
        self.rebuild_run_at_head(accepted_head)
        self.run["ui_evidence"] = [
            {
                "surface_id": "UI-001",
                "route": "/dashboard",
                "breakpoint": "desktop",
                "state": "loaded",
                "artifact_path": "docs/goal/evidence/missing.png",
                "artifact_sha256": hashlib.sha256(image).hexdigest(),
                "head_sha": accepted_head,
                "status": "PASS",
                "target_comparison": {
                    "baseline": "design_system",
                    "baseline_artifact": "check_ui_contract:clean-run",
                    "verdict": "pass",
                },
            }
        ]
        self.run_md = mf.manifest_markdown(
            "## Harness Run State", "harness_run", self.run
        )
        self.write_manifests()

        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("does not exist in accepted Git commit", result.stderr)
        self.assertFalse((self.goal / "archived").exists())

    def test_dry_run_lists_moves_and_moves_nothing(self) -> None:
        result = self.archive()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("dry run only", result.stdout)
        self.assertIn("move: docs/goal/PLAN.md", result.stdout)
        self.assertIn("move: docs/goal/evidence", result.stdout)
        self.assertIn("move: docs/tasks.md", result.stdout)
        self.assertFalse((self.goal / "archived").exists())
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_apply_moves_the_whole_coordination_set_and_never_deletes(self) -> None:
        result = self.archive("--apply")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        archived = self.archived_dir()
        self.assertEqual(
            {"PLAN.md", "RUN.md", "DECISIONS.md", "evidence", "tasks.md", "ARCHIVE_RECEIPT.json"},
            {entry.name for entry in archived.iterdir()},
        )
        self.assertEqual(
            b"png", (archived / "evidence" / "home-390-ready.png").read_bytes()
        )
        self.assertFalse((self.goal / "PLAN.md").exists())
        self.assertFalse((self.goal / "RUN.md").exists())
        self.assertFalse((self.goal / "DECISIONS.md").exists())
        self.assertFalse((self.goal / "evidence").exists())
        self.assertFalse((self.root / "docs" / "tasks.md").exists())
        self.assertTrue(self.goal.exists(), "docs/goal itself is never removed")

    def test_apply_records_the_documents_row(self) -> None:
        documents = self.root / "docs" / "DOCUMENTS.md"
        result = self.archive("--apply")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        text = documents.read_text(encoding="utf-8")
        self.assertIn("docs/goal/archived/", text)

        archive_run._update_documents(self.root)
        self.assertEqual(
            1,
            sum(
                1
                for line in documents.read_text(encoding="utf-8").splitlines()
                if "docs/goal/archived/" in line
            ),
        )

    def test_filtered_blob_read_does_not_write_the_checkout_object_database(self) -> None:
        sample = self.root / "docs" / "sample.txt"
        sample.write_bytes(b"filtered bytes\n")
        objects = self.root / ".git" / "objects"
        before = sorted(
            path.relative_to(objects).as_posix()
            for path in objects.rglob("*")
            if path.is_file()
        )
        filtered = archive_run._git_filtered_bytes(
            self.root,
            self.root / "docs" / "goal" / "archived" / "sample.txt",
            source=sample,
        )
        after = sorted(
            path.relative_to(objects).as_posix()
            for path in objects.rglob("*")
            if path.is_file()
        )
        self.assertEqual(b"filtered bytes\n", filtered)
        self.assertEqual(before, after)

    def test_empty_optional_evidence_directory_is_skipped(self) -> None:
        empty = self.goal / "evidence"
        for child in empty.iterdir():
            child.unlink()
        moves, missing = archive_run.plan_moves(self.root)
        self.assertEqual([], missing)
        self.assertNotIn(Path("docs/goal/evidence"), moves)

    def test_receipt_rejects_noncanonical_repeated_segments(self) -> None:
        value = {
            "protocol": archive_run.ARCHIVE_RECEIPT_PROTOCOL,
            "run_id": "RUN-1",
            "plan_id": "PLAN-1",
            "plan_revision": 1,
            "plan_digest_sha256": "a" * 64,
            "candidate_c": "a" * 40,
            "branch": "codex/test",
            "branch_ref": "refs/heads/codex/test",
            "expected_main": "b" * 40,
            "main_ref": "refs/heads/main",
            "stamp": "20260101-000000",
            "archive_path": "docs/goal/archived/20260101-000000-run",
            "moves": [
                {"source": "docs/goal//PLAN.md", "destination": "docs/goal/archived/20260101-000000-run/PLAN.md", "type": "file", "sha256": "c" * 64},
                {"source": "docs/goal/RUN.md", "destination": "docs/goal/archived/20260101-000000-run/RUN.md", "type": "file", "sha256": "d" * 64},
            ],
            "documents_before_sha256": None,
            "documents_after_sha256": None,
            "anchor_path": None,
            "anchor_path_sha256": None,
            "anchor_nonce": None,
            "receipt_sha256": "e" * 64,
        }
        errors = archive_run.validate_archive_receipt(value)
        self.assertTrue(any("source is outside" in item for item in errors))

        for source in ("./docs/goal/PLAN.md", "docs/goal/../PLAN.md"):
            value["moves"][0]["source"] = source
            self.assertTrue(
                any("source is outside" in item for item in archive_run.validate_archive_receipt(value)),
                source,
            )
        value["moves"][0]["source"] = "docs/goal/PLAN.md"
        value["moves"][0]["destination"] = "docs/goal/archived/20260101-000000-run//PLAN.md"
        self.assertTrue(
            any("destination is outside" in item for item in archive_run.validate_archive_receipt(value))
        )

    def test_recover_interrupted_archive_is_idempotent_and_descriptor_bound(self) -> None:
        target = self.goal / "archived" / "20260101-000000-recovery"
        target.mkdir(parents=True)
        source = self.goal / "PLAN.md"
        destination = target / "PLAN.md"
        source.rename(destination)
        journal = {
            "protocol": archive_run.ARCHIVE_JOURNAL_PROTOCOL,
            "phase": "moving",
            "archive_path": "docs/goal/archived/20260101-000000-recovery",
            "moves": [{"source": "docs/goal/PLAN.md", "destination": "docs/goal/archived/20260101-000000-recovery/PLAN.md"}],
            "moved": [],
            "documents_before_b64": None,
            "documents_before_identity": None,
            "archived_parent_created": False,
            "anchor_path": None,
        }
        (target / archive_run.ARCHIVE_JOURNAL_NAME).write_text(
            json.dumps(journal), encoding="utf-8"
        )
        self.assertEqual(0, archive_run.recover_archive(self.root, target))
        self.assertTrue(source.exists())
        self.assertFalse(target.exists())
        # A second recovery is a no-op and cannot touch the recovered source.
        self.assertEqual(0, archive_run.recover_archive(self.root, target))
        self.assertTrue(source.exists())

    def test_failed_archive_does_not_remove_a_preexisting_archived_parent(self) -> None:
        archived = self.goal / "archived"
        archived.mkdir()
        sentinel = archived / "keep.txt"
        sentinel.write_text("unrelated archive\n", encoding="utf-8")
        guard = archive_run._ArchiveMutationGuard(
            self.root,
            [Path("docs/goal/PLAN.md")],
            archived / "20260101-000000-preexisting-parent",
        )
        try:
            self.assertFalse(guard.archived_created)
            guard.remove_archived_parent()
        finally:
            guard.close()
        self.assertEqual("unrelated archive\n", sentinel.read_text(encoding="utf-8"))
        self.assertTrue(archived.exists())

    def test_nested_symlink_swap_after_guard_is_rejected(self) -> None:
        nested = self.goal / "evidence" / "deep" / "inner"
        nested.mkdir(parents=True)
        real_move = archive_run._ArchiveMutationGuard.move

        try:
            probe = nested / "probe"
            probe.symlink_to(self.root / ".git", target_is_directory=True)
            probe.unlink()
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink unavailable: {exc}")

        def swap_after_move(guard: archive_run._ArchiveMutationGuard, source: Path, destination: Path) -> None:
            real_move(guard, source, destination)
            if source.name == "evidence":
                link = destination / "deep" / "inner" / "post-guard-link"
                link.symlink_to(self.root / ".git", target_is_directory=True)

        with patch.object(archive_run._ArchiveMutationGuard, "move", autospec=True, side_effect=swap_after_move):
            code = archive_run.archive(
                self.root,
                slug="post-guard-swap",
                apply=True,
                stamp="20260101-000000",
                expected_main=self.expected_main,
                main_ref="refs/heads/main",
            )
        self.assertEqual(1, code)

    def test_nested_symlinks_at_multiple_depths_are_rejected_before_archive(self) -> None:
        for depth in (self.goal / "evidence" / "deep" / "one", self.goal / "evidence" / "deep" / "two"):
            depth.mkdir(parents=True)
            link = depth / "link-to-git"
            try:
                link.symlink_to(self.root / ".git", target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
        result = self.archive("--apply", "--stamp", "20260101-000000")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertRegex(result.stderr, "symlink|reparse")
        self.assertFalse((self.goal / "archived" / "20260101-000000-run-20260911-demo").exists())

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_nested_junctions_at_multiple_depths_are_rejected_before_archive(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is unavailable")
        target = self.root / ".git"
        for depth in (self.goal / "evidence" / "junction" / "one", self.goal / "evidence" / "junction" / "two"):
            depth.mkdir(parents=True)
            link = depth / "link-to-git"
            created = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-Command",
                    "New-Item -ItemType Junction -Path $env:PDH_JUNCTION -Target $env:PDH_TARGET -ErrorAction Stop | Out-Null",
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "PDH_JUNCTION": str(link), "PDH_TARGET": str(target)},
                timeout=30,
            )
            if created.returncode != 0:
                self.skipTest(created.stderr.strip() or "junction creation failed")
        result = self.archive("--apply", "--stamp", "20260101-000000")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertRegex(result.stderr, "reparse|symlink")

    def test_wrong_archival_base_is_refused_and_moves_nothing(self) -> None:
        wrong_base = "1" * 40
        result = self.archive("--apply", "--expected-main", wrong_base)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("not the authorized/read-back SHA", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())
        self.assertFalse((self.goal / "archived").exists())

    def test_a_move_failure_rolls_back_every_moved_entry(self) -> None:
        real_move = archive_run._ArchiveMutationGuard.move

        def fail_on_run(guard: archive_run._ArchiveMutationGuard, source: Path, destination: Path) -> None:
            if source.name == "RUN.md":
                raise OSError("injected RUN.md move failure")
            real_move(guard, source, destination)

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(archive_run._ArchiveMutationGuard, "move", autospec=True, side_effect=fail_on_run):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = archive_run.archive(
                    self.root,
                    slug="rollback",
                    apply=True,
                    stamp="20260101-000000",
                    expected_main=self.expected_main,
                    main_ref="refs/heads/main",
                )

        self.assertEqual(1, code, stdout.getvalue() + stderr.getvalue())
        self.assertIn("rolled back every moved entry", stderr.getvalue())
        for relative in (
            "docs/goal/PLAN.md",
            "docs/goal/RUN.md",
            "docs/goal/DECISIONS.md",
            "docs/goal/evidence",
            "docs/tasks.md",
        ):
            self.assertTrue((self.root / relative).exists(), relative)
        self.assertFalse((self.goal / "archived").exists())

    def test_a_documents_update_failure_rolls_back_moves_and_document_bytes(self) -> None:
        documents = self.root / "docs" / "DOCUMENTS.md"
        original = self.documents_original
        real_update = archive_run._update_documents

        def fail_after_write(root: Path) -> None:
            real_update(root)
            raise OSError("injected DOCUMENTS update failure")

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(archive_run, "_update_documents", side_effect=fail_after_write):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = archive_run.archive(
                    self.root,
                    slug="documents-rollback",
                    apply=True,
                    stamp="20260101-000000",
                    expected_main=self.expected_main,
                    main_ref="refs/heads/main",
                )

        self.assertEqual(1, code, stdout.getvalue() + stderr.getvalue())
        self.assertIn("rolled back every moved entry", stderr.getvalue())
        self.assertEqual(original, documents.read_text(encoding="utf-8"))
        self.assertTrue((self.goal / "RUN.md").exists())
        self.assertFalse((self.goal / "archived").exists())

    def test_documents_update_failure_preserves_a_concurrent_new_documents_file(self) -> None:
        documents = self.root / "docs" / "DOCUMENTS.md"
        documents.unlink()
        mf.git(self.root, "add", "docs/DOCUMENTS.md")
        mf.git(self.root, "commit", "-qm", "remove document inventory")
        new_head = mf.git(self.root, "rev-parse", "HEAD")
        self.rebuild_run_at_head(new_head)
        self.write_manifests()
        self.assertFalse(documents.exists())

        def fail_after_write(root: Path) -> None:
            (root / "docs" / "DOCUMENTS.md").write_text(
                "partial write\n", encoding="utf-8"
            )
            raise OSError("injected DOCUMENTS update failure")

        with patch.object(archive_run, "_update_documents", side_effect=fail_after_write):
            code = archive_run.archive(
                self.root,
                slug="new-documents-rollback",
                apply=True,
                stamp="20260101-000000",
                expected_main=self.expected_main,
                main_ref="refs/heads/main",
            )

        self.assertEqual(1, code)
        # A newly introduced DOCUMENTS file is not transaction-owned when the
        # write path failed before recording its identity.  Preserve it and
        # leave the journaled archive target for explicit recovery rather than
        # deleting a concurrent writer's data.
        self.assertTrue(documents.exists())
        self.assertTrue((self.goal / "RUN.md").exists())
        self.assertTrue((self.goal / "archived").exists())

    def test_documents_concurrent_edit_is_preserved_during_rollback(self) -> None:
        documents = self.root / "docs" / "DOCUMENTS.md"
        real_update = archive_run._update_documents

        def edit_after_transaction_write(root: Path) -> None:
            real_update(root)
            (root / "docs" / "DOCUMENTS.md").write_text("concurrent operator edit\n", encoding="utf-8")
            raise OSError("injected concurrent edit")

        with patch.object(archive_run, "_update_documents", side_effect=edit_after_transaction_write):
            code = archive_run.archive(
                self.root,
                slug="documents-concurrent-edit",
                apply=True,
                stamp="20260101-000000",
                expected_main=self.expected_main,
                main_ref="refs/heads/main",
            )
        self.assertEqual(1, code)
        self.assertEqual("concurrent operator edit\n", documents.read_text(encoding="utf-8"))
        self.assertTrue((self.goal / "RUN.md").exists())
        self.assertTrue((self.goal / "archived").exists())

    def test_archive_rereads_head_under_guard_before_first_write(self) -> None:
        original = archive_run._live_head_problems
        calls = {"count": 0}

        def drift_after_first_snapshot(run: dict[str, object], root: Path, expected_main: str, main_ref: str, moves: list[Path]) -> list[str]:
            calls["count"] += 1
            problems = original(run, root, expected_main, main_ref, moves)
            if calls["count"] == 1:
                mf.git(root, "commit", "--allow-empty", "-qm", "late HEAD drift")
            return problems

        with patch.object(archive_run, "_live_head_problems", side_effect=drift_after_first_snapshot):
            code = archive_run.archive(
                self.root,
                slug="late-head-drift",
                apply=True,
                stamp="20260101-000000",
                expected_main=self.expected_main,
                main_ref="refs/heads/main",
            )
        self.assertEqual(1, code)
        self.assertGreaterEqual(calls["count"], 2)
        self.assertFalse((self.goal / "archived" / "20260101-000000-late-head-drift").exists())

    def test_archive_rereads_clean_status_under_guard(self) -> None:
        original = archive_run._live_head_problems
        calls = {"count": 0}

        def dirty_after_first_snapshot(run: dict[str, object], root: Path, expected_main: str, main_ref: str, moves: list[Path]) -> list[str]:
            calls["count"] += 1
            problems = original(run, root, expected_main, main_ref, moves)
            if calls["count"] == 1:
                (root / "late-unrelated.txt").write_text("late dirty path\n", encoding="utf-8")
            return problems

        with patch.object(archive_run, "_live_head_problems", side_effect=dirty_after_first_snapshot):
            code = archive_run.archive(
                self.root,
                slug="late-clean-drift",
                apply=True,
                stamp="20260101-000000",
                expected_main=self.expected_main,
                main_ref="refs/heads/main",
            )
        self.assertEqual(1, code)
        self.assertGreaterEqual(calls["count"], 2)
        self.assertTrue((self.root / "late-unrelated.txt").exists())

    def test_anchor_timestamp_requires_strict_utc_rfc3339(self) -> None:
        for value in (
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00Z",
            "2026-01-01T00:00:00.1234567Z",
        ):
            with self.assertRaises(ValueError, msg=value):
                archive_run._validate_utc_timestamp(value, "created_at")
        archive_run._validate_utc_timestamp("2026-01-01T00:00:00.123456Z", "created_at")

    def test_apply_refuses_the_wrong_current_branch(self) -> None:
        mf.git(self.root, "checkout", "-q", "main")
        result = self.archive("--apply", "--stamp", "20260101-000000")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("forbidden on protected branch 'main'", result.stderr)
        self.assertIn("does not match run integration branch", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_apply_refuses_unrelated_dirty_paths(self) -> None:
        (self.root / "unrelated.txt").write_text("keep me\n", encoding="utf-8")
        result = self.archive("--apply", "--stamp", "20260101-000000")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("unrelated dirty path: unrelated.txt", result.stderr)
        self.assertTrue((self.root / "unrelated.txt").exists())
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_apply_rejects_documents_symlink_without_touching_internal_target(self) -> None:
        documents = self.root / "docs" / "DOCUMENTS.md"
        internal = self.root / ".git" / "config"
        original = internal.read_bytes()
        documents.unlink()
        try:
            documents.symlink_to(internal)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        result = self.archive("--apply")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertRegex(result.stderr, "unsafe (symlink|reparse)|symlink")
        self.assertEqual(original, internal.read_bytes())
        self.assertFalse((self.goal / "archived").exists())

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_apply_rejects_documents_junction_without_touching_git_metadata(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is unavailable")
        documents = self.root / "docs" / "DOCUMENTS.md"
        internal = self.root / ".git"
        config = internal / "config"
        original = config.read_bytes()
        documents.unlink()
        created = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-Command",
                "New-Item -ItemType Junction -Path $env:PDH_JUNCTION -Target $env:PDH_TARGET -ErrorAction Stop | Out-Null",
            ],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PDH_JUNCTION": str(documents),
                "PDH_TARGET": str(internal),
            },
            timeout=30,
        )
        if created.returncode != 0:
            self.skipTest(created.stderr.strip() or "junction creation failed")
        result = self.archive("--apply")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertRegex(result.stderr, "unsafe (symlink|reparse)|reparse point")
        self.assertEqual(original, config.read_bytes())
        self.assertFalse((self.goal / "archived").exists())

    def test_archive_rejects_git_replace_refs_before_validation(self) -> None:
        mf.git(self.root, "update-ref", f"refs/replace/{self.expected_main}", self.expected_main)
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("replacement refs", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_apply_refuses_a_stale_but_reachable_main_sha(self) -> None:
        mf.git(self.root, "commit", "--allow-empty", "-qm", "advance candidate")
        new_head = mf.git(self.root, "rev-parse", "HEAD")
        mf.git(self.root, "branch", "-f", "main", new_head)
        self.rebuild_run_at_head(new_head)
        self.write_manifests()

        result = self.archive(
            "--apply",
            "--stamp",
            "20260101-000000",
            "--expected-main",
            self.expected_main,
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("observed main ref refs/heads/main is", result.stderr)
        self.assertIn("not the authorized/read-back SHA", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_apply_refuses_a_resolvable_non_main_ref(self) -> None:
        mf.git(self.root, "branch", "not-main", self.expected_main)
        result = self.archive(
            "--apply",
            "--stamp",
            "20260101-000000",
            "--main-ref",
            "refs/heads/not-main",
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("--main-ref must be refs/heads/main", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_a_second_archive_into_an_existing_target_is_refused(self) -> None:
        result = self.archive("--apply", "--stamp", "20260101-000000")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        (self.goal / "PLAN.md").write_text(self.plan_md, encoding="utf-8")
        (self.goal / "RUN.md").write_text(self.run_md, encoding="utf-8")
        result = self.archive("--apply", "--stamp", "20260101-000000")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("archive target already exists", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_a_malformed_stamp_is_rejected(self) -> None:
        result = self.archive("--apply", "--stamp", "not-a-stamp")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("YYYYMMDD-HHMMSS", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_slug_defaults_to_the_run_id(self) -> None:
        result = self.archive("--apply")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("run-20260911-demo", self.archived_dir().name)

    @unittest.skipUnless(os.name == "nt", "requires Windows directory sharing semantics")
    def test_archive_parent_swap_after_preflight_cannot_escape_checkout(self) -> None:
        external = self.root.parent / f"archive-external-{self.root.name}"
        external.mkdir()
        original_init = archive_run._ArchiveMutationGuard.__init__
        attempted = {"blocked": False}
        backup = self.goal / "archived-original"

        def swap_after_guard(guard: archive_run._ArchiveMutationGuard, root: Path, moves: list[Path], target: Path, anchor_path: Path | None = None) -> None:
            original_init(guard, root, moves, target, anchor_path)
            archived = self.goal / "archived"
            try:
                archived.rename(backup)
            except OSError:
                attempted["blocked"] = True
                guard.close()
                raise
            archived.mkdir()
            attempted["blocked"] = True

        with patch.object(archive_run._ArchiveMutationGuard, "__init__", swap_after_guard):
            result = archive_run.archive(
                self.root,
                slug="run-20260911-demo",
                apply=True,
                stamp="20260101-000000",
                expected_main=self.expected_main,
                main_ref="refs/heads/main",
            )
        if (self.goal / "archived").exists() and not any((self.goal / "archived").iterdir()):
            (self.goal / "archived").rmdir()
        if backup.exists() and not (self.goal / "archived").exists():
            backup.rename(self.goal / "archived")
        self.assertEqual(1, result)
        self.assertTrue(attempted["blocked"])
        self.assertFalse(any(external.iterdir()))
        self.assertTrue((self.goal / "PLAN.md").exists())
        self.assertTrue((self.goal / "RUN.md").exists())
        self.assertFalse((self.goal / "archived" / "20260101-000000-run-20260911-demo").exists())

    @unittest.skipUnless(os.name == "nt", "requires Windows directory sharing semantics")
    def test_rollback_target_swap_is_blocked_before_handle_bound_cleanup(self) -> None:
        original_update = archive_run._update_documents
        original_remove = archive_run._ArchiveMutationGuard.remove_target
        blocked = {"value": False}

        def fail_documents(root: Path) -> None:
            original_update(root)
            raise OSError("injected rollback")

        def guarded_remove(guard: archive_run._ArchiveMutationGuard) -> None:
            backup = guard.target.with_name(guard.target.name + "-backup")
            try:
                guard.target.rename(backup)
            except OSError:
                blocked["value"] = True
            else:
                backup.rename(guard.target)
                raise AssertionError("rollback target replacement was not blocked")
            original_remove(guard)

        with patch.object(archive_run, "_update_documents", side_effect=fail_documents):
            with patch.object(archive_run._ArchiveMutationGuard, "remove_target", autospec=True, side_effect=guarded_remove):
                result = archive_run.archive(
                    self.root,
                    slug="rollback-target",
                    apply=True,
                    stamp="20260101-000000",
                    expected_main=self.expected_main,
                    main_ref="refs/heads/main",
                )
        self.assertEqual(1, result)
        self.assertTrue(blocked["value"])
        self.assertTrue((self.goal / "PLAN.md").exists())
        self.assertFalse((self.goal / "archived" / "20260101-000000-rollback-target").exists())


if __name__ == "__main__":
    unittest.main()
