"""Publication checkout paths retain approval identities and upstream history."""
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_ui_design_contract import materialize_publication
import check_ui_publication as publication
from ui_approval_digest import canonical_ui_approval_sha256


class PublicationTests(unittest.TestCase):
    def test_publication_and_drift(self):
        for required in (False, True):
            with self.subTest(required=required), tempfile.TemporaryDirectory() as temp:
                source, candidate = Path(temp) / "source", Path(temp) / "candidate"
                source.mkdir()
                materialize_publication(source, required=required)
                def git(*args):
                    subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
                git("init", "-q")
                git("add", ".")
                git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
                shutil.copytree(source, candidate)
                hifi = Path("docs/design/ui-references/run-1/index.html")
                def check(published=False):
                    return publication.validate(source, candidate, hifi=hifi, required=required, published=published)
                self.assertEqual([], check())
                self.assertEqual([], check(published=True))
                upstream = candidate / "docs/product/PRD.md"
                original = upstream.read_bytes()
                upstream.write_bytes(original + b"\ndrift")
                self.assertIn("upstream/source", " ".join(check()))
                upstream.write_bytes(original)
                page = candidate / hifi
                original_page = page.read_bytes()
                page.write_bytes(original_page + b"tamper")
                self.assertTrue(check())
                page.unlink()
                self.assertTrue(check())
                page.write_bytes(original_page)
                hidden = candidate / "docs/design/hidden.html"
                hidden.write_text("ignored candidate", encoding="utf-8")
                (candidate / ".git/info/exclude").write_text("docs/design/hidden.html\n", encoding="utf-8")
                self.assertIn("must not be ignored", " ".join(check()))
                hidden.unlink()
                git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "drift")
                self.assertIn("HEAD differs", " ".join(check()))

    def test_digest_cli_is_stable_across_derived_linkage(self):
        text = "# UI\n\nApproved direction\nCompiled design system pair: pending\n"
        linked = text.replace("pending", "docs/design/pair @ sha256:" + "a" * 64)
        self.assertEqual(canonical_ui_approval_sha256(text), canonical_ui_approval_sha256(linked))
        self.assertNotEqual(hashlib.sha256(linked.encode()).hexdigest(), canonical_ui_approval_sha256(linked))
        with tempfile.TemporaryDirectory(prefix="digest path with spaces ") as temp:
            path = Path(temp) / "ui design.md"
            path.write_text(linked, encoding="utf-8")
            script = Path(publication.__file__).with_name("ui_approval_digest.py")
            result = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(canonical_ui_approval_sha256(linked), result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
