import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (
            (candidate / ".agents" / "plugins" / "marketplace.json").is_file()
            and (candidate / "scripts" / "sync_plugin_skills.py").is_file()
        ):
            return candidate
    return None


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
PLUGIN_ROOT = REPO_ROOT / "plugins" / "fullstack-harness" if REPO_ROOT else Path()


@unittest.skipIf(REPO_ROOT is None, "repository contract test requires a source checkout")
class PrivateMarketplaceContractTests(unittest.TestCase):
    def load_json(self, relative_path: str) -> dict:
        return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))

    def test_codex_marketplace_points_to_plugin(self) -> None:
        marketplace = self.load_json(".agents/plugins/marketplace.json")
        self.assertEqual(marketplace["name"], "fullstack-goal-dev")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "fullstack-harness")
        self.assertEqual(entry["source"], {
            "source": "local",
            "path": "./plugins/fullstack-harness",
        })
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")

    def test_runtime_manifests_use_one_version(self) -> None:
        codex = self.load_json("plugins/fullstack-harness/.codex-plugin/plugin.json")
        claude = self.load_json("plugins/fullstack-harness/.claude-plugin/plugin.json")
        marketplace = self.load_json(".claude-plugin/marketplace.json")
        marketplace_plugin = marketplace["plugins"][0]

        self.assertEqual(codex["name"], "fullstack-harness")
        self.assertEqual(claude["name"], "fullstack-harness")
        self.assertEqual(marketplace_plugin["name"], "fullstack-harness")
        self.assertEqual(codex["version"], claude["version"])
        self.assertEqual(codex["version"], marketplace["metadata"]["version"])
        self.assertEqual(codex["version"], marketplace_plugin["version"])
        self.assertEqual(marketplace_plugin["source"], "./plugins/fullstack-harness")

    def test_plugin_bundle_matches_canonical_skills(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/sync_plugin_skills.py", "--check"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_both_runtime_manifests_have_all_skills(self) -> None:
        for skill in (
            "design-package-builder",
            "fullstack-harness-engineering",
            "prd-builder",
        ):
            self.assertTrue((PLUGIN_ROOT / "skills" / skill / "SKILL.md").is_file())

    def test_sync_removes_stale_generated_files(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "sync_plugin_skills", REPO_ROOT / "scripts" / "sync_plugin_skills.py"
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_skill = source_root / "sample"
            destination_skill = destination_root / "sample"
            source_skill.mkdir(parents=True)
            destination_skill.mkdir(parents=True)
            (source_skill / "SKILL.md").write_text("current\n", encoding="utf-8")
            (destination_skill / "stale.txt").write_text("stale\n", encoding="utf-8")
            removed_skill = destination_root / "removed-skill"
            removed_skill.mkdir()
            (removed_skill / "SKILL.md").write_text("removed\n", encoding="utf-8")
            marker = destination_root / ".generated-from-agents-skills"
            marker.write_text("managed\n", encoding="utf-8")

            module.SOURCE_ROOT = source_root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = marker
            module.SKILL_NAMES = ("sample",)
            module.sync()

            self.assertFalse((destination_skill / "stale.txt").exists())
            self.assertFalse(removed_skill.exists())
            self.assertEqual(
                (destination_skill / "SKILL.md").read_text(encoding="utf-8"),
                "current\n",
            )


if __name__ == "__main__":
    unittest.main()
