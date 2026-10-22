"""Keep the documented author-review handoff connected across skills."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[4]
REFERENCE = "pre-delivery-self-review.md"
DEFERRED_HANDOFF_EDGE = (
    r'(?im)^.*-->\|[^\n|]*(?:deferred|延後\s*UI|延后\s*UI|UI\s+diferida)'
    r'[^\n|]*\|\s*(?:Harness|HARNESS|route)\b'
)


class PreDeliverySelfReviewTests(unittest.TestCase):
    def test_all_stage_owners_link_the_shared_contract(self):
        for relative in (
            "skills/product-definition-builder/references/stages/product-definition.md",
            "skills/ui-design-builder/references/stages/ui-design.md",
            "skills/delivery-harness/SKILL.md",
            "skills/delivery-harness/references/installed-commands.md",
        ):
            with self.subTest(path=relative):
                self.assertIn(REFERENCE, (ROOT / relative).read_text(encoding="utf-8"))

        template = (ROOT / "skills/delivery-harness/assets/templates/PROJECT_AGENTS.template.md").read_text(encoding="utf-8")
        self.assertIn(
            "| Implementation or repair | `delivery-harness/references/governance/development-rules.md#keep-changes-simple` "
            "and `delivery-harness/references/governance/development-rules.md#consumer-core-development-principles` |",
            template,
        )

        owner = (ROOT / "skills/delivery-harness/references/governance/development-rules.md").read_text(encoding="utf-8")
        section_start = owner.index("## Consumer Core Development Principles")
        section_end = owner.find("\n## ", section_start + 1)
        consumer_section = owner[section_start:section_end if section_end != -1 else None]
        self.assertIn("`delivery-harness/references/pre-delivery-self-review.md`", consumer_section)

    def test_contract_preserves_review_order_and_evidence_boundaries(self):
        source = (ROOT / "skills/delivery-harness/references" / REFERENCE).read_text(encoding="utf-8")
        sections = ["## PRD Self-Review", "## UI Structure And Direction Self-Review",
                    "## HiFi Self-Review", "## Harness Entry"]
        offsets = [source.index(section) for section in sections]
        self.assertEqual(offsets, sorted(offsets))
        for boundary in ("present-day catch-up", "never claim the review happened before",
                         "A closed approval alone never exempts", "390, 768, 1024 and 1440",
                         "not a fifth authored target", "parent semantic handoff check",
                         "A repair self-check covers the ledger rows, changed sources, direct consumers",
                         "it does not rerun the complete matrix",
                         "builds the complete matrix receipt once per candidate"):
            self.assertIn(boundary, source)

    def test_every_readme_routes_initial_review_and_scoped_work(self):
        labels = {
            "README.md": "scoped enhancement or maintenance",
            "README.zh-TW.md": "限域增強或維護",
            "README.zh-CN.md": "限域增强或维护",
            "README.es.md": "mejora o mantenimiento acotado",
        }
        for name, label in labels.items():
            with self.subTest(path=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn(REFERENCE, source)
                self.assertIn('productself[', source)
                self.assertIn('directionself[', source)
                self.assertIn('hifiself[', source)
                for start, target in (("ProductGate", "Harness"), ("pgate", "route")):
                    self.assertRegex(
                        source,
                        start + r' -->\|"[^"\n]*' + re.escape(label)
                        + r'[^"\n]*"\| ' + target + r'\n',
                    )
                self.assertNotRegex(source, DEFERRED_HANDOFF_EDGE)

    def test_shortcut_guard_detects_each_language_and_destination(self):
        for label in ("approved, UI phase deferred", "核准、延後 UI", "批准、延后 UI", "UI diferida"):
            for target in ("Harness", "HARNESS", "route"):
                with self.subTest(label=label, target=target):
                    edge = f'    pgate -->|"{label}"| {target}\n'
                    self.assertRegex(edge, DEFERRED_HANDOFF_EDGE)


if __name__ == "__main__":
    unittest.main()
