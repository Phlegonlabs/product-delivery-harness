import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LIBRARY = ROOT / "skills/delivery-harness/references/option-library"
SELECTION = ROOT / "skills/delivery-harness/references/reference-selection.md"

DOMAIN_FILES = {
    "ai-agentic.md",
    "api.md",
    "architecture.md",
    "authentication-and-identity.md",
    "backend.md",
    "cloudflare-platform.md",
    "components-icons.md",
    "css-styling.md",
    "data-storage.md",
    "deployment.md",
    "design.md",
    "frontend.md",
    "icon-systems.md",
    "integrations.md",
    "motion.md",
    "operations.md",
    "runtime-selection.md",
    "security.md",
    "testing-acceptance.md",
}

SUPPORT_FILES = {
    "scenario-guide.md",
    "reference-maintenance.md",
    "sources.md",
}

SKILL_FILES = {
    "product-definition-builder",
    "ui-design-builder",
    "design-system-compiler",
    "delivery-harness",
    "code-security-review",
    "product-activation",
    "seo-growth-review",
}


def internal_links(path):
    text = path.read_text(encoding="utf-8")
    for match in re.finditer(r"\[[^]]+\]\(([^)]+)\)", text):
        target = match.group(1)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield target.split("#", 1)[0]


class ReferenceLibraryTests(unittest.TestCase):
    def test_catalog_has_exact_domain_and_support_coverage(self):
        actual = {path.name for path in LIBRARY.glob("*.md")}
        self.assertEqual(DOMAIN_FILES, actual - {"README.md"} - SUPPORT_FILES)
        self.assertEqual(SUPPORT_FILES, actual & SUPPORT_FILES)
        self.assertIn("README.md", actual)
        self.assertEqual(23, len(actual))

    def test_index_links_all_domains_and_states_optional_boundaries(self):
        text = (LIBRARY / "README.md").read_text(encoding="utf-8")
        for name in DOMAIN_FILES:
            self.assertRegex(text, rf"\]\({re.escape(name)}\)")
        for phrase in ("Reference only", "2026-09-25", "does not select a stack", "create a gate"):
            self.assertIn(phrase, text)

    def test_internal_catalog_links_resolve_inside_library(self):
        for path in LIBRARY.glob("*.md"):
            for target in internal_links(path):
                self.assertFalse(Path(target).is_absolute(), (path, target))
                resolved = (path.parent / target).resolve()
                self.assertTrue(resolved.exists(), (path, target))
                self.assertTrue(
                    resolved.is_relative_to(LIBRARY) or resolved == SELECTION,
                    (path, target),
                )

    def test_catalog_sources_do_not_ship_draft_internals_or_machine_paths(self):
        for path in LIBRARY.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("evidence/", text, path)
            self.assertNotIn("skill-fit-proposal.md", text, path)
            self.assertNotIn("workspace-handoff", text, path)
            self.assertIsNone(re.search(r"(?<![A-Za-z])[A-Za-z]:[/\\]", text), path)

    def test_shared_rule_is_needs_first_and_not_authority(self):
        text = SELECTION.read_text(encoding="utf-8")
        for phrase in (
            "only when a real choice is unresolved",
            "Read only the relevant domain files",
            "keep a healthy existing stack",
            "No catalog name is a mandatory vendor",
            "existing stack decisions",
            "not create a new mandatory register",
            "do not retroactively reopen approvals",
            "never grant installation",
        ):
            self.assertIn(phrase, text)

    def test_each_canonical_skill_has_conditional_installed_relative_pointer(self):
        for name in SKILL_FILES:
            path = ROOT / "skills" / name / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            if name == "delivery-harness":
                selection_pointer = "references/reference-selection.md"
                library_pointer = "references/option-library/"
                pointer_root = ROOT / "skills/delivery-harness/references"
            else:
                selection_pointer = "../delivery-harness/references/reference-selection.md"
                library_pointer = (
                    "../delivery-harness/references/option-library/"
                    if name != "seo-growth-review"
                    else None
                )
                pointer_root = ROOT / "skills"
            self.assertIn(selection_pointer, text, name)
            if library_pointer:
                self.assertIn(library_pointer, text, name)
            self.assertLess(text.count(selection_pointer), 3, name)
            for target in internal_links(path):
                if target.endswith(("reference-selection.md", "option-library/")):
                    resolved = (path.parent / target).resolve()
                    self.assertTrue(resolved.is_relative_to(pointer_root), (name, target))

    def test_stage_pointers_keep_their_existing_routes_and_boundaries(self):
        product = (ROOT / "skills/product-definition-builder/SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "architecture, API, auth, frontend, backend, data, security, product runtime",
            "closed-set stack questions",
            "No provider is mandatory",
        ):
            self.assertIn(phrase, product)

        ui = (ROOT / "skills/ui-design-builder/SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "before direction work",
            "An unresolved CSS framework, component library, icon package/dependency, or stack selection returns to `product-definition-builder` before dependent direction work",
            "Only visual and motion decisions within the approved stack belong here",
            "`frontend-design` remains mandatory",
            "Taste/GPT Taste stays optional",
            "CSS/WAAPI and GSAP routes",
        ):
            self.assertIn(phrase, ui)

        compiler = (ROOT / "skills/design-system-compiler/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("downstream consumption only", compiler)
        self.assertIn("never reselect a stack or direction", compiler)

        harness = SELECTION.read_text(encoding="utf-8")
        self.assertIn("product runtime, product agent runtime, and the current development runtime", harness)

        security = (ROOT / "skills/code-security-review/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("not a second PASS standard", security)

        activation = (ROOT / "skills/product-activation/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("adopted deployment, operations, or integration choice", activation)

        seo = (ROOT / "skills/seo-growth-review/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("public, discoverable surface", seo)
        self.assertIn("existing public-surface scope", seo)

    def test_readmes_describe_the_optional_catalog_in_each_language(self):
        for name in ("README.md", "README.zh-TW.md", "README.zh-CN.md", "README.es.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("skills/delivery-harness/references/reference-selection.md", text, name)
            self.assertIn("skills/delivery-harness/references/option-library/README.md", text, name)

    def test_catalog_is_not_a_runtime_or_flow_prerequisite(self):
        selection = SELECTION.read_text(encoding="utf-8")
        for phrase in (
            "is not a stack",
            "runtime, or second delivery workflow",
            "never grant installation",
            "runtime, subagent",
        ):
            self.assertIn(phrase, selection)
        for name in SKILL_FILES:
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("must read the option-library", text, name)
            self.assertNotIn("required option-library", text, name)


if __name__ == "__main__":
    unittest.main()
