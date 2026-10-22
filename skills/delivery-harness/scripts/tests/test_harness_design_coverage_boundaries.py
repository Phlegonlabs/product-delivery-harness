"""Coverage grammar, legacy compatibility and failed-capture recovery."""
from pathlib import Path
import sys
import unittest
from unittest import mock

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))
from test_harness_design_coverage import surface, complete_registry  # noqa: E402
from harness_design_coverage import validate_design_coverage  # noqa: E402
import harness_ui_evidence as evidence  # noqa: E402
import parity_capture as capture  # noqa: E402


class CoverageBoundaryTests(unittest.TestCase):
    def test_legacy_matrix_does_not_own_the_product_state_inventory(self):
        legacy = surface('UI-004', ['ready', 'extra-product-state'], 'ready', coverage=False)
        self.assertEqual([], evidence.validate_ui_surface_design_registry(
            {'ui_surfaces': [legacy]}, complete_registry(['ready'])))
        row = capture._matrix({'ui_surfaces': [legacy]}, None)[0]
        self.assertEqual({'surface_id', 'route', 'breakpoint', 'state'}, set(row))

    def test_optin_grammar_rejects_conflicting_or_unfilled_declarations(self):
        mutations = {
            'unknown-field': lambda c: c.update(skip=True),
            'unknown-entry-field': lambda c: c['conditions'][0].update(skip=True),
            'duplicate-spelling': lambda c: c['not_applicable'].append(
                {'state': ' submitting ', 'reason': 'This duplicates an existing exclusion.'}),
            'product-exclusion': lambda c: c['not_applicable'].append(
                {'state': 'ready', 'reason': 'This wrongly excludes an active product state.'}),
            'placeholder': lambda c: c['not_applicable'][0].update(reason='<write a reason>'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                item = surface('UI-004', ['ready'], 'ready')
                mutate(item['design_coverage'])
                self.assertTrue(validate_design_coverage(item, set(complete_registry()['stateMatrix'])))
        for marker in ['ready:n/a', 'ready: n/a', 'ready: N/A — excluded']:
            with self.subTest(marker=marker):
                item = surface('UI-004', [marker], 'ready')
                self.assertTrue(any('not an active product state' in e for e in validate_design_coverage(item)))

    def test_universal_condition_cannot_hide_in_product_na_markers(self):
        item = surface('UI-004', ['ready'], 'ready')
        item['states'].append('reduced-motion: n/a')
        item['design_coverage']['conditions'] = [x for x in item['design_coverage']['conditions'] if x['id'] != 'reduced-motion']
        errors = validate_design_coverage(item, set(complete_registry()['stateMatrix']))
        self.assertTrue(any('required universal condition' in e for e in errors), errors)

    def test_explicit_null_does_not_turn_off_the_optin_contract(self):
        self.assertTrue(validate_design_coverage(surface('UI-004', ['ready'], 'ready', coverage=None)))

    def test_native_media_is_restored_after_a_capture_failure(self):
        item = {'kind': 'design-condition', 'media_preference': 'reduced'}
        errors = []
        with mock.patch.object(capture, '_set_motion_preference', return_value=[]) as setter:
            with self.assertRaisesRegex(RuntimeError, 'capture failed'):
                with capture._motion_scope(['browser'], item, ('dark', False), errors, 'case') as prepared:
                    self.assertTrue(prepared)
                    raise RuntimeError('capture failed')
        self.assertEqual([mock.call(['browser'], 'dark', True), mock.call(['browser'], 'dark', False)], setter.call_args_list)
        self.assertEqual([], errors)
        with mock.patch.object(capture, '_set_motion_preference', side_effect=[[], ['denied']]):
            with capture._motion_scope(['browser'], item, ('light', False), errors, 'case'):
                pass
        self.assertTrue(any('restore' in e for e in errors))

    def test_legacy_capture_does_not_change_browser_media(self):
        with mock.patch.object(capture, '_set_motion_preference') as setter:
            with capture._motion_scope(['browser'], {}, None, [], 'legacy') as prepared:
                self.assertTrue(prepared)
            setter.assert_not_called()


if __name__ == '__main__':
    unittest.main()
