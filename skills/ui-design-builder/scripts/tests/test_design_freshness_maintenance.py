"""Maintenance keeps historical design drift separate from current blockers."""

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_design_freshness as freshness


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MaintenanceFreshnessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.skill = "a" * 64
        self.product = self.root / "docs/product/PRD.md"
        self.design = self.root / "docs/design/wireframes.html"
        self.home = self.root / "docs/home.html"
        self.record = self.root / "docs/epics/EPIC-maintenance.md"
        for path, content in ((self.product, "Accepted product"), (self.design, "Historical design"),
                              (self.home, "Preserved home"),
                              (self.record, "Design workflow: maintenance\nUI impact: style\n"
                               "### UI Change Scope\n| Disposition | Path | Reason / consumers |\n"
                               "| --- | --- | --- |\n| preserved | docs/home.html | Unaffected page |\n")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        self.baseline = self.root / "baseline.json"
        self.baseline.write_text(json.dumps({
            "schema": "design-observation/1", "skillDigest": self.skill,
            "implementation": "not_started", "implementationEvidence": "No implementation task started in this fixture",
            "artifacts": [{"path": "docs/design/wireframes.html", "sha256": digest(self.design),
                           "inputs": [{"path": "docs/product/PRD.md", "sha256": digest(self.product)}]}],
        }), encoding="utf-8")
        for arguments in (("init", "-q"), ("config", "core.autocrlf", "false"),
                          ("add", "docs/home.html", "docs/epics/EPIC-maintenance.md"),
                          ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                           "commit", "-qm", "Synthetic baseline")):
            subprocess.run(["git", *arguments], cwd=self.root, check=True, capture_output=True, timeout=15)

    def invoke(self, loaded=None):
        arguments = ["check_design_freshness.py", "--repo-root", str(self.root),
                     "--baseline", str(self.baseline), "--skills-root", str(self.root),
                     "--task-record", "docs/epics/EPIC-maintenance.md"]
        if loaded is not None:
            arguments.extend(("--loaded-digest", loaded))
        output = io.StringIO()
        with patch.object(sys, "argv", arguments), patch.object(freshness, "contract_digest", return_value=self.skill):
            with redirect_stdout(output):
                result = freshness.main()
        return result, json.loads(output.getvalue())

    def test_unknown_loaded_skill_remains_review_required(self):
        code, report = self.invoke()
        self.assertEqual(1, code)
        self.assertEqual("review_required", report["status"])
        self.assertIn("skill_identity_unknown", report["findings"])

    def test_restart_and_preserved_scope_failure_remain_blocking(self):
        code, report = self.invoke("b" * 64)
        self.assertEqual(1, code)
        self.assertIn("restart_required", report["findings"])
        self.home.write_text("Unexpected change", encoding="utf-8")
        code, report = self.invoke(self.skill)
        self.assertEqual(1, code)
        self.assertEqual("review_required", report["status"])
        self.assertIn("workflow: preserved page changed", "\n".join(report["findings"]))

    def test_only_historical_product_source_drift_is_nonblocking(self):
        self.product.write_text("Accepted current product wording", encoding="utf-8")
        code, report = self.invoke(self.skill)
        self.assertEqual(0, code)
        self.assertEqual("historical_design_observed", report["status"])
        self.assertEqual("historical", report["artifacts"][0]["status"])
        self.design.write_text("Changed design bytes", encoding="utf-8")
        code, report = self.invoke(self.skill)
        self.assertEqual(1, code)
        self.assertEqual("review_required", report["status"])


if __name__ == "__main__":
    unittest.main()
