"""A native Stack filled from the Product Definition template binds styling."""

import re
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = Path(__file__).resolve().parents[3]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import check_design_system_pair as pair_checker  # noqa: E402
import check_product_package  # noqa: E402
import check_ui_design_contract as ui_checker  # noqa: E402

TEMPLATE = SKILLS_ROOT / "product-definition-builder" / "references" / "output-contract.md"
SECTION = "Mobile/Desktop Technology Decision"
SELECTIONS = {
    "target operating systems": "iOS",
    "client strategy": "Platform-native",
    "framework": "SwiftUI",
    "styling approach": "platform theme",
}
SEMANTICS = {
    "platform": "ios",
    "renderingModel": "Platform-native",
    "componentFoundation": "SwiftUI",
    "stylingMechanism": "platform theme",
}


def template_layers() -> list[str]:
    text = TEMPLATE.read_text(encoding="utf-8")
    section = re.search(rf"^## {re.escape(SECTION)}\s*$([\s\S]*?)(?=^## )", text, re.MULTILINE)
    assert section is not None
    rows = re.findall(r"^\| ([^|]+?) \| \[", section.group(1), re.MULTILINE)
    return [row for row in rows if row not in ("Layer", "BDD runner")]


def native_stack(layers: list[str]) -> str:
    rows = "\n".join(
        f"| {layer} | {SELECTIONS.get(layer.casefold(), 'fixture choice')} "
        "| Approved | Owner | Fits iOS | None |"
        for layer in layers
    )
    return (
        f"# Stack Decisions\n\n## {SECTION}\n### Recorded or Approved Stack\n"
        "| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        f"{rows}\n"
    )


def surface() -> dict:
    return {"id": "UI-001", "surfaceClass": "ios", "stackSemantics": dict(SEMANTICS)}


class NativeStackStylingTests(unittest.TestCase):
    def pair_problems(self, stack: str) -> list[str]:
        registry = {
            "platform": "ios",
            "stylingMechanism": "platform theme",
            "stackSemantics": dict(SEMANTICS),
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "stack-decisions.md"
            path.write_text(stack, encoding="utf-8")
            problems: list[str] = []
            pair_checker._validate_stack_semantics(
                registry,
                stack_path=path,
                ui_view={"target_scope": {"surfaces": [surface()]}},
                problems=problems,
            )
        return problems

    def ui_problems(self, stack: str) -> list[str]:
        problems: list[str] = []
        ui_checker._validate_stack_semantics_join(
            {"surfaces": [surface()]}, stack_text=stack, problems=problems
        )
        return problems

    def test_template_and_required_layers_include_styling_approach(self) -> None:
        layers = [layer.casefold() for layer in template_layers()]
        self.assertIn("styling approach", layers)
        self.assertEqual(
            sorted(layers),
            sorted(check_product_package.STACK_SECTION_LAYERS[SECTION]),
        )

    def test_native_stack_from_template_passes_both_checkers(self) -> None:
        stack = native_stack(template_layers())
        self.assertEqual([], self.pair_problems(stack))
        self.assertEqual([], self.ui_problems(stack))

    def test_native_stack_without_styling_row_fails_both_checkers(self) -> None:
        layers = [layer for layer in template_layers() if layer.casefold() != "styling approach"]
        stack = native_stack(layers)
        self.assertTrue(
            any("stylingMechanism has no approved Stack selection" in item for item in self.pair_problems(stack))
        )
        self.assertTrue(
            any("no executable selection for stylingMechanism" in item for item in self.ui_problems(stack))
        )


if __name__ == "__main__":
    unittest.main()
