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
    def test_default_mission_topology_is_flat_isolated_and_integration_reviewed(self) -> None:
        skill = self.read("SKILL.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")
        project = self.read("assets/templates/PROJECT_AGENTS.template.md")

        self.assertIn("## Default Mission Topology", skill)
        self.assertIn("Map one independently testable goal to one mission", skill)
        self.assertIn("bounded read-only exploration", skill)
        self.assertIn("one explicit `write_scope`", skill)
        self.assertIn("Freeze shared APIs, schemas, and types", skill)
        self.assertIn("`git status --porcelain`", skill)
        self.assertIn("fresh parent-owned read-only reviewers", skill)
        self.assertIn("one planned broad final validation suite", skill)
        self.assertIn("Workers and reviewers never delegate", skill)
        self.assertIn("## No Nested Delegation", worker)
        self.assertIn("explicit file-ownership scope", project)

    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def read_sibling_skill(self, name: str) -> str:
        return (SKILLS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")

    def read_sibling_agent(self, name: str) -> str:
        return (SKILLS_ROOT / name / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )


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
        self.assertIn("lightest safe direct or PLAN-v5/RUN-v10 delivery path", agent)
        self.assertIn("A high file count", skill)
        self.assertIn("does not make work `large` by itself", skill)

    def test_progressive_disclosure_keeps_routine_context_bounded(self) -> None:
        core = self.read("SKILL.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")
        result_contract = self.read("references/worker-result-contract.md")
        adapters = (
            self.read_sibling_skill("fullstack-harness-codex"),
            self.read_sibling_skill("fullstack-harness-claude-code"),
            self.read_sibling_skill("fullstack-harness-pi"),
        )

        self.assertLess(len(core.split()), 3500)
        self.assertLess(len(worker.split()), 1200)
        for adapter in adapters:
            self.assertLess(len(adapter.split()), 1400)
            self.assertIn("This adapter adds no alternate state or handoff rules", adapter)
        self.assertIn("Read this reference only while rendering or validating", result_contract)
        self.assertIn("Result contract:", worker)

    def test_system_review_and_route_is_parent_only_before_managed_work(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        graph = self.read("references/graph-orchestration.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        goal = self.read("assets/templates/GOAL.template.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")

        for content in (skill, state, graph, runbook, goal):
            self.assertIn("System Review And Route", content)
            self.assertIn("parent-only", content)
            self.assertIn("read-only", content)
        self.assertIn("before loading any task-specific skill", skill)
        self.assertIn("Do not create or edit `PLAN.md`, `RUN.md`", skill)
        self.assertIn("does not load a task skill", state)
        self.assertIn("is not a PLAN node", graph)
        self.assertIn("The System Review And Route stage completes before this file exists", runbook)
        self.assertIn("before this delegated handoff exists", worker)
        self.assertLess(skill.index("### System Review And Route"), skill.index("## Adapter Routing"))
        self.assertLess(skill.index("### System Review And Route"), skill.index("### 2. Plan Large Work"))

    def test_new_managed_work_requires_plan_run_and_legacy_compact_is_read_only(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        goal = self.read("assets/templates/GOAL.template.md")

        for content in (skill, state, runbook, goal):
            self.assertIn("PLAN schema v5", content)
            self.assertIn("RUN schema v10", content)
            self.assertIn("legacy compact run-only", content.lower())
            self.assertIn("read", content.lower())
        self.assertIn("New managed work never authors a compact RUN-only artifact", skill)
        self.assertIn("cannot authorize new managed execution", state)
        self.assertIn("not a new authoring route", runbook)
        self.assertNotIn("compact large sequential work", runbook.lower())
        self.assertNotIn("Planning depth: direct | compact RUN", skill)

    def test_large_no_agent_route_is_real_parent_sequential_execution(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        selector = self.read("references/parallel-mission-selection.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        goal = self.read("assets/templates/GOAL.template.md")

        for content in (skill, state, selector, orchestration, runbook, goal):
            self.assertIn("sequential_parent", content)
            self.assertIn("parent", content)
            self.assertIn("one mission at a time", content)
        self.assertIn("no `spawn_subagents`", skill)
        self.assertIn("no `spawn_subagents`", state)
        self.assertIn("parent-managed worktree", state)
        self.assertIn("does not require `spawn_subagents`", orchestration)
        self.assertIn("blocks when the required parent-managed worktree is unavailable or unauthorized", orchestration)
        self.assertIn("does not require `spawn_subagents`", selector)
        self.assertIn("required large no-agent path", runbook)

    def test_sequential_parent_records_parent_executor_binding_without_shared_fallback(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        graph = self.read("references/graph-orchestration.md")
        selector = self.read("references/parallel-mission-selection.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        goal = self.read("assets/templates/GOAL.template.md")

        for content in (skill, state, graph, selector, runbook, goal):
            self.assertIn("runtime_worker", content)
            self.assertIn("parent-owned", content)
            self.assertIn("parent_managed_worktree", content)
            self.assertIn("agent_result", content)
        self.assertIn("parent-owned executor/worker binding solely for lease/state validation", state)
        self.assertIn("does not require `spawn_subagents`", selector)
        self.assertIn("route blocks rather than writing in `shared_checkout`", skill)
        self.assertNotIn("no worker identity", state.lower())
        self.assertNotIn("no worker record", selector.lower())
        self.assertNotIn("shared-checkout fallback", runbook.lower())
        self.assertNotIn("harness_parent", graph[graph.index("If the large route"):graph.index("For current PLAN")])

    def test_v10_forbids_nested_delegation_and_keeps_legacy_readable(self) -> None:
        state = self.read("references/execution-state-model.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        selector = self.read("references/parallel-mission-selection.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        goal = self.read("assets/templates/GOAL.template.md")

        for content in (state, runbook, orchestration):
            self.assertIn("RUN-v10", content)
            self.assertIn("parent", content.lower())
        self.assertIn("accepts only an omitted `nested_subagent_policy` or one with `enabled: false`", state)
        self.assertIn("RUN v6 through v9 retain their legacy nested-policy compatibility", state)
        self.assertIn("RUN-v10 workers never delegate", runbook)
        self.assertIn("Workers and reviewers never spawn or delegate further", orchestration)
        self.assertNotIn("app-task fan-out includes `spawn_subagents`", selector.lower())
        self.assertNotIn("enabled v10 policy", state.lower())

    def test_execution_intent_covers_route_subset_not_all_nine_actions(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn("only the applicable local entries", state)
        self.assertIn("outer v10 `app_threads` app-task route excludes `spawn_subagents`", state)
        self.assertIn("app-task workers never delegate", state)
        self.assertIn("Parent-dispatched direct sibling workers and reviewers", state)
        self.assertIn("does not authorize `push`", skill)
        self.assertIn("separate explicit remote instruction", runbook)
        for content in (skill, state, runbook):
            self.assertNotIn("covers all nine together", content)
            self.assertNotIn("one execution-intent instruction covers all nine", content)

    def test_same_repository_host_handoff_is_serialized_and_exact_head_bound(self) -> None:
        state = self.read("references/execution-state-model.md")
        graph = self.read("references/graph-orchestration.md")

        for content in (state, graph):
            self.assertIn("Serialized Same-Repository Host Handoff", content)
            self.assertIn("only", content)
            self.assertIn("active_wave", content)
            self.assertIn("PLAN/RUN", content)
            self.assertIn("exact", content.lower())
            self.assertIn("Host B", content)
            self.assertIn("re-probe", content)
            self.assertIn("replaces", content)
            self.assertIn("fix_required", content)
            self.assertIn("new head invalidates", content)
            self.assertIn("cross-machine handoff", content.lower())
            self.assertIn("unsupported", content.lower())
        self.assertIn("not an in-session bridge", state)
        self.assertIn("not an in-session bridge", graph)

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
        self.assertIn("probe for a Claude Code CLI, binary, or plugin as a substitute route", codex_skill)
        self.assertIn("probe for an installed Codex CLI or plugin as a substitute route", claude_skill)
        self.assertIn("there is no cross-host preflight, no bridged process, and no declared fallback", research)
        self.assertIn("blocked on provider mismatch rather than probing or launching the other runtime", research)

    def test_authorized_app_wave_requires_real_thread_launch(self) -> None:
        skill = self.read_sibling_skill("fullstack-harness-codex")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        selector = self.read("references/parallel-mission-selection.md")
        goal = self.read("assets/templates/GOAL.template.md")
        agent = self.read_sibling_agent("fullstack-harness-codex")

        self.assertIn("Do not stop after printing a non-empty app-task wave", skill)
        self.assertIn("consume every accepted dispatch entry", skill)
        self.assertIn("Search the current Codex tool surface", skill)
        self.assertIn("top-level left-sidebar app task", skill)
        self.assertIn("## Launch Selected Codex App Threads", orchestration)
        self.assertIn("one top-level worktree task/thread per mission", orchestration)
        self.assertIn("Read-only explorers and reviewers are parent-dispatched siblings", orchestration)
        self.assertIn("never children of a mission task", orchestration)
        self.assertIn("direct subagent of the coordinator is not equivalent", selector)
        self.assertIn("one top-level left-sidebar task", goal)
        self.assertIn("probe app-task and subagent surfaces", agent)
        self.assertIn("Never replace explicitly requested independent app tasks", skill)
        self.assertIn("Codex-hosted managed run", agent)

    def test_plan_backed_runs_detect_then_select_full_frontier(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        selector = self.read("references/parallel-mission-selection.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("## Default Runtime And Wave Policy", skill)
        self.assertIn("Proactively inspect the current-session native tool surface", skill)
        self.assertIn("Missing authorization must never make an available driver disappear", skill)
        self.assertIn("complete per-surface `capability_probe`", skill)
        self.assertIn("provably sequential route", skill)
        self.assertIn("Do not cap `max_parallel_workers` at a small fixed number", skill)
        self.assertIn("default immediately after Plan Readiness", state)
        self.assertIn("capability_snapshot_incomplete", state)
        self.assertIn("capability_snapshot_incomplete", selector)
        self.assertIn("full eight-entry `capability_probe`", orchestration)
        self.assertIn("may omit unused surfaces", orchestration)
        self.assertIn("may select two writers", runbook)
        self.assertIn("provably sequential route records only", runbook)
        self.assertIn("## Default Plan-Backed Wave", orchestration)
        self.assertIn("selection is the default post-readiness action", selector)
        self.assertIn("Never run parallel writers in `shared_checkout`", runbook)
        self.assertIn("lightest safe direct or PLAN-v5/RUN-v10 delivery path", agent)
        self.assertIn("Host adapter: none | codex | claude_code | pi | generic", skill)

    def test_workers_never_delegate_and_parent_owns_reviews(self) -> None:
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn("## No Nested Delegation", worker_goal)
        self.assertIn("Do not spawn, create, or delegate to another agent", worker_goal)
        self.assertIn("All explorers, writers, and reviewers are parent-dispatched siblings", worker_goal)
        self.assertIn("RUN-v10 workers never delegate", runbook)
        self.assertIn("all reviews are parent-dispatched graph nodes", runbook)

    def test_frontend_design_has_creation_and_conformance_modes(self) -> None:
        skill = self.read("SKILL.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        design_updates = self.read("references/design-input-updates.md")

        for content in (skill, plan, worker_goal):
            self.assertIn("frontend-design conformance mode", content)
            self.assertIn("design-input delta", content)
            self.assertIn("product-design-builder", content)
            self.assertIn("creation mode", content)
        self.assertIn("user explicitly selected it", plan)
        self.assertIn("new or high-impact visual surface", plan)
        self.assertIn("proposed design-input delta", design_updates)
        self.assertIn("Return it to `product-design-builder`", design_updates)

    def test_page_reference_modes_do_not_bypass_frozen_design_sources(self) -> None:
        skill = self.read("SKILL.md")
        updates = self.read("references/design-input-updates.md")

        self.assertIn("Design inspiration", updates)
        self.assertIn("Page-faithful target", updates)
        self.assertIn("non-canonical evidence", updates)
        self.assertIn("only after the user requests faithful matching", updates)
        self.assertIn("Source version / hash", updates)
        self.assertIn("Tolerance / allowed deviations", updates)
        self.assertIn("`product-design-builder` must normalize either accepted source type", updates)
        self.assertIn("user explicitly requests faithful conformance", skill)

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

        self.assertIn("Keep all 12 schema-v10 RUN authorization entries false", goal)
        self.assertIn("invoke_external_runtime", goal)
        self.assertIn("one top-level left-sidebar task with its own clean exact-base app-managed worktree", goal)

    def test_run_template_matches_the_local_only_default(self) -> None:
        """The template must keep remote publication behind explicit intent."""
        skill = self.read("SKILL.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn("default to `local_only`", skill)
        self.assertIn("integration_push", runbook)
        self.assertIn("landing.pushed_head_sha", runbook)
        self.assertIn("separate remote intent", runbook)
        self.assertIn('New RUN files start at `mode: "local_only"`', runbook)








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
        self.assertIn("`session_exact` PASS only when the verifier's pass signal is the literal `exit 0`", core)


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
        self.assertIn("`requiredContentOrder` renders, in that order", row)
        self.assertIn("those fields never drop", row)
        self.assertNotIn("and never-drop fields intact", row)




    @unittest.skipIf(REPO_ROOT is None, "repository rules require a source checkout")






    def test_builder_ux_direction_is_ready_before_implementation_and_not_usability_proof(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/contract-and-traceability.md")
        updates = self.read("references/design-input-updates.md")
        verification = self.read("references/verification-gates.md")
        plan_template = self.read("assets/templates/HARNESS_PLAN.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        e2e_template = self.read("assets/templates/E2E_VERIFICATION.template.md")
        goal = self.read("assets/templates/GOAL.template.md")

        for content in (skill, contract, updates, verification, plan_template, runbook, e2e_template, goal):
            self.assertIn("Builder UX Direction", content)
        self.assertIn("every must-have `UX-*` trace", skill)
        self.assertIn("## UX Direction And Usability Evidence", verification)
        self.assertIn("Builder approval proves only direction conformance", verification)
        self.assertIn("## UX Evidence", runbook)

    def test_stop_and_ask_separates_validator_and_judgment_stops(self) -> None:
        contract = self.read("references/contract-and-traceability.md")
        verification = self.read("references/verification-gates.md")

        self.assertIn("### Validator-Enforced Stops", contract)
        self.assertIn("### Judgment Stops", contract)
        self.assertLess(
            contract.index("### Validator-Enforced Stops"),
            contract.index("### Judgment Stops"),
        )
        # Readiness/authorization stops are blocked by the wave selector, not
        # the manifest validator; the section must name both tools.
        self.assertIn("select_ready_nodes.py", contract)
        self.assertIn("No script parses that table", contract)
        # The pair invariant is re-checked downstream, not only by the
        # authoring skill, and a hand-edited half-pair is a stop condition.
        # The command must be runnable (both required args) and read-only.
        for content in (contract, verification):
            self.assertIn(
                "check_design_system_pair.py --markdown <design-system.md>"
                " --registry <design-system.json> --require-filled",
                content,
            )
            self.assertIn("--write", content)
        self.assertIn("Design-system pair check", verification)
        # execution-task-decomposition.md points at this stop condition; keep
        # the cross-reference from dangling again, and never present the
        # classification as a manifest field the schema would reject.
        self.assertIn("migration classification unset", contract)
        self.assertIn("not a manifest field", contract)
        # The validator checks review coverage existence, not review.type
        # fitness; type appropriateness must stay a judgment stop.
        self.assertIn("without comparing `review.type` to the write scope", contract)
        self.assertNotIn("as applicable) covering it", contract)

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
        self.assertIn('"preferred_provider": null', plan)
        self.assertIn('"allowed_providers": ["codex", "claude_code", "pi", "generic"]', plan)
        self.assertIn('"pi": {"model": null, "reasoning_effort": null}', plan)
        self.assertIn('"generic": {"model": null, "reasoning_effort": null}', plan)
        # A delegated Claude Code node never defaults above sonnet: the pinned
        # top-tier model is reserved for the parent's own coordination/planning,
        # not assigned to any worker/review node by default.
        self.assertGreaterEqual(plan.count('"model": "sonnet"'), 3)
        self.assertGreaterEqual(plan.count('"model": "gpt-5.6-sol"'), 3)
        self.assertIn("gpt-5.6-terra", skill)
        self.assertIn('"reasoning_effort": "high"', plan)
        self.assertIn("Plan Mode chooses", graph)
        self.assertIn("provider-specific model options", skill)
        self.assertIn("general and backend implementation: Codex `gpt-5.6-terra`, `high`", skill)
        self.assertIn("prefer Codex `gpt-5.6-terra` with `high` reasoning", plan)
        self.assertIn("routine deterministic `backend_code` review: Codex `gpt-5.6-terra`, `medium`", skill)
        self.assertIn("routine frontend, backend, visual, and integration review: `sonnet`, `medium`", skill)
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
        self.assertIn("New managed work uses PLAN schema v5 and RUN schema v10", skill)
        self.assertIn("complete` is an execution closeout state", state)
        for content in (skill, verification, runbook):
            self.assertIn("breakpoint-by-state", content)
            self.assertIn("SHA-256", content)
            self.assertIn("docs/goal/evidence/", content)

    def test_bootstrap_seeds_agents_and_claude_governance_templates(self) -> None:
        skill = self.read("SKILL.md")
        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")
        project_claude = self.read("assets/templates/PROJECT_CLAUDE.template.md")
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        configurator = self.read("scripts/configure_project_context.py")

        self.assertIn("PROJECT_AGENTS.template.md", skill)
        self.assertIn("PROJECT_CLAUDE.template.md", skill)
        self.assertIn("## Repository Context Contract", skill)
        self.assertIn("scripts/configure_project_context.py --root <target-root>", skill)
        self.assertIn("generated files are intentionally different", skill)
        self.assertIn("Pi's native per-directory priority", skill)
        self.assertIn("Never overwrite, merge, normalize, or silently copy", skill)
        self.assertIn("Host-specific repository context:", worker_goal)
        self.assertIn("Runtime-specific worker contract:", worker_goal)
        self.assertIn("Keep automatic context discovery enabled", worker_goal)
        self.assertIn('path.open("xb")', configurator)
        self.assertIn("## Runtime Boundary", project_agents)
        self.assertIn("Codex and Pi load it as their native project context", project_agents)
        self.assertIn("## Core Development Principles", project_agents)
        self.assertIn("@AGENTS.md", project_claude)
        self.assertIn("## Claude Code Runtime Boundary", project_claude)

    def test_branch_names_are_explicit_and_have_no_harness_prefix(self) -> None:
        policy_paths = (
            "SKILL.md",
            "agents/openai.yaml",
            "references/execution-state-model.md",
            "references/verification-gates.md",
            "references/worktree-thread-orchestration.md",
            "assets/templates/GOAL.template.md",
            "assets/templates/MISSION_RUNBOOK.template.md",
            "assets/templates/PROJECT_AGENTS.template.md",
        )
        for path in policy_paths:
            with self.subTest(path=path):
                content = self.read(path)
                self.assertNotIn("codex/<short-name>", content)

        skill = self.read("SKILL.md")
        project = self.read("assets/templates/PROJECT_AGENTS.template.md")
        ci = self.read("assets/templates/PROJECT_CI.template.yml")
        codex_adapter = self.read_sibling_skill("fullstack-harness-codex")

        for content in (skill, project):
            self.assertIn("never add a fixed prefix", content.lower())
        self.assertIn("does not own shared state", codex_adapter)
        self.assertIn("ask before branch creation", skill.lower())
        self.assertIn("- '**'", ci)
        self.assertNotIn("codex/**", ci)


if __name__ == "__main__":
    unittest.main()
