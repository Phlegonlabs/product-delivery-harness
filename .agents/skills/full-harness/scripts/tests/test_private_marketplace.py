import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
    def load_sync_module(self):
        """Import scripts/sync_plugin_skills.py as a module under its real path."""
        spec = importlib.util.spec_from_file_location(
            "sync_plugin_skills", REPO_ROOT / "scripts" / "sync_plugin_skills.py"
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

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
        self.assertEqual(codex["version"], "0.20.1")
        self.assertEqual(marketplace_plugin["source"], "./plugins/fullstack-harness")

        pi_package = self.load_json("package.json")
        self.assertEqual(pi_package["version"], codex["version"])
        self.assertEqual(pi_package["type"], "commonjs")
        self.assertEqual(pi_package["pi"]["skills"], ["./.agents/skills"])

    def test_updater_covers_all_hosts_without_silent_pi_migration(self) -> None:
        updater = (REPO_ROOT / "scripts" / "update-private-skills.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("[switch]$UpdateHostRuntimes", updater)
        self.assertIn("[switch]$ReplacePiStandaloneSkills", updater)
        self.assertIn("Invoke-Checked codex update", updater)
        self.assertIn("Invoke-Checked claude update", updater)
        self.assertIn("Invoke-Checked pi update --self --no-approve", updater)
        self.assertIn("Codex marketplace is local; using its current checkout.", updater)
        self.assertIn("Claude marketplace is local; using its current checkout.", updater)
        self.assertIn("Invoke-Checked pi install $PiSource --no-approve", updater)
        self.assertIn("Invoke-Checked pi remove $installedPiSource --no-approve", updater)
        self.assertIn("restoring $installedPiSource", updater)
        self.assertIn("Standalone Pi Harness skills can shadow", updater)
        self.assertIn("Move-Item -LiteralPath $destinationSkill", updater)

    def test_sync_removes_stale_generated_files(self) -> None:
        module = self.load_sync_module()

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
            module.REPO_ROOT = root
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

    def test_sync_treats_windows_junctions_as_links(self) -> None:
        module = self.load_sync_module()

        junction = Path("junction")
        with mock.patch.object(Path, "is_symlink", return_value=False):
            with mock.patch.object(Path, "is_junction", return_value=True):
                self.assertTrue(module.is_link(junction))

    def test_sync_refuses_symlinked_marker_without_writing(self) -> None:
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_skill = source_root / "sample"
            source_skill.mkdir(parents=True)
            (source_skill / "SKILL.md").write_text("current\n", encoding="utf-8")
            destination_root.mkdir()
            marker = destination_root / ".generated-from-agents-skills"
            marker.write_text("external target stays unchanged\n", encoding="utf-8")

            module.SOURCE_ROOT = source_root
            module.REPO_ROOT = root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = marker
            module.SKILL_NAMES = ("sample",)

            original_is_symlink = Path.is_symlink

            def marker_is_symlink(path: Path) -> bool:
                return path == marker or original_is_symlink(path)

            with mock.patch.object(Path, "is_symlink", marker_is_symlink):
                with self.assertRaisesRegex(SystemExit, "symlinked marker"):
                    module.sync()

            self.assertEqual(
                marker.read_text(encoding="utf-8"),
                "external target stays unchanged\n",
            )

    def test_sync_refuses_symlinked_destination_root_without_writing(self) -> None:
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_skill = source_root / "sample"
            source_skill.mkdir(parents=True)
            (source_skill / "SKILL.md").write_text("current\n", encoding="utf-8")
            destination_root.mkdir()
            sentinel = destination_root / "important.txt"
            sentinel.write_text("external data stays unchanged\n", encoding="utf-8")

            module.SOURCE_ROOT = source_root
            module.REPO_ROOT = root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = destination_root / ".generated-from-agents-skills"
            module.SKILL_NAMES = ("sample",)

            original_is_symlink = Path.is_symlink

            def root_is_symlink(path: Path) -> bool:
                return path == destination_root or original_is_symlink(path)

            with mock.patch.object(Path, "is_symlink", root_is_symlink):
                with self.assertRaisesRegex(SystemExit, "symlinked destination root"):
                    module.sync()

            self.assertEqual(
                sentinel.read_text(encoding="utf-8"),
                "external data stays unchanged\n",
            )

    def test_check_requires_generated_marker(self) -> None:
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_skill = source_root / "sample"
            destination_skill = destination_root / "sample"
            source_skill.mkdir(parents=True)
            destination_skill.mkdir(parents=True)
            (source_skill / "SKILL.md").write_text("current\n", encoding="utf-8")
            (destination_skill / "SKILL.md").write_text("current\n", encoding="utf-8")

            module.REPO_ROOT = root
            module.SOURCE_ROOT = source_root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = destination_root / ".generated-from-agents-skills"
            module.SKILL_NAMES = ("sample",)

            self.assertIn(
                "missing: .generated-from-agents-skills",
                module.differences(),
            )

    def test_check_reports_a_source_skill_missing_from_skill_names(self) -> None:
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_skill = source_root / "sample"
            unlisted_skill = source_root / "new-skill"
            destination_skill = destination_root / "sample"
            source_skill.mkdir(parents=True)
            unlisted_skill.mkdir(parents=True)
            destination_skill.mkdir(parents=True)
            (source_skill / "SKILL.md").write_text("current\n", encoding="utf-8")
            (unlisted_skill / "SKILL.md").write_text("new\n", encoding="utf-8")
            (destination_skill / "SKILL.md").write_text("current\n", encoding="utf-8")
            marker = destination_root / ".generated-from-agents-skills"
            marker.write_text("generated\n", encoding="utf-8")

            module.REPO_ROOT = root
            module.SOURCE_ROOT = source_root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = marker
            module.SKILL_NAMES = ("sample",)

            self.assertIn("unlisted source skill: new-skill", module.differences())

    def test_sync_keeps_bytecode_out_of_the_bundle(self) -> None:
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_skill = source_root / "sample"
            source_scripts = source_skill / "scripts"
            source_scripts.mkdir(parents=True)
            (source_skill / "SKILL.md").write_text("current\n", encoding="utf-8")
            (source_scripts / "tool.py").write_text("print('hi')\n", encoding="utf-8")
            cache = source_scripts / "__pycache__"
            cache.mkdir()
            (cache / "tool.cpython-314.pyc").write_bytes(b"\x00stale")
            destination_root.mkdir(parents=True)
            marker = destination_root / ".generated-from-agents-skills"
            marker.write_text("managed\n", encoding="utf-8")

            module.REPO_ROOT = root
            module.SOURCE_ROOT = source_root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = marker
            module.SKILL_NAMES = ("sample",)
            module.sync()

            self.assertTrue(
                (destination_root / "sample" / "scripts" / "tool.py").is_file()
            )
            self.assertEqual(
                [], list(destination_root.rglob("*.pyc")) + list(destination_root.rglob("__pycache__"))
            )

    def test_check_ignores_runtime_bytecode_in_the_bundle(self) -> None:
        """Running the packaged smoke test imports the bundle and writes
        __pycache__ beside it; that runtime bytecode is not bundle drift, or
        every --check after a local packaged-test run fails on it."""
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_scripts = source_root / "sample" / "scripts"
            source_scripts.mkdir(parents=True)
            (source_root / "sample" / "SKILL.md").write_text("current\n", encoding="utf-8")
            (source_scripts / "tool.py").write_text("print('hi')\n", encoding="utf-8")
            destination_root.mkdir(parents=True)
            marker = destination_root / ".generated-from-agents-skills"
            marker.write_text("managed\n", encoding="utf-8")

            module.REPO_ROOT = root
            module.SOURCE_ROOT = source_root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = marker
            module.SKILL_NAMES = ("sample",)
            module.sync()

            cache = destination_root / "sample" / "scripts" / "__pycache__"
            cache.mkdir()
            (cache / "tool.cpython-313.pyc").write_bytes(b"\x00runtime")
            (destination_root / "sample" / "scripts" / "orphan.pyc").write_bytes(b"\x00runtime")

            self.assertEqual([], module.differences())

    def test_sync_ships_only_the_packaged_smoke_test(self) -> None:
        """Test suites run against `.agents/`, so mirroring them doubles the
        bundle for nothing. The packaged smoke test is the exception: it exists
        to run against the bundle's own layout, and CI discovers it there."""
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_tests = source_root / "sample" / "scripts" / "tests"
            source_tests.mkdir(parents=True)
            (source_root / "sample" / "SKILL.md").write_text("current\n", encoding="utf-8")
            (source_tests / "__init__.py").write_text("", encoding="utf-8")
            (source_tests / "test_packaged_smoke.py").write_text("# keep\n", encoding="utf-8")
            (source_tests / "test_harness_manifest.py").write_text("# drop\n", encoding="utf-8")
            (source_tests / "conftest.py").write_text("# drop\n", encoding="utf-8")
            destination_root.mkdir(parents=True)
            marker = destination_root / ".generated-from-agents-skills"
            marker.write_text("managed\n", encoding="utf-8")

            module.REPO_ROOT = root
            module.SOURCE_ROOT = source_root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = marker
            module.SKILL_NAMES = ("sample",)
            module.sync()

            bundled_tests = destination_root / "sample" / "scripts" / "tests"
            self.assertEqual(
                ["__init__.py", "test_packaged_smoke.py"],
                sorted(path.name for path in bundled_tests.iterdir()),
            )
            # sync and --check must agree, or a synced bundle reports as stale.
            self.assertEqual([], module.differences())

    def test_check_and_sync_remove_excluded_destination_test_drift(self) -> None:
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_tests = source_root / "sample" / "scripts" / "tests"
            source_tests.mkdir(parents=True)
            (source_root / "sample" / "SKILL.md").write_text(
                "current\n", encoding="utf-8"
            )
            # This remains intentionally excluded from source bundling.
            (source_tests / "stale_test.py").write_text(
                "# canonical test-only file\n", encoding="utf-8"
            )
            destination_root.mkdir(parents=True)
            marker = destination_root / ".generated-from-agents-skills"
            marker.write_text("managed\n", encoding="utf-8")

            module.REPO_ROOT = root
            module.SOURCE_ROOT = source_root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = marker
            module.SKILL_NAMES = ("sample",)
            module.sync()

            stale_destination = (
                destination_root
                / "sample"
                / "scripts"
                / "tests"
                / "stale_test.py"
            )
            stale_destination.parent.mkdir(parents=True, exist_ok=True)
            stale_destination.write_text("# stale generated copy\n", encoding="utf-8")

            self.assertIn(
                "extra: sample/scripts/tests/stale_test.py",
                module.differences(),
            )

            module.sync()
            self.assertFalse(stale_destination.exists())
            self.assertEqual([], module.differences())

    def test_check_rejects_symlinked_bundle_entries(self) -> None:
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_skill = source_root / "sample"
            destination_skill = destination_root / "sample"
            source_skill.mkdir(parents=True)
            destination_skill.mkdir(parents=True)
            (source_skill / "SKILL.md").write_text("current\n", encoding="utf-8")
            destination_file = destination_skill / "SKILL.md"
            destination_file.write_text("current\n", encoding="utf-8")
            marker = destination_root / ".generated-from-agents-skills"
            marker.write_text("managed\n", encoding="utf-8")

            module.REPO_ROOT = root
            module.SOURCE_ROOT = source_root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = marker
            module.SKILL_NAMES = ("sample",)

            original_is_symlink = Path.is_symlink

            def bundle_file_is_symlink(path: Path) -> bool:
                return path == destination_file or original_is_symlink(path)

            with mock.patch.object(Path, "is_symlink", bundle_file_is_symlink):
                self.assertIn("symlink: sample/SKILL.md", module.differences())

    def test_sync_refuses_symlinked_destination_ancestor_without_writing(self) -> None:
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_parent = root / "plugin"
            destination_root = destination_parent / "skills"
            source_skill = source_root / "sample"
            source_skill.mkdir(parents=True)
            destination_root.mkdir(parents=True)
            (source_skill / "SKILL.md").write_text("current\n", encoding="utf-8")
            marker = destination_root / ".generated-from-agents-skills"
            marker.write_text("managed\n", encoding="utf-8")
            sentinel = destination_root / "important.txt"
            sentinel.write_text("external data stays unchanged\n", encoding="utf-8")

            module.REPO_ROOT = root
            module.SOURCE_ROOT = source_root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = marker
            module.SKILL_NAMES = ("sample",)

            original_is_symlink = Path.is_symlink

            def ancestor_is_symlink(path: Path) -> bool:
                return path == destination_parent or original_is_symlink(path)

            with mock.patch.object(Path, "is_symlink", ancestor_is_symlink):
                with self.assertRaisesRegex(SystemExit, "symlinked destination ancestor"):
                    module.sync()

            self.assertEqual(
                sentinel.read_text(encoding="utf-8"),
                "external data stays unchanged\n",
            )

    def test_check_and_sync_reject_symlinked_source_entry_without_writing(self) -> None:
        module = self.load_sync_module()

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "source"
            destination_root = root / "destination"
            source_skill = source_root / "sample"
            destination_skill = destination_root / "sample"
            source_skill.mkdir(parents=True)
            destination_skill.mkdir(parents=True)
            source_file = source_skill / "SKILL.md"
            source_file.write_text("current\n", encoding="utf-8")
            (destination_skill / "SKILL.md").write_text("current\n", encoding="utf-8")
            marker = destination_root / ".generated-from-agents-skills"
            marker.write_text("managed\n", encoding="utf-8")
            sentinel = destination_root / "important.txt"
            sentinel.write_text("destination stays unchanged\n", encoding="utf-8")

            module.REPO_ROOT = root
            module.SOURCE_ROOT = source_root
            module.DESTINATION_ROOT = destination_root
            module.MARKER = marker
            module.SKILL_NAMES = ("sample",)

            original_is_symlink = Path.is_symlink

            def source_file_is_symlink(path: Path) -> bool:
                return path == source_file or original_is_symlink(path)

            with mock.patch.object(Path, "is_symlink", source_file_is_symlink):
                self.assertIn(
                    "source symlink: sample/SKILL.md",
                    module.differences(),
                )
                with self.assertRaisesRegex(
                    SystemExit, "Canonical skill contains symlinks"
                ):
                    module.sync()

            self.assertEqual(
                sentinel.read_text(encoding="utf-8"),
                "destination stays unchanged\n",
            )


if __name__ == "__main__":
    unittest.main()
