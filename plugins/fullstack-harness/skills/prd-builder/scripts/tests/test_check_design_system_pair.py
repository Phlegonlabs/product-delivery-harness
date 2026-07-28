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
        "platform": "web",
        "stylingMechanism": "plain CSS",
        "enforcement": "blocking",
        "tokenSources": ["src/styles/tokens.css"],
        "primitiveSources": ["src/ui/primitives.css"],
        "viewports": [390, 768, 1200],
        "tokens": {
            "color": {"surface": "#ffffff", "text": "#101010"},
            "space": {"4": "16px"},
        },
        "primitives": {
            "Stack": {"dsId": "DS-LAY-001", "layer": "layout", "gap": ["2", "4"]},
        },
        "productComponents": {
            "OrderCard": {
                "dsId": "DS-COMP-001",
                "requiredContentOrder": ["title", "price"],
                "composes": ["Stack"],
                "states": ["ready", "loading"],
            }
        },
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
""" + checker.generated_contract_block(registry())

REAL_TABLE_SHAPE_WITH_STALE_GENERATED_CONTRACT = """
# Design System

## Tokens

| Token | Value |
| --- | --- |
| `color.surface` | #ffffff |
| `color.text` | #101010 |
| `space.4` | 16px |

## Primitive Inventory

| DS ID | Primitive | Layer | Closed variant sets |
| --- | --- | --- | --- |
| DS-CTL-999 | GhostButton | control | gap: 2, 4 |

The prior inventory used Stack with gap values 2 and 4.

### Product Components

| DS ID | Component | Composes | Required content order | States |
| --- | --- | --- | --- | --- |
| DS-COMP-999 | InvoiceRow | GhostButton | price, title | ready, error |

The prior inventory used OrderCard.

## Motion

| Variant | Purpose |
| --- | --- |
| `fade-in` | Entry |

## State Matrix

| State | Required |
| --- | --- |
| `ready` | Yes |
| `loading` | Yes |

<!-- BEGIN GENERATED DESIGN SYSTEM CONTRACT -->
```json
{
  "motionVariants": [
    "fade-in"
  ],
  "primitives": {
    "GhostButton": {
      "gap": [
        "2",
        "4"
      ],
      "layer": "control"
    }
  },
  "productComponents": {
    "InvoiceRow": {
      "composes": [
        "GhostButton"
      ],
      "dsId": "DS-COMP-999",
      "requiredContentOrder": [
        "price",
        "title"
      ],
      "states": [
        "ready",
        "error"
      ]
    },
    "OrderCard": {
      "composes": [
        "GhostButton"
      ],
      "dsId": "DS-COMP-001",
      "requiredContentOrder": [
        "price",
        "title"
      ],
      "states": [
        "ready",
        "error"
      ]
    }
  },
  "stateMatrix": [
    "ready",
    "loading"
  ],
  "tokens": {
    "color": {
      "surface": "#ffffff",
      "text": "#101010"
    },
    "space": {
      "4": "16px"
    }
  }
}
```
<!-- END GENERATED DESIGN SYSTEM CONTRACT -->
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

    def test_empty_primitive_sources_passes_before_primitive_files_exist(self) -> None:
        data = registry(primitiveSources=[])
        markdown = checker.replace_generated_contract(MATCHING_MARKDOWN, data)

        code, problems = self.run_pair(markdown, data)

        self.assertEqual([], problems)
        self.assertEqual(0, code)

    def test_invalid_responsive_sets_and_platform_mismatches_fail(self) -> None:
        cases = (
            registry(viewports=["mobile", "mobile"]),
            registry(viewports=[390, 390]),
            registry(viewports=[-1, float("inf")]),
            registry(platform="ios"),
            registry(platform="web", viewports=None, sizeClasses=["compact"]),
            registry(
                platform="ios",
                viewports=None,
                sizeClasses=["compact", "compact"],
            ),
        )
        for data in cases:
            data = {key: value for key, value in data.items() if value is not None}
            markdown = checker.replace_generated_contract(MATCHING_MARKDOWN, data)
            with self.subTest(data=data):
                code, problems = self.run_pair(markdown, data)
                self.assertEqual(1, code)
                self.assertTrue(
                    any(
                        "responsive set" in problem
                        or "require platform" in problem
                        or "platform 'web'" in problem
                        for problem in problems
                    ),
                    problems,
                )

    def test_token_only_in_json_fails(self) -> None:
        data = registry()
        data["tokens"]["radius"] = {"sm": "4px"}

        code, problems = self.run_pair(MATCHING_MARKDOWN, data)

        self.assertEqual(1, code)
        self.assertTrue(any("tokens.radius" in problem for problem in problems))

    def test_variant_only_in_json_fails(self) -> None:
        data = registry()
        data["primitives"]["Stack"]["gap"] = ["2", "4", "8"]

        code, problems = self.run_pair(MATCHING_MARKDOWN, data)

        self.assertEqual(1, code)
        self.assertTrue(
            any("primitives.Stack.gap" in problem and '"8"' in problem for problem in problems)
        )

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
        self.assertTrue(any('"empty"' in problem for problem in problems))

    def test_prose_heading_does_not_create_a_second_structured_authority(self) -> None:
        markdown = MATCHING_MARKDOWN + "\n## Primitives\n\n### Callout\nA page-local surface.\n"

        code, problems = self.run_pair(markdown, registry())

        self.assertEqual(0, code)
        self.assertEqual([], problems)

    def test_real_table_shape_detects_every_structured_contract_mismatch(self) -> None:
        data = registry()
        data["productComponents"]["OrderCard"].update(
            {
                "requiredContentOrder": ["title", "price"],
                "states": ["ready", "loading"],
            }
        )

        problems = checker.compare(
            REAL_TABLE_SHAPE_WITH_STALE_GENERATED_CONTRACT,
            data,
        )

        for expected in (
            "GhostButton",
            "InvoiceRow",
            "requiredContentOrder",
            "composes",
            "states",
        ):
            with self.subTest(expected=expected):
                self.assertTrue(
                    any(expected in problem for problem in problems),
                    problems,
                )

    def test_placeholder_names_in_the_template_are_ignored(self) -> None:
        data = registry()
        data["productComponents"] = {
            "<DomainComponentName>": {
                "dsId": "DS-COMP-001",
                "requiredContentOrder": ["<field>"],
                "composes": ["<primitive>"],
                "states": ["<state>"],
            }
        }
        data["motionVariants"] = ["<variant name>"]
        markdown = checker.replace_generated_contract(MATCHING_MARKDOWN, data)

        code, problems = self.run_pair(markdown, data)

        self.assertEqual(0, code)
        self.assertEqual([], problems)

    def test_write_mode_generates_the_contract_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            md = root / "design-system.md"
            js = root / "design-system.json"
            md.write_text("# Design System\n\nHuman rationale.\n", encoding="utf-8")
            js.write_text(json.dumps(registry()), encoding="utf-8")

            code = checker.main(
                [
                    "--markdown",
                    str(md),
                    "--registry",
                    str(js),
                    "--write",
                ]
            )

            self.assertEqual(0, code)
            rendered = md.read_text(encoding="utf-8")
            self.assertIn(checker.BEGIN_MARKER, rendered)
            self.assertIn('"requiredContentOrder"', rendered)

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
