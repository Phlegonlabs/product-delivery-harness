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
                         "builds the complete matrix receipt once per candidate",
                         "only for approved scope whose bytes changed since approval",
                         "or when its UI contract version changed"):
            self.assertIn(boundary, source)

    def test_every_readme_routes_initial_review_and_scoped_work(self):
        obligations = {
            "README.md": ("headless or scoped enhancement or maintenance", "Initial UI requires design",
                          "One author self-review of the whole package", "same author checks and repairs rendered studies before owner selection",
                          "After completeness preflight, the same author self-reviews and repairs before independent review"),
            "README.zh-TW.md": ("無 UI，或限域增強或維護", "初次 UI 交付須先完成設計",
                                "作者自查整套文件一次", "原作者先檢查並修復已渲染的研究，再交 owner 選擇",
                                "完整性 preflight 後，原作者先自查及修復，再交獨立 review"),
            "README.zh-CN.md": ("无 UI，或限域增强或维护", "初次 UI 交付须先完成设计",
                                "作者自查整套文件一次", "原作者先检查并修复已渲染的研究，再交 owner 选择",
                                "完整性 preflight 后，原作者先自查及修复，再交独立 review"),
            "README.es.md": ("sin UI o mejora o mantenimiento acotado", "La entrega inicial con UI requiere diseño",
                             "Una autorrevisión del paquete completo", "mismo autor comprueba y repara los estudios renderizados antes de la selección del owner",
                             "Tras el preflight de completitud, el mismo autor revisa y repara antes de la revisión independiente"),
        }
        for name, (label, *checks) in obligations.items():
            with self.subTest(path=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn(REFERENCE, source)
                self.assertRegex(source, r'Product -->\|"' + re.escape(label) + r'"\| Harness\[')
                self.assertNotRegex(source, r'Product --> Harness\b')
                for check in checks:
                    self.assertIn(check, source)
                self.assertNotRegex(source, DEFERRED_HANDOFF_EDGE)

    def test_shortcut_guard_detects_each_language_and_destination(self):
        for label in ("approved, UI phase deferred", "核准、延後 UI", "批准、延后 UI", "UI diferida"):
            for target in ("Harness", "HARNESS", "route"):
                with self.subTest(label=label, target=target):
                    edge = f'    pgate -->|"{label}"| {target}\n'
                    self.assertRegex(edge, DEFERRED_HANDOFF_EDGE)


if __name__ == "__main__":
    unittest.main()
