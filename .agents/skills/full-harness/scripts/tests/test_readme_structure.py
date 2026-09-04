import re
import unittest
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (
            (candidate / ".agents" / "skills" / "full-harness" / "SKILL.md").is_file()
            and (candidate / "package.json").is_file()
        ):
            return candidate
    return None


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)


class ReadmeStructureTests(unittest.TestCase):
    def structure_profile(self, path: Path) -> dict[str, object]:
        lines = path.read_text(encoding="utf-8").splitlines()
        headings = [
            (index, len(match.group(1)))
            for index, line in enumerate(lines)
            if (match := re.match(r"^(#{1,6})\s+\S", line))
        ]
        fence_lines = sum(1 for line in lines if line.startswith("```"))
        self.assertEqual(fence_lines % 2, 0, f"unclosed fence in {path.name}")

        section_starts = [0, *(index for index, _level in headings)]
        section_counts = []
        for section_index, start in enumerate(section_starts):
            end = (
                section_starts[section_index + 1]
                if section_index + 1 < len(section_starts)
                else len(lines)
            )
            body = lines[start:end]
            if section_index:
                body = body[1:]
            section_counts.append(
                (
                    sum(bool(line.strip()) for line in body),
                    sum(
                        bool(re.match(r"^\s*(?:[-*+] |\d+\. )", line))
                        for line in body
                    ),
                )
            )

        return {
            "heading_order_and_levels": [level for _index, level in headings],
            "fenced_code_blocks": fence_lines // 2,
            "section_nonblank_and_bullet_counts": section_counts,
        }

    @unittest.skipIf(REPO_ROOT is None, "README contract requires a source checkout")
    def test_translations_preserve_english_structure(self) -> None:
        english = self.structure_profile(REPO_ROOT / "README.md")
        for translation in ("README.zh-CN.md", "README.zh-TW.md"):
            with self.subTest(translation=translation):
                self.assertEqual(
                    self.structure_profile(REPO_ROOT / translation),
                    english,
                )

    @unittest.skipIf(REPO_ROOT is None, "README contract requires a source checkout")
    def test_readme_outputs_have_no_standalone_run_and_mermaid_braces_close(self) -> None:
        for filename in ("README.md", "README.zh-CN.md", "README.zh-TW.md"):
            content = (REPO_ROOT / filename).read_text(encoding="utf-8")
            with self.subTest(readme=filename):
                for line in content.splitlines():
                    if line.startswith("|") and line.count("|") >= 4:
                        output_cell = line.split("|")[-2]
                        self.assertNotRegex(output_cell, r"(?:^|,\s*)`RUN\.md`(?:\s*,|$)")
                for block in re.findall(r"```mermaid\n(.*?)```", content, flags=re.DOTALL):
                    self.assertEqual(block.count("{"), block.count("}"), "unbalanced Mermaid braces")

    @unittest.skipIf(REPO_ROOT is None, "README contract requires a source checkout")
    def test_runtime_handoff_graph_profiles_and_zero_to_one_are_aligned(self) -> None:
        for filename in ("README.md", "README.zh-CN.md", "README.zh-TW.md"):
            content = (REPO_ROOT / filename).read_text(encoding="utf-8")
            with self.subTest(readme=filename):
                for required in (
                    "Zero-to-one",
                    "PLAN/RUN",
                    "same-repository",
                    "cross-machine",
                    "active host",
                    "RUN.active_wave.status",
                    "Host A",
                    "Host B",
                    "exact SHA",
                    "`runtime_unavailable`",
                    "homogeneous `tool_profile`",
                    "permission-level tool removal",
                ):
                    self.assertIn(required, content)
                self.assertIn("fresh reviewers", content)
                self.assertRegex(content, r"(?i)(never delegate|不能再次分派|不能再次分派)")
                self.assertRegex(content, r"(?i)exact-head[^\n]*review")
                self.assertNotIn("omits write-capable tools", content)
                self.assertNotIn("blocked on provider mismatch", content)
                self.assertNotIn("allowlist", content.lower())
                self.assertNotIn("白名单", content)
                self.assertNotIn("允許清單", content)


if __name__ == "__main__":
    unittest.main()
