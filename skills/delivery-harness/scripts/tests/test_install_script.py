import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / "skills" / "delivery-harness" / "SKILL.md").is_file() and (
            candidate / "package.json"
        ).is_file():
            return candidate
    return None


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)


class InstallScriptTests(unittest.TestCase):
    SKILLS = (
        "delivery-harness",
        "product-definition-builder",
        "design-system-compiler",
        "code-security-review",
        "product-activation",
    )

    def setUp(self) -> None:
        if REPO_ROOT is None or not (REPO_ROOT / "install.sh").is_file():
            self.skipTest("no repository checkout with install.sh")
        if shutil.which("bash") is None:
            self.skipTest("bash is not available")
        self._home = tempfile.TemporaryDirectory()
        self.addCleanup(self._home.cleanup)
        self.home = Path(self._home.name)

    def test_installs_five_skills_and_backs_up_existing_copies(self) -> None:
        installed = self.home / ".agents" / "skills"
        installed.mkdir(parents=True)
        legacy = installed / "delivery-harness"
        legacy.mkdir()
        (legacy / "SKILL.md").write_text("old copy", encoding="utf-8")

        env = {**os.environ, "HOME": str(self.home)}
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "install.sh")],
            capture_output=True,
            text=True,
            env=env,
            cwd=self.home,
        )
        self.assertEqual(0, result.returncode, result.stderr)

        source_root = REPO_ROOT / "skills"
        for skill in self.SKILLS:
            with self.subTest(skill=skill):
                self.assertTrue((installed / skill / "SKILL.md").is_file())
                self.assertEqual(
                    (source_root / skill / "SKILL.md").read_bytes(),
                    (installed / skill / "SKILL.md").read_bytes(),
                )
                self.assertEqual(
                    [], list((installed / skill).rglob("__pycache__"))
                )

        backups = list((self.home / ".agents" / "skill-backups").glob("*/*"))
        self.assertEqual(1, len(backups))
        self.assertEqual(
            "old copy", (backups[0] / "delivery-harness" / "SKILL.md").read_text(encoding="utf-8")
        )


if __name__ == "__main__":
    unittest.main()
