from __future__ import annotations

import subprocess
import sys
import unittest
import re
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
STAGE = "references/stages/activation.md"
STAGE_ROUTES = (
    ("required-inputs", "Before preparation or execution"),
    ("workflow", "Before preparation or execution"),
    ("status-and-outcome-handoff", "Before ending an execution pass"),
    ("reference-routing", "Before ending an execution pass"),
    ("output", "Before ending an execution pass"),
)


def markdown_headings(text: str) -> set[str]:
    headings = set()
    in_frontmatter = False
    for line in text.splitlines():
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter or not line.startswith("#"):
            continue
        heading = line.lstrip("#").strip().lower()
        heading = re.sub(r"[^a-z0-9\s-]", "", heading)
        headings.add(re.sub(r"\s+", "-", heading.strip()))
    return headings


def link_problems(text: str, source: Path) -> list[str]:
    problems = []
    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path, _, anchor = target.partition("#")
        resolved = (source.parent / path).resolve()
        if not resolved.is_file():
            problems.append(f"missing target: {target}")
            continue
        if anchor and anchor not in markdown_headings(resolved.read_text(encoding="utf-8")):
            problems.append(f"missing anchor: {target}")
    return problems


class ProductActivationSkillContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (SKILL_ROOT / relative).read_text(encoding="utf-8")

    def test_identity_metadata_and_trigger_are_specific(self) -> None:
        skill = self.read("SKILL.md")
        metadata = self.read("agents/openai.yaml")
        self.assertIn("name: product-activation", skill)
        self.assertIn("post-delivery activation", skill)
        self.assertIn(
            "websites, web apps, APIs/backend services, iOS apps, Android apps, browser extensions, macOS apps, and Windows apps",
            skill,
        )
        self.assertIn('display_name: "Product Activation"', metadata)
        self.assertIn("$product-activation", metadata)
        self.assertIn("allow_implicit_invocation: false", metadata)

    def test_skill_preserves_delivery_and_authorization_boundaries(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(STAGE)
        contract = self.read("references/activation-contract.md")
        for phrase in (
            "Never create, edit, reopen, or extend `docs/goal/PLAN.md`",
            "Capability and permission are separate facts",
            "Never implement a missing product hook here",
            "never weakens the host policy",
            "read back before retrying",
            "Treat `configured` as distinct from `verified`",
        ):
            self.assertIn(phrase, skill)
        self.assertIn("After an unknown result, read back before any retry", stage)
        self.assertIn("Exact Action Digest", contract)
        self.assertIn("action_time_confirmation", contract)
        self.assertIn("user_handoff", contract)
        self.assertIn("A task cannot be ready until every dependency is `verified`", contract)
        self.assertIn("The mutation response cannot also be the read-back evidence", contract)

    def test_route_order_profiles_and_outcome_handoff_are_documented(self) -> None:
        stage = self.read(STAGE)
        profiles = self.read("references/profile-catalog.md")
        self.assertIn(
            "purpose-built connector, official API, official CLI, Browser, Computer Use, then manual handoff",
            stage,
        )
        for heading in (
            "## Core",
            "## Web",
            "## API / Backend",
            "## iOS",
            "## Android",
            "## Desktop",
            "## Browser Extension",
            "## Responsibility Separation",
            "## Growth And Discovery Profiles",
            "### aso-and-store-launch",
            "### agent-directory",
            "### geo-readback",
        ):
            self.assertIn(heading, profiles)
        self.assertIn("No profile submits, publishes, or spends automatically", profiles)
        for marker in ("`geo-readback`", "`aso-and-store-launch`", "`agent-directory`"):
            self.assertIn(marker, stage)
        self.assertIn("requires that discovery surface", stage)
        self.assertIn("verified `MS-*`", stage)
        self.assertIn("real measurement window closes", stage)

    def test_entry_keeps_execution_boundary_and_conditional_stage_routes(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(STAGE)

        self.assertIn("## Stage Routing", skill)
        self.assertIn("Activation is execution by default", skill)
        self.assertIn("finish every ready, authorized required action", skill)
        self.assertIn("concrete blocker or an explicit owner planning request", skill)
        self.assertIn("Unknown applicability stays unresolved", skill)
        self.assertIn("fixed SHA and artifact/build identity", skill)
        self.assertIn("honest blocker", skill)
        for heading in ("## Required Inputs", "## Workflow", "## Status And Outcome Handoff", "## Reference Routing", "## Output"):
            self.assertNotIn(heading, skill)
            self.assertIn(heading, stage)
        for anchor, trigger in STAGE_ROUTES:
            with self.subTest(anchor=anchor, trigger=trigger):
                self.assertIn(trigger, skill)
                self.assertRegex(skill, rf"\({re.escape(STAGE)}#{anchor}\)")
                self.assertIn(anchor, markdown_headings(stage))

    def test_activation_consumes_approved_product_and_stack_decisions(self) -> None:
        stage = self.read(STAGE)
        contract = self.read("references/activation-contract.md")

        self.assertIn("approved Stack Decision Checkpoint", stage)
        self.assertIn("check_product_package.py", stage)
        self.assertIn("Target / guardrail", contract)
        self.assertIn("historical three-column", contract)
        self.assertIn("`Signal | Release targets | Source ID | Status`", contract)
        self.assertIn("a coverage row points at them and does not copy them", contract)

    def test_workflow_reads_are_scoped_and_checkers_run_once(self) -> None:
        stage = self.read(STAGE)
        workflow = stage.split("## Workflow", 1)[1].split("\n## ", 1)[0]

        self.assertNotIn("completely", workflow)
        self.assertIn("profile-catalog.md` Core, the surface sections that the architecture surface classes map to", workflow)
        self.assertIn("full `check_activation.py` command in step 15", workflow)
        self.assertIn("do not run them separately", workflow)
        self.assertIn("once before closeout", workflow)
        routing = stage.split("## Reference Routing", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(3, len([line for line in routing.splitlines() if line.startswith("- ")]))

    def test_required_inputs_name_the_sections_activation_reads(self) -> None:
        stage = self.read(STAGE)
        inputs = stage.split("## Required Inputs", 1)[1].split("\n## ", 1)[0]

        self.assertNotIn("Read the applicable files", inputs)
        self.assertIn("read only these sections", inputs)
        self.assertIn("Workflow checkers still join each complete file", inputs)
        for section in (
            "`Metrics`, and `Test Obligations`",
            "`Data and Trust`",
            "`Release Targets`",
            "approved Stack Decision Checkpoint and each applicable `Recorded or Approved Stack`",
            "`Required Secrets and Variables`",
            "`Product Activation Handoff`",
        ):
            self.assertIn(section, inputs)
        self.assertIn("Read another section when a selected profile or action needs it", inputs)
        self.assertIn("Read an existing `docs/ACTIVATION.md` in full", inputs)

    def test_release_authority_and_digest_contract_are_strict(self) -> None:
        stage = self.read(STAGE)
        contract = self.read("references/activation-contract.md")

        self.assertIn("architecture parser is the only release-target authority", stage)
        self.assertIn("release_targets.py", contract)
        self.assertIn("activation-action/2", contract)
        self.assertIn("read-back capability observation ID", contract)
        self.assertIn("behavior verification", contract)
        self.assertIn("duplicate required section", contract)
        self.assertIn("--architecture docs/product/architecture.md", contract)
        self.assertIn("--deployment docs/DEPLOYMENT.md", contract)

    def test_template_passes_structural_checker(self) -> None:
        template = SKILL_ROOT / "assets" / "templates" / "ACTIVATION.template.md"
        checker = SKILL_ROOT / "scripts" / "check_activation.py"
        result = subprocess.run(
            [sys.executable, str(checker), "--activation", str(template)],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_entry_and_stage_markdown_links_resolve(self) -> None:
        entry_path = SKILL_ROOT / "SKILL.md"
        stage_path = SKILL_ROOT / STAGE
        self.assertEqual([], link_problems(entry_path.read_text(encoding="utf-8"), entry_path))
        self.assertEqual([], link_problems(stage_path.read_text(encoding="utf-8"), stage_path))

    def test_missing_activation_route_or_anchor_is_detected(self) -> None:
        entry_path = SKILL_ROOT / "SKILL.md"
        entry = entry_path.read_text(encoding="utf-8")
        bad_anchor = entry.replace(f"{STAGE}#required-inputs", f"{STAGE}#missing-inputs")
        self.assertIn("missing anchor: references/stages/activation.md#missing-inputs", link_problems(bad_anchor, entry_path))

        missing_route = entry.replace(
            "- Before preparation or execution, read [Required Inputs](references/stages/activation.md#required-inputs), [Workflow](references/stages/activation.md#workflow), and [Activation Contract](references/activation-contract.md).\n",
            "",
        )
        self.assertNotIn("#required-inputs", missing_route)
        self.assertNotIn("Before preparation or execution", missing_route)


if __name__ == "__main__":
    unittest.main()
