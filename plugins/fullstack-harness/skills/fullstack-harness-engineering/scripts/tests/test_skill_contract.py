import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


def find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (
            (candidate / ".agents" / "plugins" / "marketplace.json").is_file()
            and (candidate / "scripts" / "sync_plugin_skills.py").is_file()
        ):
            return candidate
    return None


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)


class FullstackHarnessSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_project_size_gate_keeps_small_work_direct(self) -> None:
        skill = self.read("SKILL.md")
        research = self.read("references/orchestration-research-notes.md")
        selector = self.read("references/parallel-mission-selection.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("## Project Size Gate", skill)
        self.assertIn("small -> direct inspect", skill)
        self.assertIn("large -> planner", skill)
        self.assertIn("cannot override a `large` classification", skill)
        self.assertIn("Small work creates no PLAN/RUN files", skill)
        self.assertIn("scheduler fan-out only when", skill)
        self.assertIn("two-way project-size gate", research)
        self.assertIn("Small work never reaches this selector", selector)
        self.assertIn("Small direct work does not instantiate this file", runbook)
        self.assertIn("classify the project as small or large", agent)

    @unittest.skipIf(REPO_ROOT is None, "README contract requires a source checkout")
    def test_readme_explains_the_project_size_gate(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("The delivery skill makes one size decision", readme)

    def test_external_claude_bridge_is_preflighted_on_demand(self) -> None:
        skill = self.read("SKILL.md")
        research = self.read("references/orchestration-research-notes.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("Do not probe an external runtime merely because it may be available", skill)
        self.assertIn("run the bridge preflight before ready-node selection", skill)
        self.assertIn("a ready node's PLAN runtime policy calls for external Claude", skill)
        self.assertIn("does not preflight Claude merely because its CLI is installed", research)
        self.assertIn("preflight Claude before selection only when a ready PLAN node needs that route", agent)

    def test_authorized_app_wave_requires_real_thread_launch(self) -> None:
        skill = self.read("SKILL.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("Do not stop after printing a non-empty app-task wave", skill)
        self.assertIn("consume every `launch_directives` entry", skill)
        self.assertIn("## Launch Selected Codex App Threads", orchestration)
        self.assertIn("typed PLAN/RUN graph", agent)

    def test_plan_backed_runs_detect_then_select_up_to_three(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        selector = self.read("references/parallel-mission-selection.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("## Default Runtime And Wave Policy", skill)
        self.assertIn("proactively inspect the current-session native tool surface", skill)
        self.assertIn(
            "Missing authorization must never make an available driver disappear",
            skill,
        )
        self.assertIn(
            "Use three as the configured plan-backed write-worker maximum",
            skill,
        )
        self.assertIn("default immediately after Plan Readiness", state)
        self.assertIn("## Default Plan-Backed Wave", orchestration)
        self.assertIn("selection is the default post-readiness action", selector)
        self.assertIn("Never run parallel writers in `shared_checkout`", runbook)
        self.assertIn("select authorized ready nodes", agent)

    def test_nontrivial_app_worker_must_use_nested_subagent(self) -> None:
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn(
            "spawn at least one and at most `max_children` direct read-only subagents",
            worker_goal,
        )
        self.assertIn(
            "A non-trivial mission launches at least one eligible read-only lane",
            runbook,
        )

    def test_schema_v6_routes_claude_dynamic_workflow(self) -> None:
        skill = self.read("SKILL.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        selector_reference = self.read("references/parallel-mission-selection.md")
        workflow = self.read("assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js")

        for content in (skill, runbook, orchestration, selector_reference):
            self.assertIn("runtime_adapter", content)
            self.assertIn("dynamic_workflow", content)
        self.assertIn("## Launch Selected Claude Dynamic Workflow", orchestration)
        self.assertIn("`scriptPath`", orchestration)
        self.assertIn("run_dynamic_workflow", selector_reference)
        self.assertIn("CLAUDE_DYNAMIC_WORKFLOW.template.js", skill)
        self.assertIn("pipeline(args.missions", workflow)
        self.assertIn('"worker_result"', workflow)
        self.assertIn('"lease_id"', workflow)
        self.assertIn('"task_results"', workflow)
        self.assertIn('"REFINEMENT_REQUEST"', workflow)

    def test_goal_template_matches_current_authorization_ledger(self) -> None:
        goal = self.read("assets/templates/GOAL.template.md")

        self.assertIn("Keep all 17 schema-v9 RUN authorization entries false", goal)
        self.assertIn("invoke_external_runtime", goal)
        self.assertIn("create one worktree thread per selected mission", goal)

    def test_authorized_landing_runs_without_intermediate_stop(self) -> None:
        skill = self.read("SKILL.md")
        goal = self.read("assets/templates/GOAL.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        project_rules = self.read("assets/templates/PROJECT_AGENTS.template.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("#### Authorized Automatic Pull-Request Landing", skill)
        self.assertIn("do not stop after local verification", skill)
        self.assertIn("do not stop after verification or PR creation", goal)
        self.assertIn("one continuous parent-owned landing loop", runbook)
        self.assertIn("continue through that landing flow without pausing", project_rules)
        for content in (skill, goal, runbook, project_rules):
            self.assertIn("current-head", content)
            self.assertIn("merge", content.lower())
        self.assertIn("integrate verified work", agent)

    def test_plan_readiness_requests_review_and_merge_once(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        goal = self.read("assets/templates/GOAL.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        project_rules = self.read("assets/templates/PROJECT_AGENTS.template.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("request every missing launch and landing action", skill)
        self.assertIn("request every missing landing action once", state)
        self.assertIn("one-time Plan Readiness authorization checkpoint", goal)
        self.assertIn("request every missing launch and landing action", runbook)
        self.assertIn("Request every missing branch, commit, integration", project_rules)
        self.assertIn("select authorized ready nodes", agent)
        for content in (skill, state, goal, runbook, project_rules):
            self.assertIn("manage_pr_review", content)
            self.assertIn("merge_pr", content)
            self.assertIn("future-pr:", content)

    def test_current_head_e2e_replaces_only_duplicate_manual_smoke(self) -> None:
        skill = self.read("SKILL.md")
        verification = self.read("references/verification-gates.md")
        e2e_template = self.read("assets/templates/E2E_VERIFICATION.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        ci_template = self.read("assets/templates/PROJECT_CI.template.yml")
        project_rules = self.read("assets/templates/PROJECT_AGENTS.template.md")

        self.assertIn("## Automated E2E And Smoke Reuse", verification)
        self.assertIn("### Automated E2E And Smoke Reuse", runbook)
        for content in (skill, verification, e2e_template, runbook, project_rules):
            self.assertIn(
                "not required - covered by current-head E2E",
                content,
            )
            self.assertIn("deployment smoke", content.lower())
        self.assertIn("  e2e:", ci_template)
        self.assertIn("<e2e-command>", ci_template)
        self.assertIn("actions/upload-artifact@v4", ci_template)
        self.assertIn("github.event.pull_request.head.sha", ci_template)
        self.assertIn("ref: ${{ env.E2E_HEAD_SHA }}", ci_template)
        self.assertIn("e2e-${{ env.E2E_HEAD_SHA }}", ci_template)

    def test_cloudflare_release_uses_two_isolated_exact_sha_workers(self) -> None:
        skill = self.read("SKILL.md")
        lifecycle = self.read("references/cloudflare-deployment-lifecycle.md")
        state_model = self.read("references/execution-state-model.md")
        plan_template = self.read("assets/templates/HARNESS_PLAN.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        deploy_workflow = self.read(
            "assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml"
        )
        project_rules = self.read("assets/templates/PROJECT_AGENTS.template.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("one repository and one codebase deployed to two isolated Workers", lifecycle)
        self.assertIn("environment:development", lifecycle)
        self.assertIn("environment:production", lifecycle)
        self.assertIn("schema v4", plan_template)
        self.assertIn('"release"', plan_template)
        self.assertIn("schema v9", runbook)
        self.assertIn('"deployments"', runbook)
        self.assertIn("version support does not enable Cloudflare release state by itself", runbook)
        self.assertIn("required only when the matching PLAN declares `release`", runbook)
        self.assertIn("Schema version alone does not enable release behavior", state_model)
        self.assertIn("workflow_dispatch:", deploy_workflow)
        self.assertIn("source_sha:", deploy_workflow)
        self.assertIn("cloudflare/wrangler-action@v3", deploy_workflow)
        self.assertIn("steps.cloudflare-deploy.outputs.deployment-url", deploy_workflow)
        self.assertIn("steps.cloudflare-deploy.outputs.command-output", deploy_workflow)
        self.assertIn("origin/<base-branch>", deploy_workflow)
        self.assertNotIn("\n  push:", deploy_workflow)
        for content in (skill, lifecycle, project_rules):
            self.assertIn("development", content.lower())
            self.assertIn("production", content.lower())
            self.assertIn("separate", content.lower())

    def test_builder_ux_direction_is_ready_before_implementation_and_not_usability_proof(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/contract-and-traceability.md")
        updates = self.read("references/design-input-updates.md")
        verification = self.read("references/verification-gates.md")
        plan_template = self.read("assets/templates/HARNESS_PLAN.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        e2e_template = self.read("assets/templates/E2E_VERIFICATION.template.md")
        goal = self.read("assets/templates/GOAL.template.md")
        agent = self.read("agents/openai.yaml")

        for content in (skill, contract, updates, verification, plan_template, runbook, e2e_template, goal):
            self.assertIn("Builder UX Direction", content)
        self.assertIn("Every must-have `UX-*` trace", skill)
        self.assertIn("## UX Direction And Usability Evidence", verification)
        self.assertIn("Builder approval proves only direction conformance", verification)
        self.assertIn("## UX Evidence", runbook)

    def test_schema_v4_graph_and_external_claude_bridge_are_first_class(self) -> None:
        skill = self.read("SKILL.md")
        graph = self.read("references/graph-orchestration.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        run = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        workflow = self.read("assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js")
        preflight = self.read("assets/templates/CLAUDE_RUNTIME_PREFLIGHT.template.js")
        bridge = self.read("scripts/claude_runtime_bridge.py")
        selector = self.read("scripts/select_ready_nodes.py")

        for content in (skill, graph, run):
            self.assertIn("invoke_external_runtime", content)
        self.assertIn('"schema_version": 4', plan)
        self.assertIn('"schema_version": 9', run)
        self.assertIn('"graph_state"', run)
        self.assertIn("dependency", graph)
        self.assertIn("max_traversals", graph)
        self.assertIn("pipeline(workflowArgs.nodes", workflow)
        self.assertIn("protocol_version", preflight)
        self.assertIn("await agent(", preflight)
        self.assertIn("external_dynamic_workflow", selector)
        self.assertIn("--allowedTools", bridge)

    def test_plan_provider_options_bind_worker_models(self) -> None:
        skill = self.read("SKILL.md")
        graph = self.read("references/graph-orchestration.md")
        state = self.read("references/execution-state-model.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        run = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        selector = self.read("scripts/select_ready_nodes.py")
        bridge = self.read("scripts/claude_runtime_bridge.py")

        self.assertIn('"provider_options"', plan)
        self.assertIn('"preferred_provider": "claude_code"', plan)
        self.assertGreaterEqual(plan.count('"model": "claude-fable-5"'), 3)
        self.assertGreaterEqual(plan.count('"model": "gpt-5.6-sol"'), 3)
        self.assertIn("gpt-5.6-terra", skill)
        self.assertIn('"reasoning_effort": "high"', plan)
        self.assertIn("Plan Mode chooses", graph)
        self.assertIn("provider-specific model options", skill)
        self.assertIn(
            "prefer Codex `gpt-5.6-terra` with `xhigh` reasoning for general-purpose nodes, backend implementation, and `backend_code` review",
            skill,
        )
        self.assertIn(
            "For general-purpose nodes, backend implementation, and `backend_code` review, prefer Codex `gpt-5.6-terra` with `xhigh` reasoning",
            plan,
        )
        self.assertIn("For `frontend_code` review nodes, use `claude-fable-5` with `xhigh` reasoning", skill)
        for content in (skill, graph, plan):
            self.assertIn("claude-fable-5", content)
            self.assertIn("gpt-5.6-sol", content)
            self.assertIn("xhigh", content)
        self.assertIn("workers[].runtime_binding", state)
        self.assertIn("task creation `model` and `thinking`", run)
        self.assertIn('"runtime_binding": binding', selector)
        self.assertIn("PLAN-selected wave model", bridge)

    def test_schema_v9_closes_only_with_real_ui_evidence(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        verification = self.read("references/verification-gates.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn('"schema_version": 9', runbook)
        self.assertIn('"batch_gate_results"', runbook)
        self.assertIn('"final_gate_results"', runbook)
        self.assertIn('"ui_evidence"', runbook)
        self.assertIn("New plan-backed files use PLAN schema v4 and RUN schema v9", skill)
        self.assertIn("complete` is an execution closeout state", state)
        for content in (skill, verification, runbook):
            self.assertIn("breakpoint-by-state", content)
            self.assertIn("SHA-256", content)
            self.assertIn("docs/goal/evidence/", content)


if __name__ == "__main__":
    unittest.main()
