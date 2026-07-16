import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "fullstack-harness"


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


if __name__ == "__main__":
    unittest.main()
