#!/usr/bin/env python3
"""Boundary tests for the trusted-host publication helper."""

from __future__ import annotations

import contextlib
import io
import os
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import sys

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import trusted_host_publication as subject  # noqa: E402


class TrustedHostPublicationTests(unittest.TestCase):
    def test_reserved_output_replacement_is_detected_and_attacker_bytes_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.json"
            fd, identity = subject._reserve_output(path)
            os.close(fd)
            path.unlink()
            path.write_text("attacker", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "reserved output"):
                subject._assert_reserved_output(path, fd, identity)
            self.assertEqual("attacker", path.read_text(encoding="utf-8"))

    @unittest.skipIf(os.name != "nt", "simulated HKLM policy needs native Windows pathlib")
    def test_windows_hklm_policy_mock_readback_binds_principal_and_hash(self) -> None:
        class FakeKey:
            def __enter__(self) -> "FakeKey":
                return self

            def __exit__(self, *_: object) -> None:
                return None

        class FakeWinreg:
            HKEY_LOCAL_MACHINE = object()
            KEY_READ = 1
            KEY_WOW64_64KEY = 2

            @staticmethod
            def OpenKey(*_: object) -> FakeKey:
                return FakeKey()

            @staticmethod
            def QueryValueEx(*_: object) -> tuple[str, int]:
                return (
                    "archive-publisher ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAfixture comment",
                    1,
                )

        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(sys.modules, {"winreg": FakeWinreg}), patch.object(subject.os, "name", "nt"):
                policy = subject._discover_machine_trust_policy(root=Path(temp))
            try:
                self.assertEqual(
                    "HKLM\\SOFTWARE\\ProductDeliveryHarness\\ArchivePushAllowedSigners",
                    policy.policy_id,
                )
                self.assertEqual("archive-publisher", policy.principal)
                self.assertEqual(
                    hashlib.sha256(policy.allowed_signers_path.read_bytes()).hexdigest(),
                    policy.allowed_signers_sha256,
                )
            finally:
                policy.cleanup()

    def test_execution_requires_explicit_trusted_host_marker_before_reading_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "request.json"
            attempt = root / "attempt.json"
            request.write_text("not-json", encoding="utf-8")
            attempt.write_text("not-json", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch.object(subject.subprocess, "run") as run:
                args = subject.argparse.Namespace(
                    request=request,
                    attempt=attempt,
                    evidence_out=root / "evidence.json",
                    signing_key=root / "signing-key",
                    trusted_host_issuer="fixture",
                )
                with self.assertRaisesRegex(RuntimeError, "HARNESS_TRUSTED_HOST"):
                    subject.execute(args)
                run.assert_not_called()

    def test_invalid_issuer_is_rejected_before_any_push_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            attempt_path = root / "attempt.json"
            evidence_path = root / "evidence.json"
            key = root / "machine-key"
            verifier = root / "ssh-keygen"
            key.write_text("fixture", encoding="utf-8")
            verifier.write_bytes(b"verifier")
            request = {
                "attempt_path": str(attempt_path),
                "execution_evidence_path": str(evidence_path),
                "archive_path": "docs/goal/archived/A",
                "candidate_a": "a" * 40,
                "signature_verifier_path": str(verifier),
                "signature_verifier_sha256": hashlib.sha256(verifier.read_bytes()).hexdigest(),
            }
            attempt = {"attempt_sha256": "b" * 64}
            args = subject.argparse.Namespace(
                request=request_path,
                attempt=attempt_path,
                evidence_out=evidence_path,
                signing_key=key,
                trusted_host_issuer="\n",
            )
            with (
                patch.dict(os.environ, {"HARNESS_TRUSTED_HOST": "1"}, clear=True),
                patch.object(subject, "_root", return_value=root),
                patch.object(subject, "_load_request", return_value=request),
                patch.object(subject, "_load_attempt", return_value=attempt),
                patch.object(subject, "verify_archive_candidate", return_value={}),
                patch.object(subject, "_request_matches_authority"),
                patch.object(subject.subprocess, "run") as run,
            ):
                with self.assertRaisesRegex(RuntimeError, "issuer"):
                    subject.execute(args)
            run.assert_not_called()

    def test_preexisting_evidence_output_is_rejected_before_any_push_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request_path = root / "request.json"
            attempt_path = root / "attempt.json"
            evidence_path = root / "evidence.json"
            evidence_path.write_text("old", encoding="utf-8")
            request = {"attempt_path": str(attempt_path), "execution_evidence_path": str(evidence_path), "archive_path": "docs/goal/archived/A", "candidate_a": "a" * 40}
            args = subject.argparse.Namespace(request=request_path, attempt=attempt_path, evidence_out=evidence_path, signing_key=root / "key", trusted_host_issuer="trusted-host-01")
            with (
                patch.dict(os.environ, {"HARNESS_TRUSTED_HOST": "1"}, clear=True),
                patch.object(subject, "_root", return_value=root),
                patch.object(subject, "_load_request", return_value=request),
                patch.object(subject, "_load_attempt", return_value={}),
                patch.object(subject, "verify_archive_candidate", return_value={}),
                patch.object(subject, "_request_matches_authority"),
                patch.object(subject.subprocess, "run") as run,
            ):
                with self.assertRaisesRegex(RuntimeError, "already exists"):
                    subject.execute(args)
            run.assert_not_called()

    def test_invalid_request_is_rejected_before_attempt_or_push(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "request.json"
            attempt = root / "attempt.json"
            with (
                patch.dict(os.environ, {"HARNESS_TRUSTED_HOST": "1"}, clear=True),
                patch.object(subject, "_root", return_value=root),
                patch.object(
                    subject,
                    "_load_request",
                    side_effect=RuntimeError("request digest mismatch"),
                ),
                patch.object(subject, "_load_attempt") as load_attempt,
                patch.object(subject.subprocess, "run") as run,
            ):
                args = subject.argparse.Namespace(
                    request=request,
                    attempt=attempt,
                    evidence_out=root / "evidence.json",
                    signing_key=root / "signing-key",
                    trusted_host_issuer="fixture",
                )
                with self.assertRaisesRegex(RuntimeError, "request digest mismatch"):
                    subject.execute(args)
                load_attempt.assert_not_called()
                run.assert_not_called()

    def test_signing_uses_the_bound_os_managed_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            verifier = root / "ssh-keygen.exe"
            verifier.write_bytes(b"trusted verifier")
            key = root / "machine-key"
            key.write_text("private fixture", encoding="utf-8")
            signature = root / "evidence.sig"

            def complete(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                signature.write_bytes(b"detached signature")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(subject.subprocess, "run", side_effect=complete) as run:
                output, digest = subject._sign_payload(
                    b"payload",
                    key,
                    verifier,
                    hashlib.sha256(verifier.read_bytes()).hexdigest(),
                    output_dir=root,
                    signature_path=signature,
                )
            self.assertEqual(signature, output)
            self.assertEqual(hashlib.sha256(signature.read_bytes()).hexdigest(), digest)
            self.assertEqual(str(verifier), run.call_args.args[0][0])
            self.assertNotIn("-O", run.call_args.args[0])

    def test_signing_rejects_a_changed_verifier_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            verifier = root / "ssh-keygen.exe"
            verifier.write_bytes(b"changed")
            key = root / "machine-key"
            key.write_text("private fixture", encoding="utf-8")
            with patch.object(subject.subprocess, "run") as run:
                with self.assertRaisesRegex(RuntimeError, "changed before signing"):
                    subject._sign_payload(
                        b"payload",
                        key,
                        verifier,
                        "0" * 64,
                        output_dir=root,
                    )
                run.assert_not_called()

    def test_real_openssh_signing_command_produces_detached_signature(self) -> None:
        located = shutil.which("ssh-keygen")
        if located is None:
            self.skipTest("OpenSSH ssh-keygen is unavailable")
        verifier = Path(located).resolve()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            key = root / "machine-key"
            generated = subprocess.run(
                [str(verifier), "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if generated.returncode != 0:
                self.skipTest(generated.stderr.strip() or "cannot generate test key")
            signature, digest = subject._sign_payload(
                b"canonical evidence",
                key,
                verifier,
                hashlib.sha256(verifier.read_bytes()).hexdigest(),
                output_dir=root,
                signature_path=root / "evidence.sig",
            )
            self.assertTrue(signature.is_file())
            self.assertEqual(hashlib.sha256(signature.read_bytes()).hexdigest(), digest)
            self.assertIn(b"BEGIN SSH SIGNATURE", signature.read_bytes())

    def test_verify_policy_reports_machine_bound_hashes_without_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            verifier = root / "ssh-keygen"
            verifier.write_bytes(b"verifier")
            cleanup = Mock()
            policy = SimpleNamespace(
                policy_id="fixture-policy",
                principal="fixture-principal",
                allowed_signers_sha256="1" * 64,
                cleanup=cleanup,
            )
            output = io.StringIO()
            with (
                patch.object(subject, "_root", return_value=root),
                patch.object(subject, "_discover_machine_trust_policy", return_value=policy),
                patch.object(subject, "_discover_os_managed_verifier", return_value=str(verifier)),
                patch.object(subject.subprocess, "run") as run,
                contextlib.redirect_stdout(output),
            ):
                status = subject.verify_policy(
                    subject.argparse.Namespace(repo_root=root)
                )
            self.assertEqual(0, status)
            self.assertIn("fixture-policy", output.getvalue())
            self.assertIn(hashlib.sha256(b"verifier").hexdigest(), output.getvalue())
            cleanup.assert_called_once_with()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
