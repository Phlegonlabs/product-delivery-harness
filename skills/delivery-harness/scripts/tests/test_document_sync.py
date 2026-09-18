import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_document_sync import LIMIT, inspect, main, safe_path, unique_object


class DocumentSyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.doc = self.root / "AGENTS.md"
        self.doc.write_text("Owner rule: keep data.\n", encoding="utf-8")
        self.digest = hashlib.sha256(b"installed-contract").hexdigest()

    def observe(self, baseline=None, paths=None, required=()):
        return inspect(self.root, paths or ["AGENTS.md"], self.digest,
                       self.digest, baseline, required)

    def test_first_observation_requires_review_and_writes_nothing(self):
        before = self.doc.read_bytes()
        result = self.observe()
        self.assertEqual("review_required", result["status"])
        self.assertEqual("baseline_review_required", result["findings"][0]["kind"])
        self.assertEqual(before, self.doc.read_bytes())
        self.assertEqual([self.doc], list(self.root.iterdir()))

    def test_unchanged_is_byte_observation_not_approval(self):
        snapshot = self.observe()["snapshot"]
        result = self.observe(snapshot)
        self.assertEqual("unchanged", result["status"])
        self.assertIn("approval are separate", result["meaning"])

    def test_changed_missing_and_new_documents(self):
        snapshot = self.observe()["snapshot"]
        self.doc.write_text("new owner instruction", encoding="utf-8")
        self.assertEqual("document_changed", self.observe(snapshot)["findings"][0]["kind"])
        self.doc.unlink()
        self.assertEqual("missing_document", self.observe(snapshot)["findings"][0]["kind"])
        self.assertTrue(self.observe(snapshot, ["CLAUDE.md"])["findings"])

    def test_required_absent_document_fails_even_with_matching_baseline(self):
        snapshot = self.observe(paths=["CLAUDE.md"])["snapshot"]
        result = self.observe(snapshot, ["CLAUDE.md"], ["CLAUDE.md"])
        self.assertEqual("missing_document", result["findings"][0]["kind"])

    def test_runtime_mismatch_and_contract_change(self):
        snapshot = self.observe()["snapshot"]
        result = inspect(self.root, ["AGENTS.md"], self.digest, "a" * 64, snapshot)
        kinds = {row["kind"] for row in result["findings"]}
        self.assertEqual({"restart_required", "skill_contract_changed"}, kinds)

    def test_retired_pointer_is_review_not_auto_replacement(self):
        self.doc.write_text("Use `full-harness`", encoding="utf-8")
        result = self.observe(self.observe()["snapshot"])
        self.assertEqual("legacy_pointer_review", result["findings"][0]["kind"])
        self.assertEqual("Use `full-harness`", self.doc.read_text(encoding="utf-8"))

    def test_paths_never_read_secrets_or_history(self):
        for name in ("../AGENTS.md", "/AGENTS.md", "docs//x.md", ".env", "docs/secrets.md",
                     "docs/archived/PRD.md", "docs/product/outcomes/a.md", "C:/AGENTS.md", "a\\AGENTS.md"):
            with self.subTest(path=name), self.assertRaises(ValueError):
                safe_path(self.root, name, document=True)

    def test_nested_instruction_allowed(self):
        self.assertEqual(self.root / "app/AGENTS.md", safe_path(self.root, "app/AGENTS.md", document=True))

    def test_scoped_root_and_component_documents_allowed(self):
        for name in ("SECURITY.md", "README.md", "CONTRIBUTING.md", "app/operations.md"):
            self.assertEqual(self.root / name, safe_path(self.root, name, document=True))

    def test_snapshot_portable_to_another_checkout(self):
        snapshot = self.observe()["snapshot"]
        self.assertNotIn("root", snapshot)
        with tempfile.TemporaryDirectory() as other:
            root = Path(other).resolve()
            (root / "AGENTS.md").write_bytes(self.doc.read_bytes())
            self.assertEqual("unchanged", inspect(root, ["AGENTS.md"], self.digest,
                             self.digest, snapshot)["status"])

    def test_unknown_runtime_cannot_claim_unchanged(self):
        result = inspect(self.root, ["AGENTS.md"], None, self.digest, self.observe()["snapshot"])
        self.assertEqual("review_required", result["status"])
        self.assertEqual("loaded_identity_unobserved", result["findings"][0]["kind"])

    def test_symlink_rejected(self):
        link = self.root / "CLAUDE.md"
        try:
            link.symlink_to(self.doc)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaises(ValueError):
            self.observe(paths=["CLAUDE.md"])

    def test_invalid_baselines_and_paths(self):
        snapshot = self.observe()["snapshot"]
        for bad in ([], {}, dict(snapshot, root="wrong"), dict(snapshot, documents={"AGENTS.md": []})):
            with self.subTest(baseline=bad), self.assertRaises(ValueError):
                self.observe(bad)
        with self.assertRaises(ValueError):
            self.observe(paths=["AGENTS.md", "AGENTS.md"])
        with self.assertRaises(ValueError):
            json.loads('{"a":1,"a":2}', object_pairs_hook=unique_object)

    def test_link_guard_without_platform_privilege(self):
        with patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaises(ValueError):
                self.observe()

    def test_oversized_input_is_rejected(self):
        self.doc.write_bytes(b"x" * (LIMIT + 1))
        with self.assertRaises(ValueError):
            self.observe()

    def test_cli_installed_digest_is_observed_not_caller_override(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            result = main(["--repo-root", str(self.root), "--loaded-digest", self.digest,
                           "--installed-digest", "0" * 64, "--path", "AGENTS.md"])
        self.assertEqual(2, result)
        self.assertEqual("invalid", json.loads(stream.getvalue())["status"])

    def test_cli_error_is_redacted(self):
        self.doc.write_bytes(b"\xffDO-NOT-PRINT")
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), patch("check_document_sync.contract_digest", return_value=self.digest):
            result = main(["--repo-root", str(self.root), "--loaded-digest", self.digest,
                           "--path", "AGENTS.md"])
        self.assertEqual(2, result)
        self.assertNotIn("DO-NOT-PRINT", stream.getvalue())

    def test_deep_baseline_returns_structured_invalid(self):
        (self.root / "baseline.json").write_text('{"x":' + '[' * 2000 + '0' + ']' * 2000 + '}')
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), patch("check_document_sync.contract_digest", return_value=self.digest):
            status = main(["--repo-root", str(self.root), "--baseline", "baseline.json"])
        self.assertEqual(2, status)
        self.assertEqual("invalid", json.loads(stream.getvalue())["status"])


if __name__ == "__main__":
    unittest.main()
