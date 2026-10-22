import re
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

MANAGED_STAGE = "references/stages/managed-delivery.md"
MANAGED_STAGE_ROUTES = (
    ("plan", "managed-route"),
    ("plan", "reference-routing"),
    ("plan", "2-plan-large-work"),
    ("runtime", "adapter-routing"),
    ("dispatch", "default-runtime-and-wave-policy"),
    ("dispatch", "default-mission-topology"),
    ("dispatch", "3-pass-plan-readiness"),
    ("execution", "4-execute-and-integrate"),
    ("verification", "5-verify-local-first"),
    ("closeout", "6-complete"),
)
ACTIVATION_STAGE_ROUTES = (
    ("required-inputs", "Before preparation or execution"),
    ("workflow", "Before platform-specific work"),
    ("status-and-outcome-handoff", "Before ending an execution pass"),
    ("checker-contract", "Before ending an execution pass"),
)
SEO_STAGE_ROUTES = (
    ("required-inputs", "Before an actual review"),
    ("workflow", "Before an actual review"),
    ("saved-lifecycle-public-release-review", "Before a saved lifecycle public-release review"),
)
SECURITY_STAGE_FILES = (
    (
        "references/stages/security-review.md",
        "Security Review Stage",
        ("Required Inputs", "Workflow", "Handoff"),
    ),
    (
        "references/review-contract.md",
        "Review Contract",
        ("Harness Placement", "Result"),
    ),
)


def stage_headings(text: str) -> set[str]:
    headings = set()
    inside_frontmatter = False
    for line in text.splitlines():
        if line.strip() == "---":
            inside_frontmatter = not inside_frontmatter
            continue
        if inside_frontmatter or not line.startswith("#"):
            continue
        heading = line.lstrip("#").strip().lower()
        heading = re.sub(r"[^a-z0-9\s-]", "", heading)
        heading = re.sub(r"\s+", "-", heading.strip())
        headings.add(heading)
    return headings


class DeliveryHarnessSkillContractTests(unittest.TestCase):
    def test_enhancements_preserve_ui_and_record_small_followups(self) -> None:
        bounded = self.read("references/bounded-enhancement.md")
        epic = self.read("assets/templates/EPIC.template.md")
        ui_root = SKILL_ROOT.parent / "ui-design-builder"
        recommendations = (ui_root / "references/enhancement-recommendations.md").read_text(encoding="utf-8")
        ui_stage = (ui_root / "references/stages/ui-design.md").read_text(encoding="utf-8")
        for phrase in ("## Epic Selection And Change History", "before implementation",
                       "same accepted outcome", "closed Epic", "small fix"):
            self.assertIn(phrase, bounded)
        self.assertIn("## Change Log", epic)
        for phrase in ("## Incremental UI Scope", "added", "changed", "preserved",
                       "complete coverage is not a redraw instruction", "entry links",
                       "shared component", "unchanged product"):
            self.assertIn(phrase, recommendations)
        self.assertIn("Enhancement mode takes precedence", ui_stage)
        self.assertIn("Do not restart the all-screen authoring sequence", ui_stage)
        product = (SKILL_ROOT.parent / "product-definition-builder" / "SKILL.md").read_text(encoding="utf-8")
        compiler_stage = (SKILL_ROOT.parent / "design-system-compiler" / "references/stages/design-compilation.md").read_text(encoding="utf-8")
        self.assertIn("Incremental UI Scope", product)
        self.assertIn("Incremental UI Scope", compiler_stage)

    @unittest.skipUnless(sys.platform == "win32" and REPO_ROOT is not None,
                         "Windows CI candidate identity")
    def test_windows_ci_uses_exact_candidate_and_stops_at_each_failed_shard(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/harness-ci.yml").read_text(encoding="utf-8")
        job = workflow.split("\n  windows-native:\n", 1)[1].split("\n  validate:\n", 1)[0]
        self.assertIn("ref: ${{ env.CANDIDATE_SHA }}", job)
        self.assertIn('-ne $env:CANDIDATE_SHA', job)
        step = job.split("      - name: Run native Harness shard\n", 1)[1]
        step = step.split("      - name:", 1)[0].split("        run: |\n", 1)[1]
        self.assertIn("--platform windows --shard-count 4", step)
        self.assertIn("--shard-index '${{ matrix.shard }}'", step)
        self.assertIn("shard: [0, 1, 2, 3]", job)
        self.assertIn("$plannerStatus = $LASTEXITCODE", step)
        self.assertIn("if ($plannerStatus -ne 0) {", step)
        self.assertIn("exit $plannerStatus", step)
        self.assertIn("$plan = $planJson | ConvertFrom-Json", step)
        self.assertLess(
            step.index("$plannerStatus = $LASTEXITCODE"),
            step.index("$plan = $planJson | ConvertFrom-Json"),
        )
        self.assertIn("foreach ($testFile in $plan.files) {", step)
        self.assertIn("$suiteStatus = $LASTEXITCODE", step)
        self.assertIn("if ($suiteStatus -ne 0) {", step)
        self.assertIn("exit $suiteStatus", step)

    @unittest.skipIf(REPO_ROOT is None, "brand contract requires a source checkout")
    def test_product_delivery_harness_brand_and_skill_ids_are_canonical(self) -> None:
        package = (REPO_ROOT / "package.json").read_text(encoding="utf-8")
        self.assertIn('"name": "product-delivery-harness"', package)
        # VERSION is the one source; every other release surface must match it.
        version = self.read("VERSION").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertIn(f'"version": "{version}"', package)
        for readme in ("README.md", "README.zh-TW.md", "README.zh-CN.md", "README.es.md"):
            with self.subTest(readme=readme):
                text = (REPO_ROOT / readme).read_text(encoding="utf-8")
                self.assertIn(f"badge/version-{version}-", text)
                self.assertIn(f"\n- **{version}** ", text)
        self.assertFalse(
            (REPO_ROOT / "Tasks.md").exists(),
            "the source repository must not keep a root Tasks.md flow log",
        )

        skills_root = REPO_ROOT / "skills"
        current = {
            "delivery-harness": "Delivery Harness",
            "product-definition-builder": "Product Definition Builder",
            "ui-design-builder": "UI Design Builder",
            "design-system-compiler": "Design System Compiler",
            "code-security-review": "Code Security Review",
            "product-activation": "Product Activation",
            "seo-growth-review": "SEO Growth Review",
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
                self.assertIn("`ui-design-builder`", readme)
                self.assertIn("`design-system-compiler`", readme)
                self.assertIn("`code-security-review`", readme)
                self.assertIn("`product-activation`", readme)
                self.assertIn("`seo-growth-review`", readme)

    @unittest.skipIf(REPO_ROOT is None, "install migration requires a source checkout")
    def test_renamed_installs_have_a_recoverable_legacy_migration(self) -> None:
        documents = {
            "AGENTS.md": (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            "source-maintenance.md": self.read("references/governance/source-maintenance.md"),
            "runtime-upgrades.md": self.read("references/runtime-upgrades.md"),
            **{
                name: (REPO_ROOT / name).read_text(encoding="utf-8")
                for name in ("README.md", "README.zh-CN.md", "README.zh-TW.md", "README.es.md")
            },
        }
        for name, content in documents.items():
            with self.subTest(document=name):
                if name == "AGENTS.md":
                    self.assertIn(
                        "governance/source-maintenance.md#update-local-skills",
                        content,
                    )
                    continue
                if name == "runtime-upgrades.md":
                    self.assertIn("governance/source-maintenance.md#update-local-skills", content)
                    continue
                for skill_id in (
                    "full-harness",
                    "prd-builder",
                    "product-design-builder",
                    "delivery-harness",
                    "product-definition-builder",
                    "ui-design-builder",
                    "design-system-compiler",
                    "code-security-review",
                    "product-activation",
                    "seo-growth-review",
                ):
                    self.assertIn(f"`{skill_id}`", content)
                self.assertIn(
                    "~/.agents/skill-backups/product-delivery-harness/", content
                )
                self.assertIn("~/.agents/skills/", content)

        agents = documents["source-maintenance.md"]
        runtime = documents["runtime-upgrades.md"]
        self.assertIn("never overwrite or delete", agents)
        self.assertIn("Never overwrite or delete", runtime)
        self.assertIn("previous release tag", agents)
        self.assertIn("previous release tag", runtime)
        self.assertNotIn("Restore the backup if verification fails", runtime)
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
        skill = self.read(MANAGED_STAGE)
        entry = self.read("SKILL.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")
        project = self.read("assets/templates/PROJECT_AGENTS.template.md")
        operating = self.read("references/project-operating-rules.md")
        managed_owner = self.owner_section(
            operating, "## Managed Product Delivery Harness Runs"
        )

        topology = self.owner_section(
            self.read("references/verification-gates.md"), "## Review Topology"
        )
        self.assertIn("Default `review_policy: final_candidate`", topology)
        self.assertIn("security lens re-binds", topology.lower())
        self.assertIn("Security never skips and never reuses", topology)
        self.assertIn("## Default Mission Topology", skill)
        self.assertIn("Map one feature batch to one mission", skill)
        self.assertIn("one bounded worker slice per task", skill)
        self.assertIn("count planned review nodes", skill)
        self.assertIn("one bounded worker slice", skill)
        self.assertIn("10-20 minutes", skill)
        self.assertIn("no wall-time percentage target", skill)
        self.assertIn("stop paying for the same work twice", skill)
        self.assertIn("bounded read-only exploration", skill)
        self.assertIn("one explicit `write_scope`", skill)
        self.assertIn("Freeze shared APIs, schemas, and types", skill)
        self.assertIn("`git status --porcelain`", skill)
        self.assertIn("one planned parent-owned read-only reviewer", skill)
        self.assertIn("union of lenses the mission's write scope needs", skill)
        self.assertIn("at most one repair-and-re-review cycle", skill)
        self.assertIn("do not dispatch another same-scope review", skill)
        self.assertIn("do not attach the full PLAN/RUN", skill)
        self.assertIn("one planned broad final validation suite", skill)
        self.assertIn("Pinned managed protocols retain parent-owned PLAN/RUN", entry)
        self.assertIn("## No Nested Delegation", worker)
        self.assertIn(
            "delivery-harness/references/project-operating-rules.md"
            "#managed-product-delivery-harness-runs",
            project,
        )
        self.assertIn("explicit file-ownership scope", managed_owner)

    def test_missions_are_cohesive_and_tasks_keep_atomic_commit_boundaries(self) -> None:
        skill = self.read(MANAGED_STAGE)
        decomposition = self.read("references/execution-task-decomposition.md")
        convention = self.read("references/commit-convention.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")
        result_validator = self.read("scripts/validate_worker_result.py")
        operating = self.read("references/project-operating-rules.md")
        managed_owner = self.owner_section(
            operating, "## Managed Product Delivery Harness Runs"
        )

        self.assertIn("A mission is not a phase label", skill)
        self.assertIn("Pass the Mission Cohesion Gate", skill)
        self.assertIn("## Mission Cohesion Gate", decomposition)
        self.assertIn("Shared foundations do not justify a catch-all mission", decomposition)
        self.assertIn("Expected merge conflicts are scheduling facts", decomposition)
        self.assertIn("A mission is a feature batch", decomposition)
        self.assertIn("Split a mission only when one of these is true", decomposition)
        self.assertIn("A one-task mission needs one of the reasons above", decomposition)
        self.assertIn("The 10-20 minute slice applies to each task", decomposition)
        self.assertNotIn("Prefer the smaller cohesive mission", decomposition)
        self.assertIn("Before readiness, apply", plan)
        self.assertIn("Every executable task gets its own initial atomic commit", convention)
        self.assertIn("## Run-Wide Atomicity", convention)
        self.assertIn("never an unrelated fix, cleanup, or formatting", convention)
        self.assertIn("never product code", convention)
        self.assertIn("never folded into the merge body", convention)

        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")
        self.assertIn(
            "delivery-harness/references/project-operating-rules.md"
            "#managed-product-delivery-harness-runs",
            project_agents,
        )
        self.assertIn(
            "follows `delivery-harness/references/commit-convention.md`", managed_owner
        )
        self.assertIn("### Commit Messages", managed_owner)
        self.assertIn("<type>(<scope>): <imperative summary>", managed_owner)
        self.assertIn("One commit holds one kind of change", managed_owner)
        self.assertIn("exactly one task ID", managed_owner)
        self.assertIn("never a fake task body", managed_owner)
        self.assertIn(
            "Direct small work — including plan-mode edits outside a managed run — "
            "commits with the same subject shape",
            managed_owner,
        )
        self.assertIn("chore(deps): bump playwright to 1.49", managed_owner)
        self.assertIn("## Direct Commits", convention)
        self.assertIn("The subject is the record", convention)
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
        skill = self.read(MANAGED_STAGE)
        graph = self.read("references/graph-orchestration.md")
        decomposition = self.read("references/execution-task-decomposition.md")
        verification = self.read("references/verification-gates.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")

        self.assertIn("root-cause failure family", skill)
        self.assertIn("A generic instruction to continue", skill)
        self.assertIn("## Root-Cause Repair Escalation", graph)
        self.assertIn("one review, one consolidated repair, and one targeted re-check", graph)
        self.assertIn("the owner's quoted decision", graph)
        self.assertIn("docs/goal/DECISIONS.md", graph)
        self.assertIn("stable mission + review surface + root-cause lineage", graph)
        self.assertIn("A mission-level replan does not replenish a review budget", decomposition)
        self.assertIn("Do not authorize another example-specific patch", verification)
        self.assertIn("A replan does not grant a fresh review budget", plan)
        self.assertIn("Repair context (omit for an initial implementation)", worker)
        self.assertIn("fix the named root-cause family", worker)
        gen_verify = self.read("references/gen-verify-correct.md")
        self.assertIn("wait until every required review of that candidate has returned", graph)
        self.assertIn("never make `fix_required`", graph)
        self.assertIn("Collect every required review result for the same candidate", skill)
        self.assertIn("it is not a fresh full review", skill)
        self.assertIn("A failed re-review stops at `blocked` and returns to the owner", gen_verify)

    def test_scripted_transition_flag_surfaces_are_documented(self) -> None:
        state = self.read("references/execution-state-model.md")
        skill = self.read("SKILL.md")
        self.assertIn("### Scripted Transition Flag Surfaces", state)
        self.assertIn("`pause`, `resume`, `cancel`: `--source`", state)
        self.assertNotIn("--additional-attempts", state)
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
        self.assertNotIn("## Machine Telemetry", performance)
        self.assertNotIn("record-runtime-observation", performance)
        self.assertNotIn('"runtime_metrics"', runbook)
        self.assertNotIn("target_reduction_percent", runbook)
        self.assertIn("BATCH_PROTOCOL", verifier)

    def test_project_entry_links_conditional_rules_and_epic_baseline(self) -> None:
        entry = (SKILL_ROOT / "assets/templates/PROJECT_AGENTS.template.md").read_text(encoding="utf-8")
        rules = self.read("references/project-operating-rules.md")
        task_owner = self.read("references/governance/task-and-handoff.md")
        product_owner = self.read("references/governance/product-contracts.md")
        for title in ("Monetization And Partner Channels", "Post-Delivery Activation", "Managed Product Delivery Harness Runs"):
            anchor = title.lower().replace(" ", "-")
            if title == "Monetization And Partner Channels":
                self.assertIn("delivery-harness/references/governance/product-contracts.md#consumer-keep-product-contracts-current", entry)
                self.assertIn("project-operating-rules.md#" + anchor, entry)
                self.assertIn("## " + title, product_owner)
            else:
                self.assertIn("project-operating-rules.md#" + anchor, entry)
                self.assertIn("## " + title, rules)
        for marker in ("## Project Entry And Current Work", "## Required Reading", "## Completion", "docs/epics/EPIC-<id>.md", "unknown means unknown"):
            if marker == "## Project Entry And Current Work":
                self.assertIn(marker, task_owner)
                self.assertIn("task-and-handoff.md#project-entry-and-current-work", entry)
            elif marker in {"docs/epics/EPIC-<id>.md", "unknown means unknown"}:
                self.assertIn(marker, task_owner)
                self.assertIn("task-and-handoff.md#project-entry-and-current-work", entry)
            elif marker == "## Completion":
                self.assertIn("## Source Completion", task_owner)
                self.assertIn("## Consumer Completion", task_owner)
                self.assertIn("task-and-handoff.md#consumer-completion", entry)
            else:
                self.assertIn(marker, entry)
        epic = self.read("assets/templates/EPIC.template.md")
        self.assertIn("Keep one current PRD", epic)
        self.assertIn("this file grants none", epic)
        self.assertIn("Small fixes", task_owner)
        self.assertIn("docs/epics/", self.read("assets/templates/DOCUMENTS.template.md"))

    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")


    def owner_section(self, text: str, heading: str) -> str:
        self.assertIn(heading, text)
        return text.split(heading, 1)[1].split("\n## ", 1)[0]


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
        self.assertIn("Use this routing only when the size gate classifies work as `large`", skill)
        self.assertIn("two-way project-size gate", research)
        self.assertIn("Small work never reaches this selector", selector)
        self.assertIn("Small direct work does not instantiate this file", runbook)
        self.assertIn("lightest safe direct or PLAN-v6/RUN-v11 delivery path", agent)
        self.assertIn("A high file count", skill)
        self.assertIn("does not make work `large` by itself", skill)

    def test_managed_stage_routing_is_conditional_and_targets_exist(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(MANAGED_STAGE)

        self.assertIn("Use this routing only when the size gate classifies work as `large`", skill)
        self.assertIn("For direct work, do not read the managed stage file", skill)
        self.assertTrue((SKILL_ROOT / MANAGED_STAGE).is_file())
        for trigger, anchor in MANAGED_STAGE_ROUTES:
            with self.subTest(trigger=trigger, anchor=anchor):
                self.assertRegex(skill, rf"\({re.escape(MANAGED_STAGE)}#{anchor}\)")
                self.assertIn(anchor, stage_headings(stage))

        missing_anchor = stage.replace("### 6. Complete", "### Finished")
        with self.assertRaises(AssertionError):
            self.assertIn("6-complete", stage_headings(missing_anchor))

        missing_pointer = skill.replace("#6-complete", "#missing-complete")
        self.assertNotRegex(
            missing_pointer,
            rf"\({re.escape(MANAGED_STAGE)}#6-complete\)",
        )
        self.assertIn("#missing-complete", missing_pointer)

    def test_activation_stage_routing_is_conditional_and_targets_exist(self) -> None:
        skill = (SKILL_ROOT.parent / "product-activation" / "SKILL.md").read_text(encoding="utf-8")
        stage = (SKILL_ROOT.parent / "product-activation" / "references/stages/activation.md").read_text(encoding="utf-8")
        activation_contract = (SKILL_ROOT.parent / "product-activation" / "references/activation-contract.md").read_text(encoding="utf-8")

        self.assertIn("Activation is execution by default", skill)
        self.assertIn("explicit owner planning request", skill)
        for anchor, trigger in ACTIVATION_STAGE_ROUTES:
            with self.subTest(anchor=anchor, trigger=trigger):
                self.assertIn(trigger, skill)
                pointer_root = "references/activation-contract.md" if anchor == "checker-contract" else "references/stages/activation.md"
                self.assertIn(f"{pointer_root}#{anchor}", skill)
                anchor_document = activation_contract if anchor == "checker-contract" else stage
                self.assertIn(anchor, stage_headings(anchor_document))

        missing_anchor = stage.replace("## Checker Contract", "## Finished Checks")
        with self.assertRaises(AssertionError):
            self.assertIn("checker-contract", stage_headings(missing_anchor))

        missing_pointer = skill.replace("references/activation-contract.md#checker-contract", "references/activation-contract.md#missing-checks")
        self.assertNotIn("references/activation-contract.md#checker-contract", missing_pointer)
        self.assertIn("references/activation-contract.md#missing-checks", missing_pointer)

    def test_progressive_disclosure_keeps_routine_context_bounded(self) -> None:
        core = self.read("SKILL.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")
        result_contract = self.read("references/worker-result-contract.md")
        runtime_adapters = self.read("references/runtime-adapters.md")

        self.assertLess(len(core.split()), 2000)
        managed_stage = self.read(MANAGED_STAGE)
        self.assertLess(len(managed_stage.split()), 2400)
        self.assertLessEqual(len(worker.split()), 1200)
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
        self.assertLess(
            skill.index("### System Review And Route"),
            skill.index("## Managed Stage Routing"),
        )
        stage = self.read(MANAGED_STAGE)
        self.assertIn("## Adapter Routing", stage)
        self.assertLess(stage.index("## Adapter Routing"), stage.index("### 2. Plan Large Work"))

    def test_new_managed_work_requires_plan_run_and_legacy_compact_is_read_only(self) -> None:
        skill = self.read(MANAGED_STAGE)
        state = self.read("references/execution-state-model.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        goal = self.read("assets/templates/GOAL.template.md")

        for content in (skill, state, runbook, goal):
            self.assertIn("PLAN schema v6", content)
            self.assertIn("RUN schema v11", content)
            self.assertIn("compact run-only", content.lower())
            self.assertIn("read", content.lower())
        self.assertIn("New managed work never authors a compact RUN-only artifact", skill)
        self.assertIn("cannot authorize new managed execution", state)
        self.assertIn("not a new authoring route", runbook)
        self.assertNotIn("compact large sequential work", runbook.lower())
        self.assertNotIn("Planning depth: direct | compact RUN", skill)
        self.assertNotIn("New managed work uses PLAN schema v6", self.read("SKILL.md"))

    def test_large_no_agent_route_is_real_parent_sequential_execution(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(MANAGED_STAGE)
        state = self.read("references/execution-state-model.md")
        selector = self.read("references/parallel-mission-selection.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        goal = self.read("assets/templates/GOAL.template.md")

        for content in (stage, state, selector, orchestration, runbook, goal):
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
        self.assertIn("Workers and reviewers never delegate", state)
        self.assertIn("exact pinned bundle", state)
        self.assertIn("RUN-v11 workers never delegate", runbook)
        self.assertIn("Workers and reviewers never spawn or delegate further", orchestration)
        self.assertNotIn("app-task fan-out includes `spawn_subagents`", selector.lower())
        self.assertNotIn("enabled v10 policy", state.lower())

    def test_execution_intent_covers_route_subset_not_all_nine_actions(self) -> None:
        skill = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn("only the applicable local entries", state)
        self.assertIn("App-task dispatch is historical and unsupported", state)
        self.assertIn("Parent-dispatched sibling workers and reviewers", state)
        self.assertIn("does not authorize `push`", skill)
        self.assertIn("separate exact SHA/branch instruction", runbook)
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
            "Resolve new Skill Bindings from observed skills with owner confirmation",
            skill,
        )
        self.assertIn("## Skill Bindings", project_agents)
        self.assertIn("| ui_design |", project_agents)
        self.assertIn("| style_integration |", project_agents)
        self.assertIn("| design_compilation |", project_agents)
        self.assertIn("| frontend_implementation |", project_agents)
        self.assertIn("| ui_quality_verification |", project_agents)
        self.assertIn("| code_security_verification |", project_agents)
        self.assertIn("intentionally unresolved", project_agents)
        self.assertIn("full-tree SHA-256", project_agents)
        self.assertIn("not a Harness read-only reviewer", project_agents)
        # Required Reading names the installed orchestration skill itself; the
        # Skill Bindings table binds only the stage slots it dispatches.
        self.assertIn(
            "the installed `delivery-harness` SKILL.md (the orchestration skill itself",
            project_agents,
        )
        self.assertNotIn("bound in the Skill Bindings table", project_agents)
        self.assertIn("owner-confirmed Skill Bindings table", skill)

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
            "Hand-editing the RUN JSON for these steps is forbidden",
            self.read("references/worktree-thread-orchestration.md"),
        )
        self.assertIn(
            "manifest_already_validated",
            self.read("references/runtime-performance.md"),
        )
        self.assertNotIn('"runtime_metrics"', runbook)
        self.assertIn("inspect_harness_run.py", state)
        self.assertIn("check_skill_bindings.py", state)
        self.assertIn("--max-diff-bytes", packet_guide)
        self.assertIn("REFINEMENT_BACKLOG.template.md", updates)
        self.assertIn(
            "| `design-system.md` + `design-system.json` | `docs/design/` |", documents
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
            "parity/<label>-<tuple-sha256>-target.png",
            "parity/<label>-<tuple-sha256>-actual.png",
            "use the exact paths recorded in `manifest.json`",
            "target_comparison",
            "The loop uses the one repair and re-check from `gen-verify-correct.md`",
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
        self.assertIn("current UI-design sources reflect the change", contract)
        self.assertIn("Routine maintenance", contract)
        self.assertIn("RUN `deviation_ledger`", gates)
        self.assertIn(
            "accumulated in-tolerance drift never substitutes for a doc update", gates
        )
        self.assertIn("The RUN `deviation_ledger` is complete", gates)
        self.assertIn("classify the completed change", worker_goal)
        self.assertIn("## Deviation Ledger", e2e_template)
        self.assertIn("Allowed-deviation citation", e2e_template)
        self.assertIn("rule-8 UI-impact classification", skill)
        self.assertIn("never a silent local restyle", updates)
        self.assertIn(
            "return to `ui-design-builder`",
            updates,
        )
        self.assertIn(
            "Motion is a design decision, not an implementation preference", contract
        )
        self.assertIn("Static screenshots never close a motion change", gates)
        self.assertIn("run `scripts/parity_capture.py", gates)
        self.assertIn("parity-board.html", gates)
        self.assertIn("`agent-browser` CLI", gates)
        self.assertIn("strongest task impact", contract)
        self.assertIn(
            "`doc_delta` is required when that strongest impact is `structure` or `both`",
            contract,
        )
        self.assertIn("`integration_notes`", worker_goal)
        self.assertIn("is a recorded attestation, not a validator-proven fact", gates)
        self.assertIn("strongest task impact the mission's workers reported", gates)

    def test_responsive_targets_and_layout_safety_are_end_to_end_contracts(self) -> None:
        skill = self.read("SKILL.md")
        trace = self.read("references/contract-and-traceability.md")
        ui_contract = self.read("references/ui-implementation-contract.md")
        gates = self.read("references/verification-gates.md")
        join = self.read("scripts/harness_contract_join.py")

        self.assertIn("responsive sets must agree", skill)
        self.assertIn("invariant `` `responsive` `` anchor", trace)
        self.assertIn("PRD's `UI-*` surface contract agree exactly", trace)
        self.assertIn("Missing or mismatched route, state, responsive set", ui_contract)
        self.assertIn("Routine maintenance checks the current accepted product", ui_contract)
        self.assertIn("unintended element overlap, clipping, occlusion", gates)
        self.assertIn("browser geometry/reviewer evidence", gates)
        self.assertIn("PRD_RESPONSIVE_RE", join)
        self.assertIn("differ from the wireframe responsive", join)

    def test_final_ui_acceptance_combines_parity_and_page_quality(self) -> None:
        skill = self.read("SKILL.md")
        gates = self.read("references/verification-gates.md")
        contract = self.read("references/ui-implementation-contract.md")

        for content in (skill, contract):
            self.assertIn("page-quality pass", content)
            self.assertIn("Final UI Acceptance", content)
        self.assertIn("### Final UI Acceptance", gates)
        self.assertIn("#### Final Visual Parity Loop", gates)
        self.assertIn("#### Final Page-Quality Pass", gates)
        self.assertNotIn("follows the Final Visual Parity Loop", gates)
        self.assertIn("one independent read-only acceptance for parity and page quality", gates)
        self.assertIn("covers only implementation-only properties", gates)
        self.assertIn("the HiFi evidence is current", gates)
        self.assertIn("both must pass", gates)
        self.assertIn("planned `visual` review on the same candidate", gates)
        self.assertIn("Do not add another reviewer node or reset its lineage budget", gates)
        self.assertIn("Retain required matrix coverage", gates)
        self.assertIn("Frozen RUNs retain their pinned contracts", gates)
        self.assertIn("Impeccable is not the default", gates)
        self.assertIn("adds no review attempts of its own", gates)
        self.assertIn("Neither authorizes a local change", gates)
        self.assertIn("Read-only reviewer actions only", gates)
        self.assertIn("returns to `ui-design-builder`", gates)
        self.assertIn("`UNVALIDATED`", gates)
        self.assertIn("unresolved or incompatible slot", skill)

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

    def test_seo_stage_routing_is_conditional_and_targets_exist(self) -> None:
        seo = SKILL_ROOT.parent / "seo-growth-review"
        entry = (seo / "SKILL.md").read_text(encoding="utf-8")
        stage_path = seo / "references/stages/seo-review.md"
        stage = stage_path.read_text(encoding="utf-8")
        method = (seo / "references/review-method.md").read_text(encoding="utf-8")

        self.assertIn("no repository prerequisite, but still needs the production URL or domain", entry)
        self.assertIn("target market, language, and business outcome", entry)
        self.assertIn("makes SEO `not applicable`", entry)
        self.assertIn("Inline output follows the applicable rules without creating a repository artifact", entry)
        for anchor, trigger in SEO_STAGE_ROUTES:
            with self.subTest(anchor=anchor, trigger=trigger):
                self.assertIn(trigger, entry)
                pointer_root = "references/review-method.md" if anchor == "saved-lifecycle-public-release-review" else "references/stages/seo-review.md"
                pointer = f"{pointer_root}#{anchor}"
                self.assertIn(pointer, entry)
                self.assertIn(anchor, stage_headings(method if pointer.startswith("references/review-method") else stage))

        workflow = stage.split("## Workflow\n", 1)[1].split("\n## ", 1)[0]
        self.assertNotIn("## Workflow", entry)
        self.assertIn("references/source-catalog.md", workflow)
        self.assertIn("references/review-method.md", workflow)
        self.assertIn("assets/templates/SEO_REVIEW.template.md", workflow)
        self.assertIn("scripts/check_seo_review.py --require-lifecycle", workflow)

        missing_anchor = stage.replace("## Required Inputs", "Intake")
        self.assertNotIn("required-inputs", stage_headings(missing_anchor))
        missing_pointer = entry.replace(
            "references/stages/seo-review.md#required-inputs",
            "references/stages/seo-review.md#missing-intake",
        )
        self.assertNotIn("references/stages/seo-review.md#required-inputs", missing_pointer)
        self.assertIn("references/stages/seo-review.md#missing-intake", missing_pointer)

    def test_security_review_stage_and_contract_are_full_mandatory_reads(self) -> None:
        security_root = SKILL_ROOT.parent / "code-security-review"
        entry = (security_root / "SKILL.md").read_text(encoding="utf-8")
        for pointer, display, anchors in SECURITY_STAGE_FILES:
            with self.subTest(route=pointer):
                self.assertIn(f"[{display}]({pointer})", entry)
                self.assertNotIn(f"{pointer}#", entry)
                document = (security_root / pointer).read_text(encoding="utf-8")
                self.assertTrue(document.strip())
                self.assertTrue((security_root / pointer).is_file())
                for anchor in anchors:
                    self.assertIn(anchor, document)
                    self.assertIn(anchor.lower().replace(" ", "-"), stage_headings(document))

        self.assertIn("Before any actual security review", entry)
        self.assertIn("complete-file routes", entry)
        self.assertIn("no reading reduction", entry)
        self.assertIn("full source-to-sink coverage", entry)
        self.assertNotIn("## Required Inputs", entry)
        self.assertNotIn("## Workflow", entry)
        self.assertNotIn("## Handoff", entry)
        self.assertIn("exact candidate SHA", entry)
        self.assertIn("The reviewer never delegates", entry)
        self.assertIn("Do not edit files", entry)
        self.assertIn("Do not probe production", entry)

        stage = (security_root / "references/stages/security-review.md").read_text(encoding="utf-8")
        self.assertIn("`../delivery-harness/references/reference-selection.md`", stage)
        self.assertNotIn("`../../../delivery-harness/", stage)
        self.assertIn("[Review Contract](../review-contract.md)", stage)
        missing_route = entry.replace(
            "references/stages/security-review.md",
            "references/stages/missing-security-review.md",
        )
        self.assertNotIn("references/stages/security-review.md", missing_route)
        self.assertIn("references/stages/missing-security-review.md", missing_route)
        missing_contract = entry.replace(
            "references/review-contract.md",
            "references/missing-review-contract.md",
        )
        self.assertNotIn("references/review-contract.md", missing_contract)
        self.assertIn("references/missing-review-contract.md", missing_contract)

    def test_deployment_contract_maps_candidate_then_main(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(MANAGED_STAGE)
        stage = self.read(MANAGED_STAGE)
        contract = self.read("references/deployment-contract.md")
        operating = self.read("references/project-operating-rules.md")
        activation_owner = self.owner_section(operating, "## Post-Delivery Activation")
        promotion = self.read("references/branch-promotion-contract.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")
        managed_owner = self.read("references/governance/managed-delivery.md")
        project_claude = self.read("assets/templates/PROJECT_CLAUDE.template.md")

        self.assertIn("references/deployment-contract.md", stage)
        self.assertIn("references/branch-promotion-contract.md", stage)
        self.assertIn("references/branch-promotion-contract.md", skill)
        for phrase in (
            "Production tracks `main`",
            "isolated internal environment tracks the exact candidate run branch",
            "PR or branch Preview replaces protected-development landing",
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
            "Named environments do not inherit bindings",
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
            "Protected Branches",
            "require its tree to equal the verified candidate tree",
            "exact SHA before promotion or release completion",
            "fast-forward to that exact SHA",
            "Every fetch, branch creation, ref update, merge, push, external test, and branch deletion",
            "The archived RUN grants nothing",
            "the owner's exact instruction naming the SHA and branch",
            "Never use force",
            "Read back the remote ref and record it in the Epic",
            "C..A archive allowlist check passes",
            "legacy-pins.md#branch-protocols-before-063",
        ):
            self.assertIn(phrase, promotion)
        self.assertIn("forward-integration SHA T and read-back", self.read("references/legacy-pins.md"))
        self.assertIn("initial-delivery and enhancement run branches", orchestration)
        self.assertIn("frozen remote `main` head for both ordinary work and hotfixes", orchestration)
        state = self.read("references/execution-state-model.md")
        goal = self.read("assets/templates/GOAL.template.md")
        for content in (operating, orchestration, state, goal):
            self.assertIn("main-preview/1", content)
        self.assertNotIn("freeze the observed remote `development` head for ordinary work", operating)
        self.assertNotIn("A current managed run uses PLAN `branch_policy` to freeze remote `development`", state)
        self.assertNotIn("Ordinary flow verifies S on `development`", orchestration)
        self.assertNotIn("Protected-development landing and `main` promotion each", goal)
        self.assertIn("## Deployment", project_agents)
        self.assertIn("deployment-contract.md", project_agents)
        self.assertIn(
            "delivery-harness/references/deployment-contract.md#deployment-contract",
            project_agents,
        )
        self.assertIn("delivery-harness/references/governance/managed-delivery.md#git-safety", project_agents)
        self.assertIn("branch-promotion-contract.md", managed_owner)
        self.assertIn("exact-SHA promotion to protected `main`", managed_owner)
        self.assertIn("Protected resources preview must never bind", project_agents)
        self.assertIn(
            "general runtime adapter reference", project_claude
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
            "| Surface | Surface suffix | Production release name | Development release name | Production provider / channel | Development provider / channel |",
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
        self.assertIn("Render `docs/tasks.md` explicitly when needed", stage)
        self.assertIn("RUN transitions do not refresh", stage)
        self.assertIn("no RUN grant authorizes them", stage)
        self.assertIn(
            "delivery-harness/references/project-operating-rules.md"
            "#post-delivery-activation",
            project_agents,
        )
        self.assertIn("## Post-Delivery Activation", operating)
        self.assertIn("Capability never grants permission", activation_owner)
        if REPO_ROOT is not None:
            root_agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
            source_owner = self.read("references/governance/source-maintenance.md")
            self.assertIn("governance/source-maintenance.md#git-flow", root_agents)
            self.assertIn("Protect `main` permanently", source_owner)
            self.assertIn("no `development` branch or development integration is required", source_owner)
            self.assertIn("Consumer promotions retain", source_owner)
            self.assertIn("separate exact target/SHA authorization", source_owner)
            self.assertIn("never force-push", source_owner.casefold())

    def test_adding_a_binding_runbook_orders_resource_before_declaration(self) -> None:
        contract = self.read("references/deployment-contract.md")
        deployment_template = self.read("assets/templates/DEPLOYMENT.template.md")

        for phrase in (
            "create the non-production resource",
            "deploy the exact candidate branch/SHA",
            "separately land the verified candidate on main",
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
            "Provider changes require explicit replanning", adapters
        )
        self.assertIn(
            "Do not probe another runtime as a substitute route",
            adapters,
        )
        self.assertIn("There is no cross-host preflight, no bridged process, and no declared fallback", research)
        self.assertIn("blocked on provider mismatch rather than probing or launching the other runtime", research)

    def test_current_dispatch_blocks_explicit_unsupported_app_tasks(self) -> None:
        adapters = self.read("references/runtime-adapters.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        selector = self.read("references/parallel-mission-selection.md")
        goal = self.read("assets/templates/GOAL.template.md")
        self.assertIn("Current dispatch does not support user-owned app tasks", adapters)
        self.assertIn("Never silently substitute subagents or parent execution", adapters)
        self.assertIn("Current managed dispatch does not support user-owned app tasks", orchestration)
        self.assertIn("never replace it silently", orchestration)
        self.assertIn("Never replace those tasks silently", selector)
        self.assertIn("An explicit request for them blocks", goal)
        for content in (adapters, orchestration, selector, goal):
            self.assertNotIn("--task-thread-id", content)
            self.assertNotIn("app_threads", content)

    def test_plan_backed_runs_detect_then_select_full_frontier(self) -> None:
        skill = self.read(MANAGED_STAGE)
        entry = self.read("SKILL.md")
        state = self.read("references/execution-state-model.md")
        orchestration = self.read("references/worktree-thread-orchestration.md")
        selector = self.read("references/parallel-mission-selection.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("## Default Runtime And Wave Policy", skill)
        self.assertIn("Proactively inspect the current-session native tool surface", skill)
        self.assertIn("Missing authorization must never make an available driver disappear", skill)
        self.assertIn("Observe every advertised current driver", skill)
        self.assertIn("unrelated surfaces", skill)
        self.assertIn("Do not cap `max_parallel_workers` at a small fixed number", skill)
        self.assertIn("default immediately after Plan Readiness", state)
        self.assertIn("Observe actual required capabilities before dispatch", state)
        self.assertIn("Observe every advertised current driver", selector)
        self.assertIn("Observe each advertised driver", orchestration)
        self.assertIn("no launch grant is implied", orchestration)
        self.assertIn("Observe the actual driver", runbook)
        self.assertNotIn("capability_probe", runbook)
        self.assertIn("## Default Plan-Backed Wave", orchestration)
        self.assertIn("selection is the default post-readiness action", selector)
        self.assertIn("Never run parallel writers in `shared_checkout`", runbook)
        self.assertIn("lightest safe direct or PLAN-v6/RUN-v11 delivery path", agent)
        self.assertIn("Host adapter: none | general (observed host identity or generic)", entry)

    def test_runtime_upgrade_gate_blocks_old_or_stale_sessions(self) -> None:
        skill = self.read("SKILL.md")
        upgrades = self.read("references/runtime-upgrades.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        selector = self.read("scripts/select_ready_nodes.py")

        self.assertIn("references/runtime-upgrades.md", skill)
        self.assertIn("Never hot-upgrade a live worker", upgrades)
        self.assertIn("runtime_adapter.version_gate", upgrades)
        self.assertIn("## Re-Orchestrate Remaining Work Onto The New Runtime", upgrades)
        self.assertIn("Never revive a lease or re-execute completed missions", upgrades)
        self.assertIn("provider outside `allowed_providers` needs an explicitly authorized PLAN revision", upgrades)
        self.assertIn("## Run-Scoped Contract Pin", upgrades)
        self.assertIn("A new bundle applies to the next RUN", upgrades)
        self.assertIn("pinned_bundle_or_restart_required", upgrades)
        self.assertIn("A 0.66+ RUN cannot use that status", upgrades)
        self.assertNotIn("adopt-runtime-contract", upgrades)
        self.assertIn("re-orchestrates every remaining task onto the new runtime", skill)
        version = self.read("VERSION").strip()
        self.assertIn(f'"required_harness_version": "{version}"', runbook)
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

    def test_harness_owns_compilation_and_conformance_contracts(self) -> None:
        skill = self.read("SKILL.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        design_updates = self.read("references/design-input-updates.md")

        for content in (skill, plan, worker_goal):
            self.assertIn("design-system-compiler", content)
            self.assertIn("frontend-author", content)
            self.assertNotIn("frontend-design` in conformance mode", content)
            self.assertNotIn("`frontend-design` and `design-system-compiler`", content)
        self.assertIn("Harness—not the external skill—owns", worker_goal)
        self.assertNotIn("a direct parent may author", worker_goal)
        self.assertIn(
            "agent policy selects the UI author",
            worker_goal,
        )
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
        self.assertIn("approved UI design contract", updates)
        self.assertIn("Design System Need Gate", updates)
        self.assertIn("user explicitly requests faithful conformance", skill)

    def test_native_workflow_templates_are_removed(self) -> None:
        for name in ("CLAUDE_DYNAMIC_WORKFLOW.template.js", "CLAUDE_GRAPH_WORKFLOW.template.js"):
            self.assertFalse((SKILL_ROOT / "assets/templates" / name).exists())
        self.assertNotIn('"workflow_runs"', self.read("assets/templates/MISSION_RUNBOOK.template.md"))

    @unittest.skipIf(REPO_ROOT is None, "host-neutral documentation check requires a source checkout")
    def test_human_facing_docs_use_host_neutral_agent_graph_language(self) -> None:
        repo_paths = (
            "README.md",
            "README.zh-TW.md",
            "README.zh-CN.md",
            "README.es.md",
            "CLAUDE.md",
            "skills/delivery-harness/assets/templates/GOAL.template.md",
            "skills/delivery-harness/assets/templates/MISSION_RUNBOOK.template.md",
            "skills/delivery-harness/assets/templates/PROJECT_CLAUDE.template.md",
            "skills/delivery-harness/references/execution-state-model.md",
            "skills/delivery-harness/references/graph-orchestration.md",
            "skills/delivery-harness/references/orchestration-research-notes.md",
            "skills/delivery-harness/references/parallel-mission-selection.md",
            "skills/delivery-harness/references/runtime-adapters.md",
            "skills/delivery-harness/references/runtime-upgrades.md",
            "skills/delivery-harness/references/worktree-thread-orchestration.md",
            "skills/product-definition-builder/SKILL.md",
            "skills/product-definition-builder/references/agent-work-graph.md",
            "skills/product-definition-builder/references/output-contract.md",
            "skills/product-definition-builder/references/research-first-guide.md",
        )
        for relative_path in repo_paths:
            with self.subTest(path=relative_path):
                content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
                self.assertNotIn("dynamic workflow", content.casefold())
                self.assertNotIn("动态工作流", content)
                self.assertNotIn("動態工作流", content)

        self.assertIn(
            "## General runtime adapter",
            (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "# Read-Only Analysis Helpers",
            (
                REPO_ROOT
                / "skills"
                / "product-definition-builder"
                / "references"
                / "agent-work-graph.md"
            ).read_text(encoding="utf-8"),
        )

    def test_goal_template_matches_current_authorization_ledger(self) -> None:
        goal = self.read("assets/templates/GOAL.template.md")

        self.assertIn("Keep all 12 schema-v11 RUN authorization entries false", goal)
        self.assertIn("invoke_external_runtime", goal)
        self.assertIn("record real identities", goal)
        self.assertIn(
            "Do not replace explicitly requested user-owned tasks with direct agents or parent execution",
            goal,
        )
        self.assertIn(
            "Missing required capability blocks the affected work",
            goal,
        )

    def test_run_template_matches_the_local_only_default(self) -> None:
        """The template must keep remote publication behind explicit intent."""
        skill = self.read(MANAGED_STAGE)
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn("RUNs close `local_only`", skill)
        self.assertIn("`integration_push` remains legacy recovery state only", runbook)
        self.assertIn("`pushed_head_sha` stays null", runbook)
        self.assertIn("an explicit no-force push, and remote readback", runbook)
        self.assertIn("Harness 0.38+ RUNs start and finish `local_only`", runbook)








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
        self.assertFalse(
            authorization_covers(run_at(9), "push", "M1", "branch:development")
        )
        current = run_at(11)
        grant = current["authorizations"].pop("push")
        grant["scope"]["targets"] = ["branch:codex/work"]
        current["authorizations"]["create_local_commits"] = grant
        self.assertFalse(
            authorization_covers(current, "create_local_commits", "M1", "branch:codex/work")
        )
        grant["scope"].update(plan_revision=4, plan_digest_sha256="b" * 64)
        self.assertTrue(
            authorization_covers(current, "create_local_commits", "M1", "branch:codex/work")
        )
        current["authorizations"]["delete_branches"] = grant
        for branch in ("main", "development"):
            grant["scope"]["targets"] = [f"branch:{branch}"]
            self.assertFalse(
                authorization_covers(current, "delete_branches", "M1", f"branch:{branch}")
            )

        self.assertIn("Schema v10 additionally requires `plan_revision` and `plan_digest_sha256`", reference)
        self.assertIn('"plan_digest_sha256": "<64-hex>"', reference)
        self.assertIn("the invalidation rule is inert there", reference)

    def test_unfilled_observed_snapshot_empties_dispatchable_nodes(self) -> None:
        """The old wording sent the operator looking for an empty
        `ready_frontier`. At draft/ready the frontier stays populated and only
        `dispatchable_nodes` empties, so the operator saw a full frontier and
        concluded the snapshot was already filled in."""
        core = self.read(MANAGED_STAGE)
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



    def test_readiness_requires_every_node_to_have_a_host(self) -> None:
        """A node whose `allowed_providers` no participating host satisfies is a
        readiness gap, not a surprise at dispatch time."""
        core = self.read(MANAGED_STAGE)

        readiness = core[core.index("### 3. Pass Plan Readiness") : core.index("### 4. Execute And Integrate")]
        self.assertIn("Executability covers the whole graph, not just the next node", readiness)
        self.assertIn("`allowed_providers`", readiness)
        self.assertIn("blocking readiness gap", readiness)
        # Literal reference paths are skill-root-relative, even in the stage.
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






    def test_ui_design_intake_is_ready_before_implementation_and_not_usability_proof(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/contract-and-traceability.md")
        updates = self.read("references/design-input-updates.md")
        verification = self.read("references/verification-gates.md")
        plan_template = self.read("assets/templates/HARNESS_PLAN.template.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        e2e_template = self.read("assets/templates/E2E_VERIFICATION.template.md")
        goal = self.read("assets/templates/GOAL.template.md")

        for content in (skill, verification, plan_template, e2e_template):
            self.assertIn("UI Design Intake", content)
        self.assertIn("human-owned `ui-design.md`", goal)
        self.assertIn("ui-design.md", contract)
        self.assertIn("ui-design-builder", updates)
        self.assertIn("Every must-have `UX-*` trace", skill)
        self.assertIn("## UX Direction And Usability Evidence", verification)
        self.assertIn("owner approval proves only direction conformance", verification)
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
            commands = re.findall(
                r'`python "<design-system-compiler-skill-root>/scripts/check_design_system_pair\.py" [^`]+`',
                content,
            )
            self.assertEqual(1, len(commands), commands)
            self.assertIn("--markdown <design-system.md>", commands[0])
            self.assertIn("--registry <design-system.json>", commands[0])
            self.assertIn("--repo-root <repository-root>", commands[0])
            self.assertIn("--require-filled", commands[0])
            self.assertNotIn("--registry <design-system.json> --require-filled", commands[0])
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

    def test_both_documented_schema2_pair_commands_bind_repo_root(self) -> None:
        expected = (
            'python "<design-system-compiler-skill-root>/scripts/check_design_system_pair.py" '
            "--markdown <design-system.md> --registry <design-system.json> "
            "--repo-root <repository-root> --require-filled"
        )
        commands: list[str] = []
        for relative_path in (
            "references/contract-and-traceability.md",
            "references/verification-gates.md",
        ):
            content = self.read(relative_path)
            found = re.findall(rf"`({re.escape(expected)})`", content)
            self.assertEqual([expected], found, relative_path)
            commands.extend(found)
        self.assertEqual([expected, expected], commands)

    def test_schema_v5_graph_is_first_class(self) -> None:
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        run = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        self.assertIn('"schema_version": 6', plan)
        self.assertIn('"schema_version": 11', run)
        self.assertIn('"graph_state"', run)
        self.assertIn("max_traversals", self.read("references/graph-orchestration.md"))
        self.assertIn("invoke_external_runtime", run)
        self.assertNotIn('"workflow_runs"', run)

    def test_plan_provider_options_bind_worker_models(self) -> None:
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        adapters = self.read("references/runtime-adapters.md")
        self.assertIn('"allowed_providers": ["generic"]', plan)
        self.assertIn('"generic": {"model": null, "reasoning_effort": null}', plan)
        self.assertIn("Unsupported explicit options block", adapters)
        self.assertIn("host defaults", adapters)
        for model in ("gpt-5.6-sol", "gpt-5.6-terra", "sonnet", "haiku"):
            self.assertNotIn(model, plan + adapters)

    def test_verification_policy_selects_and_reuses_only_exact_focused_checks(self) -> None:
        skill = self.read(MANAGED_STAGE)
        verification = self.read("references/verification-gates.md")
        plan = self.read("assets/templates/HARNESS_PLAN.template.md")
        run = self.read("assets/templates/MISSION_RUNBOOK.template.md")
        worker = self.read("assets/templates/WORKER_GOAL.template.md")

        for content in (verification, plan, worker):
            self.assertIn('selection.mode: "changed_files"', content)
            self.assertIn("parent-observed changed files", content)
        for content in (skill, verification, run):
            self.assertIn("session_exact", content)
            self.assertIn("repository-external", content)
        self.assertIn('"isolation": "host"', plan)
        self.assertIn('"parallel_safe": false', plan)
        self.assertIn("real cross-mission", verification)
        self.assertIn("broad regression, browser E2E", verification)
        self.assertIn("after exact-SHA review and repair converge", plan)

    def test_schema_v10_closes_only_with_real_ui_evidence(self) -> None:
        skill = self.read(MANAGED_STAGE)
        state = self.read("references/execution-state-model.md")
        verification = self.read("references/verification-gates.md")
        runbook = self.read("assets/templates/MISSION_RUNBOOK.template.md")

        self.assertIn('"schema_version": 11', runbook)
        self.assertIn('"batch_gate_results"', runbook)
        self.assertIn('"final_gate_results"', runbook)
        self.assertIn('"ui_evidence"', runbook)
        self.assertIn("New managed work uses PLAN schema v6 and RUN schema v11", skill)
        self.assertIn("complete` is an execution closeout state", state)
        for content in (verification, runbook):
            self.assertIn("breakpoint-by-state", content)
            self.assertIn("SHA-256", content)
            self.assertIn("docs/goal/evidence/", content)

    def test_verifier_docs_bind_explicit_host_and_container_preflight(self) -> None:
        graph = self.read("references/graph-orchestration.md")
        verification = self.read("references/verification-gates.md")
        worker = self.read("references/worker-result-contract.md")
        self.assertIn("`host` policy", graph)
        self.assertIn("legacy-pins.md#container-verifiers-before-066", graph)
        for content in (verification, worker):
            self.assertIn("host", content)
            self.assertIn("container", content)
            self.assertIn("PLAN-bound", content)
        for content in (graph, verification, worker):
            self.assertNotIn("future separately implemented route", content)
            self.assertNotIn("route them through a planned external read-only verifier node", content)

    def test_bootstrap_seeds_agents_and_claude_governance_templates(self) -> None:
        skill = self.read("SKILL.md")
        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")
        development_owner = self.read("references/governance/development-rules.md")
        product_owner = self.read("references/governance/product-contracts.md")
        managed_owner = self.read("references/governance/managed-delivery.md")
        source_owner = self.read("references/governance/source-maintenance.md")
        project_claude = self.read("assets/templates/PROJECT_CLAUDE.template.md")
        worker_goal = self.read("assets/templates/WORKER_GOAL.template.md")
        configurator = self.read("scripts/configure_project_context.py")
        operating = self.read("references/project-operating-rules.md")
        managed_route = self.owner_section(
            operating, "## Managed Product Delivery Harness Runs"
        )

        self.assertIn("PROJECT_AGENTS.template.md", skill)
        self.assertIn("PROJECT_CLAUDE.template.md", skill)
        self.assertIn("## Repository Context Contract", skill)
        self.assertIn("scripts/configure_project_context.py --root <target-root>", skill)
        self.assertIn("generated files differ", skill)
        self.assertIn("current host's effective instruction precedence", skill)
        self.assertIn("never overwrite, normalize, silently copy", skill)
        self.assertIn("--merge-agents", skill)
        self.assertIn("reviewed plan", skill)
        self.assertIn("original/template hashes", skill)
        self.assertIn("unresolved semantic divergences", skill)
        self.assertIn("Host-specific context:", worker_goal)
        self.assertIn("Worker contract:", worker_goal)
        self.assertIn("Context source hashes:", worker_goal)
        self.assertIn("parent ran `scripts/check_launch_packet.py` before dispatch", worker_goal)
        self.assertIn("resources, permissions, authorizations", worker_goal)
        self.assertIn("Keep automatic context discovery enabled", worker_goal)
        self.assertIn('path.open("xb")', configurator)
        self.assertIn("## Runtime Boundary", project_agents)
        self.assertIn("Preserve the current host's effective instruction discovery", project_agents)
        self.assertIn("## Consumer Core Development Principles", development_owner)
        self.assertIn("### First Principles", development_owner)
        self.assertIn(
            "not from habit, inherited patterns, or how another project solved it",
            development_owner,
        )
        self.assertIn("### Module Size Limit", development_owner)
        self.assertNotIn("deleted and rewritten from scratch", project_agents)
        self.assertIn(
            "New code modules, including tests, are limited to 500 physical lines.",
            development_owner,
        )
        self.assertIn("Record existing oversized modules for scoped follow-up", development_owner)
        self.assertIn("not the Harness skill-source repository", development_owner)
        self.assertIn("checkpoint, not a hard limit", development_owner)
        self.assertIn("## Managed Product Delivery Harness Runs", managed_owner)
        self.assertIn("Small bounded work may proceed directly", development_owner)
        self.assertIn("## Consumer Keep Product Contracts Current", product_owner)
        self.assertIn(
            "small post-delivery fixes that do not use Product Delivery Harness PLAN/RUN",
            product_owner,
        )
        self.assertIn(
            "Adding a page, route, visible region, state, or responsive behavior is at least `structure`",
            product_owner,
        )
        self.assertIn(
            "not complete while implementation and the canonical product documents disagree",
            product_owner,
        )
        self.assertNotIn("<verification-command>", project_agents)
        self.assertNotIn("<e2e-command>", project_agents)
        self.assertNotIn("(List protected files here", project_agents)
        self.assertNotIn("current v10", project_agents)
        self.assertIn(
            "branch-promotion-contract.md#managed-run-archive-before-promotion",
            managed_route,
        )
        self.assertIn("@AGENTS.md", project_claude)
        self.assertIn("general runtime adapter reference", project_claude)
        self.assertIn("Direct work follows `AGENTS.md`", project_claude)
        self.assertIn("parent retains authorization", project_claude)
        self.assertIn("one fresh read-only reviewer on the unified head", project_claude)
        self.assertIn("security lens", project_claude)

        if REPO_ROOT is not None:
            root_agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
            root_claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertNotIn("codex/<short-name>", root_agents)
            self.assertIn("never add a fixed prefix", source_owner.lower())
            self.assertIn("governance/product-contracts.md#source-keep-product-contracts-current", root_agents)
            self.assertIn("@AGENTS.md", root_claude)
            self.assertIn("Direct work follows `AGENTS.md`", root_claude)
            self.assertIn("parent retains authorization", root_claude)

    def test_gitignore_contract_is_toolchain_specific_and_applies_to_both_routes(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/gitignore-contract.md")
        project_agents = self.read("assets/templates/PROJECT_AGENTS.template.md")
        root_agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8") if REPO_ROOT else ""

        self.assertIn("Gitignore impact: none | update | needs owner decision", skill)
        self.assertIn("both direct and managed routes", skill)
        self.assertIn("references/gitignore-contract.md", skill)
        self.assertIn("delivery-harness/references/gitignore-contract.md", project_agents)
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
            root_ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("skills/delivery-harness/references/gitignore-contract.md", root_agents)
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
        operating = self.read("references/project-operating-rules.md")
        product_owner = self.read("references/governance/product-contracts.md")
        monetization_owner = self.owner_section(
            operating, "## Monetization And Partner Channels"
        )

        self.assertIn("Monetization infrastructure gate", archetypes)
        self.assertIn("Partner channel gate and affiliate / referral / reseller model", archetypes)
        self.assertIn("add a separate partner-channel mission", archetypes)
        self.assertIn("Do not fold it into the billing/entitlement mission", archetypes)
        self.assertIn("commission reversal after refund/chargeback", archetypes)
        self.assertIn("PARTNER-* affiliate/referral/reseller", archetypes)
        self.assertIn("delivery-harness/references/governance/product-contracts.md#consumer-keep-product-contracts-current", project_agents)
        self.assertIn(
            "delivery-harness/references/project-operating-rules.md"
            "#monetization-and-partner-channels",
            project_agents,
        )
        self.assertIn("## Monetization And Partner Channels", operating)
        self.assertIn("RevenueCat is one candidate, never the default", monetization_owner)
        self.assertIn("an affiliate link alone does not satisfy it", monetization_owner)
        self.assertIn("#monetization-and-partner-channels", product_owner)

        if REPO_ROOT is not None:
            root_agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("governance/product-contracts.md#source-keep-product-contracts-current", root_agents)

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
        managed_owner = self.read("references/governance/managed-delivery.md")
        source_owner = self.read("references/governance/source-maintenance.md")
        ci = self.read("assets/templates/PROJECT_CI.template.yml")
        adapters = self.read("references/runtime-adapters.md")

        for content in (skill, managed_owner, source_owner):
            self.assertIn("never add a fixed prefix", content.lower())
        self.assertIn("does not own shared state", adapters)
        self.assertIn("ask before branch creation", skill.lower())
        self.assertNotIn("- '**'", ci)
        self.assertNotIn("push:", ci)
        self.assertNotIn("- development", ci)
        self.assertNotIn("codex/**", ci)

    def test_repo_ci_workflow_verifies_every_pushed_branch(self) -> None:
        # A candidate verifies once through pull_request; merge queue
        # candidates and manual releases still get dedicated CI runs.
        if REPO_ROOT is None:
            self.skipTest("no repository checkout around the skill")
        workflow = REPO_ROOT / ".github" / "workflows" / "harness-ci.yml"
        if not workflow.is_file():
            self.skipTest("repository has no harness-ci workflow")
        content = workflow.read_text(encoding="utf-8")
        self.assertNotIn("push:", content.split("jobs:", 1)[0])
        self.assertNotIn("- development", content)
        self.assertNotIn("codex/**", content)
        self.assertNotIn("- '**'", content)
        self.assertIn("merge_group:", content)
        self.assertIn("workflow_dispatch:", content)
        self.assertIn("github.event.pull_request.base.sha", content)
        self.assertIn("github.event.merge_group.base_sha", content)
        self.assertIn('[ "$result" != success ]', content)
        self.assertIn('HARNESS_GOLDEN_PATH: "1"', content)
        self.assertIn('-p "test_golden_path.py" -v', content)
        self.assertIn("PDH_REQUIRE_BROWSER_TESTS: \"1\"", content)
        self.assertIn("npx playwright install --with-deps chromium", content)
        for suite in ("product-definition-builder", "design-system-compiler", "product-activation", "seo-growth-review"):
            self.assertIn(
                f"unittest discover -s skills/{suite}/scripts/tests -v",
                content,
            )
        self.assertIn("skills/product-activation/scripts", content)
        self.assertIn(
            "unittest discover -s skills/product-activation/scripts/tests -v",
            content,
        )
        self.assertIn("skills/seo-growth-review/scripts", content)
        self.assertIn(
            "unittest discover -s skills/seo-growth-review/scripts/tests -v",
            content,
        )


if __name__ == "__main__":
    unittest.main()
