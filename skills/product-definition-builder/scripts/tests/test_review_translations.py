import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from check_review_translations import validate_pair


class ReviewTranslationTests(unittest.TestCase):
    def test_contract_reaches_drafting_review_publication_and_handoff(self):
        root = SCRIPTS.parent
        for path in ("SKILL.md", "references/output-contract.md", "references/artifact-lifecycle.md",
                     "references/architecture-playbook.md", "references/agent-work-graph.md"):
            self.assertIn("bilingual-review.md", (root / path).read_text(encoding="utf-8"))
        contract = (root / "references/bilingual-review.md").read_text(encoding="utf-8")
        for phrase in ("English files alone are canonical", "before every owner review",
                       "does not prove translation quality", "English source first",
                       "after writing approval metadata", "archive each English/review pair together",
                       "Existing English-only Documents", "same directory", "Create missing copies exclusively",
                       "Preserve the English bytes", "read-only task"):
            self.assertIn(phrase.lower(), contract.lower())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "PRD.md"
        self.review = self.root / "PRD.zh-TW.md"
        self.source.write_text("# Product\nPRD-001: Save a draft. TEST-001 verifies it.\n", encoding="utf-8")
        self.write_review()

    def write_review(self, body="# 產品\nPRD-001：儲存草稿。TEST-001 驗證此行為。\n", name="PRD.md"):
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.review.write_text(f"<!-- review-source: {name} sha256:{digest} -->\n{body}", encoding="utf-8")

    def test_matching_pair_is_read_only(self):
        before = (self.source.read_bytes(), self.review.read_bytes())
        self.assertEqual([], validate_pair(self.source, self.review))
        self.assertEqual(before, (self.source.read_bytes(), self.review.read_bytes()))

    def test_english_change_invalidates_review_even_with_same_ids(self):
        self.source.write_text(self.source.read_text(encoding="utf-8").replace("Save", "Delete"), encoding="utf-8")
        self.assertTrue(any("stale review" in error for error in validate_pair(self.source, self.review)))

    def test_missing_and_extra_ids_are_rejected(self):
        self.write_review("PRD-002：草稿。TEST-001\n")
        errors = validate_pair(self.source, self.review)
        self.assertTrue(any("missing trace IDs: PRD-001" in error for error in errors))
        self.assertTrue(any("extra trace IDs: PRD-002" in error for error in errors))

    def test_wrong_source_and_duplicate_marker_are_rejected(self):
        self.write_review(name="architecture.md")
        self.assertTrue(any("filename" in error for error in validate_pair(self.source, self.review)))
        self.review.write_text(self.review.read_text(encoding="utf-8") * 2, encoding="utf-8")
        self.assertTrue(any("exactly one" in error for error in validate_pair(self.source, self.review)))

    def test_missing_and_same_file_are_rejected(self):
        self.assertTrue(validate_pair(self.source, self.root / "missing.md"))
        self.assertTrue(validate_pair(self.source, self.source))

    def test_cli_accepts_legacy_prd_without_architecture(self):
        command = [sys.executable, str(SCRIPTS / "check_review_translations.py"),
                   "--prd", str(self.source)]
        before = self.source.read_bytes()
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(before, self.source.read_bytes())
        self.review.unlink()
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(1, result.returncode)
        result = subprocess.run(command + ["--architecture-review", str(self.root / "orphan.md")],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(2, result.returncode)

    def test_cli_requires_companions_for_every_supplied_source(self):
        architecture = self.root / "architecture.md"
        architecture.write_text("# Architecture\nARCH-001: Local persistence.\n", encoding="utf-8")
        command = [sys.executable, str(SCRIPTS / "check_review_translations.py"),
                   "--prd", str(self.source), "--architecture", str(architecture)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(1, result.returncode)
        digest = hashlib.sha256(architecture.read_bytes()).hexdigest()
        (self.root / "architecture.zh-TW.md").write_text(
            f"<!-- review-source: architecture.md sha256:{digest} -->\n# 架構\nARCH-001：本地持久化。\n",
            encoding="utf-8")
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
