"""Non-secret policy binding and isolated credential helper wiring."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import publication_credentials as subject
import push_archived_candidate as archive
import trusted_host_publication as host
from harness_core import ManifestError
from harness_git import git_executable

URL = "https://example.invalid/team/private.git"


class CredentialTests(unittest.TestCase):
    def test_real_git_uses_only_the_approved_helper_in_a_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="credential fixture ") as temp:
            root = Path(temp)
            helper = root / "fixture helper.sh"
            helper.write_text("#!/bin/sh\nprintf 'username=fixture-user\\npassword=fixture-only\\n'\n", encoding="utf-8")
            helper.chmod(0o755)
            binding = {"helper": helper.as_posix(), "endpoint": URL,
                       "helper_sha256": hashlib.sha256(helper.read_bytes()).hexdigest(),
                       "policy_sha256": "a" * 64}
            with patch.object(subject, "credential_binding", return_value=binding):
                env = subject.publication_environment(URL, expected=binding)
            result = subprocess.run([git_executable(), "credential", "fill"], cwd=root, env=env,
                                    input="protocol=https\nhost=example.invalid\npath=team/private.git\n\n",
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(0, result.returncode, "isolated fixture helper failed")
            self.assertIn("username=fixture-user", result.stdout)
            self.assertIn("password=fixture-only", result.stdout)

    def test_policy_hash_endpoint_and_helper_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            helper = Path(temp) / "trusted helper.exe"
            helper.write_bytes(b"fixture executable")
            policy = {"endpoints": [URL], "helper": str(helper),
                      "sha256": hashlib.sha256(helper.read_bytes()).hexdigest()}
            def payload():
                return json.dumps(policy).encode()
            with patch.object(subject, "_policy_bytes", side_effect=payload), patch.object(
                subject, "_trusted_executable", return_value=helper
            ):
                binding = subject.credential_binding(URL)
                self.assertEqual(URL, binding["endpoint"])
                self.assertIsNone(subject.credential_binding(URL + "/other"))
                with patch.dict(os.environ, {"GIT_CONFIG_COUNT": "99", "GIT_ASKPASS": "evil",
                                             "GIT_CONFIG_GLOBAL": "evil", "GIT_TRACE_CURL": "trace.log",
                                             "GCM_TRACE_SECRETS": "1", "GIT_CURL_VERBOSE": "1"}):
                    env = subject.publication_environment(URL, expected=binding)
                self.assertEqual("4", env["GIT_CONFIG_COUNT"])
                self.assertEqual("http.followRedirects", env["GIT_CONFIG_KEY_3"])
                self.assertEqual("false", env["GIT_CONFIG_VALUE_3"])
                self.assertNotIn("GIT_ASKPASS", env)
                self.assertFalse(any(key.startswith(("GIT_TRACE", "GCM_TRACE")) for key in env))
                self.assertNotIn("GIT_CURL_VERBOSE", env)
                self.assertEqual("0", env["GIT_TERMINAL_PROMPT"])
                self.assertIn(helper.as_posix(), env["GIT_CONFIG_VALUE_1"])
                policy["endpoints"].append(URL + "/other")
                with self.assertRaisesRegex(ManifestError, "changed"):
                    subject.publication_environment(URL, expected=binding)
                helper.write_bytes(b"changed")
                with self.assertRaises(ManifestError):
                    subject.credential_binding(URL)

    def test_missing_policy_cannot_be_injected_or_enable_old_request(self):
        with patch.object(subject, "_policy_bytes", return_value=None):
            env = subject.publication_environment(URL, expected=None)
            self.assertNotIn("GIT_CONFIG_COUNT", env)
        with patch.object(subject, "credential_binding", return_value={"helper": "new"}):
            with self.assertRaisesRegex(ManifestError, "changed"):
                subject.publication_environment(URL, expected=None)

    def test_user_writable_or_relative_helper_is_rejected(self):
        for helper in ("relative-helper", str(Path.cwd() / "helper.exe")):
            payload = json.dumps({"helper": helper, "sha256": "a" * 64, "endpoints": [URL]}).encode()
            with patch.object(subject, "_policy_bytes", return_value=payload):
                with self.assertRaises((ManifestError, RuntimeError)):
                    subject.credential_binding(URL)

    def test_private_read_paths_pass_bound_credentials_to_isolated_git(self):
        binding = {"policy_sha256": "a" * 64, "helper": "/trusted/helper",
                   "helper_sha256": "b" * 64, "endpoint": URL}
        completed = subprocess.CompletedProcess([], 0, "a" * 40 + "\trefs/heads/run\n", "")
        for module, read in ((archive, lambda: archive._remote_state(Path.cwd(), URL, "refs/heads/run", credentials=binding)),
                             (host, lambda: host._remote_head(URL, "refs/heads/run", cwd=Path.cwd(), credentials=binding))):
            with patch.object(subject, "credential_binding", return_value=binding), patch.object(
                module, "git_executable", return_value="git"
            ), patch.object(module.subprocess, "run", return_value=completed) as run:
                self.assertEqual("a" * 40, read())
                env = run.call_args.kwargs["env"]
                self.assertEqual("4", env["GIT_CONFIG_COUNT"])
                self.assertNotEqual(Path.cwd(), run.call_args.kwargs["cwd"])
                self.assertIn(URL, run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
