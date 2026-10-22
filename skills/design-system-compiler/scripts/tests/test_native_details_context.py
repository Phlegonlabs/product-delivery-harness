"""ds-showcase/2 component plates keep a specimen's native <details> context.

Synthetic Ferry Desk fixture, not an approved product. The bound option sits in
a closed native disclosure with an absolutely positioned menu. Browser cases are
required when PDH_REQUIRE_BROWSER_TESTS=1.
"""

import base64
import copy
import hashlib
import html as html_lib
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
sys.path.append(str(TESTS.parents[2] / "ui-design-builder/scripts/tests"))

import design_system_gallery as gallery  # noqa: E402
import design_system_showcase as showcase  # noqa: E402
from design_system_gallery_assets import FRAME_RUNTIME, FRAME_RUNTIME_DISCLOSURE  # noqa: E402

BROWSER_TIMEOUT_SECONDS = 120
CSS = ("body{margin:0;font:16px/1.4 sans-serif}[data-hifi-canvas][data-hifi-target=\"390\"]{width:390px}"
       ".hd{display:flex;justify-content:flex-end;padding:8px}.lang{position:relative}"
       ".lang-btn{list-style:none;cursor:pointer;padding:8px;border:1px solid #333}.lang-btn::-webkit-details-marker{display:none}"
       ".lang[open]>.lang-btn{background:#222;color:#fff}"
       ".lang-menu{position:absolute;right:0;top:calc(100% + 6px);min-width:12rem;margin:0;padding:6px;list-style:none;background:#fff;border:1px solid #333}"
       ".lang-opt{display:flex;min-height:44px;align-items:center;padding:0 10px;color:#111;text-decoration:none}"
       ".lang-opt:hover,.lang-opt:focus-visible{background:rgb(200, 220, 240)}.lang-opt[aria-current=\"true\"]{font-weight:700}")
LOCALES = (("en", "English"), ("es", "Español"), ("ja", "日本語"))
SUMMARY = '<summary class="lang-btn"><span>Language</span> <span data-current>English</span></summary>'


def options():
    return "".join(
        f'<li><a class="lang-opt" role="button" href="index.html" hreflang="{code}"'
        + (' aria-current="true"' if code == "en" else "")
        + f' data-specimen-variant="locale" data-specimen-state="{"current" if code == "en" else "default"}">{label}</a></li>'
        for code, label in LOCALES)


MENU = f'<details class="lang">{SUMMARY}<ul class="lang-menu" aria-label="Language">{options()}</ul></details>'


def page(menu=MENU):
    manifest = json.dumps({"schema": "ui-hifi/2", "pages": [], "surfaces": [], "interactions": []})
    return ('<!doctype html><html lang="en"><head><title>Ferry Desk</title>'
            f"<style>{CSS}</style></head><body>"
            '<div data-hifi-canvas data-hifi-targets="390" data-hifi-target="390">'
            f'<main data-ui-surface="UI-001"><header class="hd"><nav>{menu}</nav></header><p>Sailings</p></main></div>'
            '<script>document.documentElement.setAttribute("data-product-ran", "1")</script>'
            f'<script id="ui-hifi-manifest" type="application/json">{manifest}</script></body></html>')


def registry(schema="ds-showcase/2"):
    subject = {"kind": "primitive", "name": "LanguageOption"}
    specimens = [{"id": f"option-{state}", "subject": subject, "axes": {"variants": "locale"},
                  "source": {"page": "index.html", "selector": ".lang-opt", "variant": "locale", "state": state}}
                 for state in ("default", "current")]
    states = [{"subject": subject, "state": "default", "mode": "rendered", "specimen": "option-default"},
              {"subject": subject, "state": "hover", "mode": "pseudo", "specimen": "option-default"},
              {"subject": subject, "state": "focus-visible", "mode": "pseudo", "specimen": "option-default"}]
    states += [{"subject": subject, "state": state, "mode": "not_applicable", "reason": f"Language links have no {state} look."}
               for state in ("active", "disabled")]
    return {"schema": "design-system/4", "product": "Ferry Desk (synthetic fixture)", "platform": "web",
            "viewports": [390, 768, 1024], "tokens": {}, "motionVariants": [], "productComponents": {},
            "primitives": {"LanguageOption": {"layer": "control", "class": "lang-opt", "variants": ["locale"]}},
            "sourceBindings": {}, "showcase": {"schema": schema, "specimens": specimens, "states": states, "motion": []}}


def render(pages=None, data=None):
    pages = pages or {"index.html": page()}
    data = data or registry()
    manifest = json.loads(showcase.MANIFEST_RE.search(pages["index.html"]).group("data"))
    resolved, problems = showcase.resolve(data, pages)
    if problems:
        raise ValueError("\n".join(problems))
    return gallery.render_gallery(data, b"{}", b"", pages, manifest, resolved, {"path": "hifi/index.html", "sha256": "0" * 64})


def frames(document):
    return {html_lib.unescape(attrs): html_lib.unescape(src)
            for attrs, src in re.findall(r'<iframe ([^>]*?) srcdoc="([^"]*)"></iframe>', document)}


def plate(document, state):
    return next(src for attrs, src in frames(document).items() if f'title="LanguageOption variants locale {state}"' in attrs)


def digest(script):
    return "'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"


def problems(pages, data=None):
    data = data or registry()
    return "\n".join(showcase.registry_findings(data) or showcase.resolve(data, pages)[1])


class NativeDetailsStaticTests(unittest.TestCase):
    def test_component_plate_keeps_the_closed_source_disclosure(self):
        document = render()
        for state, label in (("default", "Español"), ("current", "English")):
            with self.subTest(state=state):
                frame = plate(document, state)
                self.assertIn('<details class="lang">' + SUMMARY, frame, "closed, with the exact original summary")
                self.assertNotRegex(frame, r"<details[^>]*\bopen\b")
                self.assertEqual(3, frame.count('class="lang-opt"'), "sibling options are copied context")
                body = re.sub(r"<(script|style)\b[^>]*>[\s\S]*?</\1>", "", frame)
                self.assertEqual(1, body.count("data-ds-subject"), "one bound subject")
                subject = re.search(r"<a [^>]*data-ds-subject[^>]*>([^<]*)</a>", frame)
                self.assertEqual(label, subject.group(1))
                self.assertEqual(1, body.count('aria-current="true"'))
                self.assertIn('hreflang="en" aria-current="true" data-specimen-variant="locale" data-specimen-state="current"', body)
                self.assertIn(f"<script>{FRAME_RUNTIME_DISCLOSURE}</script>", frame)
                self.assertNotIn("data-product-ran", re.sub(r"<script>[\s\S]*?</script>", "", frame.split("</head>")[0]))
                self.assertEqual(1, len(re.findall(r"<script>", frame)), "only the pinned renderer runtime runs")
        policy = html_lib.unescape(re.search(r'Content-Security-Policy" content="([^"]+)"', document).group(1))
        self.assertIn(digest(FRAME_RUNTIME_DISCLOSURE), policy)
        self.assertIn("connect-src 'none'", policy)
        for attrs in frames(document):
            self.assertIn('sandbox="allow-scripts"', attrs)
            self.assertNotIn("allow-same-origin", attrs)

    def test_schema_one_and_plates_without_disclosures_keep_their_bytes(self):
        legacy = render(data=registry("ds-showcase/1"))
        frame = plate(legacy, "default")
        self.assertNotIn("<summary", frame)
        self.assertEqual(1, frame.count('class="lang-opt"'))
        self.assertNotIn(digest(FRAME_RUNTIME_DISCLOSURE), legacy)
        self.assertIn(f"<script>{FRAME_RUNTIME}</script>", frame)
        flat = page(f'<ul class="lang-menu">{options()}</ul>')
        plain = render({"index.html": flat})
        self.assertNotIn(digest(FRAME_RUNTIME_DISCLOSURE), plain)
        self.assertEqual(1, plate(plain, "default").count('class="lang-opt"'))
        from showcase_fixture import DEMO_DIR
        self.assertNotIn(FRAME_RUNTIME_DISCLOSURE[:400], (DEMO_DIR / "design-system-preview.html").read_text(encoding="utf-8"))

    def test_nested_disclosures_keep_every_controlling_summary(self):
        inner = f'<details class="more"><summary class="more-btn">More languages</summary><ul>{options()}</ul></details>'
        nested = page(f'<details class="lang">{SUMMARY}<div class="lang-menu">{inner}</div></details>')
        frame = plate(render({"index.html": nested}), "default")
        self.assertIn(SUMMARY, frame)
        self.assertIn('<summary class="more-btn">More languages</summary>', frame)
        self.assertEqual(2, frame.count("<details"))
        self.assertNotRegex(frame, r"<details[^>]*\bopen\b")

    def test_malformed_or_ambiguous_context_fails_explicitly(self):
        inner = f'<details class="more"><ul>{options()}</ul></details>'
        cases = {
            "missing summary": page(MENU.replace(SUMMARY, "")),
            "two summaries": page(MENU.replace(SUMMARY, SUMMARY * 2)),
            "unclosed details": page(MENU.replace("</details>", "")),
            "nested missing summary": page(f'<details class="lang">{SUMMARY}<div class="lang-menu">{inner}</div></details>'),
            "state view inside": page(MENU.replace("<ul", '<div data-hifi-state-view="ready"><ul').replace("</ul>", "</ul></div>")),
        }
        for label, source in cases.items():
            with self.subTest(label):
                found = problems({"index.html": source})
                self.assertRegex(found, r"showcase specimen option-default native <details> context")
                with self.assertRaisesRegex(ValueError, "native <details> context"):
                    render({"index.html": source})
                self.assertNotRegex(problems({"index.html": source}, registry("ds-showcase/1")), "native <details>")

    def test_context_earns_no_coverage_and_open_claims_still_fail(self):
        # The default plate copies a sibling annotated "current", yet only a registry row covers that value.
        sibling = page().replace('data-specimen-variant="locale" data-specimen-state="current"',
                                 'data-specimen-variant="current" data-specimen-state="default"')
        data = registry()
        data["showcase"]["specimens"] = [row for row in data["showcase"]["specimens"] if row["id"] != "option-current"]
        data["primitives"]["LanguageOption"]["variants"] = ["locale", "current"]
        self.assertIn('data-specimen-variant="current"', plate(render({"index.html": sibling}, copy.deepcopy(data)), "default"))
        self.assertIn("missing primitive LanguageOption variants=current", problems({"index.html": sibling}, data))
        data = registry()
        data["showcase"]["states"].append({"subject": {"kind": "primitive", "name": "LanguageOption"}, "state": "open",
                                           "mode": "rendered", "specimen": "option-default"})
        data["showcase"]["specimens"][0]["source"]["state"] = "open"
        opened = page(MENU.replace('data-specimen-state="default"', 'data-specimen-state="open"', 1))
        self.assertIn("closed <details> source node", "\n".join(showcase.resolve(data, {"index.html": opened})[1]))


class NativeContextScriptGuardStaticTests(unittest.TestCase):
    def test_script_sibling_is_rejected_before_rendering(self):
        body = 'document.documentElement.setAttribute("data-product-ran", "1")'
        menu = MENU.replace("</ul>", f"<script>{body}</script></ul>")
        source = page(menu)
        tree = showcase.SourceTree(source)
        node = tree.first(lambda item: showcase.selector_matches(item, ".lang-opt")
                          and item["map"].get("data-specimen-state") == "default")
        context, failure = showcase.disclosure_context(tree, node)
        self.assertIsNone(context)
        self.assertRegex(failure, r"unsupported script descendant")
        self.assertRegex("\n".join(showcase.resolve(registry(), {"index.html": source})[1]),
                         r"unsupported script descendant")
        self.assertIn(body, showcase.product_scripts(source, with_controls=True))
        self.assertIn(digest(body), gallery.content_security_policy([body]))

    def test_guard_rejects_executable_and_inert_script_descendants(self):
        executable = 'document.documentElement.setAttribute("data-script-ran", "1")'
        inert = '<script type="application/json">{}</script>'
        nested = MENU.replace("</ul>", f"<script>{executable}</script></ul>")
        deep = MENU.replace("</ul>",
                            f'<details class="more"><summary>More</summary><script>{executable}</script>'
                            "</details></ul>")
        data_script = MENU.replace("</ul>", f"{inert}</ul>")
        template_script = MENU.replace(
            "</ul>", f'<template><script>{executable}</script></template></ul>')
        for label, source in (("sibling", nested), ("nested", deep),
                              ("data script", data_script), ("template script", template_script)):
            with self.subTest(label):
                page_source = page(source)
                found = problems({"index.html": page_source})
                self.assertRegex(found, r"script descendant")
                with self.assertRaisesRegex(ValueError, "script descendant"):
                    render({"index.html": page_source})

    def test_schema_one_does_not_expand_or_copy_the_script_sibling(self):
        body = 'document.documentElement.setAttribute("data-script-ran", "1")'
        source = page(MENU.replace("</ul>", f"<script>{body}</script></ul>"))
        data = registry("ds-showcase/1")
        resolved, issues = showcase.resolve(data, {"index.html": source})
        self.assertEqual([], issues)
        frame = plate(render({"index.html": source}, data), "default")
        self.assertNotIn(f"<script>{body}</script>", frame)
        self.assertEqual(1, frame.count('class="lang-opt"'))


def _playwright():
    from test_reviewer_browser import playwright_module  # shared discovery convention

    node = shutil.which("node")
    return node, playwright_module(node) if node else None


BROWSER = r"""
const [,, url, module] = process.argv;
const {chromium} = require(module);
(async () => {
  const browser = await chromium.launch();
  const r = {errors: [], requests: [], popups: []};
  try {
    const context = await browser.newContext({viewport: {width: 1280, height: 900}});
    const page = await context.newPage();
    page.on("console", message => { if (message.type() === "error") r.errors.push(message.text()); });
    page.on("pageerror", error => r.errors.push(String(error)));
    page.on("popup", popup => r.popups.push(popup.url()));
    context.on("request", request => { if (!/^(file|about|data):/.test(request.url())) r.requests.push(request.url()); });
    await page.goto(url);
    await page.waitForTimeout(800);
    const host = await page.$('iframe[title="LanguageOption variants locale default"]');
    const frame = await host.contentFrame();
    const read = () => frame.evaluate(() => {
      const details = document.querySelector("details.lang"), subject = document.querySelector("[data-ds-subject]");
      const inside = [...document.querySelectorAll(".lang-opt")].every(item => { const box = item.getBoundingClientRect();
        return box.width > 0 && box.left >= 0 && box.top >= 0 && box.right <= innerWidth && box.bottom <= innerHeight; });
      return {open: details.open, summary: details.querySelector(":scope > summary").textContent,
        subjects: document.querySelectorAll("[data-ds-subject]").length, visible: subject.checkVisibility(),
        current: document.querySelector('[aria-current="true"]').textContent, inside, ran: document.documentElement.hasAttribute("data-product-ran"),
        background: getComputedStyle(subject).backgroundColor, focusVisible: subject.matches(":focus-visible"),
        menuBottom: Math.ceil(document.querySelector(".lang-menu").getBoundingClientRect().bottom)};
    });
    const height = async () => Math.round((await host.boundingBox()).height);
    r.closed = await read(); r.closedHeight = await height();
    await frame.click("summary.lang-btn");
    await page.waitForTimeout(400);
    r.opened = await read(); r.openHeight = await height();
    await frame.hover("[data-ds-subject]");
    await page.waitForTimeout(100);
    r.hovered = await read();
    await frame.focus("summary.lang-btn");
    await page.keyboard.press("Enter");
    await page.waitForTimeout(400);
    r.keyClosed = await read(); r.keyClosedHeight = await height();
    await page.keyboard.press("Space");
    await page.waitForTimeout(300);
    r.keyOpened = await read();
    await page.mouse.move(0, 0);
    await page.keyboard.press("Tab"); await page.keyboard.press("Tab");
    r.focused = await read();
    await frame.click("[data-ds-subject]");
    await page.waitForTimeout(300);
    r.stayed = frame.url();
    r.status = await page.$eval(`[data-ds-status="${await host.getAttribute("data-ds-frame")}"]`, item => item.textContent);
  } finally { await browser.close(); }
  console.log(JSON.stringify(r));
})().catch(error => { console.error(error); process.exit(1); });
"""


class NativeDetailsBrowserTests(unittest.TestCase):
    def test_native_summary_opens_and_closes_without_clipping(self):
        node, module = _playwright()
        if not node or not module:
            if os.environ.get("PDH_REQUIRE_BROWSER_TESTS") == "1":
                self.fail("Node.js and PLAYWRIGHT_MODULE are required for the native details browser test")
            self.skipTest("Node Playwright is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "preview.html"
            target.write_text(render(), encoding="utf-8")
            try:
                completed = subprocess.run([node, "-", target.as_uri(), module], input=BROWSER, text=True, encoding="utf-8",
                                           capture_output=True, timeout=BROWSER_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired as error:
                self.fail(f"native details browser check exceeded {BROWSER_TIMEOUT_SECONDS}s: {error}")
        self.assertEqual(0, completed.returncode, completed.stderr[-3000:])
        r = json.loads(completed.stdout.strip().splitlines()[-1])
        self.assertEqual(([], [], []), (r["errors"], r["requests"], r["popups"]))
        closed, opened = r["closed"], r["opened"]
        self.assertEqual((False, False, 1, "English", False), (closed["open"], closed["visible"], closed["subjects"],
                                                               closed["current"], closed["ran"]))
        self.assertEqual("Language English", closed["summary"])
        self.assertEqual((True, True, True), (opened["open"], opened["visible"], opened["inside"]))
        self.assertGreater(r["openHeight"], r["closedHeight"])
        self.assertGreaterEqual(r["openHeight"], opened["menuBottom"])
        self.assertEqual("rgb(200, 220, 240)", r["hovered"]["background"])
        self.assertNotEqual(opened["background"], r["hovered"]["background"])
        self.assertFalse(r["keyClosed"]["open"])
        self.assertEqual(r["closedHeight"], r["keyClosedHeight"])
        self.assertTrue(r["keyOpened"]["open"])
        self.assertTrue(r["focused"]["focusVisible"], r["focused"])
        self.assertEqual("rgb(200, 220, 240)", r["focused"]["background"])
        self.assertEqual((1, "English"), (r["focused"]["subjects"], r["focused"]["current"]))
        self.assertEqual("about:srcdoc", r["stayed"])
        self.assertIn("index.html", r["status"])


if __name__ == "__main__":
    unittest.main()
