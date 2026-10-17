"""Focused tests for ui-direction-review/1 assembly and its reviewer shim."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import assemble_ui_review
import check_ui_design_contract as ui_contract_checker
import check_wireframe_html
import direction_review
import reviewer_shell
import ui_design_v3

TEMPLATES = SCRIPTS_DIR.parents[0] / "assets/templates"
FILES = ("vd-01.html", "vd-02.html", "vd-03.html")
CASES = [
    {"id": "primary", "surface": "UI-001", "platform": "web", "targetFamily": "viewports",
     "widths": {"390": 390, "1200": 1200}},
    {"id": "stress", "surface": "UI-004", "platform": "ios", "targetFamily": "sizeClasses",
     "widths": {"compact": 390, "regular": 820}},
]


LOCAL_PAGE_CSP = check_wireframe_html.REQUIRED_HIFI_CSP.replace("navigate-to 'none'", "navigate-to 'self'")


def source_html(name: str, *, csp: str = LOCAL_PAGE_CSP, extra: str = "",
                views: tuple[str, ...] = ("primary", "stress")) -> str:
    body = "".join(
        f'<section data-direction-case-view="{view}" data-ui-surface="UI-{view}"><h1>{name} {view}</h1></section>'
        for view in views
    )
    return (f'<!doctype html><html lang="en"><head><meta http-equiv="Content-Security-Policy" content="{csp}">'
            f"<title>{name}</title><style>.product-{name}{{color:#123}}</style>{extra}</head>"
            f'<body><main data-hifi-canvas class="product-{name}">{body}</main></body></html>')


class DirectionAssemblyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.out = self.root / "docs/design/directions/round-1"
        self.pages = {file: source_html(file[:-5]) for file in FILES}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def profile(self) -> dict:
        return {
            "schema": "ui-direction-review/1",
            "round": "round-1",
            "directions": [
                {"id": f"VD-R1-0{index}", "file": file,
                 "sourceSha256": hashlib.sha256(self.pages[file].encode("utf-8")).hexdigest()}
                for index, file in enumerate(self.pages, 1)
            ],
            "cases": copy.deepcopy(CASES),
        }

    def run_assembly(self, profile: dict | None = None, *, output: Path | None = None, overwrite: bool = False):
        for file, html in self.pages.items():
            (self.sources / file).write_text(html, encoding="utf-8", newline="")
        manifest = self.root / "direction-review.json"
        manifest.write_text(json.dumps(profile or self.profile()), encoding="utf-8")
        return assemble_ui_review.assemble_direction(
            manifest, [f"{file}={self.sources / file}" for file in self.pages], output or self.out,
            overwrite=overwrite,
        )

    def assert_rejected(self, expected: str, profile: dict | None = None, **options) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            self.run_assembly(profile, **options)
        self.assertIn(expected, stderr.getvalue())
        self.assertFalse(self.out.exists(), "a rejected assembly must not write studies")

    def test_assembles_three_distinct_studies_without_an_entry_or_token_panels(self) -> None:
        paths = self.run_assembly()
        self.assertEqual([str(self.out / file) for file in FILES], paths)
        self.assertEqual(sorted(FILES), sorted(path.name for path in self.out.iterdir()))
        studies = {file: (self.out / file).read_text(encoding="utf-8") for file in FILES}
        self.assertEqual(3, len(set(studies.values())))
        for file, html in studies.items():
            self.assertEqual([], ui_design_v3.direction_review_findings(html, f"docs/design/directions/round-1/{file}"))
            self.assertEqual([], reviewer_shell.shared_css_drift(html))
            self.assertIn(reviewer_shell.runtime_block(), html)
            self.assertNotIn("<script>connectHifiReviewer", html)
            self.assertNotIn('data-hifi-panel="', html)
            self.assertNotIn("data-hifi-review-view=", html)
            self.assertNotIn('href="index.html', html)
            # The author's product DOM is carried through byte for byte.
            product = self.pages[file].split("<body>", 1)[1].split("</body>", 1)[0]
            self.assertIn(product, html)
            for index, other in enumerate(FILES, 1):
                current = ' aria-current="page"' if other == file else ""
                self.assertIn(
                    f'<a href="{other}" data-direction-file="{other}" data-direction-id="VD-R1-0{index}"{current}>'
                    f"VD-R1-0{index}<small>{other}</small></a>", html)
            shell = html.split("<!-- reviewer:start -->", 1)[1].split("<!-- reviewer:end -->", 1)[0]
            self.assertEqual(1, shell.count('aria-current="page"'))

    def test_each_case_exposes_only_its_own_approved_targets(self) -> None:
        shell = direction_review.build_shell(self.profile(), "vd-02.html")
        self.assertIn('data-hifi-target-control="390" data-direction-case="primary" data-direction-width="390" aria-pressed="true">390px<', shell)
        self.assertIn('data-hifi-target-control="1200" data-direction-case="primary" data-direction-width="1200" aria-pressed="false">1200px<', shell)
        self.assertIn('data-hifi-target-control="compact" data-direction-case="stress" data-direction-width="390" aria-pressed="false" hidden>compact<small>390px</small>', shell)
        self.assertIn('data-hifi-target-control="regular" data-direction-case="stress" data-direction-width="820" aria-pressed="false" hidden>', shell)
        self.assertEqual(4, shell.count("data-hifi-target-control="))
        self.assertIn('data-hifi-state-control="stress" data-hifi-state-surface="UI-004" data-direction-platform="ios" data-direction-family="sizeClasses" aria-pressed="false">', shell)
        self.assertIn('data-hifi-platform="web"', shell)
        self.assertIn("round-1, 3 studies, 2 cases", shell)

    def test_one_study_is_accepted_and_two_are_not(self) -> None:
        self.pages = {"vd-01.html": self.pages["vd-01.html"]}
        self.assertEqual([str(self.out / "vd-01.html")], self.run_assembly())
        self.assertIn("round-1, 1 study, 2 cases", (self.out / "vd-01.html").read_text(encoding="utf-8"))
        profile = self.profile()
        profile["directions"].append(dict(profile["directions"][0], id="VD-R1-02", file="vd-02.html", sourceSha256="0" * 64))
        self.assertIn("directions must list three studies, or one by explicit owner choice",
                      direction_review.profile_findings(profile))

    def test_profile_rejects_inexact_platform_families_and_width_maps(self) -> None:
        def findings(change) -> str:
            profile = self.profile()
            change(profile)
            return " | ".join(direction_review.profile_findings(profile))

        self.assertEqual([], direction_review.profile_findings(self.profile()))
        self.assertIn("platform web requires targetFamily viewports",
                      findings(lambda p: p["cases"][0].update(targetFamily="sizeClasses", widths={"compact": 390})))
        self.assertIn("platform ios requires targetFamily sizeClasses",
                      findings(lambda p: p["cases"][1].update(targetFamily="viewports", widths={"390": 390})))
        self.assertIn("viewport '390' must equal its own integer pixel width",
                      findings(lambda p: p["cases"][0]["widths"].update({"390": 400})))
        self.assertIn("size class 'compact' must be a named target",
                      findings(lambda p: p["cases"][1]["widths"].update(compact=0)))
        self.assertIn("size class 'compact' must be a named target",
                      findings(lambda p: p["cases"][1]["widths"].update(compact=True)))
        self.assertIn("widths must map every approved target", findings(lambda p: p["cases"][0].update(widths={})))
        self.assertIn("must contain exactly id, surface, platform, targetFamily and widths",
                      findings(lambda p: p["cases"][0].pop("surface")))
        self.assertIn("cases must name each review case once", findings(lambda p: p["cases"][1].update(id="primary")))
        self.assertIn("directions must name each study file once",
                      findings(lambda p: p["directions"][1].update(file="VD-01.html")))
        self.assertIn("file must be the study's actual <name>.html filename",
                      findings(lambda p: p["directions"][0].update(file="../vd-01.html")))
        self.assertIn("exactly schema, round, directions and cases", findings(lambda p: p.update(pages=[])))
        self.assertIn("must be schema ui-direction-review/1", findings(lambda p: p.update(schema="ui-hifi/2")))

    def test_stale_hash_csp_resources_and_product_structure_fail_before_any_write(self) -> None:
        profile = self.profile()
        self.pages["vd-02.html"] += "<!-- edited after the profile was recorded -->"
        self.assert_rejected("declared source is stale: vd-02.html", profile)

        self.pages["vd-02.html"] = source_html("vd-02", csp="default-src 'self'")
        self.assert_rejected("HiFi CSP policy")
        self.pages["vd-02.html"] = source_html("vd-02", csp=check_wireframe_html.REQUIRED_HIFI_CSP)
        self.assert_rejected("must use the exact local-page CSP policy")
        self.pages["vd-02.html"] = source_html("vd-02").replace("<h1>", '<a href="https://example.invalid/">x</a><h1>', 1)
        self.assert_rejected("must not contain active external or executable surfaces")
        self.pages["vd-02.html"] = source_html("vd-02", extra='<link rel="stylesheet" href="https://example.invalid/a.css">')
        self.assert_rejected("must not load linked, imported or external resources")
        self.pages["vd-02.html"] = source_html("vd-02", views=("primary",))
        self.assert_rejected("exactly one [data-direction-case-view] per review case: primary, stress")
        self.pages["vd-02.html"] = source_html("vd-02").replace(" data-hifi-canvas", "")
        self.assert_rejected("exactly one author-owned [data-hifi-canvas]")
        self.pages["vd-02.html"] = source_html("vd-02").replace("<body>", "<body><aside data-hifi-reviewer-shell></aside>")
        self.assert_rejected("already contains reviewer chrome")
        self.pages["vd-02.html"] = self.pages["vd-01.html"]
        self.assert_rejected("directions must name each study source once")

    def test_sources_must_match_the_profile_and_never_alias_outputs(self) -> None:
        profile = self.profile()
        self.pages["extra.html"] = source_html("extra")
        self.assert_rejected("declared sources must exactly match the profile's study filenames", profile)
        del self.pages["extra.html"]
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            self.run_assembly(output=self.sources, overwrite=True)
        self.assertIn("output destination aliases an input", stderr.getvalue())
        for file in FILES:
            self.assertEqual(self.pages[file], (self.sources / file).read_text(encoding="utf-8"))

    def test_overwrite_rejects_hardlinked_outputs_and_preserves_inputs(self) -> None:
        self.pages = {"vd-01.html": self.pages["vd-01.html"]}
        for file, html in self.pages.items():
            (self.sources / file).write_text(html, encoding="utf-8", newline="")
        profile = self.profile()
        manifest = self.root / "direction-review.json"
        manifest.write_text(json.dumps(profile), encoding="utf-8")
        self.out.mkdir(parents=True)
        source = self.sources / "vd-01.html"
        hard_output = self.out / "vd-01.html"
        os.link(source, hard_output)
        source_bytes = source.read_bytes()
        output_bytes = hard_output.read_bytes()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            assemble_ui_review.assemble_direction(
                manifest, [f"vd-01.html={source}"], self.out, overwrite=True)
        self.assertIn("hard links an input", stderr.getvalue())
        self.assertEqual(source_bytes, source.read_bytes())
        self.assertEqual(output_bytes, hard_output.read_bytes())
        self.assertTrue(hard_output.samefile(source))

    def test_overwrite_rejects_a_hardlinked_manifest_output(self) -> None:
        self.pages = {"vd-01.html": self.pages["vd-01.html"]}
        for file, html in self.pages.items():
            (self.sources / file).write_text(html, encoding="utf-8", newline="")
        profile = self.profile()
        manifest = self.root / "direction-review.json"
        manifest.write_text(json.dumps(profile), encoding="utf-8")
        self.out.mkdir(parents=True)
        hard_output = self.out / "vd-01.html"
        os.link(manifest, hard_output)
        manifest_bytes = manifest.read_bytes()
        output_bytes = hard_output.read_bytes()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            assemble_ui_review.assemble_direction(
                manifest, [f"vd-01.html={self.sources / 'vd-01.html'}"], self.out,
                overwrite=True)
        self.assertIn("hard links an input", stderr.getvalue())
        self.assertEqual(manifest_bytes, manifest.read_bytes())
        self.assertEqual(output_bytes, hard_output.read_bytes())
        self.assertTrue(hard_output.samefile(manifest))

    def test_overwrite_replaces_a_hardlinked_output_entry_without_truncating_the_link(self) -> None:
        self.pages = {"vd-01.html": self.pages["vd-01.html"]}
        unrelated = self.root / "elsewhere" / "unrelated.html"
        unrelated.parent.mkdir()
        unrelated.write_bytes(b"unrelated study bytes")
        self.out.mkdir(parents=True)
        hard_output = self.out / "vd-01.html"
        try:
            os.link(unrelated, hard_output)
        except OSError:
            self.skipTest("hard links are unavailable")
        self.run_assembly(overwrite=True)
        rendered = hard_output.read_bytes()
        self.assertNotEqual(b"unrelated study bytes", rendered)
        self.assertTrue(ui_design_v3.has_direction_review_profile(rendered.decode("utf-8")))
        self.assertEqual(b"unrelated study bytes", unrelated.read_bytes())
        self.assertFalse(hard_output.samefile(unrelated))

    def test_existing_studies_are_kept_unless_overwrite_is_explicit(self) -> None:
        self.run_assembly()
        kept = (self.out / "vd-01.html").read_bytes()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            self.run_assembly()
        self.assertIn("output files already exist; pass --overwrite", stderr.getvalue())
        self.assertEqual(kept, (self.out / "vd-01.html").read_bytes())
        self.run_assembly(overwrite=True)
        self.assertEqual(kept, (self.out / "vd-01.html").read_bytes(), "assembly must be reproducible")

    def test_strict_profile_is_separate_from_readable_older_studies(self) -> None:
        older = source_html("older", csp=check_wireframe_html.REQUIRED_HIFI_CSP)
        self.assertEqual([], ui_design_v3.study_html_findings(older, "older.html"))
        linked = older.replace("<h1>", '<a href="vd-02.html">x</a><h1>', 1)
        self.assertIn("active external or executable surfaces",
                      " ".join(ui_design_v3.study_html_findings(linked, "older.html")))
        self.assertFalse(ui_design_v3.has_direction_review_profile(older))
        self.assertIn("must embed exactly one ui-direction-review/1 profile",
                      " ".join(ui_design_v3.direction_review_findings(older, "older.html")))

        self.run_assembly()
        study = (self.out / "vd-01.html").read_text(encoding="utf-8")
        self.assertTrue(ui_design_v3.has_direction_review_profile(study))
        # The older check is unchanged, so a checker must route profiled studies to the strict one.
        self.assertNotEqual([], ui_design_v3.study_html_findings(study, "vd-01.html"))

        def strict(html: str, path: str = "vd-01.html") -> str:
            return " | ".join(ui_design_v3.direction_review_findings(html, path))

        self.assertIn("reviewer shell must exactly match its profile",
                      strict(study.replace('data-direction-width="1200"', 'data-direction-width="1440"')))
        self.assertIn("reviewer shell must exactly match its profile",
                      strict(study.replace('<a href="vd-02.html"', '<a href="index.html"')))
        self.assertIn("exact shared runtime and direction shim", strict(study.replace("selectCase(id)", "selectCase(x)")))
        self.assertIn("exact direction reviewer styles", strict(study.replace("display:none!important}\n[data-hifi-review-mode", "display:block}\n[data-hifi-review-mode", 1)))
        self.assertIn("REVIEWER_SHARED.css", strict(study.replace("--review-accent:#2557a7", "--review-accent:#ff0000")))
        self.assertIn("not one of its profile's actual study filenames", strict(study, "renamed.html"))
        self.assertIn("viewport '390' must equal", strict(study.replace('"390":390', '"390":391')))

    def test_command_line_defaults_to_hifi_and_selects_direction(self) -> None:
        self.assertEqual("hifi", assemble_ui_review.parse_args(["--manifest", "m", "--source", "a=b", "--output-dir", "o"]).mode)
        for file, html in self.pages.items():
            (self.sources / file).write_text(html, encoding="utf-8", newline="")
        manifest = self.root / "direction-review.json"
        manifest.write_text(json.dumps(self.profile()), encoding="utf-8")
        arguments = ["--mode", "direction", "--manifest", str(manifest), "--output-dir", str(self.out)]
        for file in FILES:
            arguments += ["--source", f"{file}={self.sources / file}"]
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(0, assemble_ui_review.main(arguments))
        self.assertIn("PASS assembled", stdout.getvalue())
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            assemble_ui_review.main(arguments[2:])
        self.assertIn("the entry page index.html is required", stderr.getvalue())

    def test_contract_routes_profiled_studies_and_keeps_legacy_checks(self) -> None:
        self.run_assembly()
        name = FILES[0]
        path = f"docs/design/directions/round-1/{name}"
        profiled = (self.out / name).read_text(encoding="utf-8")
        self.assertTrue(ui_design_v3.has_direction_review_profile(profiled))
        self.assertNotEqual([], ui_design_v3.study_html_findings(profiled, name))

        def route(html: str, sha256: str, *, study_path: str = path) -> list[str]:
            style = f"""### Direction comparison

| Direction | UI surface | State | Target | Scenario | Content basis | Screenshot | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VD-R1-01 | UI-001 | ready | 390 | primary | Approved copy | docs/design/directions/primary.png @ sha256:{'a' * 64} | Same case |

### Direction studies

| Direction | Study | Author | Self-check by | Self-check |
| --- | --- | --- | --- | --- |
| VD-R1-01 | {study_path} @ sha256:{sha256} | Author | Author | pass |
"""
            problems: list[str] = []
            ui_contract_checker._resolve_direction_studies(style, self.root, problems)
            return problems

        self.assertEqual([], route(profiled, hashlib.sha256((self.out / name).read_bytes()).hexdigest()))
        edited = profiled.replace('<a href="vd-02.html"', '<a href="index.html"', 1)
        (self.out / name).write_text(edited, encoding="utf-8", newline="")
        self.assertIn("reviewer shell must exactly match its profile", " ".join(
            route(edited, hashlib.sha256((self.out / name).read_bytes()).hexdigest())))

        legacy_dir = self.root / "docs/design/directions/round-0"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_path = legacy_dir / "legacy.html"
        linked = source_html("older", csp=check_wireframe_html.REQUIRED_HIFI_CSP).replace(
            "<h1>", '<a href="https://example.invalid/">x</a><h1>', 1)
        legacy_path.write_text(linked, encoding="utf-8", newline="")
        self.assertFalse(ui_design_v3.has_direction_review_profile(linked))
        self.assertIn("must not contain active external or executable surfaces", " ".join(route(
            linked, hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
            study_path="docs/design/directions/round-0/legacy.html")))

    def test_profile_cases_join_approved_scope_without_state_coverage(self) -> None:
        scope = {
            "captureMode": "mixed",
            "surfaces": [
                {"id": "UI-001", "captureMode": "hosted-browser", "stackSemantics": {"platform": "web"},
                 "responsive": {"kind": "viewports", "targets": [390, 1200]}},
                {"id": "UI-004", "captureMode": "native", "stackSemantics": {"platform": "ios"},
                 "responsive": {"kind": "sizeClasses", "targets": ["compact", "regular"]}},
            ],
        }
        profile = self.profile()
        self.assertEqual([], ui_contract_checker._direction_profile_scope_findings(
            f'<script id="ui-direction-review" type="application/json">{json.dumps(profile)}</script>',
            "study.html", scope))

        mutations = (
            (lambda case: case.update(surface="UI-999"), "names a case outside Approved target scope", True),
            (lambda case: case.update(platform="android"), "uses a platform outside Approved target scope", False),
            (lambda case: case.update(targetFamily="sizeClasses"), "uses the wrong target family", False),
            (lambda case: case.update(widths={"390": 390}), "uses targets outside Approved target scope", False),
        )
        for mutate, expected, platform_gap in mutations:
            changed = copy.deepcopy(profile)
            mutate(changed["cases"][0])
            findings = ui_contract_checker._direction_profile_scope_findings(
                f'<script id="ui-direction-review" type="application/json">{json.dumps(changed)}</script>',
                "study.html", scope)
            self.assertIn(expected, " ".join(findings))
            if platform_gap:
                self.assertIn("every platform", " ".join(findings))


class SharedReviewerBytesTests(unittest.TestCase):
    def test_hifi_runtime_injection_keeps_its_bytes(self) -> None:
        expected = (
            "<html><body><p>x</p><!-- hifi-reviewer:runtime:start -->\n" + reviewer_shell.runtime_source()
            + "\n<!-- hifi-reviewer:runtime:end -->\n<script>connectHifiReviewer()</script>\n</body></html>"
        )
        self.assertEqual(expected, reviewer_shell.inject_runtime("<html><body><p>x</p></body></html>"))

    def test_direction_styles_only_use_the_shared_reviewer_palette(self) -> None:
        css = direction_review.style_block()
        self.assertNotRegex(css, r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(")
        self.assertNotIn("--review-", css.replace("var(--review-", ""))
        for line in css.splitlines()[2:-2]:
            self.assertTrue(line.startswith('[data-hifi-review-mode="direction"] '), line)
        shared = (TEMPLATES / "REVIEWER_SHARED.css").read_text(encoding="utf-8")
        hifi = (TEMPLATES / "HIFI_REVIEWER.template.html").read_text(encoding="utf-8")
        self.assertIn(shared.rstrip(), hifi)
        self.assertNotIn("direction", shared)
        self.assertNotIn("direction", hifi)


class DirectionShimRuntimeTests(unittest.TestCase):
    def test_case_switching_validates_targets_through_the_core_runtime(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const cut=(file,id)=>fs.readFileSync(file,'utf8').split('<script id="'+id+'">')[1].split('</script>')[0];
const context={window:{}};
vm.createContext(context);
vm.runInContext(cut(process.argv[2],'hifi-reviewer-runtime'),context);
vm.runInContext(cut(process.argv[3],'direction-reviewer-runtime'),context);
const cases=[
  {id:'primary',surface:'UI-001',platform:'web',family:'viewports',targets:['390','1200'],widths:{'390':390,'1200':1200}},
  {id:'dense',surface:'UI-002',platform:'web',family:'viewports',targets:['390','768'],widths:{'390':390,'768':768}},
  {id:'stress',surface:'UI-004',platform:'ios',family:'sizeClasses',targets:['compact','regular'],widths:{compact:390,regular:820}}];
const memory=new Map(),storage={getItem:k=>memory.has(k)?memory.get(k):null,setItem:(k,v)=>memory.set(k,String(v))};
const seen=[];
const make=()=>context.window.createDirectionReviewerRuntime({cases,storage,packageId:'ui-direction-review/1:test',onChange:s=>seen.push(s)});
const first=make();
assert.deepStrictEqual(JSON.parse(JSON.stringify(first.snapshot())),{case:'primary',surface:'UI-001',platform:'web',family:'viewports',target:'390',width:390,targets:['390','1200']});
assert.strictEqual(first.selectTarget('1200').width,1200);
assert.throws(()=>first.selectTarget('compact'),/not approved for case primary/);
assert.throws(()=>first.selectTarget('768'),/not approved for case primary/);
assert.throws(()=>first.selectCase('missing'),/Unknown direction review case/);
// A mixed native case exposes only its own size classes and its own pixel widths.
let native=first.selectCase('stress');
assert.deepStrictEqual([native.target,native.width,native.platform,native.family,native.targets.join()],['compact',390,'ios','sizeClasses','compact,regular']);
assert.throws(()=>first.selectTarget('1200'),/not approved for case stress/);
assert.strictEqual(first.selectTarget('regular').width,820);
// Each case remembers its own target; an unsupported carried target falls back to the case's first.
assert.strictEqual(first.selectCase('primary').target,'1200');
assert.strictEqual(first.selectCase('dense').target,'390');
assert.strictEqual(first.selectCase('stress').target,'regular');
assert.strictEqual(seen[seen.length-1].case,'stress');
// A sibling study in the same session opens on the same case and target.
const sibling=make().snapshot();
assert.deepStrictEqual([sibling.case,sibling.target,sibling.width],['stress','regular',820]);
// Unusable storage still yields a working first case.
const broken={getItem(){throw Error('denied')},setItem(){throw Error('denied')}};
const isolated=context.window.createDirectionReviewerRuntime({cases,storage:broken,packageId:'x'});
assert.strictEqual(isolated.selectCase('dense').target,'390');
assert.throws(()=>context.window.createDirectionReviewerRuntime({cases:[]}),/at least one case/);
'''
        result = subprocess.run(
            [node, "-", str(TEMPLATES / "HIFI_REVIEWER.template.html"), str(TEMPLATES / "DIRECTION_REVIEWER.template.html")],
            input=script, capture_output=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
