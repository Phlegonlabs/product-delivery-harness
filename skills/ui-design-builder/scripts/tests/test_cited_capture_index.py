"""The Visual Approval check names cited captures that a fresh checkout would lack."""
import contextlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from test_structure_publication import build_receipt, checker, digest
from test_wireframe_free_publication import current_publication

CONTRACT = Path(__file__).resolve().parents[3] / "delivery-harness" / "references" / "gitignore-contract.md"


def capture_rules():
    text = CONTRACT.read_text(encoding="utf-8").replace("\r\n", "\n")
    section = text.split("\n## UI Capture Output\n", 1)[1].split("\n## ", 1)[0]
    return re.search(r"```gitignore\n(.*?)```", section, re.S).group(1)


def png_captures(root, ui):
    """Rename the review captures the Visual Approval receipts cite to PNG and re-seal those receipts."""
    text = ui.read_text(encoding="utf-8")
    renamed = []
    for receipt_path in sorted((root / "docs/evidence").glob("*.json")):
        old = digest(receipt_path)
        if old not in text:
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        out_path = root / receipt["receipt"]["outputArtifact"]["path"]
        output = json.loads(out_path.read_text(encoding="utf-8"))
        for row in (output.get("assessment") or {}).get("observations", []):
            for binding in row["evidence"]:
                png = binding["path"].removesuffix(".json") + ".png"
                (root / binding["path"]).rename(root / png)
                binding["path"] = png
                renamed.append(png)
        out_path.write_text(json.dumps(output), encoding="utf-8")
        receipt_path.write_text(json.dumps(build_receipt(root, out_path.relative_to(root).as_posix())),
                                encoding="utf-8")
        text = text.replace(old, digest(receipt_path))
    text = re.sub(r"ui-design=docs/design/ui-design.md @ sha256:[0-9a-f]{64}",
                  "ui-design=docs/design/ui-design.md @ sha256:" + checker.canonical_ui_approval_sha256(text), text)
    ui.write_text(text, encoding="utf-8")
    return sorted(renamed)


def approval_check(root):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = checker.main([
            "--ui-design", str(root / "docs/design/ui-design.md"), "--repo-root", str(root),
            "--prd", str(root / "docs/product/PRD.md"), "--hifi", str(root / "docs/design/ui-references/run-1/index.html"),
            "--require-filled", "--require-visual-approved",
        ])
    return code, err.getvalue()


class CitedCaptureIndexTests(unittest.TestCase):
    def test_ignored_cited_captures_are_listed_until_force_added(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            ui, _, _ = current_publication(root)
            captures = png_captures(root, ui)
            self.assertGreater(len(captures), 1)
            self.assertEqual((0, ""), approval_check(root))
            (root / ".gitignore").write_text(capture_rules(), encoding="utf-8", newline="\n")

            def git(*arguments):
                subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True, timeout=60)

            git("init", "-q")
            git("add", "-A")
            code, err = approval_check(root)
            self.assertEqual(1, code)
            self.assertEqual(1, err.count("git add -f"), err)
            self.assertIn("git add -f -- " + " ".join(f"'{path}'" for path in captures) + "\n", err)

            copy = Path(directory) / "copy"
            shutil.copytree(root, copy, ignore=shutil.ignore_patterns(".git"))
            self.assertEqual((0, ""), approval_check(copy))

            git("add", "-f", "--", *captures)
            self.assertEqual((0, ""), approval_check(root))

    def test_a_long_capture_list_becomes_a_pathspec_file(self):
        limit = checker.FORCE_ADD_INLINE_LIMIT
        paths = [f"docs/design/evidence/run-1/case {index:03}.png" for index in range(limit + 1)]
        self.assertNotIn("\n", checker._force_add_instruction(paths[:limit]))
        message = checker._force_add_instruction(paths)
        self.assertIn("git add -f --pathspec-from-file=<file>", message)
        self.assertEqual(paths, message.split("\n")[1:])


if __name__ == "__main__":
    unittest.main()
