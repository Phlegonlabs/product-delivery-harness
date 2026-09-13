import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class SeoGrowthReviewSkillContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (SKILL_ROOT / relative).read_text(encoding="utf-8")

    def test_skill_is_read_only_and_routes_owned_mutations(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn("name: seo-growth-review", skill)
        self.assertIn("Remain read-only", skill)
        self.assertIn("`product-activation`", skill)
        self.assertIn("`product-definition-builder`", skill)
        self.assertIn("`delivery-harness`", skill)
        self.assertIn("`connector_gap`", skill)
        self.assertIn("Never embed an OAuth flow", skill)
        self.assertIn("Do not promise rankings", skill)

    def test_source_roles_do_not_conflate_unlike_metrics(self) -> None:
        catalog = self.read("references/source-catalog.md")
        method = self.read("references/review-method.md")

        self.assertIn("Search Console", catalog)
        self.assertIn("GA4", catalog)
        self.assertIn("Google Trends", catalog)
        self.assertIn("Keyword Planner", catalog)
        self.assertIn("advertiser competition, not organic SEO difficulty", catalog)
        self.assertIn("do not force clicks and sessions", catalog)
        self.assertIn("`observed`", method)
        self.assertIn("`estimated`", method)
        self.assertIn("`hypothesis`", method)

    def test_review_has_modes_routes_and_no_mandatory_dashboard(self) -> None:
        skill = self.read("SKILL.md")
        method = self.read("references/review-method.md")

        for mode in ("`baseline`", "`growth_review`", "`traffic_drop`"):
            self.assertIn(mode, skill)
        for route in (
            "`product_activation`",
            "`product_definition`",
            "`delivery`",
            "`connector`",
            "`observe_later`",
            "`owner`",
        ):
            self.assertIn(route, method)
        self.assertIn("Return the result inline", method)
        self.assertIn("do not create a kanban board, standing dashboard", skill)

    def test_openai_metadata_matches_skill_identity(self) -> None:
        metadata = self.read("agents/openai.yaml")

        self.assertIn('display_name: "SEO Growth Review"', metadata)
        self.assertIn("$seo-growth-review", metadata)

    def test_saved_lifecycle_review_is_separate_from_inline_audit(self) -> None:
        skill = self.read("SKILL.md")
        method = self.read("references/review-method.md")
        catalog = self.read("references/source-catalog.md")
        template = self.read("assets/templates/SEO_REVIEW.template.md")

        self.assertIn("A standalone inline audit remains valid", skill)
        self.assertIn("docs/seo/reviews/YYYY-MM-DD-<slug>.md", skill)
        self.assertIn("check_seo_review.py --require-lifecycle", skill)
        self.assertIn("## Saved Lifecycle Public-Release Review", method)
        self.assertIn("Activation sha256", template)
        self.assertIn("only when Activation marks the matching `MS-*` source", catalog)


if __name__ == "__main__":
    unittest.main()
