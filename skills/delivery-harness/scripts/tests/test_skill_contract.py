import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (
            (candidate / "skills" / "delivery-harness" / "SKILL.md").is_file()
            and (candidate / "package.json").is_file()
        ):
            return candidate
    return None


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)


class DeliveryHarnessSkillContractTests(unittest.TestCase):
    @unittest.skipIf(REPO_ROOT is None, "brand contract requires a source checkout")
    def test_product_delivery_harness_brand_and_skill_ids_are_canonical(self) -> None:
        package = (REPO_ROOT / "package.json").read_text(encoding="utf-8")
        self.assertIn('"name": "product-delivery-harness"', package)
        self.assertIn('"version": "0.35.3"', package)
        self.assertEqual(
            "0.35.3",
            (REPO_ROOT / "skills" / "delivery-harness" / "VERSION")
            .read_text(encoding="utf-8")
            .strip(),
        )
        self.assertFalse(
            (REPO_ROOT / "Tasks.md").exists(),
            "the source repository must not keep a root Tasks.md flow log",
        )

        skills_root = REPO_ROOT / "skills"
        current = {
            "delivery-harness": "Delivery Harness",
            "product-definition-builder": "Product Definition Builder",
            "design-system-compiler": "Design System Compiler",
            "code-security-review": "Code Security Review",
            "product-activation": "Product Activation",
        }
        for skill_id, display_name in current.items():
            with self.subTest(skill=skill_id):
                skill_root = skills_root / skill_id
                self.assertTrue((skill_root / "SKILL.md").is_file())
                self.assertIn(
                    f"name: {skill_id}",
                    (skill_root / "SKILL.md").read_text(encoding="utf-8"),
                )
                self.assertIn(
                    f'display_name: "{display_name}"',
                    (skill_root / "agents" / "openai.yaml").read_text(encoding="utf-8"),
                )

        for legacy in ("full-harness", "prd-builder", "product-design-builder"):
            self.assertFalse((skills_root / legacy).exists())

        for readme_name in ("README.md", "README.zh-TW.md", "README.zh-CN.md", "README.es.md"):
            with self.subTest(readme=readme_name):
                readme = (REPO_ROOT / readme_name).read_text(encoding="utf-8")
                self.assertIn("Product Delivery Harness", readme)
                self.assertIn("`delivery-harness`", readme)
                self.assertIn("`product-definition-builder`", readme)
                self.assertIn("`design-system-compiler`", readme)
                self.assertIn("`code-security-review`", readme)
                self.assertIn("`product-activation`", readme)

    @unittest.skipIf(REPO_ROOT is None, "install migration requires a source checkout")
    def test_renamed_installs_have_a_recoverable_legacy_migration(self) -> None:
        documents = {
            "AGENTS.md": (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            "runtime-upgrades.md": self.read("references/runtime-upgrades.md"),
            **{
                name: (REPO_ROOT / name).read_text(encoding="utf-8")
                for name in ("README.md", "README.zh-CN.md", "README.zh-TW.md", "README.es.md")
            },
        }
        for name, content in documents.items():
            with self.subTest(document=name):
                for skill_id in (
                    "full-harness",
                    "prd-builder",
                    "product-design-builder",
                    "delivery-harness",
                    "product-definition-builder",
                    "design-system-compiler",
                    "code-security-review",
                    "product-activation",
                ):
                    self.assertIn(f"`{skill_id}`", content)
                self.assertIn(
                    "~/.agents/skill-backups/product-delivery-harness/", content
                )
                self.assertIn("~/.agents/skills/", content)

        agents = documents["AGENTS.md"]
        runtime = documents["runtime-upgrades.md"]
        self.assertIn("never overwrite or delete", agents)
        self.assertIn("Never overwrite or delete", runtime)
        self.assertIn("Restore the backup if verification fails", agents)
        self.assertIn("Restore the backup if verification fails", runtime)
        readme_backup_phrases = {
            "README.md": "archive the legacy directories under their original IDs",
            "README.zh-CN.md": "用原 ID 保存各旧目录",
            "README.zh-TW.md": "用原 ID 保存各舊目錄",
            "README.es.md": "archiva los directorios heredados bajo sus IDs originales",
        }
        for name, phrase in readme_backup_phrases.items():
            with self.subTest(readme=name, rule="original backup id"):
                self.assertIn(phrase, documents[name])
                for old_id, new_id in (
                    ("full-harness", "delivery-harness"),
                    ("prd-builder", "product-definition-builder"),
                    ("product-design-builder", "design-system-compiler"),
                ):
                    self.assertIn(
                        f"`{old_id}` → `{new_id}`", documents[name]
                    )

    def test_default_mission_topology_is_flat_isolated_and_integration_reviewed(self) -> None:
        skill = self.read("SKILL.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")
        project = self.read("assets/templates/PROJECT_AGENTS.template.md")

        self.assertIn("## Default Mission Topology", skill)
        self.assertIn("Map one independently testable goal to one mission", skill)
        self.assertIn("one bounded worker slice", skill)
        self.assertIn("10-20 minutes", skill)
        self.assertIn("no wall-time percentage target", skill)
        self.assertIn("stop paying for the same work twice", skill)
        self.assertIn("bounded read-only exploration", skill)
        self.assertIn("one explicit `write_scope`", skill)
        self.assertIn("Freeze shared APIs, schemas, and types", skill)
        self.assertIn("`git status --porcelain`", skill)
        self.assertIn("one planned parent-owned read-only reviewer", skill)
        self.assertIn("at most one repair-and-re-review cycle", skill)
        self.assertIn("do not dispatch another same-scope review", skill)
        self.assertIn("do not attach the full PLAN/RUN", skill)
        self.assertIn("one planned broad final validation suite", skill)
        self.assertIn("Workers and reviewers never delegate", skill)
        self.assertIn("## No Nested Delegation", worker)
        self.assertIn("explicit file-ownership scope", project)

    def test_missions_are_cohesive_and_tasks_keep_atomic_commit_boundaries(self) -> None:
        skill = self.read("SKILL.md")
        decomposition = self.read("references/execution-task-decomposition.md")
        convention = self.read("references/commit-convention.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")
        result_validator = self.read("scripts/validate_worker_result.py")

        self.assertIn("A mission is not a phase label", skill)
        self.assertIn("Pass the Mission Cohesion Gate", skill)
        self.assertIn("## Mission Cohesion Gate", decomposition)
        self.assertIn("Shared foundations do not justify a catch-all mission", decomposition)
        self.assertIn("Expected merge conflicts are scheduling facts", decomposition)
        self.assertIn("Before readiness, apply", plan)
        self.assertIn("Every executable task gets its own initial atomic commit", convention)
        self.assertIn("## Run-Wide Atomicity", convention)
        self.assertIn("never an unrelated fix, cleanup, or formatting", convention)
        self.assertIn("never product code", convention)
        self.assertIn("never folded into the merge body", convention)

        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")
        self.assertIn("### Commit Messages", project_agents)
        self.assertIn(
            "follows `delivery-harness/references/commit-convention.md`", project_agents
        )
        self.assertIn("<type>(<scope>): <imperative summary>", project_agents)
        self.assertIn("One commit holds one kind of change", project_agents)
        self.assertIn("exactly one task ID", project_agents)
        self.assertIn("never a fake task body", project_agents)
        orchestration = self.read("references/worktree-thread-orchestration.md")
        self.assertIn(
            "Keep the integration commit atomic per `commit-convention.md`'s Run-Wide Atomicity rule",
            orchestration,
        )
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        self.assertIn(
            "the closeout itself never lands a mixed catch-all commit", runbook
        )
        self.assertIn("only then begin the next task", worker)
        self.assertIn("commit_order_mismatch", result_validator)

    def test_related_review_findings_escalate_by_root_cause_across_revisions(self) -> None:
        skill = self.read("SKILL.md")
        graph = self.read("references/graph-orchestration.md")
        decomposition = self.read("references/execution-task-decomposition.md")
        verification = self.read("references/verification-gates.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")

        self.assertIn("root-cause failure family", skill)
        self.assertIn("A generic instruction to continue", skill)
        self.assertIn("## Root-Cause Repair Escalation", graph)
        self.assertIn("open grammar needs an appropriate scanner, parser, state machine", graph)
        self.assertIn("stable mission + review surface + root-cause lineage", graph)
        self.assertIn("A mission-level replan does not replenish a review budget", decomposition)
        self.assertIn("Do not authorize another example-specific patch", verification)
        self.assertIn("A replan does not grant a fresh review budget", plan)
        self.assertIn("Repair context (omit for an initial implementation)", worker)
        self.assertIn("fix the named root-cause family", worker)

    def test_scripted_transition_flag_surfaces_are_documented(self) -> None:
        state = self.read("references/execution-state-model.md")
        skill = self.read("SKILL.md")
        self.assertIn("### Scripted Transition Flag Surfaces", state)
        self.assertIn("`pause`, `resume`, `cancel`: `--source`", state)
        self.assertIn("--additional-attempts", state)
        self.assertIn("--ancestry-confirmed", state)
        self.assertIn("--packet-out", state)
        self.assertIn("--security-result", state)
        self.assertIn(
            "`pause`, `resume`, or `cancel`, each requiring `--source`", skill
        )

    def test_managed_review_dispatch_is_reserved_and_independent(self) -> None:
        skill = self.read("SKILL.md")
        graph = self.read("references/graph-orchestration.md")
        state = self.read("references/execution-state-model.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        transition = self.read("scripts/harness_transition.py")
        adapters = self.read("references/runtime-adapters.md")

        for content in (skill, graph, state, runbook, adapters):
            self.assertIn("reserve-review-dispatch", content)
        self.assertIn("independent_reviewer_unavailable", graph)
        self.assertIn("cannot satisfy a fresh independent review node", adapters)
        self.assertIn("no matching reserved dispatch receipt", transition)
        self.assertIn("already used its one owner-granted successor", transition)

    def test_runtime_performance_contract_is_machine_measured_and_safety_preserving(self) -> None:
        performance = self.read("references/runtime-performance.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        verifier = self.read("scripts/verifier_runtime.py")

        # No percentage target: the old 75/85 figures were never measured
        # against anything, and chasing an invented number pressures a run
        # toward slicing too small or skipping a gate.
        self.assertNotIn("75%", performance)
        self.assertNotIn("85%", performance)
        self.assertIn("carries no percentage target", performance)
        self.assertIn("Re-dispatching a reviewer against a commit", performance)
        self.assertIn("context capsule", performance)
        self.assertIn("cursor wait", performance)
        self.assertIn("read-only pre-integration review", performance)
        self.assertIn("execution.parallel_safe", performance)
        # Turn count is a runtime cost like any other; pin the contract that
        # says which reads batch and which stay their own stop.
        self.assertIn("Parent Turn Boundaries", performance)
        self.assertIn("harness_step.py", performance)
        self.assertIn("validate_result.py", performance)
        self.assertIn("never weakens authorization", performance)
        self.assertIn('"runtime_metrics"', runbook)
        self.assertNotIn("target_reduction_percent", runbook)
        self.assertIn("BATCH_PROTOCOL", verifier)

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
        self.assertIn("lightest safe direct or PLAN-v6/RUN-v11 delivery path", agent)
        self.assertIn("A high file count", skill)
        self.assertIn("does not make work `large` by itself", skill)

    def test_progressive_disclosure_keeps_routine_context_bounded(self) -> None:
        core = self.read("SKILL.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")
        result_contract = self.read("references/worker-result-contract.md")
        runtime_adapters = self.read("references/runtime-adapters.md")

        self.assertLess(len(core.split()), 3600)
        self.assertLess(len(worker.split()), 1200)
        # One shared contract plus one section per provider replaces the three
        # adapter skills; the merged file stays near what those three weighed.
        self.assertLess(len(runtime_adapters.split()), 3700)
        self.assertIn(
            "This adapter adds no alternate state or handoff rules", runtime_adapters
        )
        self.assertIn("Read this reference only while rendering or validating", result_contract)
        self.assertIn("Result contract:", worker)

    def test_system_review_and_route_is_parent_only_before_managed_work(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        graph = self.read("references/graph-orchestration.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        goal = self.read("assets/templates/GOAL.template.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")

        # Named everywhere it matters; described once, in execution-state-model.md.
        for content in (skill, state, graph, runbook, goal):
            self.assertIn("System Review And Route", content)
        for content in (skill, state, runbook, goal):
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
            self.assertIn("PLAN schema v6", content)
            self.assertIn("RUN schema v11", content)
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
        # The full binding rules live once in execution-state-model.md's
        # anchored section; every other file points at that heading.
        self.assertIn("## Sequential Parent Route", state)
        self.assertIn("one mission at a time", state)
        self.assertIn("no `spawn_subagents`", state)
        self.assertIn("parent-managed worktree", state)
        self.assertIn("one mission at a time", skill)
        for content in (skill, selector, orchestration, runbook, goal):
            self.assertIn("Sequential Parent Route", content)

    def test_sequential_parent_records_parent_executor_binding_without_shared_fallback(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        graph = self.read("references/graph-orchestration.md")
        selector = self.read("references/parallel-mission-selection.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        goal = self.read("assets/templates/GOAL.template.md")

        # The binding is defined once, under an anchored heading in
        # execution-state-model.md. Every other file points at that heading;
        # a restatement is what drifts.
        self.assertIn("## Sequential Parent Route", state)
        self.assertIn("parent-owned executor/worker binding solely for lease/state validation", state)
        self.assertIn("worker_runtime: parent", state)
        self.assertIn("parent_managed_worktree", state)
        self.assertIn("agent_result", state)
        self.assertIn("route blocks rather than writing in `shared_checkout`", state)
        for content in (skill, selector, runbook, goal):
            self.assertIn("Sequential Parent Route", content)
            # The backticked binding spelling belongs to the definition only;
            # GOAL's plain option menu (worker_runtime: parent | ...) is not a
            # restatement.
            self.assertNotIn("`worker_runtime: parent`", content)
        for content in (graph, selector):
            self.assertIn(
                "`execution-state-model.md`'s `sequential_parent` definition", content
            )
        self.assertNotIn("no worker identity", state.lower())
        self.assertNotIn("no worker record", selector.lower())
        self.assertNotIn("shared-checkout fallback", runbook.lower())
        self.assertNotIn("harness_parent", graph[graph.index("If the large route"):graph.index("For current PLAN")])

    def test_v10_forbids_nested_delegation_and_keeps_legacy_readable(self) -> None:
        state = self.read("references/execution-state-model.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        selector = self.read("references/parallel-mission-selection.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")

        for content in (state, runbook, orchestration):
            self.assertIn("RUN-v11", content)
            self.assertIn("parent", content.lower())
        self.assertIn("accepts only an omitted `nested_subagent_policy` or one with `enabled: false`", state)
        self.assertIn("RUN v6 through v9 retain their legacy nested-policy compatibility", state)
        self.assertIn("RUN-v11 workers never delegate", runbook)
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

        # The rules live once, in execution-state-model.md; graph-orchestration
        # keeps the heading and its one graph-specific rule so a reader lands
        # somewhere, without a second copy that can drift.
        for content in (state, graph):
            self.assertIn("Serialized Same-Repository Host Handoff", content)
        for assertion in (
            "only",
            "active_wave",
            "PLAN/RUN",
            "Host B",
            "re-probe",
            "replaces",
            "fix_required",
            "new head invalidates",
        ):
            self.assertIn(assertion, state)
        for assertion in ("exact", "cross-machine handoff", "unsupported"):
            self.assertIn(assertion, state.lower())
        self.assertIn("does not gain a host-handoff node", graph)
        self.assertIn("not an in-session bridge", state)

    @unittest.skipIf(REPO_ROOT is None, "README contract requires a source checkout")
    def test_skill_bindings_make_the_catalog_a_project_setting(self) -> None:
        skill = self.read("SKILL.md")
        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")

        self.assertIn(
            "fills the new `AGENTS.md`'s Skill Bindings table from locally observed skills",
            skill,
        )
        self.assertIn("## Skill Bindings", project_agents)
        self.assertIn("| design_direction |", project_agents)
        self.assertIn("| design_compilation |", project_agents)
        self.assertIn("| frontend_implementation |", project_agents)
        self.assertIn("| ui_quality_verification |", project_agents)
        self.assertIn("| code_security_verification |", project_agents)
        self.assertIn("a project edit, not a harness change", project_agents)
        self.assertIn("An unbound slot uses the bundled default", project_agents)
        # Required Reading names the installed orchestration skill itself; the
        # Skill Bindings table binds only the stage slots it dispatches.
        self.assertIn(
            "the installed `delivery-harness` SKILL.md (the orchestration skill itself",
            project_agents,
        )
        self.assertNotIn("bound in the Skill Bindings table", project_agents)
        self.assertIn("Skill Bindings table in its `AGENTS.md`", skill)

    @unittest.skipIf(REPO_ROOT is None, "security skill requires a source checkout")
    def test_code_security_review_is_exact_sha_read_only_and_blocking(self) -> None:
        security = (
            REPO_ROOT / "skills" / "code-security-review" / "SKILL.md"
        ).read_text(encoding="utf-8")
        contract = (
            REPO_ROOT
            / "skills"
            / "code-security-review"
            / "references"
            / "review-contract.md"
        ).read_text(encoding="utf-8")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        gates = self.read("references/verification-gates.md")

        for phrase in (
            "exact candidate SHA",
            "fresh sibling reviewer",
            "The reviewer never delegates",
            "Do not edit files",
            "not for live penetration testing",
        ):
            self.assertIn(phrase, security)
        self.assertIn("integration-stage runtime review", contract)
        self.assertIn("never eligible for the byte-identical-tree skip", contract)
        self.assertIn('"security_review": {', plan)
        self.assertIn('"status": "required"', plan)
        self.assertIn('"required_reviews": ["security"]', plan)
        self.assertIn('"type": "security"', plan)
        self.assertIn("code_security_verification", gates)
        self.assertIn("--security-result", contract)
        self.assertIn("--security-result", gates)
        self.assertIn(
            '"code-security-review"',
            self.read("scripts/harness_contract.py"),
        )

    def test_recently_added_tooling_is_documented(self) -> None:
        gates = self.read("references/verification-gates.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        state = self.read("references/execution-state-model.md")
        packet_guide = self.read("references/graph-orchestration.md")
        updates = self.read("references/design-input-updates.md")
        documents = self.read("assets/templates/DOCUMENTS.template.md")

        self.assertIn("skip-integration-review", gates)
        self.assertIn("--tree-sha", gates)
        for command in (
            "skip-integration-review",
            "acquire-run-lock",
            "release-run-lock",
            "heartbeat-run-lock",
            "watchdog",
            "record-observation",
            "accept-wave",
            "lease-worker",
            "record-worker-result",
            "reject-worker-result",
            "record-integration",
            "--packet-out",
            "--security-result",
        ):
            self.assertIn(command, runbook)
        self.assertIn(
            "Hand-editing the RUN JSON for these steps is the path the transitions replaced",
            self.read("references/worktree-thread-orchestration.md"),
        )
        self.assertIn(
            "manifest_already_validated",
            self.read("references/runtime-performance.md"),
        )
        self.assertIn('"runtime_metrics": null', runbook)
        self.assertIn("inspect_harness_run.py", state)
        self.assertIn("check_skill_bindings.py", state)
        self.assertIn("--max-diff-bytes", packet_guide)
        self.assertIn("REFINEMENT_BACKLOG.template.md", updates)
        self.assertIn(
            "| `design-system.md` / `design-system.json` | `docs/product/` |", documents
        )
        self.assertIn("- `tasks.md` is a rendered view", documents)

    def test_final_visual_parity_loop_is_documented(self) -> None:
        skill = self.read("SKILL.md")
        gates = self.read("references/verification-gates.md")
        contract = self.read("references/ui-implementation-contract.md")

        self.assertIn("Final Visual Parity Loop", skill)
        for phrase in (
            "### Final Visual Parity Loop",
            "`html_target`",
            "`design_system`",
            "parity/<route>-<state>-<breakpoint>-target.png",
            "target_comparison",
            "Stop after two failed repair rounds",
        ):
            self.assertIn(phrase, gates)
        self.assertIn("never widen the tolerance", gates)
        self.assertIn("A parity repair is an ordinary candidate-changing repair", gates)
        self.assertIn("does not add attempts on top of that budget", gates)
        self.assertIn("Final Visual Parity Loop", contract)

    def test_ui_impact_classification_and_deviation_ledger_are_binding(self) -> None:
        contract = self.read("references/ui-implementation-contract.md")
        gates = self.read("references/verification-gates.md")
        skill = self.read("SKILL.md")
        updates = self.read("references/design-input-updates.md")
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        e2e_template = self.read("assets/templates/E2E_VERIFICATION.template.md")

        self.assertIn(
            "`none`, `style`, `structure`, or `both`", contract
        )
        self.assertIn(
            "never integrate a structural change ahead of its doc delta", contract
        )
        self.assertIn("RUN `deviation_ledger`", gates)
        self.assertIn(
            "accumulated in-tolerance drift never substitutes for a doc update", gates
        )
        self.assertIn("The RUN `deviation_ledger` is complete", gates)
        self.assertIn("classify the completed change's UI impact", worker_goal)
        self.assertIn("## Deviation Ledger", e2e_template)
        self.assertIn("Allowed-deviation citation", e2e_template)
        self.assertIn("rule-8 UI-impact classification", skill)
        self.assertIn("never a silent local restyle", updates)
        self.assertIn(
            "returns through `product-definition-builder` as a design-input delta",
            updates,
        )
        self.assertIn(
            "Motion is a design decision, not an implementation preference", contract
        )
        self.assertIn("Static screenshots never close a motion change", gates)
        self.assertIn("strongest task impact", contract)
        self.assertIn(
            "`doc_delta` is required when that strongest impact is `structure` or `both`",
            contract,
        )
        self.assertIn("`integration_notes` line", worker_goal)
        self.assertIn("UI impact: <none|style|structure|both>", worker_goal)
        self.assertIn("is a recorded attestation, not a validator-proven fact", gates)
        self.assertIn("strongest task impact the mission's workers reported", gates)

    def test_responsive_targets_and_layout_safety_are_end_to_end_contracts(self) -> None:
        skill = self.read("SKILL.md")
        trace = self.read("references/contract-and-traceability.md")
        ui_contract = self.read("references/ui-implementation-contract.md")
        gates = self.read("references/verification-gates.md")
        join = self.read("scripts/harness_contract_join.py")

        self.assertIn("exact responsive set", skill)
        self.assertIn("declared platform minimum", skill)
        self.assertIn("invariant `` `responsive` `` anchor", trace)
        self.assertIn("PRD, approved `wireframes.html`, every PLAN UI surface", trace)
        self.assertIn("missing or mismatched responsive set", ui_contract)
        self.assertIn("unintended element overlap, clipping, occlusion", gates)
        self.assertIn("browser geometry/reviewer evidence", gates)
        self.assertIn("PRD_RESPONSIVE_RE", join)
        self.assertIn("differ from the wireframe responsive", join)

    def test_final_page_quality_pass_is_documented(self) -> None:
        skill = self.read("SKILL.md")
        gates = self.read("references/verification-gates.md")
        contract = self.read("references/ui-implementation-contract.md")

        for content in (skill, gates, contract):
            self.assertIn("page-quality pass", content)
        self.assertIn("### Final Page-Quality Pass", gates)
        self.assertIn("follows the Final Visual Parity Loop", gates)
        self.assertIn("`ui_quality_verification`", gates)
        self.assertIn("`impeccable` by default", gates)
        self.assertIn("adds no review attempts of its own", gates)
        self.assertIn("never authorizes a local change", gates)
        self.assertIn("Evaluate commands only", gates)
        self.assertIn("route it to `product-definition-builder` as a design-input delta", gates)
        self.assertIn("`UNVALIDATED`", gates)
        self.assertIn("page-quality-verification slots", skill)

    def test_seo_metadata_is_bound_through_implementation(self) -> None:
        contract = self.read("references/ui-implementation-contract.md")
        gates = self.read("references/verification-gates.md")

        self.assertIn("records SEO metadata implements exactly that", contract)
        self.assertIn("the rendered `<head>` is part of the deliverable", contract)
        self.assertIn(
            "PRD contract gap routed to `product-definition-builder`, never an implementation-time invention",
            contract,
        )
        self.assertIn("the rendered `<head>` on the integration head", gates)
        self.assertIn("its `<title>` and meta description match the PRD record", gates)
        self.assertIn("A mismatch is a failing check, not a style preference", gates)

    def test_deployment_contract_maps_candidate_then_main(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/deployment-contract.md")
        promotion = self.read("references/branch-promotion-contract.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")
        project_claude = self.read("assets/templates/PROJECT_CLAUDE.template.md")

        self.assertIn("references/deployment-contract.md", skill)
        self.assertIn("references/branch-promotion-contract.md", skill)
        for phrase in (
            "Production tracks `main`",
            "isolated internal environment tracks the exact candidate run branch",
            "There is no persistent integration branch",
            "A development PASS never proves production",
            "adds no RUN authorization keys",
            "never triggers, rolls back, or reconfigures a deployment",
            "wrangler pages project create",
            "cannot later become git-connected",
            "`wrangler versions upload --env development`",
            "The default Cloudflare route is Workers with Static Assets",
            "Report the observed non-production or production URL",
            "never construct or guess a URL",
            "Version previews inherit the Worker's existing bindings",
            "named environments do not inherit bindings",
            "`wrangler d1 create <resource-name>-dev`",
            "is a blocker, not a configuration preference",
            "shares live bindings",
            "any production ID appearing in a development binding",
            "## Platform: cloudflare",
            "## Platform: vercel",
            "## Platform: aws",
            "## Platform: generic",
            "never invent a platform capability",
            "Migrating",
        ):
            self.assertIn(phrase, contract)
        for phrase in (
            "initial_delivery",
            "enhancement",
            "Delivery Kind And Base",
            "Candidate Gate",
            "Promote To Main",
            "Retired Development Branch",
            "require its tree to equal the verified candidate tree",
            "exact remote `main` SHA before tagging",
            "fast-forward to that exact SHA",
            "Every fetch, branch creation, ref update, merge, push, external test, and branch deletion",
            "never inherits or reuses a RUN push grant",
            "exact verified candidate at remote `main`",
        ):
            self.assertIn(phrase, promotion)
        self.assertIn("both initial-delivery and enhancement run branches", orchestration)
        self.assertIn("observed remote `main`", orchestration)
        self.assertIn("## Deployment", project_agents)
        self.assertIn("deployment-contract.md", project_agents)
        self.assertIn("branch-promotion-contract.md", project_agents)
        self.assertIn("fast-forward that SHA to `main`", project_agents)
        self.assertIn("Protected resources preview must never bind", project_agents)
        self.assertIn(
            "runtime adapter reference (Claude Code section)", project_claude
        )
        deployment_template = self.read("assets/templates/DEPLOYMENT.template.md")
        documents_template = self.read("assets/templates/DOCUMENTS.template.md")

        self.assertIn("## Human Setup Checklist", deployment_template)
        self.assertIn("## Required Secrets and Variables", deployment_template)
        self.assertIn("## External Console Setup", deployment_template)
        self.assertIn("never record a secret value", deployment_template)
        self.assertIn(
            "Reconcile every required secret and variable name", deployment_template
        )
        self.assertIn("### Git connection", deployment_template)
        self.assertIn("### CI connection", deployment_template)
        self.assertIn("ci_connected", deployment_template)
        self.assertIn("ci_connected", project_agents)
        self.assertIn("## Resource Isolation", deployment_template)
        self.assertIn("## Release Unit Names", deployment_template)
        self.assertIn(
            "| Surface | Surface suffix | Production release name | Development release name | Provider / channel |",
            deployment_template,
        )
        self.assertIn("never adds `-prod`", deployment_template)
        self.assertIn("that exact name plus `-dev`", deployment_template)
        self.assertIn(
            "| Binding class | Production resource | Development resource |",
            deployment_template,
        )
        self.assertIn("fully separate D1/KV/R2/Durable-Object resources", project_agents)
        self.assertIn(
            "the Harness never performs, triggers, or reconfigures them",
            deployment_template,
        )
        self.assertIn("## Environment Status", deployment_template)
        self.assertIn("## Branch Promotion", deployment_template)
        self.assertIn("Main exact-SHA result", deployment_template)
        self.assertIn("## Product Activation Handoff", deployment_template)
        self.assertIn("## Human Configuration Handoff", contract)
        self.assertIn("## Product Activation Handoff", contract)
        self.assertIn("receives no authorization", contract)
        self.assertIn("Before every deployable push", contract)
        self.assertIn("Never open value-bearing local files", contract)
        self.assertIn("exact pending names and console tasks", contract)
        self.assertIn("does not authorize or require another push", contract)
        self.assertIn("`docs/DEPLOYMENT.md`, seeded during PRD creation", contract)
        self.assertIn("| `docs/DEPLOYMENT.md` | `docs/` |", documents_template)
        self.assertIn("| `docs/ACTIVATION.md` | `docs/` |", documents_template)
        self.assertIn("| `docs/DOCUMENTS.md` | `docs/` |", documents_template)
        self.assertIn("root carries only what runtimes auto-discover", documents_template)
        self.assertIn("# Documents", documents_template)
        self.assertIn("non-canonical view of RUN", documents_template)
        self.assertIn("`docs/product/`", documents_template)
        self.assertIn("render `docs/tasks.md`", skill)
        self.assertIn("`product-activation` follows required promotion and deployment verification; RUN grants no authority", skill)
        self.assertIn("## Post-Delivery Activation", project_agents)
        self.assertIn("Capability never grants permission", project_agents)
        if REPO_ROOT is not None:
            root_agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("An `initial_delivery` or `enhancement` completes", root_agents)
            self.assertIn("permanently main-only", root_agents)
            self.assertIn("never force-push", root_agents)

    def test_adding_a_binding_runbook_orders_resource_before_declaration(self) -> None:
        contract = self.read("references/deployment-contract.md")
        deployment_template = self.read("assets/templates/DEPLOYMENT.template.md")

        for phrase in (
            "create the non-production resource",
            "deploy the exact candidate branch/SHA",
            "promote that exact verified SHA to `main`",
            "Development secrets stay fake or dedicated",
            "D1 migrations run against the non-production database first",
        ):
            self.assertIn(phrase, contract)
        # The wrangler procedure is cloudflare-scoped: it lives inside the
        # cloudflare platform section, never in the portable model.
        self.assertLess(
            contract.index("## Platform: cloudflare"),
            contract.index("Adding a binding follows"),
        )
        self.assertLess(
            contract.index("Adding a binding follows"),
            contract.index("## Platform: vercel"),
        )
        for phrase in (
            "## Adding A Binding",
            "### cloudflare",
            "### vercel, aws, generic",
            "Do not reuse the cloudflare commands",
            "deploy the exact candidate branch/SHA",
            "never in the wrangler config",
            "fast-forward the exact verified SHA to `main`",
        ):
            self.assertIn(phrase, deployment_template)
        self.assertLess(
            deployment_template.index("## Adding A Binding"),
            deployment_template.index("### cloudflare"),
        )
        # The wrangler environment names are the convention: development for
        # the non-production side, production for the production side.
        self.assertIn("env.development", deployment_template)
        self.assertIn("env.production", deployment_template)
        for retired in ("env.preview", "env.platform", "--env preview"):
            self.assertNotIn(retired, deployment_template)
        self.assertIn("env.development", contract)
        # The hard constraint, machine-checked: each declaration step comes
        # after its resource-creation step.
        self.assertLess(
            deployment_template.index("Create the development-side resource"),
            deployment_template.index(
                "Declare the binding in the development environment"
            ),
        )
        self.assertLess(
            deployment_template.index("Create the production-side resource"),
            deployment_template.index("Add the production declaration"),
        )

    def test_readme_explains_the_project_size_gate(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("The delivery core makes one size decision", readme)

    def test_provider_mismatch_is_blocked_not_bridged(self) -> None:
        adapters = self.read("references/runtime-adapters.md")
        research = self.read("references/orchestration-research-notes.md")

        self.assertIn(
            "There is no mechanism in the adapter layer to invoke another provider", adapters
        )
        self.assertIn(
            "Do not probe for another runtime's CLI, binary, or plugin as a substitute route",
            adapters,
        )
        self.assertIn("there is no cross-host preflight, no bridged process, and no declared fallback", research)
        self.assertIn("blocked on provider mismatch rather than probing or launching the other runtime", research)

    def test_authorized_app_wave_requires_real_thread_launch(self) -> None:
        adapters = self.read("references/runtime-adapters.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        selector = self.read("references/parallel-mission-selection.md")
        goal = self.read("assets/templates/GOAL.template.md")

        self.assertIn("Do not stop after printing a non-empty app-task wave", adapters)
        self.assertIn("consume every accepted dispatch entry", adapters)
        self.assertIn("Search the current Codex tool surface", adapters)
        self.assertIn("top-level left-sidebar app task", adapters)
        self.assertIn("## Launch Selected Codex App Threads", orchestration)
        self.assertIn("one top-level worktree task/thread per mission", orchestration)
        self.assertIn("Read-only explorers and reviewers are parent-dispatched siblings", orchestration)
        self.assertIn("never children of a mission task", orchestration)
        self.assertIn("direct subagent of the coordinator is not equivalent", selector)
        self.assertIn("one top-level left-sidebar task", goal)
        self.assertIn("Never replace explicitly requested independent app tasks", adapters)

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
        self.assertIn("lightest safe direct or PLAN-v6/RUN-v11 delivery path", agent)
        self.assertIn("Host adapter: none | codex | claude_code | pi | generic", skill)

    def test_runtime_upgrade_gate_blocks_old_or_stale_sessions(self) -> None:
        skill = self.read("SKILL.md")
        upgrades = self.read("references/runtime-upgrades.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        selector = self.read("scripts/select_ready_nodes.py")

        self.assertIn("references/runtime-upgrades.md", skill)
        self.assertIn("Never hot-upgrade a live worker", upgrades)
        self.assertIn("runtime_adapter.version_gate", upgrades)
        self.assertIn("## Re-Orchestrate Remaining Work Onto The New Runtime", upgrades)
        self.assertIn("an upgrade re-binds work, it does not redo it", upgrades)
        self.assertIn("a provider switch is never inferred from an upgrade alone", upgrades)
        self.assertIn("re-orchestrates every remaining task onto the new runtime", skill)
        self.assertIn('"required_harness_version": "0.35.3"', runbook)
        for reason in (
            "runtime_version_unobserved",
            "runtime_upgrade_pending",
            "runtime_upgrade_required",
            "runtime_restart_required",
        ):
            self.assertIn(reason, selector)

    def test_workers_never_delegate_and_parent_owns_reviews(self) -> None:
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn("## No Nested Delegation", worker_goal)
        self.assertIn("Do not spawn, create, or delegate to another agent", worker_goal)
        self.assertIn("All explorers, writers, and reviewers are parent-dispatched siblings", worker_goal)
        self.assertIn("RUN-v11 workers never delegate", runbook)
        self.assertIn("all reviews are parent-dispatched graph nodes", runbook)

    def test_frontend_design_has_compilation_and_conformance_modes(self) -> None:
        skill = self.read("SKILL.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        design_updates = self.read("references/design-input-updates.md")

        for content in (skill, plan, worker_goal):
            self.assertIn("frontend-design conformance mode", content)
            self.assertIn("design-input delta", content)
            self.assertIn("design-system-compiler", content)
            self.assertIn("compilation mode", content.casefold())
        self.assertIn("user explicitly selected it", plan)
        self.assertIn("new or high-impact visual surface", plan)
        self.assertIn("proposed design-input delta", design_updates)
        self.assertIn("return formal pair changes to `design-system-compiler`", design_updates)

    def test_page_reference_modes_do_not_bypass_frozen_design_sources(self) -> None:
        skill = self.read("SKILL.md")
        updates = self.read("references/design-input-updates.md")

        self.assertIn("Design inspiration", updates)
        self.assertIn("Page-faithful target", updates)
        self.assertIn("non-canonical evidence", updates)
        self.assertIn("only after the user requests faithful matching", updates)
        self.assertIn("Source version / hash", updates)
        self.assertIn("Tolerance / allowed deviations", updates)
        self.assertIn("PRD UI Design Handoff", updates)
        self.assertIn("Design System Need Gate", updates)
        self.assertIn("user explicitly requests faithful conformance", skill)

    def test_schema_v6_routes_claude_dynamic_workflow(self) -> None:
        skill = self.read("references/runtime-adapters.md")
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
        self.assertNotIn("capsule_sha256", workflow)
        self.assertNotIn("context_bytes", workflow)
        self.assertIn("complete live task", workflow)

    def test_goal_template_matches_current_authorization_ledger(self) -> None:
        goal = self.read("assets/templates/GOAL.template.md")

        self.assertIn("Keep all 12 schema-v11 RUN authorization entries false", goal)
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
        product-definition-builder contracts them that way; this row is the only place the
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
        self.assertIn("`plan_readiness` in RUN is the single machine gate", contract)
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
        self.assertIn('"schema_version": 6', plan)
        self.assertIn('"schema_version": 11', run)
        self.assertIn('"graph_state"', run)
        self.assertIn("dependency", graph)
        self.assertIn("max_traversals", graph)
        self.assertIn("pipeline(workflowArgs.nodes", workflow)
        self.assertIn("tool_profile", selector)
        self.assertIn('"workflow_runs"', run)
        self.assertIn("mission_write", run)
        self.assertIn("EnterWorktree", workflow)
        self.assertNotIn("capsule_sha256", workflow)
        self.assertNotIn("context_bytes", workflow)
        self.assertIn("complete live task", workflow)

    def test_plan_provider_options_bind_worker_models(self) -> None:
        skill = "\n".join(
            (
                self.read("SKILL.md"),
                self.read("references/runtime-adapters.md"),
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
        self.assertIn('"pi": {"model": null, "reasoning_effort": "high"}', plan)
        self.assertIn('"pi": {"model": null, "reasoning_effort": "medium"}', plan)
        self.assertIn('"generic": {"model": null, "reasoning_effort": null}', plan)
        self.assertIn("10-20 minutes", plan)
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
        self.assertIn("routine deterministic `backend_code` or `security` review: Codex `gpt-5.6-terra`, `medium`", skill)
        self.assertIn("routine frontend, backend, visual, security, and integration review: `sonnet`, `medium`", skill)
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

        self.assertIn('"schema_version": 11', runbook)
        self.assertIn('"batch_gate_results"', runbook)
        self.assertIn('"final_gate_results"', runbook)
        self.assertIn('"ui_evidence"', runbook)
        self.assertIn("New managed work uses PLAN schema v6 and RUN schema v11", skill)
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
        self.assertIn("### First Principles", project_agents)
        self.assertIn(
            "not from habit, inherited patterns, or how another project solved it",
            project_agents,
        )
        self.assertIn("### File Size Limit", project_agents)
        self.assertIn("deleted and rewritten from scratch", project_agents)
        self.assertIn(
            "no compatibility shim keeps the replaced module alive", project_agents
        )
        self.assertIn("## Managed Product Delivery Harness Runs", project_agents)
        self.assertIn("Small bounded work may proceed directly", project_agents)
        self.assertIn("## Keep Product Contracts Current", project_agents)
        self.assertIn(
            "small post-delivery fixes that do not use Product Delivery Harness PLAN/RUN",
            project_agents,
        )
        self.assertIn(
            "Adding a page, route, visible region, state, or responsive behavior is at least `structure`",
            project_agents,
        )
        self.assertIn(
            "not complete while implementation and the canonical product documents disagree",
            project_agents,
        )
        self.assertNotIn("<verification-command>", project_agents)
        self.assertNotIn("<e2e-command>", project_agents)
        self.assertNotIn("(List protected files here", project_agents)
        self.assertNotIn("current v10", project_agents)
        self.assertIn("The RUN push guard", project_agents)
        self.assertIn("@AGENTS.md", project_claude)
        self.assertIn("## Claude Code Runtime Boundary", project_claude)
        self.assertIn("Direct Claude Code work follows `AGENTS.md`", project_claude)
        self.assertIn("does not transfer to the worker", project_claude)

        if REPO_ROOT is not None:
            root_agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
            root_claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertNotIn("codex/<short-name>", root_agents)
            self.assertIn("never add a fixed prefix", root_agents.lower())
            self.assertIn("## Keep Product Contracts Current", root_agents)
            self.assertIn("@AGENTS.md", root_claude)
            self.assertIn("Direct Claude Code work follows `AGENTS.md`", root_claude)
            self.assertIn("does not transfer to the worker", root_claude)

    def test_gitignore_contract_is_toolchain_specific_and_applies_to_both_routes(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/gitignore-contract.md")
        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")

        self.assertIn("Gitignore impact: none | update | needs owner decision", skill)
        self.assertIn("both direct and managed routes", skill)
        self.assertIn("references/gitignore-contract.md", skill)
        self.assertIn("## Gitignore Hygiene", project_agents)
        for phrase in (
            "not a generic list copied into every repository",
            "Never add an ignore rule only to make a dirty worktree look clean",
            "dependency manifests and lockfiles",
            "`.env.example`, `.env.*.example`",
            "Do not create an empty example file",
            "git check-ignore -v --no-index",
            "git status --short --ignored",
            "git ls-files",
        ):
            self.assertIn(phrase, contract)

        if REPO_ROOT is not None:
            root_agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
            root_ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("## Gitignore Hygiene", root_agents)
            for pattern in (
                ".env\n",
                ".env.*\n",
                "!.env.example\n",
                "!.env.*.example\n",
                ".dev.vars\n",
                "!.dev.vars.example\n",
            ):
                self.assertIn(pattern, root_ignore)

    def test_platform_archetypes_keep_monetization_and_partner_channels_separate(self) -> None:
        archetypes = self.read("references/platform-archetypes.md")
        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")

        self.assertIn("Monetization infrastructure gate", archetypes)
        self.assertIn("Partner channel gate and affiliate / referral / reseller model", archetypes)
        self.assertIn("add a separate partner-channel mission", archetypes)
        self.assertIn("Do not fold it into the billing/entitlement mission", archetypes)
        self.assertIn("commission reversal after refund/chargeback", archetypes)
        self.assertIn("PARTNER-* affiliate/referral/reseller", archetypes)
        self.assertIn("## Monetization And Partner Channels", project_agents)
        self.assertIn("RevenueCat is one candidate, never the default", project_agents)
        self.assertIn("an affiliate link alone does not satisfy it", project_agents)

        if REPO_ROOT is not None:
            root_agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("## Monetization And Partner Channels", root_agents)

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
        adapters = self.read("references/runtime-adapters.md")

        for content in (skill, project):
            self.assertIn("never add a fixed prefix", content.lower())
        self.assertIn("does not own shared state", adapters)
        self.assertIn("ask before branch creation", skill.lower())
        self.assertIn("- '**'", ci)
        self.assertNotIn("codex/**", ci)

    def test_repo_ci_workflow_verifies_every_pushed_branch(self) -> None:
        # The template promises `'**'`; this pins the repository's own workflow
        # to the same filter so a governance-legal branch push can never skip
        # CI. Standalone installs (no repo checkout) have no workflow to read.
        if REPO_ROOT is None:
            self.skipTest("no repository checkout around the skill")
        workflow = REPO_ROOT / ".github" / "workflows" / "harness-ci.yml"
        if not workflow.is_file():
            self.skipTest("repository has no harness-ci workflow")
        content = workflow.read_text(encoding="utf-8")
        self.assertIn("- '**'", content)
        self.assertNotIn("codex/**", content)
        self.assertIn('HARNESS_GOLDEN_PATH: "1"', content)
        self.assertIn('-p "test_golden_path.py" -v', content)
        self.assertIn("skills/product-activation/scripts", content)
        self.assertIn(
            "unittest discover -s skills/product-activation/scripts/tests -v",
            content,
        )


if __name__ == "__main__":
    unittest.main()
