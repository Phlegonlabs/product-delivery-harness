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
    load_registry,
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
    "reviewScaffoldClasses": ["state-label"],
    "motionVariants": ["fade"],
    "viewports": [390],
    "recipes": {"home": {"sections": ["Hero"]}},
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
        return self.write("ui-registry.json", json.dumps(REGISTRY if data is None else data))

    def test_valid_registry_exposes_classes_and_containers(self) -> None:
        registry = load_registry(self.registry())

        self.assertIn("surface", registry.known_classes)
        self.assertIn("surface--raised", registry.known_classes)
        self.assertIn("gap-4", registry.known_classes)
        self.assertIn("state-label", registry.known_classes)
        self.assertIn("container", registry.container_classes)
        self.assertNotIn("stack", registry.container_classes)

    def test_missing_registry_file_is_rejected(self) -> None:
        with self.assertRaises(UiContractError):
            load_registry(self.root / "nope.json")

    def test_malformed_json_is_rejected(self) -> None:
        path = self.write("bad.json", "{not json")
        with self.assertRaises(UiContractError):
            load_registry(path)

    def test_non_object_registry_is_rejected(self) -> None:
        path = self.write("list.json", "[]")
        with self.assertRaises(UiContractError):
            load_registry(path)

    def test_primitives_must_be_an_object(self) -> None:
        path = self.registry({"primitives": []})
        with self.assertRaises(UiContractError):
            load_registry(path)

    def test_primitive_spec_must_be_an_object(self) -> None:
        path = self.registry({"primitives": {"Button": "primary"}})
        with self.assertRaises(UiContractError):
            load_registry(path)

    def test_unknown_extra_keys_are_tolerated(self) -> None:
        data = dict(REGISTRY, futureField={"anything": True})
        registry = load_registry(self.registry(data))

        self.assertIn("btn", registry.known_classes)

    def test_registry_rejects_ambiguous_responsive_sets(self) -> None:
        data = dict(REGISTRY, viewports=[390, 768], sizeClasses=["compact"])
        with self.assertRaises(UiContractError):
            load_registry(self.registry(data))

    def test_registry_rejects_invalid_viewport_values(self) -> None:
        for values in ([0, 768], [True, 768], [390, 390], [float("inf")]):
            with self.subTest(values=values):
                data = dict(REGISTRY, viewports=values)
                with self.assertRaises(UiContractError):
                    load_registry(self.registry(data))

    def test_registry_requires_one_responsive_set(self) -> None:
        data = dict(REGISTRY)
        del data["viewports"]
        with self.assertRaises(UiContractError):
            load_registry(self.registry(data))

    def test_registry_rejects_empty_or_duplicate_size_classes(self) -> None:
        for values in ([], ["compact", "compact"], ["compact", " "]):
            with self.subTest(values=values):
                data = dict(REGISTRY, sizeClasses=values)
                del data["viewports"]
                with self.assertRaises(UiContractError):
                    load_registry(self.registry(data))

    def test_registry_accepts_positive_finite_numeric_viewports(self) -> None:
        data = dict(REGISTRY, viewports=[390, 768.5])
        load_registry(self.registry(data))

    def test_registry_validates_recipe_ui_trace_binding_type(self) -> None:
        data = dict(REGISTRY)
        data["recipes"] = {
            "/home": {"uiId": ["UI-001"], "requiredStates": ["ready"]}
        }
        with self.assertRaises(UiContractError):
            load_registry(self.registry(data))

    def test_registry_rejects_blank_recipe_evidence_values(self) -> None:
        data = dict(REGISTRY)
        data["recipes"] = {
            "/home": {"uiId": " ", "requiredStates": ["ready", " "]}
        }
        with self.assertRaises(UiContractError):
            load_registry(self.registry(data))


class RuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        registry_path = self.root / "ui-registry.json"
        registry_path.write_text(json.dumps(REGISTRY), encoding="utf-8")
        self.registry = load_registry(registry_path)

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

    def test_unregistered_class_is_reported(self) -> None:
        rules = self.rules('<section class="container"><div class="fancy-card">x</div></section>')
        self.assertIn("unregistered-class", rules)

    def test_call_site_motion_value_is_reported(self) -> None:
        self.assertIn(
            "call-site-motion",
            self.rules("<style>.surface { transition: opacity 240ms; }</style>"),
        )

    def test_section_without_a_container_is_reported(self) -> None:
        self.assertIn("section-without-container", self.rules('<section class="stack">x</section>'))

    def test_container_nested_inside_the_section_satisfies_the_rule(self) -> None:
        page = '<section class="stack"><div class="container">x</div></section>'
        self.assertNotIn("section-without-container", self.rules(page))

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
        self.registry_path = self.root / "ui-registry.json"
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
        primitives = self.write("ui/primitives.css", ".btn { border: 1px solid; }")
        self.assertEqual(self.run_cli(str(primitives)), 1)
        self.assertEqual(
            self.run_cli(str(primitives), "--primitive-source", "ui/primitives.css"), 0
        )

    def test_media_query_breakpoint_literal_is_allowed(self) -> None:
        page = self.write(
            "responsive.css", "@media (min-width: 768px) { .grid { gap: var(--space-4); } }"
        )
        self.assertEqual(self.run_cli(str(page)), 0)


if __name__ == "__main__":
    unittest.main()
