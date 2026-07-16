import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class FullstackHarnessSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_authorized_app_wave_requires_real_thread_launch(self) -> None:
        skill = self.read("SKILL.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("Do not stop after printing a non-empty app-task wave", skill)
        self.assertIn("consume every `launch_directives` entry", skill)
        self.assertIn("## Launch Selected Codex App Threads", orchestration)
        self.assertIn("one worktree thread per selected mission", agent)

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
        self.assertIn("up to three authorized nonconflicting missions", agent)

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

        self.assertIn("Keep all 16 RUN authorization entries false", goal)
        self.assertNotIn("Keep all 13 RUN authorization entries false", goal)
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
        self.assertIn("continue automatically through Draft PR", agent)
        for content in (skill, goal, runbook, project_rules, agent):
            self.assertIn("current-head", content)
            self.assertIn("merge", content.lower())

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


if __name__ == "__main__":
    unittest.main()
