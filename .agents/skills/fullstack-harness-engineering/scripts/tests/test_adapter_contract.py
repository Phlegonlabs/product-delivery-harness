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
        self.assertIn("RUN-v11 forbids task-local child agents", codex)
        self.assertIn("probe app-task and subagent surfaces", prompt)
        self.assertIn("keep all workers and reviewers flat and parent-owned", prompt)
        self.assertIn("Never replace explicitly requested independent app tasks", codex)

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

        self.assertIn("A review app task needs `create_user_owned_tasks`", codex)
        self.assertIn("a direct-subagent review needs `spawn_subagents`", codex)
        self.assertNotIn("a read-only review node's required actions are only", codex)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_every_adapter_preserves_host_specific_context_discovery(self) -> None:
        codex = self.read_sibling_skill("fullstack-harness-codex")
        claude = self.read_sibling_skill("fullstack-harness-claude-code")
        pi = self.read_sibling_skill("fullstack-harness-pi")

        self.assertIn("Codex worker contract", codex)
        self.assertIn("`AGENTS.override.md` / `AGENTS.md` repository context paths", codex)
        self.assertIn("do not inject `CLAUDE.md` as Codex instructions", codex)
        self.assertIn("`AGENTS.md` context discovery enabled", codex)

        self.assertIn("Claude Code worker contract", claude)
        self.assertIn("effective `CLAUDE.md` repository context paths", claude)
        self.assertIn("shared `AGENTS.md` governance paths", claude)
        self.assertIn("Do not apply Codex or Pi worker mechanics", claude)

        self.assertIn("Pi worker contract", pi)
        self.assertIn("`AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`", pi)
        self.assertIn("When `AGENTS.md` exists do not also inject `CLAUDE.md`", pi)
        self.assertIn("Pi context discovery enabled", pi)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_every_adapter_uses_fresh_context_terminal_events_and_runtime_metrics(self) -> None:
        codex = self.read_sibling_skill("fullstack-harness-codex")
        claude = self.read_sibling_skill("fullstack-harness-claude-code")
        pi = self.read_sibling_skill("fullstack-harness-pi")

        for name, content in (("codex", codex), ("claude", claude), ("pi", pi)):
            with self.subTest(adapter=name):
                self.assertIn("bounded context packet", content)
                self.assertIn("runtime_metrics", content)
                self.assertIn("pre-integration review", content)
                self.assertIn("fresh", content)

        self.assertIn("cursor-based `wait_threads`", codex)
        self.assertIn("Do not repeatedly read unchanged tasks", codex)
        self.assertIn("`pipeline()` / `agent_result` terminal output", claude)
        self.assertIn("Subscribe or block on terminal child/status events", pi)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_every_adapter_applies_the_shared_runtime_upgrade_gate(self) -> None:
        codex = self.read_sibling_skill("fullstack-harness-codex")
        claude = self.read_sibling_skill("fullstack-harness-claude-code")
        pi = self.read_sibling_skill("fullstack-harness-pi")

        for name, content in (("codex", codex), ("claude", claude), ("pi", pi)):
            with self.subTest(adapter=name):
                self.assertIn("runtime_adapter.version_gate", content)
                self.assertIn("runtime-upgrades.md", content)
                self.assertIn("compatible_old", content)
                self.assertIn("restart_required", content)

        self.assertIn("fresh top-level task", codex)
        self.assertIn("`/reload-plugins` or restart Claude Code", claude)
        self.assertIn("Never overwrite standalone skills", pi)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_same_repository_handoff_is_serialized_and_cross_machine_is_unsupported(self) -> None:
        state = self.read("references/execution-state-model.md")
        self.assertIn("Serialized Same-Repository Host Handoff", state)
        self.assertIn("Host A must close the active wave", state)
        self.assertIn("`RUN.active_wave.status` is neither `active` nor `proposed`", state)
        self.assertIn("The `active_wave` object remains part of RUN", state)
        self.assertIn("canonical PLAN/RUN and graph state", state)
        self.assertIn("current exact head SHA", state)
        self.assertIn("then re-probe its own runtime", state)
        self.assertIn("If Host B's review returns `fix_required`", state)
        self.assertIn("the old review is invalid", state.lower())
        self.assertIn("Cross-machine handoff is unsupported until a future schema", state)
        self.assertIn("not an in-session bridge", state)

        for name in (
            "fullstack-harness-codex",
            "fullstack-harness-claude-code",
            "fullstack-harness-pi",
        ):
            content = self.read_sibling_skill(name)
            with self.subTest(adapter=name):
                self.assertIn("Serialized Same-Repository Host Handoff", content)
                self.assertIn("references/execution-state-model.md", content)
                self.assertIn("This adapter adds no alternate state or handoff rules", content)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_pi_preserves_installed_role_and_model_routing(self) -> None:
        pi = self.read_sibling_skill("fullstack-harness-pi")
        prompt = self.read_agent_prompt("fullstack-harness-pi")

        self.assertIn("Pi owns role-to-model and fallback selection", pi)
        self.assertIn("`provider_options.pi.model` null", pi)
        self.assertIn("role-aware Pi launch surface", pi)
        self.assertIn("generic `agents.spawn` surface", pi)
        self.assertIn("lacks a Pi role selector, it does not satisfy this capability", pi)
        self.assertIn("Omit `model` from the Pi launch call", pi)
        self.assertIn("Do not manually respawn the node on another model or provider", pi)
        self.assertIn("PLAN may lower or raise reasoning effort per node", pi)
        self.assertIn("per-run thinking suffix", pi)
        self.assertIn("`medium` for bounded discovery", pi)
        self.assertIn("`high` for general implementation", pi)
        self.assertIn("`xhigh` only for a justified high-risk or unified final synthesis", pi)
        self.assertIn("`frontend_designer` role", pi)
        self.assertIn("general implementation use `worker`", pi)
        self.assertIn("read-only review uses `reviewer`", pi)
        self.assertIn("actual resolved role, model, effort, fallback, run id", pi)
        self.assertIn('explicit `context: "fresh"`', pi)
        self.assertIn("Fork only an `oracle`", pi)
        self.assertIn("one bounded fresh-child slice whose fixed overhead stays small", pi)
        self.assertIn("never pass `--no-context-files` or `-nc`", pi)
        self.assertIn("Pi's effective per-directory context selection", pi)
        self.assertIn("One mission has one writer", pi)
        self.assertIn("A Pi child must not delegate again", pi)
        self.assertIn("preserve Pi's installed role and model routing", prompt)

        graph = self.read("references/graph-orchestration.md")
        self.assertIn("not cross-provider fallback hints", graph)
        self.assertIn("On a Pi host, every review uses the installed `reviewer` role", graph)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_claude_graph_workflow_splits_mixed_frontiers_by_tool_profile(self) -> None:
        claude = self.read_sibling_skill("fullstack-harness-claude-code")
        prompt = self.read_agent_prompt("fullstack-harness-claude-code")

        self.assertIn("homogeneous `tool_profile`", claude)
        self.assertIn("Each group gets its own bounded call", claude)
        self.assertIn("Never put a `mission_write` node beside a `code_review_readonly`", claude)
        self.assertIn("homogeneous `tool_profile` groups", claude)
        self.assertIn("permission-level tool removal", claude)
        self.assertNotIn("omits write-capable tools", claude)
        self.assertIn("group nodes by tool profile", prompt)


if __name__ == "__main__":
    unittest.main()
