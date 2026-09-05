import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import check_design_system_pair as checker  # noqa: E402


def registry(**overrides: object) -> dict:
    base = {
        "schema": "design-system/1",
        "product": "Fixture Product",
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
            "Stack": {"layer": "layout", "gap": ["2", "4"]},
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
    def run_pair(
        self,
        markdown: str,
        data: dict,
        *,
        require_filled: bool = False,
    ) -> tuple[int, list[str]]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            md = root / "design-system.md"
            js = root / "design-system.json"
            md.write_text(markdown, encoding="utf-8")
            js.write_text(json.dumps(data), encoding="utf-8")
            problems = checker.compare(
                markdown,
                data,
                require_filled=require_filled,
            )
            argv = ["--markdown", str(md), "--registry", str(js)]
            if require_filled:
                argv.append("--require-filled")
            code = checker.main(argv)
        return code, problems

    def test_matching_pair_passes(self) -> None:
        code, problems = self.run_pair(MATCHING_MARKDOWN, registry())

        self.assertEqual([], problems)
        self.assertEqual(0, code)

    def test_malformed_or_duplicate_ds_ids_fail(self) -> None:
        data = registry()
        data["productComponents"]["OrderCard"]["dsId"] = "comp-1"
        _, problems = self.run_pair(MATCHING_MARKDOWN, data)
        self.assertTrue(
            any("must match DS-COMP-<number>" in problem for problem in problems)
        )

        data = registry()
        data["productComponents"]["InvoiceRow"] = {
            "dsId": "DS-COMP-001",
            "requiredContentOrder": ["title"],
            "composes": ["Stack"],
            "states": ["ready"],
        }
        _, problems = self.run_pair(MATCHING_MARKDOWN, data)
        self.assertTrue(
            any("duplicates DS-COMP-001" in problem for problem in problems)
        )

    def test_markdown_naming_an_unregistered_ds_comp_fails(self) -> None:
        markdown = MATCHING_MARKDOWN.replace(
            "### OrderCard\nComposes `Stack`.",
            "### OrderCard\nComposes `Stack` and DS-COMP-777.",
        )
        _, problems = self.run_pair(markdown, registry())
        self.assertTrue(
            any(
                "DS ids missing from design-system.json" in problem
                and "DS-COMP-777" in problem
                for problem in problems
            )
        )

    def test_unregistered_signature_rule_id_fails(self) -> None:
        markdown = MATCHING_MARKDOWN.replace(
            "### OrderCard\nComposes `Stack`.",
            "### OrderCard\nComposes `Stack` per signature rule DS-999.",
        )
        _, problems = self.run_pair(markdown, registry())
        self.assertTrue(
            any(
                "DS ids missing from design-system.json" in problem
                and "DS-999" in problem
                for problem in problems
            )
        )

    def test_registered_signature_rule_id_passes(self) -> None:
        data = registry(signatureRules=["DS-010"])
        markdown = checker.replace_generated_contract(
            MATCHING_MARKDOWN.replace(
                "### OrderCard\nComposes `Stack`.",
                "### OrderCard\nComposes `Stack` per signature rule DS-010.",
            ),
            data,
        )
        code, problems = self.run_pair(markdown, data)
        self.assertEqual([], problems)
        self.assertEqual(0, code)

    def test_primitive_ds_ids_validate_and_must_be_unique(self) -> None:
        data = registry()
        data["primitives"]["Stack"]["dsId"] = "stack-1"
        _, problems = self.run_pair(MATCHING_MARKDOWN, data)
        self.assertTrue(
            any("must match DS-<family>-<number>" in problem for problem in problems)
        )

        data = registry()
        data["primitives"]["Stack"]["dsId"] = "DS-LAY-001"
        data["primitives"]["Cluster"] = dict(data["primitives"]["Stack"])
        data["primitives"]["Cluster"]["dsId"] = "DS-LAY-001"
        _, problems = self.run_pair(MATCHING_MARKDOWN, data)
        self.assertTrue(
            any("duplicates DS-LAY-001" in problem for problem in problems)
        )

        data = registry()
        data["primitives"]["Stack"]["dsId"] = "DS-LAY-001"
        markdown = checker.replace_generated_contract(MATCHING_MARKDOWN, data)
        markdown = markdown.replace(
            "### Stack\nVariants",
            "### Stack (DS-LAY-001)\nVariants",
        )
        code, problems = self.run_pair(markdown, data)
        self.assertEqual(0, code)

    def test_real_templates_match_and_product_drift_fails(self) -> None:
        template = (
            SKILL_ROOT / "assets/templates/DESIGN_SYSTEM.template.md"
        ).read_text(encoding="utf-8")
        data = json.loads(
            (
                SKILL_ROOT / "assets/templates/DESIGN_SYSTEM.template.json"
            ).read_text(encoding="utf-8")
        )
        self.assertNotIn(checker.BEGIN_MARKER, template)

        markdown = checker.replace_generated_contract(template, data)
        self.assertEqual([], checker.compare(markdown, data))
        self.assertEqual(markdown, checker.replace_generated_contract(markdown, data))

        drifted = dict(data)
        drifted["product"] = "Different Product"
        problems = checker.compare(markdown, drifted)

        self.assertTrue(
            any(
                "generated contract.product differs" in problem
                and "Different Product" in problem
                for problem in problems
            ),
            problems,
        )

    def test_missing_or_blank_json_product_fails_validation(self) -> None:
        for invalid in (None, "", "   ", 42):
            data = registry()
            if invalid is None:
                del data["product"]
            else:
                data["product"] = invalid
            markdown = checker.replace_generated_contract(MATCHING_MARKDOWN, data)

            with self.subTest(product=invalid):
                code, problems = self.run_pair(markdown, data)
                self.assertEqual(1, code)
                self.assertTrue(
                    any("product must be a non-empty string" in problem for problem in problems),
                    problems,
                )

    def test_empty_primitive_sources_passes_before_primitive_files_exist(self) -> None:
        data = registry(primitiveSources=[])
        markdown = checker.replace_generated_contract(MATCHING_MARKDOWN, data)

        code, problems = self.run_pair(markdown, data)

        self.assertEqual([], problems)
        self.assertEqual(0, code)

    def test_optional_component_and_motion_inventories_may_be_omitted(self) -> None:
        data = registry()
        del data["productComponents"]
        del data["motionVariants"]
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

    def test_unknown_component_composition_fails_validation(self) -> None:
        data = registry()
        data["productComponents"]["OrderCard"]["composes"] = ["MissingPrimitive"]
        markdown = checker.replace_generated_contract(MATCHING_MARKDOWN, data)

        code, problems = self.run_pair(markdown, data)

        self.assertEqual(1, code)
        self.assertTrue(
            any(
                "composes names 'MissingPrimitive'" in problem
                and "not a key in primitives" in problem
                for problem in problems
            ),
            problems,
        )

    def test_placeholders_are_allowed_by_default_and_rejected_when_required_filled(self) -> None:
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

        code, problems = self.run_pair(markdown, data, require_filled=True)

        self.assertEqual(1, code)
        for path in (
            "design-system.json.productComponents.<DomainComponentName>",
            "design-system.json.productComponents.<DomainComponentName>.requiredContentOrder[0]",
            "design-system.json.productComponents.<DomainComponentName>.composes[0]",
            "design-system.json.productComponents.<DomainComponentName>.states[0]",
            "design-system.json.motionVariants[0]",
        ):
            with self.subTest(path=path):
                self.assertTrue(
                    any(path in problem for problem in problems),
                    problems,
                )

    def test_write_mode_generates_the_contract_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            md = root / "design-system.md"
            js = root / "design-system.json"
            md.write_text("# Design System\n\nHuman rationale.\n", encoding="utf-8")
            data = registry(product="Jolvex")
            js.write_text(json.dumps(data), encoding="utf-8")

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
            self.assertIn("Human rationale.", rendered)
            self.assertIn('"product": "Jolvex"', rendered)
            self.assertIn('"requiredContentOrder"', rendered)
            self.assertEqual([], checker.compare(rendered, data))

    def test_write_preserves_newlines_and_second_write_is_a_byte_for_byte_noop(self) -> None:
        for newline in (b"\n", b"\r\n"):
            with self.subTest(newline=newline):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    md = root / "design-system.md"
                    js = root / "design-system.json"
                    md.write_bytes(
                        newline.join(
                            (
                                b"# Design System",
                                b"",
                                b"Human rationale.",
                                b"",
                            )
                        )
                    )
                    js.write_text(json.dumps(registry()), encoding="utf-8")
                    argv = [
                        "--markdown",
                        str(md),
                        "--registry",
                        str(js),
                        "--write",
                    ]

                    self.assertEqual(0, checker.main(argv))
                    first_bytes = md.read_bytes()
                    self.assertTrue(
                        first_bytes.startswith(
                            newline.join(
                                (
                                    b"# Design System",
                                    b"",
                                    b"Human rationale.",
                                    b"",
                                )
                            )
                        )
                    )
                    first_hash = hashlib.sha256(first_bytes).hexdigest()
                    first_mtime = md.stat().st_mtime_ns
                    if newline == b"\r\n":
                        self.assertNotIn(b"\n", first_bytes.replace(b"\r\n", b""))
                    else:
                        self.assertNotIn(b"\r\n", first_bytes)

                    self.assertEqual(0, checker.main(argv))

                    second_bytes = md.read_bytes()
                    self.assertEqual(first_bytes, second_bytes)
                    self.assertEqual(
                        first_hash,
                        hashlib.sha256(second_bytes).hexdigest(),
                    )
                    self.assertEqual(first_mtime, md.stat().st_mtime_ns)

    def test_write_rejects_duplicate_begin_marker_without_changing_markdown(self) -> None:
        generated = checker.generated_contract_block(registry())
        markdown = (
            "# Design System\n\n"
            f"{checker.BEGIN_MARKER}\n"
            "Human rationale between duplicate markers must survive.\n\n"
            f"{generated}\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            md = root / "design-system.md"
            js = root / "design-system.json"
            md.write_text(markdown, encoding="utf-8")
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

            self.assertEqual(2, code)
            self.assertEqual(markdown, md.read_text(encoding="utf-8"))

    def test_replace_and_extract_reject_inverse_and_unmatched_markers(self) -> None:
        cases = {
            "inverse": f"{checker.END_MARKER}\nHuman rationale.\n{checker.BEGIN_MARKER}",
            "begin only": f"Human rationale.\n{checker.BEGIN_MARKER}",
            "end only": f"{checker.END_MARKER}\nHuman rationale.",
            "duplicate end": (
                checker.generated_contract_block(registry())
                + f"\nHuman rationale.\n{checker.END_MARKER}"
            ),
        }
        for label, markdown in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    checker.replace_generated_contract(markdown, registry())
                problems = checker.compare(markdown, registry())
                self.assertTrue(
                    any("marker" in problem for problem in problems),
                    problems,
                )

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
