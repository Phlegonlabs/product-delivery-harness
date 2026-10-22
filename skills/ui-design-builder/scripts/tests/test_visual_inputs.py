"""Visual handoff assembly uses synthetic sources, not product acceptance proof."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from visual_inputs import build_visual_inputs


class VisualInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prd = self.write("docs/product/PRD.md", "# Product\n")
        self.architecture = self.write("docs/product/architecture.md", "# Architecture\n")
        self.stack = self.write("docs/product/stack-decisions.md", "# Stack\n")
        self.screen = self.write("docs/design/directions/selected.png", b"synthetic selected capture")
        self.other = self.write("docs/design/directions/rejected.png", b"synthetic rejected capture")
        self.child = self.write("docs/design/ui-references/run/child.html", "<h1>Details</h1>")
        manifest = {"schema": "ui-hifi/2", "surfaces": [], "interactions": [],
                    "pages": [{"path": "child.html", "sha256": self.digest(self.child)}]}
        self.hifi = self.write("docs/design/ui-references/run/index.html",
                               '<script id="ui-hifi-manifest" type="application/json">'
                               + json.dumps(manifest) + '</script><style>@font-face{font-family:Brand;src:url(data:font/woff2;base64,AA==)}</style>')
        self.ui = "docs/design/ui-design.md"

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return relative

    def digest(self, relative):
        return hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

    def binding(self, relative):
        return relative + " @ sha256:" + self.digest(relative)

    def contract(self, *, selected="VD-R1-01 editorial", target=False, hifi=False):
        scope = ('; scope=surfaces=[{"id":"UI-001","route":"/","states":["ready"],'
                 '"stackSemantics":{"platform":"web","renderingModel":"SPA",'
                 '"componentFoundation":"shadcn/ui owned source","stylingMechanism":"Tailwind CSS"}}]'
                 '|routes=["/"]|states=["ready"]'
                 '|responsive={"kind":"viewports","targets":[390,768,1200]}'
                 '|tolerance="exact"|allowedDeviations=[]|captureMode=hosted-browser')
        text = f"""# UI Design Contract
UI contract: ui-design/2

## Source Product Definition
PRD source: {self.binding(self.prd)}
Architecture source: {self.binding(self.architecture)}
Stack source: {self.binding(self.stack)}

## UI Design Intake
Direction mode: three comparable directions
### Design Brief
Reference lessons: editorial composition; avoid repeated cards.

## Motion And Media Intent
Motion direction: functional_only

## Style Integration
Selected direction: {selected}
Candidate theme: Brand font, editorial heading contrast, warm ink.
Connected HiFi reference: {self.binding(self.hifi) if hifi else 'pending'}
### Direction comparison
| Direction | UI surface | State | Target | Scenario | Content basis | Screenshot | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VD-R1-01 | UI-001 | ready | 390 | primary | Approved copy | {self.binding(self.screen)} | Editorial hierarchy |
| VD-R1-02 | UI-001 | ready | 390 | primary | Approved copy | {self.binding(self.other)} | Rejected cards |

## Visual Approval
Approved target: {self.binding(self.hifi) + scope if target else 'pending'}

## Design System Need Gate
Decision: not_required
"""
        self.write(self.ui, text)
        return text

    def test_direction_exploration_allows_selection_and_target_pending(self):
        self.contract(selected="pending")
        packet = build_visual_inputs(self.root, self.ui, "direction")
        self.assertIn("- Selected direction: pending", packet)
        self.assertIn(self.binding(self.prd), packet)
        self.assertIn(self.binding(self.screen), packet)
        self.assertIn(self.binding(self.other), packet)

    def test_hifi_handoff_selects_owner_direction_without_final_target(self):
        self.contract()
        packet = build_visual_inputs(self.root, self.ui, "hifi")
        self.assertIn(self.binding(self.screen), packet)
        self.assertNotIn(self.other, packet)
        self.assertIn("- Approved target: pending", packet)

    def test_implementation_retains_selected_capture_and_complete_hifi(self):
        self.contract(target=True, hifi=True)
        packet = build_visual_inputs(self.root, self.ui, "implementation")
        self.assertIn(self.binding(self.screen), packet)
        self.assertNotIn(self.other, packet)
        self.assertIn(self.binding(self.hifi), packet)
        self.assertIn(self.binding(self.child), packet)
        self.assertIn('"targets": [390, 768, 1200]', packet)
        self.assertIn("- Fonts:", packet)
        self.assertIn("- Assets:", packet)
        self.assertIn("- Visual features:", packet)
        self.assertEqual(packet, build_visual_inputs(self.root, self.ui, "implementation"))

    def test_missing_selection_or_target_blocks_dependent_stage(self):
        self.contract(selected="pending")
        with self.assertRaisesRegex(ValueError, "selected direction"):
            build_visual_inputs(self.root, self.ui, "hifi")
        self.contract()
        with self.assertRaisesRegex(ValueError, "approved target"):
            build_visual_inputs(self.root, self.ui, "implementation")

    def test_required_pair_and_preview_are_transferred_without_redefining_values(self):
        markdown = self.write("docs/design/design-system.md", "# Approved system\n")
        registry = self.write("docs/design/design-system.json", '{"schema":"design-system/4"}')
        preview = self.write("docs/design/design-system-preview.html", "<h1>Derived preview</h1>")
        text = self.contract(target=True, hifi=True).replace("UI contract: ui-design/2", "UI contract: ui-design/3").replace(
            "Decision: not_required", "Decision: required\nCompiled design system pair: "
            + self.binding(markdown) + " and " + self.binding(registry) + "\nPackage action: compile")
        self.write(self.ui, text)
        packet = build_visual_inputs(self.root, self.ui, "implementation")
        for source in (markdown, registry, preview):
            self.assertIn(self.binding(source), packet)
        (self.root / preview).rename(self.root / "preserved-preview.html")
        with self.assertRaisesRegex(ValueError, "missing"):
            build_visual_inputs(self.root, self.ui, "implementation")

    def test_missing_or_malformed_visual_material_is_blocked(self):
        self.contract(target=True, hifi=True)
        (self.root / self.screen).rename(self.root / "preserved-capture.png")
        with self.assertRaisesRegex(ValueError, "missing"):
            build_visual_inputs(self.root, self.ui, "implementation")
        (self.root / "preserved-capture.png").rename(self.root / self.screen)
        self.write(self.hifi, '<script id="ui-hifi-manifest" type="application/json">[]</script>')
        self.contract(target=True, hifi=True)
        with self.assertRaisesRegex(ValueError, "ui-hifi/2"):
            build_visual_inputs(self.root, self.ui, "implementation")

    def test_stale_prd_capture_and_child_are_rejected(self):
        for source in (self.prd, self.screen, self.child):
            with self.subTest(source=source):
                self.contract(target=True, hifi=True)
                path = self.root / source
                original = path.read_bytes()
                path.write_bytes(original + b" changed")
                with self.assertRaisesRegex(ValueError, "stale"):
                    build_visual_inputs(self.root, self.ui, "implementation")
                path.write_bytes(original)

    def test_no_input_bytes_are_written_and_cli_uses_same_packet(self):
        self.contract(target=True, hifi=True)
        before = {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "visual_inputs.py"),
                                 "--repo-root", str(self.root), "--ui-design", self.ui,
                                 "--stage", "implementation"], capture_output=True, text=True,
                                encoding="utf-8", timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(build_visual_inputs(self.root, self.ui, "implementation"), result.stdout)
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.root.rglob("*") if path.is_file()})


if __name__ == "__main__":
    unittest.main()
