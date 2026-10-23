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

import check_ui_contract  # noqa: E402
import harness_transition  # noqa: E402


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
