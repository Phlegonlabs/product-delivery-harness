"""CLI entry points must survive non-UTF-8 consoles by reconfiguring stdio."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ENTRY_MARKER = 'if __name__ == "__main__":'
RECONFIGURE_LOOP = "for stream in (sys.stdout, sys.stderr):"
RECONFIGURE_CALL = 'stream.reconfigure(encoding="utf-8", errors="backslashreplace")'


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (
            (candidate / "skills" / "delivery-harness" / "SKILL.md").is_file()
            and (candidate / "package.json").is_file()
        ):
            return candidate
    raise AssertionError(
        "repository root with skills/delivery-harness/SKILL.md and package.json not found"
    )


class CliUtf8OutputTests(unittest.TestCase):
    def test_every_cli_entry_point_writes_utf8(self) -> None:
        root = _repo_root()
        checked: list[str] = []
        failing: list[str] = []
        for path in sorted(root.glob("skills/*/scripts/*.py")):
            text = path.read_text(encoding="utf-8")
            if "\ndef main(" not in text:
                continue
            relative = path.relative_to(root).as_posix()
            checked.append(relative)
            problems: list[str] = []
            if ENTRY_MARKER not in text:
                problems.append("missing __main__ entry block")
            else:
                tail = text.rsplit(ENTRY_MARKER, 1)[1]
                if RECONFIGURE_LOOP not in tail:
                    problems.append("missing stdout/stderr reconfigure loop")
                if RECONFIGURE_CALL not in tail:
                    problems.append("missing utf-8 reconfigure call")
            if "import sys" not in text.splitlines():
                problems.append("missing a line exactly 'import sys'")
            if problems:
                failing.append(f"{relative}: {'; '.join(problems)}")
        self.assertGreaterEqual(
            len(checked), 50, "expected at least 50 CLI entry points"
        )
        self.assertEqual([], failing, "CLI entry points missing UTF-8 stdio setup")

    def test_cjk_findings_survive_non_utf8_stdout(self) -> None:
        root = _repo_root()
        template = (
            root / "skills/product-activation/assets/templates/ACTIVATION.template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("- Status: seeded", template)
        with tempfile.TemporaryDirectory() as temporary_directory:
            activation = Path(temporary_directory) / "ACTIVATION.md"
            activation.write_text(
                template.replace("- Status: seeded", "- Status: 準備中", 1),
                encoding="utf-8",
            )
            environment = dict(os.environ)
            environment["PYTHONIOENCODING"] = "cp1252"
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "skills/product-activation/scripts/check_activation.py"),
                    "--activation",
                    str(activation),
                ],
                capture_output=True,
                timeout=120,
                check=False,
                env=environment,
            )
        self.assertEqual(1, result.returncode)
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertIn("準備中", result.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
