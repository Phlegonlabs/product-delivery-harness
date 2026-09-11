import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from configure_project_context import configure_context  # noqa: E402


SCRIPT = SCRIPTS_DIR / "configure_project_context.py"


class ConfigureProjectContextTests(unittest.TestCase):
    def make_templates(self, root: Path) -> tuple[Path, Path]:
        agents_template = root / "agents-template.md"
        claude_template = root / "claude-template.md"
        agents_template.write_text(
            "# Shared Rules\n\n- Verify changes.\n", encoding="utf-8"
        )
        claude_template.write_text(
            "# Claude Rules\n\n@AGENTS.md\n\n- Use Claude workers.\n",
            encoding="utf-8",
        )
        return agents_template, claude_template

    def test_both_missing_receive_distinct_host_templates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_templates(root)

            result = configure_context(root, agents_template, claude_template)

            self.assertEqual(["AGENTS.md", "CLAUDE.md"], result["created"])
            self.assertEqual(agents_template.read_bytes(), (root / "AGENTS.md").read_bytes())
            self.assertEqual(claude_template.read_bytes(), (root / "CLAUDE.md").read_bytes())
            self.assertNotEqual(
                (root / "AGENTS.md").read_bytes(), (root / "CLAUDE.md").read_bytes()
            )

    def test_existing_agents_is_preserved_and_claude_uses_its_own_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_templates(root)
            agents = root / "AGENTS.md"
            agents.write_text("# Existing Agents\n", encoding="utf-8")

            result = configure_context(root, agents_template, claude_template)

            self.assertEqual(["CLAUDE.md"], result["created"])
            self.assertEqual("# Existing Agents\n", agents.read_text(encoding="utf-8"))
            self.assertEqual(
                claude_template.read_bytes(), (root / "CLAUDE.md").read_bytes()
            )
            self.assertIn("@AGENTS.md", (root / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_existing_claude_is_preserved_and_agents_uses_its_own_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_templates(root)
            claude = root / "CLAUDE.md"
            claude.write_text("# Existing Claude\n", encoding="utf-8")

            result = configure_context(root, agents_template, claude_template)

            self.assertEqual(["AGENTS.md"], result["created"])
            self.assertEqual("# Existing Claude\n", claude.read_text(encoding="utf-8"))
            self.assertEqual(
                agents_template.read_bytes(), (root / "AGENTS.md").read_bytes()
            )

    def test_existing_pair_is_never_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_templates(root)
            agents = root / "AGENTS.md"
            claude = root / "CLAUDE.md"
            agents.write_text("agents\n", encoding="utf-8")
            claude.write_text("claude\n", encoding="utf-8")

            result = configure_context(root, agents_template, claude_template)

            self.assertEqual([], result["created"])
            self.assertEqual("agents\n", agents.read_text(encoding="utf-8"))
            self.assertEqual("claude\n", claude.read_text(encoding="utf-8"))

    def test_check_mode_is_read_only_and_reports_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root), "--check"],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(1, result.returncode)
            self.assertIn('"AGENTS.md"', result.stdout)
            self.assertIn('"CLAUDE.md"', result.stdout)
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertFalse((root / "CLAUDE.md").exists())


if __name__ == "__main__":
    unittest.main()
