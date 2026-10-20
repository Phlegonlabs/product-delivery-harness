"""An open native disclosure keeps its source paint inside the ds-showcase/2 plate.

Synthetic Ferry Desk fixture from test_native_details_context, with a solid offset
menu shadow and an outset option focus ring in probe colors. The browser case
measures painted pixels of the frame, not element boxes. It is required when
PDH_REQUIRE_BROWSER_TESTS=1.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))

from test_native_details_context import CSS, _playwright, page, render  # noqa: E402

BROWSER_TIMEOUT_SECONDS = 120
SHADOW = 6
PAINT = (CSS.replace("border:1px solid #333}.lang-opt{", f"border:1px solid #333;box-shadow:{SHADOW}px {SHADOW}px 0 rgb(255, 0, 0)}}.lang-opt{{")
         + ".lang-opt:focus-visible{outline:3px solid rgb(0, 0, 255);outline-offset:3px}")
if PAINT.count("rgb(255, 0, 0)") != 1:
    raise RuntimeError("test_native_details_context CSS changed; update the paint fixture")

BROWSER = r"""
const [,, url, module] = process.argv;
const {chromium} = require(module);
(async () => {
  const browser = await chromium.launch();
  const r = {errors: [], requests: [], popups: []};
  try {
    const context = await browser.newContext({viewport: {width: 1280, height: 900}, deviceScaleFactor: 1});
    const page = await context.newPage();
    page.on("console", message => { if (message.type() === "error") r.errors.push(message.text()); });
    page.on("pageerror", error => r.errors.push(String(error)));
    page.on("popup", popup => r.popups.push(popup.url()));
    context.on("request", request => { if (!/^(file|about|data):/.test(request.url())) r.requests.push(request.url()); });
    await page.goto(url);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(800);
    const host = await page.$('iframe[title="LanguageOption variants locale default"]');
    const frame = await host.contentFrame();
    const decoder = await context.newPage();
    // Lowest painted row (exclusive) of the probe shadow and focus colors in a frame screenshot.
    const paint = async () => decoder.evaluate(async source => {
      const image = new Image(); image.src = source; await image.decode();
      const canvas = document.createElement("canvas"); canvas.width = image.width; canvas.height = image.height;
      const context = canvas.getContext("2d"); context.drawImage(image, 0, 0);
      const data = context.getImageData(0, 0, canvas.width, canvas.height).data;
      let shadow = 0, focus = 0;
      for (let y = 0; y < canvas.height; y += 1) for (let x = 0; x < canvas.width; x += 1) {
        const i = (y * canvas.width + x) * 4;
        if (data[i] > 200 && data[i + 1] < 60 && data[i + 2] < 60) shadow = y + 1;
        if (data[i] < 60 && data[i + 1] < 60 && data[i + 2] > 200) focus = y + 1;
      }
      return {width: canvas.width, height: canvas.height, shadow, focus};
    }, "data:image/png;base64," + (await host.screenshot()).toString("base64"));
    const read = () => frame.evaluate(() => {
      const options = [...document.querySelectorAll(".lang-opt")], subject = document.querySelector("[data-ds-subject]");
      return {open: document.querySelector("details.lang").open, viewport: innerHeight,
        menuBottom: document.querySelector(".lang-menu").getBoundingClientRect().bottom,
        inside: options.every(item => item.getBoundingClientRect().bottom <= innerHeight),
        subjects: document.querySelectorAll("[data-ds-subject]").length, focusVisible: subject.matches(":focus-visible"),
        labels: options.map(item => item.textContent), subject: subject.textContent};
    });
    r.closed = await read(); r.closedPaint = await paint();
    await frame.click("summary.lang-btn");
    await page.waitForTimeout(400);
    r.opened = await read(); r.openedPaint = await paint();
    await frame.focus("summary.lang-btn");
    await page.keyboard.press("Enter");
    await page.waitForTimeout(400);
    r.keyClosed = await read(); r.keyClosedPaint = await paint();
    await page.keyboard.press("Space");
    await page.waitForTimeout(400);
    r.keyOpened = await read(); r.keyOpenedPaint = await paint();
    for (let step = 0; step <= r.keyOpened.labels.indexOf(r.keyOpened.subject); step += 1) await page.keyboard.press("Tab");
    await page.waitForTimeout(200);
    r.focused = await read(); r.focusedPaint = await paint();
  } finally { await browser.close(); }
  console.log(JSON.stringify(r));
})().catch(error => { console.error(error); process.exit(1); });
"""


class NativeDetailsPaintTests(unittest.TestCase):
    def test_open_disclosure_paint_has_frame_clearance(self):
        node, module = _playwright()
        if not node or not module:
            if os.environ.get("PDH_REQUIRE_BROWSER_TESTS") == "1":
                self.fail("Node.js and PLAYWRIGHT_MODULE are required for the native details paint test")
            self.skipTest("Node Playwright is unavailable")
        source = page().replace(f"<style>{CSS}</style>", f"<style>{PAINT}</style>")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "preview.html"
            target.write_text(render({"index.html": source}), encoding="utf-8")
            try:
                completed = subprocess.run([node, "-", target.as_uri(), module], input=BROWSER, text=True, encoding="utf-8",
                                           capture_output=True, timeout=BROWSER_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired as error:
                self.fail(f"native details paint check exceeded {BROWSER_TIMEOUT_SECONDS}s: {error}")
        self.assertEqual(0, completed.returncode, completed.stderr[-3000:])
        r = json.loads(completed.stdout.strip().splitlines()[-1])
        self.assertEqual(([], [], []), (r["errors"], r["requests"], r["popups"]))
        self.assertEqual((False, 0, 0), (r["closed"]["open"], r["closedPaint"]["shadow"], r["closedPaint"]["focus"]))
        self.assertEqual(r["closedPaint"]["height"], r["keyClosedPaint"]["height"], "closing restores the closed frame")
        self.assertEqual(0, r["keyClosedPaint"]["shadow"])
        for name in ("opened", "keyOpened", "focused"):
            state, paint = r[name], r[name + "Paint"]
            with self.subTest(name):
                self.assertTrue(state["open"] and state["inside"], state)
                self.assertEqual(1, state["subjects"])
                # A frame at a fractional page offset screenshots one extra device row.
                self.assertLessEqual(abs(paint["height"] - state["viewport"]), 1, "screenshot covers the frame viewport")
                # The whole source shadow paints below the menu border, then the frame keeps clear rows.
                self.assertLessEqual(abs(state["menuBottom"] + SHADOW - paint["shadow"]), 1, (state["menuBottom"], paint))
                self.assertGreaterEqual(paint["height"] - paint["shadow"], 4, paint)
        self.assertEqual(r["openedPaint"]["height"], r["keyOpenedPaint"]["height"], "pointer and keyboard open alike")
        self.assertTrue(r["focused"]["focusVisible"], r["focused"])
        self.assertGreater(r["focusedPaint"]["focus"], 0, "the focus ring paints")
        self.assertLess(r["focusedPaint"]["focus"], r["focusedPaint"]["height"], r["focusedPaint"])


if __name__ == "__main__":
    unittest.main()
