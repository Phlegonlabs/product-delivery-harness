"""Lifecycle summaries preserve unrelated pages and create no approval authority."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from design_workflow import read_scope, report


class WorkflowTests(unittest.TestCase):
    def test_maintenance_does_not_request_design_regeneration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", str(root)], capture_output=True, check=True, timeout=15)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                            "commit", "--allow-empty", "-m", "synthetic test"], capture_output=True, check=True, timeout=15)
            (root / "docs").mkdir()
            (root / "docs/goal").mkdir()
            (root / "docs/goal/PLAN.md").write_text("plan presence", encoding="utf-8")
            (root / "docs/goal/RUN.md").write_text("run presence", encoding="utf-8")
            (root / "docs/task.md").write_text(
                "Design workflow: maintenance\nUI impact: none\n- [ ] Verify current product\n", encoding="utf-8")
            result = report(root, "docs/task.md")
            self.assertFalse(result["designRequired"])
            self.assertEqual("none", result["uiImpact"])
            self.assertEqual(["docs/goal/PLAN.md", "docs/goal/RUN.md"], result["activeTaskFiles"])
            self.assertEqual("presence_only", result["taskFileObservation"])
            self.assertIn("does not establish an active RUN or live process", result["meaning"])
            self.assertEqual("Verify current product", result["next"])
            self.assertNotIn("approval", result)

    def test_maintenance_structure_requires_design_and_reports_inconsistency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", str(root)], capture_output=True, check=True, timeout=15)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                            "commit", "--allow-empty", "-m", "synthetic test"], capture_output=True, check=True, timeout=15)
            (root / "docs").mkdir()
            (root / "docs/task.md").write_text(
                "Design workflow: maintenance\nUI impact: structure\n", encoding="utf-8")
            result = report(root, "docs/task.md")
            self.assertEqual("structure", result["uiImpact"])
            self.assertTrue(result["designRequired"])
            self.assertTrue(any("must use the affected design gates" in item for item in result["findings"]))

    def test_maintenance_missing_or_fenced_impact_is_unknown_and_conservative(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", str(root)], capture_output=True, check=True, timeout=15)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                            "commit", "--allow-empty", "-m", "synthetic test"], capture_output=True, check=True, timeout=15)
            (root / "docs").mkdir()
            record = root / "docs/task.md"
            record.write_text("Design workflow: maintenance\n", encoding="utf-8")
            missing = report(root, "docs/task.md")
            self.assertEqual("unknown", missing["uiImpact"])
            self.assertTrue(missing["designRequired"])
            self.assertTrue(any("requires exactly one UI impact" in item for item in missing["findings"]))
            record.write_text("Design workflow: maintenance\n```text\nUI impact: none\n```\n", encoding="utf-8")
            fenced = report(root, "docs/task.md")
            self.assertEqual("unknown", fenced["uiImpact"])
            self.assertTrue(fenced["designRequired"])

    def test_enhancement_requires_scope_and_detects_preserved_change(self):
        with self.assertRaises(ValueError):
            read_scope("Design workflow: enhancement")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", str(root)], capture_output=True, check=True, timeout=15)
            (root / "docs").mkdir()
            (root / "docs/home.html").write_text("baseline", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "docs/home.html"], capture_output=True, check=True, timeout=15)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                            "commit", "-m", "synthetic test"], capture_output=True, check=True, timeout=15)
            (root / "docs/task.md").write_text("Design workflow: enhancement\n### UI Change Scope\n"
                "| Disposition | Path | Reason / consumers |\n| --- | --- | --- |\n"
                "| preserved | docs/home.html | Unaffected home |\n", encoding="utf-8")
            self.assertEqual([], report(root, "docs/task.md")["findings"])
            (root / "docs/home.html").write_text("Unexpected redesign", encoding="utf-8")
            self.assertIn("preserved page changed", report(root, "docs/task.md")["findings"][0])

    def test_conflicting_route_and_duplicate_scope_fail(self):
        with self.assertRaises(ValueError):
            read_scope("Design workflow: maintenance\nDesign workflow: enhancement")
        with self.assertRaises(ValueError):
            read_scope("Design workflow: enhancement\n### UI Change Scope\n"
                       "| changed | docs/a.html | new region |\n| preserved | docs/a.html | none |")

    def test_fenced_maintenance_example_is_not_a_task_classification(self):
        with self.assertRaises(ValueError):
            read_scope("```markdown\nDesign workflow: maintenance\n```\n")


if __name__ == "__main__":
    unittest.main()
