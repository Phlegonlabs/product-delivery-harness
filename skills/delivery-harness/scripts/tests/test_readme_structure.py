import re
import unittest
from pathlib import Path


REPO_ROOT = next(
    (path for path in Path(__file__).resolve().parents
     if (path / "package.json").is_file() and (path / "README.md").is_file()),
    None,
)
READMES = ("README.md", "README.zh-TW.md", "README.zh-CN.md", "README.es.md")


@unittest.skipIf(REPO_ROOT is None, "README contract requires a source checkout")
class ReadmeStructureTests(unittest.TestCase):
    def profile(self, content: str) -> tuple[list[int], int]:
        headings = [len(match.group(1)) for match in re.finditer(r"^(#{1,6})\s+\S", content, re.M)]
        fences = sum(line.startswith("```") for line in content.splitlines())
        self.assertEqual(fences % 2, 0, "unclosed Markdown fence")
        return headings, fences // 2

    def test_translations_preserve_structure_without_line_count_lock(self) -> None:
        english = self.profile((REPO_ROOT / "README.md").read_text(encoding="utf-8"))
        for name in READMES:
            with self.subTest(readme=name):
                content = (REPO_ROOT / name).read_text(encoding="utf-8")
                self.assertLess(len(content.splitlines()), 300)
                self.assertEqual(self.profile(content), english)

    def test_readmes_keep_five_recent_entries_and_link_the_shared_history(self) -> None:
        version = (REPO_ROOT / "skills/delivery-harness/VERSION").read_text().strip()
        self.assertTrue((REPO_ROOT / "CHANGELOG.md").is_file())
        for name in READMES:
            with self.subTest(readme=name):
                content = (REPO_ROOT / name).read_text(encoding="utf-8")
                versions = re.findall(r"^- \*\*(\d+\.\d+\.\d+)\*\* ", content, re.M)
                self.assertEqual(len(versions), 5)
                self.assertEqual(versions[0], version)
                self.assertIn("](CHANGELOG.md)", content)
                self.assertNotIn("docs/WORKFLOW.zh-TW.md", content)
                self.assertNotIn("install.ps1", content)

    def test_output_tables_and_mermaid_keep_valid_shapes(self) -> None:
        for name in READMES:
            with self.subTest(readme=name):
                content = (REPO_ROOT / name).read_text(encoding="utf-8")
                for line in content.splitlines():
                    if line.startswith("|") and line.count("|") >= 4:
                        self.assertNotRegex(line.split("|")[-2], r"(?:^|,\s*)`RUN\.md`(?:\s*,|$)")
                for block in re.findall(r"```mermaid\n(.*?)```", content, re.S):
                    self.assertEqual(block.count("{"), block.count("}"), "unbalanced Mermaid braces")


if __name__ == "__main__":
    unittest.main()
