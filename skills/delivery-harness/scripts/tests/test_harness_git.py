#!/usr/bin/env python3
"""Adversarial tests for exact-SHA Git object handling."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_git import (  # noqa: E402
    GitConfigurationError,
    GitMetadataError,
    git_environment,
    reject_object_substitution,
    run_git,
)
from harness_core import read_git_blob  # noqa: E402


class HarnessGitTests(unittest.TestCase):
    def test_git_environment_strips_repository_overrides_case_insensitively(self):
        environment = git_environment(
            {
                "Path": "trusted-bin",
                "git_dir": "attacker.git",
                "Git_Work_Tree": "attacker-tree",
                "git_replace_ref_base": "refs/attacker/",
            }
        )
        self.assertEqual("trusted-bin", environment["Path"])
        self.assertEqual("1", environment["GIT_NO_REPLACE_OBJECTS"])
        normalized = {key.upper() for key in environment}
        self.assertNotIn("GIT_DIR", normalized)
        self.assertNotIn("GIT_WORK_TREE", normalized)
        self.assertNotIn("GIT_REPLACE_REF_BASE", normalized)

    def _repo(self, root: Path) -> tuple[str, str]:
        subprocess.run(["git", "init", "-q", "-b", "work"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.invalid"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Harness Test"], cwd=root, check=True
        )
        sample = root / "sample.txt"
        sample.write_text("trusted\n", encoding="utf-8")
        subprocess.run(["git", "add", "sample.txt"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "trusted"], cwd=root, check=True)
        trusted = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
        sample.write_text("substituted\n", encoding="utf-8")
        subprocess.run(["git", "commit", "-qam", "substituted"], cwd=root, check=True)
        substituted = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
        return trusted, substituted

    def test_hardened_read_uses_raw_object_and_rejects_replace_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            trusted, substituted = self._repo(root)
            subprocess.run(["git", "replace", trusted, substituted], cwd=root, check=True)

            ordinary = subprocess.check_output(
                ["git", "show", f"{trusted}:sample.txt"], cwd=root, text=True
            )
            hardened = run_git(root, "show", f"{trusted}:sample.txt")

            self.assertEqual("substituted\n", ordinary)
            self.assertEqual(0, hardened.returncode)
            self.assertEqual("trusted\n", hardened.stdout)
            blob, error = read_git_blob(
                root,
                trusted,
                "sample.txt",
                "missing immutable source",
            )
            self.assertIsNone(blob)
            self.assertIn("replacement refs", error or "")
            with self.assertRaisesRegex(GitMetadataError, "replacement refs"):
                reject_object_substitution(root)

    def test_legacy_graft_metadata_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._repo(root)
            git_dir = Path(
                subprocess.check_output(
                    ["git", "rev-parse", "--absolute-git-dir"], cwd=root, text=True
                ).strip()
            )
            graft = git_dir / "info" / "grafts"
            graft.parent.mkdir(parents=True, exist_ok=True)
            graft.write_text("# unexpected graft metadata\n", encoding="utf-8")

            with self.assertRaisesRegex(GitMetadataError, "graft metadata"):
                reject_object_substitution(root)

    def test_repository_identity_environment_overrides_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            root = Path(first)
            other = Path(second)
            _trusted, root_head = self._repo(root)
            self._repo(other)
            subprocess.run(
                ["git", "commit", "--allow-empty", "-qm", "other identity"],
                cwd=other,
                check=True,
            )
            other_git = subprocess.check_output(
                ["git", "rev-parse", "--absolute-git-dir"], cwd=other, text=True
            ).strip()
            result = run_git(
                root,
                "rev-parse",
                "HEAD",
                environment={
                    **os.environ,
                    "GIT_DIR": other_git,
                    "GIT_WORK_TREE": str(other),
                },
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual(root_head, result.stdout.strip())

    def test_git_environment_strips_config_and_helper_injection_families(self) -> None:
        environment = git_environment(
            {
                "gIt_CoNfIg_CoUnT": "1",
                "GIT_CONFIG_KEY_0": "core.sshCommand",
                "git_config_value_0": "sentinel",
                "GIT_SSH_COMMAND": "sentinel-ssh",
                "git_ssh": "sentinel-ssh",
                "Git_AskPass": "sentinel-askpass",
                "GIT_PROXY_COMMAND": "sentinel-proxy",
                "SSH_ASKPASS": "sentinel-askpass",
            }
        )
        normalized = {key.upper() for key in environment}
        self.assertFalse(
            any(key == "GIT_CONFIG" or key.startswith("GIT_CONFIG_") for key in normalized)
        )
        for key in ("GIT_SSH_COMMAND", "GIT_SSH", "GIT_ASKPASS", "GIT_PROXY_COMMAND", "SSH_ASKPASS"):
            self.assertNotIn(key, normalized)

    def test_local_helper_and_endpoint_rewrite_config_fails_closed_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._repo(root)
            sentinel = root / "sentinel-ran.txt"
            command = f"python -c \"from pathlib import Path; Path(r'{sentinel}').write_text('ran')\""
            subprocess.run(["git", "config", "core.sshCommand", command], cwd=root, check=True)
            with self.assertRaisesRegex(GitConfigurationError, "core.sshcommand"):
                run_git(root, "rev-parse", "HEAD")
            self.assertFalse(sentinel.exists())

            subprocess.run(["git", "config", "--unset", "core.sshCommand"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "url.https://attacker.invalid/.insteadOf", "origin"],
                cwd=root,
                check=True,
            )
            with self.assertRaisesRegex(GitConfigurationError, "insteadof"):
                run_git(root, "remote", "get-url", "origin")

            subprocess.run(
                ["git", "config", "--unset-all", "url.https://attacker.invalid/.insteadOf"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "url.https://attacker.invalid/.pushInsteadOf", "origin"],
                cwd=root,
                check=True,
            )
            with self.assertRaisesRegex(GitConfigurationError, "pushinsteadof"):
                run_git(root, "remote", "get-url", "origin")

            subprocess.run(["git", "config", "--unset-all", "url.https://attacker.invalid/.pushInsteadOf"], cwd=root, check=True)
            subprocess.run(["git", "config", "extensions.worktreeConfig", "true"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "--worktree", "core.sshCommand", command],
                cwd=root,
                check=True,
            )
            with self.assertRaisesRegex(GitConfigurationError, "core.sshcommand"):
                run_git(root, "status", "--porcelain")
            self.assertFalse(sentinel.exists())


if __name__ == "__main__":
    unittest.main()
