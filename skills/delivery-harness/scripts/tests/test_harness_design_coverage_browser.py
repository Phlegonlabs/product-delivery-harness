"""Optional real Chromium proof, separate from mocked capture-driver tests."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ReducedMotionBrowserFixtureTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("PDH_REQUIRE_BROWSER_TESTS") == "1"
        and os.environ.get("PLAYWRIGHT_MODULE"),
        "browser fixture requires an observed Playwright installation",
    )
    def test_browser_reduced_motion_preference_is_real(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "motion.html"
            page.write_text("<!doctype html><body>Motion fixture</body>", encoding="utf-8")
            script = root / "motion.cjs"
            script.write_text(r"""
const [modulePath, pageUrl] = process.argv.slice(2);
const { chromium } = require(modulePath);
(async () => {
  const browser = await chromium.launch({headless: true});
  try {
    const values = [];
    for (const reducedMotion of ['no-preference', 'reduce']) {
      const context = await browser.newContext({reducedMotion});
      const page = await context.newPage();
      await page.goto(pageUrl);
      values.push(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches));
      await context.close();
    }
    console.log(JSON.stringify({browser: browser.browserType().name(), version: browser.version(), values}));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
""", encoding="utf-8")
            result = subprocess.run(
                ["node", str(script), os.environ["PLAYWRIGHT_MODULE"], page.as_uri()],
                capture_output=True, text=True, timeout=30, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual("chromium", report["browser"])
            self.assertTrue(report["version"])
            self.assertEqual([False, True], report["values"])


if __name__ == "__main__":
    unittest.main()
