"""Exercise consumer command examples with real parsers and source scans."""

import contextlib
import io
import json
from pathlib import Path
import re
import shlex
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import check_ui_contract  # noqa: E402
import harness_transition  # noqa: E402
import worktree_fanout  # noqa: E402


class DocumentedCommandTests(unittest.TestCase):
    def test_ui_research_uses_current_parent_owned_assignment_contract(self):
        skills = SCRIPTS.parents[1]
        stage_path = skills / "ui-design-builder/references/stages/ui-design.md"
        source = stage_path.read_text(encoding="utf-8")
        research = source.split("2. **Resolve UI research", 1)[1].split("\n3. ", 1)[0]
        target = "../../../delivery-harness/references/delegation-contract.md"
        self.assertIn(f"]({target})", research)
        self.assertTrue((stage_path.parent / target).resolve().is_file())
        for obligation in ("frozen assignment packets", "parent launches", "result reconciliation",
                           "input identities", "separate launch records", "joined sourced findings",
                           "Agent policy", "required research independence"):
            self.assertIn(obligation, research)
        self.assertNotIn("readonly_assignments.cjs", source)

    def test_project_agents_template_points_at_real_managed_run_rules(self):
        templates = SCRIPTS.parent / "assets/templates"
        agents = (templates / "PROJECT_AGENTS.template.md").read_text(encoding="utf-8")
        self.assertNotIn("this file's **Managed Product Delivery Harness Runs**", agents)
        self.assertNotIn("Rules under **Managed Product Delivery Harness Runs**", agents)
        self.assertIn("project-operating-rules.md#managed-product-delivery-harness-runs", agents)
        rules = (SCRIPTS.parent / "references/project-operating-rules.md").read_text(encoding="utf-8")
        self.assertIn("\n## Managed Product Delivery Harness Runs\n", rules.replace("\r\n", "\n"))

    def test_deployment_template_prose_is_not_a_placeholder(self):
        import check_deployment

        template = (SCRIPTS.parent / "assets/templates/DEPLOYMENT.template.md").read_text(encoding="utf-8")
        intro = [line for line in template.splitlines() if line.startswith("One row per `MS-*` source")]
        self.assertEqual(1, len(intro))
        self.assertFalse(check_deployment._is_placeholder(intro[0]))

    def test_readiness_card_keeps_unused_actions_and_push_unauthorized(self):
        cards = (SCRIPTS.parent / "references/stages/stage-cards.md").read_text(encoding="utf-8")
        self.assertNotIn("every action entry needs `authorized: true`", cards)
        self.assertIn("`push` always, stays `authorized: false`", cards)
        readiness = cards.split("## Card 3: Readiness", 1)[1].split("## Card 4", 1)[0]
        self.assertIn("Run the Environment Preflight once in the clean base checkout", readiness)
        self.assertIn("An Environment Preflight row fails or is unobserved", readiness)

    def test_dispatch_card_keeps_parent_commits_off_the_run_branch(self):
        cards = (SCRIPTS.parent / "references/stages/stage-cards.md").read_text(encoding="utf-8")
        dispatch = cards.split("## Card 4: Dispatch", 1)[1].split("## Card 5", 1)[0]
        self.assertIn("the run branch takes only the mission merge", dispatch)
        record = cards.split("## Card 5: Record Results", 1)[1].split("## Card 6", 1)[0]
        self.assertIn("a parent commit sits between the recorded integration head", record)
        state = (SCRIPTS.parent / "references/execution-state-model.md").read_text(encoding="utf-8")
        self.assertIn("commit nothing to the run branch except mission merges", state)
        self.assertNotIn("No coordination commit is needed between checkpoints", state)

    def test_stack_option_map_retains_authorship_and_checker_without_generator(self):
        source = (SCRIPTS.parents[1] / "product-definition-builder/references/output-contract.md").read_text(encoding="utf-8")
        section = source.split("## `stack-decisions.md`", 1)[1].split("### Coherent Options Presented", 1)[0]
        for obligation in ("Product Definition author derives", "owner's accepted checkpoint",
                           "canonical digest binding", "Approved option map: None",
                           "complete option evidence and exact map", "product-package checker",
                           "repository authority"):
            self.assertIn(obligation, section)
        self.assertNotIn("render_stack_option_map.py", source)

    def commands(self, reference, script):
        text = (SCRIPTS.parent / "references" / reference).read_text(encoding="utf-8")
        examples = [shlex.split(value) for value in re.findall(r"`(python [^`]+)`", text)
                    if f"/{script}" in value]
        self.assertTrue(examples, f"Missing executable {script} example in {reference}")
        return examples

    def test_plan_width_examples_parse_and_documented_codes_match_the_script(self):
        import plan_width
        from manifest_fixtures import graph_node, mission, task, valid_plan

        stage = (SCRIPTS.parent / "references/stages/managed-delivery.md").read_text(encoding="utf-8")
        cards = (SCRIPTS.parent / "references/stages/stage-cards.md").read_text(encoding="utf-8")
        inline = re.findall(r"`(python [^`]*plan_width\.py[^`]*)`", stage)
        fenced = [line.strip() for line in cards.splitlines()
                  if line.strip().startswith("python ") and "/plan_width.py" in line]
        self.assertEqual(1, len(inline))
        self.assertEqual(1, len(fenced))
        for command in inline + fenced:
            argv = shlex.split(command)
            parsed = plan_width.build_parser().parse_args(argv[2:])
            self.assertEqual(Path("<PLAN.md>"), parsed.plan)
            self.assertFalse(parsed.json)

        plan = valid_plan()
        plan["missions"] = [
            mission(f"M{index}", f"REQ-{index:03d}", f"src/{chr(96 + index)}/**",
                    [task(f"M{index}", 1, f"REQ-{index:03d}", f"src/{chr(96 + index)}/one.py")])
            for index in range(1, 6)
        ]
        for item in plan["missions"][2:]:
            item["serialized_resources"] = ["db:primary"]
        outcomes = ["pass", "retryable_failure", "blocked", "contract_gap"]
        plan["graph"] = {
            "entry_nodes": ["N-M1", "N-M2", "N-M4", "N-M5"],
            "nodes": [graph_node(f"N-M{index}", "mission", f"M{index}", "runtime_worker", outcomes)
                      for index in range(1, 6)],
            "edges": [{
                "id": "E-M1-M3", "kind": "dependency", "from": "N-M1", "to": "N-M3",
                "on_outcomes": ["pass"], "max_traversals": None,
            }],
        }
        plan["max_parallel_workers"] = 2
        emitted = {finding["code"] for finding in plan_width.measure(plan)["findings"]}
        documented = set(re.findall(
            r"`([a-z_]+)`", re.search(r"findings \(([^)]*)\)", stage).group(1)))
        self.assertEqual(
            {"chain_without_conflict", "same_level_conflict",
             "shared_exclusive_resource", "budget_below_width"},
            emitted)
        self.assertEqual(emitted, documented)

    def test_documented_product_css_flag_parses_in_the_assembler(self):
        builder = SCRIPTS.parents[1] / "ui-design-builder"
        contract = (builder / "references/output-contract.md").read_text(encoding="utf-8")
        self.assertIn("assemble_ui_review.py --mode hifi --product-css <file>", contract)
        sys.path.insert(0, str(builder / "scripts"))
        try:
            import assemble_ui_review
            parsed = assemble_ui_review.parse_args([
                "--mode", "hifi", "--product-css", "kit.css", "--manifest", "m.json",
                "--source", "index.html=index.html", "--output-dir", "out"])
        finally:
            sys.path.remove(str(builder / "scripts"))
        self.assertEqual(Path("kit.css"), parsed.product_css)
        self.assertIsNone(assemble_ui_review.parse_args(
            ["--manifest", "m.json", "--source", "index.html=index.html", "--output-dir", "out"]).product_css)

    def test_direct_fan_out_commands_parse_and_route_is_linked(self):
        examples = self.commands("direct-fan-out.md", "worktree_fanout.py")
        self.assertEqual(2, len(examples))
        scopes, merge_check = (
            worktree_fanout.build_parser().parse_args(parts[2:]) for parts in examples
        )
        self.assertEqual("scopes", scopes.command)
        self.assertEqual(2, len(scopes.part))
        self.assertEqual("merge-check", merge_check.command)
        self.assertEqual("<root>", merge_check.repo_root)
        self.assertEqual("<sha>", merge_check.base)
        self.assertEqual("<branch>", merge_check.head)
        self.assertEqual(["<claim>"], merge_check.scope)
        self.assertEqual("<worktree>", merge_check.worktree)
        skill = (SCRIPTS.parent / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("(references/direct-fan-out.md)", skill)

    def test_documented_review_skip_parses_without_state_mutation(self):
        examples = self.commands("verification-gates.md", "harness_transition.py")
        skips = [parts for parts in examples if "skip-integration-review" in parts]
        self.assertEqual(1, len(skips))
        parsed = harness_transition.build_parser().parse_args(skips[0][2:])
        self.assertEqual("skip-integration-review", parsed.command)
        self.assertEqual(Path("<root>"), parsed.repo_root)
        self.assertEqual(Path("<PLAN.md>"), parsed.plan)
        self.assertEqual(Path("<RUN.md>"), parsed.run)

    def test_documented_conditional_repair_routes_validate_and_stay_bounded(self):
        from harness_manifest import validate_plan
        from manifest_fixtures import conditional_final_candidate_plan

        text = (SCRIPTS.parent / "references/graph-orchestration.md").read_text(encoding="utf-8")
        section = text.split("### Optional Repair-Only Mission", 1)[1].split("## Root-Cause", 1)[0]
        routes = json.loads(re.search(r"```json\n(.*?)\n```", section, re.S).group(1))
        for route in routes:
            for key in ("from", "to"):
                if route[key] == "N-REPAIR":
                    route[key] = "N-M4"
        plan = conditional_final_candidate_plan()
        route_ids = {route["id"] for route in routes}
        plan["graph"]["edges"] = [edge for edge in plan["graph"]["edges"] if edge["id"] not in route_ids] + routes
        self.assertEqual([], validate_plan(plan))
        routes[0]["max_traversals"] = 2
        self.assertTrue(any("one bounded repair" in error for error in validate_plan(plan)))

    def test_documented_ui_scans_check_real_source_and_reject_raw_values(self):
        for reference in ("ui-implementation-contract.md", "verification-gates.md"):
            for command in self.commands(reference, "check_ui_contract.py"):
                with self.subTest(reference=reference), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve()
                    source = root / "src"
                    source.mkdir()
                    page = source / "page.css"
                    page.write_text(".content { color: var(--text); }", encoding="utf-8")
                    registry = root / "design-system.json"
                    registry.write_text(json.dumps({"tokenSources": [], "primitiveSources": [],
                                                    "primitives": {}, "motionVariants": [],
                                                    "viewports": [390, 768, 1440]}),
                                        encoding="utf-8")
                    values = {"<root>": str(root), "<design-system.json>": str(registry),
                              "<product-source-dir>": str(source)}
                    argv = [values.get(part, part) for part in command[2:]]
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        result = check_ui_contract.main(argv)
                    self.assertEqual(0, result, output.getvalue())
                    page.write_text(".content { color: #123456; padding: 13px; }", encoding="utf-8")
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(1, check_ui_contract.main(argv))


if __name__ == "__main__":
    unittest.main()
