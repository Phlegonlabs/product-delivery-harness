"""Real native-boundary races across all four document-write consumers."""

import os
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
COMPILER = SCRIPTS.parents[1] / "design-system-compiler/scripts"
sys.path[:0] = [str(SCRIPTS), str(COMPILER)]
import archive_run  # noqa: E402
import document_write  # noqa: E402
import design_document_write  # noqa: E402
import check_design_system_pair  # noqa: E402
import harness_transition  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
import render_tasks_view  # noqa: E402


class DocumentWriteTests(unittest.TestCase):
    def consumer(self, root, kind):
        parent = root / "owned"
        parent.mkdir()
        target = parent / "document.md"
        original = b"owner original\n"
        target.write_bytes(original)
        helper = document_write
        if kind == "run":
            invoke = lambda: harness_transition._replace_document_text(target, "generated\n", expected_text="owner original\n")
        elif kind == "archive":
            invoke = lambda: archive_run._write_documents(target, b"generated\n", expected=original)
        elif kind == "compiler":
            helper = design_document_write
            invoke = lambda: check_design_system_pair._write_markdown(target, b"generated\n", original)
        else:
            plan = mf.valid_plan()
            run = mf.valid_run(plan)
            target.unlink()
            render_tasks_view.refresh_view(plan, run, target)
            original = target.read_bytes()
            run["status"] = "paused"
            invoke = lambda: render_tasks_view.refresh_view(plan, run, target)
        return target, original, invoke, helper

    def matrix(self, scenario):
        for kind in ("run", "tasks", "compiler", "archive"):
            with self.subTest(consumer=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target, original, invoke, helper = self.consumer(root, kind)
                native_name = "_windows_replace" if os.name == "nt" else "_posix_exchange"
                native = getattr(helper, native_name)
                calls = []
                outside = root / "outside"
                outside.mkdir()
                (outside / target.name).write_bytes(b"outside bytes\n")
                moved = root / "moved"

                def boundary(*arguments):
                    calls.append(arguments)
                    if len(calls) == 1:
                        if scenario == "same-bytes-new-inode":
                            replacement = root / "owner-new.md"
                            replacement.write_bytes(original)
                            os.replace(replacement, target)
                        elif scenario == "parent":
                            target.parent.rename(moved)
                            target.parent.symlink_to(outside, target_is_directory=True)
                        elif scenario == "leaf":
                            target.rename(root / "owner-preserved.md")
                            target.symlink_to(outside / target.name)
                        elif scenario == "unavailable":
                            raise OSError("native replacement unavailable")
                        elif scenario == "staging":
                            replacement = Path(arguments[1]) if os.name == "nt" else target.parent / arguments[1]
                            replacement.write_bytes(b"staging owner edit\n")
                        else:
                            target.write_bytes(b"first owner edit\n")
                    elif len(calls) == 2:
                        if scenario == "restore-edit": target.write_bytes(b"second owner edit\n")
                        elif scenario == "restore-failure": raise OSError("restore unavailable")
                    native(*arguments)
                    if len(calls) == 1 and scenario == "after-replace":
                        target.write_bytes(b"second owner edit\n")

                if scenario == "leaf":
                    probe = root / "link-probe"
                    try:
                        probe.symlink_to(outside / target.name)
                    except OSError as error:
                        self.skipTest(f"symlink unavailable: {error}")
                    probe.unlink()
                with patch.object(helper, native_name, side_effect=boundary):
                    with self.assertRaises((OSError, ValueError, harness_transition.ManifestError)):
                        invoke()
                self.assertTrue(calls, "the actual native boundary must be exercised")
                self.assertEqual(b"outside bytes\n", (outside / target.name).read_bytes())
                retained = [path.read_bytes() for path in root.rglob("*")
                            if path.is_file() and not path.is_symlink()]
                if scenario in {"after-replace", "restore-edit"}:
                    self.assertIn(b"first owner edit\n", retained)
                    self.assertIn(b"second owner edit\n", retained)
                elif scenario == "staging":
                    self.assertIn(b"staging owner edit\n", retained)
                    self.assertIn(original, retained)
                elif scenario not in {"parent", "leaf", "unavailable", "same-bytes-new-inode"}:
                    self.assertIn(b"first owner edit\n", retained)
                else:
                    self.assertIn(original, retained)

    def test_initial_native_swap_preserves_owner_edit(self): self.matrix("edit")
    def test_identical_bytes_with_replaced_identity_are_refused(self): self.matrix("same-bytes-new-inode")
    def test_owner_edit_after_initial_swap_is_preserved(self): self.matrix("after-replace")
    def test_restore_native_swap_captures_a_second_edit(self): self.matrix("restore-edit")
    def test_restore_failure_retains_displaced_owner_bytes(self): self.matrix("restore-failure")
    def test_parent_swap_never_writes_through_redirected_path(self): self.matrix("parent")
    def test_leaf_swap_never_writes_through_symlink(self): self.matrix("leaf")
    def test_unavailable_native_primitive_refuses_without_owner_loss(self): self.matrix("unavailable")
    def test_staging_swap_cannot_report_a_successful_generated_write(self): self.matrix("staging")

    @unittest.skipUnless(os.name == "nt", "Windows backup collision")
    def test_backup_collision_preserves_unexpected_owner_file(self):
        for kind in ("run", "tasks", "compiler", "archive"):
            with self.subTest(consumer=kind), tempfile.TemporaryDirectory() as directory:
                target, original, invoke, helper = self.consumer(Path(directory), kind)
                native = helper._windows_replace
                injected = []
                def boundary(destination, replacement, backup):
                    backup.write_bytes(b"backup owner edit\n")
                    injected.append(backup)
                    native(destination, replacement, backup)
                with patch.object(helper, "_windows_replace", side_effect=boundary):
                    with self.assertRaises((OSError, ValueError, harness_transition.ManifestError)):
                        invoke()
                self.assertEqual(1, len(injected))
                self.assertEqual(original, target.read_bytes())
                self.assertEqual(b"backup owner edit\n", injected[0].read_bytes())

    def test_ordinary_success_and_owned_staging_cleanup(self):
        for kind in ("run", "tasks", "compiler", "archive"):
            with self.subTest(consumer=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target, original, invoke, _ = self.consumer(root, kind)
                invoke()
                self.assertNotEqual(original, target.read_bytes())
                self.assertEqual([], list(root.rglob(".pdh-conflict-*")))

    def test_run_text_snapshot_accepts_raw_crlf(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "RUN.md"
            target.write_bytes(b"owner\r\n")
            harness_transition._replace_document_text(target, "updated\n", expected_text="owner\n")
            self.assertEqual(b"updated\n", target.read_bytes())

    def test_public_run_transition_refuses_native_boundary_owner_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            head = mf.init_repo(root, "README.md", default_branch="codex/test")
            plan = mf.valid_plan()
            mf.materialize_plan_sources(root, plan)
            run = mf.valid_run(plan)
            run["integration"].update(branch="codex/test", batch_base_sha=head, integration_head_sha=head)
            goal = root / "docs/goal"
            goal.mkdir()
            plan_path, run_path = goal / "PLAN.md", goal / "RUN.md"
            plan_path.write_text(mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", plan), encoding="utf-8")
            run_path.write_text(mf.manifest_markdown("## Harness Run State", "harness_run", run), encoding="utf-8")
            native_name = "_windows_replace" if os.name == "nt" else "_posix_exchange"
            native = getattr(document_write, native_name)
            calls = []
            def boundary(*arguments):
                calls.append(arguments)
                if len(calls) == 1: run_path.write_bytes(b"owner revocation at native boundary\n")
                native(*arguments)
            output = io.StringIO()
            with patch.object(document_write, native_name, side_effect=boundary), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                code = harness_transition.main(["--plan", str(plan_path), "--run", str(run_path),
                    "--repo-root", str(root), "--session-id", "BOUNDARY-RACE", "acquire-run-lock"])
            self.assertEqual(2, code, output.getvalue())
            self.assertTrue(calls, output.getvalue())
            self.assertEqual(b"owner revocation at native boundary\n", run_path.read_bytes())

    def test_standalone_compiler_uses_the_same_bounded_primitive(self):
        self.assertEqual(Path(document_write.__file__).read_bytes(), Path(design_document_write.__file__).read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "design-system.md"
            target.write_bytes(b"\xef\xbb\xbfowner\r\n")
            target.chmod(0o640)
            mode = target.stat().st_mode
            check_design_system_pair._write_markdown(target, b"\xef\xbb\xbfcompiled\r\n", target.read_bytes())
            self.assertEqual(b"\xef\xbb\xbfcompiled\r\n", target.read_bytes())
            self.assertEqual(mode, target.stat().st_mode)


if __name__ == "__main__":
    unittest.main()
