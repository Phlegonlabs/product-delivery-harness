import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = SKILL_ROOT.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (
            (candidate / ".agents" / "plugins" / "marketplace.json").is_file()
            and (candidate / "scripts" / "sync_plugin_skills.py").is_file()
        ):
            return candidate
    return None


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)

RETIRED_ADAPTER_SKILLS = (
    "fullstack-harness-codex",
    "fullstack-harness-claude-code",
    "fullstack-harness-pi",
)


class AdapterContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def read_adapters(self) -> str:
        return self.read("references/runtime-adapters.md")

    def test_project_templates_point_at_the_runtime_adapter_reference(self) -> None:
        agents = (SKILLS_ROOT / "full-harness" / "assets" / "templates" / "PROJECT_AGENTS.template.md").read_text(encoding="utf-8")
        claude = (SKILL_ROOT / "assets" / "templates" / "PROJECT_CLAUDE.template.md").read_text(encoding="utf-8")

        for content in (agents, claude):
            self.assertIn("runtime adapter reference", content)
            self.assertNotIn("Full-Stack Harness adapter", content)

    def test_runtime_adapters_replaces_the_retired_adapter_skills(self) -> None:
        core = self.read("SKILL.md")

        self.assertIn("references/runtime-adapters.md", core)
        self.assertIn(
            "Adding a host adds one provider section to that reference, not a new skill",
            core,
        )
        self.assertNotIn("../fullstack-harness-codex/SKILL.md", core)
        self.assertNotIn("../fullstack-harness-claude-code/SKILL.md", core)
        self.assertNotIn("../fullstack-harness-pi/SKILL.md", core)
        for name in RETIRED_ADAPTER_SKILLS:
            self.assertFalse(
                (SKILLS_ROOT / name / "SKILL.md").exists(),
                f"retired adapter skill still exists: {name}",
            )

    def test_every_schema_provider_has_one_documented_section(self) -> None:
        from harness_schema import RUNTIME_DRIVER_PRIORITY

        adapters = self.read_adapters()

        for provider in sorted(RUNTIME_DRIVER_PRIORITY):
            with self.subTest(provider=provider):
                self.assertIn(f"## Provider: {provider}", adapters)

    def test_runtime_adapters_documents_how_to_add_a_provider(self) -> None:
        adapters = self.read_adapters()

        self.assertIn("## Adding A Provider", adapters)
        self.assertIn("needs no schema change", adapters)
        self.assertIn(
            "runs the Provider: generic route with the generic driver ladder", adapters
        )
        self.assertIn("`RUNTIME_DRIVER_PRIORITY` in `scripts/harness_schema.py`", adapters)
        self.assertIn(
            "never adds authorization keys, alternate state, handoff, or upgrade rules",
            adapters,
        )

    def test_generic_provider_section_is_a_complete_route_for_any_host(self) -> None:
        adapters = self.read_adapters()

        self.assertIn(
            "Any host without a dedicated section above runs the generic route unchanged",
            adapters,
        )
        self.assertIn("Any lowercase provider id is schema-valid", adapters)
        self.assertIn("the names are illustrative, not a support list", adapters)
        self.assertIn("no generic model catalog", adapters)
        self.assertIn("never substitute a different model silently", adapters)
        self.assertIn(
            "Do not inject another runtime's instruction file as this host's instructions",
            adapters,
        )
        self.assertIn("in-reviewer browser surface", adapters)
        self.assertIn("cannot satisfy a fresh independent review node", adapters)
        self.assertIn(
            "that section replaces this one for that host", adapters
        )

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_allowed_providers_alone_controls_current_host_eligibility(self) -> None:
        adapters = self.read_adapters()
        research = self.read("references/orchestration-research-notes.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")

        for provider in ("codex", "claude_code", "pi", "generic"):
            self.assertIn(
                f"A PLAN node is selectable here when its `allowed_providers` includes `{provider}`",
                adapters,
            )
        self.assertIn(
            "`preferred_provider` is advisory ordering among allowed hosts; it never blocks the current host",
            adapters,
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
        for content in (adapters, research, orchestration):
            self.assertNotIn("required or preferred provider", content)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_codex_uses_flat_parent_owned_delegation(self) -> None:
        adapters = self.read_adapters()

        self.assertIn("Flat Parent-Owned Delegation", adapters)
        self.assertIn("No worker or reviewer spawns another agent", adapters)
        self.assertIn("sibling nodes dispatched by the Harness parent", adapters)
        self.assertIn("fresh read-only reviewers", adapters)
        self.assertIn("exact unified integration SHA", adapters)
        self.assertIn("one planned broad final validation", adapters)
        self.assertIn("dispatchable_nodes[].required_actions", adapters)
        self.assertIn("RUN-v11 forbids task-local child agents", adapters)
        self.assertIn("Never replace explicitly requested independent app tasks", adapters)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_launch_and_review_actions_follow_each_dispatchable_node(self) -> None:
        adapters = self.read_adapters()

        self.assertIn("dispatchable_nodes[].required_actions", adapters)
        self.assertIn("Never infer extra authorization", adapters)

        self.assertIn("A review app task needs `create_user_owned_tasks`", adapters)
        self.assertIn("a direct-subagent review needs `spawn_subagents`", adapters)
        self.assertNotIn("a read-only review node's required actions are only", adapters)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_every_adapter_preserves_host_specific_context_discovery(self) -> None:
        adapters = self.read_adapters()

        self.assertIn("Codex worker contract", adapters)
        self.assertIn("`AGENTS.override.md` / `AGENTS.md` repository context paths", adapters)
        self.assertIn("do not inject `CLAUDE.md` as Codex instructions", adapters)
        self.assertIn("`AGENTS.md` context discovery enabled", adapters)

        self.assertIn("Claude Code worker contract", adapters)
        self.assertIn("effective `CLAUDE.md` repository context paths", adapters)
        self.assertIn("shared `AGENTS.md` governance paths", adapters)
        self.assertIn("Do not apply Codex or Pi worker mechanics", adapters)

        self.assertIn("Pi worker contract", adapters)
        self.assertIn("`AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`", adapters)
        self.assertIn("When `AGENTS.md` exists do not also inject `CLAUDE.md`", adapters)
        self.assertIn("Pi context discovery enabled", adapters)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_every_adapter_uses_fresh_context_terminal_events_and_runtime_metrics(self) -> None:
        adapters = self.read_adapters()

        for phrase in (
            "bounded context packet",
            "runtime_metrics",
            "pre-integration review",
            "fresh",
        ):
            self.assertIn(phrase, adapters)

        self.assertIn("cursor-based `wait_threads`", adapters)
        self.assertIn("Do not repeatedly read unchanged tasks", adapters)
        self.assertIn("`pipeline()` / `agent_result` terminal output", adapters)
        self.assertIn("Subscribe or block on terminal child/status events", adapters)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_every_adapter_applies_the_shared_runtime_upgrade_gate(self) -> None:
        adapters = self.read_adapters()

        for phrase in (
            "runtime_adapter.version_gate",
            "runtime-upgrades.md",
            "compatible_old",
            "restart_required",
        ):
            self.assertIn(phrase, adapters)

        self.assertIn("fresh top-level task", adapters)
        self.assertIn("`/reload-plugins` or restart Claude Code", adapters)
        self.assertIn("Never overwrite standalone skills", adapters)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_every_adapter_probes_chrome_devtools_inside_the_reviewer(self) -> None:
        adapters = self.read_adapters()
        state = self.read("references/execution-state-model.md")
        workflow = self.read("assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js")

        for phrase in (
            "runtime_capabilities.reviewer_tools.chrome_devtools",
            "probe_scope: reviewer_session",
            "not a review attempt",
        ):
            self.assertIn(phrase, adapters)

        self.assertIn("surface: raw_cdp", adapters)
        self.assertIn("`Runtime.evaluate`", adapters)
        self.assertIn("`claude --chrome`", adapters)
        self.assertIn("surface: claude_in_chrome", adapters)
        self.assertIn("`mcp__claude-in-chrome__*`", adapters)
        self.assertIn("`subagents.agentOverrides.reviewer.extensions`", adapters)
        self.assertIn("strict tool allowlist", adapters)
        self.assertIn("`npm:@narumitw/pi-chrome-devtools`", adapters)
        self.assertIn("surface: pi_chrome_devtools", adapters)
        self.assertIn("parent's browser connection", state)
        self.assertIn("required_tools", workflow)
        self.assertIn("reviewer_tool_capabilities", workflow)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_same_repository_handoff_is_serialized_and_cross_machine_is_unsupported(self) -> None:
        state = self.read("references/execution-state-model.md")
        adapters = self.read_adapters()
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

        self.assertIn("Serialized Same-Repository Host Handoff", adapters)
        self.assertIn("execution-state-model.md", adapters)
        self.assertIn("This adapter adds no alternate state or handoff rules", adapters)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_pi_preserves_installed_role_and_model_routing(self) -> None:
        adapters = self.read_adapters()

        self.assertIn("Pi owns role-to-model and fallback selection", adapters)
        self.assertIn("`provider_options.pi.model` null", adapters)
        self.assertIn("role-aware Pi launch surface", adapters)
        self.assertIn("generic `agents.spawn` surface", adapters)
        self.assertIn("lacks a Pi role selector, it does not satisfy this capability", adapters)
        self.assertIn("Omit `model` from the Pi launch call", adapters)
        self.assertIn("Do not manually respawn the node on another model or provider", adapters)
        self.assertIn("PLAN may lower or raise reasoning effort per node", adapters)
        self.assertIn("per-run thinking suffix", adapters)
        self.assertIn("`medium` for bounded discovery", adapters)
        self.assertIn("`high` for general implementation", adapters)
        self.assertIn("`xhigh` only for a justified high-risk or unified final synthesis", adapters)
        self.assertIn("`frontend_designer` role", adapters)
        self.assertIn("general implementation use `worker`", adapters)
        self.assertIn("read-only review uses `reviewer`", adapters)
        self.assertIn("actual resolved role, model, effort, fallback, run id", adapters)
        self.assertIn('explicit `context: "fresh"`', adapters)
        self.assertIn("Fork only an `oracle`", adapters)
        self.assertIn("one bounded fresh-child slice whose fixed overhead stays small", adapters)
        self.assertIn("never pass `--no-context-files` or `-nc`", adapters)
        self.assertIn("Pi's effective per-directory context selection", adapters)
        self.assertIn("One mission has one writer", adapters)
        self.assertIn("A Pi child must not delegate again", adapters)

        graph = self.read("references/graph-orchestration.md")
        self.assertIn("not cross-provider fallback hints", graph)
        self.assertIn("On a Pi host, every review uses the installed `reviewer` role", graph)

    @unittest.skipIf(REPO_ROOT is None, "adapter contract requires a source checkout")
    def test_claude_graph_workflow_splits_mixed_frontiers_by_tool_profile(self) -> None:
        adapters = self.read_adapters()

        self.assertIn("homogeneous `tool_profile`", adapters)
        self.assertIn("Each group gets its own bounded call", adapters)
        self.assertIn("Never put a `mission_write` node beside a `code_review_readonly`", adapters)
        self.assertIn("homogeneous `tool_profile` groups", adapters)
        self.assertIn("permission-level tool removal", adapters)
        self.assertNotIn("omits write-capable tools", adapters)


if __name__ == "__main__":
    unittest.main()
