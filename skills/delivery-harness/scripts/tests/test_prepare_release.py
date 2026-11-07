"""prepare_release.py on a fixture copy of the real release surfaces."""

from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import prepare_release  # noqa: E402

REPO_ROOT = next(
    (path for path in SCRIPTS.parents
     if (path / "package.json").is_file() and (path / "CHANGELOG.md").is_file()),
    None,
)
SURFACES = (
    "skills/delivery-harness/VERSION", "package.json", "package-lock.json", "CHANGELOG.md",
    "README.md", "README.zh-TW.md", "README.zh-CN.md", "README.es.md",
)
BODIES = {
    "en.md": "Fixture release. English body.",
    "zh-TW.md": "測試版本。繁體內文。",
    "zh-CN.md": "测试版本。简体正文。",
    "es.md": "Versión de prueba. Cuerpo en español.",
}
ENTRY = re.compile(r"^- \*\*(\d+\.\d+\.\d+)\*\* ", re.M)


@unittest.skipIf(REPO_ROOT is None, "release surfaces require a source checkout")
class PrepareReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repo"
        for name in SURFACES:
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / name, self.root / name)
        self.entries = Path(temporary.name) / "entries"
        self.entries.mkdir()
        for name, body in BODIES.items():
            (self.entries / name).write_text(body + "\n", encoding="utf-8")
        self.old = (self.root / SURFACES[0]).read_text(encoding="utf-8").strip()
        major, minor, _ = self.old.split(".")
        self.new = f"{major}.{int(minor) + 1}.0"

    def run_main(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = prepare_release.main(["--root", str(self.root), *argv])
        return code, out.getvalue(), err.getvalue()

    def snapshot(self) -> dict[str, bytes]:
        return {name: (self.root / name).read_bytes() for name in SURFACES}

    def text(self, name: str) -> str:
        return (self.root / name).read_text(encoding="utf-8")

    def set_line_endings(self, newline: str) -> None:
        for name in SURFACES:
            data = (self.root / name).read_bytes().replace(b"\r\n", b"\n")
            (self.root / name).write_bytes(data.replace(b"\n", newline.encode()))

    def test_check_passes_on_the_real_surfaces(self) -> None:
        code, out, err = self.run_main("--check")
        self.assertEqual(0, code, err)
        self.assertIn(f"release surfaces agree on {self.old}", out)
        self.assertIn('package-lock.json packages[""].version', out)

    def test_bump_inserts_entries_and_rotates_the_oldest_into_the_changelog(self) -> None:
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                self.setUp()
                self.set_line_endings(newline)
                before = {name: self.text(name) for name in SURFACES}
                english = ENTRY.findall(before["README.md"])
                oldest = re.search(r"^- \*\*" + re.escape(english[-1]) + r"\*\* .*$", before["README.md"], re.M).group(0)

                code, out, err = self.run_main("--version", self.new, "--entries", str(self.entries))
                self.assertEqual(0, code, err)
                self.assertEqual(sorted(SURFACES), sorted(out.split()))

                self.assertEqual(self.new, self.text(SURFACES[0]).strip())
                self.assertEqual(self.new, json.loads(self.text("package.json"))["version"])
                lock = json.loads(self.text("package-lock.json"))
                self.assertEqual(self.new, lock["version"])
                self.assertEqual(self.new, lock["packages"][""]["version"])
                old_lock = json.loads(before["package-lock.json"])
                old_lock["version"] = old_lock["packages"][""]["version"] = self.new
                self.assertEqual(old_lock, lock)
                for entry, readme in prepare_release.READMES.items():
                    text = self.text(readme)
                    versions = ENTRY.findall(text)
                    self.assertEqual(ENTRY.findall(before[readme])[:-1], versions[1:])
                    self.assertIn(f"badge/version-{self.new}-", text)
                    self.assertIn(f"\n- **{self.new}** — {BODIES[entry]}\n\n- **{self.old}** ", text)
                    self.assertEqual(before[readme].count("\n"), text.count("\n"))

                changelog = self.text("CHANGELOG.md")
                self.assertIn(f"English release history through {english[-1]}. ", changelog)
                first = changelog.index("\n- **")
                self.assertTrue(changelog[first + 1:].startswith(oldest + "\n\n- **"))
                self.assertEqual(1, changelog.count(oldest))
                for name in SURFACES:
                    data = (self.root / name).read_bytes()
                    self.assertEqual(newline == "\r\n", b"\r\n" in data, name)
                    self.assertEqual(newline == "\n", b"\r\n" not in data and b"\n" in data, name)

                code, out, err = self.run_main("--check")
                self.assertEqual(0, code, err)
                self.assertIn(f"release surfaces agree on {self.new}", out)

    def test_refuses_and_writes_nothing_when_a_surface_disagrees(self) -> None:
        def stale_badge(root: Path) -> None:
            path = root / "README.es.md"
            path.write_bytes(path.read_bytes().replace(f"badge/version-{self.old}-".encode(), b"badge/version-0.0.1-"))

        def stale_lock_package(root: Path) -> None:
            path = root / "package-lock.json"
            text = path.read_text(encoding="utf-8")
            parts = text.split(f'"version": "{self.old}"')
            path.write_text(parts[0] + f'"version": "{self.old}"' + parts[1] + '"version": "0.0.1"'
                            + f'"version": "{self.old}"'.join(parts[2:]), encoding="utf-8")

        def short_history(root: Path) -> None:
            path = root / "README.zh-CN.md"
            text = path.read_text(encoding="utf-8")
            lines = text.split("\n")
            index = max(i for i, line in enumerate(lines) if ENTRY.match(line))
            del lines[index:index + 2]
            path.write_text("\n".join(lines), encoding="utf-8")

        for name, damage, label in (
            ("badge", stale_badge, "README.es.md badge 0.0.1"),
            ("lock package field", stale_lock_package, 'package-lock.json packages[""].version 0.0.1'),
            ("entry count", short_history, "READMEs hold different entry counts"),
        ):
            with self.subTest(case=name):
                self.setUp()
                damage(self.root)
                before = self.snapshot()
                code, out, err = self.run_main("--version", self.new, "--entries", str(self.entries))
                self.assertEqual(1, code)
                self.assertEqual("", out)
                self.assertIn(label, err)
                self.assertEqual(before, self.snapshot())
                code, _, err = self.run_main("--check")
                self.assertEqual(1, code)
                self.assertIn(label, err)

    def test_refuses_bad_versions_and_entries(self) -> None:
        cases = {
            "same version": (lambda: None, self.old, "must be greater"),
            "not semver": (lambda: None, "1.0", "must be X.Y.Z"),
            "missing entry": (lambda: (self.entries / "es.md").unlink(), self.new, "missing entry file"),
            "two lines": (lambda: (self.entries / "en.md").write_text("one\ntwo\n", encoding="utf-8"),
                          self.new, "must be one line"),
            "full entry": (lambda: (self.entries / "en.md").write_text(f"- **{self.new}** — x", encoding="utf-8"),
                           self.new, "only the entry body"),
        }
        for name, (damage, version, message) in cases.items():
            with self.subTest(case=name):
                self.setUp()
                damage()
                before = self.snapshot()
                code, _, err = self.run_main("--version", version, "--entries", str(self.entries))
                self.assertEqual(1, code)
                self.assertIn(message, err)
                self.assertEqual(before, self.snapshot())

    def test_cli_needs_entries_with_version(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "prepare_release.py"), "--root", str(self.root), "--version", self.new],
            capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("--version needs --entries", result.stderr)


if __name__ == "__main__":
    unittest.main()
