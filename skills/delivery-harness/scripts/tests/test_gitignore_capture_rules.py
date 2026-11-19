"""The documented UI capture ignore rules behave as the contract says under real Git."""

from pathlib import Path
import re
import subprocess
import tempfile
import unittest

CONTRACT = Path(__file__).resolve().parents[2] / "references" / "gitignore-contract.md"

LOCAL = (
    "docs/evidence/run-1/surface-1/UI-001-ready-390-0123456789.png",
    "docs/evidence/run-1/surface-1/intermediate/UI-001-ready-795-0123456789.png",
    "docs/evidence/run-1/shot.jpg",
    "docs/evidence/run-1/shot.jpeg",
    "docs/evidence/run-1/shot.webp",
    "docs/design/evidence/run-1/audit/cases/UI-002/capture.png",
    "docs/design/evidence/run-1/motion/clip.webm",
    "docs/design/evidence/run-1/motion/clip.mp4",
    "docs/design/evidence/run-1/checks/stderr.log",
)

TRACKED = (
    "docs/evidence/run-1/surface-1/ui-output.json",
    "docs/evidence/run-1/surface-1/matrix-capture.json",
    "docs/evidence/run-1/browser-receipt.json",
    "docs/design/evidence/run-1/defect-ledger.json",
    "docs/design/evidence/run-1/comparison-sheet.html",
    "docs/design/evidence/run-1/audit/cases/UI-002/dom.html",
    "docs/goal/evidence/parity/home-0123456789-actual.png",
    "docs/verification/evidence/TEST-001-login.png",
    "docs/design/directions/r1/study-a.png",
    "docs/design/ui-references/run-1/index.html",
)


def capture_rules() -> str:
    text = CONTRACT.read_text(encoding="utf-8").replace("\r\n", "\n")
    section = text.split("\n## UI Capture Output\n", 1)[1].split("\n## ", 1)[0]
    blocks = re.findall(r"```gitignore\n(.*?)```", section, re.S)
    if len(blocks) != 1:
        raise AssertionError(f"expected one gitignore block, found {len(blocks)}")
    return blocks[0]


class UiCaptureIgnoreRuleTests(unittest.TestCase):
    def test_raw_captures_are_local_and_records_stay_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=30)
            (root / ".gitignore").write_text(capture_rules(), encoding="utf-8", newline="\n")
            for path, expected in [(p, True) for p in LOCAL] + [(p, False) for p in TRACKED]:
                result = subprocess.run(
                    ["git", "check-ignore", "-q", "--no-index", path],
                    cwd=root, capture_output=True, text=True, timeout=30,
                )
                with self.subTest(path=path):
                    self.assertIn(result.returncode, (0, 1), result.stderr)
                    self.assertEqual(expected, result.returncode == 0)


if __name__ == "__main__":
    unittest.main()
