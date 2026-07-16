import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class PrdBuilderSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_skill_routes_browser_products_to_frontend_selection(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("references/frontend-stack-selection.md", skill)
        self.assertIn("recommend one explicit stack", skill)
        self.assertIn("recommendation is not misrepresented as a fixed requirement", skill)
        self.assertIn("Cloudflare is a deployment/runtime platform", skill)
        self.assertIn("when the product has a browser surface", agent)

    def test_selection_guide_separates_layers_and_product_patterns(self) -> None:
        guide = self.read("references/frontend-stack-selection.md")

        self.assertIn("## First Separate the Layers", guide)
        self.assertIn("## Product-Fit Patterns", guide)
        self.assertIn("Astro + React islands", guide)
        self.assertIn("React + Vite", guide)
        self.assertIn("Cloudflare Workers with Static Assets", guide)
        self.assertIn("## Official Sources to Recheck", guide)

    def test_output_contract_requires_decision_and_verification(self) -> None:
        contract = self.read("references/output-contract.md")

        self.assertIn("## Frontend Delivery Requirements", contract)
        self.assertIn("## Frontend Technology Decision", contract)
        self.assertIn("Decision status: [Required / Selected / Recommended / Provisional]", contract)
        self.assertIn("### Recorded or Recommended Stack", contract)
        self.assertIn("### Rendering and Route Strategy", contract)
        self.assertIn("### Platform Compatibility Verification", contract)
        self.assertIn("### Unresolved Decision Protocol", contract)
        self.assertIn("a bare `TBD` does not pass validation", contract)

    def test_discovery_and_architecture_capture_selection_evidence(self) -> None:
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")

        self.assertIn("content-led, interaction-led", interview)
        self.assertIn("rendering needs", interview)
        self.assertIn(
            "For products with a browser frontend, frontend technology layers",
            architecture,
        )
        self.assertIn("official-source verification date", architecture)

    def test_wireframes_keep_landing_pages_simple_and_label_media(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read("agents/openai.yaml")
        interview = self.read("references/interview-guide.md")
        guide = self.read("references/wireframe-guide.md")
        contract = self.read("references/output-contract.md")

        self.assertIn("one job per section", skill)
        self.assertIn("exact UI wording or a bounded display contract", skill)
        self.assertIn("## Content Specificity Rules", guide)
        self.assertIn("## Style And Anti-Slop Structure Rules", guide)
        self.assertIn("colored side rail or accent stripe", guide)
        self.assertIn("A box in an ASCII wireframe must mean real grouping", guide)
        self.assertIn("`Exact copy`", guide)
        self.assertIn("`Display contract`", guide)
        self.assertIn("Do not leave `Main content`", guide)
        self.assertIn("## KISS Landing Page Rules", guide)
        self.assertIn("Do not turn every PRD requirement", guide)
        self.assertIn("### Content, Style, Media & Motion Notes", guide)
        self.assertIn("Style direction", guide)
        self.assertIn("required / optional / none", guide)
        self.assertIn("### Content, Style, Media & Motion Notes", contract)
        self.assertIn("Exact wording or display contract", contract)
        self.assertNotIn("| Main content", contract)
        self.assertIn("KISS landing-page wireframes", agent)
        self.assertIn("bounded display contracts", agent)
        self.assertIn("explicit style/image/media/motion labels", agent)
        self.assertIn("restrained container use", agent)
        self.assertIn("already have approved wording", interview)
        self.assertIn("bounded display responsibilities", interview)
        self.assertIn("specific style direction or animation", interview)
        self.assertIn("Required style and motion intent", interview)


if __name__ == "__main__":
    unittest.main()
