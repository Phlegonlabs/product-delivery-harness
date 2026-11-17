"""Direct product joins preserve checks after removal of the wireframe stage."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_ui_design_contract as ui
from hifi_product_contract import hifi_prd_findings
from test_operation_coverage import prd


def fixture():
    operation = {"id": "OP-home", "trigger": "Home", "control": "home", "sourceState": "ready",
                 "destination": {"surface": "UI-001", "state": "ready"}, "presentation": "page"}
    manifest = {"schema": "ui-hifi/2", "pages": [], "surfaces": [
        {"id": "UI-001", "page": "index.html", "route": "/account", "states": ["ready"],
         "responsive": {"kind": "viewports", "targets": [390, 768, 1200]}, "controls": ["home"]}],
        "interactions": [{"id": "OP-home", "control": "home", "kind": "navigate",
                          "source": {"surface": "UI-001", "state": "ready"}, "destination": operation["destination"]}]}
    inventory = {"schema": "ui-hifi-copy/1", "locale": "en", "surfaces": [
        {"id": "UI-001", "copyStatus": "approved", "items": [{"id": "home", "copy": {
            "kind": "static", "role": "action", "text": "Home", "source": "PRD action Home",
            "status": "approved"}}]}]}
    markup = '<main data-ui-surface="UI-001"><a data-copy-id="home" data-copy-locale="en">Home</a></main>'
    return prd(operation), manifest, inventory, markup


def documents(inventory, markup):
    return {"index.html": markup + '<script id="ui-hifi-copy" type="application/json">' + json.dumps(inventory) + '</script>'}


class HiFiProductContractTests(unittest.TestCase):
    def test_terminal_surface_rejects_custom_interactive_roles_and_inline_widgets(self):
        product, manifest, inventory, markup = fixture()
        anchor = next(line for line in product.splitlines() if '`operations`:' in line)
        product = product.replace(anchor, '- `operations`: none — read-only receipt with no product controls')
        manifest['surfaces'][0].update(navigation=[], controls=[])
        manifest['interactions'] = []
        passive = markup.replace('<a ', '<p ').replace('</a>', '</p>')
        roles = ('button', 'link', 'menuitem', 'tab', 'checkbox', 'radio', 'switch',
                 'slider', 'spinbutton', 'textbox', 'combobox')
        for attributes in tuple(f'role="{role}" tabindex="0" aria-checked="false"' for role in roles) + (
                'tabindex="0" onclick="this.dataset.changed=true"',
                'tabindex="-1" onclick="this.dataset.changed=true"',
                'onclick="this.dataset.changed=true"',
                'tabindex="-1" onkeydown="this.dataset.changed=true"',
                'role="checkbox" tabindex="-1" onclick="this.dataset.changed=true"'):
            with self.subTest(attributes=attributes):
                widget = passive.replace('<p ', '<p ' + attributes + ' ', 1)
                findings = hifi_prd_findings(product, manifest, documents(inventory, widget))
                self.assertIn('renders a product control', '\n'.join(findings))
        self.assertEqual([], hifi_prd_findings(product, manifest, documents(inventory, passive)))

    def test_passive_focus_targets_remain_valid_on_terminal_surfaces(self):
        product, manifest, inventory, markup = fixture()
        anchor = next(line for line in product.splitlines() if '`operations`:' in line)
        product = product.replace(anchor, '- `operations`: none — read-only receipt with no product controls')
        manifest['surfaces'][0].update(navigation=[], controls=[])
        manifest['interactions'] = []
        inventory['surfaces'][0]['items'][0]['copy'].update(
            text='Receipt', role='heading', source='Owner receipt heading')
        for attributes in ('tabindex="-1" onanimationend="this.classList.remove(\'entering\')"',
                           'tabindex="-1" onfocus="this.classList.remove(\'entering\')"',
                           'tabindex="0" onanimationend="this.classList.remove(\'entering\')"',
                           'tabindex="0" onfocus="this.classList.remove(\'entering\')"'):
            with self.subTest(attributes=attributes):
                passive = markup.replace('<a ', '<h2 ' + attributes + ' ').replace('>Home</a>', '>Receipt</h2>')
                self.assertEqual([], hifi_prd_findings(product, manifest, documents(inventory, passive)))
                parser = ui._HiFiProductControls()
                parser.feed(passive)
                parser.close()
                self.assertEqual([], parser.errors)
                self.assertFalse(parser.controls)

    def test_handler_discovery_separates_pointer_keyboard_and_passive_handlers(self):
        groups = (
            (('onclick', 'ondblclick', 'onpointerdown', 'onpointerup', 'onmousedown', 'onmouseup',
              'ontouchstart', 'ontouchend'),
             (('0', True), ('-1', True), ('invalid', True), ('', True), (None, True))),
            (('onkeydown', 'onkeyup', 'onkeypress'),
             (('0', True), ('-1', True), ('invalid', True), ('', True), (None, False))),
            (('onanimationend', 'onfocus', 'onblur', 'ontransitionend', 'onload', 'onscroll',
              'onpointermove', 'onmouseenter', 'ondragstart', 'oninput'),
             (('0', False), ('-1', False), ('invalid', False), ('', False), (None, False))),
        )
        product, manifest, inventory, markup = fixture()
        anchor = next(line for line in product.splitlines() if '`operations`:' in line)
        product = product.replace(anchor, '- `operations`: none — read-only receipt with no product controls')
        manifest['surfaces'][0].update(navigation=[], controls=[])
        manifest['interactions'] = []
        for handlers, cases in groups:
            for handler in handlers:
                for tabindex, expected in cases:
                    with self.subTest(handler=handler, tabindex=tabindex):
                        binding = '' if tabindex is None else f'tabindex="{tabindex}"'
                        widget = markup.replace('<a ', f'<p {binding} {handler}="activate()" ').replace('</a>', '</p>')
                        parser = ui._HiFiProductControls()
                        parser.feed(widget)
                        parser.close()
                        self.assertEqual(expected, 'needs a navigation/control ID' in '\n'.join(parser.errors))
                        findings = hifi_prd_findings(product, manifest, documents(inventory, widget))
                        if expected:
                            self.assertIn('renders a product control', '\n'.join(findings))
                        else:
                            self.assertEqual([], findings)
        for markup in ('<button onclick="activate()">Action</button>',
                       '<input onkeydown="activate()">', '<a href="details.html" onclick="activate()">Action</a>'):
            parser = ui._HiFiProductControls()
            parser.feed('<main data-ui-surface="UI-001">' + markup + '</main>')
            parser.close()
            self.assertIn('needs a navigation/control ID', '\n'.join(parser.errors))

    def test_keyboard_discovery_includes_native_focusability_only_with_a_handler(self):
        product, manifest, inventory, markup = fixture()
        anchor = next(line for line in product.splitlines() if '`operations`:' in line)
        product = product.replace(anchor, '- `operations`: none — read-only receipt with no product controls')
        manifest['surfaces'][0].update(navigation=[], controls=[])
        manifest['interactions'] = []
        cases = (('summary', '', True), ('area', 'href="details.html"', True), ('area', '', False),
                 ('iframe', '', True), ('audio', 'controls', True), ('audio', '', False),
                 ('video', 'controls', True), ('video', '', False), ('p', 'contenteditable', True),
                 ('p', 'contenteditable="plaintext-only"', True), ('p', 'contenteditable="false"', False),
                 ('p', 'contenteditable="FALSE"', False))
        for tag, attributes, focusable in cases:
            for handler in ('', 'onkeydown="activate()"', 'onfocus="observe()"'):
                with self.subTest(tag=tag, attributes=attributes, handler=handler):
                    widget = markup.replace('<a ', f'<{tag} {attributes} {handler} ').replace('</a>', f'</{tag}>')
                    if tag == 'summary':
                        widget = widget.replace('<summary ', '<details><summary ').replace('</summary>', '</summary></details>')
                    elif tag == 'area':
                        widget = widget.replace('>Home</area>', ' alt="Home">')
                    expected = focusable and handler.startswith('onkeydown=')
                    parser = ui._HiFiProductControls()
                    parser.feed(widget)
                    parser.close()
                    self.assertEqual(expected, 'needs a navigation/control ID' in '\n'.join(parser.errors))
                    findings = hifi_prd_findings(product, manifest, documents(inventory, widget))
                    if expected:
                        self.assertIn('renders a product control', '\n'.join(findings))
                    else:
                        self.assertEqual([], findings)

    def test_all_interactive_roles_use_the_same_control_discovery(self):
        for role in ('button', 'link', 'menuitem', 'tab', 'checkbox', 'radio', 'switch',
                     'slider', 'spinbutton', 'textbox', 'combobox'):
            with self.subTest(role=role):
                markup = f'<main data-ui-surface="UI-001"><p role="{role}" data-control-id="toggle">Toggle</p></main>'
                parser = ui._HiFiProductControls()
                parser.feed(markup)
                parser.close()
                self.assertEqual([], parser.errors)
                self.assertIn(('UI-001', 'toggle'), parser.controls)
                surface_parser = ui._HiFiSurfaceParser()
                surface_parser.feed(markup)
                surface_parser.close()
                self.assertIn('toggle', surface_parser.surfaces['UI-001']['controls'])
                unbound = ui._HiFiProductControls()
                unbound.feed(markup.replace(' data-control-id="toggle"', ''))
                unbound.close()
                self.assertIn('needs a navigation/control ID', '\n'.join(unbound.errors))

    def test_terminal_prd_surface_has_empty_lists_and_no_product_control(self):
        product, manifest, inventory, markup = fixture()
        anchor = next(line for line in product.splitlines() if '`operations`:' in line)
        product = product.replace(anchor, '- `operations`: none — read-only receipt with no product controls')
        manifest['surfaces'][0].update(navigation=[], controls=[])
        manifest['interactions'] = []
        passive = markup.replace('<a ', '<p ').replace('</a>', '</p>')
        self.assertEqual([], hifi_prd_findings(product, manifest, documents(inventory, passive)))
        self.assertIn('renders a product control', '\n'.join(hifi_prd_findings(product, manifest, documents(inventory, markup))))
        manifest['surfaces'][0]['controls'] = ['home']
        self.assertIn('has controls but PRD operations are none', '\n'.join(
            hifi_prd_findings(product, manifest, documents(inventory, passive))))

    def test_direct_join_needs_no_wireframe(self):
        product, manifest, inventory, markup = fixture()
        self.assertEqual([], hifi_prd_findings(product, manifest, documents(inventory, markup)))

    def test_missing_surface_operation_state_route_or_target_fails(self):
        product, manifest, inventory, markup = fixture()
        for key, value in (("route", "/wrong"), ("states", []), ("responsive", {"kind": "viewports", "targets": [390, 1200]})):
            bad = copy.deepcopy(manifest); bad["surfaces"][0][key] = value
            self.assertTrue(hifi_prd_findings(product, bad, documents(inventory, markup)), key)
        for key in ("surfaces", "interactions"):
            bad = copy.deepcopy(manifest); bad[key] = []
            self.assertTrue(hifi_prd_findings(product, bad, documents(inventory, markup)), key)

    def test_wrong_operation_identity_destination_and_kind_fail(self):
        product, manifest, inventory, markup = fixture()
        for key, value in (("id", "invented"), ("kind", "state"), ("destination", {"surface": "UI-001", "state": "error"})):
            bad = copy.deepcopy(manifest); bad["interactions"][0][key] = value
            self.assertTrue(hifi_prd_findings(product, bad, documents(inventory, markup)), key)

    def test_copy_is_real_product_dom_not_reviewer_or_inert_markup(self):
        product, manifest, inventory, markup = fixture()
        for bad in (markup.replace('data-ui-surface', 'data-reviewer'), '<template>'+markup+'</template>',
                    markup.replace('>Home<', '>Wrong<'), markup.replace('data-copy-id="home"', ''),
                    markup + '<main data-ui-surface="UI-001">Unbound claim</main>',
                    markup + markup.replace('>Home<', '>Wrong<')):
            self.assertTrue(hifi_prd_findings(product, manifest, documents(inventory, bad)), bad)

    def test_assistive_label_cannot_mask_different_visible_text(self):
        product, manifest, inventory, markup = fixture()
        for attr in ('aria-label="Home"', 'value="Home"', 'alt="Home"', 'placeholder="Home"'):
            bad = markup.replace('data-copy-locale="en">Home<', 'data-copy-locale="en" ' + attr + '>Leave<')
            self.assertIn("product text differs", "\n".join(
                hifi_prd_findings(product, manifest, documents(inventory, bad))), attr)
        for good in ('<input data-copy-id="home" data-copy-locale="en" value="Home">',
                     '<img data-copy-id="home" data-copy-locale="en" alt="Home">',
                     '<button data-copy-id="home" data-copy-locale="en" aria-label="Home"><svg></svg></button>'):
            self.assertEqual([], hifi_prd_findings(product, manifest, documents(
                inventory, '<main data-ui-surface="UI-001">' + good + '</main>')), good)

    def test_copy_inventory_missing_extra_and_child_declaration_fail(self):
        product, manifest, inventory, markup = fixture()
        self.assertTrue(hifi_prd_findings(product, manifest, {"index.html": markup}))
        bad = documents(inventory, markup); bad['child.html'] = bad['index.html']
        self.assertTrue(hifi_prd_findings(product, manifest, bad))
        for page in ('index.html', 'child.html'):
            bad = documents(inventory, markup)
            bad[page] = bad.get(page, '') + '<script type="application/json" id="ui-hifi-copy">{}</script>'
            self.assertTrue(hifi_prd_findings(product, manifest, bad))
        inventory['surfaces'][0]['items'] = []
        self.assertTrue(hifi_prd_findings(product, manifest, documents(inventory, markup)))

    def test_dynamic_and_parallel_copy_keep_existing_contract_rules(self):
        product, manifest, inventory, markup = fixture()
        item = inventory['surfaces'][0]['items'][0]['copy']
        item.update(kind='dynamic', example='Home')
        self.assertTrue(hifi_prd_findings(product, manifest, documents(inventory, markup)))
        item.update(kind='static', locale='en', parallel=[dict(kind='static', role='action', text='首頁', source='Owner translation', status='approved', locale='zh-TW')])
        self.assertTrue(hifi_prd_findings(product, manifest, documents(inventory, markup)))
        markup = markup.replace('</main>', '<span data-copy-id="home" data-copy-locale="zh-TW">首頁</span></main>')
        self.assertEqual([], hifi_prd_findings(product, manifest, documents(inventory, markup)))

    def test_version_marker_cannot_downgrade_malformed_current_package(self):
        self.assertEqual('legacy', ui.ui_contract_version('# UI Design Contract\n'))
        self.assertEqual('ui-design/2', ui.ui_contract_version('# UI Design Contract\nUI contract: ui-design/2\n'))
        self.assertEqual('ui-design/3', ui.ui_contract_version('# UI Design Contract\nUI contract: ui-design/3\n'))
        for marker in ('', 'ui-design/9', 'ui-design/2 extra', 'ui-design/2\nUI contract: ui-design/3'):
            with self.assertRaises(ValueError):
                ui.ui_contract_version('# UI Design Contract\nUI contract: '+marker+'\n')


if __name__ == '__main__':
    unittest.main()
