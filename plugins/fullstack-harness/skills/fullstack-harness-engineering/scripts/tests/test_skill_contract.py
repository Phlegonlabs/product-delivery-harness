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


class FullstackHarnessSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def read_sibling_skill(self, name: str) -> str:
        return (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")

    def read_sibling_agent(self, name: str) -> str:
        return (SKILLS_ROOT / name / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )

    def test_runtime_and_landing_adapters_load_lazily(self) -> None:
        core = self.read("SKILL.md")
        codex = self.read_sibling_skill("fullstack-harness-codex")
        claude = self.read_sibling_skill("fullstack-harness-claude-code")
        landing = self.read_sibling_skill("fullstack-harness-github-landing")

        self.assertIn("Do not load all adapters in one run", core)
        self.assertIn("Do not also read the Claude Code adapter", core)
        self.assertIn("Do not also read the Codex adapter", core)
        self.assertIn("only when the requested outcome includes push", core)
        self.assertIn("Do not load the Claude Code adapter in the same parent", codex)
        self.assertIn("Do not load the Codex adapter in the same parent", claude)
        self.assertIn("Local branch, commit, or integration work stays `local_only`", landing)
        self.assertNotIn("## Authorized Automatic Pull-Request Landing", codex)
        self.assertNotIn("## Authorized Automatic Pull-Request Landing", claude)

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

        self.assertIn("The delivery core makes one size decision", readme)

    def test_provider_mismatch_is_blocked_not_bridged(self) -> None:
        codex_skill = self.read_sibling_skill("fullstack-harness-codex")
        claude_skill = self.read_sibling_skill("fullstack-harness-claude-code")
        research = self.read("references/orchestration-research-notes.md")

        self.assertIn("## Provider Boundary", codex_skill)
        self.assertIn("## Provider Boundary", claude_skill)
        self.assertIn("There is no mechanism in this adapter to invoke Claude Code", codex_skill)
        self.assertIn("There is no mechanism in this adapter to invoke Codex", claude_skill)
        self.assertIn(
            "do not attempt to launch it and do not probe for a Claude Code CLI, binary, or plugin as a substitute route",
            codex_skill,
        )
        self.assertIn(
            "do not attempt to launch it and do not probe for an installed Codex CLI or plugin as a substitute route",
            claude_skill,
        )
        self.assertIn("there is no cross-host preflight, no bridged process, and no declared fallback", research)
        self.assertIn("blocked on provider mismatch rather than probing or launching the other runtime", research)

    def test_authorized_app_wave_requires_real_thread_launch(self) -> None:
        skill = self.read_sibling_skill("fullstack-harness-codex")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        agent = self.read_sibling_agent("fullstack-harness-codex")

        self.assertIn("Do not stop after printing a non-empty app-task wave", skill)
        self.assertIn("consume every `launch_directives` entry", skill)
        self.assertIn("## Launch Selected Codex App Threads", orchestration)
        self.assertIn("Codex-hosted large run", agent)

    def test_plan_backed_runs_detect_then_select_full_frontier(self) -> None:
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
            "Do not cap `max_parallel_workers` at a small fixed number",
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
        skill = self.read_sibling_skill("fullstack-harness-claude-code")
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
        self.assertIn("pipeline(workflowArgs.missions", workflow)
        self.assertIn('"worker_result"', workflow)
        self.assertIn('"lease_id"', workflow)
        self.assertIn('"task_results"', workflow)
        self.assertIn('"REFINEMENT_REQUEST"', workflow)

    def test_goal_template_matches_current_authorization_ledger(self) -> None:
        goal = self.read("assets/templates/GOAL.template.md")

        self.assertIn("Keep all 19 schema-v10 RUN authorization entries false", goal)
        self.assertIn("invoke_external_runtime", goal)
        self.assertIn("create one worktree thread per selected mission", goal)

    def test_authorized_landing_runs_without_intermediate_stop(self) -> None:
        skill = self.read_sibling_skill("fullstack-harness-github-landing")
        goal = self.read("assets/templates/GOAL.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        project_rules = self.read("assets/templates/PROJECT_AGENTS.template.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("## Authorized Automatic Pull-Request Landing", skill)
        self.assertIn("do not stop after local verification", skill)
        self.assertIn("do not stop after verification or PR creation", goal)
        self.assertIn("one continuous parent-owned landing loop", runbook)
        self.assertIn("continue through that landing flow without pausing", project_rules)
        self.assertIn("With separate `create_pr` authorization, open a Draft PR", project_rules)
        self.assertIn("without matching `manage_pr_review` authorization", project_rules)
        for content in (skill, goal, runbook, project_rules):
            self.assertIn("current-head", content)
            self.assertIn("merge", content.lower())
        self.assertIn("integrate passing work", agent)

    def test_remote_verification_is_final_head_and_parallel(self) -> None:
        core = self.read("SKILL.md")
        landing = self.read_sibling_skill("fullstack-harness-github-landing")
        verification = self.read("references/verification-gates.md")
        state = self.read("references/execution-state-model.md")
        project_rules = self.read("assets/templates/PROJECT_AGENTS.template.md")

        self.assertIn("does not wait for GitHub CI or GitHub review", core)
        self.assertIn("Do not push intermediate worker heads merely to obtain CI", landing)
        self.assertIn("poll both concurrently", landing)
        self.assertIn("sibling remote gates", landing)
        self.assertIn("run or observe current-head CI and current-head Codex review concurrently", verification)
        self.assertIn("CI and review are independent sibling gates", state)
        self.assertIn("Poll both gates concurrently", project_rules)

    def test_runbook_defaults_to_local_only_landing(self) -> None:
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn('"mode": "local_only"', runbook)
        self.assertIn('New RUN files default to `mode: "local_only"`', runbook)
        self.assertIn("switch to `pull_request` only when the user explicitly requests remote landing", runbook)

    @unittest.skipIf(REPO_ROOT is None, "repository rules require a source checkout")
    def test_repository_rules_do_not_shadow_concurrent_review_flow(self) -> None:
        repository_rules = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("request Codex review immediately after creation", repository_rules)
        self.assertIn("Observe current-head CI and review concurrently", repository_rules)
        self.assertIn("poll both gates concurrently", repository_rules)

    def test_plan_readiness_requests_review_and_merge_once(self) -> None:
        skill = self.read_sibling_skill("fullstack-harness-github-landing")
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
        self.assertIn("`release:<target-id>`", lifecycle)
        self.assertIn("`web-development`", lifecycle)
        self.assertIn("`web-production`", lifecycle)
        self.assertIn("PLAN schema v5", plan_template)
        self.assertIn('"release"', plan_template)
        self.assertIn("RUN schema v10", runbook)
        self.assertIn('"targets"', runbook)
        self.assertIn("Older RUN schemas remain readable", runbook)
        self.assertIn("keys must exactly equal the PLAN `release.targets[].id` set", runbook)
        self.assertIn("Current PLAN schema v5 uses provider-neutral `release.targets`", state_model)
        self.assertIn("Older RUN v7-v9 `deployments` objects remain readable", state_model)
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

    def test_cloudflare_deploy_requires_wrangler_config_and_account_verification(self) -> None:
        lifecycle = self.read("references/cloudflare-deployment-lifecycle.md")
        verification = self.read("references/verification-gates.md")
        deploy_workflow = self.read("assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml")
        project_claude = self.read("assets/templates/PROJECT_CLAUDE.template.md")
        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")

        self.assertIn("## Wrangler Config and Account Bootstrap", lifecycle)
        self.assertIn(
            "generate `wrangler.jsonc` before attempting any deploy",
            lifecycle,
        )
        self.assertIn("Verify the current Wrangler config schema against official documentation", lifecycle)
        self.assertIn("stop — do not attempt the deploy", lifecycle)
        self.assertIn("wrangler whoami", lifecycle)
        self.assertIn("https://developers.cloudflare.com/workers/wrangler/configuration/", lifecycle)

        self.assertIn(
            "Before either gate below can be attempted, a blocking prerequisite gate must pass",
            verification,
        )

        self.assertIn(
            '"cloudflare-development" and "cloudflare-production" GitHub Environments',
            deploy_workflow,
        )

        for content in (project_claude, project_agents):
            self.assertIn(
                "confirm Cloudflare account access is verified",
                content,
            )
            self.assertIn("Never attempt a deploy while either is unverified", content)

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

    def test_schema_v5_graph_is_first_class(self) -> None:
        skill = self.read("SKILL.md")
        graph = self.read("references/graph-orchestration.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        run = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        workflow = self.read("assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js")
        selector = self.read("scripts/select_ready_nodes.py")

        for content in (skill, run):
            self.assertIn("invoke_external_runtime", content)
        self.assertIn('"schema_version": 5', plan)
        self.assertIn('"schema_version": 10', run)
        self.assertIn('"graph_state"', run)
        self.assertIn("dependency", graph)
        self.assertIn("max_traversals", graph)
        self.assertIn("pipeline(workflowArgs.nodes", workflow)
        self.assertIn("tool_profile", selector)
        self.assertIn('"workflow_runs"', run)
        self.assertIn("mission_write", run)
        self.assertIn("EnterWorktree", workflow)

    def test_plan_provider_options_bind_worker_models(self) -> None:
        skill = "\n".join(
            (
                self.read("SKILL.md"),
                self.read_sibling_skill("fullstack-harness-codex"),
                self.read_sibling_skill("fullstack-harness-claude-code"),
            )
        )
        graph = self.read("references/graph-orchestration.md")
        state = self.read("references/execution-state-model.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        run = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        selector = self.read("scripts/select_ready_nodes.py")

        self.assertIn('"provider_options"', plan)
        self.assertIn('"preferred_provider": "claude_code"', plan)
        # A delegated Claude Code node never defaults above sonnet: the pinned
        # top-tier model is reserved for the parent's own coordination/planning,
        # not assigned to any worker/review node by default.
        self.assertGreaterEqual(plan.count('"model": "sonnet"'), 3)
        self.assertGreaterEqual(plan.count('"model": "gpt-5.6-sol"'), 3)
        self.assertIn("gpt-5.6-terra", skill)
        self.assertIn('"reasoning_effort": "high"', plan)
        self.assertIn("Plan Mode chooses", graph)
        self.assertIn("provider-specific model options", skill)
        self.assertIn(
            "for general-purpose nodes and backend implementation, prefer Codex `gpt-5.6-terra` with `high` reasoning",
            skill,
        )
        self.assertIn(
            "For general-purpose nodes and backend implementation, prefer Codex `gpt-5.6-terra` with `high` reasoning",
            plan,
        )
        self.assertIn(
            "routine deterministic `backend_code` review uses Codex `gpt-5.6-terra` with `medium`",
            skill,
        )
        self.assertIn(
            "routine `frontend_code`, `backend_code`, and visual review use `sonnet` with `medium` effort",
            skill,
        )
        self.assertIn("reserve", skill.lower())
        for content in (skill, graph, plan):
            self.assertIn("claude-fable-5", content)
            self.assertIn("gpt-5.6-sol", content)
            self.assertIn("xhigh", content)
        self.assertIn("workers[].runtime_binding", state)
        self.assertIn("task creation `model` and `thinking`", run)
        self.assertIn('"runtime_binding": binding', selector)

    def test_verification_policy_selects_and_reuses_only_exact_focused_checks(self) -> None:
        skill = self.read("SKILL.md")
        verification = self.read("references/verification-gates.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        run = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")

        for content in (skill, verification, plan, worker):
            self.assertIn('selection.mode: "changed_files"', content)
            self.assertIn("parent-observed changed files", content)
        for content in (skill, verification, plan, run):
            self.assertIn("session_exact", content)
            self.assertIn("repository-external", content)
        self.assertIn("real cross-mission", verification)
        self.assertIn("broad regression, browser E2E", skill)
        self.assertIn("after exact-SHA code review and repair loops converge", plan)

    def test_schema_v10_closes_only_with_real_ui_evidence(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        verification = self.read("references/verification-gates.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn('"schema_version": 10', runbook)
        self.assertIn('"batch_gate_results"', runbook)
        self.assertIn('"final_gate_results"', runbook)
        self.assertIn('"ui_evidence"', runbook)
        self.assertIn("New plan-backed files use PLAN schema v5 and RUN schema v10", skill)
        self.assertIn("complete` is an execution closeout state", state)
        for content in (skill, verification, runbook):
            self.assertIn("breakpoint-by-state", content)
            self.assertIn("SHA-256", content)
            self.assertIn("docs/goal/evidence/", content)

    def test_bootstrap_seeds_agents_and_claude_governance_templates(self) -> None:
        skill = self.read("SKILL.md")
        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")
        project_claude = self.read("assets/templates/PROJECT_CLAUDE.template.md")

        self.assertIn("PROJECT_AGENTS.template.md", skill)
        self.assertIn("PROJECT_CLAUDE.template.md", skill)
        self.assertIn("seed a missing root `AGENTS.md`", skill)
        self.assertIn("a missing root `CLAUDE.md`", skill)
        self.assertIn("Skip either file that already exists", skill)
        self.assertIn(
            "never overwrite an established root `AGENTS.md` or `CLAUDE.md`", skill
        )
        self.assertIn("## Core Development Principles", project_agents)
        self.assertIn("## Core Development Principles", project_claude)


if __name__ == "__main__":
    unittest.main()
