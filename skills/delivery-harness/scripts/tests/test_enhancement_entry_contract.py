"""Keep shared enhancement rules wired into every installed skill surface."""

import unittest
from pathlib import Path


SKILLS = Path(__file__).resolve().parents[3]
REPO = SKILLS.parent
NAMES = (
    "delivery-harness", "product-definition-builder", "ui-design-builder",
    "design-system-compiler", "code-security-review", "product-activation",
    "seo-growth-review",
)


class EnhancementEntryContractTests(unittest.TestCase):
    def test_repository_checkpoints_are_standalone_and_preserve_authority(self):
        template = (SKILLS / "delivery-harness/assets/templates/PROJECT_AGENTS.template.md").read_text(encoding="utf-8")
        section = template.split("## Repository Change Checkpoints\n", 1)[1].split("\n## ", 1)[0]
        for phrase in ("outside Product Delivery Harness", "task start", "significant edit",
                       "before completion or handoff", "commits made outside Harness",
                       "baseline gap", "observed / unverified", "working-tree", "actual verification separately",
                       "fingerprint", "no-change check", "read-only or no-write task",
                       "not a background timer", "Keep `docs/DOCUMENTS.md` indexed"):
            self.assertIn(phrase, section)
        if (REPO / "AGENTS.md").exists():
            root = (REPO / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(section, root.split("## Repository Change Checkpoints\n", 1)[1].split("\n## ", 1)[0])

    def test_handoff_audit_matches_root_rule_and_preserves_generated_tasks_authority(self):
        template = (SKILLS / "delivery-harness/assets/templates/PROJECT_AGENTS.template.md").read_text(encoding="utf-8")
        seeded = template.split("## Handoff Documentation Audit\n", 1)[1].split("\n## ", 1)[0]
        root = (REPO / "AGENTS.md").read_text(encoding="utf-8")
        root_section = root.split("## Handoff Documentation Audit\n", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(seeded, root_section)
        for phrase in (
            "Before every handoff", "docs/DOCUMENTS.md", "Epic Change Log",
            "docs/goal/PLAN.md` and `RUN.md", "renderer's `--check`",
            "RUN is authoritative", "Do not hand-edit the generated part of `docs/tasks.md`",
            "observed installed", "delivery-harness/assets/templates/PROJECT_AGENTS.template.md`",
            "delivery-harness/VERSION",
            "current`, `stale` or `unknown`", "update only stale shared instructions in place",
            "A read-only handoff reports proposed updates", "not a timer",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, seeded)

    def test_every_entry_routes_to_shared_sync_and_bounded_policy(self):
        for name in NAMES:
            with self.subTest(skill=name):
                content = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("references/document-sync-contract.md", content)
                self.assertIn("references/bounded-enhancement.md", content)
                for reference in ("document-sync-contract.md", "bounded-enhancement.md"):
                    self.assertTrue((SKILLS / "delivery-harness/references" / reference).is_file())

    def test_readme_languages_explain_all_shared_contracts(self):
        if not (REPO / "README.md").exists():
            self.skipTest("source-checkout documentation only")
        markers = {
            "README.md": ("Before every handoff", "generated content is not hand-edited"),
            "README.zh-TW.md": ("每次交接前", "不能手動編輯產生區段"),
            "README.zh-CN.md": ("每次交接前", "不能手动编辑生成区段"),
            "README.es.md": ("Antes de cada handoff", "no se edita a mano el contenido generado"),
        }
        for filename, (handoff_marker, generated_view_rule) in markers.items():
            with self.subTest(readme=filename):
                content = (REPO / filename).read_text(encoding="utf-8")
                for reference in ("document-sync-contract.md", "bounded-enhancement.md", "delivery-acceptance-contract.md"):
                    self.assertIn(reference, content)
                self.assertIn(handoff_marker, content)
                self.assertIn("docs/tasks.md", content)
                self.assertIn(generated_view_rule, content)

    def test_required_failure_handoff_cannot_mint_pass(self):
        content = (SKILLS / "delivery-harness/references/bounded-enhancement.md").read_text(encoding="utf-8")
        for phrase in ("entire accepted scope passed", "Never reset the counter", "invent a human attestation", "not successful closeout", "user data", "not launched automatically"):
            self.assertIn(phrase.lower(), content.lower())

    def test_fixture_lifecycle_and_evidence_are_reachable(self):
        root = SKILLS / "delivery-harness"
        template = (root / "assets/templates/E2E_VERIFICATION.template.md").read_text(encoding="utf-8")
        self.assertIn("test-fixture-lifecycle.md", template)
        self.assertIn("delivery-acceptance-contract.md", template)
        gates = (root / "references/verification-gates.md").read_text(encoding="utf-8")
        self.assertIn("always-run final verifier", gates)
        self.assertIn("direct work runs it", gates)

    def test_current_prd_is_live_and_history_remains_reference(self):
        content = (SKILLS / "product-definition-builder/references/artifact-lifecycle.md").read_text(encoding="utf-8")
        self.assertIn("Historical PRDs may be read", content)
        self.assertIn("never archives the live PRD", content)
        self.assertNotIn("Never use `docs/product/archived/` as an input or output location", content)


if __name__ == "__main__":
    unittest.main()
