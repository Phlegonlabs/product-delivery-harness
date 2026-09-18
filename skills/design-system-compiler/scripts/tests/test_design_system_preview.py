"""Derived views preserve source identities and never execute registry values."""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import render_design_system_preview as preview


class DesignSystemPreviewTests(unittest.TestCase):
    def source(self):
        return json.dumps({
            "product": "Studio <script>alert(1)</script>",
            "tokens": {"color": {"ink": "#123456", "bad": "red; background:url(https://example.com)"},
                       "fontSize": {"body": "16px"}, "space": {"gap": "1rem"},
                       "radius": {"control": "4px"}, "lineHeight": {"body": "1.5"}},
            "primitives": {"Button": {"variants": ["primary", "secondary"], "minTargetPx": 44}},
            "productComponents": {}, "stateMatrix": ["ready", "empty"],
            "surfaceContracts": {"UI-002": {"surfaceClass": "native-mobile", "responsive": {"kind": "sizeClasses", "targets": ["compact", "regular"]}}},
            "sourceBindings": {"hifi": {"path": "docs/design/ui-references/demo/index.html", "sha256": "a" * 64}},
        }).encode()

    def test_deterministic_safe_view_preserves_values_and_platform_contract(self):
        source = self.source()
        output = preview.render_preview(source, b"approved rationale")
        self.assertEqual(output, preview.render_preview(source, b"approved rationale"))
        self.assertIn(hashlib.sha256(source).hexdigest(), output)
        self.assertIn("&lt;script&gt;", output)
        self.assertNotIn("<script>", output)
        self.assertNotIn('style="background:red;', output)
        self.assertIn('style="background:#123456"', output)
        self.assertIn('style="font-size:16px"', output)
        self.assertIn("native-mobile", output)
        self.assertIn("compact", output)
        self.assertIn("minTargetPx", output)
        self.assertIn("No component styles are inferred", output)

    def test_unsupported_values_are_text_only(self):
        for value in ['url(https://example.com)', '16px;display:none', '"><img src=x>', {"light": "#fff"}]:
            with self.subTest(value=value):
                self.assertEqual("Recorded value; no browser specimen", preview.specimen("fontSize", value))

    def test_flat_and_nested_token_values_remain_visible(self):
        registry = json.loads(self.source())
        registry["tokens"] = {"fontFamily": "System font", "color": {"surface": {"light": "#fff", "dark": "#000"}}}
        output = preview.render_preview(json.dumps(registry).encode(), b"rationale")
        self.assertIn("System font", output)
        self.assertIn("light", output)
        self.assertIn("#000", output)

    def test_view_check_rejects_pair_drift_and_hand_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, markdown, output = (root / name for name in ("design-system.json", "design-system.md", "preview.html"))
            registry.write_bytes(self.source())
            markdown.write_bytes(b"approved rationale")
            output.write_bytes(preview.render_preview(registry.read_bytes(), markdown.read_bytes()).encode())
            args = ["--registry", str(registry), "--markdown", str(markdown), "--repo-root", str(root), "--check", str(output)]
            with patch.object(preview, "compare", return_value=[]) as check, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(0, preview.main(args))
                self.assertTrue(check.call_args.kwargs["require_filled"])
                self.assertEqual(root, check.call_args.kwargs["repo_root"])
                output.write_bytes(output.read_bytes() + b"edited")
                self.assertEqual(1, preview.main(args))
                output.write_bytes(preview.render_preview(registry.read_bytes(), markdown.read_bytes()).encode())
                markdown.write_bytes(b"changed rationale")
                self.assertEqual(1, preview.main(args))
                with patch.object(preview, "compare", return_value=["stale source hash"]):
                    self.assertEqual(1, preview.main(args))

    def test_invalid_pair_never_emits_html(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry, markdown = root / "design-system.json", root / "design-system.md"
            registry.write_text('{"schema":"design-system/2"}', encoding="utf-8")
            markdown.write_text("not an approved pair", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(1, preview.main(["--registry", str(registry), "--markdown", str(markdown), "--repo-root", str(root)]))
            self.assertEqual("", output.getvalue())


if __name__ == "__main__":
    unittest.main()
