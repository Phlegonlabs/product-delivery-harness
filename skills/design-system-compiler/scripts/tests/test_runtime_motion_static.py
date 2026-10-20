"""ds-showcase/2 source-runtime motion: closed shape and static source joins.

All HiFi bytes are the synthetic Kiln Timer fixture, not an approved product.
Static joins prove identity and association only; playback is browser-tested
in test_runtime_motion_browser.py.
"""

import base64
import copy
import hashlib
import html as html_lib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
sys.path.append(str(TESTS))

import design_system_showcase as showcase  # noqa: E402
import render_design_system_preview as preview  # noqa: E402
import showcase_runtime as runtime  # noqa: E402
from design_system_runtime_assets import INITIAL_MOUNT, RUNTIME_FRAME, RUNTIME_GALLERY  # noqa: E402
from runtime_fixture import (HIFI, INTENTS, PRODUCT_CSS, PRODUCT_SCRIPT, REVIEWER_RUNTIME, UI, evidence_files,  # noqa: E402
                             pages, reader, registry, render, repo_files, sha, ui_record)


def joins(data=None, page_set=None, files=None):
    data = registry() if data is None else data
    page_set = pages() if page_set is None else page_set
    problems = showcase.registry_findings(data)
    if problems:
        return problems
    manifest = json.loads(showcase.MANIFEST_RE.search(page_set["index.html"]).group("data"))
    found = showcase.resolve(data, page_set)[1]
    return found + runtime.resolve_runtime(data, page_set, manifest, reader(files or repo_files(page_set)))[1]


def row(data, variant):
    return next(item for item in data["showcase"]["motion"] if item["variant"] == variant)


class TriggerShapeTests(unittest.TestCase):
    def test_fixture_binds_each_row_to_its_exact_copies(self):
        page_set = pages()
        self.assertEqual([], joins(page_set=page_set))
        manifest = json.loads(showcase.MANIFEST_RE.search(page_set["index.html"]).group("data"))
        bound, _ = runtime.resolve_runtime(registry(), page_set, manifest, reader(repo_files(page_set)))
        self.assertEqual({"kiln-rise", "belt-step", "belt-stripes"}, set(bound))
        tree = bound["kiln-rise"]["tree"]
        for target, node in bound["kiln-rise"]["subjects"].items():
            view = next(item for item in tree.ancestors(node) if "data-hifi-state-view" in item["map"])
            self.assertEqual(("ready", target), (view["map"]["data-hifi-state-view"], view["map"]["data-responsive-target"]))
        self.assertEqual({"390", "768"}, set(bound["belt-stripes"]["subjects"]))

    def test_open_or_executable_shapes_fail_closed(self):
        cases = {
            "callback key": (lambda d: row(d, "kiln-rise")["trigger"].update(onFinish="play()"), "must contain exactly"),
            "activation callback": (lambda d: row(d, "kiln-rise")["trigger"].update(activation={"kind": "viewport", "callback": "go"}),
                                    "activation must be exactly"),
            "unknown activation": (lambda d: row(d, "kiln-rise")["trigger"].update(activation={"kind": "hover"}), "activation must be exactly"),
            "url target": (lambda d: row(d, "kiln-rise")["trigger"].update(target="https://example.invalid/x"), "target is not a closed literal"),
            "code intent": (lambda d: row(d, "kiln-rise")["trigger"].update(intent="MM-001();"), "intent is not a closed literal"),
            "object hash": (lambda d: row(d, "kiln-rise")["trigger"].update(scriptSha256={"eval": "x"}), "scriptSha256 is not a closed literal"),
            "open mechanism": (lambda d: row(d, "belt-stripes")["trigger"].update(mechanism="css-transition"), "mechanism must be"),
            "duplicate intent": (lambda d: row(d, "belt-stripes")["trigger"].update(intent="MM-002"), "bound by more than one"),
            "schema 1": (lambda d: d["showcase"].update(schema="ds-showcase/1"), "attribute, class or animation trigger"),
        }
        for label, (mutate, expected) in cases.items():
            with self.subTest(label):
                data = registry()
                mutate(data)
                self.assertIn(expected, "\n".join(joins(data)))


class IntentEvidenceTests(unittest.TestCase):
    def files_with(self, text=None, **changes):
        files = evidence_files()
        files.update(changes)
        files[UI] = (text if text is not None else ui_record(evidence_files())).encode("utf-8")
        files.update({"docs/design/ui-references/kiln/index.html": pages()["index.html"].encode("utf-8")})
        return files

    def test_intent_and_evidence_bind_to_the_current_ui_record(self):
        scope_moved = tuple((i, "UI-002 / kiln demonstration" if i == "MM-001" else s, t) for i, s, t in INTENTS)
        no_reduced = {path: data for path, data in evidence_files().items() if path != "docs/design/evidence/mm-003-reduced.json"}
        cases = {
            "missing intent": (None, {}, lambda d: row(d, "kiln-rise")["trigger"].update(intent="MM-009"), "is not in the approved"),
            "unapproved intent": (ui_record(evidence_files(), status="proposed"), {}, None, "must be an approved motion intent"),
            "scope surface": (ui_record(evidence_files(), rows=scope_moved), {}, None, "scope does not name surface UI-001"),
            "missing reduced": (ui_record(no_reduced), {}, None, "MM-003 has no reduced-motion PASS evidence"),
            "stale evidence": (None, {"docs/design/evidence/mm-002-normal.json": b"{}"}, None, "MM-002 normal-motion evidence is missing or stale"),
        }
        for label, (text, changes, mutate, expected) in cases.items():
            with self.subTest(label):
                data = registry()
                if mutate:
                    mutate(data)
                self.assertIn(expected, "\n".join(joins(data, files=self.files_with(text, **changes))))
        files = self.files_with()
        del files[UI]
        self.assertIn("readable sourceBindings.uiDesign", "\n".join(joins(files=files)))
        self.assertEqual([], joins(files=self.files_with()))


class ScriptAndScopeTests(unittest.TestCase):
    def test_script_hash_binds_one_preserved_product_script(self):
        reviewer_body = re.search(r"<script>([\s\S]*?)</script>", REVIEWER_RUNTIME).group(1)
        cases = {
            "unknown": ("0" * 64, None, "matches no executable inline product script"),
            "reviewer runtime": (sha(reviewer_body), None, "names a reviewer script"),
            "reviewer call": (sha('connectHifiReviewer({"packageId": "ui-hifi/2:kiln"})'), None, "names a reviewer script"),
            "normalized whitespace": (sha(" ".join(PRODUCT_SCRIPT.split())), None, "matches no executable"),
            "duplicate": (sha(PRODUCT_SCRIPT), pages(scripts_after=f"<script>{PRODUCT_SCRIPT}</script>"), "more than one inline product script"),
        }
        for label, (digest, page_set, expected) in cases.items():
            with self.subTest(label):
                data = registry()
                row(data, "kiln-rise")["trigger"]["scriptSha256"] = digest
                self.assertIn(expected, "\n".join(joins(data, page_set=page_set)))

    def test_surface_state_target_and_specimen_scope(self):
        cases = {
            "state": ({"state": "submitting"}, None, "not an approved state"),
            "target": ({"target": "1024"}, None, "not an approved target"),
            "surface": ({"surface": "UI-002"}, None, "is not the manifest surface"),
            "specimen absent from state": ({"state": "running"}, None, "does not resolve inside UI-001 state running"),
        }
        for label, (change, page_set, expected) in cases.items():
            with self.subTest(label):
                data = registry()
                row(data, "kiln-rise")["trigger"].update(change)
                self.assertIn(expected, "\n".join(joins(data, page_set=page_set)))
        stage = '<section class="kiln" data-specimen-variant="demo" data-specimen-state="final"></section>'
        doubled = pages()["index.html"].replace('data-responsive-target="390"><h1>', 'data-responsive-target="390">' + stage + "<h1>", 1)
        self.assertIn("specimen is ambiguous in UI-001 ready at 390", "\n".join(joins(page_set={"index.html": doubled})))
        only_wide = pages()["index.html"].replace('data-responsive-target="390"><h1>', 'data-responsive-target="390" data-x><h1>', 1)
        only_wide = re.sub(r'(data-responsive-target="390" data-x>[\s\S]*?)<section class="kiln"[\s\S]*?</section>', r"\1", only_wide, count=1)
        self.assertIn("does not resolve inside UI-001 state ready at target 390", "\n".join(joins(page_set={"index.html": only_wide})))
        data = registry()
        row(data, "kiln-rise")["trigger"]["target"] = "768"
        self.assertEqual([], joins(data, page_set={"index.html": only_wide}))


class SourceProvenanceTests(unittest.TestCase):
    RULE = "[data-ui-surface] :focus-visible{outline:3px solid var(--glow);outline-offset:2px}"

    def test_shared_focus_ring_needs_its_scope_on_the_specimen_path(self):
        self.assertIn(self.RULE, PRODUCT_CSS)
        self.assertEqual([], joins())
        for replacement, ok in ((".other :focus-visible{outline:3px solid}", False),
                                ("[data-ui-surface] .x :focus-visible{outline:3px solid}", False),
                                ("@media (min-width:1px){[data-ui-surface] :focus-visible{outline:3px solid}}", False),
                                ('[data-ui-route="/other"] :focus-visible{outline:3px solid}', False),
                                ('[data-ui-route="/kiln"] :focus-visible{outline:3px solid}', True),
                                ("section :focus-visible{outline:3px solid}", True)):
            with self.subTest(replacement):
                page_set = pages(css=PRODUCT_CSS.replace(self.RULE, replacement))
                found = "\n".join(joins(page_set=page_set, files=repo_files(page_set)))
                self.assertEqual(ok, ".field:focus-visible rule" not in found, found)
        legacy = registry()
        legacy["showcase"]["schema"], legacy["showcase"]["motion"], legacy["motionVariants"] = "ds-showcase/1", [], []
        self.assertIn(".field:focus-visible rule in approved CSS", "\n".join(joins(legacy)))

    def test_closed_native_details_cannot_be_rendered_open(self):
        for opened, expected in (("", True), (" open", False)):
            with self.subTest(opened=opened):
                menu = (f'<details class="lang"{opened} data-specimen-variant="default" data-specimen-state="open">'
                        "<summary>Language</summary><a href=\"#es\">Español</a></details>")
                page_set = {"index.html": pages()["index.html"].replace("<h1>Kiln two</h1>", menu + "<h1>Kiln two</h1>", 1)}
                data = registry()
                data["productComponents"] = {"LanguageMenu": {"states": ["open"]}}
                data["showcase"]["specimens"].append({"id": "lang-open", "subject": {"kind": "component", "name": "LanguageMenu"},
                                                      "axes": {}, "source": {"page": "index.html", "selector": ".lang",
                                                                             "variant": "default", "state": "open"}})
                data["showcase"]["states"].append({"subject": {"kind": "component", "name": "LanguageMenu"}, "state": "open",
                                                   "mode": "rendered", "specimen": "lang-open"})
                found = "\n".join(joins(data, page_set=page_set, files=repo_files(page_set)))
                self.assertEqual(expected, "closed <details> source node" in found, found)


class RenderTests(unittest.TestCase):
    def test_plates_mark_bound_copies_and_pin_every_script(self):
        document = render()
        frames = [html_lib.unescape(src) for attrs, src in re.findall(r'<iframe ([^>]*?) srcdoc="([^"]*)"></iframe>', document)
                  if "data-ds-runtime-frame" in attrs]
        self.assertEqual(3, len(frames))
        policy = html_lib.unescape(re.search(r'Content-Security-Policy" content="([^"]+)"', document).group(1))
        for script in (RUNTIME_FRAME, RUNTIME_GALLERY, PRODUCT_SCRIPT):
            digest = "'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"
            self.assertIn(digest, policy)
        for frame in frames:
            self.assertIn(INITIAL_MOUNT, frame)
            self.assertLess(frame.index(RUNTIME_FRAME), frame.index(PRODUCT_SCRIPT), "the head runtime precedes product source")
            self.assertEqual(1, frame.count(f"<script>{PRODUCT_SCRIPT}</script>"))
            self.assertEqual(2, len(re.findall(r'data-ds-motion-subject="(?:390|768)"', frame)))
            self.assertIn('<div class="kiln-side" aria-hidden="true"></div>', frame)
            self.assertNotIn("connectHifiReviewer({", frame)
        self.assertIn("render candidate", document)
        self.assertIn('[data-ui-surface] :focus-visible</code> rule', document)

    def test_legacy_showcase_output_has_no_runtime(self):
        from showcase_fixture import render_demo

        legacy = render_demo()[0]
        for marker in ("data-ds-runtime-frame", "ds-mount", RUNTIME_GALLERY[:40]):
            self.assertNotIn(marker, legacy)
        dsthree = json.dumps({"schema": "design-system/3", "product": "P", "tokens": {}}).encode()
        self.assertEqual(preview.render_preview(dsthree, b"m"), preview.render_view(dsthree, b"m", Path(".")))

    def test_render_view_runs_the_runtime_joins_against_repository_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = repo_files()
            for path, payload in files.items():
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                (root / path).write_bytes(payload)
            data = registry()
            data["sourceBindings"]["hifi"]["sha256"] = hashlib.sha256(files[HIFI]).hexdigest()
            payload = json.dumps(data).encode("utf-8")
            self.assertIn("data-ds-runtime-frame", preview.render_view(payload, b"# P\n", root))
            (root / "docs/design/evidence/mm-001-reduced.json").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "MM-001 reduced-motion evidence is missing or stale"):
                preview.render_view(payload, b"# P\n", root)
            stale = copy.deepcopy(data)
            row(stale, "belt-step")["trigger"]["scriptSha256"] = "1" * 64
            with self.assertRaisesRegex(ValueError, "scriptSha256 matches no executable"):
                preview.render_view(json.dumps(stale).encode("utf-8"), b"# P\n", root)


if __name__ == "__main__":
    unittest.main()
