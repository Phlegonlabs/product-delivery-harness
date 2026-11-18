"""Synthetic packages test current publication without inventing real review evidence."""
import json
from pathlib import Path
import re
import tempfile
import unittest

from test_structure_publication import modern_publication, digest, checker, build_receipt


def current_publication(root):
    ui, prd, wf, hifi = modern_publication(root)
    text = ui.read_text(encoding='utf-8')
    start, end = text.index('## Wireframe Validation'), text.index('### Frontend Design Usage')
    text = text[:start] + text[end:]
    text = re.sub(r'^\| wireframe \|.*\n', '', text, flags=re.M)
    text = re.sub(r'; wireframe=[^;\n]+', '', text)
    text = text.replace('# UI Design Contract\n', '# UI Design Contract\n\nUI contract: ui-design/2\n', 1)
    old_hifi = digest(hifi)
    html = hifi.read_text(encoding='utf-8')
    match = checker.HIFI_MANIFEST_RE.search(html)
    manifest = json.loads(match.group('data'))
    for action in manifest['interactions']:
        action['id'] = 'OP-' + action['id']
    html = html[:match.start('data')] + json.dumps(manifest) + html[match.end('data'):]
    html = html.replace('<h1>', '<h1 data-hifi-state-view="ready">', 1)
    html = html.replace('<section class="product-feedback"',
                        '<section data-hifi-state-view="updated" class="product-feedback"', 1)
    items = []
    for copy_id, value, marker in (
        ('home', 'Pages', 'data-navigation-id="home"'),
        ('title', 'HiFi review surface with meaningful content', '<h1'),
        ('refresh', 'Refresh', 'data-control-id="refresh"'),
        ('filter', 'Retained input', 'data-control-id="filter"'),
        ('feedback', 'Saved locally.', 'class="product-feedback"'),
    ):
        html = html.replace(marker, marker + f' data-copy-id="{copy_id}" data-copy-locale="en-US"')
        items.append({'id': copy_id, 'copy': {'kind': 'static', 'role': 'content', 'text': value,
                                            'status': 'approved', 'source': 'Synthetic approved fixture'}})
    inventory = {'schema': 'ui-hifi-copy/1', 'locale': 'en-US', 'surfaces': [
        {'id': 'UI-001', 'copyStatus': 'approved', 'items': items}]}
    html = html.replace('</body>', '''<script>
document.querySelector('[data-control-id="filter"]').addEventListener('input', function () {
    document.__hifiReviewerRuntime.selectState('updated');
});
</script></body>''', 1)
    html = html.replace('</body>', '<script id="ui-hifi-copy" type="application/json">' + json.dumps(inventory) + '</script></body>')
    hifi.write_text(html, encoding='utf-8')
    text = text.replace(old_hifi, digest(hifi))
    # Rebuild synthetic receipts with current bytes. This is fixture generation,
    # never evidence migration for a real approved package.
    for receipt_path in (root / 'docs/evidence').glob('*.json'):
        if receipt_path.name.endswith('-output.json'):
            continue
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        old_receipt = digest(receipt_path)
        out_path = root / receipt['receipt']['outputArtifact']['path']
        output = json.loads(out_path.read_text(encoding='utf-8'))
        if output['subject']['path'] == wf.relative_to(root).as_posix():
            continue
        output['subject']['sha256'] = digest(hifi)
        for binding in output['execution']['artifacts']:
            if binding['path'] == hifi.relative_to(root).as_posix():
                binding['sha256'] = digest(hifi)
        output['execution']['artifacts'] = [binding for binding in output['execution']['artifacts']
                                           if binding['path'] != wf.relative_to(root).as_posix()]
        for field in ('interactions', 'navigation'):
            for row in output.get(field, []):
                row['id'] = 'OP-' + row['id']
        out_path.write_text(json.dumps(output), encoding='utf-8')
        receipt_path.write_text(json.dumps(build_receipt(root, out_path.relative_to(root).as_posix())), encoding='utf-8')
        text = text.replace(old_receipt, digest(receipt_path))
    text = re.sub(r'ui-design=docs/design/ui-design.md @ sha256:[0-9a-f]{64}',
                  'ui-design=docs/design/ui-design.md @ sha256:' + checker.canonical_ui_approval_sha256(text), text)
    ui.write_text(text, encoding='utf-8')
    wf.unlink()  # Only a disposable test fixture; prove no hidden file dependency.
    return ui, prd, hifi


class WireframeFreePublicationTests(unittest.TestCase):
    def test_legacy_structure_only_check_still_hashes_recorded_target(self):
        from test_ui_design_contract import materialize_publication
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prd, _, _, wf, hifi, _ = materialize_publication(root, required=False)
            hifi.write_text(hifi.read_text(encoding='utf-8')+'\n', encoding='utf-8')
            findings = checker.validate(root/'docs/design/ui-design.md', repo_root=root,
                prd_path=prd, wireframes_path=wf, require_wireframe_approved=True)
            self.assertIn('Approved target', '\n'.join(findings))

    def test_preflight_and_final_visual_gate_without_wireframe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = current_publication(root)
            self.assertEqual([], checker.validate(ui, repo_root=root, prd_path=prd,
                hifi_path=hifi, require_hifi_preflight=True))
            self.assertEqual([], checker.validate(ui, repo_root=root, prd_path=prd,
                hifi_path=hifi, require_filled=True, require_visual_approved=True))

    def test_preflight_does_not_require_final_review_or_owner_visual_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = current_publication(root)
            text = ui.read_text(encoding='utf-8')
            start, end = text.index('## HiFi Review'), text.index('## Design System Need Gate')
            text = text[:start] + '## HiFi Review\n\n## Visual Approval\n\nDecision: pending\n\n' + text[end:]
            ui.write_text(text, encoding='utf-8')
            self.assertEqual([], checker.validate(ui, repo_root=root, prd_path=prd,
                hifi_path=hifi, require_hifi_preflight=True))
            self.assertTrue(checker.validate(ui, repo_root=root, prd_path=prd,
                hifi_path=hifi, require_visual_approved=True))

    def test_harness_adapter_and_compiler_preflight_without_wireframe(self):
        from harness_contract_join import full_ui_design_checker_errors_at_paths
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ui, prd, hifi = current_publication(root)
            self.assertEqual([], full_ui_design_checker_errors_at_paths(ui, repo_root=root,
                prd_path=prd, wireframes_path=None, hifi_path=hifi))
            text = ui.read_text(encoding='utf-8').replace('Decision: not_required', 'Decision: required')
            text = re.sub(r'^Replacement visual contract when_not_required:.*$',
                          'Compiled design system pair: pending — design-system-compiler', text, flags=re.M)
            ui.write_text(text, encoding='utf-8')
            self.assertEqual([], checker._validate_for_design_system_preflight(ui, repo_root=root,
                prd_path=prd, wireframes_path=None, hifi_path=hifi))


if __name__ == '__main__':
    unittest.main()
