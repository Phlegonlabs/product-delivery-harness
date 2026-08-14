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
        pi = self.read_sibling_skill("fullstack-harness-pi")
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
            "A PLAN node is selectable here when its `allowed_providers` includes `pi`",
            pi,
        )
        self.assertIn(
            "`preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Codex host",
            codex,
        )
        self.assertIn(
            "`preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Claude Code host",
            claude,
        )
        self.assertIn(
            "`preferred_provider` is advisory ordering among allowed hosts; it never blocks the current Pi host",
            pi,
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
        for content in (codex, claude, pi, research, orchestration):
            self.assertNotIn("required or preferred provider", content)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_codex_uses_flat_parent_owned_delegation(self) -> None:
        codex = self.read_sibling_skill("fullstack-harness-codex")
        prompt = self.read_agent_prompt("fullstack-harness-codex")

        self.assertIn("Flat Parent-Owned Delegation", codex)
        self.assertIn("No worker or reviewer spawns another agent", codex)
        self.assertIn("sibling nodes dispatched by the Harness parent", codex)
        self.assertIn("fresh read-only reviewers", codex)
        self.assertIn("exact unified integration SHA", codex)
        self.assertIn("one planned broad final validation", codex)
        self.assertIn("dispatchable_nodes[].required_actions", codex)
        self.assertIn("RUN-v10 forbids task-local child agents", codex)
        self.assertIn("clean before launch", prompt)
        self.assertIn("workers and reviewers never create child agents", prompt)
        self.assertIn("fresh reviewers of the unified integration head", prompt)
        self.assertIn("one broad final validation", prompt)
        self.assertIn("Never replace requested top-level tasks", prompt)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_launch_and_review_actions_follow_each_dispatchable_node(self) -> None:
        codex = self.read_sibling_skill("fullstack-harness-codex")
        claude = self.read_sibling_skill("fullstack-harness-claude-code")
        pi = self.read_sibling_skill("fullstack-harness-pi")

        self.assertIn("dispatchable_nodes[].required_actions", codex)
        self.assertIn("dispatchable_nodes[].required_actions", claude)
        self.assertIn("dispatchable_nodes[].required_actions", pi)
        self.assertIn("Never infer extra authorization", claude)
        self.assertIn("Never infer extra authorization", pi)

        self.assertIn("an app-thread review needs `create_user_owned_tasks`", codex)
        self.assertIn("a direct-subagent review needs `spawn_subagents`", codex)
        self.assertNotIn("a read-only review node's required actions are only", codex)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_every_adapter_preserves_host_specific_context_discovery(self) -> None:
        codex = self.read_sibling_skill("fullstack-harness-codex")
        claude = self.read_sibling_skill("fullstack-harness-claude-code")
        pi = self.read_sibling_skill("fullstack-harness-pi")

        self.assertIn("Codex worker contract", codex)
        self.assertIn("`AGENTS.override.md`/`AGENTS.md` repository context paths", codex)
        self.assertIn("do not inject `CLAUDE.md` as Codex instructions", codex)
        self.assertIn("`AGENTS.md` context discovery enabled", codex)

        self.assertIn("Claude Code worker contract", claude)
        self.assertIn("effective `CLAUDE.md` repository context paths", claude)
        self.assertIn("shared `AGENTS.md` governance paths", claude)
        self.assertIn("Do not apply Codex or Pi worker mechanics", claude)

        self.assertIn("Pi worker contract", pi)
        self.assertIn("`AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`", pi)
        self.assertIn("when `AGENTS.md` exists do not also inject `CLAUDE.md`", pi)
        self.assertIn("Pi context discovery enabled", pi)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_same_repository_handoff_is_serialized_and_cross_machine_is_unsupported(self) -> None:
        for name, host in (
            ("fullstack-harness-codex", "Codex"),
            ("fullstack-harness-claude-code", "Claude Code"),
            ("fullstack-harness-pi", "Pi"),
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
    def test_pi_preserves_installed_role_and_model_routing(self) -> None:
        pi = self.read_sibling_skill("fullstack-harness-pi")
        prompt = self.read_agent_prompt("fullstack-harness-pi")

        self.assertIn("Pi owns role-to-model selection", pi)
        self.assertIn('`{"model": null, "reasoning_effort": null}`', pi)
        self.assertIn("`frontend_designer` role", pi)
        self.assertIn("`worker` role", pi)
        self.assertIn("`reviewer` role", pi)
        self.assertIn("actual resolved role, model, fallback, run id", pi)
        self.assertIn("Forked subagent context requires a persisted Pi parent session", pi)
        self.assertIn("With `--no-session`, launch a fresh child context instead", pi)
        self.assertIn("never pass `--no-context-files` or `-nc`", pi)
        self.assertIn("Pi's effective per-directory context selection", pi)
        self.assertIn("One mission has one writer", pi)
        self.assertIn("A Pi child must not delegate again", pi)
        self.assertIn("installed Pi role and model configuration", prompt)

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
