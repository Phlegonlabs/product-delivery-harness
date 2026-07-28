import json
import tempfile
import unittest
from pathlib import Path

import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import check_design_system_pair as checker  # noqa: E402


def registry(**overrides: object) -> dict:
    base = {
        "schema": "design-system/1",
        "tokens": {
            "color": {"surface": "#ffffff", "text": "#101010"},
            "space": {"4": "16px"},
        },
        "primitives": {
            "Stack": {"dsId": "DS-LAY-001", "layer": "layout", "gap": ["2", "4"]},
        },
        "productComponents": {"OrderCard": {"dsId": "DS-COMP-001", "composes": ["Stack"]}},
        "motionVariants": ["fade-in"],
        "stateMatrix": ["ready", "loading"],
    }
    base.update(overrides)
    return base


MATCHING_MARKDOWN = """
# Design System

## Tokens

| Token | Value |
| --- | --- |
| `color.surface` | #ffffff |
| `color.text` | #101010 |
| `space.4` | 16px |

## Primitives

### Stack
Variants: `gap` accepts `2` and `4`.

## Product Components

### OrderCard
Composes `Stack`.

## Motion

| Variant | Purpose |
| --- | --- |
| `fade-in` | Entry |

## State Matrix

| State | Required |
| --- | --- |
| `ready` | Yes |
| `loading` | Yes |
"""


class CheckDesignSystemPairTests(unittest.TestCase):
    def run_pair(self, markdown: str, data: dict) -> tuple[int, list[str]]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            md = root / "design-system.md"
            js = root / "design-system.json"
            md.write_text(markdown, encoding="utf-8")
            js.write_text(json.dumps(data), encoding="utf-8")
            problems = checker.compare(markdown, data)
            code = checker.main(["--markdown", str(md), "--registry", str(js)])
        return code, problems

    def test_matching_pair_passes(self) -> None:
        code, problems = self.run_pair(MATCHING_MARKDOWN, registry())

        self.assertEqual([], problems)
        self.assertEqual(0, code)

    def test_token_only_in_json_fails(self) -> None:
        data = registry()
        data["tokens"]["radius"] = {"sm": "4px"}

        code, problems = self.run_pair(MATCHING_MARKDOWN, data)

        self.assertEqual(1, code)
        self.assertTrue(any("radius.sm" in problem for problem in problems))

    def test_variant_only_in_json_fails(self) -> None:
        data = registry()
        data["primitives"]["Stack"]["gap"] = ["2", "4", "8"]

        code, problems = self.run_pair(MATCHING_MARKDOWN, data)

        self.assertEqual(1, code)
        self.assertTrue(any("gap=8" in problem for problem in problems))

    def test_product_component_only_in_json_fails(self) -> None:
        data = registry()
        data["productComponents"]["InvoiceRow"] = {"dsId": "DS-COMP-002"}

        code, problems = self.run_pair(MATCHING_MARKDOWN, data)

        self.assertEqual(1, code)
        self.assertTrue(any("InvoiceRow" in problem for problem in problems))

    def test_state_only_in_json_fails(self) -> None:
        data = registry()
        data["stateMatrix"] = ["ready", "loading", "empty"]

        code, problems = self.run_pair(MATCHING_MARKDOWN, data)

        self.assertEqual(1, code)
        self.assertTrue(any("'empty'" in problem for problem in problems))

    def test_primitive_only_in_markdown_fails(self) -> None:
        markdown = MATCHING_MARKDOWN + "\n## Primitives\n\n### Callout\nA page-local surface.\n"

        code, problems = self.run_pair(markdown, registry())

        self.assertEqual(1, code)
        self.assertTrue(any("Callout" in problem for problem in problems))

    def test_placeholder_names_in_the_template_are_ignored(self) -> None:
        data = registry()
        data["productComponents"] = {"<DomainComponentName>": {"dsId": "DS-COMP-001"}}
        data["motionVariants"] = ["<variant name>"]

        _, problems = self.run_pair(MATCHING_MARKDOWN, data)

        self.assertEqual([], [p for p in problems if "<" in p])

    def test_invalid_json_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            md = root / "design-system.md"
            js = root / "design-system.json"
            md.write_text(MATCHING_MARKDOWN, encoding="utf-8")
            js.write_text("{not json", encoding="utf-8")

            code = checker.main(["--markdown", str(md), "--registry", str(js)])

        self.assertEqual(2, code)

    def test_missing_file_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            md = root / "design-system.md"
            md.write_text(MATCHING_MARKDOWN, encoding="utf-8")

            code = checker.main(
                ["--markdown", str(md), "--registry", str(root / "absent.json")]
            )

        self.assertEqual(2, code)


if __name__ == "__main__":
    unittest.main()
