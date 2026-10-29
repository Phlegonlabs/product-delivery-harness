"""Entry routes must name complete, resolvable governance owners."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_ROOT = REPO_ROOT / "skills/delivery-harness"
SKILLS_ROOT = REPO_ROOT / "skills"
GOVERNANCE = SKILL_ROOT / "references/governance"
ENTRY_TEMPLATE = SKILL_ROOT / "assets/templates/PROJECT_AGENTS.template.md"


def anchor_slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", heading.lower().replace(" ", "-"))


def route_target(route: str, *, consumer: bool = False) -> tuple[Path, str]:
    target, separator, anchor = route.partition("#")
    assert separator, route
    if consumer:
        prefix = "delivery-harness/"
        assert target.startswith(prefix), route
        target = target[len(prefix):]
    path = SKILL_ROOT / target if consumer else REPO_ROOT / target
    return path, anchor


class GovernanceEntryRouteTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        self.assertTrue(path.is_file(), path)
        return path.read_text(encoding="utf-8")

    def assert_routes_resolve(self, text: str, *, consumer: bool) -> None:
        if consumer:
            routes = re.findall(r"`(delivery-harness/references/[^`#]+#[^`]+)`", text)
        else:
            routes = [
                match.group(1)
                for match in re.finditer(r"\]\(([^)#]+#[^)]+)\)", text)
                if not match.group(1).startswith(("http://", "https://"))
            ]
        self.assertGreater(len(routes), 0)
        for route in routes:
            with self.subTest(route=route):
                path, anchor = route_target(route, consumer=consumer)
                self.assertTrue(path.is_file(), route)
                headings = re.findall(r"^#{1,6} (.+)$", self.read(path), re.MULTILINE)
                self.assertIn(anchor, {anchor_slug(heading) for heading in headings}, route)

    def test_source_entry_routes_are_complete_and_resolvable(self) -> None:
        root = self.read(REPO_ROOT / "AGENTS.md")
        self.assert_routes_resolve(root, consumer=False)
        self.assertIn("Task start; significant edit", root)
        self.assertIn("Preserve unrelated local work.", root)
        self.assertIn("explicit owner approval before deletion, overwrite, or move.", root)
        for route in (
            "skills/delivery-harness/references/governance/task-and-handoff.md#project-entry-and-current-work",
            "skills/delivery-harness/references/governance/task-and-handoff.md#repository-change-checkpoints",
            "skills/delivery-harness/references/governance/task-and-handoff.md#handoff-documentation-audit",
            "skills/delivery-harness/references/governance/development-rules.md#protect-local-data",
            "skills/delivery-harness/references/governance/development-rules.md#keep-changes-simple",
            "skills/delivery-harness/references/governance/development-rules.md#document-writing",
            "skills/delivery-harness/references/governance/development-rules.md#source-core-development-principles",
            "skills/delivery-harness/references/governance/product-contracts.md#source-keep-product-contracts-current",
            "skills/delivery-harness/references/governance/product-contracts.md#monetization-and-partner-channels",
            "skills/delivery-harness/references/governance/source-maintenance.md#required-reading",
            "skills/delivery-harness/references/governance/source-maintenance.md#mission-task-split",
            "skills/delivery-harness/references/governance/source-maintenance.md#git-flow",
            "skills/delivery-harness/references/governance/source-maintenance.md#required-verification",
            "skills/delivery-harness/references/governance/source-maintenance.md#update-local-skills",
            "skills/delivery-harness/references/governance/source-maintenance.md#review-guidelines",
        ):
            with self.subTest(mandatory_source_route=route):
                self.assertIn(route, root)
        self.assertIn(
            "The actual frontend author reads the complete pinned `frontend-design` SKILL.md "
            "and applicable project design skills in its own context; verify the full-tree pin independently.",
            root,
        )

    def test_consumer_entry_routes_are_complete_and_resolvable(self) -> None:
        template = self.read(ENTRY_TEMPLATE)
        self.assert_routes_resolve(template, consumer=True)
        self.assertIn("Task start; significant edit", template)
        self.assertIn("Preserve unrelated local work.", template)
        self.assertIn("explicit owner approval before deletion, overwrite, or move.", template)
        for route in (
            "delivery-harness/references/governance/task-and-handoff.md#project-entry-and-current-work",
            "delivery-harness/references/governance/task-and-handoff.md#repository-change-checkpoints",
            "delivery-harness/references/governance/task-and-handoff.md#handoff-documentation-audit",
            "delivery-harness/references/governance/development-rules.md#protect-local-data",
            "delivery-harness/references/governance/development-rules.md#keep-changes-simple",
            "delivery-harness/references/governance/development-rules.md#document-writing",
            "delivery-harness/references/governance/development-rules.md#consumer-core-development-principles",
            "delivery-harness/references/governance/product-contracts.md#consumer-keep-product-contracts-current",
            "delivery-harness/references/project-operating-rules.md#monetization-and-partner-channels",
            "delivery-harness/references/governance/managed-delivery.md#git-safety",
            "delivery-harness/references/governance/managed-delivery.md#managed-product-delivery-harness-runs",
            "delivery-harness/references/governance/managed-delivery.md#review-guidelines",
        ):
            with self.subTest(mandatory_consumer_route=route):
                self.assertIn(route, template)
        self.assertIn(
            "The actual frontend author reads the complete pinned `frontend-design` SKILL.md "
            "and applicable project design skills in its own context; verify the full-tree pin independently.",
            template,
        )
        self.assertNotIn(
            "delivery-harness/references/governance/task-and-handoff.md#source-completion",
            template,
        )

    def test_moved_top_level_sections_have_applicable_routes(self) -> None:
        source_routes = self.read(REPO_ROOT / "AGENTS.md")
        consumer_routes = self.read(ENTRY_TEMPLATE)
        source_coverage = {
            "task-and-handoff.md": (
                "#project-entry-and-current-work",
                "#repository-change-checkpoints",
                "#handoff-documentation-audit",
                "#source-completion",
            ),
            "development-rules.md": (
                "#protect-local-data", "#keep-changes-simple",
                "#document-writing", "#source-core-development-principles",
            ),
            "product-contracts.md": (
                "#source-keep-product-contracts-current",
                "#monetization-and-partner-channels",
            ),
            "source-maintenance.md": (
                "#required-reading", "#mission-task-split", "#git-flow",
                "#update-local-skills", "#required-verification",
                "#review-guidelines",
            ),
        }
        consumer_coverage = {
            "task-and-handoff.md": (
                "#project-entry-and-current-work",
                "#repository-change-checkpoints",
                "#handoff-documentation-audit",
                "#consumer-completion",
            ),
            "development-rules.md": (
                "#protect-local-data", "#keep-changes-simple",
                "#document-writing", "#consumer-core-development-principles",
            ),
            "product-contracts.md": ("#consumer-keep-product-contracts-current",),
            "managed-delivery.md": (
                "#git-safety", "#managed-product-delivery-harness-runs",
                "#review-guidelines",
            ),
        }
        for routes, coverage in (
            (source_routes, source_coverage),
            (consumer_routes, consumer_coverage),
        ):
            for owner, anchors in coverage.items():
                for anchor in anchors:
                    with self.subTest(owner=owner, anchor=anchor):
                        self.assertIn(owner + anchor, routes)

    def test_consumer_lifecycle_routes_are_conditionally_separate(self) -> None:
        template = self.read(ENTRY_TEMPLATE)
        table = template.split("## Mandatory Governance Routes", 1)[1].split(
            "The Epic and index record", 1
        )[0]
        lines = table.splitlines()
        managed_line = next(line for line in lines if line.startswith("| Managed PLAN/RUN"))
        deployment_line = next(line for line in lines if line.startswith("| Deployment "))
        setup_line = next(line for line in lines if line.startswith("| External setup and measurement sources"))

        self.assertIn(
            "delivery-harness/references/governance/managed-delivery.md"
            "#managed-product-delivery-harness-runs",
            managed_line,
        )
        self.assertIn(
            "delivery-harness/references/project-operating-rules.md"
            "#managed-product-delivery-harness-runs",
            managed_line,
        )
        self.assertNotIn("#external-setup", managed_line)
        self.assertNotIn("#monetization-and-partner-channels", managed_line)
        self.assertIn(
            "delivery-harness/references/deployment-contract.md#deployment-contract",
            deployment_line,
        )
        self.assertNotIn("managed-delivery.md", deployment_line)
        self.assertNotIn("project-operating-rules.md", deployment_line)
        self.assertIn(
            "delivery-harness/references/project-operating-rules.md"
            "#external-setup",
            setup_line,
        )
        self.assertNotIn("managed-delivery.md", setup_line)
        self.assertNotIn("#monetization-and-partner-channels", setup_line)
        self.assertNotIn("Managed PLAN/RUN, deployment", table)

    def test_owner_links_resolve_from_each_owner_file(self) -> None:
        for path in GOVERNANCE.glob("*.md"):
            text = self.read(path)
            links = [
                match.group(1)
                for match in re.finditer(r"\]\(([^)#]+)(?:#[^)]*)?\)", text)
                if not match.group(1).startswith(("http://", "https://"))
            ]
            for relative_target in links:
                with self.subTest(owner=path.name, target=relative_target):
                    resolved = (path.parent / relative_target).resolve()
                    self.assertTrue(resolved.exists(), relative_target)
                    self.assertTrue(resolved.is_relative_to(SKILLS_ROOT), relative_target)

    def test_source_owner_references_distinguish_links_from_root_commands(self) -> None:
        source = self.read(GOVERNANCE / "source-maintenance.md")
        commands = source.split("```text", 1)[1].split("```", 1)[0]
        for command in (
            "python skills/delivery-harness/scripts/check_skill_spec.py\n",
            "python skills/delivery-harness/scripts/docs_weight.py\n",
            "git diff --check\n",
        ):
            with self.subTest(repository_root_command=command.strip()):
                self.assertIn(command, commands)
        development = self.read(GOVERNANCE / "development-rules.md")
        source_principles = development.split(
            "## Source Core Development Principles", 1
        )[1].split("\n## ", 1)[0]
        self.assertIn("[pre-delivery-self-review](../pre-delivery-self-review.md)", source_principles)
        self.assertIn("[bounded-enhancement](../bounded-enhancement.md)", source_principles)
        self.assertNotIn("`../pre-delivery-self-review.md`", source_principles)
        self.assertNotIn("`../bounded-enhancement.md`", source_principles)

    def test_missing_owner_target_and_route_are_negative_findings(self) -> None:
        missing_owner = GOVERNANCE / "does-not-exist.md"
        missing_anchor = "task-and-handoff.md#missing-rule"
        self.assertFalse(missing_owner.exists())
        path, _ = route_target(
            "delivery-harness/references/governance/does-not-exist.md#rule",
            consumer=True,
        )
        self.assertFalse(path.exists())
        with self.assertRaises(AssertionError):
            path, anchor = route_target(
                "delivery-harness/references/governance/" + missing_anchor,
                consumer=True,
            )
            headings = re.findall(r"^#{1,6} (.+)$", self.read(path), re.MULTILINE)
            self.assertIn(anchor, {anchor_slug(heading) for heading in headings})


if __name__ == "__main__":
    unittest.main()
