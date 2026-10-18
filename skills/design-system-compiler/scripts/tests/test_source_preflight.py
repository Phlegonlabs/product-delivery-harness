"""Early diagnostics reuse compiler provenance without claiming full coverage."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import animation_provenance as provenance
import design_system_showcase as showcase


def document(css, *, outside="", inside_style=""):
    return ('<html><head><style>' + css + '</style></head><body>' + outside
            + '<main data-ui-surface="UI-001"><button class="sample" data-specimen-variant="default" '
            + 'data-specimen-state="default" style="' + inside_style + '">Save</button></main></body></html>')


class SourcePreflightTests(unittest.TestCase):
    def test_static_and_source_backed_animation_need_no_warning(self):
        for css in ('.sample{color:red}', '.sample{animation:none}',
                    '@media(min-width:600px){.sample{--ink:red;color:var(--ink)}}',
                    '@keyframes pulse{to{opacity:0}}.sample{animation:pulse 1s}',
                    '@keyframes pulse{to{opacity:0}}:root{--motion:pulse}.sample{animation:var(--motion) 1s}',
                    '@keyframes pulse{to{opacity:0}}.sample{animation:pulse 1s}'
                    '@media(prefers-reduced-motion:reduce){.sample{animation:none}}'):
            with self.subTest(css=css):
                self.assertEqual([], showcase.source_preflight({'index.html': document(css)}))

    def test_unresolved_sources_are_page_scoped_advisories(self):
        for css in ('.sample{animation:missing 1s}',
                    '@layer motion{.sample{animation:pulse 1s}}',
                    '@keyframes pulse{to{opacity:0}}main .sample{animation:pulse 1s}',
                    '.sample{--motion:var(--motion);animation:var(--motion) 1s}'):
            with self.subTest(css=css):
                findings = showcase.source_preflight({'index.html': document(css)})
                self.assertEqual(1, len(findings))
                self.assertIn('index.html', findings[0])
                self.assertIn('confirm its intended registry trigger', findings[0])

    def test_reviewer_chrome_is_excluded_and_inline_animation_is_inspected(self):
        chrome = '<button class="sample" data-specimen-variant="default" data-specimen-state="default" style="animation:missing 1s">Reviewer</button>'
        html = document('', outside=chrome)
        self.assertEqual([], showcase.source_preflight({'index.html': html}))
        self.assertTrue(showcase.source_preflight({'index.html': document('', inside_style='animation:missing 1s')}))
        css = '<!-- hifi-reviewer:css:start --><style>@layer x{.sample{animation:missing 1s}}</style><!-- hifi-reviewer:css:end -->'
        self.assertEqual([], showcase.source_preflight({'index.html': document('') + css}))

    def test_typed_status_preserves_boolean_compiler_behavior(self):
        tree = showcase.SourceTree(document(''))
        node = next(item for item in tree.nodes if item['tag'] == 'button')
        for css, status in (('', 'no_animation'), ('.sample{animation:none}', 'no_animation'),
                            ('.sample{animation:missing 1s}', 'unresolved'),
                            ('@keyframes pulse{to{opacity:0}}.sample{animation:pulse 1s}', 'source_backed')):
            with self.subTest(status=status, css=css):
                self.assertEqual(status, provenance.source_status(css, node, tree.ancestors(node)))
                self.assertEqual(status == 'source_backed', provenance.source_backed(css, node, tree.ancestors(node)))

    def test_diagnostics_are_bounded_without_dropping_the_remaining_count(self):
        pages = {f'page{index}.html': document('.sample{animation:missing 1s}') for index in range(30)}
        findings = showcase.source_preflight(pages)
        self.assertEqual(26, len(findings))
        self.assertIn('5 additional pages', findings[-1])


if __name__ == '__main__':
    unittest.main()
