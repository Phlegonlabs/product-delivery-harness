"""Keep shared rules scoped to explicitly requested skill workflows."""

import unittest
from pathlib import Path

import yaml


SKILLS = Path(__file__).resolve().parents[3]
REPO = SKILLS.parent
GOVERNANCE = SKILLS / "delivery-harness/references/governance"
NAMES = (
    "delivery-harness", "product-definition-builder", "ui-design-builder",
    "design-system-compiler", "product-activation",
    "seo-growth-review",
)


class EnhancementEntryContractTests(unittest.TestCase):
    def read_root(self) -> str:
        return (REPO / "AGENTS.md").read_text(encoding="utf-8")

    def read_template(self) -> str:
        return (SKILLS / "delivery-harness/assets/templates/PROJECT_AGENTS.template.md").read_text(encoding="utf-8")

    def owner_section(self, name: str, heading: str) -> str:
        text = (GOVERNANCE / name).read_text(encoding="utf-8")
        self.assertIn(heading, text)
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    def test_repository_checkpoints_are_opt_in_and_preserve_authority(self):
        template = self.read_template()
        root = self.read_root()
        self.assertIn(
            "delivery-harness/references/governance/task-and-handoff.md#repository-change-checkpoints",
            template,
        )
        self.assertIn(
            "skills/delivery-harness/references/governance/task-and-handoff.md#repository-change-checkpoints",
            root,
        )
        section = self.owner_section(
            "task-and-handoff.md", "## Repository Change Checkpoints"
        )
        self.assertNotIn("apply to every agent task", section)
        for phrase in ("only within an explicitly requested skill workflow", "task start", "significant edit",
                       "before completion or handoff", "commits made outside Harness",
                       "baseline gap", "observed / unverified", "working-tree", "actual verification separately",
                       "fingerprint", "no-change check", "read-only or no-write task",
                       "not a background timer", "Keep `docs/DOCUMENTS.md` indexed",
                       "one entry check with one record"):
            self.assertIn(phrase, section)
        if (REPO / "AGENTS.md").exists():
            self.assertIn("significant edit", root.lower())

    def test_all_suite_skills_disable_implicit_invocation(self):
        core = sorted(SKILLS.glob("*/SKILL.md"))
        standalone = sorted((REPO / "standalone-skills").glob("*/SKILL.md"))
        self.assertEqual(len(core), len(NAMES))
        self.assertEqual(len(standalone), 4)
        for path in core + standalone:
            with self.subTest(skill=path.parent.name):
                metadata = yaml.safe_load(
                    (path.parent / "agents/openai.yaml").read_text(encoding="utf-8")
                )
                self.assertIs(metadata["policy"]["allow_implicit_invocation"], False)
                self.assertIn(
                    "$" + path.parent.name, metadata["interface"]["default_prompt"]
                )
                content = path.read_text(encoding="utf-8")
                fields = yaml.safe_load(content.split("---", 2)[1])
                self.assertIn("explicitly requests " + fields["name"], fields["description"])
                self.assertIn("does not activate it", content)
                self.assertIn("a new top-level stage needs an explicit request", content)

    def test_seeded_instructions_do_not_activate_harness_for_ordinary_tasks(self):
        for content in (self.read_root(), self.read_template()):
            activation = content.split("## Skill Activation\n", 1)[1].split("\n## ", 1)[0]
            with self.subTest(entry=content[:50]):
                for boundary in (
                    "discussing a skill does not",
                    "existing PLAN/RUN files do not activate a workflow",
                    "For ordinary tasks",
                    "Do not run Harness routing, document sync, Epic/index updates, template audits or PLAN/RUN",
                    "Existing data protection and action authorization still apply",
                ):
                    self.assertIn(boundary, activation)
        claude = (SKILLS / "delivery-harness/assets/templates/PROJECT_CLAUDE.template.md").read_text(encoding="utf-8")
        self.assertNotIn("On each skill invocation", claude)
        self.assertIn("Only within an explicitly requested skill workflow from this suite", claude)

    def test_handoff_audit_matches_root_rule_and_preserves_generated_tasks_authority(self):
        template = self.read_template()
        root = self.read_root()
        self.assertIn(
            "delivery-harness/references/governance/task-and-handoff.md#handoff-documentation-audit",
            template,
        )
        self.assertIn(
            "skills/delivery-harness/references/governance/task-and-handoff.md#handoff-documentation-audit",
            root,
        )
        seeded = self.owner_section(
            "task-and-handoff.md", "## Handoff Documentation Audit"
        )
        for phrase in (
            "Before every handoff", "docs/DOCUMENTS.md", "Epic Change Log",
            "docs/goal/PLAN.md` and `RUN.md", "renderer's `--check`",
            "RUN is authoritative", "Do not hand-edit the generated part of `docs/tasks.md`",
            "observed installed", "delivery-harness/assets/templates/PROJECT_AGENTS.template.md`",
            "delivery-harness/VERSION",
            "current`, `stale` or `unknown`", "update only stale shared instructions in place",
            "A read-only handoff reports proposed updates", "not a timer",
            "This audit is the one exit check",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, seeded)

    def test_every_entry_routes_to_shared_sync_and_bounded_policy(self):
        checklist = self.owner_section("task-and-handoff.md", "## Project Entry And Current Work")
        for reference in ("document-sync-contract.md", "bounded-enhancement.md",
                          "delegation-contract.md", "gen-verify-correct.md", "prd-refinement.md"):
            with self.subTest(checklist=reference):
                self.assertIn(reference + ")", checklist)
        for name in NAMES:
            with self.subTest(skill=name):
                content = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(
                    "references/governance/task-and-handoff.md#project-entry-and-current-work)", content
                )
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
                self.assertIn("source hashes", content)

    def test_scoped_child_and_template_audit_boundaries_are_current(self):
        sync = (SKILLS / "delivery-harness/references/document-sync-contract.md").read_text(encoding="utf-8")
        bounded = (SKILLS / "delivery-harness/references/bounded-enhancement.md").read_text(encoding="utf-8")
        template = self.read_template()
        owner = (GOVERNANCE / "task-and-handoff.md").read_text(encoding="utf-8")

        for phrase in (
            "full global inventory at first entry",
            "omits the parent global `--baseline`",
            "never replaces the parent snapshot",
            "evaluate the inventory triggers",
            "child independently reads its complete named instruction chain",
            "verifies packet source hashes",
            "Unknown loaded identity stays unknown",
        ):
            with self.subTest(reference="document-sync", phrase=phrase):
                self.assertIn(phrase, sync)
        for phrase in (
            "A later invocation reuses it while HEAD and the instruction bytes match",
            "one Change Log row with the adopted digest in the current Epic, never a new Epic",
            "Reuse a semantic template audit",
            "recorded SHA-256 values",
            "newly applicable, missing, or changed input invalidates reuse",
            "the audit survives summary compaction",
            "as do restart",
            "Never synthesize unknown loaded identity",
        ):
            with self.subTest(reference="task-and-handoff", phrase=phrase):
                self.assertIn(phrase, owner)
        self.assertIn("semantic template audit", bounded)
        delegation = (SKILLS / "delivery-harness/references/delegation-contract.md").read_text(encoding="utf-8")
        performance = (SKILLS / "delivery-harness/references/runtime-performance.md").read_text(encoding="utf-8")
        self.assertIn("source hashes", delegation)
        self.assertIn("parent claim does not substitute", delegation)
        self.assertIn("before dispatch", performance)
        self.assertIn("never replaces that launch check", performance)
        for phrase in ("full global inventory", "semantic template audit", "unknown loaded identity stays unknown"):
            with self.subTest(reference="template", phrase=phrase):
                self.assertIn(phrase, owner)
        self.assertIn(
            "delivery-harness/references/governance/task-and-handoff.md#project-entry-and-current-work",
            template,
        )

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
