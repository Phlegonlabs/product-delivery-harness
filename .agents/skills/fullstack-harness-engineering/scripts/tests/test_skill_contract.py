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
        selector = self.read("references/parallel-mission-selection.md")
        goal = self.read("assets/templates/GOAL.template.md")
        agent = self.read_sibling_agent("fullstack-harness-codex")

        self.assertIn("Do not stop after printing a non-empty app-task wave", skill)
        self.assertIn("consume every `launch_directives` entry", skill)
        self.assertIn("search the current Codex tool surface", skill)
        self.assertIn("own conversation in the left sidebar", skill)
        self.assertIn("## Launch Selected Codex App Threads", orchestration)
        self.assertIn("one top-level worktree task/thread per mission", orchestration)
        self.assertIn("each sibling task runs its own independent Multi-agent set", orchestration)
        self.assertIn("direct subagent of the coordinator is not equivalent", selector)
        self.assertIn("one top-level left-sidebar task", goal)
        self.assertIn("Never replace requested top-level tasks", agent)
        self.assertIn(
            "do not replace it with direct subagents or sequential parent execution",
            skill,
        )
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
            "A non-trivial mission must complete a post-edit read-only reviewer",
            runbook,
        )
        self.assertIn(
            "require an equivalent parent-owned read-only review before integration",
            runbook,
        )

    def test_frontend_design_is_loaded_only_in_ui_conformance_mode(self) -> None:
        skill = self.read("SKILL.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        design_updates = self.read("references/design-input-updates.md")

        for content in (skill, plan, worker_goal):
            self.assertIn("frontend-design conformance mode", content)
            self.assertIn("design-input delta", content)
        self.assertIn("user explicitly selected it", plan)
        self.assertIn("new or high-impact visual surface", plan)
        self.assertIn("proposed design-input delta", design_updates)

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
        self.assertIn(
            "create one top-level left-sidebar task with its own app-managed worktree per selected mission",
            goal,
        )

    def test_run_template_matches_the_integration_push_default(self) -> None:
        """The template has to describe the landing model SKILL.md now defaults to.

        A RUN authored from a template that still says ordinary work stays
        local_only would silently follow the old flow and never record the
        development push.
        """
        skill = self.read("SKILL.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn("uses `integration_push`", skill)
        self.assertIn("integration_push", runbook)
        self.assertIn("landing.pushed_head_sha", runbook)
        self.assertNotIn("Ordinary PRD, UI, and feature work stays `local_only`", runbook)
        self.assertNotIn('New RUN files default to `mode: "local_only"`.', runbook)

    def test_authorized_landing_runs_without_intermediate_stop(self) -> None:
        skill = self.read_sibling_skill("fullstack-harness-github-landing")
        goal = self.read("assets/templates/GOAL.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        project_rules = self.read("assets/templates/PROJECT_AGENTS.template.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("## Pull-Request Handover", skill)
        self.assertIn("stopping at — a merge-ready PR", skill)
        self.assertIn(
            "After final user approval starts an authorized protected-branch promotion",
            goal,
        )
        self.assertIn("one continuous parent-owned landing loop", runbook)
        self.assertIn("continue through that landing flow without pausing", project_rules)
        self.assertIn("With separate `create_pr` authorization, open a Draft PR", project_rules)
        self.assertIn("without matching `manage_pr_review` authorization", project_rules)
        # The merge toward the protected base is the human's; the harness may
        # prepare the PR and must stop there.
        self.assertIn("It does not merge and does not enable auto-merge", skill)
        self.assertIn("merge-ready PR", goal)
        self.assertIn("Do not merge and do not enable auto-merge", runbook)
        self.assertIn("The merge toward the protected base is the human's", project_rules)
        for content in (skill, goal, runbook, project_rules):
            self.assertIn("current-head", content)
            self.assertIn("merge", content.lower())
        self.assertIn("integrate passing work", agent)

    def test_ledger_reference_lists_exactly_the_code_actions(self) -> None:
        """The ledger reference drifted to v9/17 actions once already, because
        nothing tied its list to the constant the validator uses."""
        from harness_schema import AUTHORIZATION_KEYS_V10, EXECUTION_INTENT_SCOPED_ACTIONS

        reference = self.read("references/execution-state-model.md")
        core = self.read("SKILL.md")

        block_start = reference.index("The current schema-v10 ledger has")
        fence = reference.index("```text", block_start) + len("```text")
        listed = reference[fence : reference.index("```", fence)].split()

        self.assertEqual(sorted(AUTHORIZATION_KEYS_V10), sorted(listed))
        self.assertEqual(len(AUTHORIZATION_KEYS_V10), len(listed))
        self.assertIn(f"has {len(AUTHORIZATION_KEYS_V10)} actions", reference)

        for action in AUTHORIZATION_KEYS_V10:
            self.assertIn(f"`{action}`", core)
        for action in EXECUTION_INTENT_SCOPED_ACTIONS:
            self.assertIn(action, reference)

    def test_out_of_scope_targets_carry_their_own_recorded_source(self) -> None:
        core = self.read("SKILL.md")
        reference = self.read("references/execution-state-model.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn("`target_sources`", core)
        self.assertIn("## Per-Target Provenance For The Scoped Three", reference)
        self.assertIn("must differ from the entry `source`", reference)
        self.assertIn("Resolution fails closed", reference)
        self.assertIn("`target_sources` is rejected on any other action", reference)
        self.assertIn("in every landing mode", reference)
        self.assertIn('"target_sources": {', runbook)
        self.assertIn("in every landing mode", runbook)

    def test_merge_policy_splits_on_the_pr_base_branch(self) -> None:
        """Auto-merge is allowed into the integration branch and never into the
        protected landing branch.

        Regression guard: the ledger's grouped execution-intent bundle now
        carries `merge_pr`, so the only thing keeping a promotion PR from being
        merged automatically is that the grouping is scoped to the integration
        base.
        """
        core = self.read("SKILL.md")
        landing = self.read_sibling_skill("fullstack-harness-github-landing")
        project_rules = self.read("assets/templates/PROJECT_AGENTS.template.md")

        self.assertIn(
            "`merge_pr` and `deploy` are outside the bundle entirely under this model",
            core,
        )
        self.assertIn(
            "Repository auto-merge is available only for a PR whose base is a resolved "
            "non-protected integration branch",
            core,
        )
        self.assertIn(
            "A merge into `main` is never the harness's to initiate",
            core,
        )
        self.assertIn("does not enable auto-merge there", core)
        self.assertIn("Which side of this section applies is decided by the PR's base branch", landing)
        self.assertIn("It does not merge and does not enable auto-merge there", landing)
        for content in (project_rules,):
            self.assertIn("the next step depends on the PR's base", content)
            self.assertIn("resolved integration branch", content)
        self.assertIn("The merge toward the protected base is the human's", project_rules)

    def test_production_deploy_is_its_own_grant_not_the_merge(self) -> None:
        """One rule, three sites. The docs used to give three answers: the core
        said the harness never runs the production deploy, the Cloudflare
        reference said the parent runs it, and the validator required an exact
        `deploy` grant for the production target — which only makes sense if the
        harness can run it. The grant is what decides, not the merge.
        """
        from harness_authorization import execution_intent_target_in_scope

        core = self.read("SKILL.md")
        lifecycle = self.read("references/cloudflare-deployment-lifecycle.md")

        plan = {
            "release": {
                "targets": [
                    {"id": "web-development", "stage": "development"},
                    {"id": "web-production", "stage": "production"},
                ]
            }
        }
        run = {
            "integration": {"branch": "development"},
            "landing": {"base_branch": "production"},
        }
        # The development target rides the execution-intent instruction; the
        # production one is its own authorization moment.
        self.assertTrue(
            execution_intent_target_in_scope(plan, run, "deploy", "release:web-development")
        )
        self.assertFalse(
            execution_intent_target_in_scope(plan, run, "deploy", "release:web-production")
        )
        self.assertFalse(
            execution_intent_target_in_scope(
                plan, run, "merge_pr", "pr:https://github.com/o/r/pull/1"
            )
        )

        self.assertIn(
            "The harness runs it when `deploy` is authorized for that exact target at that "
            "exact head",
            core,
        )
        self.assertIn("One rule covers who runs the production deploy", lifecycle)
        self.assertIn(
            "The harness runs the production deploy command when `deploy` is authorized "
            "for that exact production `release:<target-id>` at that exact head",
            lifecycle,
        )
        # The merge stays the human's on both sites, and neither implies the other.
        for content in (core, lifecycle):
            self.assertIn("does not enable auto-merge", content)
        self.assertNotIn("does not run the production deploy", core)
        # The checkpoint no longer claims the parent performs the promotion merge.
        self.assertNotIn(
            "or performs the auto-deploy-triggering merge into `main`",
            lifecycle,
        )
        self.assertIn(
            "before it hands over the auto-deploy-triggering merge into `main`",
            lifecycle,
        )

    def test_deploy_target_prefix_records_the_schema_version_split(self) -> None:
        """v10 `targets` wants `release:`, the older v7-v9 `deployments` path
        wants `environment:`, and action-aware validation rejects the other
        schema version's target kind."""
        from harness_schema import TARGET_RE

        reference = self.read("references/execution-state-model.md")

        self.assertIsNotNone(TARGET_RE.fullmatch("release:web-production"))
        self.assertIsNotNone(TARGET_RE.fullmatch("environment:production"))

        self.assertIn("The `deploy` target prefix differs between those two shapes", reference)
        self.assertIn("requires `deploy` authorization for `release:<target-id>`", reference)
        self.assertIn("requires `environment:<target-id>` for the same grant", reference)
        self.assertIn(
            "Shared action/target rules reject the other schema version's target kind",
            reference,
        )

    def test_authorization_scope_binds_the_plan_digest_only_at_v10(self) -> None:
        """`SKILL.md` says a plan revision or digest change invalidates a grant.
        That is only true at v10, and the reference has to say so — below v10
        nothing compares a plan binding and a stale grant keeps matching."""
        from harness_authorization import authorization_covers

        reference = self.read("references/execution-state-model.md")

        def run_at(schema_version: int) -> dict:
            return {
                "schema_version": schema_version,
                "run_id": "RUN-1",
                "status": "running",
                "plan": {"revision": 4, "digest_sha256": "b" * 64},
                "authorizations": {
                    "push": {
                        "authorized": True,
                        "source": "user: build it",
                        "scope": {
                            "run_id": "RUN-1",
                            # Bound to a plan revision/digest that has moved on.
                            "plan_revision": 3,
                            "plan_digest_sha256": "a" * 64,
                            "mission_ids": ["M1"],
                            "targets": ["branch:development"],
                        },
                        "expires_when": "run_complete",
                    }
                },
            }

        self.assertFalse(
            authorization_covers(run_at(10), "push", "M1", "branch:development")
        )
        self.assertTrue(
            authorization_covers(run_at(9), "push", "M1", "branch:development")
        )

        self.assertIn("Schema v10 additionally requires `plan_revision` and `plan_digest_sha256`", reference)
        self.assertIn('"plan_digest_sha256": "<64-hex>"', reference)
        self.assertIn("the invalidation rule is inert there", reference)

    def test_unfilled_observed_snapshot_empties_dispatchable_nodes(self) -> None:
        """The old wording sent the operator looking for an empty
        `ready_frontier`. At draft/ready the frontier stays populated and only
        `dispatchable_nodes` empties, so the operator saw a full frontier and
        concluded the snapshot was already filled in."""
        core = self.read("SKILL.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        for content in (core, runbook):
            self.assertIn("`dispatchable_nodes`", content)
            self.assertIn("`deferred_nodes`", content)
            self.assertIn("parent_state_unreconciled", content)
            self.assertIn("batch_base_missing", content)
            self.assertIn("observed.captured_at", content)
            self.assertIn("dispatch-time reasons", content)
            self.assertNotIn("an empty frontier with every node deferred", content)
            self.assertNotIn("returns an empty frontier", content)

    def test_session_exact_reuse_lists_the_pass_signal_precondition(self) -> None:
        """The pass signal is the first condition the runtime checks and was the
        one missing from the core's list of four."""
        core = self.read("SKILL.md")
        runtime = self.read("scripts/verifier_runtime.py")

        self.assertIn("pass_signal_not_cacheable", runtime)
        self.assertIn(
            "may reuse a `session_exact` PASS only when the verifier's pass signal "
            "is the literal `exit 0`",
            core,
        )

    def test_cache_reuse_is_scoped_to_one_attempt_and_banned_layers_hold(self) -> None:
        """`same-session` over-promised: reuse is actually scoped to one attempt
        under one lease, because those IDs are in the execution key. The layer
        ban is now enforced at run time as well as at PLAN time."""
        from verifier_runtime import CACHE_BANNED_LAYERS

        core = self.read("SKILL.md")

        self.assertEqual(
            CACHE_BANNED_LAYERS,
            {"mission_integration", "batch", "final", "release"},
        )
        self.assertIn(
            "may reuse only an exact same-attempt `session_exact` PASS, bound to its "
            "`attempt_id` and `lease_id`",
            core,
        )
        self.assertIn("again at run time in `verifier_runtime.py`", core)
        self.assertNotIn("same-session", core)

    def test_readiness_requires_every_node_to_have_a_host(self) -> None:
        """A node whose `allowed_providers` no participating host satisfies is a
        readiness gap, not a surprise at dispatch time."""
        core = self.read("SKILL.md")

        readiness = core[core.index("### 3. Pass Plan Readiness") : core.index("### 4. Execute And Integrate")]
        self.assertIn("Executability covers the whole graph, not just the next node", readiness)
        self.assertIn("`allowed_providers`", readiness)
        self.assertIn("blocking readiness gap", readiness)
        # Reference paths in the core resolve from the skill root, unprefixed.
        self.assertIn("`references/graph-orchestration.md`", readiness)
        self.assertNotIn("`../references/graph-orchestration.md`", readiness)

    def test_release_target_ids_are_reused_from_architecture(self) -> None:
        """Both places that tell a planner to declare release targets used to
        read as an invitation to mint fresh IDs. This is a prose rule only — no
        harness script reads `architecture.md` — so nothing here may imply a
        validator checks it."""
        core = self.read("SKILL.md")
        lifecycle = self.read("references/cloudflare-deployment-lifecycle.md")

        self.assertIn(
            "When `architecture.md` has a `## Release Targets` section, reuse its target IDs "
            "verbatim instead of minting new ones",
            core,
        )
        self.assertIn(
            "Use the stable target IDs `architecture.md`'s `## Release Targets` section already declares",
            lifecycle,
        )
        self.assertIn("only when no such section exists", lifecycle)
        self.assertNotIn("Use stable target IDs such as", lifecycle)
        for content in (core, lifecycle):
            self.assertNotIn("the validator checks release target", content)

    def test_content_contract_row_treats_required_order_as_the_never_drop_set(self) -> None:
        """`requiredContentOrder` and "never-drop fields" are one set, not two.
        prd-builder contracts them that way; this row is the only place the
        harness names the term."""
        verification = self.read("references/verification-gates.md")

        row = next(
            line
            for line in verification.splitlines()
            if line.startswith("| Content contract conformance ")
        )
        self.assertIn(
            "every field in `design-system.json`'s `requiredContentOrder` renders, in that order "
            "— those fields never drop",
            row,
        )
        self.assertNotIn("and never-drop fields intact", row)

    def test_execution_intent_bundle_covers_both_hosts_worker_launch(self) -> None:
        """`create_user_owned_tasks` is Codex's worker launch and must be grouped
        with `spawn_subagents`, or the same instruction would mean different
        things on the two hosts."""
        core = self.read("SKILL.md")

        bundle = core[core.index("Nine of these actions") : core.index("That grouping is scoped")]
        for action in ("spawn_subagents", "create_user_owned_tasks"):
            self.assertIn(action, bundle)
        self.assertIn(
            "it is the Codex host's worker-launch action",
            core,
        )
        remaining = core[core.index("The remaining actions —") : core.index("`trigger_remote_ci` uses exact")]
        self.assertIn("archive_worker_tasks", remaining)
        self.assertNotIn("create_user_owned_tasks", remaining)

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

    def test_runbook_starts_local_only_and_names_all_three_modes(self) -> None:
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        # A fresh RUN has pushed nothing yet, so it still starts local_only.
        self.assertIn('"mode": "local_only"', runbook)
        self.assertIn('New RUN files start at `mode: "local_only"`', runbook)
        for mode in ("`local_only`", "`integration_push`", "`pull_request`"):
            self.assertIn(mode, runbook)
        self.assertIn(
            "only after the user separately asks for the pull request into the protected base",
            runbook,
        )

    @unittest.skipIf(REPO_ROOT is None, "repository rules require a source checkout")
    def test_repository_rules_do_not_shadow_concurrent_review_flow(self) -> None:
        repository_rules = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("request Codex review immediately after creation", repository_rules)
        self.assertIn("Observe current-head CI and review concurrently", repository_rules)
        self.assertIn("poll both gates concurrently", repository_rules)

    def test_production_promotion_waits_for_late_final_approval(self) -> None:
        skill = self.read_sibling_skill("fullstack-harness-github-landing")
        state = self.read("references/execution-state-model.md")
        goal = self.read("assets/templates/GOAL.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        project_rules = self.read("assets/templates/PROJECT_AGENTS.template.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn(
            "do not include a future protected-branch promotion",
            skill,
        )
        self.assertIn(
            "future-pr:<owner>/<repo>:base=<resolved-base>:head=<resolved-head>",
            skill,
        )
        self.assertIn("Do not put the later `main` landing", state)
        self.assertIn(
            "do not request or infer a future protected-branch promotion",
            goal,
        )
        self.assertIn(
            "Do not include protected-branch promotion in an ordinary mission run",
            runbook,
        )
        self.assertIn(
            "Do not request or infer a protected-branch pull request at Plan Readiness",
            project_rules,
        )
        self.assertIn("select authorized ready nodes", agent)
        for content in (skill, state, goal, runbook, project_rules):
            self.assertIn("manage_pr_review", content)
            self.assertIn("merge_pr", content)
            self.assertIn("future-pr:", content)

    def test_worktree_review_and_main_only_branch_policy(self) -> None:
        core = self.read("SKILL.md")
        codex = self.read_sibling_skill("fullstack-harness-codex")
        verification = self.read("references/verification-gates.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        project_rules = self.read("assets/templates/PROJECT_AGENTS.template.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        worktrees = self.read("references/worktree-thread-orchestration.md")

        self.assertIn("## Default Main-Only Branch Policy", core)
        self.assertIn("Target-repository governance wins", core)
        self.assertIn("at least one read-only review round", core)
        self.assertIn(
            "resolved target-repository integration branch",
            codex,
        )
        self.assertIn("Worktree pre-integration review gate", verification)
        self.assertIn('"branch": "refs/heads/codex/<short-name>"', runbook)
        self.assertIn('"head_branch": "refs/heads/codex/<short-name>"', runbook)
        self.assertIn('"base_branch": "main"', runbook)
        self.assertIn("one child must review the proposed diff", worker_goal)
        self.assertIn(
            "If the repository already defines another branch or pull-request model",
            project_rules,
        )
        self.assertIn(
            "Never start ordinary feature, PRD, or UI work from the resolved protected landing branch",
            project_rules,
        )
        self.assertIn('"source": "production_head"', plan)
        self.assertIn(
            "creates every worktree from the same recorded `batch_base_sha`",
            worktrees,
        )
        self.assertNotIn("recorded current `development` SHA", worktrees)

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

    def test_cloudflare_release_publishes_one_production_worker(self) -> None:
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

        self.assertIn("one repository and one codebase deployed to one production Worker", lifecycle)
        self.assertIn("`production` is a Cloudflare environment, not a Git branch", lifecycle)
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

        for content in (project_agents,):
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
        # The premium Claude model name is illustrative, not normative, so it is
        # deliberately not pinned here: pinning `claude-opus-4-8` in three files
        # is what let it rot in place. Assert the rule that outlives the name.
        for content in (skill, graph, plan):
            self.assertIn("for the parent's own coordination and planning", content)
            self.assertIn("sonnet", content)
            self.assertIn("gpt-5.6-sol", content)
            self.assertIn("xhigh", content)
        for content in (skill, graph):
            self.assertIn("haiku", content)
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

        self.assertIn("PROJECT_AGENTS.template.md", skill)
        self.assertNotIn("PROJECT_CLAUDE.template.md", skill)
        self.assertIn("seed a missing root `AGENTS.md`", skill)
        self.assertIn("a missing root `CLAUDE.md`", skill)
        self.assertIn("Skip either file that already exists", skill)
        self.assertIn(
            "never overwrite an established root `AGENTS.md` or `CLAUDE.md`", skill
        )
        self.assertIn("## Core Development Principles", project_agents)


if __name__ == "__main__":
    unittest.main()
