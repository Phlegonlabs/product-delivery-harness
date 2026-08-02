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

    def read_agent_prompt(self, name: str) -> str:
        return (SKILLS_ROOT / name / "agents" / "openai.yaml").read_text(encoding="utf-8")

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

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_codex_nested_helpers_are_optional_but_exact_head_review_is_mandatory(self) -> None:
        codex = self.read_sibling_skill("fullstack-harness-codex")
        prompt = self.read_agent_prompt("fullstack-harness-codex")

        self.assertIn("Nested Read-Only Helpers (Optional)", codex)
        self.assertIn("Nested helpers are optional", codex)
        self.assertIn("optional at the policy level", codex)
        self.assertIn("An omitted or disabled `nested_subagent_policy` runs with no helper", codex)
        self.assertIn("must launch its task-local reviewer child", codex)
        self.assertIn("other helper lanes remain optional", codex)
        self.assertIn("dispatchable_nodes[].required_actions", codex)
        self.assertIn("Outer app-task nodes follow that directive exactly", codex)
        self.assertIn("separately verify an exact `spawn_subagents` grant", codex)
        self.assertIn("grant covering the `worker:<id>` target", codex)
        self.assertNotIn("run-wide `*`", codex)
        self.assertNotIn("explicitly run-wide", codex)
        self.assertIn("selector's outer `required_actions` does not grow", codex)
        self.assertIn("terminal `review_workers[]` PASS", codex)
        self.assertIn("absence of a nested helper never lowers the gate", codex)
        self.assertNotIn("Every non-trivial app-task mission gets", codex)
        self.assertNotIn("Each task runs its own read-only Multi-agent reviewer", prompt)
        self.assertIn("Nested read-only helpers are optional", prompt)
        self.assertIn("optional at the policy level", prompt)
        self.assertIn("omit or disable the policy to run with no helper", prompt)
        self.assertIn("must launch its reviewer child", prompt)
        self.assertIn("other helper lanes remain optional", prompt)
        self.assertIn("outer task follows its required_actions exactly", prompt)
        self.assertIn("immediately before a child launch", prompt)
        self.assertIn("policy is disabled", prompt)
        self.assertIn("terminal exact-head PASS", prompt)
        self.assertIn("Never replace requested top-level tasks", prompt)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_launch_and_review_actions_follow_each_dispatchable_node(self) -> None:
        codex = self.read_sibling_skill("fullstack-harness-codex")
        claude = self.read_sibling_skill("fullstack-harness-claude-code")

        self.assertIn("dispatchable_nodes[].required_actions", codex)
        self.assertIn("dispatchable_nodes[].required_actions", claude)
        self.assertIn("Never infer extra authorization", claude)

        self.assertIn("an app-thread review needs `create_user_owned_tasks`", codex)
        self.assertIn("a direct-subagent review needs `spawn_subagents`", codex)
        self.assertNotIn("a read-only review node's required actions are only", codex)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_same_repository_handoff_is_serialized_and_cross_machine_is_unsupported(self) -> None:
        for name, host in (
            ("fullstack-harness-codex", "Codex"),
            ("fullstack-harness-claude-code", "Claude Code"),
        ):
            content = self.read_sibling_skill(name)
            with self.subTest(adapter=name):
                self.assertIn("Serialized Same-Repository Host Handoff", content)
                self.assertIn("Host A must close the active wave", content)
                self.assertIn("`RUN.active_wave.status` is neither `active` nor `proposed`", content)
                self.assertIn("The `active_wave` object remains part of RUN", content)
                self.assertIn("canonical PLAN/RUN and graph state", content)
                self.assertIn("current exact head SHA", content)
                self.assertIn(f"Host B re-probes the current {host} runtime", content)
                self.assertIn("If that review returns `fix_required`", content)
                self.assertIn("the old review is invalid", content)
                self.assertIn("Cross-machine handoff is unsupported until a future schema", content)
                self.assertIn("not an in-session bridge", content)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_claude_graph_workflow_splits_mixed_frontiers_by_tool_profile(self) -> None:
        claude = self.read_sibling_skill("fullstack-harness-claude-code")
        prompt = self.read_agent_prompt("fullstack-harness-claude-code")

        self.assertIn("homogeneous `tool_profile`", claude)
        self.assertIn("Each group gets its own bounded call", claude)
        self.assertIn("never put a `mission_write` node beside a `code_review_readonly`", claude)
        self.assertIn("Do not mix tool profiles", claude)
        self.assertIn("permission-level tool removal", claude)
        self.assertNotIn("omits write-capable tools", claude)
        self.assertIn("homogeneous tool_profile groups", prompt)
        self.assertIn("never mix write missions with read-only reviews in one call", prompt)


if __name__ == "__main__":
    unittest.main()
