"""Behavior checks for the standalone npm README verifier.

Optional retained-archive replay (four offline npm installs):
python skills/delivery-harness/scripts/tests/test_npm_readme_artifact.py --archives <run-directory>
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[4]
SKILL = ROOT / "standalone-skills/release-packager"
HELPER = SKILL / "scripts/check_npm_readme.py"
SPEC = importlib.util.spec_from_file_location("npm_readme_verifier", HELPER)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)
NAME = "synthetic-asset-release-fixture"
README = f'''# Fixture
<picture>
<source media="(prefers-color-scheme: dark)" srcset="assets/dark.svg">
<img src="assets/light.svg" alt="Mark">
</picture>
```sh
{NAME} hello input.txt
```
'''
CLI = '''const fs = require('node:fs');
const [command, input] = process.argv.slice(2);
if (command !== 'hello') { process.stderr.write('Unsupported command'); process.exitCode = 2; }
else console.log('Hello, ' + fs.readFileSync(input, 'utf8').trim() + '!');
'''


def review_for(artifact, argv=None, stdout="Hello, fixture!\n"):
    return {"artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "argv": argv or [NAME, "hello", "input.txt"], "stdout": stdout,
            "offline_code_reviewed": True}


class NpmReadmeArtifactTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="pdh-npm-readme-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.consumer = self.root / "consumer"
        self.consumer.mkdir()
        (self.consumer / "input.txt").write_text("fixture\n", encoding="utf-8")
        self.manifest = {"name": NAME, "version": "1.0.0", "bin": {NAME: "bin/cli.cjs"}}
        self.files = {"README.md": README.encode(), "bin/cli.cjs": CLI.encode(),
                      "assets/light.svg": b"<svg/>", "assets/dark.svg": b"<svg/>"}

    def prepare(self):
        self.files["package.json"] = json.dumps(self.manifest).encode()
        artifact = self.root / "fixture.tgz"
        with tarfile.open(artifact, "w:gz") as archive:
            for name, data in self.files.items():
                member = tarfile.TarInfo("package/" + name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        package = self.consumer / "node_modules" / self.manifest["name"]
        for name, data in self.files.items():
            path = package / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return artifact, package

    def verify(self, **kwargs):
        artifact, _ = self.prepare()
        return CHECK.verify(artifact, self.consumer, review_for(artifact), **kwargs)

    def test_html_dark_source_and_installed_useful_command(self):
        result = self.verify()
        self.assertEqual(result["cli"]["status"], "passed")
        self.assertEqual(result["images"]["local"], ["assets/dark.svg", "assets/light.svg"])

    def test_missing_dark_archive_asset_fails_despite_source_asset(self):
        (self.root / "dark.svg").write_text("source copy", encoding="utf-8")
        del self.files["assets/dark.svg"]
        with self.assertRaisesRegex(CHECK.CheckError, "missing packaged README image: assets/dark.svg"):
            self.verify()

    def test_wrong_documented_command_cannot_reuse_good_approval(self):
        self.files["README.md"] = README.replace(" hello ", " greet ").encode()
        with self.assertRaisesRegex(CHECK.CheckError, "reviewed argv differs"):
            self.verify()

    def test_explicitly_reviewed_wrong_command_reaches_installed_cli_and_fails(self):
        self.files["README.md"] = README.replace(" hello ", " greet ").encode()
        artifact, _ = self.prepare()
        with self.assertRaisesRegex(CHECK.CheckError, "documented CLI failed with exit 2"):
            CHECK.verify(artifact, self.consumer, review_for(artifact, [NAME, "greet", "input.txt"]))

    def test_stdout_must_prove_the_useful_behavior(self):
        artifact, _ = self.prepare()
        with self.assertRaisesRegex(CHECK.CheckError, "stdout differs"):
            CHECK.verify(artifact, self.consumer, review_for(artifact, stdout="wrong\n"))

    def test_markdown_inline_reference_encoded_paths_and_srcset(self):
        self.files["README.md"] = (README + '''
![Light](./assets/light.svg?raw=1#mark "Title")
![Dark][night]
[night]: <assets/dark.svg>
![Space](<assets/with space.svg>)
<img srcset="assets/light.svg 1x, assets/dark.svg 2x">
![Remote](https://example.invalid/image.svg)
''').encode()
        self.files["assets/with space.svg"] = b"<svg/>"
        result = self.verify()
        self.assertEqual(result["images"]["external_unverified"], ["https://example.invalid/image.svg"])
        self.assertIn("assets/with space.svg", result["images"]["local"])

    def test_scoped_string_bin_and_esm_package(self):
        self.manifest.update(name="@fixture/" + NAME, type="module", bin="bin/cli.js")
        del self.files["bin/cli.cjs"]
        self.files["bin/cli.js"] = CLI.replace("const fs = require('node:fs');", "import fs from 'node:fs';").encode()
        self.assertEqual(self.verify()["cli"]["exit_code"], 0)

    def test_library_cli_is_not_applicable_without_claiming_import_verification(self):
        del self.manifest["bin"]
        artifact, _ = self.prepare()
        result = CHECK.verify(artifact, self.consumer)
        self.assertEqual(result["cli"]["status"], "not_applicable")
        self.assertIn("separate", result["cli"]["reason"])

    def test_applicable_inputs_cannot_silently_skip(self):
        artifact, _ = self.prepare()
        with self.assertRaisesRegex(CHECK.CheckError, "review must bind"):
            CHECK.verify(artifact, self.consumer)
        with self.assertRaisesRegex(CHECK.CheckError, "isolated installed consumer"):
            CHECK.verify(artifact, None)
        approval = review_for(artifact)
        approval["offline_code_reviewed"] = False
        with self.assertRaisesRegex(CHECK.CheckError, "offline execution"):
            CHECK.verify(artifact, self.consumer, approval)

    def test_unsupported_bins_and_non_useful_examples_fail(self):
        self.manifest["bin"][NAME] = "bin/native.exe"
        self.files["bin/native.exe"] = b"not executable"
        with self.assertRaisesRegex(CHECK.CheckError, "only Node JS CLI bins"):
            self.verify()
        self.manifest["bin"][NAME] = "bin/cli.cjs"
        self.files["README.md"] = README.replace("hello input.txt", "--version").encode()
        with self.assertRaisesRegex(CHECK.CheckError, "no supported useful direct CLI example"):
            self.verify()

    def test_npx_or_unfenced_example_is_unresolved(self):
        for readme in (README.replace(NAME + " hello", "npx " + NAME + " hello"),
                       README.replace("```sh\n", "").replace("```\n", "")):
            with self.subTest(readme=readme):
                self.files["README.md"] = readme.encode()
                with self.assertRaisesRegex(CHECK.CheckError, "no supported useful direct CLI example"):
                    self.verify()

    def test_unparseable_applicable_readme_is_a_failure(self):
        for readme in (README + "![x](assets/nested(name).svg)",
                       README + "![x][undefined]", README + "```sh\nunterminated",
                       README.replace('srcset="assets/dark.svg"', 'srcset="assets/dark.svg nope"'),
                       README.replace("hello input.txt", "hello 'input.txt"),
                       README + '<img src="assets/missing.svg"',
                       README + "![x](\n[x]: assets/light.svg\n"):
            with self.subTest(readme=readme):
                self.files["README.md"] = readme.encode()
                with self.assertRaises(CHECK.CheckError):
                    self.verify()

    def test_implicit_cli_and_missing_node_cannot_be_reported_as_not_applicable(self):
        artifact, _ = self.prepare()
        with patch.object(CHECK.shutil, "which", return_value=None):
            with self.assertRaisesRegex(CHECK.CheckError, "Node is required"):
                CHECK.verify(artifact, self.consumer, review_for(artifact))
        del self.manifest["bin"]
        self.manifest["directories"] = {"bin": "bin"}
        with self.assertRaisesRegex(CHECK.CheckError, "implicit directories.bin"):
            self.verify()

    def test_node_options_preload_is_not_inherited(self):
        poison = self.root / "poison.cjs"
        poison.write_text("process.exit(77);", encoding="utf-8")
        with patch.dict(os.environ, {"NODE_OPTIONS": "--require " + str(poison), "NODE_PATH": str(self.root)}):
            self.assertEqual(self.verify()["cli"]["status"], "passed")

    def test_missing_readme_case_sensitive_images_and_traversal(self):
        for readme in (None, README.replace("dark.svg", "Dark.svg"),
                       README.replace("assets/dark.svg", "../dark.svg")):
            with self.subTest(readme=readme):
                self.files.pop("README.md", None)
                if readme is not None:
                    self.files["README.md"] = readme.encode()
                with self.assertRaises(CHECK.CheckError):
                    self.verify()

    def test_installed_bytes_cannot_be_masked_by_a_source_or_global_cli(self):
        artifact, package = self.prepare()
        (package / "bin/cli.cjs").write_text("console.log('Hello, fixture!');", encoding="utf-8")
        with self.assertRaisesRegex(CHECK.CheckError, "installed bytes differ"):
            CHECK.verify(artifact, self.consumer, review_for(artifact))

    def test_archive_links_and_traversal_are_rejected_without_extracting(self):
        artifact, _ = self.prepare()
        for name, kind in (("package/../escape", tarfile.REGTYPE), ("package/link", tarfile.SYMTYPE)):
            with self.subTest(name=name):
                with tarfile.open(artifact, "w:gz") as archive:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = "../../outside"
                    archive.addfile(member)
                with self.assertRaises(CHECK.CheckError):
                    CHECK.verify(artifact, self.consumer)
        self.assertFalse((self.root / "escape").exists())

    def test_shell_syntax_is_never_executed(self):
        self.files["README.md"] = README.replace("hello input.txt", "hello input.txt; touch marker").encode()
        with self.assertRaisesRegex(CHECK.CheckError, "shell syntax"):
            self.verify()
        self.assertFalse((self.consumer / "marker").exists())

    def test_other_readme_chunks_and_lifecycle_scripts_are_never_executed(self):
        self.files["README.md"] = (README + "```sh\nnode -e \"require('fs').writeFileSync('marker', '')\"\n```\n").encode()
        self.manifest["scripts"] = {"postinstall": "node -e \"require('fs').writeFileSync('marker', '')\""}
        self.verify()
        self.assertFalse((self.consumer / "marker").exists())

    def test_network_and_child_process_apis_are_blocked(self):
        for source in ("require('node:dns').lookup('example.invalid', () => {});",
                       "import {lookup} from 'node:dns'; lookup('example.invalid', () => {});",
                       "fetch('https://example.invalid');",
                       "require('node:child_process').spawnSync(process.execPath, ['--version']);"):
            with self.subTest(source=source):
                self.files["bin/cli.cjs"] = source.encode()
                if source.startswith("import"):
                    self.manifest["bin"][NAME] = "bin/cli.mjs"
                    self.files["bin/cli.mjs"] = source.encode()
                else:
                    self.manifest["bin"][NAME] = "bin/cli.cjs"
                expected = "ERR_ACCESS_DENIED" if "child_process" in source else "network access is disabled"
                with self.assertRaisesRegex(CHECK.CheckError, expected):
                    self.verify()

    def test_cli_deadline_is_enforced(self):
        self.files["bin/cli.cjs"] = b"while (true) {}"
        with self.assertRaisesRegex(CHECK.CheckError, "deadline"):
            self.verify(timeout=0.2)

    def test_cli_cannot_write_into_the_consumer(self):
        self.files["bin/cli.cjs"] = b"require('node:fs').writeFileSync('marker', 'unexpected');"
        with self.assertRaisesRegex(CHECK.CheckError, "ERR_ACCESS_DENIED"):
            self.verify()
        self.assertFalse((self.consumer / "marker").exists())

    def test_stale_review_hash_fails_and_cli_entry_returns_nonzero(self):
        artifact, _ = self.prepare()
        approval = review_for(artifact)
        approval["artifact_sha256"] = "0" * 64
        review = self.root / "review.json"
        review.write_text(json.dumps(approval), encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", str(HELPER), "--tarball", str(artifact),
                                 "--consumer", str(self.consumer), "--review", str(review)],
                                capture_output=True, text=True, encoding="utf-8", timeout=15, shell=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "failed")

    def test_normal_npm_verification_requires_executable_helper(self):
        for relative in ("SKILL.md", "references/runtime-packaging.md", "references/artifact-checks.md"):
            self.assertIn("check_npm_readme.py", (SKILL / relative).read_text(encoding="utf-8"))


def replay_archives(directory):
    """Install retained bytes offline; never rerun the old source scenario."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node is required for retained-archive replay")
    npm = Path(node).parent / "node_modules/npm/bin/npm-cli.js"
    if not npm.is_file():
        raise RuntimeError("expected local npm-cli.js beside Node")
    for case in ("good", "bad-asset-inclusion", "bad-derived-command", "restored"):
        artifact = (directory / (case + ".tgz")).resolve()
        with tempfile.TemporaryDirectory(prefix="pdh-npm-archive-") as temporary:
            root = Path(temporary)
            consumer = root / "consumer"
            consumer.mkdir()
            (consumer / "package.json").write_text('{"private":true}', encoding="utf-8")
            (consumer / "input.txt").write_text("fixture\n", encoding="utf-8")
            for filename in ("user.npmrc", "global.npmrc"):
                (root / filename).write_text("", encoding="utf-8")
            env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP", "PATH") if key in os.environ}
            env.update(npm_config_cache=str(root / "cache"), npm_config_offline="true",
                       npm_config_userconfig=str(root / "user.npmrc"),
                       npm_config_globalconfig=str(root / "global.npmrc"),
                       npm_config_update_notifier="false")
            with (root / "install.log").open("wb") as log:
                result = subprocess.run([node, str(npm), "install", str(artifact), "--offline", "--ignore-scripts",
                                         "--no-audit", "--no-fund", "--package-lock=false"],
                                        cwd=consumer, env=env, stdout=log, stderr=subprocess.STDOUT,
                                        timeout=30, shell=False)
            if result.returncode:
                raise RuntimeError("offline install failed: " + (root / "install.log").read_text()[-2000:])
            argv = [NAME, "greet" if case == "bad-derived-command" else "hello", "input.txt"]
            approval = review_for(artifact, argv)
            review = root / "review.json"
            review.write_text(json.dumps(approval), encoding="utf-8")
            result = subprocess.run([sys.executable, "-B", str(HELPER), "--tarball", str(artifact),
                                     "--consumer", str(consumer), "--review", str(review), "--timeout", "5"],
                                    capture_output=True, text=True, encoding="utf-8", timeout=15, shell=False)
            report = json.loads(result.stdout)
            expected_code = 1 if case.startswith("bad-") else 0
            if result.returncode != expected_code:
                raise AssertionError((case, result.returncode, report))
            if case == "bad-asset-inclusion" and "logo-dark.svg" not in report.get("error", ""):
                raise AssertionError(report)
            if case == "bad-derived-command" and "exit 2" not in report.get("error", ""):
                raise AssertionError(report)
            print(json.dumps({"case": case, "helper_exit": result.returncode,
                              "artifact_sha256": approval["artifact_sha256"], "report": report}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--archives", type=Path)
    options, remaining = parser.parse_known_args()
    if options.archives:
        replay_archives(options.archives)
    else:
        unittest.main(argv=[sys.argv[0], *remaining])
