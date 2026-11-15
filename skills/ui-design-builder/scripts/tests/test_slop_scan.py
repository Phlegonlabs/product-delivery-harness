"""The slop scanner reports default design patterns; it is advisory and never a gate."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "slop-scan"
sys.path.insert(0, str(SCRIPTS))
import direction_review
import reviewer_shell
import slop_scan

ROCKET = chr(0x1F680)
CHECK = chr(0x2713)
# One page that fires every pattern the scanner can emit.
EVERYTHING = (
    "<style>:root{--g:linear-gradient(120deg,#7c3aed,#4f46e5)}"
    "body{font-family:Inter,sans-serif;background:#f5f0e8}"
    ".a,.b,.c{border-radius:16px;box-shadow:0 2px 8px rgba(0,0,0,.1)}"
    ".hero{background:var(--g);-webkit-background-clip:text;backdrop-filter:blur(10px);"
    "box-shadow:0 10px 40px rgba(124,58,237,.4)}"
    ".grid{display:grid;grid-template-columns:repeat(4,1fr)}.tag{border-radius:9999px}</style>"
    "<h2>" + ROCKET + " Title</h2><span class=tag>1</span><span class=tag>2</span><span class=tag>3</span>"
)


def page(style="", body=""):
    return "<!doctype html><html><head><style>" + style + "</style></head><body>" + body + "</body></html>"


def ids(html, allow=()):
    return {row["id"]: row for row in slop_scan.scan_html(html, set(allow))["hits"]}


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = slop_scan.main(list(argv))
        except SystemExit as exit_:
            code = exit_.code
    return code, out.getvalue(), err.getvalue()


class PatternTests(unittest.TestCase):
    def assertHit(self, pattern, html):
        self.assertIn(pattern, ids(html), html)

    def assertNoHit(self, pattern, html):
        self.assertNotIn(pattern, ids(html), html)

    def test_default_sans(self):
        for css in ("body{font-family:Inter,sans-serif}", "h1{font-family:'Segoe UI',Arial}",
                    "body{font:16px/1.5 system-ui}", "html{font-family:sans-serif}",
                    ":root{--f:Roboto,sans-serif}body{font-family:var(--f)}"):
            self.assertHit("default-sans", page(css))
        self.assertHit("default-sans", page(body='<p style="font-family:Poppins">x</p>'))
        for css in ("body{font-family:'Fraunces',Inter,sans-serif}", ".card{font-family:Inter}",
                    "code{font-family:monospace}", "body{font:16px/1.5 Georgia,serif}"):
            self.assertNoHit("default-sans", page(css))

    def test_purple_gradient(self):
        for css in ("a{background:linear-gradient(135deg,#7c3aed,#4f46e5)}",
                    "a{background-image:radial-gradient(circle,hsl(270 70% 50%),#fff)}",
                    ":root{--g:linear-gradient(#7c3aed,#fff)}a{background:var(--g)}",
                    ":root{--p:#8b5cf6}a{background:linear-gradient(var(--p),#fff)}"):
            self.assertHit("purple-gradient", page(css))
        for css in ("a{background:linear-gradient(#0b6e4f,#e8f5ee)}", "a{background:linear-gradient(#777,#888)}",
                    "a{background:#7c3aed}", ":root{--g:linear-gradient(#7c3aed,#fff)}"):
            self.assertNoHit("purple-gradient", page(css))

    def test_gradient_text(self):
        for css in ("h1{background-clip:text}", "h1{-webkit-background-clip:text}"):
            self.assertHit("gradient-text", page(css))
        self.assertNoHit("gradient-text", page("h1{background-clip:padding-box}"))

    def test_glass_blur(self):
        for css in ("a{backdrop-filter:blur(8px)}", "a{-webkit-backdrop-filter:saturate(1.4) blur(8px)}"):
            self.assertHit("glass-blur", page(css))
        for css in ("a{filter:blur(4px)}", "a{backdrop-filter:none}"):
            self.assertNoHit("glass-blur", page(css))

    def test_colored_glow(self):
        self.assertHit("colored-glow", page("a{box-shadow:0 8px 32px rgba(124,58,237,.35)}"))
        self.assertHit("colored-glow", page("a{box-shadow:0 1px 2px #000,0 0 24px hsl(200 80% 50%)}"))
        for css in ("a{box-shadow:0 4px 12px rgba(124,58,237,.3)}", "a{box-shadow:0 20px 40px rgba(0,0,0,.15)}",
                    "a{box-shadow:0 12px 32px rgba(16,24,40,.1)}", "a{box-shadow:none}"):
            self.assertNoHit("colored-glow", page(css))

    def test_beige_canvas(self):
        for css in ("body{background:#f5f0e8}", "html{background-color:hsl(40 30% 95%)}",
                    ":root{--bg:#f5f0e8}body{background:var(--bg)}"):
            self.assertHit("beige-canvas", page(css))
        for css in ("body{background:#fbfbfa}", "body{background:#fff}", "body{background:#1a1a1a}",
                    ".card{background:#f5f0e8}", "body{background:#e9d8b4}"):
            self.assertNoHit("beige-canvas", page(css))

    def test_uniform_rounded_cards(self):
        shadow = "box-shadow:0 2px 8px rgba(0,0,0,.1)"
        three = ".a{border-radius:16px;%s}.b{border-radius:16px;%s}.c{border-radius:16px;%s}" % ((shadow,) * 3)
        self.assertHit("uniform-rounded-cards", page(three))
        self.assertEqual(3, ids(page(three))["uniform-rounded-cards"]["count"])
        self.assertNoHit("uniform-rounded-cards", page(three.replace(".c{border-radius:16px;" + shadow + "}", "")))
        self.assertNoHit("uniform-rounded-cards", page(three.replace("16px;" + shadow + "}.b", "20px;" + shadow + "}.b", 1)))
        self.assertNoHit("uniform-rounded-cards", page(three.replace("16px", "4px")))
        self.assertNoHit("uniform-rounded-cards", page(three.replace(shadow, "border:1px solid #ccc")))

    def test_equal_feature_tiles(self):
        for css in ("a{grid-template-columns:repeat(3,1fr)}", "a{grid-template-columns:repeat(4, minmax(0, 1fr))}"):
            self.assertHit("equal-feature-tiles", page(css))
        for css in ("a{grid-template-columns:repeat(2,1fr)}", "a{grid-template-columns:2fr 1fr}",
                    "a{grid-template-columns:repeat(3,200px)}"):
            self.assertNoHit("equal-feature-tiles", page(css))

    def test_emoji_ui(self):
        for body in ("<h2>%s Fast</h2>", "<button>%s Go</button>", "<a href=x>%s Docs</a>", "<ul><li>%s Done</li></ul>"):
            self.assertHit("emoji-ui", page(body=body % ROCKET))
        for body in ("<p>%s Fast</p>", "<h2>Fast</h2>", "<li>%s Done</li>" % CHECK):
            self.assertNoHit("emoji-ui", page(body=body % ROCKET if "%s" in body else body))

    def test_pill_badge_row(self):
        tags = "<span class=tag>1</span><span class=tag>2</span><span class=tag>3</span>"
        self.assertEqual(3, ids(page(".tag{border-radius:999px}", tags))["pill-badge-row"]["count"])
        self.assertHit("pill-badge-row", page(".tag{border-radius:100vmax}", tags))
        self.assertHit("pill-badge-row", page(".tag{border-radius:50rem}", tags))
        self.assertHit("pill-badge-row", page(body="<i style='border-radius:9999px'>1</i>" * 3))
        self.assertNoHit("pill-badge-row", page(".tag{border-radius:999px}", tags[:-len("<span class=tag>3</span>")]))
        self.assertNoHit("pill-badge-row", page(".tag{border-radius:8px}", tags))
        self.assertNoHit("pill-badge-row", page("button{border-radius:999px}", "<button>1</button>" * 3))
        self.assertNoHit("pill-badge-row", page(".pill{border-radius:999px}", "<a class='pill btn'>x</a>" * 3))

    def test_neutral_pages_have_no_hits(self):
        html = (FIXTURES / "neutral.html").read_text(encoding="utf-8")
        self.assertEqual({}, ids(html))
        self.assertEqual({}, ids(page()))

    def test_every_listed_pattern_can_be_emitted(self):
        emitted = set(ids(EVERYTHING))
        code, out, _ = run("--list")
        listed = {line.partition(":")[0] for line in out.splitlines()}
        self.assertEqual(0, code)
        self.assertEqual(listed, emitted)
        self.assertEqual(set(slop_scan.PATTERNS), emitted)
        self.assertTrue(all(line.partition(": ")[2] for line in out.splitlines()))


class ReviewerShellTests(unittest.TestCase):
    TRIGGERS = ('<aside data-hifi-reviewer-shell style="background:linear-gradient(#7c3aed,#4f46e5);'
                'font-family:Inter"><h2>' + ROCKET + ' Review</h2></aside>')

    def test_hifi_shell_from_real_templates_is_ignored(self):
        manifest = {"surfaces": [{"id": "UI-001", "page": "index.html", "platformGroup": "web",
                                  "responsive": {"targets": [390, 1200]}, "states": ["ready", "empty"]}]}
        html = (FIXTURES / "neutral.html").read_text(encoding="utf-8")
        html = reviewer_shell.inject_shared_css(html)
        html = reviewer_shell.inject_shell(manifest, html, "index.html")
        html = reviewer_shell.inject_runtime(html)
        self.assertIn("hifi-reviewer:css:start", html)
        self.assertIn("data-hifi-reviewer-shell", html)
        self.assertEqual({}, ids(html))

    def test_direction_shell_is_ignored(self):
        html = (FIXTURES / "neutral.html").read_text(encoding="utf-8")
        html = reviewer_shell.inject_shared_css(html)
        html = html.replace("</head>", direction_review.style_block() + "\n</head>")
        html = html.replace("<body>", "<body>\n<!-- reviewer:start -->" + self.TRIGGERS + "<!-- reviewer:end -->")
        html = html.replace("</body>", direction_review.runtime_block("pkg") + "\n</body>")
        self.assertIn("direction-reviewer:css:start", html)
        self.assertEqual({}, ids(html))

    def test_shell_markers_hide_planted_triggers_but_product_content_still_hits(self):
        planted = "<!-- reviewer:start -->" + self.TRIGGERS + "<!-- reviewer:end -->"
        self.assertEqual({}, ids(page(body=planted)))
        self.assertEqual({}, ids(page(body=self.TRIGGERS)))
        self.assertIn("emoji-ui", ids(page(body=planted + "<h1>" + ROCKET + " Product</h1>")))


class AllowAndClusterTests(unittest.TestCase):
    def report(self, html, allow=()):
        return slop_scan.scan_html(html, set(allow))

    def test_cluster_at_exactly_three(self):
        two = page("body{font-family:Inter}a{backdrop-filter:blur(4px)}")
        three = page("body{font-family:Inter}a{backdrop-filter:blur(4px)}h1{background-clip:text}")
        self.assertEqual((2, False), (self.report(two)["distinctPatterns"], self.report(two)["cluster"]))
        self.assertEqual((3, True), (self.report(three)["distinctPatterns"], self.report(three)["cluster"]))

    def test_repeated_pattern_counts_once_toward_a_cluster(self):
        html = page("body{font-family:Inter}h1{font-family:Roboto}h2{font-family:Arial}")
        report = self.report(html)
        self.assertEqual(3, report["hits"][0]["count"])
        self.assertEqual((1, False), (report["distinctPatterns"], report["cluster"]))

    def test_allow_keeps_the_hit_listed_but_uncounted(self):
        html = page("body{font-family:Inter}a{backdrop-filter:blur(4px)}h1{background-clip:text}")
        report = self.report(html, ["default-sans"])
        self.assertEqual({"default-sans": True, "glass-blur": False, "gradient-text": False},
                         {row["id"]: row["allowed"] for row in report["hits"]})
        self.assertEqual((2, False), (report["distinctPatterns"], report["cluster"]))

    def test_evidence_is_short_and_capped_at_three(self):
        html = page("".join("h%d{font-family:Inter}" % n for n in range(1, 6)))
        row = self.report(html)["hits"][0]
        self.assertEqual(5, row["count"])
        self.assertEqual(3, len(row["evidence"]))
        self.assertTrue(all(len(item) <= 90 for item in row["evidence"]))


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cluster = self.write("docs/a.html", (FIXTURES / "cluster.html").read_text(encoding="utf-8"))
        self.neutral = self.write("docs/b.html", (FIXTURES / "neutral.html").read_text(encoding="utf-8"))

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return relative

    def scan(self, *extra):
        return run("--repo-root", str(self.root), *extra)

    def test_report_shape_and_exit_zero_with_clusters(self):
        code, out, _ = self.scan("--page", self.cluster, "--page", self.neutral)
        self.assertEqual(0, code)
        report = json.loads(out)
        self.assertEqual("slop-scan/1", report["schema"])
        self.assertEqual(1, report["clusters"])
        first, second = report["pages"]
        self.assertEqual((self.cluster, True), (first["path"], first["cluster"]))
        self.assertEqual(hashlib.sha256((self.root / self.cluster).read_bytes()).hexdigest(), first["sha256"])
        self.assertEqual((self.neutral, 0, False, []), (second["path"], second["distinctPatterns"],
                                                        second["cluster"], second["hits"]))
        self.assertEqual({"id", "count", "evidence", "allowed"}, set(first["hits"][0]))
        self.assertEqual([row["id"] for row in first["hits"]], sorted(row["id"] for row in first["hits"]))

    def test_output_is_deterministic(self):
        runs = {self.scan("--page", self.cluster, "--page", self.neutral, "--allow", "emoji-ui")[1] for _ in range(2)}
        self.assertEqual(1, len(runs))
        with_allow = json.loads(runs.pop())
        self.assertEqual(["emoji-ui"], with_allow["allowed"])

    def test_allow_accepts_several_ids_and_rejects_unknown_ones(self):
        code, out, _ = self.scan("--page", self.cluster, "--allow", "emoji-ui", "glass-blur")
        self.assertEqual(0, code)
        self.assertEqual(["emoji-ui", "glass-blur"], json.loads(out)["allowed"])
        code, out, err = self.scan("--page", self.cluster, "--allow", "no-such-pattern")
        self.assertEqual((2, ""), (code, out))
        self.assertIn("unknown pattern id: no-such-pattern", err)

    def test_missing_and_escaping_pages_exit_two(self):
        for bad in ("docs/missing.html", "../outside.html", "docs/../../outside.html", "/etc/hosts",
                    "docs\\a.html", "C:/Windows/win.ini"):
            code, out, err = self.scan("--page", bad)
            self.assertEqual((2, ""), (code, out), bad)
            self.assertEqual(1, len(err.strip().splitlines()), bad)
        self.assertEqual(2, run("--repo-root", str(self.root))[0])

    def test_linked_pages_are_rejected(self):
        link = self.root / "docs" / "link.html"
        try:
            os.symlink(self.root / self.cluster, link)
        except (OSError, NotImplementedError):
            junction = self.root / "linked"
            made = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(self.root / "docs")],
                                  capture_output=True) if os.name == "nt" else None
            if made is None or made.returncode != 0:
                self.skipTest("this account cannot create links")
            link = junction / "a.html"
        code, _, err = self.scan("--page", link.relative_to(self.root).as_posix())
        self.assertEqual(2, code)
        self.assertIn("links", err)

    def test_out_writes_and_refuses_overwrite(self):
        code, out, _ = self.scan("--page", self.neutral, "--out", "docs/report.json")
        self.assertEqual((0, ""), (code, out))
        written = (self.root / "docs" / "report.json").read_bytes()
        self.assertEqual("slop-scan/1", json.loads(written)["schema"])
        code, _, err = self.scan("--page", self.cluster, "--out", "docs/report.json")
        self.assertEqual(2, code)
        self.assertIn("--overwrite", err)
        self.assertEqual(written, (self.root / "docs" / "report.json").read_bytes())
        self.assertEqual(0, self.scan("--page", self.cluster, "--out", "docs/report.json", "--overwrite")[0])
        self.assertNotEqual(written, (self.root / "docs" / "report.json").read_bytes())
        self.assertEqual(2, self.scan("--page", self.neutral, "--out", "../report.json")[0])

    def test_script_runs_from_the_command_line(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "slop_scan.py"), "--repo-root", str(self.root),
                                 "--page", self.cluster], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)["pages"][0]["cluster"])


if __name__ == "__main__":
    unittest.main()
