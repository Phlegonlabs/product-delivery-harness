"""Source diagnostics are advisory; current UI evidence gates stay intact."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_ui_design_v3 import checker, digest, v3_publication
from test_wireframe_free_publication import current_publication


class CompilerSourcePreflightTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def validate(self, ui, prd, hifi, diagnostics):
        return checker.validate(ui, repo_root=self.root, prd_path=prd, hifi_path=hifi,
                                require_hifi_preflight=True, compiler_diagnostics=diagnostics)

    def add_unresolved_css(self, ui, hifi, *, refresh=True):
        before = digest(hifi)
        hifi.write_text(hifi.read_text(encoding='utf-8').replace(
            '</head>', '<style>@layer motion{.product-button{animation:missing 1s}}</style></head>', 1), encoding='utf-8')
        if refresh:
            ui.write_text(ui.read_text(encoding='utf-8').replace(before, digest(hifi)), encoding='utf-8')

    def test_v3_advisory_does_not_create_a_new_gate_or_registry(self):
        ui, prd, hifi = v3_publication(self.root)
        self.add_unresolved_css(ui, hifi)
        diagnostics = []
        self.assertEqual([], self.validate(ui, prd, hifi, diagnostics))
        self.assertTrue(any('WARN compiler-source:' in item for item in diagnostics))
        self.assertTrue(any('deferred to compilation' in item for item in diagnostics))
        self.assertFalse((self.root / 'docs/design/design-system.json').exists())

    def test_v2_behavior_is_unchanged(self):
        ui, prd, hifi = current_publication(self.root)
        self.add_unresolved_css(ui, hifi)
        diagnostics = []
        self.assertEqual([], self.validate(ui, prd, hifi, diagnostics))
        self.assertEqual([], diagnostics)

    def test_stale_hifi_still_fails(self):
        ui, prd, hifi = v3_publication(self.root)
        self.add_unresolved_css(ui, hifi, refresh=False)
        self.assertTrue(self.validate(ui, prd, hifi, []))

    def test_missing_helper_is_reported_without_claiming_inspection(self):
        ui, prd, hifi = v3_publication(self.root)
        diagnostics = []
        with patch.object(checker, '_compiler_source_preflight', None):
            self.assertEqual([], self.validate(ui, prd, hifi, diagnostics))
        self.assertTrue(any('source inspection was not performed' in item for item in diagnostics))

    def test_diagnostics_survive_caller_path_restoration(self):
        ui, prd, hifi = v3_publication(self.root)
        self.add_unresolved_css(ui, hifi)
        diagnostics = []
        with patch.object(sys, 'path', [item for item in sys.path if 'design-system-compiler' not in item]):
            self.assertEqual([], self.validate(ui, prd, hifi, diagnostics))
        self.assertTrue(any('static animation provenance' in item for item in diagnostics))

    def test_fresh_cli_reports_requested_gate_and_deferred_compilation(self):
        ui, prd, hifi = v3_publication(self.root)
        self.add_unresolved_css(ui, hifi)
        command = [sys.executable, str(Path(checker.__file__)), '--ui-design', str(ui),
                   '--repo-root', str(self.root), '--prd', str(prd), '--hifi', str(hifi), '--require-hifi-preflight']
        result = subprocess.run(command, text=True, encoding='utf-8', capture_output=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('WARN compiler-source:', result.stdout)
        self.assertIn('deferred to compilation', result.stdout)
        self.assertIn('PASS UI design contract is complete for the requested gate', result.stdout)


if __name__ == '__main__':
    unittest.main()
