"""design-system/4 showcase: source-bound coverage, fidelity and sandboxed gallery.

All HiFi bytes here are synthetic fixtures, not approved products.
"""

import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
# Append, never prepend: both suites own a test_skill_contract module.
sys.path.append(str(TESTS.parents[2] / "ui-design-builder/scripts/tests"))
sys.path.append(str(TESTS.parents[2] / "ui-design-builder/scripts"))

import check_design_system_pair as checker  # noqa: E402
import design_system_showcase as showcase  # noqa: E402
import render_design_system_preview as preview  # noqa: E402
from showcase_fixture import DEMO_DIR, demo_pages, demo_registry, render_demo  # noqa: E402

BROWSER_TIMEOUT_SECONDS = 120


def findings(registry, pages=None):
    problems = showcase.registry_findings(registry)
    if problems:
        return problems
    return showcase.resolve(registry, pages or demo_pages())[1]


class ShowcaseCoverageTests(unittest.TestCase):
    def test_demo_registry_is_complete_and_source_bound(self):
        self.assertEqual([], findings(demo_registry()))

    def test_every_gap_or_unbacked_claim_fails(self):
        def drop_specimen(data, specimen_id):
            data["showcase"]["specimens"] = [row for row in data["showcase"]["specimens"] if row["id"] != specimen_id]
            data["showcase"]["states"] = [row for row in data["showcase"]["states"] if row.get("specimen") != specimen_id]
            data["showcase"]["motion"] = [row for row in data["showcase"]["motion"] if row["specimen"] != specimen_id]

        def mutate_specimen(specimen_id, **source):
            def apply(data):
                row = next(item for item in data["showcase"]["specimens"] if item["id"] == specimen_id)
                row["source"].update(source)
            return apply

        cases = {
            "missing axis value": (lambda d: drop_specimen(d, "tag-alert"), "StatusTag tones=alert"),
            "missing primitive": (lambda d: drop_specimen(d, "tide-dot"), "primitive TideDot"),
            "missing component state": (lambda d: drop_specimen(d, "berth-card-empty"), "component BerthCard state empty"),
            "missing control state": (lambda d: d["showcase"].update(states=[r for r in d["showcase"]["states"] if r["state"] != "hover"]),
                                      "primitive Button state hover"),
            "unregistered axis value": (lambda d: d["showcase"]["specimens"][0]["axes"].update(variants="ghost"), "closed variant sets"),
            "axis not in source variant": (lambda d: d["showcase"]["specimens"][0]["axes"].update(sizes="md", variants="secondary"),
                                           "must carry axis value secondary"),
            "unknown subject": (lambda d: d["showcase"]["specimens"][0]["subject"].update(name="Ghost"), "unregistered subject"),
            "duplicate id": (lambda d: d["showcase"]["specimens"][1].update(id="button-primary"), "must be unique"),
            "vague reason": (lambda d: d["showcase"]["states"][4].update(reason="n/a"), "concrete reason"),
            "rendered wrong state": (lambda d: d["showcase"]["states"][3].update(specimen="button-primary"), "needs a source element in that state"),
            "unregistered motion": (lambda d: d["showcase"]["motion"][0].update(variant="sheet-drop"), "unregistered variant"),
            "missing motion": (lambda d: d["showcase"].update(motion=d["showcase"]["motion"][:1]), "motion specimen for tide-pulse"),
            "open shape": (lambda d: d["showcase"].update(extra=[]), "exactly schema, specimens, states and motion"),
            "complex selector": (mutate_specimen("tag-calm", selector=".desk .tag"), "simple selector"),
            "unresolved source": (mutate_specimen("tag-calm", variant="calm soft"), "does not resolve"),
            "state claim without source": (mutate_specimen("field-error", state="warning"), "needs a source element in that state"),
            "unknown page": (mutate_specimen("tag-calm", page="missing.html"), "not in the approved HiFi package"),
        }
        for label, (mutate, expected) in cases.items():
            with self.subTest(label):
                data = demo_registry()
                mutate(data)
                self.assertIn(expected, "\n".join(findings(data)))

    def test_json_token_values_match_a_hifi_declaration(self):
        self.assertEqual([], checker.token_value_findings(demo_registry(), demo_pages()))
        data = demo_registry()
        data["tokens"]["color"]["--sea"] = "#2F6F8F"
        self.assertEqual([], checker.token_value_findings(data, demo_pages()))
        data["tokens"]["color"]["--sea"] = "#2f6f8e"
        self.assertEqual(["design-system.json tokens.color.--sea value '#2f6f8e' matches no --sea declaration "
                          "in the approved HiFi CSS"], checker.token_value_findings(data, demo_pages()))
        # Any scope may match; var() declarations, comments and undeclared names are skipped.
        pages = {"index.html": "<style>:root{--a:#fff;--b:var(--a)}[data-theme=dark]{--a: #000 !important}"
                               "/* --c:#456 */</style>"}
        data = {"tokens": {"color": {"--a": "#FFF", "--b": "#123", "--c": "#999"}, "colorDark": {"--a": "#000"}}}
        self.assertEqual([], checker.token_value_findings(data, pages))
        data["tokens"]["colorDark"]["--a"] = "#111"
        self.assertEqual(1, len(checker.token_value_findings(data, pages)))

    def test_rendered_specimens_do_not_replace_required_state_rows(self):
        for kind, name, state in (
            ("component", "BerthCard", "empty"),
            ("primitive", "Button", "default"),
            ("primitive", "TextField", "disabled"),
        ):
            with self.subTest(subject=name, state=state):
                data = demo_registry()
                data["showcase"]["states"] = [
                    row for row in data["showcase"]["states"]
                    if (row["subject"]["kind"], row["subject"]["name"], row["state"]) != (kind, name, state)
                ]
                self.assertTrue(any(
                    row["subject"] == {"kind": kind, "name": name} and row["source"]["state"] == state
                    for row in data["showcase"]["specimens"]
                ))
                self.assertIn(f"showcase is missing {kind} {name} state {state}",
                              "\n".join(showcase.registry_findings(data)))

    def test_pseudo_states_and_motion_need_approved_css(self):
        pages = demo_pages()
        without_active = dict(pages, **{"index.html": pages["index.html"].replace(".btn:active{transform:translateY(1px)}", "")})
        self.assertIn(".btn:active rule", "\n".join(findings(demo_registry(), without_active)))
        reduced_rule = "@media (prefers-reduced-motion:reduce){.sheet{transition:none}.tide-dot{animation:none}.btn{transition:none}}"
        self.assertIn(reduced_rule, pages["index.html"])
        without_reduced = dict(pages, **{"index.html": pages["index.html"].replace(reduced_rule, "")})
        self.assertIn("prefers-reduced-motion", "\n".join(findings(demo_registry(), without_reduced)))
        data = demo_registry()
        data["showcase"]["motion"][0]["trigger"]["from"] = "closed"
        self.assertIn("not backed by the approved source", "\n".join(findings(data)))

    def test_animation_provenance_belongs_to_the_bound_specimen(self):
        data = demo_registry()
        data["showcase"]["motion"][1]["specimen"] = "button-primary"
        with self.subTest(unrelated_specimen="button-primary"):
            self.assertIn("source element and CSS", "\n".join(findings(data)))
        changes = (
            ("@keyframes tide-pulse", "@keyframes unrelated-pulse"),
            ("animation:tide-pulse", "animation:missing-pulse"),
            (".tide-dot{display", ".tide-dot-other{display"),
            ("</style>", ".tide-dot{animation:none}</style>"),
            ("animation:tide-pulse 1.6s var(--ease-out) infinite", "animation:var(--unresolved-animation)"),
        )
        for old, new in changes:
            with self.subTest(change=new):
                pages = demo_pages()
                self.assertIn(old, pages["index.html"])
                pages["index.html"] = pages["index.html"].replace(old, new)
                self.assertIn("source element and CSS", "\n".join(findings(demo_registry(), pages)))
        with self.subTest(reduced_motion_only=True):
            pages = demo_pages()
            pages["index.html"] = pages["index.html"].replace(
                "animation:tide-pulse 1.6s var(--ease-out) infinite", "animation-name:none"
            ).replace(".tide-dot{animation:none}", ".tide-dot{animation:tide-pulse 1.6s infinite}")
            self.assertIn("source element and CSS", "\n".join(findings(demo_registry(), pages)))
        for old, new in (
            (".tide-dot{display", ".unrelated,.tide-dot{display"),
            (".tide-dot{display", "span.tide-dot{display"),
            ("animation:tide-pulse 1.6s var(--ease-out) infinite",
             "animation-name:tide-pulse;animation-duration:1.6s"),
        ):
            with self.subTest(valid_rule=new):
                pages = demo_pages()
                self.assertIn(old, pages["index.html"])
                pages["index.html"] = pages["index.html"].replace(old, new)
                self.assertEqual([], findings(demo_registry(), pages))

    def test_state_view_specimen_renders_at_its_view_target(self):
        page = ('<html lang="en"><body><div data-hifi-canvas data-hifi-targets="390 768" data-hifi-target="390">'
                '<main data-ui-surface="UI-001"><div data-hifi-state-view="loading" data-responsive-target="768" hidden>'
                '<p class="note" data-specimen-variant="default" data-specimen-state="loading">Loading</p></div></main>'
                '</div></body></html>')
        tree = showcase.SourceTree(page)
        node = tree.first(lambda item: item["map"].get("data-specimen-state") == "loading")
        self.assertEqual("768", showcase.specimen_target(tree, node))
        _, _, content = showcase.fragment(tree, node, marker="plate-001")
        self.assertIn('data-hifi-target="768"', content)
        self.assertIn('<div data-hifi-state-view="loading" data-responsive-target="768">', content)
        self.assertIn('<p class="note" data-specimen-variant="default" data-specimen-state="loading" '
                      'data-ds-subject="plate-001">Loading</p>', content)

    def test_animation_provenance_resolves_variables_and_cascade(self):
        keyframes = "@keyframes pulse{from{opacity:.5}to{opacity:1}}"
        cases = (
            (".dot{animation:pulse 1s var(--missing) infinite}", False),
            (".dot{animation:none!important}.dot{animation:pulse 1s linear infinite}", False),
            ("span.dot{animation:none}.dot{animation:pulse 1s linear infinite}", False),
            ("span.dot{animation:pulse 1s linear infinite}.dot{animation:none}", True),
            (".dot{animation:pulse 1s var(--missing, linear) infinite}", True),
            (".dot{--ease:linear;animation:pulse 1s var(--ease) infinite}", True),
            (".dot{--ease:var(--missing);animation:pulse 1s var(--ease) infinite}", False),
            (".dot{--ease:var(--ease,linear);animation:pulse 1s var(--ease) infinite}", False),
            (".dot{--ease:var(--ease,linear);animation:pulse 1s var(--ease,linear) infinite}", True),
            (".dot{animation:pulse 1s cubic-bezier(2,0,0,1) infinite}", False),
            (".dot{animation:pulse 1s steps(0) infinite}", False),
            (".dot{animation:pulse 1s steps(2,jump-none) infinite}", True),
            (".dot{animation:pulse 1s;animation-name:none!important}", False),
            (".dot{animation-name:none!important;animation:pulse 1s}", False),
            (".dot{animation:pulse 1s!important;animation-name:none}", True),
            ("span.dot{animation-name:pulse}.dot{animation:none}", True),
            (".dot{animation:pulse 1s;all:initial}", False),
            (".dot{animation:pulse 1s;-webkit-animation:none!important}", False),
            (".dot{animation:pulse 1s none none}", False),
            (".dot{animation:pulse 1s none}", True),
            (".dot{animation:pulse 1s none forwards}", False),
            (".dot{animation:pulse 1s forwards none}", False),
            (".dot{animation:none 1s forwards}", False),
            (r".dot{animation:pulse 1s}.dot{\61 nimation:none}", False),
            (".dot{animation:var(--missing,pulse 1s steps(2,jump-none))}", True),
            (".dot{animation:pulse 1s}@media(min-width:1px){.dot{animation:none}}", False),
            (".dot{animation:pulse 1s}.dot:hover{animation:none}", False),
        )
        tree = showcase.SourceTree('<html><body><span class="dot"></span></body></html>')
        node = tree.first(lambda item: item["tag"] == "span")
        for css, expected in cases:
            with self.subTest(css=css):
                self.assertEqual(expected, showcase.animation_source_backed(keyframes + css, node))
        for style, expected in (("animation:pulse 1s", True), ("animation:pulse 1s!important", True)):
            with self.subTest(inline=style):
                node["map"]["style"] = style
                self.assertEqual(expected, showcase.animation_source_backed(keyframes, node))
        node["map"]["style"] = "animation:pulse 1s"
        self.assertFalse(showcase.animation_source_backed(keyframes + ".dot{animation:none!important}", node))
        node["map"]["style"] = r"animation:pulse 1s;\61 nimation:none"
        self.assertFalse(showcase.animation_source_backed(keyframes, node))
        node["map"]["style"] = ""
        self.assertFalse(showcase.animation_source_backed("@keyframes NONE{to{opacity:0}}.dot{animation-name:NONE}", node))

    def test_animation_variables_use_computed_ancestor_values(self):
        pages = demo_pages()
        original = "animation:tide-pulse 1.6s var(--ease-out) infinite"
        cases = (
            ("animation:tide-pulse 1.6s var(--missing-easing) infinite", "", False),
            (original, "span.tide-dot{animation:none}", False),
            (original + "!important", ".tide-dot{animation:none}", True),
            (original, ":root{--alias:var(--ease-out)}.tide-dot{--ease-out:var(--alias)}", True),
            ("animation:tide-pulse 1.6s var(--ease-out,linear) infinite", ".tide-dot{--ease-out:initial}", True),
            (original, ".tide-dot{--ease-out:initial}", False),
            (original, r".tide-dot{\61 nimation:none}", False),
            ("animation:tide-pulse 1.6s linear none forwards", "", False),
        )
        for declaration, extra, expected in cases:
            with self.subTest(declaration=declaration, extra=extra):
                changed = dict(pages)
                changed["index.html"] = pages["index.html"].replace(original, declaration).replace("</style>", extra + "</style>")
                self.assertEqual(expected, not findings(demo_registry(), changed))

    def test_package_loader_rejects_stale_or_missing_children(self):
        pages = demo_pages()
        entry = pages["index.html"].encode("utf-8")
        documents, manifest, problems = showcase.load_hifi_package(entry, lambda name: pages[name].encode("utf-8"))
        self.assertEqual(([], ["index.html", "log.html"]), (problems, sorted(documents)))
        self.assertIn("does not match its manifest sha256", "\n".join(showcase.load_hifi_package(
            entry, lambda name: pages[name].encode("utf-8") + b" ")[2]))
        self.assertIn("is missing", "\n".join(showcase.load_hifi_package(entry, lambda name: None)[2]))


class GalleryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html, cls.pages, cls.registry = render_demo()

    def frames(self):
        return re.findall(r'<iframe ([^>]*?) srcdoc="([^"]*)"></iframe>', self.html)

    def test_committed_demo_is_current(self):
        committed = (DEMO_DIR / "design-system-preview.html").read_bytes()
        self.assertEqual(committed, self.html.encode("utf-8"),
                         "regenerate with: python skills/design-system-compiler/scripts/tests/showcase_fixture.py --write")
        self.assertEqual(self.html, render_demo()[0])

    def test_default_state_rows_are_visible_and_counted_once(self):
        count = len(self.registry["showcase"]["states"])
        self.assertIn(f"<strong>{count}</strong>State treatments", self.html)
        self.assertEqual(2, len(re.findall(r'<th scope="row">default</th>', self.html)))

    def test_scripts_are_hash_pinned_and_frames_sandboxed(self):
        policy = re.search(r'Content-Security-Policy" content="([^"]+)"', self.html).group(1).replace("&#x27;", "'")
        self.assertIn("frame-src 'none'", policy)
        self.assertIn("connect-src 'none'", policy)
        script_src = re.search(r"script-src ([^;]+)", policy).group(1)
        self.assertNotIn("unsafe", script_src)
        pinned = set(script_src.split())
        import html as html_lib
        documents = [self.html] + [html_lib.unescape(src) for _, src in self.frames()]
        for document in documents:
            for attrs, body in re.findall(r"<script\b([^>]*)>([\s\S]*?)</script>", document):
                if "application/json" in attrs:
                    continue
                digest = "'sha256-" + __import__("base64").b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'"
                self.assertIn(digest, pinned)
        self.assertNotRegex(self.html, r"<script[^>]+src=|https?://")
        attrs = [item for item, _ in self.frames()]
        self.assertEqual(len(attrs), len(re.findall(r"<iframe ", self.html)))
        for item in attrs:
            self.assertIn('sandbox="allow-scripts"', item)
            self.assertNotIn("allow-same-origin", item)
            self.assertIn("title=", item)

    def test_plates_copy_approved_source_verbatim(self):
        import html as html_lib
        frames = [html_lib.unescape(src) for _, src in self.frames()]
        loading = next(doc for doc in frames if 'data-specimen-state="loading"' in doc and "data-ds-subject" in doc
                       and "Loading arrivals" in doc and "data-hifi-state-view=\"loading\"" in doc)
        # The hidden source state view is shown, exactly as the reviewer runtime does.
        self.assertRegex(loading, r'<div data-hifi-state-view="loading" data-responsive-target="390">')
        self.assertIn("<h2>Berth 4</h2><p>Loading arrivals</p>", loading)
        from showcase_fixture import PRODUCT_CSS
        self.assertIn(PRODUCT_CSS, loading)
        self.assertNotIn("data-hifi-reviewer-shell]{position:fixed", loading)
        self.assertNotIn("data-product-menu", loading)
        component_scripts = re.findall(r"<script>([\s\S]*?)</script>", loading)
        self.assertEqual(1, len(component_scripts), "component plates run only the frame runtime")
        surfaces = [doc for doc in frames if '"kind": "surface"' in doc]
        self.assertEqual(2, len(surfaces))
        self.assertTrue(all("data-product-menu" in doc or "data-product-tab" in doc for doc in surfaces))
        self.assertIn('media="not all"', loading)

    def test_gallery_covers_every_registered_item(self):
        text = self.html
        for token_group in self.registry["tokens"].values():
            for name in token_group:
                self.assertIn(name, text)
        for row in self.registry["showcase"]["specimens"]:
            self.assertIn(f">{row['id']}</a>", text)
        for variant in self.registry["motionVariants"]:
            self.assertIn(f'id="m-{variant}"', text)
        for surface in ("UI-001", "UI-002"):
            self.assertIn(f'id="s-{surface.lower()}"', text)
        for target in ("390", "768", "1200"):
            self.assertIn(f'data-ds-target="{target}"', text)
        self.assertIn("@container (min-width:700px)", text)
        self.assertIn("Fields keep their border on hover", text)
        self.assertIn("data-ds-reduced-toggle", text)
        self.assertIn("OP-open-actions", text)
        self.assertNotIn("Not native evidence", text)
        native = copy.deepcopy(self.registry)
        native["platform"] = "ios"
        import design_system_gallery
        manifest = json.loads(showcase.MANIFEST_RE.search(self.pages["index.html"]).group("data"))
        resolved, _ = showcase.resolve(native, self.pages)
        native_html = design_system_gallery.render_gallery(native, b"{}", b"", self.pages, manifest, resolved,
                                                           {"path": "x/index.html", "sha256": "0" * 64})
        self.assertIn("HTML demonstration of an approved native design. Not native evidence.", native_html)


class PairIntegrationTests(unittest.TestCase):
    def build(self, root):
        from test_ui_design_v3 import v3_publication
        from test_structure_publication import digest
        from test_check_design_system_pair import registry

        ui, prd, hifi = v3_publication(root)
        na = "not_applicable"
        reason = "The synthetic fixture control has no distinct {} appearance."
        states = [{"subject": {"kind": "primitive", "name": name}, "state": state, "mode": na, "reason": reason.format(state)}
                  for name in ("Link", "TextField") for state in ("hover", "focus-visible", "active", "disabled")]
        states += [{"subject": {"kind": "primitive", "name": name}, "state": "default", "mode": "rendered", "specimen": specimen}
                   for name, specimen in (("Link", "link"), ("TextField", "field"))]
        data = registry(schema="design-system/4", stylingMechanism="Tailwind CSS", stateMatrix=["ready", "updated"],
                        motionVariants=[], productComponents={},
                        primitives={"Link": {"layer": "control", "class": "product-link", "variants": ["default"]},
                                    "TextField": {"layer": "control", "class": "product-input", "variants": ["default"]},
                                    "Feedback": {"layer": "surface", "class": "product-feedback"}},
                        showcase={"schema": "ds-showcase/1", "states": states, "motion": [], "specimens": [
                            {"id": "link", "subject": {"kind": "primitive", "name": "Link"}, "axes": {"variants": "default"},
                             "source": {"page": "index.html", "selector": ".product-link", "variant": "default", "state": "default"}},
                            {"id": "field", "subject": {"kind": "primitive", "name": "TextField"}, "axes": {"variants": "default"},
                             "source": {"page": "index.html", "selector": ".product-input", "variant": "default", "state": "default"}},
                            {"id": "feedback", "subject": {"kind": "primitive", "name": "Feedback"}, "axes": {},
                             "source": {"page": "index.html", "selector": ".product-feedback", "variant": "default", "state": "default"}}]})
        data["stackSemantics"] = {"platform": "web", "renderingModel": "SPA",
                                  "componentFoundation": "shadcn/ui owned source", "stylingMechanism": "Tailwind CSS"}
        data["sourceBindings"] = {key: {"path": path.relative_to(root).as_posix(), "sha256": digest(path)}
                                  for key, path in {"prd": prd, "architecture": root / "docs/product/architecture.md",
                                                    "stack": root / "docs/product/stack-decisions.md", "uiDesign": ui, "hifi": hifi}.items()}
        data["sourceBindings"]["uiDesign"]["sha256"] = checker.canonical_ui_approval_sha256(ui.read_text(encoding="utf-8"))
        design = root / "docs/design"
        (design / "design-system.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        (design / "design-system.md").write_text(checker.replace_generated_contract("# Pair\n", data), encoding="utf-8")
        return data, design, hifi

    def cli(self, root, design, *extra):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err):
            stdout = io.BytesIO()
            wrapper = io.TextIOWrapper(stdout, encoding="utf-8")
            with contextlib.redirect_stdout(wrapper):
                code = preview.main(["--repo-root", str(root), "--registry", str(design / "design-system.json"),
                                     "--markdown", str(design / "design-system.md"), *extra])
                wrapper.flush()
        out.write(stdout.getvalue().decode("utf-8", errors="replace"))
        return code, stdout.getvalue(), err.getvalue()

    def test_full_package_validates_renders_and_detects_staleness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, design, hifi = self.build(root)
            markdown = (design / "design-system.md").read_text(encoding="utf-8")
            self.assertEqual([], checker.compare(markdown, data, require_filled=True, repo_root=root))
            code, html, err = self.cli(root, design)
            self.assertEqual(0, code, err)
            self.assertIn(b"Design system specimen book", html)
            (design / "design-system-preview.html").write_bytes(html)
            self.assertEqual(0, self.cli(root, design, "--check", str(design / "design-system-preview.html"))[0])
            # Hand edits and stale HiFi bytes are rejected; a failing pair emits nothing.
            (design / "design-system-preview.html").write_bytes(html + b"<!-- edit -->")
            self.assertEqual(1, self.cli(root, design, "--check", str(design / "design-system-preview.html"))[0])
            original = hifi.read_bytes()
            hifi.write_bytes(original + b"\n")
            code, emitted, err = self.cli(root, design)
            self.assertEqual((1, b""), (code, emitted))
            self.assertIn("sha256 does not match", err)
            hifi.write_bytes(original)
            bad = copy.deepcopy(data)
            bad["showcase"]["specimens"][1]["source"]["variant"] = "default compact"
            self.assertIn("does not resolve", "\n".join(checker.compare(
                checker.replace_generated_contract("# Pair\n", bad), bad, require_filled=True, repo_root=root)))

    def test_token_values_are_checked_against_the_bound_hifi(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, design, hifi = self.build(root)
            css = showcase.analysis_css(hifi.read_text(encoding="utf-8"))
            data["tokens"]["color"]["--ink"] = re.search(r"--ink\s*:\s*([^;{}]+)", css).group(1)
            markdown = checker.replace_generated_contract("# Pair\n", data)
            self.assertEqual([], checker.compare(markdown, data, require_filled=True, repo_root=root))
            data["tokens"]["color"]["--ink"] = "#abcdef"
            markdown = checker.replace_generated_contract("# Pair\n", data)
            self.assertIn("tokens.color.--ink value '#abcdef' matches no --ink declaration", "\n".join(
                checker.compare(markdown, data, require_filled=True, repo_root=root)))

    def test_reuse_keeps_unchanged_package_valid_but_approval_edits_go_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, design, _ = self.build(root)
            ui = root / "docs/design/ui-design.md"
            compiled = ui.read_text(encoding="utf-8")
            package = {name: (design / name).read_bytes() for name in ("design-system.json", "design-system.md")}
            # A later round switches compile/none to reuse/retain without touching the package.
            reused = re.sub(r"^Existing design-system pair disposition: none", "Existing design-system pair disposition: retain",
                            compiled.replace("Package action: compile", "Package action: reuse"), flags=re.M)
            self.assertNotEqual(compiled, reused)
            ui.write_text(reused, encoding="utf-8")
            self.assertEqual(checker.canonical_ui_approval_sha256(compiled), checker.canonical_ui_approval_sha256(reused))
            markdown = package["design-system.md"].decode("utf-8")
            self.assertEqual([], checker.compare(markdown, data, require_filled=True, repo_root=root))
            self.assertEqual(package, {name: (design / name).read_bytes() for name in package})
            # A substantive approval change still invalidates the reused package.
            ui.write_text(reused.replace("Reason:", "Reason: Revised.", 1), encoding="utf-8")
            self.assertIn("sourceBindings.uiDesign sha256 does not match", "\n".join(
                checker.compare(markdown, data, require_filled=True, repo_root=root)))
            # ui-design/2 keeps hashing the same lines it always did.
            legacy = compiled.replace("UI contract: ui-design/3", "UI contract: ui-design/2")
            self.assertNotEqual(checker.canonical_ui_approval_sha256(legacy), checker.canonical_ui_approval_sha256(
                legacy.replace("Existing design-system pair disposition: none", "Existing design-system pair disposition: retain")))

    def test_schema_and_ui_contract_versions_pair_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, design, _ = self.build(root)
            legacy = copy.deepcopy(data)
            legacy["schema"] = "design-system/3"
            joined = "\n".join(checker.compare(checker.replace_generated_contract("# Pair\n", legacy), legacy,
                                               require_filled=True, repo_root=root))
            self.assertIn("showcase requires design-system/4", joined)
            legacy.pop("showcase")
            self.assertIn("must select UI contract ui-design/2 for design-system/3", "\n".join(checker.compare(
                checker.replace_generated_contract("# Pair\n", legacy), legacy, require_filled=True, repo_root=root)))
            ui = root / "docs/design/ui-design.md"
            ui.write_text(ui.read_text(encoding="utf-8").replace("UI contract: ui-design/3", "UI contract: ui-design/2"),
                          encoding="utf-8")
            self.assertIn("must select UI contract ui-design/3 for design-system/4", "\n".join(checker.compare(
                (design / "design-system.md").read_text(encoding="utf-8"), data, require_filled=True, repo_root=root)))

    def test_legacy_preview_bytes_are_unchanged(self):
        legacy = json.dumps({"schema": "design-system/3", "product": "P", "tokens": {}}).encode()
        self.assertEqual(preview.render_preview(legacy, b"m"), preview.render_view(legacy, b"m", Path(".")))


def _playwright():
    from test_reviewer_browser import playwright_module  # shared discovery convention

    node = shutil.which("node")
    return node, playwright_module(node) if node else None


class GalleryBrowserTests(unittest.TestCase):
    """Real Chromium behavior of the committed demo; required when PDH_REQUIRE_BROWSER_TESTS=1."""

    def test_demo_gallery_runs_sandboxed_and_interactive(self):
        node, module = _playwright()
        if not node or not module:
            if os.environ.get("PDH_REQUIRE_BROWSER_TESTS") == "1":
                self.fail("Node.js and PLAYWRIGHT_MODULE are required for the gallery browser test")
            self.skipTest("Node Playwright is unavailable")
        script = r"""
const [,, url, module] = process.argv;
const {chromium} = require(module);
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({viewport: {width: 1280, height: 900}});
  const page = await context.newPage();
  const errors = [], requests = [], popups = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", error => errors.push(String(error)));
  context.on("request", request => { if (!request.url().startsWith("file:") && !request.url().startsWith("about:") && !request.url().startsWith("data:")) requests.push(request.url()); });
  page.on("popup", popup => popups.push(popup.url()));
  await page.goto(url);
  await page.waitForTimeout(1500);
  const result = {};
  result.frames = await page.$$eval("iframe[data-ds-frame]", items => items.map(item => ({id: item.dataset.dsFrame, height: item.getBoundingClientRect().height, ready: item.dataset.dsReady || null})));
  const handle = async id => (await page.$(`iframe[data-ds-frame="${id}"]`)).contentFrame();
  const surfaceId = await page.$eval("select[data-ds-state-for]", item => item.dataset.dsStateFor);
  const surface = await handle(surfaceId);
  await page.click(`button[data-ds-for="${surfaceId}"][data-ds-target="1200"]`);
  await page.waitForTimeout(300);
  result.canvasWide = await surface.$eval("[data-hifi-canvas]", item => Math.round(item.getBoundingClientRect().width));
  result.columns = await surface.$eval(".board", item => getComputedStyle(item).gridTemplateColumns.split(" ").length);
  await page.$eval(`input[data-ds-width-for="${surfaceId}"]`, item => { item.value = "560"; item.dispatchEvent(new Event("input", {bubbles: true})); });
  await page.waitForTimeout(300);
  result.canvasMid = await surface.$eval("[data-hifi-canvas]", item => Math.round(item.getBoundingClientRect().width));
  await page.selectOption(`select[data-ds-state-for="${surfaceId}"]`, "empty");
  await page.waitForTimeout(200);
  result.emptyVisible = await surface.$eval('[data-card-state="empty"]', item => item.offsetParent !== null);
  await surface.click("[data-product-menu]");
  result.menuOpen = await surface.$eval("#berth-menu", item => !item.hidden);
  await surface.click('a[href="log.html"]');
  await page.waitForTimeout(300);
  result.stayed = surface.url();
  result.status = await page.$eval(`[data-ds-status="${surfaceId}"]`, item => item.textContent);
  const motionId = await page.$eval('#m-sheet-rise + figure button[data-ds-motion="play"]', item => item.dataset.dsFor);
  const motion = await handle(motionId);
  await page.click(`button[data-ds-for="${motionId}"][data-ds-motion="play"]`);
  await page.waitForTimeout(100);
  result.sheetOpen = await motion.$eval("[data-ds-subject]", item => item.getAttribute("data-open"));
  const tideId = await page.$eval('#m-tide-pulse + figure button[data-ds-motion="play"]', item => item.dataset.dsFor);
  const tide = await handle(tideId);
  // Animations on the attached subject, by play state; detached nodes never count.
  const tideStates = () => tide.evaluate(() => {
    const subject = document.querySelector("[data-ds-subject]");
    return document.getAnimations().filter(item => subject && subject.isConnected && item.effect.target === subject).map(item => item.playState);
  });
  const tideClick = async action => { await page.click(`button[data-ds-for="${tideId}"][data-ds-motion="${action}"]`); await page.waitForTimeout(100); return tideStates(); };
  result.tideReplay = await tideClick("play");
  result.tideReplayAgain = await tideClick("play");
  result.tideStop = await tideClick("stop");
  result.tideStopReplay = await tideClick("play");
  await page.click("[data-ds-reduced-toggle]");
  await page.waitForTimeout(200);
  result.reducedPressed = await page.$eval("[data-ds-reduced-toggle]", item => item.getAttribute("aria-pressed"));
  result.reducedMedia = await motion.$eval("style[data-ds-reduced]", item => item.media);
  result.tideReduced = await tideStates();
  const fresh = await context.newPage();
  fresh.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  await fresh.goto(url);
  await fresh.keyboard.press("Tab");
  result.firstFocus = await fresh.evaluate(() => document.activeElement && document.activeElement.className);
  await fresh.keyboard.press("Enter");
  result.skipTarget = await fresh.evaluate(() => document.activeElement && document.activeElement.id);
  await fresh.focus(`button[data-ds-for="${surfaceId}"][data-ds-target="768"]`);
  await fresh.keyboard.press("Enter");
  result.keyboardTarget = await fresh.$eval(`button[data-ds-for="${surfaceId}"][data-ds-target="768"]`, item => item.getAttribute("aria-pressed"));
  result.hostWidth = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
  await page.setViewportSize({width: 390, height: 800});
  await page.waitForTimeout(200);
  result.mobileNoOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
  console.log(JSON.stringify({result, errors, requests, popups}));
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
"""
        url = (DEMO_DIR / "design-system-preview.html").resolve().as_uri()
        try:
            completed = subprocess.run([node, "-", url, module], input=script, text=True, encoding="utf-8",
                                       capture_output=True, timeout=BROWSER_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            self.fail(f"gallery browser check exceeded {BROWSER_TIMEOUT_SECONDS}s: {error}")
        self.assertEqual(0, completed.returncode, completed.stderr[-3000:])
        report = json.loads(completed.stdout.strip().splitlines()[-1])
        result = report["result"]
        self.assertEqual([], report["errors"])
        self.assertEqual([], report["requests"])
        self.assertEqual([], report["popups"])
        self.assertTrue(result["frames"])
        self.assertTrue(all(item["ready"] == "1" for item in result["frames"]), result["frames"])
        self.assertEqual(1200, result["canvasWide"])
        self.assertEqual(3, result["columns"])
        self.assertEqual(560, result["canvasMid"])
        self.assertTrue(result["emptyVisible"])
        self.assertTrue(result["menuOpen"])
        self.assertEqual("about:srcdoc", result["stayed"])
        self.assertIn("log.html", result["status"])
        self.assertEqual("true", result["sheetOpen"])
        self.assertEqual(["running"], result["tideReplay"])
        self.assertEqual(["running"], result["tideReplayAgain"])
        self.assertEqual(["paused"], result["tideStop"])
        self.assertEqual(["running"], result["tideStopReplay"])
        self.assertEqual("true", result["reducedPressed"])
        self.assertEqual("all", result["reducedMedia"])
        self.assertEqual([], result["tideReduced"])
        self.assertEqual("skip", result["firstFocus"])
        self.assertEqual("main", result["skipTarget"])
        self.assertEqual("true", result["keyboardTarget"])
        self.assertTrue(result["hostWidth"])
        self.assertTrue(result["mobileNoOverflow"])


if __name__ == "__main__":
    unittest.main()
