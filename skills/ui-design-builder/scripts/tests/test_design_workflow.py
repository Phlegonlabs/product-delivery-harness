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
            (root / "docs/task.md").write_text("Design workflow: maintenance\n- [ ] Verify current product\n", encoding="utf-8")
            result = report(root, "docs/task.md")
            self.assertFalse(result["designRequired"])
            self.assertEqual("Verify current product", result["next"])
            self.assertNotIn("approval", result)

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
