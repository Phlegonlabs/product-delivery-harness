"""Synthetic occurrence and shared-surface boundary regressions."""

import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import design_system_showcase as source
import showcase_runtime as runtime
import source_script_order as order
from test_script_order_static import FILLER_BODY


def script():
    return '<script>' + FILLER_BODY + '</script>'


def panel(tag='section'):
    return '<' + tag + ' data-hifi-panel="design-tokens">' + script() + '</' + tag + '>'


class OccurrenceTests(unittest.TestCase):
    def test_parent_must_be_a_section(self):
        html = '<body><main data-ui-surface="UI-001"></main>' + panel('div') + '</body>'
        tree = source.SourceTree(html)
        node = next(n for n in tree.nodes if n['tag'] == 'script')
        self.assertFalse(source.reviewer_tokens_filler(tree, node))
        _, findings = order.inventory(tree, source.surface_node(tree, 'UI-001'), 'test')
        self.assertTrue(any('no retained source parent' in f for f in findings))

    def test_identical_product_occurrence_is_not_removed(self):
        html = '<body><main data-ui-surface="UI-001">' + script() + '</main>' + panel() + '</body>'
        self.assertEqual([FILLER_BODY], source.product_scripts(html, with_controls=True))
        digest = hashlib.sha256(FILLER_BODY.encode()).hexdigest()
        self.assertIsNone(runtime.script_finding(html, digest))
        tree = source.SourceTree(html)
        slots, findings = order.inventory(tree, source.surface_node(tree, 'UI-001'), 'test')
        self.assertEqual([], findings)
        self.assertEqual(1, len(slots['slots']))

    def test_duplicate_product_occurrences_still_reject(self):
        html = '<body><main data-ui-surface="UI-001">' + script() * 2 + '</main>' + panel() + '</body>'
        self.assertEqual([FILLER_BODY] * 2, source.product_scripts(html, with_controls=True))
        digest = hashlib.sha256(FILLER_BODY.encode()).hexdigest()
        self.assertEqual('matches more than one inline product script', runtime.script_finding(html, digest))


class SharedPathTests(unittest.TestCase):
    def copies(self, attrs='', wrapper=''):
        subject = '<span class="subject" data-specimen-variant="default" data-specimen-state="default"></span>'
        body = '<div ' + wrapper + '>' + subject + '</div>'
        tree = source.SourceTree('<main data-ui-surface="UI-001" ' + attrs + '>' + body + '</main>')
        spec = {'selector': '.subject', 'variant': 'default', 'state': 'default'}
        return runtime.scoped_copies(tree, spec, 'UI-001', 'summary', ['390'])['390']

    def test_surface_itself_supplies_visibility_and_target_constraints(self):
        for attrs in ['hidden', 'data-responsive-target="768"', 'data-on="running"']:
            with self.subTest(attrs=attrs):
                self.assertEqual([], self.copies(attrs))

    def test_base_state_is_updated_before_keep_rule(self):
        attrs = 'data-first="running" data-base="running" data-keep="summary" data-bases="summary"'
        self.assertEqual(1, len(self.copies(attrs, 'data-in="summary"')))
        self.assertEqual([], self.copies(attrs, 'data-in="running"'))

    def test_empty_base_does_not_fabricate_current_state(self):
        self.assertEqual([], self.copies('data-keep="summary"', 'data-in="summary"'))

    def test_empty_constraints_fail_closed_without_exception(self):
        for wrapper in ['data-in', 'data-on', 'data-live-on']:
            with self.subTest(wrapper=wrapper):
                self.assertEqual([], self.copies(wrapper=wrapper))


if __name__ == '__main__':
    unittest.main()
