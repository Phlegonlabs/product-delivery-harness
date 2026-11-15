"""capture_sheet.py builds a self-contained image sheet from synthetic PNG bytes."""

import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

SCRIPTS = Path(__file__).resolve().parents[1]
SCRIPT = SCRIPTS / "capture_sheet.py"


def png(red):
    """A valid 2x2 PNG in one colour, so each test image has distinct bytes."""
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    raw = b"".join(b"\x00" + bytes([red, 0, 0]) * 2 for _ in range(2))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class CaptureSheetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.images = {}
        for index, name in enumerate(("a.png", "b.png", "c.png")):
            self.images[name] = self.write("refs/" + name, png(40 + index))
        self.write("refs/photo.jpg", b"\xff\xd8\xff synthetic jpeg")

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def run_sheet(self, *args, out="sheet.html"):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), "--repo-root", str(self.root),
                               "--title", "Reference board", *args, "--out", out],
                              capture_output=True, text=True, encoding="utf-8", timeout=30)

    def page(self, out="sheet.html"):
        return (self.root / out).read_text(encoding="utf-8")

    def test_board_and_comparison_rows_keep_order_and_hashes(self):
        result = self.run_sheet("--row", "Home", "refs/b.png", "--row", "Detail", "refs/a.png", "refs/c.png",
                                "--columns", "Selected direction", "HiFi candidate")
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        text = self.page()
        self.assertEqual("capture-sheet/1", report["schema"])
        self.assertEqual(["Home", "Detail"], [row["label"] for row in report["rows"]])
        self.assertEqual([[("refs/b.png", self.images["b.png"])],
                          [("refs/a.png", self.images["a.png"]), ("refs/c.png", self.images["c.png"])]],
                         [[(i["path"], i["sha256"]) for i in row["images"]] for row in report["rows"]])
        self.assertEqual({"path": "sheet.html", "sha256": hashlib.sha256((self.root / "sheet.html").read_bytes()).hexdigest()},
                         report["out"])
        for digest in self.images.values():
            self.assertIn("sha256:" + digest, text)
        for first, second in (("Home", "Detail"), ("refs/a.png", "refs/c.png"), ("Selected direction", "HiFi candidate")):
            self.assertLess(text.index(first), text.index(second))
        self.assertLess(text.index("refs/b.png"), text.index("refs/a.png"))
        self.assertEqual(3, text.count("<img "))

    def test_column_headings_appear_once_per_image_position(self):
        result = self.run_sheet("--row", "Detail", "refs/a.png", "refs/c.png", "--columns", "Target", "Candidate")
        self.assertEqual(0, result.returncode, result.stderr)
        text = self.page()
        self.assertEqual(1, text.count("<b>Target</b>"))
        self.assertEqual(1, text.count("<b>Candidate</b>"))

    def test_labels_titles_and_columns_are_escaped(self):
        result = self.run_sheet("--row", '<img src=x onerror=1>&"', "refs/a.png", "--columns", "<b>col</b>")
        self.assertEqual(0, result.returncode, result.stderr)
        text = self.page()
        self.assertNotIn("<img src=x", text)
        self.assertIn("&lt;img src=x onerror=1&gt;&amp;&quot;", text)
        self.assertIn("&lt;b&gt;col&lt;/b&gt;", text)

    def test_output_is_self_contained(self):
        result = self.run_sheet("--row", "Home", "refs/a.png", "--row", "Photo", "refs/photo.jpg")
        self.assertEqual(0, result.returncode, result.stderr)
        text = self.page()
        bare = re.sub(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+", "data:", text)
        self.assertEqual(2, text.count("data:image/"))
        self.assertIn("data:image/jpeg;base64,", text)
        self.assertNotRegex(bare.lower(), r"https?:|//|@import|url\(|<script|<link|src=\"(?!data:)")
        self.assertIn("default-src 'none'; img-src data:; style-src 'unsafe-inline'", text)
        self.assertIn("prefers-color-scheme:dark", text)
        self.assertIn("object-fit:contain", text)

    def test_overwrite_is_refused_until_requested(self):
        args = ("--row", "Home", "refs/a.png")
        self.assertEqual(0, self.run_sheet(*args).returncode)
        first = (self.root / "sheet.html").read_bytes()
        refused = self.run_sheet("--row", "Home", "refs/b.png")
        self.assertEqual(2, refused.returncode)
        self.assertIn("--overwrite", refused.stderr)
        self.assertEqual(first, (self.root / "sheet.html").read_bytes())
        self.assertEqual(0, self.run_sheet("--row", "Home", "refs/b.png", "--overwrite").returncode)
        self.assertNotEqual(first, (self.root / "sheet.html").read_bytes())

    def test_bad_paths_exit_two_with_one_line(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        stray = Path(outside.name) / "stray.png"
        stray.write_bytes(png(1))
        self.write("refs/notes.txt", b"not an image")
        cases = {
            "escape": (("--row", "Home", "../outside.png"), "sheet.html"),
            "absolute escape": (("--row", "Home", str(stray)), "sheet.html"),
            "missing": (("--row", "Home", "refs/none.png"), "sheet.html"),
            "extension": (("--row", "Home", "refs/notes.txt"), "sheet.html"),
            "label only": (("--row", "Home"), "sheet.html"),
            "output escape": (("--row", "Home", "refs/a.png"), "../sheet.html"),
            "too many images": (("--row", "Home", "refs/a.png", "refs/b.png", "--columns", "Only"), "sheet.html"),
        }
        for name, (args, out) in cases.items():
            with self.subTest(name):
                result = self.run_sheet(*args, out=out)
                self.assertEqual(2, result.returncode, result.stderr)
                self.assertEqual(1, len(result.stderr.strip().splitlines()), result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse((self.root / "sheet.html").exists())

    def test_linked_image_is_rejected(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        (Path(outside.name) / "stray.png").write_bytes(png(2))
        link = self.root / "linked"
        try:
            link.symlink_to(outside.name, target_is_directory=True)
        except OSError:
            if sys.platform != "win32":
                raise
            subprocess.run(["cmd", "/c", "mklink", "/J", str(link), outside.name],
                           check=True, capture_output=True, timeout=15)
        self.addCleanup(link.rmdir)
        result = self.run_sheet("--row", "Home", "linked/stray.png")
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertIn("links or reparse points", result.stderr)

    def test_output_is_deterministic(self):
        args = ("--row", "Home", "refs/a.png", "refs/b.png", "--columns", "Target", "Candidate")
        first = self.run_sheet(*args, out="one.html")
        second = self.run_sheet(*args, out="two.html")
        self.assertEqual((self.root / "one.html").read_bytes(), (self.root / "two.html").read_bytes())
        self.assertEqual(json.loads(first.stdout)["rows"], json.loads(second.stdout)["rows"])
        self.assertEqual(json.loads(first.stdout)["out"]["sha256"], json.loads(second.stdout)["out"]["sha256"])


if __name__ == "__main__":
    unittest.main()
