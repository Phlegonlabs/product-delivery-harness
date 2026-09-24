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
                       "do not prove translation quality", "English source first",
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

    def write_pair(self, source, review):
        self.source.write_text(source, encoding="utf-8")
        self.write_review(review)

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

    def test_missing_heading_table_and_numeric_coverage_is_rejected(self):
        self.write_pair(
            "# Product\n## Service Level\nTarget: 95% within 2 days and 120 ms.\n"
            "| Signal | Target |\n| --- | --- |\n| Latency | 120 ms |\n"
            "## Recovery\nRestore within 4 hours.\n",
            "# 產品\n## 服務水準\n目標：95% 於 2 days 內。\n",
        )
        errors = validate_pair(self.source, self.review)
        joined = "\n".join(errors)
        self.assertIn("missing heading-level coverage: H2: 1", joined)
        self.assertIn("missing table-shape coverage: 1 table(s) with 2 columns and 1 data rows", joined)
        self.assertIn("missing numeric-literal coverage", joined)
        self.assertIn("'120 ms'", joined)
        self.assertIn("'4 hours'", joined)

    def test_translated_reordered_headings_and_tables_pass_structural_coverage(self):
        self.write_pair(
            "# Product\n## Service Level\nTarget: 95% within 2 days and 120 ms.\n"
            "| Signal | Target |\n| --- | --- |\n| Latency | 120 ms |\n"
            "## Recovery\nRestore within 4 hours.\n"
            "| Mode | Result |\n| --- | --- |\n| Retry | 3 attempts |\n",
            "# 產品\n## 復原\n4 hours 內還原。\n"
            "| 模式 | 結果 |\n| --- | --- |\n| 重試 | 3 attempts |\n"
            "## 服務水準\n目標：95% 於 2 days 內，120 ms。\n"
            "| 指標 | 目標 |\n| --- | --- |\n| 延遲 | 120 ms |\n",
        )
        self.assertEqual([], validate_pair(self.source, self.review))

    def test_fenced_headings_and_tables_do_not_add_coverage_requirements(self):
        self.write_pair(
            "# Product\n```markdown\n## Example\n| A | B |\n| --- | --- |\n| x | y |\n```\n",
            "# 產品\n",
        )
        self.assertEqual([], validate_pair(self.source, self.review))

    def test_numeric_coverage_ignores_trace_ids_urls_and_digests(self):
        digest = "a" * 64
        self.write_pair(
            f"# Product\nPRD-001 target 95%. URL https://example.test/v3. Approval sha256:{digest}.\n",
            "# 產品\nPRD-001 目標 95%。\n",
        )
        errors = validate_pair(self.source, self.review)
        self.assertFalse(any("numeric-literal coverage" in error for error in errors), errors)

    def test_numeric_counts_with_unit_names_pass_without_unit_obligation(self):
        self.write_pair(
            "# Product\nThe platform runs 3 services and sends 2 monthly reports.\n",
            "# 產品\n平台運行 3 個服務，並寄送 2 份月報。\n",
        )
        self.assertEqual([], validate_pair(self.source, self.review))

    def test_changed_ms_literal_is_rejected(self):
        self.write_pair(
            "# Product\nStartup takes 200 ms.\n",
            "# 產品\n啟動需 250 ms。\n",
        )
        errors = validate_pair(self.source, self.review)
        self.assertTrue(any("missing numeric-literal coverage: '200 ms' x1" in error for error in errors), errors)

    def test_identifier_prefix_cannot_satisfy_a_shorter_numeric_target(self):
        self.write_pair(
            "# Product\nMaximum: 20 accounts.\n",
            "# 產品\n上限：200msomething。\n",
        )
        errors = validate_pair(self.source, self.review)
        self.assertTrue(any("missing numeric-literal coverage: '20' x1" in error for error in errors), errors)

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
