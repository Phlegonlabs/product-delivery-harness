"""Heading links in skill Markdown must point at a rendered heading."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
ROOTS = (REPO_ROOT / "skills", REPO_ROOT / "standalone-skills")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
LINK = re.compile(r"\]\(([^)\s#]*)#([^)\s]+)\)")


def slug(heading: str) -> str:
    # GitHub: lowercase, drop punctuation except - and _, spaces become -.
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def rendered_lines(text: str):
    """Yield (line number, line) outside fenced code blocks."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            yield number, line


def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    seen: dict[str, int] = {}
    for _, line in rendered_lines(path.read_text(encoding="utf-8")):
        match = HEADING.match(line)
        if not match:
            continue
        base = slug(match.group(1))
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")
    return found


def broken_links(path: Path, root: Path = REPO_ROOT) -> list[str]:
    problems = []
    for number, line in rendered_lines(path.read_text(encoding="utf-8")):
        for match in LINK.finditer(line):
            target, fragment = match.groups()
            if target.startswith(("http://", "https://")):
                continue
            if target and not target.endswith(".md"):
                continue
            resolved = (path.parent / target).resolve() if target else path
            if not resolved.is_file():
                continue  # Missing files are a different check.
            if fragment.lower() not in anchors(resolved):
                problems.append(f"{path.relative_to(root).as_posix()}:{number}: {target}#{fragment}")
    return problems


class MarkdownAnchorLinkTests(unittest.TestCase):
    def test_heading_links_resolve(self) -> None:
        problems = [
            problem
            for root in ROOTS
            for path in sorted(root.rglob("*.md"))
            for problem in broken_links(path)
        ]
        self.assertEqual([], problems)

    def test_heading_inside_a_fence_is_not_an_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target.md"
            target.write_text(
                "# Real Heading\n\n```markdown\n## Fenced Heading\n```\n",
                encoding="utf-8",
            )
            source = Path(tmp) / "source.md"
            source.write_text(
                "[ok](target.md#real-heading) [dead](target.md#fenced-heading)\n",
                encoding="utf-8",
            )
            self.assertEqual({"real-heading"}, anchors(target))
            self.assertEqual(
                ["source.md:1: target.md#fenced-heading"],
                broken_links(source, Path(tmp)),
            )

    def test_slug_matches_github_for_dots_and_code(self) -> None:
        self.assertEqual("legacy-ui-contracts-before-059", slug("Legacy UI Contracts Before 0.59"))
        self.assertEqual("architecturemd", slug("`architecture.md`"))


if __name__ == "__main__":
    unittest.main()
