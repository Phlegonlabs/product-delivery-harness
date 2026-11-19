"""hifi_matrix_capture --measure-a11y text-split: figures and short CJK words drawn across a line break.

Real Chromium over tiny fixture elements on the UI-002 page. Synthetic fixture pages only.
The browser run needs Node Playwright and is required when PDH_REQUIRE_BROWSER_TESTS=1.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_hifi_matrix_capture as base  # noqa: E402

m = base.m

PAY = "請於今日下午五點前完成付款並保留收據以便日後查詢"     # 24 characters; 付 is the 12th, 款 the 13th
MONO = "font-family:monospace"
# Widths are in em of each element's own font, so a monospace or CJK glyph count decides where a line breaks
# on any platform font. The wrapper spans the grid, so only #zoomsplit depends on the canvas width, and every
# box fits the 147 px the surface has at 390 under zoom-200, so the axis itself passes.
TEXT_SPLIT_EXTRA = f"""<div style="grid-column:1/-1">
<p id="amount" style="width:6em;{MONO}">HK$ 12,345.67</p>
<p id="nowrap" style="width:6em;{MONO};white-space:nowrap">HK$ 12,345.67</p>
<p id="spanned" style="width:6em;{MONO}"><span>HK$</span> 12,345.67</p>
<p id="trend" style="width:3.4em;{MONO}">+12.5 %</p>
<p id="clipped" style="width:6em;height:1.5em;overflow:hidden;{MONO}">HK$ 12,345.67</p>
<p id="date" lang="zh-Hant" style="width:5.5em">2026年11月19日</p>
<button id="pay" lang="zh-Hant" style="width:12.5em;padding:0;border:0;font:10px/1.5 sans-serif">{PAY}</button>
<button id="paylong" lang="zh-Hant" style="width:12.5em;padding:0;border:0;font:10px/1.5 sans-serif">{PAY}。</button>
<p id="paragraph" lang="zh-Hant" style="width:12.5em;font-size:10px">{PAY}{PAY}</p>
<p id="words" style="width:6em">Harbour pilots board early</p>
<h3 id="heading" style="width:5em">Pay the berth fee</h3>
<p id="zoomsplit" style="width:50%;{MONO}">Fee HK$ 1,280</p>
<p id="stacked" style="{MONO}">USD<span style="display:block">Berth 4</span>12</p>
</div>"""
OWN = ("amount", "nowrap", "spanned", "trend", "clipped", "date", "pay", "paylong", "paragraph", "words", "heading", "zoomsplit",
       "stacked")


class TextSplitBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node, module = shutil.which("node"), os.environ.get("PLAYWRIGHT_MODULE")
        if not module and (base.SCRIPTS.parents[2] / "node_modules" / "playwright").exists():
            module = str(base.SCRIPTS.parents[2] / "node_modules" / "playwright")
        if not node or not module or not Path(module).exists():
            message = "Required browser test prerequisite missing: Node.js and PLAYWRIGHT_MODULE"
            if os.environ.get("PDH_REQUIRE_BROWSER_TESTS") == "1":
                raise AssertionError(message)
            raise unittest.SkipTest(message)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = base.build_package(root, details_extra=TEXT_SPLIT_EXTRA)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), mock.patch.dict(os.environ, {"PLAYWRIGHT_MODULE": module}):
                cls.code = m.main(["--repo-root", str(root), "--package", str(package), "--out", "docs/evidence/split",
                                   "--only", "UI-002", "--measure-a11y", "--axes", "zoom-200"])
            cls.text = buffer.getvalue()
            folder = root / "docs/evidence/split"
            cls.output = json.loads((folder / m.OUTPUT_NAME).read_text(encoding="utf-8"))
            sidecar = json.loads((folder / m.SIDECAR_NAME).read_text(encoding="utf-8"))
            cls.a11y, cls.axes = sidecar["a11y"], sidecar["axes"]

    def rows(self, **where):
        """text-split rows on the fixture's own elements, as (target, selector, token, lines)."""
        return {(f["target"], f["selector"], f["token"], f["lines"]) for f in self.a11y["findings"]
                if f["measure"] == "text-split" and f["selector"].split("#")[-1] in OWN
                and all(f[key] == value for key, value in where.items())}

    def test_split_figures_and_short_cjk_words_are_reported_on_every_base_case(self):
        expected = {("p#amount", "HK$ 12,345.67", 2), ("p#spanned", "HK$ 12,345.67", 2), ("p#trend", "+12.5 %", 2),
                    ("p#date", "2026年11月19日", 2), ("button#pay", "付款", 2)}
        for state in ("ready", "loading", "error"):
            self.assertEqual({(target, *row) for target in ("390", "1200") for row in expected},
                             self.rows(axis="base", state=state), state)
        row = next(f for f in self.a11y["findings"] if f["measure"] == "text-split" and f["selector"] == "button#pay")
        self.assertEqual({"level": "fail", "limit": 1, "surface": "UI-002"},
                         {key: row[key] for key in ("level", "limit", "surface")})

    def test_nowrap_words_long_cjk_clipped_text_and_text_across_a_block_give_no_row(self):
        named = {selector for _, selector, _, _ in self.rows()}
        for quiet in ("p#nowrap", "button#paylong", "p#paragraph", "p#words", "h3#heading", "p#clipped", "p#stacked"):
            self.assertNotIn(quiet, named)
        # the clipped amount is text-clip's finding, not a second one here
        self.assertTrue(any(f["measure"] == "text-clip" and f["selector"] == "p#clipped" for f in self.a11y["findings"]))

    def test_a_split_only_at_200_percent_is_reported_on_that_axis(self):
        self.assertNotIn("p#zoomsplit", {selector for _, selector, _, _ in self.rows(axis="base")})
        self.assertEqual({("390", "p#zoomsplit", "HK$ 1,280", 2)},
                         {row for row in self.rows(axis="zoom-200") if row[1] == "p#zoomsplit"})
        self.assertIn(("390", "button#pay", "付款", 2), self.rows(axis="zoom-200"))

    def test_findings_change_no_result_or_exit_code(self):
        self.assertEqual(0, self.code, [row for row in self.axes if row["result"] != "PASS"])
        self.assertEqual({"PASS"}, {r["result"] for r in self.output["results"]})
        line = json.loads(self.text.strip().splitlines()[-1])
        self.assertEqual(self.a11y["summary"]["text-split"]["fail"], line["a11y"]["text-split"])
        self.assertGreater(self.a11y["summary"]["text-split"]["checked"], self.a11y["summary"]["text-split"]["fail"])


if __name__ == "__main__":
    unittest.main()
