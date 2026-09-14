#!/usr/bin/env python3
"""Adversarial tests for exact-SHA Git object handling."""

from __future__ import annotations

import os
import ctypes
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


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
                "GIT_SSL_NO_VERIFY": "1",
                "GIT_SSL_CAPATH": "attacker-ca",
            }
        )
        normalized = {key.upper() for key in environment}
        self.assertFalse(
            any(key == "GIT_CONFIG" or key.startswith("GIT_CONFIG_") for key in normalized)
        )
        for key in ("GIT_SSH_COMMAND", "GIT_SSH", "GIT_ASKPASS", "GIT_PROXY_COMMAND", "SSH_ASKPASS", "GIT_SSL_NO_VERIFY", "GIT_SSL_CAPATH"):
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

    def test_local_tls_weakening_is_rejected_and_trusted_global_proxy_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._repo(root)
            subprocess.run(["git", "config", "http.sslVerify", "false"], cwd=root, check=True)
            with self.assertRaisesRegex(GitConfigurationError, "http.sslverify"):
                run_git(root, "rev-parse", "HEAD")

            # System/global corporate proxy configuration is allowed; only
            # repository-local endpoint/config injection is rejected.
            import harness_git as module

            with patch.object(
                module,
                "_raw_git",
                return_value=subprocess.CompletedProcess(
                    ["git", "config"], 0, "file:/etc/gitconfig\x00http.proxy\x00", ""
                ),
            ):
                module.reject_dangerous_local_config(root)

    @unittest.skipUnless(os.name != "nt", "POSIX ownership fixture only")
    def test_git_executable_rejects_writable_parent_component(self) -> None:
        import harness_git as module

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / "git"
            executable.write_bytes(b"fixture")
            executable.chmod(0o755)
            root.chmod(0o777)
            with patch.object(module, "_machine_git_roots", return_value=(root,)):
                with self.assertRaisesRegex(GitMetadataError, "root-owned and not writable"):
                    module._trusted_executable(executable, "Git executable")

    @unittest.skipUnless(os.name == "nt", "Windows machine-root fixture only")
    def test_windows_machine_roots_ignore_spoofed_environment(self) -> None:
        import harness_git as module

        with patch.dict(
            os.environ,
            {"ProgramFiles": str(Path(tempfile.gettempdir()) / "fake-programs"), "SystemRoot": str(Path(tempfile.gettempdir()) / "fake-system")},
            clear=False,
        ):
            roots = module.windows_machine_roots()
        self.assertNotIn(Path(tempfile.gettempdir()).resolve() / "fake-programs", roots)
        self.assertNotIn(Path(tempfile.gettempdir()).resolve() / "fake-system", roots)

    @unittest.skipUnless(os.name == "nt", "Windows ACL fixture only")
    def test_windows_custom_group_write_ace_fails_closed(self) -> None:
        import harness_git as module

        with tempfile.TemporaryDirectory() as temp:
            tool = Path(temp) / "icacls.exe"
            tool.write_bytes(b"trusted")
            for rights in ("(I)(F)", "(I)(WD,AD)", "(I)(GW)"):
                with self.subTest(rights=rights):
                    output = f"C:\\Program Files\\Git\\cmd CUSTOM\\BuildUsers:{rights}\n"
                    with patch.object(module, "windows_icacls_path", return_value=(tool, __import__("hashlib").sha256(tool.read_bytes()).hexdigest())), patch.object(
                        module.subprocess,
                        "run",
                        return_value=subprocess.CompletedProcess([str(tool)], 0, output, ""),
                    ):
                        self.assertTrue(module._windows_parent_user_writable(Path(temp)))

    @unittest.skipUnless(os.name == "nt", "Windows restricted-token fixture only")
    def test_restricted_probe_token_disables_enabled_administrators(self) -> None:
        import harness_git as module
        from ctypes import wintypes

        sid_buffer = ctypes.create_string_buffer(b"fixture-admin-sid")
        get_info = Mock()

        def get_token_information(_token, _kind, buffer, length, returned):
            if buffer is None:
                returned._obj.value = 64
                return False
            ctypes.c_uint32.from_buffer(buffer).value = 1
            ctypes.c_void_p.from_buffer(buffer, 8).value = ctypes.addressof(sid_buffer)
            ctypes.c_uint32.from_buffer(buffer, 8 + ctypes.sizeof(ctypes.c_void_p)).value = 4
            return True

        get_info.side_effect = get_token_information
        convert_sid = Mock(side_effect=lambda _sid, output: (setattr(output._obj, "value", "S-1-5-32-544") or True))
        create_restricted = Mock(side_effect=lambda *_args: (setattr(_args[-1]._obj, "value", 100) or True))
        duplicate = Mock(side_effect=lambda *_args: (setattr(_args[-1]._obj, "value", 200) or True))
        advapi = type("FakeAdvapi", (), {})()
        advapi.GetTokenInformation = get_info
        advapi.ConvertSidToStringSidW = convert_sid
        advapi.CreateRestrictedToken = create_restricted
        advapi.DuplicateTokenEx = duplicate
        kernel32 = type("FakeKernel", (), {"LocalFree": lambda *_: None, "CloseHandle": lambda *_: None})()
        token = module._windows_restricted_probe_token(advapi, kernel32, wintypes.HANDLE(42))
        self.assertEqual(200, token.value)
        create_restricted.assert_called_once()

    @unittest.skipUnless(os.name == "nt", "Windows owner/access fixture only")
    def test_program_files_path_does_not_bypass_native_owner_access_check(self) -> None:
        import harness_git as module

        system_tool = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "icacls.exe"
        with patch.object(
            module,
            "windows_icacls_path",
            return_value=(system_tool, "0" * 64),
        ), patch.object(
            module,
            "_windows_acl_allows_current_write",
            return_value=True,
        ) as access_check:
            self.assertTrue(
                module._windows_parent_user_writable(Path(r"C:\Program Files\OwnedByUser"))
            )
        access_check.assert_called_once()

if __name__ == "__main__":
    unittest.main()
