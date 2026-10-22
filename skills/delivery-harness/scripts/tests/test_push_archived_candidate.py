"""Archive publication handoff tests: prepare prints a no-force argv, read-back proves A."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
TESTS = SCRIPTS / "tests"
PDB_TESTS = SCRIPTS.parent.parent / "product-definition-builder" / "scripts" / "tests"

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
from harness_core import ManifestError  # noqa: E402
from test_product_package_checker import (  # noqa: E402
    release_architecture,
    strictize_approved_package,
    valid_prd,
    valid_stack,
)

while str(PDB_TESTS) in sys.path:
    sys.path.remove(str(PDB_TESTS))


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def manifest(heading: str, wrapper: str, value: dict) -> str:
    return f"# Fixture\n\n{heading}\n\n```json\n{json.dumps({wrapper: value}, indent=2)}\n```\n"


def reviewer_binding() -> dict[str, object]:
    probe = {"status": "available", "evidence": "observed in a fresh probe"}
    return {
        "kind": "native",
        "native_agent_type": "native-subagent",
        "model_provider": "codex",
        "model": None,
        "reasoning_effort": "xhigh",
        "capability_probe": {
            "direct_subagent_spawn": {**probe, "probe_id": "probe-spawn"},
            "direct_agent_result": {**probe, "probe_id": "probe-result"},
        },
        "worker_runtime": "subagent",
        "workspace_mode": "shared_checkout",
        "completion_channel": "agent_result",
    }


def version_gate(version: str) -> dict[str, object]:
    return {
        "host_version": "test-current", "minimum_host_version": None,
        "harness_version": version, "required_harness_version": version,
        "session_id": "test-session", "loaded_contract_digest": "a" * 64,
        "installed_contract_digest": "a" * 64, "status": "current", "evidence": "fixture",
    }


class ArchivePublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temps: list[tempfile.TemporaryDirectory[str]] = []

    def tearDown(self) -> None:
        for item in self._temps:
            item.cleanup()

    def _fixture(self, *, main_preview: bool = False) -> dict[str, Path | str]:
        """Create one real archive A with a bare remote and a closed receipt."""
        holder = tempfile.TemporaryDirectory()
        self._temps.append(holder)
        root = Path(holder.name)
        remote_holder = tempfile.TemporaryDirectory(prefix="archive-remote-")
        self._temps.append(remote_holder)
        remote = Path(remote_holder.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        product = root / "docs/product"
        product.mkdir(parents=True)
        architecture = release_architecture()
        if main_preview:
            architecture = architecture.replace("## Release Targets\n", "## Release Targets\n\nRelease source policy: main-preview/1\n")
        approved_prd, approved_architecture, approved_stack = strictize_approved_package(
            mf.eval_exempt_prd(valid_prd()) if main_preview else valid_prd(), architecture, valid_stack()
        )
        version = "0.63.0" if main_preview else "0.38.0"
        files = {
            "PRD.md": approved_prd,
            "architecture.md": approved_architecture,
            "stack-decisions.md": approved_stack,
        }
        for name, text in files.items():
            (product / name).write_text(text, encoding="utf-8")
        plan = mf.valid_plan()
        plan["security_review"] = {"status": "not_applicable", "skill_slot": "code_security_verification", "reason": "documentation-only fixture"}
        plan["sources"] = []
        for index, (kind, name) in enumerate((("prd", "PRD.md"), ("architecture", "architecture.md"), ("stack decisions", "stack-decisions.md")), start=1):
            path = product / name
            plan["sources"].append({"id": f"SRC-{index:03d}", "kind": kind, "location": f"docs/product/{name}", "owner": "fixture", "status": "frozen", "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "source_revision": None, "staged_revision": None, "notes": "fixture"})
        for trace in plan["traces"]:
            trace["source_ids"] = ["SRC-001"]
        for mission in plan["missions"]:
            mission["write_scope"] = ["docs/README.md"]
            for task in mission["tasks"]:
                task["write_scope"] = ["docs/README.md"]
        mf.carry_security_requirement(plan)
        from harness_manifest import plan_digest as fixture_plan_digest
        run = mf.valid_run(plan)
        run["plan"]["digest_sha256"] = fixture_plan_digest(plan)
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"] = version_gate(version)
        docs = root / "docs"
        (docs / "goal/evidence").mkdir(parents=True)
        (docs / "goal/evidence/check.txt").write_text("checked at C\n", encoding="utf-8")
        (docs / "DOCUMENTS.md").write_text("# Documents\n", encoding="utf-8")
        mf.git(root, "init", "-q", "-b", "main")
        mf.git(root, "config", "user.email", "test@example.com")
        mf.git(root, "config", "user.name", "Harness Test")
        mf.git(root, "add", "docs/product", "docs/DOCUMENTS.md", "docs/goal/evidence")
        mf.git(root, "commit", "-qm", "freeze sources")
        expected_main = mf.git(root, "rev-parse", "HEAD")
        if main_preview:
            plan["branch_policy"] = {"protocol": "main-preview/1", "kind": "ordinary",
                "base_ref": "refs/remotes/origin/main", "base_sha": expected_main}
            run["plan"]["digest_sha256"] = fixture_plan_digest(plan)
        mf.git(root, "branch", "codex/test", expected_main)
        mf.git(root, "checkout", "-q", "codex/test")
        run["integration"].update({"branch": "codex/test", "batch_base_sha": expected_main, "integration_head_sha": expected_main})
        run["observed"]["git"].update({"parent_worktree_path": root.as_posix(), "parent_branch": "main", "parent_head_sha": expected_main, "parent_dirty": False})
        mf.mark_complete(plan, run)
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"] = version_gate(version)
        run["integration"].update({"branch": "codex/test", "batch_base_sha": expected_main, "integration_head_sha": expected_main})
        run["landing"]["continuity"].update({"branch_ref": "refs/heads/codex/test", "head_sha": expected_main})
        if main_preview:
            run["runtime_capabilities"]["runtime_adapter"]["role_bindings"] = {"reviewer": reviewer_binding()}
        (docs / "goal" / "PLAN.md").write_text(mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", plan), encoding="utf-8")
        (docs / "goal" / "RUN.md").write_text(mf.manifest_markdown("## Harness Run State", "harness_run", run), encoding="utf-8")
        self._archive(root, "20260913-000000", expected_main)
        archive = next((root / "docs/goal/archived").iterdir())
        mf.git(root, "add", ".")
        mf.git(root, "commit", "-qm", "archive A")
        candidate_a = mf.git(root, "rev-parse", "HEAD")
        mf.git(root, "remote", "add", "origin", str(remote))
        return {
            "root": root, "remote": remote, "request": root.parent / f"request-{root.name}.json",
            "archive": archive, "candidate_c": expected_main, "candidate_a": candidate_a,
        }

    def _archive(self, root: Path, stamp: str, expected_main: str) -> None:
        result = subprocess.run([
            sys.executable, str(SCRIPTS / "archive_run.py"), "--repo-root", str(root), "--apply",
            "--stamp", stamp, "--expected-main", expected_main, "--main-ref", "refs/heads/main",
        ], capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)

    def _prepare(self, fixture: dict[str, Path | str]) -> dict[str, object]:
        self.addCleanup(lambda: Path(fixture["request"]).unlink(missing_ok=True))
        return subject.prepare(
            Path(fixture["root"]),
            archive_path=Path(fixture["archive"]),
            remote="origin",
            request_path=Path(fixture["request"]),
        )

    def _push(self, fixture: dict[str, Path | str], revision: str | None = None) -> None:
        git(Path(fixture["root"]), "--no-replace-objects", "push", "--", "origin", f"{revision or fixture['candidate_a']}:refs/heads/codex/test")

    def _amend_archive(self, fixture: dict[str, Path | str], message: str) -> str:
        root = Path(fixture["root"])
        git(root, "add", ".")
        git(root, "commit", "--amend", "-qm", message)
        return git(root, "rev-parse", "HEAD")

    def _rewrite_receipt(self, fixture: dict[str, Path | str], change) -> str:
        path = Path(fixture["archive"]) / "ARCHIVE_RECEIPT.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        change(value)
        value["receipt_sha256"] = archive_run._receipt_digest(value)
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        return self._amend_archive(fixture, "rewritten receipt")

    def test_prepare_prints_the_no_force_argv_and_never_touches_the_network(self) -> None:
        fixture = self._fixture()
        calls: list[tuple[str, ...]] = []
        original_git = subject._git
        original_run = subject.subprocess.run

        def local_only(argv, *args, **kwargs):
            if any(item in {"push", "fetch", "ls-remote", "pull"} for item in argv):
                raise AssertionError("prepare started a network command")
            return original_run(argv, *args, **kwargs)

        def record(root: Path, *args: str, **kwargs: object):
            calls.append(args)
            return original_git(root, *args, **kwargs)

        with patch.object(subject, "_git", side_effect=record), \
                patch.object(subject.subprocess, "run", side_effect=local_only), \
                patch.object(subject, "_remote_state", side_effect=AssertionError("prepare read the remote")):
            request = self._prepare(fixture)
        self.assertEqual("PREPARED", request["status"])
        self.assertEqual(fixture["candidate_a"], request["candidate_a"])
        self.assertEqual(fixture["candidate_c"], request["candidate_c"])
        self.assertEqual(
            ["git", "--no-replace-objects", "push", "--no-force", "--", str(fixture["remote"]),
             f"{fixture['candidate_a']}:refs/heads/codex/test"],
            request["push_argv"],
        )
        self.assertFalse(any("--force" in item or "--force-with-lease" in item or item.startswith("+") for item in request["push_argv"]))
        self.assertFalse(any(args[0] in {"push", "fetch", "ls-remote", "pull"} for args in calls if args))
        self.assertEqual("", git(Path(fixture["root"]), "ls-remote", str(fixture["remote"])))

    def test_readback_passes_only_after_the_remote_ref_equals_a(self) -> None:
        fixture = self._fixture()
        self._prepare(fixture)
        with self.assertRaisesRegex(ManifestError, "readback does not equal A"):
            subject.verify_receipt(Path(fixture["root"]), request_path=Path(fixture["request"]))
        request = json.loads(Path(fixture["request"]).read_text(encoding="utf-8"))
        git(Path(fixture["root"]), *request["push_argv"][1:])
        result = subject.verify_receipt(Path(fixture["root"]), request_path=Path(fixture["request"]))
        self.assertEqual("PASS", result["status"])
        self.assertEqual(fixture["candidate_a"], result["readback_head_sha"])
        # A remote ref that moved to another commit fails the read-back.
        git(Path(fixture["root"]), "--no-replace-objects", "push", "--force", "--", "origin", f"{fixture['candidate_c']}:refs/heads/codex/test")
        with self.assertRaisesRegex(ManifestError, "readback does not equal A"):
            subject.verify_receipt(Path(fixture["root"]), request_path=Path(fixture["request"]))

    def test_request_edit_with_a_recomputed_digest_is_rejected(self) -> None:
        fixture = self._fixture()
        request = self._prepare(fixture)
        request.pop("status")
        request.pop("request_path")
        request["push_argv"] = ["git", "push", "--force", "--", "elsewhere", "HEAD:refs/heads/main"]
        request["request_sha256"] = subject._digest({key: value for key, value in request.items() if key != "request_sha256"})
        Path(fixture["request"]).write_text(json.dumps(request, indent=2), encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "push argv"):
            subject.verify_receipt(Path(fixture["root"]), request_path=Path(fixture["request"]))
        request["plan_id"] = "PLAN-TAMPERED"
        Path(fixture["request"]).write_text(json.dumps(request, indent=2), encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "digest mismatch"):
            subject.verify_receipt(Path(fixture["root"]), request_path=Path(fixture["request"]))

    def test_remote_url_drift_is_rejected_before_readback(self) -> None:
        fixture = self._fixture()
        self._prepare(fixture)
        git(Path(fixture["root"]), "remote", "set-url", "--push", "origin", "/different/remote.git")
        with patch.object(subject, "_remote_state", side_effect=AssertionError("unexpected network")):
            with self.assertRaisesRegex(ManifestError, "push URL changed"):
                subject.verify_receipt(Path(fixture["root"]), request_path=Path(fixture["request"]))

    def test_readback_rejects_multiple_or_malformed_ref_rows(self) -> None:
        for output in (f"{'a' * 40}\trefs/heads/other\n",
                       f"{'a' * 40}\trefs/heads/test\n{'b' * 40}\trefs/heads/test\n"):
            with self.subTest(output=output), patch.object(subject.subprocess, "run", return_value=
                    subprocess.CompletedProcess([], 0, stdout=output, stderr="")):
                with self.assertRaisesRegex(ManifestError, "malformed"):
                    subject._remote_state("https://example.invalid/r.git", "refs/heads/test")

    def test_prepare_refuses_a_request_inside_the_checkout_or_already_used(self) -> None:
        fixture = self._fixture()
        with self.assertRaisesRegex(ManifestError, "outside the reviewed checkout"):
            subject.prepare(Path(fixture["root"]), archive_path=Path(fixture["archive"]), remote="origin",
                            request_path=Path(fixture["root"]) / "request.json")
        self._prepare(fixture)
        with self.assertRaisesRegex(ManifestError, "already consumed"):
            self._prepare(fixture)

    def test_prepare_refuses_a_dirty_checkout_and_a_head_that_is_not_a(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        (root / "drift.txt").write_text("drift\n", encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "must be clean"):
            self._prepare(fixture)
        (root / "drift.txt").unlink()
        git(root, "commit", "--allow-empty", "-qm", "later commit")
        with self.assertRaisesRegex(ManifestError, "complete and record candidate C|direct child of C"):
            self._prepare(fixture)
        self.assertFalse(Path(fixture["request"]).exists())

    def test_a_c_to_a_diff_touching_a_product_path_fails(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        (root / "docs/product/PRD.md").write_text("changed after C\n", encoding="utf-8")
        candidate_a = self._amend_archive(fixture, "archive A with a product edit")
        with self.assertRaisesRegex(ManifestError, "unauthorized path|validation failed|does not match"):
            subject.verify_archive_candidate(root, archive_path=Path(fixture["archive"]), candidate_a=candidate_a)
        (root / "docs/product/PRD.md").unlink()
        candidate_a = self._amend_archive(fixture, "archive A that deletes a product file")
        with self.assertRaisesRegex(ManifestError, "unauthorized path|validation failed|does not match"):
            subject.verify_archive_candidate(root, archive_path=Path(fixture["archive"]), candidate_a=candidate_a)

    def test_real_archive_run_output_is_accepted_by_the_verifier(self) -> None:
        fixture = self._fixture()
        verified = subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=str(fixture["candidate_a"]))
        self.assertEqual(fixture["candidate_c"], verified["candidate_c"])
        self.assertEqual(fixture["candidate_a"], verified["candidate_a"])
        self.assertIsNone(verified["replacement_base"])
        receipt = json.loads((Path(fixture["archive"]) / "ARCHIVE_RECEIPT.json").read_text(encoding="utf-8"))
        self.assertFalse(set(receipt) & archive_run.ARCHIVE_RECEIPT_LEGACY_ANCHOR_KEYS)

    def test_a_receipt_archived_before_0_66_with_anchor_keys_still_verifies(self) -> None:
        fixture = self._fixture()
        candidate_a = self._rewrite_receipt(fixture, lambda value: value.update(
            anchor_path=None, anchor_path_sha256=None, anchor_nonce=None))
        verified = subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=candidate_a)
        self.assertEqual(candidate_a, verified["candidate_a"])

    def test_main_preview_archive_verifies_without_development_branch(self) -> None:
        fixture = self._fixture(main_preview=True)
        result = subject.verify_archive_candidate(
            fixture["root"], archive_path=fixture["archive"], candidate_a=fixture["candidate_a"]
        )
        self.assertIsNone(result["replacement_base"])
        self.assertNotIn("refs/heads/development", git(fixture["root"], "for-each-ref", "--format=%(refname)").splitlines())

    def _next_preview_archive(self, fixture, *, omit_source=False, changed_policy=False, forged_batch=False):
        """Archive a correction C2 as A2 on the same run branch."""
        from harness_core import load_plan
        root = Path(fixture["root"])
        prior_a = str(fixture["candidate_a"])
        plan = copy.deepcopy(load_plan(Path(fixture["archive"]) / "PLAN.md"))
        plan["plan_id"] = "PLAN-NEXT"
        if changed_policy:
            plan["branch_policy"]["base_sha"] = prior_a
        if not omit_source:
            receipt = Path(fixture["archive"]) / "ARCHIVE_RECEIPT.json"
            plan["sources"].append({"id": "SRC-PRIOR-A", "kind": "prior archive candidate",
                "location": receipt.relative_to(root).as_posix(), "owner": "fixture", "status": "frozen",
                "content_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(), "source_revision": prior_a,
                "staged_revision": None, "notes": "correction"})
        git(root, "checkout", "-q", "main")
        git(root, "commit", "--allow-empty", "-qm", "later main hotfix")
        main = git(root, "rev-parse", "HEAD")
        git(root, "checkout", "-q", "codex/test")
        git(root, "commit", "--allow-empty", "-qm", "next candidate")
        if forged_batch:
            git(root, "commit", "--allow-empty", "-qm", "second repair")
        candidate = git(root, "rev-parse", "HEAD")
        run = mf.valid_run(plan)
        run["run_id"] = "RUN-NEXT"
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"].update(harness_version="0.63.0", required_harness_version="0.63.0")
        run["integration"].update(branch="codex/test", batch_base_sha=str(fixture["candidate_c"]) if forged_batch else prior_a, integration_head_sha=candidate)
        mf.mark_complete(plan, run)
        run["runtime_capabilities"]["runtime_adapter"]["role_bindings"] = {"reviewer": reviewer_binding()}
        run["observed"]["git"].update(parent_head_sha=candidate, parent_branch="codex/test", parent_dirty=False)
        goal = root / "docs/goal"
        (goal / "PLAN.md").write_text(mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", plan), encoding="utf-8")
        (goal / "RUN.md").write_text(mf.manifest_markdown("## Harness Run State", "harness_run", run), encoding="utf-8")
        self._archive(root, "20260913-000001", main)
        archive = next(path for path in (goal / "archived").iterdir() if path.name.startswith("20260913-000001"))
        git(root, "add", ".")
        git(root, "commit", "-qm", "next archive A2")
        return root, archive, git(root, "rev-parse", "HEAD")

    def test_correction_binds_the_prior_a_and_keeps_the_frozen_policy(self) -> None:
        fixture = self._fixture(main_preview=True)
        self._push(fixture)
        root, archive, head = self._next_preview_archive(fixture)
        result = subject.verify_archive_candidate(root, archive_path=archive, candidate_a=head)
        self.assertEqual(fixture["candidate_a"], result["replacement_base"])
        # Publishing A2 prints the same plain argv for the new A.
        request = subject.prepare(root, archive_path=archive, remote="origin", request_path=Path(fixture["request"]))
        self.addCleanup(lambda: Path(fixture["request"]).unlink(missing_ok=True))
        self.assertEqual(f"{head}:refs/heads/codex/test", request["push_argv"][-1])

    def test_correction_rejects_a_changed_frozen_policy(self) -> None:
        fixture = self._fixture(main_preview=True)
        root, archive, head = self._next_preview_archive(fixture, changed_policy=True)
        with self.assertRaisesRegex(ManifestError, "retain the prior frozen branch policy"):
            subject.verify_archive_candidate(root, archive_path=archive, candidate_a=head)

    def test_omitted_prior_source_is_rejected_from_archive_lineage(self) -> None:
        fixture = self._fixture(main_preview=True)
        root, archive, head = self._next_preview_archive(fixture, omit_source=True)
        with self.assertRaisesRegex(ManifestError, "must include exactly one prior archive candidate"):
            subject.verify_archive_candidate(root, archive_path=archive, candidate_a=head)

    def test_forged_batch_base_and_two_repairs_still_require_prior_source(self) -> None:
        fixture = self._fixture(main_preview=True)
        root, archive, head = self._next_preview_archive(fixture, omit_source=True, forged_batch=True)
        with self.assertRaisesRegex(ManifestError, "must include exactly one prior archive candidate"):
            subject.verify_archive_candidate(root, archive_path=archive, candidate_a=head)

    def test_archived_git_tree_rejects_symlink_and_gitlink_modes(self) -> None:
        for mode, object_type in (("120000", "blob"), ("160000", "commit")):
            with self.subTest(mode=mode):
                fake = subprocess.CompletedProcess(
                    ["git", "ls-tree"],
                    0,
                    stdout=f"{mode} {object_type} {'a' * 40}\tdocs/goal/evidence/unsafe\0".encode(),
                    stderr=b"",
                )
                with patch.object(subject, "_git", return_value=fake):
                    with self.assertRaisesRegex(ManifestError, "non-regular entry"):
                        subject._tree_files(Path("."), "a" * 40, "docs/goal/evidence")

    def test_receipt_must_cover_optional_coordination_files_from_candidate_c(self) -> None:
        fixture = self._fixture()
        with patch.object(subject, "_coordination_files", return_value={"docs/goal/DECISIONS.md": "0" * 64}):
            with self.assertRaisesRegex(ManifestError, "cover every coordination file|missing=docs/goal/DECISIONS.md"):
                subject.verify_archive_candidate(
                    Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=str(fixture["candidate_a"]))

    def test_receipt_move_type_tamper_is_rejected_even_with_recomputed_digest(self) -> None:
        fixture = self._fixture()
        candidate_a = self._rewrite_receipt(fixture, lambda value: value["moves"][0].update(type="directory"))
        with self.assertRaisesRegex(ManifestError, "type must be file|invalid fields"):
            subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=candidate_a)

    def test_self_consistent_evidence_rewrite_still_fails_candidate_c_binding(self) -> None:
        fixture = self._fixture()
        evidence = Path(fixture["archive"]) / "evidence/check.txt"
        evidence.write_text("rewritten after C\n", encoding="utf-8")

        def change(value: dict) -> None:
            move = next(item for item in value["moves"] if item["source"] == "docs/goal/evidence/check.txt")
            move["sha256"] = hashlib.sha256(archive_run._git_filtered_bytes(Path(fixture["root"]), evidence, source=evidence)).hexdigest()

        candidate_a = self._rewrite_receipt(fixture, change)
        with self.assertRaisesRegex(ManifestError, "source does not match candidate C"):
            subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=candidate_a)

    def test_optional_move_rewrite_is_rejected(self) -> None:
        fixture = self._fixture()
        candidate_a = self._rewrite_receipt(fixture, lambda value: value["moves"].append(
            {"source": "docs/tasks.md", "destination": f"{value['archive_path']}/tasks.md", "type": "file", "sha256": "0" * 64}))
        with self.assertRaisesRegex(ManifestError, "extra or missing|receipt move"):
            subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=candidate_a)

    def test_full_branch_ref_in_the_receipt_is_handled(self) -> None:
        fixture = self._fixture()
        candidate_a = self._rewrite_receipt(fixture, lambda value: value.update(branch="refs/heads/codex/test"))
        self.assertEqual("codex/test", subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=candidate_a)["run_branch"])

    def test_receipt_null_main_authority_and_stamp_path_mismatch_are_rejected(self) -> None:
        fixture = self._fixture()
        candidate_a = self._rewrite_receipt(fixture, lambda value: value.update(expected_main=None, main_ref=None))
        with self.assertRaisesRegex(ManifestError, "expected_main|main_ref"):
            subject.verify_archive_candidate(Path(fixture["root"]), archive_path=Path(fixture["archive"]), candidate_a=candidate_a)
        fixture = self._fixture()
        candidate_a = self._rewrite_receipt(fixture, lambda value: value.update(stamp="20260101-000000"))
        with self.assertRaisesRegex(ManifestError, "stamp"):
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

        def change(value: dict) -> None:
            value["moves"][0]["sha256"] = hashlib.sha256(archive_run._git_filtered_bytes(root, plan_path, source=plan_path)).hexdigest()
            value["plan_digest_sha256"] = subject.plan_digest(plan_doc["harness_plan"])

        candidate_a = self._rewrite_receipt(fixture, change)
        with self.assertRaisesRegex(ManifestError, "validation failed|objective"):
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
        self.assertFalse(archive_first_required({"runtime_capabilities": {}}))

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

    def test_unsafe_push_urls_are_rejected(self) -> None:
        for url in (
            "ext::sh -c touch /tmp/x", "-oProxyCommand=x", "https://user:secret@example.invalid/r.git",
            "https://example.invalid/r.git?token=1", "https://example.invalid/r.git#frag",
            "file:///tmp/r --upload-pack=x", "ftp://example.invalid/r.git", "https://exam ple.invalid/r.git",
        ):
            with self.subTest(url=url), self.assertRaises(ManifestError):
                subject._safe_push_url(url)
        for url in ("https://example.invalid/r.git", "ssh://git@example.invalid/r.git", "git@example.invalid:team/r.git", "/srv/git/r.git"):
            self.assertEqual(url, subject._safe_push_url(url))

    def test_removed_trusted_host_commands_are_refused(self) -> None:
        for command in ("begin-handoff", "execute", "recover"):
            with self.subTest(command=command), self.assertRaises(SystemExit):
                subject.main([command, "--repo-root", ".", "--request", "request.json"])
        with self.assertRaises(SystemExit):
            subject.main(["prepare", "--repo-root", ".", "--archive", "a", "--remote", "origin",
                          "--request-out", "r.json", "--archive-anchor", "anchor.json"])
        for gone in ("trusted_host_publication.py", "publication_credentials.py"):
            self.assertFalse((SCRIPTS / gone).exists(), gone)

    def test_prepare_cli_prints_json_and_read_back_cli_reports_a_mismatch(self) -> None:
        fixture = self._fixture()
        self.addCleanup(lambda: Path(fixture["request"]).unlink(missing_ok=True))
        prepared = subprocess.run([
            sys.executable, str(SCRIPTS / "push_archived_candidate.py"), "prepare", "--repo-root", str(fixture["root"]),
            "--archive", str(fixture["archive"]), "--remote", "origin", "--request-out", str(fixture["request"]),
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, prepared.returncode, prepared.stdout + prepared.stderr)
        self.assertEqual("PREPARED", json.loads(prepared.stdout)["status"])
        verified = subprocess.run([
            sys.executable, str(SCRIPTS / "push_archived_candidate.py"), "verify-receipt", "--repo-root", str(fixture["root"]),
            "--request", str(fixture["request"]),
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(2, verified.returncode)
        self.assertEqual("ERROR", json.loads(verified.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
