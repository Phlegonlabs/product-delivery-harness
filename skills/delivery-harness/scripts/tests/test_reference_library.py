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
    "growth-review",
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
            if name == "product-definition-builder":
                path = ROOT / "skills" / name / "references/stages/product-definition.md"
                selection_pointer = "../delivery-harness/references/reference-selection.md"
                library_pointer = "../delivery-harness/references/option-library/"
                pointer_root = ROOT / "skills/product-definition-builder"
            elif name == "ui-design-builder":
                path = ROOT / "skills" / name / "references/stages/ui-design.md"
                selection_pointer = "../delivery-harness/references/reference-selection.md"
                library_pointer = "../delivery-harness/references/option-library/"
                pointer_root = ROOT / "skills/ui-design-builder"
            elif name == "design-system-compiler":
                path = ROOT / "skills" / name / "references/stages/design-compilation.md"
                selection_pointer = "../../../delivery-harness/references/reference-selection.md"
                library_pointer = "../../../delivery-harness/references/option-library/"
                pointer_root = ROOT / "skills"
            else:
                path = ROOT / "skills" / name / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            if name == "delivery-harness":
                selection_pointer = "references/reference-selection.md"
                library_pointer = "references/option-library/"
                pointer_root = ROOT / "skills/delivery-harness/references"
            elif name not in {"product-definition-builder", "design-system-compiler"}:
                selection_pointer = "../delivery-harness/references/reference-selection.md"
                library_pointer = (
                    "../delivery-harness/references/option-library/"
                    if name != "growth-review"
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
        product = (ROOT / "skills/product-definition-builder/references/stages/product-definition.md").read_text(encoding="utf-8")
        for phrase in (
            "architecture, API, auth, frontend, backend, data, security, product runtime",
            "closed-set stack questions",
            "No provider is mandatory",
        ):
            self.assertIn(phrase, product)

        ui = (ROOT / "skills/ui-design-builder/references/stages/ui-design.md").read_text(encoding="utf-8")
        for phrase in (
            "before direction work",
            "An unresolved CSS framework, component library, icon package/dependency, or stack selection returns to `product-definition-builder` before dependent direction work",
            "Only visual and motion decisions within the approved stack belong here",
            "`frontend-design` remains mandatory",
            "Taste/GPT Taste stays optional",
            "CSS/WAAPI, Motion, GSAP and Three.js routes",
        ):
            self.assertIn(phrase, ui)

        compiler = (ROOT / "skills/design-system-compiler/references/stages/design-compilation.md").read_text(encoding="utf-8")
        self.assertIn("downstream consumption only", compiler)
        self.assertIn("never reselect a stack or direction", compiler)

        harness = SELECTION.read_text(encoding="utf-8")
        self.assertIn("product runtime, product agent runtime, and the current development runtime", harness)

        security = (ROOT / "skills/delivery-harness/references/security-review.md").read_text(encoding="utf-8")
        self.assertIn("not a second PASS standard", security)

        growth_entry = (ROOT / "skills/growth-review/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("[Workflow](references/stages/growth-review.md#workflow)", growth_entry)
        self.assertIn("only when material to a finding", growth_entry)

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

    def test_void_guidance_keeps_optional_layers_and_routing_authority(self):
        frontend = (LIBRARY / "frontend.md").read_text(encoding="utf-8")
        backend = (LIBRARY / "backend.md").read_text(encoding="utf-8")
        cloudflare = (LIBRARY / "cloudflare-platform.md").read_text(encoding="utf-8")
        frontend_selection = (
            ROOT / "skills/product-definition-builder/references/frontend-stack-selection.md"
        ).read_text(encoding="utf-8")
        backend_selection = (
            ROOT / "skills/product-definition-builder/references/backend-stack-selection.md"
        ).read_text(encoding="utf-8")

        for phrase in ("Stack Decision Checkpoint", "Framework 模式", "Better Auth"):
            self.assertIn(phrase, frontend)
        for phrase in ("optional self-hosted Void platform", "Framework mode", "approved auth"):
            self.assertIn(phrase, backend)
        self.assertIn("node_modules/void/docs/", backend)
        self.assertIn("effective instructions", backend)
        self.assertIn("不自動採用或全域連結", backend)
        self.assertIn("isolated local database and state", backend)
        self.assertIn("Remote Workers AI development calls", backend)
        self.assertIn("team Void platform", cloudflare)
        self.assertIn("Native Void mode owns routing and rendering", frontend_selection)
        self.assertIn("If the owner approves Void", backend_selection)
        self.assertNotIn("Void is an approved full-stack", backend_selection)

    def test_void_sources_record_dated_official_scope(self):
        sources = (LIBRARY / "sources.md").read_text(encoding="utf-8")
        self.assertIn("2026-10-16 Void", sources)
        for url in (
            "https://void.cloud/guide/quickstart",
            "https://void.cloud/integrations/agents",
            "https://void.cloud/integrations/frameworks/overview",
            "https://void.cloud/reference/cli/setup",
            "https://void.cloud/reference/cli/deploy",
            "https://void.cloud/integrations/cloudflare",
            "https://void.cloud/guide/deployment",
            "https://void.cloud/reference/structure",
        ):
            self.assertIn(url, sources)

    def test_void_cloudflare_deployment_keeps_side_effect_and_isolation_guards(self):
        contract = (
            ROOT / "skills/delivery-harness/references/deployment-contract.md"
        ).read_text(encoding="utf-8")
        template = (
            ROOT / "skills/delivery-harness/assets/templates/DEPLOYMENT.template.md"
        ).read_text(encoding="utf-8")
        deployment_catalog = (LIBRARY / "deployment.md").read_text(encoding="utf-8")
        for phrase in (
            "`void deploy --platform cloudflare`",
            "adds no stage, gate, schema or agent role",
            "Commit those files",
            "generated `.void/` types/local state and `.void-wrangler.jsonc`",
            "preserving required `.void/` recovery files on disk",
            "supports neither named environments nor `--project`",
            "is not proof of no side effects",
            "may send traffic before checks",
            "workers do not deploy independently",
            "Code rollback does not reverse DB migrations",
            "Never equate a production Worker's Version URL with an isolated Preview",
        ):
            self.assertIn(phrase, contract)
        self.assertIn("<delivery-harness-skill-root>/references/deployment-contract.md", template)
        self.assertIn("logical `delivery-harness/references/deployment-contract.md`", deployment_catalog)
        self.assertIn("observed installed skill root", deployment_catalog)

    def test_void_preview_routes_before_generic_wrangler_commands(self):
        template = (
            ROOT / "skills/delivery-harness/assets/templates/DEPLOYMENT.template.md"
        ).read_text(encoding="utf-8")
        contract = (
            ROOT / "skills/delivery-harness/references/deployment-contract.md"
        ).read_text(encoding="utf-8")
        void_route = template.split("#### Void direct Cloudflare\n", 1)[1].split(
            "#### Wrangler Workers", 1
        )[0]
        for phrase in (
            "Do not inherit the Wrangler procedure or CI checklist commands",
            "separate config root and `void.lock.json` mapping",
            "approved isolated development Worker alternative",
            "project-local `void deploy --platform cloudflare`",
            "Worker apps cannot use `--skip-build`",
            "candidate SHA, resources, and smoke result",
            "Native Preview remains blocked",
        ):
            self.assertIn(phrase, void_route)
        self.assertNotIn("wrangler preview", void_route)
        self.assertNotIn("--env development", void_route)
        self.assertNotIn("--project", void_route)
        self.assertNotIn("env.production", void_route)
        wrangler_route = template.split("#### Wrangler Workers", 1)[1].split(
            "### vercel, aws, generic", 1
        )[0]
        self.assertIn("env.production", wrangler_route)
        self.assertIn("On other Workers", template)
        self.assertIn("For the Wrangler route, create", template)
        self.assertIn("Generated config alone is insufficient", contract)
        self.assertIn("Do not substitute raw `wrangler preview`", contract)


if __name__ == "__main__":
    unittest.main()
