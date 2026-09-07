import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_ui_contract import (  # noqa: E402
    UiContractError,
    check_file,
    load_design_system,
    main,
)


REGISTRY = {
    "tokenSources": ["styles/tokens.css"],
    "primitives": {
        "Container": {"layer": "layout", "sizes": ["shell", "narrow"], "rawStylesAllowed": False},
        "Stack": {"layer": "layout", "gaps": ["1", "4"], "rawStylesAllowed": False},
        "Surface": {"layer": "surface", "variants": ["plain", "raised"], "rawStylesAllowed": False},
        "Button": {
            "layer": "control",
            "class": "btn",
            "variants": ["primary", "danger"],
            "sizes": ["md"],
            "minTargetPx": 44,
            "rawStylesAllowed": False,
        },
    },
    "primitiveSources": ["ui/primitives.css"],
    "motionVariants": ["fade"],
    "viewports": [390, 1200],
}


class RegistryLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def registry(self, data: dict | None = None) -> Path:
        return self.write("design-system.json", json.dumps(REGISTRY if data is None else data))

    def test_valid_design_system_exposes_its_declared_sources(self) -> None:
        design_system = load_design_system(self.registry())

        self.assertEqual(design_system.token_sources, ["styles/tokens.css"])
        self.assertEqual(design_system.primitive_sources, ["ui/primitives.css"])
        self.assertIn("Button", design_system.primitives)

    def test_primitive_without_a_layer_is_rejected(self) -> None:
        data = dict(REGISTRY)
        data["primitives"] = {"Button": {"class": "btn", "variants": ["primary"]}}
        with self.assertRaises(UiContractError):
            load_design_system(self.registry(data))

    def test_primitive_with_an_unknown_layer_is_rejected(self) -> None:
        data = dict(REGISTRY)
        data["primitives"] = {"Button": {"layer": "widget", "class": "btn"}}
        with self.assertRaises(UiContractError):
            load_design_system(self.registry(data))

    def test_primitive_with_a_blank_class_is_rejected(self) -> None:
        data = dict(REGISTRY)
        data["primitives"] = {"Button": {"layer": "control", "class": "  "}}
        with self.assertRaises(UiContractError):
            load_design_system(self.registry(data))

    def test_non_string_token_sources_are_rejected(self) -> None:
        data = dict(REGISTRY)
        data["tokenSources"] = ["styles/tokens.css", 7]
        with self.assertRaises(UiContractError):
            load_design_system(self.registry(data))

    def test_non_string_primitive_sources_are_rejected(self) -> None:
        data = dict(REGISTRY)
        data["primitiveSources"] = [None]
        with self.assertRaises(UiContractError):
            load_design_system(self.registry(data))

    def test_missing_registry_file_is_rejected(self) -> None:
        with self.assertRaises(UiContractError):
            load_design_system(self.root / "nope.json")

    def test_malformed_json_is_rejected(self) -> None:
        path = self.write("bad.json", "{not json")
        with self.assertRaises(UiContractError):
            load_design_system(path)

    def test_non_object_registry_is_rejected(self) -> None:
        path = self.write("list.json", "[]")
        with self.assertRaises(UiContractError):
            load_design_system(path)

    def test_primitives_must_be_an_object(self) -> None:
        path = self.registry({"primitives": []})
        with self.assertRaises(UiContractError):
            load_design_system(path)

    def test_primitive_spec_must_be_an_object(self) -> None:
        path = self.registry({"primitives": {"Button": "primary"}})
        with self.assertRaises(UiContractError):
            load_design_system(path)

    def test_unknown_extra_keys_are_tolerated(self) -> None:
        data = dict(REGISTRY, futureField={"anything": True})
        design_system = load_design_system(self.registry(data))

        self.assertEqual(design_system.primitives["Button"]["class"], "btn")

    def test_registry_rejects_ambiguous_responsive_sets(self) -> None:
        data = dict(REGISTRY, viewports=[390, 768], sizeClasses=["compact"])
        with self.assertRaises(UiContractError):
            load_design_system(self.registry(data))

    def test_registry_rejects_invalid_viewport_values(self) -> None:
        for values in (
            [390],
            [0, 768],
            [True, 768],
            [390, 390],
            [768, 390],
            [float("inf")],
        ):
            with self.subTest(values=values):
                data = dict(REGISTRY, viewports=values)
                with self.assertRaises(UiContractError):
                    load_design_system(self.registry(data))

    def test_registry_requires_one_responsive_set(self) -> None:
        data = dict(REGISTRY)
        del data["viewports"]
        with self.assertRaises(UiContractError):
            load_design_system(self.registry(data))

    def test_registry_rejects_empty_or_duplicate_size_classes(self) -> None:
        for values in (
            [],
            ["compact"],
            ["compact", "compact"],
            ["compact", " "],
        ):
            with self.subTest(values=values):
                data = dict(REGISTRY, sizeClasses=values)
                del data["viewports"]
                with self.assertRaises(UiContractError):
                    load_design_system(self.registry(data))

    def test_registry_accepts_positive_finite_numeric_viewports(self) -> None:
        data = dict(REGISTRY, viewports=[390, 768.5])
        load_design_system(self.registry(data))

    def test_recipes_key_is_ignored_rather_than_validated(self) -> None:
        # Page recipes are no longer part of the contract. A stale key left in
        # an older file must not fail the check or resurrect the rule.
        data = dict(REGISTRY)
        data["recipes"] = {"/home": {"uiId": ["UI-001"]}}
        self.assertIsNotNone(load_design_system(self.registry(data)))


class RuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        registry_path = self.root / "design-system.json"
        registry_path.write_text(json.dumps(REGISTRY), encoding="utf-8")
        self.registry = load_design_system(registry_path)

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def rules(self, text: str, name: str = "page.html", token_source: bool = False) -> list[str]:
        path = self.write(name, text)
        return [finding.rule for finding in check_file(path, self.registry, token_source)]

    def test_clean_page_has_no_findings(self) -> None:
        page = """
        <section class="container">
          <div class="stack gap-4">
            <div class="surface surface--raised">ok</div>
            <button class="btn btn--primary">Go</button>
          </div>
        </section>
        """
        self.assertEqual(self.rules(page), [])

    def test_raw_hex_color_on_a_page_is_reported(self) -> None:
        self.assertIn("raw-color", self.rules("<style>.surface { color: #ff0000; }</style>"))

    def test_raw_color_function_on_a_page_is_reported(self) -> None:
        self.assertIn("raw-color", self.rules("<style>.surface { color: rgb(1,2,3); }</style>"))

    def test_raw_values_in_a_token_source_are_allowed(self) -> None:
        text = ":root { --ink: #101010; --space-4: 16px; --fast: 160ms; }"
        self.assertEqual(self.rules(text, "styles/tokens.css", token_source=True), [])

    def test_raw_dimension_declaration_is_reported(self) -> None:
        self.assertIn("raw-dimension", self.rules("<style>.stack { gap: 13px; }</style>"))

    def test_token_backed_dimension_is_allowed(self) -> None:
        self.assertNotIn(
            "raw-dimension", self.rules("<style>.stack { gap: var(--space-4); }</style>")
        )

    def test_arbitrary_utility_value_is_reported(self) -> None:
        self.assertIn("raw-dimension", self.rules('<div class="stack">x</div><p class-x="mt-[13px]">'))

    def test_inline_layout_style_is_reported(self) -> None:
        self.assertIn(
            "inline-layout-style",
            self.rules('<section class="container" style="display:grid;gap:2px">x</section>'),
        )

    def test_jsx_object_inline_layout_style_is_reported(self) -> None:
        """React-family code writes inline layout as an object literal.

        .tsx/.jsx/.vue are in this checker's own extension list, so matching only
        the quoted-attribute form made the rule invisible to the codebases the
        design system mostly targets.
        """
        page = '<div style={{ display: "grid", flexDirection: "column" }}>x</div>'
        self.assertIn("inline-layout-style", self.rules(page, name="Card.tsx"))

    def test_jsx_object_without_layout_properties_is_allowed(self) -> None:
        page = '<div style={{ color: "red" }}>x</div>'
        self.assertNotIn("inline-layout-style", self.rules(page, name="Card.tsx"))

    def test_inline_non_layout_style_is_allowed(self) -> None:
        self.assertNotIn(
            "inline-layout-style",
            self.rules('<section class="container" style="text-align:center">x</section>'),
        )

    def test_page_local_control_styling_is_reported(self) -> None:
        self.assertIn(
            "page-local-control-style",
            self.rules("<style>button { border: 1px solid; }</style>"),
        )

    def test_call_site_motion_value_is_reported(self) -> None:
        self.assertIn(
            "call-site-motion",
            self.rules("<style>.surface { transition: opacity 240ms; }</style>"),
        )

    def test_a_class_outside_the_design_system_is_not_reported(self) -> None:
        # Class membership is no longer enforced: without page recipes there is
        # no closed route composition to check a class name against, and real
        # product code carries state and utility classes the system never lists.
        rules = self.rules('<section class="container"><div class="fancy-card">x</div></section>')
        self.assertEqual(rules, [])

    def test_a_section_without_a_container_is_not_reported(self) -> None:
        self.assertEqual(self.rules('<section class="stack">x</section>'), [])

    def test_comments_are_not_scanned(self) -> None:
        self.assertEqual(self.rules("<!-- color: #ff0000 -->"), [])

    def test_unreadable_file_is_rejected(self) -> None:
        with self.assertRaises(UiContractError):
            check_file(self.root / "missing.html", self.registry, False)


class MainCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.registry_path = self.root / "design-system.json"
        self.registry_path.write_text(json.dumps(REGISTRY), encoding="utf-8")

    def write(self, name: str, text: str) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_cli(self, *args: str) -> int:
        return main(["--registry", str(self.registry_path), *args])

    def test_clean_file_exits_zero(self) -> None:
        page = self.write("clean.html", '<section class="container"><p class="stack">x</p></section>')
        self.assertEqual(self.run_cli(str(page)), 0)

    def test_violation_exits_one(self) -> None:
        page = self.write("dirty.html", "<style>.stack { gap: 13px; }</style>")
        self.assertEqual(self.run_cli(str(page)), 1)

    def test_no_target_exits_two(self) -> None:
        self.assertEqual(self.run_cli(), 2)

    def test_unsupported_only_target_exits_two(self) -> None:
        notes = self.write("notes.md", "No analyzable UI source here.")
        self.assertEqual(self.run_cli(str(notes)), 2)

    def test_empty_directory_walk_exits_two(self) -> None:
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(self.run_cli("--path", str(empty)), 2)

    def test_missing_registry_exits_two(self) -> None:
        self.assertEqual(main(["--registry", str(self.root / "gone.json"), "x.html"]), 2)

    def test_directory_walk_finds_files(self) -> None:
        self.write("pages/dirty.html", "<style>.stack { gap: 13px; }</style>")
        self.assertEqual(self.run_cli("--path", str(self.root / "pages")), 1)

    def test_walk_rejects_a_non_directory(self) -> None:
        page = self.write("solo.html", "x")
        self.assertEqual(self.run_cli("--path", str(page)), 2)

    def test_rule_filter_can_pass_a_file_with_other_violations(self) -> None:
        page = self.write("dirty.html", "<style>.stack { gap: 13px; }</style>")
        self.assertEqual(self.run_cli(str(page), "--rule", "raw-color"), 0)
        self.assertEqual(self.run_cli(str(page), "--rule", "raw-dimension"), 1)

    def test_extra_token_source_relaxes_raw_values(self) -> None:
        # A raw value outside a :root block is a violation in a page file and
        # allowed once the file is declared a token source.
        tokens = self.write("theme/vars.css", ".theme-dark { --ink: #101010; }")
        self.assertEqual(self.run_cli(str(tokens)), 1)
        self.assertEqual(self.run_cli(str(tokens), "--token-source", "theme/vars.css"), 0)

    def test_root_block_is_always_a_token_region(self) -> None:
        tokens = self.write("styles/theme.css", ":root { --ink: #101010; --space-4: 16px; }")
        self.assertEqual(self.run_cli(str(tokens)), 0)

    def test_primitive_source_may_define_control_selectors(self) -> None:
        # An undeclared file defining .btn is a page-local control style; the
        # same file becomes legal once it is declared a primitive source, either
        # on the command line or in the design system's primitiveSources.
        undeclared = self.write("ui/extra-controls.css", ".btn { border: 1px solid; }")
        self.assertEqual(self.run_cli(str(undeclared)), 1)
        self.assertEqual(
            self.run_cli(str(undeclared), "--primitive-source", "ui/extra-controls.css"), 0
        )

    def test_design_system_primitive_sources_exempt_a_file_without_a_flag(self) -> None:
        declared = self.write("ui/primitives.css", ".btn { border: 1px solid; }")
        self.assertEqual(self.run_cli(str(declared)), 0)

    def test_media_query_breakpoint_literal_is_allowed(self) -> None:
        page = self.write(
            "responsive.css", "@media (min-width: 768px) { .grid { gap: var(--space-4); } }"
        )
        self.assertEqual(self.run_cli(str(page)), 0)


if __name__ == "__main__":
    unittest.main()
