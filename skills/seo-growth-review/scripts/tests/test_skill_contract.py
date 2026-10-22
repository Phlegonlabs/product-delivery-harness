import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
SEO_STAGE = "references/stages/seo-review.md"


def markdown_targets(text: str):
    for match in re.finditer(r"\[[^]]+\]\(([^)]+)\)", text):
        target = match.group(1)
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        yield target


def markdown_headings(text: str) -> set[str]:
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
        headings.add(re.sub(r"\s+", "-", heading.strip()))
    return headings


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
        stage = self.read(SEO_STAGE)
        method = self.read("references/review-method.md")

        for mode in ("`baseline`", "`growth_review`", "`traffic_drop`"):
            self.assertIn(mode, stage)
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
        self.assertIn("do not create a kanban board, standing dashboard", stage)

    def test_openai_metadata_matches_skill_identity(self) -> None:
        metadata = self.read("agents/openai.yaml")

        self.assertIn('display_name: "SEO Growth Review"', metadata)
        self.assertIn("$seo-growth-review", metadata)

    def test_saved_lifecycle_review_is_separate_from_inline_audit(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(SEO_STAGE)
        method = self.read("references/review-method.md")
        catalog = self.read("references/source-catalog.md")
        template = self.read("assets/templates/SEO_REVIEW.template.md")

        self.assertIn("A standalone inline audit remains valid", skill)
        self.assertIn("`seo-review/2` is the only format", skill)
        self.assertNotIn("seo-review/1", skill)
        self.assertIn("sections of [SEO Source Catalog]", skill)
        self.assertIn("docs/seo/reviews/YYYY-MM-DD-<slug>.md", stage)
        self.assertIn("check_seo_review.py --require-lifecycle", stage)
        self.assertIn("## Saved Lifecycle Public-Release Review", method)
        self.assertIn("Activation sha256", template)
        self.assertIn("only when Activation marks the matching `MS-*` source", catalog)

    def test_stage_routing_keeps_inline_and_saved_reviews_separate(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(SEO_STAGE)

        self.assertIn("## Stage Routing", skill)
        self.assertIn("no repository prerequisite, but still needs the production URL or domain", skill)
        self.assertIn("target market, language, and business outcome", skill)
        self.assertIn("makes SEO `not applicable`", skill)
        self.assertIn("Missing market, language, or business outcome remains a review gap", skill)
        self.assertIn("Inline output follows the applicable rules without creating a repository artifact", skill)
        self.assertIn("use them only after an explicit save request", skill)

        for heading in ("Required Inputs", "Modes", "Workflow", "Reference Routing", "Output"):
            with self.subTest(heading=heading):
                self.assertNotIn(f"## {heading}", skill)
                self.assertIn(f"## {heading}", stage)

        workflow = stage.split("## Workflow\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("references/source-catalog.md", workflow)
        self.assertIn("references/review-method.md", workflow)
        self.assertIn("assets/templates/SEO_REVIEW.template.md", workflow)
        self.assertIn("scripts/check_seo_review.py --require-lifecycle", workflow)

        sources = (
            ("entry", SKILL_ROOT, SKILL_ROOT / "SKILL.md"),
            ("stage", SKILL_ROOT / SEO_STAGE, SKILL_ROOT / SEO_STAGE),
        )
        for source_name, source_root, source_path in sources:
            for target in markdown_targets(source_path.read_text(encoding="utf-8")):
                with self.subTest(source=source_name, target=target):
                    self.assertFalse(target.startswith(("/", "\\\\")), target)
                    file_part, separator, anchor = target.partition("#")
                    resolved = (source_root / file_part).resolve()
                    self.assertTrue(resolved.is_file(), target)
                    if separator:
                        self.assertIn(anchor, markdown_headings(resolved.read_text(encoding="utf-8")))

        missing_anchor = stage.replace("## Workflow", "## Review Steps")
        self.assertNotIn("workflow", markdown_headings(missing_anchor))

        missing_pointer = skill.replace(
            "references/stages/seo-review.md#workflow",
            "references/stages/seo-review.md#missing-workflow",
        )
        self.assertNotIn("references/stages/seo-review.md#workflow", missing_pointer)
        self.assertIn("references/stages/seo-review.md#missing-workflow", missing_pointer)


if __name__ == "__main__":
    unittest.main()
