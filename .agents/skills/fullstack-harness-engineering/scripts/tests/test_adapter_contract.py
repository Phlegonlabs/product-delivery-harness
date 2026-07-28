import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = SKILL_ROOT.parent


def find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (
            (candidate / ".agents" / "plugins" / "marketplace.json").is_file()
            and (candidate / "scripts" / "sync_plugin_skills.py").is_file()
        ):
            return candidate
    return None


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)


class AdapterContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def read_sibling_skill(self, name: str) -> str:
        return (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")

    @unittest.skipIf(REPO_ROOT is None, "README contract requires a source checkout")

    def test_allowed_providers_alone_controls_current_host_eligibility(self) -> None:
        codex = self.read_sibling_skill("fullstack-harness-codex")
        claude = self.read_sibling_skill("fullstack-harness-claude-code")
        research = self.read("references/orchestration-research-notes.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")

        self.assertIn(
            "A PLAN node is selectable here when its `allowed_providers` includes `codex`",
            codex,
        )
        self.assertIn(
            "A PLAN node is selectable here when its `allowed_providers` includes `claude_code`",
            claude,
        )
        self.assertIn(
            "`preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Codex host",
            codex,
        )
        self.assertIn(
            "`preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Claude Code host",
            claude,
        )
        for content in (research, orchestration):
            self.assertIn(
                "eligible on the current host exactly when its `allowed_providers` includes that host",
                content,
            )
            self.assertIn(
                "`preferred_provider` is advisory ordering among allowed hosts and never blocks an otherwise allowed current host",
                content,
            )
        for content in (codex, claude, research, orchestration):
            self.assertNotIn("required or preferred provider", content)


if __name__ == "__main__":
    unittest.main()
