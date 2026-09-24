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
from check_document_sync import LIMIT, default_inventory, inspect, main, safe_path, unique_object


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
        self.assertEqual([], result["impacts"])

    def test_impacts_route_changes_without_changing_snapshot(self):
        name = "docs/product/PRD.md"
        path = self.root / name
        path.parent.mkdir(parents=True)
        path.write_text("Requirement UI-1", encoding="utf-8")
        first = self.observe(paths=[name])
        self.assertEqual("first_observation", first["impacts"][0]["reason"])
        self.assertEqual({"schema", "installed_digest", "documents"}, set(first["snapshot"]))
        path.write_text("Requirement UI-1 revised", encoding="utf-8")
        changed = self.observe(first["snapshot"], [name])["impacts"][0]
        self.assertEqual(name, changed["source"])
        self.assertIn("HiFi", changed["affected_artifacts"])
        self.assertIn("requirement-linked tests", changed["required_checks"])
        self.assertTrue(changed["semantic_review_required"])
        path.unlink()
        missing = self.observe(first["snapshot"], [name])["impacts"][0]
        self.assertEqual("missing_document", missing["reason"])

    def test_unknown_source_requires_parent_review(self):
        (self.root / "notes.md").write_text("A local rule", encoding="utf-8")
        impact = self.observe(paths=["notes.md"])["impacts"][0]
        self.assertEqual(["parent semantic review"], impact["affected_stages"])
        self.assertTrue(impact["semantic_review_required"])

    def test_default_inventory_observes_epics_and_retains_missing_paths(self):
        folder = self.root / "docs/epics"
        folder.mkdir(parents=True)
        epic = folder / "EPIC-1.md"
        epic.write_text("Current PRD: UI-1", encoding="utf-8")
        (folder / "archived").mkdir()
        (folder / "archived/old.md").write_text("history", encoding="utf-8")
        paths = default_inventory(self.root)
        self.assertIn("docs/epics/EPIC-1.md", paths)
        self.assertNotIn("docs/epics/archived/old.md", paths)
        observed = self.observe(paths=paths)
        epic.unlink()
        paths = default_inventory(self.root, observed["snapshot"])
        result = self.observe(observed["snapshot"], paths)
        self.assertIn({"kind": "missing_document", "path": "docs/epics/EPIC-1.md"}, result["findings"])

    def test_epic_discovery_rejects_linked_directory(self):
        with patch.object(Path, "is_symlink", lambda path: path == self.root / "docs/epics"):
            with self.assertRaises(ValueError):
                default_inventory(self.root)

    def test_removed_inventory_source_keeps_a_specific_impact(self):
        first = self.observe()["snapshot"]
        result = self.observe(first, ["CLAUDE.md"])
        self.assertIn({"kind": "removed_from_inventory", "path": "AGENTS.md"}, result["findings"])
        self.assertEqual("AGENTS.md", result["impacts"][0]["source"])
        self.assertEqual("removed_from_inventory", result["impacts"][0]["reason"])

    def test_explicit_nested_epic_does_not_expand_default_scope(self):
        folder = self.root / "docs/epics/team"
        folder.mkdir(parents=True)
        (folder / "E.md").write_text("nested source", encoding="utf-8")
        previous = self.observe(paths=["docs/epics/team/E.md"])["snapshot"]
        paths = default_inventory(self.root, previous)
        self.assertNotIn("docs/epics/team/E.md", paths)
        result = self.observe(previous, paths)
        self.assertEqual("removed_from_inventory", result["impacts"][0]["reason"])

    def test_epic_directory_enumeration_is_bounded_before_sorting(self):
        folder = self.root / "docs/epics"
        folder.mkdir(parents=True)
        for suffix in (".md", ".txt"):
            with self.subTest(suffix=suffix):
                entries = [type("Entry", (), {"path": str(folder / (str(i) + suffix))})() for i in range(129)]
                with patch("check_document_sync.os.scandir") as scan:
                    scan.return_value.__enter__.return_value = iter(entries)
                    with self.assertRaises(ValueError):
                        default_inventory(self.root)

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

    def test_retirement_catalog_is_quiet_but_actionable_references_still_warn(self):
        catalog = ("The installer retires `full-harness`, `prd-builder`, and "
                   "`product-design-builder`.")
        self.doc.write_text(catalog, encoding="utf-8")
        result = self.observe(self.observe()["snapshot"])
        self.assertFalse(any(row["kind"] == "legacy_pointer_review" for row in result["findings"]))

        for content in (
            catalog + "\nRun `full-harness` for the old stage.",
            catalog + "\nRead `skills/prd-builder/SKILL.md` for the old workflow.",
            "Installer retires [`full-harness`](skills/full-harness/SKILL.md).",
            "```shell\nrun `full-harness`\n```",
        ):
            with self.subTest(content=content):
                self.doc.write_text(content, encoding="utf-8")
                snapshot = self.observe()["snapshot"]
                result = self.observe(snapshot)
                self.assertTrue(any(row["kind"] == "legacy_pointer_review"
                                    for row in result["findings"]), result["findings"])

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
