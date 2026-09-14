#!/usr/bin/env python3
"""Prepare and verify an archive-first exact-SHA publication handoff.

This local tool never invokes ``git push``.  It writes closed immutable
request/attempt records, returns a safe no-force argv for a human or trusted
host, and closes the receipt only after recovery reads back the exact SHA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_core import ManifestError, extract_json_manifest_text, is_full_sha, plan_digest
from harness_git import (
    GitMetadataError,
    git_environment,
    reject_object_substitution,
    run_git,
)
from harness_schema import PLAN_HEADING, RUN_HEADING, archive_first_required
from harness_manifest import validate_plan, validate_run
from harness_contract_join import validate_frozen_contract_joins
from harness_ui_evidence import validate_ui_evidence_files
from push_integration_branch import (
    _push_url_metadata,
    _safe_push_url,
    _safe_remote,
    _verify_configured_remote,
)
from archive_run import _documents_after_bytes, validate_archive_receipt
from archive_run import validate_archive_anchor


POSIX_TRUST_POLICY_PATH = Path("/etc/product-delivery-harness/archive-push.allowed_signers")
WINDOWS_TRUST_REGISTRY_PATH = r"SOFTWARE\ProductDeliveryHarness"
WINDOWS_TRUST_REGISTRY_VALUE = "ArchivePushAllowedSigners"


@dataclass(frozen=True)
class MachineTrustPolicy:
    policy_id: str
    allowed_signers_path: Path
    allowed_signers_sha256: str
    principal: str
    cleanup_path: Path | None = None

    def cleanup(self) -> None:
        if self.cleanup_path is not None:
            try:
                self.cleanup_path.unlink()
            except OSError:
                pass

    def __del__(self) -> None:
        self.cleanup()

REQUEST_PROTOCOL = "harness-archive-push-request-v3"
RECEIPT_PROTOCOL = "harness-archive-push-receipt-v3"
ATTEMPT_PROTOCOL = "harness-archive-push-attempt-v2"
EXECUTION_EVIDENCE_PROTOCOL = "trusted-host-publication-v1"
EXECUTION_EVIDENCE_NAMESPACE = "harness-archive-push"
LOCAL_AUTHORIZATION_SOURCE = "external-human-or-trusted-host"
LOCAL_AUTHORIZATION_REF = "not-authorized-by-local-executor"
PENDING_TRUSTED_HOST_STATUS = "PENDING_TRUSTED_HOST_PUBLICATION"
REQUEST_KEYS = {
    "protocol", "authorization_source", "authorization_ref", "plan_id", "plan_revision",
    "plan_digest_sha256", "run_id", "run_schema_version", "archive_path", "archive_hashes",
    "moves", "archive_receipt_sha256", "expected_main", "main_ref", "stamp",
    "documents_before_sha256", "documents_after_sha256",
    "anchor_path", "anchor_path_sha256", "anchor_nonce",
    "candidate_c", "candidate_a", "replacement_base", "run_branch", "branch_ref", "remote",
    "prior_publication_state", "prior_publication_receipt_path", "prior_publication_receipt_sha256",
    "push_url", "push_endpoint_kind", "push_endpoint_summary", "push_url_sha256", "remote_pre_push_head",
    "request_path", "request_path_sha256", "receipt_path", "receipt_path_sha256",
    "execution_evidence_path", "execution_evidence_path_sha256",
    "trust_policy_id", "trust_policy_sha256", "trusted_host_principal",
    "signature_verifier_path", "signature_verifier_sha256",
    "execution_nonce", "created_at", "request_sha256", "attempt_path", "attempt_path_sha256",
}
RECEIPT_KEYS = {
    "protocol", "status", "request_path", "request_path_sha256", "request_sha256", "attempt_path", "attempt_path_sha256", "receipt_path", "receipt_path_sha256",
    "execution_nonce", "candidate_a", "branch_ref", "remote", "push_endpoint_kind",
    "push_url", "push_endpoint_summary", "push_url_sha256", "remote_pre_push_head", "readback_head_sha",
    "plan_id", "plan_revision", "plan_digest_sha256", "run_id", "run_schema_version",
    "archive_path", "archive_hashes", "moves", "archive_receipt_sha256", "candidate_c",
    "run_branch", "replacement_base", "prior_publication_state", "prior_publication_receipt_path", "prior_publication_receipt_sha256", "expected_main", "main_ref", "stamp", "documents_before_sha256",
    "documents_after_sha256", "receipt_sha256",
    "anchor_path", "anchor_path_sha256", "anchor_nonce",
    "execution_evidence_path", "execution_evidence_path_sha256", "execution_evidence_sha256",
    "trusted_host_issuer", "trusted_host_principal",
    "trust_policy_id", "trust_policy_sha256", "signature_verifier_path", "signature_verifier_sha256",
}
ATTEMPT_KEYS = {
    "protocol", "request_sha256", "attempt_path", "attempt_path_sha256",
    "execution_nonce", "candidate_a", "replacement_base", "branch_ref", "remote", "started_at",
    "push_mode", "push_url", "push_endpoint_kind", "push_endpoint_summary", "push_url_sha256",
    "remote_pre_push_head", "attempt_sha256",
    "execution_evidence_path", "execution_evidence_path_sha256",
    "prior_publication_state", "prior_publication_receipt_path", "prior_publication_receipt_sha256",
    "trust_policy_id", "trust_policy_sha256", "signature_verifier_path", "signature_verifier_sha256",
}
EXECUTION_EVIDENCE_KEYS = {
    "protocol", "request_sha256", "attempt_sha256", "execution_nonce", "candidate_a",
    "branch_ref", "push_url", "push_url_sha256", "remote_pre_push_head",
    "readback_head_sha", "push_argv", "push_argv_sha256", "request_reloaded",
    "authorization_revalidated", "endpoint_revalidated", "config_sanitized",
    "dangerous_local_config_rejected", "trusted_host_issuer", "trusted_host_principal", "trust_policy_id",
    "authentication_proof", "executed_at", "evidence_sha256",
}
COORDINATION_NAMES = ("PLAN.md", "RUN.md", "DECISIONS.md", "REFINEMENT_BACKLOG.md")
COORDINATION_DIR = Path("docs/goal")
DOCUMENTS_PATH = Path("docs/DOCUMENTS.md")
ARCHIVE_RECEIPT_NAME = "ARCHIVE_RECEIPT.json"
ARCHIVE_RECEIPT_PROTOCOL = "harness-archive-receipt-v1"
ARCHIVE_RECEIPT_KEYS = {
    "protocol", "run_id", "plan_id", "plan_revision", "plan_digest_sha256", "candidate_c",
    "branch", "branch_ref", "expected_main", "main_ref", "stamp", "archive_path", "moves",
    "documents_before_sha256", "documents_after_sha256", "receipt_sha256",
}


def _git(root: Path, *args: str, text: bool = True) -> subprocess.CompletedProcess[Any]:
    return run_git(root, *args, capture_output=True, text=text, timeout=30, check=False)


def _out(root: Path, *args: str) -> str:
    result = _git(root, *args)
    if result.returncode != 0:
        raise ManifestError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _path_digest(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode()).hexdigest()


def _deterministic_publication_receipt_path(anchor_path: str | Path) -> Path:
    anchor = Path(anchor_path).resolve(strict=False)
    return anchor.with_name(anchor.stem + "-publication-receipt.json")


def _require_sha(value: object, *, length: int = 40, label: str = "SHA") -> None:
    if not isinstance(value, str) or len(value) != length or any(char not in "0123456789abcdef" for char in value):
        raise ManifestError(f"{label} must be lowercase hexadecimal SHA-{length * 4}")


def _require_nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ManifestError(f"{label} must be a non-empty exact string")
    return value


def _canonical_external_path(value: object, *, label: str, root: Path) -> str:
    if isinstance(value, Path):
        value = str(value)
    raw = _require_nonempty(value, label)
    resolved = Path(raw).resolve(strict=False)
    if raw != str(resolved):
        raise ManifestError(f"{label} must be a canonical absolute path")
    if resolved.is_relative_to(root.resolve()):
        raise ManifestError(f"{label} must live outside the reviewed checkout")
    return raw


def _trusted_signature_verifier_path(value: object, *, root: Path) -> str:
    """Accept only an OS-managed OpenSSH verifier, never caller code."""

    raw = _canonical_external_path(value, label="signature_verifier_path", root=root)
    path = Path(raw)
    normalized = str(path).casefold().replace("\\", "/")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetWindowsDirectoryW.restype = wintypes.UINT
        windows_buffer = ctypes.create_unicode_buffer(32768)
        length = kernel32.GetWindowsDirectoryW(windows_buffer, len(windows_buffer))
        if not length:
            raise ManifestError("cannot resolve the Windows system directory")
        system_root = str(Path(windows_buffer.value[:length]).resolve()).casefold().replace("\\", "/")
        program_files = str(Path(system_root).anchor + "Program Files").casefold().replace("\\", "/")
        allowed = {
            f"{system_root}/system32/openssh/ssh-keygen.exe",
            f"{program_files}/openssh/ssh-keygen.exe",
            f"{program_files}/git/usr/bin/ssh-keygen.exe",
        }
    else:
        allowed = {"/usr/bin/ssh-keygen", "/bin/ssh-keygen", "/usr/local/bin/ssh-keygen"}
        try:
            components = list(reversed(path.parents)) + [path]
            for component in components:
                info = component.stat()
                if info.st_uid != 0 or info.st_mode & 0o022:
                    raise ManifestError("signature verifier path is not root-owned and private")
        except (OSError, ValueError) as exc:
            raise ManifestError("cannot inspect signature verifier ownership") from exc
    if normalized not in allowed:
        raise ManifestError("signature_verifier_path is not an OS-managed OpenSSH verifier")
    return raw


def _parse_machine_signer_line(value: str, *, policy_id: str) -> tuple[str, bytes]:
    lines = value.splitlines()
    if len(lines) != 1 or not lines[0].strip():
        raise ManifestError(
            f"machine trust policy {policy_id} must contain exactly one allowed-signers line; "
            "install the administrator-provided policy before archive publication"
        )
    line = lines[0].strip()
    fields = line.split()
    if len(fields) < 3 or not re.fullmatch(r"(?:ssh|ecdsa|sk|rsa)-[^\s]+", fields[1]):
        raise ManifestError(
            f"machine trust policy {policy_id} has an invalid allowed-signers line"
        )
    principal = fields[0]
    return principal, (line + "\n").encode("utf-8")


def _protected_policy_path(path: Path, *, root: Path) -> Path:
    resolved = Path(_canonical_external_path(path, label="machine trust policy", root=root))
    if not resolved.is_file():
        raise ManifestError(
            "machine trust policy is absent; an administrator must install the archive-push allowed-signers policy"
        )
    if os.name != "nt":
        try:
            for component in list(reversed(resolved.parents)) + [resolved]:
                info = component.stat()
                if info.st_uid != 0 or info.st_mode & 0o022:
                    raise ManifestError(
                        "machine trust policy must be root-owned and not group/world writable"
                    )
        except OSError as exc:
            raise ManifestError("cannot inspect machine trust policy ownership") from exc
    return resolved


def _discover_machine_trust_policy(*, root: Path | None = None) -> MachineTrustPolicy:
    """Read the administrator/host trust root; callers cannot select it."""

    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                WINDOWS_TRUST_REGISTRY_PATH,
                0,
                winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0),
            ) as key:
                value, value_type = winreg.QueryValueEx(key, WINDOWS_TRUST_REGISTRY_VALUE)
        except (FileNotFoundError, OSError) as exc:
            raise ManifestError(
                "machine trust policy is absent; an administrator must install "
                "HKLM\\SOFTWARE\\ProductDeliveryHarness\\ArchivePushAllowedSigners"
            ) from exc
        if value_type not in {1, 2} or not isinstance(value, str):
            raise ManifestError("machine trust policy registry value must be a string")
        policy_id = f"HKLM\\{WINDOWS_TRUST_REGISTRY_PATH}\\{WINDOWS_TRUST_REGISTRY_VALUE}"
        principal, payload = _parse_machine_signer_line(value, policy_id=policy_id)
        handle = tempfile.NamedTemporaryFile(
            prefix="harness-machine-signers-",
            suffix=".allowed-signers",
            delete=False,
        )
        path = Path(handle.name).resolve()
        try:
            handle.write(payload)
            handle.flush()
        finally:
            handle.close()
        return MachineTrustPolicy(
            policy_id=policy_id,
            allowed_signers_path=path,
            allowed_signers_sha256=hashlib.sha256(payload).hexdigest(),
            principal=principal,
            cleanup_path=path,
        )

    path = _protected_policy_path(POSIX_TRUST_POLICY_PATH, root=(root or Path.cwd()).resolve())
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ManifestError("cannot read the administrator machine trust policy") from exc
    principal, payload = _parse_machine_signer_line(value, policy_id=f"file:{path}")
    return MachineTrustPolicy(
        policy_id=f"file:{path}",
        allowed_signers_path=path,
        allowed_signers_sha256=hashlib.sha256(payload).hexdigest(),
        principal=principal,
    )


def _discover_os_managed_verifier(*, root: Path) -> str:
    """Select an OS-managed ssh-keygen without caller-supplied paths."""

    candidates: list[Path] = []
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetWindowsDirectoryW.restype = wintypes.UINT
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel32.GetWindowsDirectoryW(buffer, len(buffer))
        if length:
            windows = Path(buffer.value[:length]).resolve()
            candidates.extend(
                (
                    windows / "System32" / "OpenSSH" / "ssh-keygen.exe",
                    windows.anchor and Path(windows.anchor) / "Program Files" / "OpenSSH" / "ssh-keygen.exe",
                    windows.anchor and Path(windows.anchor) / "Program Files" / "Git" / "usr" / "bin" / "ssh-keygen.exe",
                )
            )
    else:
        candidates.extend((Path("/usr/bin/ssh-keygen"), Path("/bin/ssh-keygen"), Path("/usr/local/bin/ssh-keygen")))
    for candidate in candidates:
        if candidate and candidate.is_file():
            return _trusted_signature_verifier_path(candidate, root=root)
    raise ManifestError(
        "OS-managed ssh-keygen is absent; install OpenSSH/ssh-keygen before archive publication"
    )


def _validate_timestamp(value: object, label: str) -> None:
    if not isinstance(value, str) or value != value.strip() or not value.endswith("Z"):
        raise ManifestError(f"{label} must be an RFC3339 UTC timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ManifestError(f"{label} must be an RFC3339 UTC timestamp") from exc


def _validate_endpoint(metadata: dict[str, Any]) -> None:
    push_url = metadata.get("push_url")
    if not isinstance(push_url, str):
        raise ManifestError("push_url must be present in the immutable publication record")
    _safe_push_url(push_url)
    _require_nonempty(metadata.get("push_endpoint_kind"), "push_endpoint_kind")
    _require_nonempty(metadata.get("push_endpoint_summary"), "push_endpoint_summary")
    _require_sha(metadata.get("push_url_sha256"), length=64, label="push_url_sha256")
    if hashlib.sha256(push_url.encode("utf-8")).hexdigest() != metadata["push_url_sha256"]:
        raise ManifestError("push_url_sha256 does not match the canonical push_url")


def _execution_argv(request: dict[str, Any]) -> list[str]:
    """Return the only publication argv a trusted host may execute."""

    return [
        "git",
        "--no-replace-objects",
        "push",
        "--",
        request["push_url"],
        f"{request['candidate_a']}:{request['branch_ref']}",
    ]


def _execution_evidence_payload(evidence: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: value for key, value in evidence.items() if key != "evidence_sha256"
    }
    proof = payload.get("authentication_proof")
    if isinstance(proof, dict) and "signature_sha256" in proof:
        # The detached signature necessarily cannot sign its own digest.  The
        # field remains hash-checked outside the signed payload.
        payload["authentication_proof"] = {
            **proof,
            "signature_sha256": "<detached-signature>",
        }
    return payload


def _validate_execution_evidence_shape(
    evidence: dict[str, Any],
    request: dict[str, Any],
    attempt: dict[str, Any],
    *,
    root: Path,
) -> None:
    if set(evidence) != EXECUTION_EVIDENCE_KEYS:
        raise ManifestError("trusted-host execution evidence has missing or extra fields")
    if evidence.get("protocol") != EXECUTION_EVIDENCE_PROTOCOL:
        raise ManifestError("trusted-host execution evidence protocol is invalid")
    for key in ("request_sha256", "attempt_sha256"):
        _require_sha(evidence.get(key), length=64, label=f"evidence.{key}")
    if evidence.get("request_sha256") != request.get("request_sha256"):
        raise ManifestError("trusted-host evidence request digest does not match request")
    if evidence.get("attempt_sha256") != attempt.get("attempt_sha256"):
        raise ManifestError("trusted-host evidence attempt digest does not match attempt")
    if evidence.get("execution_nonce") != request.get("execution_nonce"):
        raise ManifestError("trusted-host evidence nonce does not match request")
    if evidence.get("candidate_a") != request.get("candidate_a"):
        raise ManifestError("trusted-host evidence candidate does not match request")
    if evidence.get("branch_ref") != request.get("branch_ref"):
        raise ManifestError("trusted-host evidence branch does not match request")
    if evidence.get("push_url") != request.get("push_url"):
        raise ManifestError("trusted-host evidence push URL does not match request")
    if evidence.get("push_url_sha256") != request.get("push_url_sha256"):
        raise ManifestError("trusted-host evidence push URL digest does not match request")
    if evidence.get("remote_pre_push_head") != request.get("remote_pre_push_head"):
        raise ManifestError("trusted-host evidence remote pre-state does not match request")
    _require_sha(evidence.get("readback_head_sha"), label="evidence.readback_head_sha")
    if evidence.get("readback_head_sha") != request.get("candidate_a"):
        raise ManifestError("trusted-host evidence readback must equal candidate A")
    argv = evidence.get("push_argv")
    expected_argv = _execution_argv(request)
    if argv != expected_argv:
        raise ManifestError("trusted-host evidence argv does not use the exact canonical push URL")
    if evidence.get("push_argv_sha256") != _digest(argv):
        raise ManifestError("trusted-host evidence argv digest does not match argv")
    for key in (
        "request_reloaded",
        "authorization_revalidated",
        "endpoint_revalidated",
        "config_sanitized",
        "dangerous_local_config_rejected",
    ):
        if evidence.get(key) is not True:
            raise ManifestError(f"trusted-host evidence must attest {key}")
    issuer = evidence.get("trusted_host_issuer")
    principal = evidence.get("trusted_host_principal")
    _require_nonempty(issuer, "evidence.trusted_host_issuer")
    _require_nonempty(principal, "evidence.trusted_host_principal")
    _require_nonempty(evidence.get("trust_policy_id"), "evidence.trust_policy_id")
    proof = evidence.get("authentication_proof")
    if not isinstance(proof, dict) or set(proof) != {
        "kind",
        "namespace",
        "policy_id",
        "principal",
        "signature_path",
        "signature_sha256",
    }:
        raise ManifestError("trusted-host evidence requires a detached signature proof")
    if proof.get("kind") != "ssh-signature" or proof.get("namespace") != EXECUTION_EVIDENCE_NAMESPACE:
        raise ManifestError("trusted-host evidence signature proof is invalid")
    if proof.get("principal") != principal:
        raise ManifestError("trusted-host evidence principal does not match signature proof")
    _canonical_external_path(proof.get("signature_path"), label="evidence.signature_path", root=root)
    _require_sha(proof.get("signature_sha256"), length=64, label="evidence.signature_sha256")
    _validate_timestamp(evidence.get("executed_at"), "evidence.executed_at")
    _require_sha(evidence.get("evidence_sha256"), length=64, label="evidence.evidence_sha256")
    unsigned = {
        key: value for key, value in evidence.items() if key != "evidence_sha256"
    }
    if evidence["evidence_sha256"] != _digest(unsigned):
        raise ManifestError("trusted-host evidence digest mismatch")


def _verify_execution_evidence_signature(
    evidence: dict[str, Any],
    *,
    root: Path,
    request: dict[str, Any],
) -> None:
    """Verify a detached trusted-host signature; local prose cannot satisfy it."""

    proof = evidence["authentication_proof"]
    policy = _discover_machine_trust_policy(root=root)
    if policy.policy_id != request["trust_policy_id"] or policy.policy_id != evidence["trust_policy_id"]:
        policy.cleanup()
        raise ManifestError("machine trust policy identity changed after prepare")
    if policy.allowed_signers_sha256 != request["trust_policy_sha256"]:
        policy.cleanup()
        raise ManifestError("machine trust policy hash changed after prepare")
    if policy.principal != request["trusted_host_principal"] or policy.principal != proof["principal"]:
        policy.cleanup()
        raise ManifestError("machine trust policy principal changed after prepare")
    if proof.get("policy_id") != policy.policy_id:
        policy.cleanup()
        raise ManifestError("trusted-host evidence policy ID does not match machine policy")
    configured_signers = policy.allowed_signers_path
    signature_path = Path(proof["signature_path"])
    signers_path = configured_signers
    if not signature_path.is_file() or not signers_path.is_file():
        policy.cleanup()
        raise ManifestError("trusted-host signature or allowed-signers file is missing")
    bound_fds: list[int] = []

    def bind(path: Path, expected: str) -> tuple[int, str]:
        if os.name == "nt":
            # Hold the original pathname with FILE_SHARE_READ only.  A same
            # user cannot replace/delete it while ssh-keygen is reading it.
            import ctypes
            import msvcrt
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateFileW.restype = wintypes.HANDLE
            kernel32.CreateFileW.argtypes = [
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.HANDLE,
            ]
            handle = kernel32.CreateFileW(
                str(path),
                0x80000000,  # GENERIC_READ
                0x00000001,  # FILE_SHARE_READ (deny write/delete)
                None,
                3,  # OPEN_EXISTING
                0x00200000,  # FILE_FLAG_OPEN_REPARSE_POINT
                None,
            )
            invalid = wintypes.HANDLE(-1).value
            if handle in (None, invalid):
                raise ManifestError(f"cannot hold trusted-host bound file: {path}")
            handle_owned = True
            try:
                kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
                buffer = ctypes.create_unicode_buffer(32768)
                length = kernel32.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
                if not length:
                    raise ManifestError(f"cannot resolve trusted-host bound file: {path}")
                actual = buffer.value[:length].removeprefix("\\\\?\\").casefold().replace("\\", "/")
                expected_path = str(path.resolve(strict=False)).casefold().replace("\\", "/")
                if actual != expected_path:
                    raise ManifestError("trusted-host bound file final path changed")
                fd = msvcrt.open_osfhandle(int(handle), os.O_RDONLY)
                handle_owned = False
            except Exception:
                if handle_owned:
                    kernel32.CloseHandle(handle)
                raise
            with os.fdopen(os.dup(fd), "rb") as stream:
                payload = stream.read()
            if hashlib.sha256(payload).hexdigest() != expected:
                os.close(fd)
                raise ManifestError("trusted-host bound file changed after request/evidence validation")
            os.lseek(fd, 0, os.SEEK_SET)
            bound_fds.append(fd)
            return fd, str(path)
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        if os.name != "nt":
            flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            raise ManifestError(f"cannot open trusted-host bound file: {exc}") from exc
        try:
            with os.fdopen(os.dup(fd), "rb") as stream:
                payload = stream.read()
            if hashlib.sha256(payload).hexdigest() != expected:
                raise ManifestError("trusted-host bound file changed after request/evidence validation")
            os.lseek(fd, 0, os.SEEK_SET)
        except Exception:
            os.close(fd)
            raise
        bound_fds.append(fd)
        if os.name != "nt":
            for prefix in ("/proc/self/fd", "/dev/fd"):
                if Path(prefix).exists():
                    return fd, f"{prefix}/{fd}"
            os.close(fd)
            bound_fds.pop()
            raise ManifestError("no descriptor path is available for trusted-host verifier")
        return fd, str(path)
    try:
        configured_verifier = Path(_discover_os_managed_verifier(root=root))
    except Exception:
        policy.cleanup()
        raise
    if str(configured_verifier) != request["signature_verifier_path"]:
        policy.cleanup()
        raise ManifestError("signature verifier path does not match request")
    result = None
    try:
        _, verifier_arg = bind(configured_verifier, request["signature_verifier_sha256"])
        _, signers_arg = bind(signers_path, request["trust_policy_sha256"])
        _, signature_arg = bind(signature_path, proof["signature_sha256"])
        command = [
            verifier_arg,
            "-Y",
            "verify",
            "-f",
            signers_arg,
            "-I",
            proof["principal"],
            "-n",
            proof["namespace"],
            "-s",
            signature_arg,
        ]
        result = subprocess.run(
            command,
            cwd=root,
            input=json.dumps(
                _execution_evidence_payload(evidence),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8"),
            capture_output=True,
            timeout=10,
            check=False,
            env=git_environment(),
            pass_fds=tuple(bound_fds) if os.name != "nt" else (),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ManifestError(f"trusted-host signature verification unavailable: {exc}") from exc
    finally:
        for fd in bound_fds:
            try:
                os.close(fd)
            except OSError:
                pass
        policy.cleanup()
    if result is None:
        raise ManifestError("trusted-host signature verification did not run")
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip() if isinstance(result.stderr, bytes) else str(result.stderr).strip()
        raise ManifestError(detail or "trusted-host signature verification failed")


def _read_execution_evidence(
    root: Path,
    request: dict[str, Any],
    attempt: dict[str, Any],
) -> dict[str, Any]:
    path = Path(request["execution_evidence_path"])
    _canonical_external_path(path, label="execution_evidence_path", root=root)
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read trusted-host execution evidence: {exc}") from exc
    if not isinstance(evidence, dict):
        raise ManifestError("trusted-host execution evidence must be an object")
    _validate_execution_evidence_shape(evidence, request, attempt, root=root)
    _verify_execution_evidence_signature(
        evidence,
        root=root,
        request=request,
    )
    return evidence


def _validate_archive_authority(authority: dict[str, Any]) -> None:
    for key in ("plan_id", "run_id", "archive_path", "run_branch", "branch_ref", "candidate_c", "candidate_a"):
        _require_nonempty(authority.get(key), key)
    _require_sha(authority["plan_digest_sha256"], length=64, label="plan_digest_sha256")
    _require_sha(authority["candidate_c"], label="candidate_c")
    _require_sha(authority["candidate_a"], label="candidate_a")
    replacement_base = authority.get("replacement_base")
    if replacement_base is not None:
        _require_sha(replacement_base, label="replacement_base")
        if replacement_base in {authority["candidate_c"], authority["candidate_a"]}:
            raise ManifestError("replacement_base must identify the prior candidate, not C or A")
    branch = _canonical_branch(authority["run_branch"])
    if branch is None or _protected_branch(branch) or authority["branch_ref"] != f"refs/heads/{branch}":
        raise ManifestError("archive branch/ref is not canonical or is protected")
    if not _canonical_archive_path(authority["archive_path"]):
        raise ManifestError("archive_path is not canonical")
    if not isinstance(authority.get("run_schema_version"), int) or isinstance(authority.get("run_schema_version"), bool):
        raise ManifestError("run_schema_version must be an integer")
    if not isinstance(authority.get("archive_hashes"), dict) or not authority["archive_hashes"]:
        raise ManifestError("archive_hashes must be a non-empty object")
    for path, digest in authority["archive_hashes"].items():
        if not isinstance(path, str) or not path.startswith(authority["archive_path"] + "/"):
            raise ManifestError("archive_hashes contains a path outside archive_path")
        _require_sha(digest, length=64, label=f"archive_hashes[{path}]")
    if not isinstance(authority.get("moves"), list) or not authority["moves"]:
        raise ManifestError("moves must be a non-empty list")
    for move in authority["moves"]:
        if not isinstance(move, dict) or set(move) != {"source", "destination", "type", "sha256"}:
            raise ManifestError("moves contains an invalid row")
        _require_nonempty(move.get("source"), "move.source")
        _require_nonempty(move.get("destination"), "move.destination")
        if move["type"] != "file":
            raise ManifestError("move.type must be file")
        _require_sha(move.get("sha256"), length=64, label="move.sha256")
    receipt_digest = authority.get("archive_receipt_sha256")
    _require_sha(receipt_digest, length=64, label="archive_receipt_sha256")
    stamp = authority.get("stamp")
    if not isinstance(stamp, str) or re.fullmatch(r"\d{8}-\d{6}", stamp) is None:
        raise ManifestError("stamp is invalid")
    for key in ("documents_before_sha256", "documents_after_sha256"):
        value = authority.get(key)
        if value is not None:
            _require_sha(value, length=64, label=key)
    anchor_path = authority.get("anchor_path")
    anchor_nonce = authority.get("anchor_nonce")
    if not isinstance(anchor_path, str) or not Path(anchor_path).is_absolute():
        raise ManifestError("anchor_path must be an absolute external path")
    _require_sha(authority.get("anchor_path_sha256"), length=64, label="anchor_path_sha256")
    if _path_digest(Path(anchor_path)) != authority["anchor_path_sha256"]:
        raise ManifestError("anchor_path_sha256 does not match canonical path")
    if not isinstance(anchor_nonce, str) or re.fullmatch(r"[0-9a-f]{64}", anchor_nonce) is None:
        raise ManifestError("anchor_nonce must be 64 lowercase hex characters")
    publication_state = authority.get("prior_publication_state")
    if publication_state not in {"not_applicable", "published", "unpublished"}:
        raise ManifestError("prior_publication_state must be explicitly bound")
    publication_path = authority.get("prior_publication_receipt_path")
    publication_digest = authority.get("prior_publication_receipt_sha256")
    if publication_state == "published":
        if not isinstance(publication_path, str) or not Path(publication_path).is_absolute():
            raise ManifestError("prior_publication_receipt_path must be an absolute external path")
        _require_sha(
            publication_digest,
            length=64,
            label="prior_publication_receipt_sha256",
        )
    elif publication_path is not None or publication_digest is not None:
        raise ManifestError(
            "unpublished/not_applicable prior publication state must not name a receipt"
        )


def _validate_request_values(request: dict[str, Any], root: Path, request_path: Path) -> None:
    if set(request) != REQUEST_KEYS - {"request_sha256"} and set(request) != REQUEST_KEYS:
        raise ManifestError("request has missing or extra fields before digest")
    if request.get("protocol") != REQUEST_PROTOCOL:
        raise ManifestError("request protocol is invalid")
    if request.get("authorization_source") != LOCAL_AUTHORIZATION_SOURCE:
        raise ManifestError(
            "caller-supplied authorization prose/ref cannot authorize archive publication"
        )
    if request.get("authorization_ref") != LOCAL_AUTHORIZATION_REF:
        raise ManifestError(
            "caller-supplied authorization prose/ref cannot authorize archive publication"
        )
    _validate_archive_authority(request)
    _require_nonempty(request.get("remote"), "remote")
    _canonical_external_path(
        request.get("execution_evidence_path"),
        label="execution_evidence_path",
        root=root,
    )
    if request["execution_evidence_path"] in {
        request["request_path"],
        request["attempt_path"],
        request["receipt_path"],
    }:
        raise ManifestError("execution evidence path must be distinct from request/attempt/receipt")
    _validate_endpoint(request)
    policy = _discover_machine_trust_policy(root=root)
    if request.get("trust_policy_id") != policy.policy_id:
        policy.cleanup()
        raise ManifestError("request trust policy ID does not match machine policy")
    if request.get("trust_policy_sha256") != policy.allowed_signers_sha256:
        policy.cleanup()
        raise ManifestError("request trust policy hash does not match machine policy")
    if request.get("trusted_host_principal") != policy.principal:
        policy.cleanup()
        raise ManifestError("request trust policy principal does not match machine policy")
    verifier_path = _discover_os_managed_verifier(root=root)
    verifier_file = Path(verifier_path)
    if not verifier_file.is_file():
        policy.cleanup()
        raise ManifestError("trusted-host signature verifier is missing")
    _require_sha(request.get("signature_verifier_sha256"), length=64, label="signature_verifier_sha256")
    if hashlib.sha256(verifier_file.read_bytes()).hexdigest() != request["signature_verifier_sha256"]:
        policy.cleanup()
        raise ManifestError("trusted-host signature verifier hash does not match request")
    policy.cleanup()
    pre = request.get("remote_pre_push_head")
    if pre is not None:
        _require_sha(pre, label="remote_pre_push_head")
    for key in (
        "request_path",
        "attempt_path",
        "receipt_path",
        "execution_evidence_path",
    ):
        _canonical_external_path(request.get(key), label=key, root=root)
        digest_key = key + "_sha256"
        if request[digest_key] != _path_digest(Path(request[key])):
            raise ManifestError(f"{key} digest does not match canonical path")
    if len(
        {
            request["request_path"],
            request["attempt_path"],
            request["receipt_path"],
            request["execution_evidence_path"],
        }
    ) != 4:
        raise ManifestError(
            "request, attempt, receipt, and execution evidence paths must be pairwise distinct"
        )
    if request["request_path"] != str(request_path.resolve()):
        raise ManifestError("request_path does not match the loaded request path")
    _canonical_external_path(request.get("anchor_path"), label="anchor_path", root=root)
    nonce = request.get("execution_nonce")
    if not isinstance(nonce, str) or re.fullmatch(r"[0-9a-f]{64}", nonce) is None:
        raise ManifestError("execution_nonce must be 64 lowercase hex characters")
    _validate_timestamp(request.get("created_at"), "created_at")


def _root(root: Path) -> Path:
    root = root.resolve()
    if Path(_out(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ManifestError("--repo-root must be the repository root")
    try:
        reject_object_substitution(root)
    except GitMetadataError as exc:
        raise ManifestError(str(exc)) from exc
    return root


def _blob(root: Path, revision: str, path: str) -> bytes:
    result = _git(root, "show", "--format=", f"{revision}:{path}", text=False)
    if result.returncode != 0:
        raise ManifestError(f"missing immutable Git blob {revision}:{path}")
    return bytes(result.stdout)


def _manifest(root: Path, revision: str, path: str, heading: str, wrapper: str) -> dict[str, Any]:
    payload = extract_json_manifest_text(_blob(root, revision, path).decode("utf-8"), heading, wrapper, source=f"{revision}:{path}")
    return payload if isinstance(payload, dict) else json.loads(payload)


def _archive_rel(root: Path, archive: Path) -> Path:
    try:
        rel = archive.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ManifestError("archive must be inside the repository root") from exc
    if len(rel.parts) != 4 or rel.parts[:3] != ("docs", "goal", "archived"):
        raise ManifestError("archive must be docs/goal/archived/<stamp-run>")
    if any(part in {"", ".", ".."} for part in rel.parts) or any(char in rel.name for char in "\\\0\r\n"):
        raise ManifestError("archive path is not canonical")
    return rel


def _tree_files(root: Path, revision: str, prefix: str) -> dict[str, str]:
    result = _git(root, "ls-tree", "-r", "-z", "--name-only", revision, "--", prefix, text=False)
    if result.returncode != 0:
        raise ManifestError("cannot inspect archived Git tree")
    names = [item.decode("utf-8") for item in bytes(result.stdout).split(b"\0") if item]
    return {name: hashlib.sha256(_blob(root, revision, name)).hexdigest() for name in names}


def _coordination_files(root: Path, revision: str) -> dict[str, str]:
    files: dict[str, str] = {}
    for name in COORDINATION_NAMES:
        path = (COORDINATION_DIR / name).as_posix()
        try:
            files[path] = hashlib.sha256(_blob(root, revision, path)).hexdigest()
        except ManifestError:
            pass
    files.update(_tree_files(root, revision, "docs/goal/evidence"))
    try:
        files["docs/tasks.md"] = hashlib.sha256(_blob(root, revision, "docs/tasks.md")).hexdigest()
    except ManifestError:
        pass
    return files


def _documents_after_archive(value: bytes | None) -> bytes | None:
    return _documents_after_bytes(value)


def _canonical_branch(value: object) -> str | None:
    if not isinstance(value, str) or not value or value != value.strip():
        return None
    branch = value.removeprefix("refs/heads/")
    if not branch or branch.startswith("refs/") or "\\" in branch:
        return None
    if any(part in {"", ".", ".."} for part in branch.split("/")):
        return None
    return branch


def _protected_branch(value: object) -> bool:
    branch = _canonical_branch(value)
    return branch is not None and branch.casefold() in {"main", "master", "development", "default"}


def _canonical_archive_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and value == value.replace("\\", "/")
        and value.startswith("docs/goal/archived/")
        and len(Path(value).parts) == 4
        and all(part not in {"", ".", ".."} for part in Path(value).parts)
    )


def _read_receipt(root: Path, revision: str, receipt_path: str) -> dict[str, Any]:
    try:
        value = json.loads(_blob(root, revision, receipt_path).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ManifestError("archive receipt is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ManifestError("archive receipt must be an object")
    errors = validate_archive_receipt(value)
    if errors:
        raise ManifestError("; ".join(errors))
    return value


def _read_archive_anchor(root: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    path_value = receipt.get("anchor_path")
    if not isinstance(path_value, str):
        raise ManifestError("archive receipt is missing external anchor_path")
    anchor_path = Path(path_value).resolve(strict=False)
    if str(anchor_path) != path_value or anchor_path.is_relative_to(root.resolve()):
        raise ManifestError("archive anchor path is not canonical and external")
    if not anchor_path.is_file():
        raise ManifestError("archive anchor file is missing")
    try:
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("archive anchor is not valid JSON") from exc
    errors = validate_archive_anchor(anchor, root=root)
    if errors:
        raise ManifestError("; ".join(errors))
    if anchor.get("anchor_path") != path_value or anchor.get("anchor_path_sha256") != receipt.get("anchor_path_sha256"):
        raise ManifestError("archive anchor path identity does not match receipt")
    if anchor.get("receipt_sha256") != receipt.get("receipt_sha256") or anchor.get("anchor_nonce") != receipt.get("anchor_nonce"):
        raise ManifestError("archive anchor receipt or nonce does not match")
    for key in ("run_id", "plan_id", "plan_revision", "plan_digest_sha256", "candidate_c", "branch", "branch_ref", "expected_main", "main_ref", "stamp", "archive_path"):
        if anchor.get(key) != receipt.get(key):
            raise ManifestError(f"archive anchor authority does not match receipt: {key}")
    if anchor.get("source_inventory") != receipt.get("moves"):
        raise ManifestError("archive anchor source inventory does not match receipt moves")
    moves = receipt.get("moves")
    expected_moves_digest = hashlib.sha256(json.dumps(moves, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    if anchor.get("moves_sha256") != expected_moves_digest:
        raise ManifestError("archive anchor moves digest does not match receipt")
    return anchor


def _replacement_base_from_plan(
    root: Path,
    plan: dict[str, Any],
    *,
    branch: str,
    candidate_c: str,
    expected_main: str,
) -> tuple[str | None, dict[str, Any]]:
    """Resolve an explicit prior archive candidate for a correction RUN."""

    sources = [
        source
        for source in plan.get("sources", [])
        if isinstance(source, dict)
        and " ".join(
            str(source.get("kind", "")).replace("_", " ").split()
        ).casefold()
        == "prior archive candidate"
    ]
    if not sources:
        return None, {
            "prior_publication_state": "not_applicable",
            "prior_publication_receipt_path": None,
            "prior_publication_receipt_sha256": None,
        }
    if len(sources) != 1:
        raise ManifestError(
            "correction RUN requires exactly one prior archive candidate source"
        )
    source = sources[0]
    revision = source.get("source_revision")
    location = source.get("location")
    content_sha256 = source.get("content_sha256")
    if not is_full_sha(revision):
        raise ManifestError(
            "prior archive candidate source_revision must be exact A"
        )
    if (
        not isinstance(location, str)
        or not _canonical_archive_path(str(Path(location).parent).replace("\\", "/"))
        or Path(location).name != ARCHIVE_RECEIPT_NAME
    ):
        raise ManifestError(
            "prior archive candidate source must name its archived ARCHIVE_RECEIPT.json"
        )
    notes = str(source.get("notes", ""))
    state_match = re.search(
        r"(?:^|;)prior_publication_state=(published|unpublished)(?:;|$)",
        notes,
        re.IGNORECASE,
    )
    if state_match is None:
        raise ManifestError(
            "prior archive candidate source must bind prior_publication_state in notes"
        )
    publication_state = state_match.group(1).casefold()
    receipt_match = re.search(
        r"(?:^|;)prior_publication_receipt=(none|[^;]+)(?:;|$)",
        notes,
        re.IGNORECASE,
    )
    if receipt_match is None:
        raise ManifestError(
            "prior archive candidate source must bind prior_publication_receipt in notes"
        )
    receipt_descriptor = receipt_match.group(1)
    prior_publication_receipt_path: str | None = None
    prior_publication_receipt_sha256: str | None = None
    if publication_state == "published":
        if "@" not in receipt_descriptor:
            raise ManifestError(
                "published prior archive candidate must bind receipt path@sha256"
            )
        prior_publication_receipt_path, prior_publication_receipt_sha256 = receipt_descriptor.rsplit("@", 1)
        prior_publication_receipt_path = _canonical_external_path(
            prior_publication_receipt_path,
            label="prior_publication_receipt_path",
            root=root,
        )
        _require_sha(
            prior_publication_receipt_sha256,
            length=64,
            label="prior_publication_receipt_sha256",
        )
        prior_path = Path(prior_publication_receipt_path)
        if not prior_path.is_file():
            raise ManifestError("published prior archive candidate receipt is missing")
        if hashlib.sha256(prior_path.read_bytes()).hexdigest() != prior_publication_receipt_sha256:
            raise ManifestError("published prior archive candidate receipt hash does not match")
        try:
            publication_receipt = json.loads(prior_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ManifestError("published prior archive candidate receipt is not valid JSON") from exc
        if not isinstance(publication_receipt, dict):
            raise ManifestError("published prior archive candidate receipt must be an object")
        if publication_receipt.get("protocol") != RECEIPT_PROTOCOL or publication_receipt.get("status") != "PASS":
            raise ManifestError("published prior archive candidate receipt must be a closed PASS receipt")
        unsigned_receipt = {
            key: value for key, value in publication_receipt.items() if key != "receipt_sha256"
        }
        if publication_receipt.get("receipt_sha256") != _digest(unsigned_receipt):
            raise ManifestError("published prior archive candidate receipt digest is invalid")
        if publication_receipt.get("candidate_a") != revision:
            raise ManifestError("published prior archive candidate receipt does not bind prior A")
        if publication_receipt.get("branch_ref") != f"refs/heads/{branch}":
            raise ManifestError("published prior archive candidate receipt branch does not match")
        prior_request_path = publication_receipt.get("request_path")
        if not isinstance(prior_request_path, str):
            raise ManifestError("published prior receipt is missing its immutable request path")
        prior_request = _load_request(Path(prior_request_path), root)
        prior_attempt = _load_attempt(prior_request, root)
        if prior_request.get("candidate_a") != revision:
            raise ManifestError("published prior request does not bind prior A")
        prior_evidence = _read_execution_evidence(
            root,
            prior_request,
            prior_attempt,
        )
        if prior_evidence.get("readback_head_sha") != revision:
            raise ManifestError("published prior evidence does not read back prior A")
    elif receipt_descriptor.casefold() != "none":
        raise ManifestError("unpublished prior archive candidate must prove no publication receipt")
    receipt_bytes = _blob(root, revision, location)
    if (
        not isinstance(content_sha256, str)
        or hashlib.sha256(receipt_bytes).hexdigest() != content_sha256
    ):
        raise ManifestError("prior archive candidate source hash does not match exact A")
    prior_receipt = _read_receipt(root, revision, location)
    prior_anchor = _read_archive_anchor(root, prior_receipt)
    deterministic_receipt = _deterministic_publication_receipt_path(prior_anchor["anchor_path"])
    if deterministic_receipt.is_file():
        deterministic_digest = hashlib.sha256(deterministic_receipt.read_bytes()).hexdigest()
        if publication_state != "published":
            raise ManifestError(
                "prior publication notes claim unpublished but the deterministic publication receipt exists"
            )
        if (
            prior_publication_receipt_path != str(deterministic_receipt.resolve())
            or prior_publication_receipt_sha256 != deterministic_digest
        ):
            raise ManifestError(
                "prior publication notes do not match the deterministic publication receipt"
            )
    elif publication_state == "published":
        raise ManifestError(
            "published prior archive candidate requires its deterministic publication receipt"
        )
    if _canonical_branch(prior_receipt.get("branch")) != branch:
        raise ManifestError("prior archive candidate belongs to another run branch")
    if prior_receipt.get("expected_main") != expected_main:
        raise ManifestError("prior archive candidate records another main base")
    parents = _out(root, "rev-list", "--parents", "-n", "1", revision).split()
    if (
        len(parents) != 2
        or parents[1] != prior_receipt.get("candidate_c")
    ):
        raise ManifestError("prior archive candidate is not its receipt-bound archive A")
    if _git(root, "merge-base", "--is-ancestor", revision, candidate_c).returncode != 0:
        raise ManifestError("prior archive candidate is not an ancestor of correction C2")
    return revision, {
        "prior_publication_state": publication_state,
        "prior_publication_receipt_path": prior_publication_receipt_path,
        "prior_publication_receipt_sha256": prior_publication_receipt_sha256,
    }


def _has_receipt_bound_archive(root: Path, revision: str) -> bool:
    """Return whether a revision is an archive-only candidate with a receipt."""

    if not is_full_sha(revision):
        return False
    result = _git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        revision,
        "--",
        "docs/goal/archived",
    )
    if result.returncode != 0:
        return False
    for name in result.stdout.splitlines():
        if not name.endswith("/" + ARCHIVE_RECEIPT_NAME):
            continue
        try:
            receipt = _read_receipt(root, revision, name)
        except ManifestError:
            continue
        if receipt.get("candidate_c") and receipt.get("branch_ref"):
            parents = _out(root, "rev-list", "--parents", "-n", "1", revision).split()
            if len(parents) == 2 and receipt.get("candidate_c") == parents[1]:
                return True
    return False


def _archive_lineage_candidates(
    root: Path,
    candidate_c: str,
    expected_main: str,
) -> list[str]:
    """List receipt-bound archive candidates after the recorded main base."""

    result = _git(
        root,
        "rev-list",
        "--first-parent",
        candidate_c,
        "--not",
        expected_main,
    )
    if result.returncode != 0:
        raise ManifestError("cannot inspect candidate first-parent lineage")
    return [
        revision
        for revision in result.stdout.splitlines()
        if is_full_sha(revision) and _has_receipt_bound_archive(root, revision)
    ]


def verify_archive_candidate(root: Path, *, archive_path: Path, candidate_a: str) -> dict[str, Any]:
    """Verify archive-only candidate A using the receipt as byte authority."""

    root = _root(root)
    if not is_full_sha(candidate_a):
        raise ManifestError("candidate A must be a lowercase full Git SHA")
    rel = _archive_rel(root, archive_path)
    branch = _canonical_branch(_out(root, "branch", "--show-current"))
    if branch is None or _protected_branch(branch):
        raise ManifestError("archive candidate requires a named non-protected branch")
    if _out(root, "rev-parse", "HEAD") != candidate_a:
        raise ManifestError("live HEAD is not archive candidate A")
    if _out(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ManifestError("archive candidate checkout must be clean")
    parents = _out(root, "rev-list", "--parents", "-n", "1", candidate_a).split()
    if len(parents) != 2 or not is_full_sha(parents[1]):
        raise ManifestError("archive A must be a direct non-merge child of C")
    candidate_c = parents[1]
    archive_prefix = rel.as_posix()
    receipt_path = f"{archive_prefix}/{ARCHIVE_RECEIPT_NAME}"
    plan_path = f"{archive_prefix}/PLAN.md"
    run_path = f"{archive_prefix}/RUN.md"
    plan = _manifest(root, candidate_a, plan_path, PLAN_HEADING, "harness_plan")
    run = _manifest(root, candidate_a, run_path, RUN_HEADING, "harness_run")
    receipt = _read_receipt(root, candidate_a, receipt_path)
    if archive_first_required(run):
        _read_archive_anchor(root, receipt)

    validation_errors = []
    validation_errors.extend(validate_plan(plan, repo_root=root))
    validation_errors.extend(validate_run(plan, run))
    validation_errors.extend(validate_frozen_contract_joins(plan, root, run=run))
    validation_errors.extend(validate_ui_evidence_files(plan, run, root))
    if validation_errors:
        raise ManifestError("archived PLAN/RUN validation failed: " + "; ".join(validation_errors[:8]))

    integration = run.get("integration")
    if not isinstance(integration, dict):
        raise ManifestError("archived RUN integration is missing")
    archived_branch = _canonical_branch(integration.get("branch"))
    if archived_branch is None or archived_branch != branch:
        raise ManifestError("archived integration.branch does not match the live run branch")
    if run.get("status") != "complete" or integration.get("integration_head_sha") != candidate_c:
        raise ManifestError("archived RUN must be complete and record candidate C")
    prior_sources = [
        source
        for source in plan.get("sources", [])
        if isinstance(source, dict)
        and " ".join(str(source.get("kind", "")).replace("_", " ").split()).casefold()
        == "prior archive candidate"
    ]
    lineage_archives = _archive_lineage_candidates(
        root,
        candidate_c,
        receipt.get("expected_main"),
    )
    if lineage_archives and len(prior_sources) != 1:
        raise ManifestError(
            "correction candidate descends from a receipt-bound archive A and "
            "must include exactly one prior archive candidate source"
        )
    replacement_base, prior_publication = _replacement_base_from_plan(
        root,
        plan,
        branch=branch,
        candidate_c=candidate_c,
        expected_main=receipt.get("expected_main"),
    )
    if lineage_archives and replacement_base != lineage_archives[0]:
        raise ManifestError(
            "prior archive candidate source must bind the latest receipt-bound archive A"
        )
    if run.get("plan", {}).get("id") != plan.get("plan_id") or run.get("plan", {}).get("revision") != plan.get("revision") or run.get("plan", {}).get("digest_sha256") != plan_digest(plan):
        raise ManifestError("archived PLAN/RUN identity or digest mismatch")
    expected_authority = {
        "run_id": run.get("run_id"),
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": plan_digest(plan),
        "candidate_c": candidate_c,
        "archive_path": archive_prefix,
        "branch_ref": f"refs/heads/{branch}",
    }
    for key, expected in expected_authority.items():
        if receipt.get(key) != expected:
            raise ManifestError(f"archive receipt authority does not match archived PLAN/RUN/A: {key}")
    if _canonical_branch(receipt.get("branch")) != branch:
        raise ManifestError("archive receipt branch does not match the live run branch")
    stamp = receipt.get("stamp")
    if (receipt.get("expected_main") is not None or receipt.get("main_ref") is not None) and (not isinstance(stamp, str) or not rel.name.startswith(stamp + "-")):
        raise ManifestError("archive receipt stamp does not match archive path")

    moves = receipt.get("moves")
    if not isinstance(moves, list):
        raise ManifestError("archive receipt moves are malformed")
    move_map = {str(item["destination"]): item for item in moves if isinstance(item, dict) and isinstance(item.get("destination"), str)}
    actual_archive = _tree_files(root, candidate_a, archive_prefix)
    expected_destinations = set(move_map)
    if set(actual_archive) != expected_destinations | {receipt_path}:
        raise ManifestError("archive tree has extra or missing files")
    for destination, move in move_map.items():
        if actual_archive[destination] != move["sha256"]:
            raise ManifestError(f"archive blob does not match receipt move: {destination}")
        source = str(move["source"])
        if _git(root, "cat-file", "-e", f"{candidate_a}:{source}").returncode == 0:
            raise ManifestError(f"live coordination path remains in A: {source}")

    source_names = {str(item["source"]) for item in moves if isinstance(item, dict)}
    if "docs/goal/PLAN.md" not in source_names or "docs/goal/RUN.md" not in source_names:
        raise ManifestError("archive receipt moves must include PLAN.md and RUN.md")
    c_files = _coordination_files(root, candidate_c)
    allowed_changes = set(c_files) | source_names | expected_destinations | {receipt_path, DOCUMENTS_PATH.as_posix()}
    changed = set(filter(None, _out(root, "diff", "--name-only", candidate_c, candidate_a).splitlines()))
    if not changed.issubset(allowed_changes):
        raise ManifestError("C->A changed files include an unauthorized path")
    c_docs = None
    try:
        c_docs = _blob(root, candidate_c, DOCUMENTS_PATH.as_posix())
    except ManifestError:
        pass
    try:
        a_docs = _blob(root, candidate_a, DOCUMENTS_PATH.as_posix())
    except ManifestError:
        a_docs = None
    expected_docs = _documents_after_archive(c_docs)
    if a_docs != expected_docs:
        raise ManifestError("DOCUMENTS.md is not the deterministic archive_run transformation")
    if receipt.get("documents_before_sha256") != (hashlib.sha256(c_docs).hexdigest() if c_docs is not None else None):
        raise ManifestError("ARCHIVE_RECEIPT documents_before_sha256 is incorrect")
    if receipt.get("documents_after_sha256") != (hashlib.sha256(expected_docs).hexdigest() if expected_docs is not None else None):
        raise ManifestError("ARCHIVE_RECEIPT documents_after_sha256 is incorrect")
    expected_main = receipt.get("expected_main")
    main_ref = receipt.get("main_ref")
    observed_main = _out(root, "rev-parse", "--verify", f"{main_ref}^{{commit}}")
    if observed_main != expected_main:
        raise ManifestError("archive receipt main_ref no longer resolves to expected_main")
    ancestry = _git(root, "merge-base", "--is-ancestor", expected_main, candidate_c)
    if ancestry.returncode != 0:
        raise ManifestError("expected_main is not an ancestor of candidate C")
    receipt_digest = hashlib.sha256(_blob(root, candidate_a, receipt_path)).hexdigest()
    archive_hashes = {path: digest for path, digest in actual_archive.items()}
    return {
        **expected_authority,
        "run_schema_version": run.get("schema_version"),
        "run_branch": branch,
        "candidate_a": candidate_a,
        "replacement_base": replacement_base,
        **prior_publication,
        "archive_path": archive_prefix,
        "archive_hashes": archive_hashes,
        "moves": moves,
        "archive_receipt_sha256": receipt_digest,
        "expected_main": receipt.get("expected_main"),
        "main_ref": receipt.get("main_ref"),
        "stamp": stamp,
        "documents_before_sha256": receipt.get("documents_before_sha256"),
        "documents_after_sha256": receipt.get("documents_after_sha256"),
        "anchor_path": receipt.get("anchor_path"),
        "anchor_path_sha256": receipt.get("anchor_path_sha256"),
        "anchor_nonce": receipt.get("anchor_nonce"),
    }


def _read_closed(path: Path, protocol: str, keys: set[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read immutable artifact: {exc}") from exc
    if not isinstance(value, dict) or value.get("protocol") != protocol or set(value) != keys:
        raise ManifestError("immutable artifact has missing or extra fields")
    return value


def _write_closed(path: Path, value: dict[str, Any], root: Path) -> None:
    if path.resolve().is_relative_to(root.resolve()):
        raise ManifestError("immutable request/receipt must be outside checkout")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, sort_keys=True, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise ManifestError("immutable request/receipt path is already consumed") from exc


def _remote_state(root: Path, endpoint: str, branch_ref: str) -> str | None:
    """Read a remote ref through the exact URL bound to the request.

    The configured remote-name form remains accepted for backwards-compatible
    diagnostics/tests, but all archive publication paths pass the immutable
    canonical URL and never emit a remote name to a trusted host.
    """

    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", endpoint or ""):
        checked = _safe_remote(endpoint, configured_name=True)
        _, url = _verify_configured_remote(root, checked)
    else:
        url = _safe_push_url(endpoint)
    # Read the exact URL from a fresh non-repository cwd with system/global
    # config disabled.  This closes the check-to-use window in which a config
    # rewrite could be inserted after the normal repository preflight.  A
    # private remote that needs credential helpers must be read by the trusted
    # host's separately authenticated publication process instead.
    isolated_directory = Path(tempfile.mkdtemp(prefix="harness-git-isolated-"))
    try:
        environment = git_environment()
        environment["GIT_CONFIG_NOSYSTEM"] = "1"
        environment["GIT_CONFIG_GLOBAL"] = os.devnull if os.name != "nt" else "NUL"
        environment["GIT_CEILING_DIRECTORIES"] = str(isolated_directory)
        result = subprocess.run(
            ["git", "--no-replace-objects", "ls-remote", "--", url, branch_ref],
            cwd=isolated_directory,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ManifestError(f"isolated configured remote read failed: {exc}") from exc
    finally:
        try:
            isolated_directory.rmdir()
        except OSError:
            # Never recursively delete an attacker-populated isolation path.
            # Git ls-remote should not create files; leave unexpected contents
            # for the host's normal temporary-directory cleanup.
            pass
    if result.returncode != 0:
        raise ManifestError("configured remote readback failed")
    lines = result.stdout.strip().splitlines()
    if not lines:
        return None
    fields = lines[0].split()
    if len(fields) != 2 or fields[1] != branch_ref or not is_full_sha(fields[0]):
        raise ManifestError("remote readback is malformed")
    return fields[0]


def prepare(
    root: Path,
    *,
    archive_path: Path,
    remote: str,
    request_path: Path,
    attempt_path: Path,
    receipt_path: Path,
    archive_anchor: Path | None = None,
    execution_evidence_path: Path | None = None,
    authorization_source: str | None = None,
    authorization_ref: str | None = None,
) -> dict[str, Any]:
    root = _root(root)
    if authorization_source is not None or authorization_ref is not None:
        raise ManifestError(
            "caller-supplied authorization prose/ref is rejected; prepare only creates a trusted-host handoff"
        )
    request_path = Path(_canonical_external_path(request_path, label="request_path", root=root))
    attempt_path = Path(_canonical_external_path(attempt_path, label="attempt_path", root=root))
    receipt_path = Path(_canonical_external_path(receipt_path, label="receipt_path", root=root))
    if execution_evidence_path is None:
        execution_evidence_path = request_path.with_name(
            request_path.stem + ".execution.json"
        )
    execution_evidence_path = Path(
        _canonical_external_path(
            execution_evidence_path,
            label="execution_evidence_path",
            root=root,
        )
    )
    policy = _discover_machine_trust_policy(root=root)
    try:
        verifier_path = Path(_discover_os_managed_verifier(root=root))
        policy_id = policy.policy_id
        policy_sha256 = policy.allowed_signers_sha256
        policy_principal = policy.principal
    finally:
        policy.cleanup()
    if len({request_path, attempt_path, receipt_path, execution_evidence_path}) != 4:
        raise ManifestError(
            "request, attempt, receipt, and execution evidence paths must be pairwise distinct"
        )
    if any(path.exists() for path in (request_path, attempt_path, receipt_path, execution_evidence_path)):
        raise ManifestError("request/attempt/receipt/evidence paths must be unused")
    candidate_a = _out(root, "rev-parse", "HEAD")
    verified = verify_archive_candidate(root, archive_path=archive_path, candidate_a=candidate_a)
    _manifest(root, candidate_a, f"{verified['archive_path']}/PLAN.md", PLAN_HEADING, "harness_plan")
    run = _manifest(root, candidate_a, f"{verified['archive_path']}/RUN.md", RUN_HEADING, "harness_run")
    if not archive_first_required(run):
        raise ManifestError("archive-first prepare requires a valid >=0.38 RUN pin")
    _validate_archive_authority(verified)
    if archive_anchor is None:
        raise ManifestError("prepare requires --archive-anchor for archive-first candidates")
    if archive_anchor is not None and str(Path(archive_anchor).resolve()) != verified["anchor_path"]:
        raise ManifestError("--archive-anchor does not match ARCHIVE_RECEIPT anchor_path")
    deterministic_receipt = _deterministic_publication_receipt_path(verified["anchor_path"])
    if receipt_path != deterministic_receipt:
        raise ManifestError(
            "v3 receipt_path must be the deterministic anchor-bound publication receipt path"
        )
    checked = _safe_remote(remote, configured_name=True)
    _, url = _verify_configured_remote(root, checked)
    url = _safe_push_url(url)
    pre = _remote_state(root, url, verified["branch_ref"])
    replacement_base = verified.get("replacement_base")
    if replacement_base is None:
        allowed_pre = {None, verified["candidate_c"]}
    elif verified.get("prior_publication_state") == "published":
        allowed_pre = {replacement_base}
    elif verified.get("prior_publication_state") == "unpublished":
        allowed_pre = {None}
    else:
        raise ManifestError("correction archive is missing prior publication state")
    if pre not in allowed_pre:
        expectation = (
            "the exact published replacement base"
            if verified.get("prior_publication_state") == "published"
            else "absent because the prior candidate was not published"
            if replacement_base is not None
            else "absent or C"
        )
        raise ManifestError(
            f"remote pre-state must be {expectation}"
        )
    metadata = _push_url_metadata(url)
    request = {
        "protocol": REQUEST_PROTOCOL,
        "authorization_source": LOCAL_AUTHORIZATION_SOURCE,
        "authorization_ref": LOCAL_AUTHORIZATION_REF,
        "plan_id": verified["plan_id"],
        "plan_revision": verified["plan_revision"],
        "plan_digest_sha256": verified["plan_digest_sha256"],
        "run_id": verified["run_id"],
        "run_schema_version": verified["run_schema_version"],
        "archive_path": verified["archive_path"],
        "archive_hashes": verified["archive_hashes"],
        "moves": verified["moves"],
        "archive_receipt_sha256": verified["archive_receipt_sha256"],
        "expected_main": verified["expected_main"],
        "main_ref": verified["main_ref"],
        "stamp": verified["stamp"],
        "documents_before_sha256": verified["documents_before_sha256"],
        "documents_after_sha256": verified["documents_after_sha256"],
        "anchor_path": verified["anchor_path"],
        "anchor_path_sha256": verified["anchor_path_sha256"],
        "anchor_nonce": verified["anchor_nonce"],
        "candidate_c": verified["candidate_c"],
        "replacement_base": verified.get("replacement_base"),
        "prior_publication_state": verified["prior_publication_state"],
        "prior_publication_receipt_path": verified.get("prior_publication_receipt_path"),
        "prior_publication_receipt_sha256": verified.get("prior_publication_receipt_sha256"),
        "candidate_a": verified["candidate_a"],
        "run_branch": verified["run_branch"],
        "branch_ref": verified["branch_ref"],
        "remote": checked,
        "push_url": url,
        **metadata,
        "remote_pre_push_head": pre,
        "request_path": str(request_path),
        "request_path_sha256": _path_digest(request_path),
        "attempt_path": str(attempt_path),
        "attempt_path_sha256": _path_digest(attempt_path),
        "receipt_path": str(receipt_path),
        "receipt_path_sha256": _path_digest(receipt_path),
        "execution_evidence_path": str(execution_evidence_path),
        "execution_evidence_path_sha256": _path_digest(execution_evidence_path),
        "trust_policy_id": policy_id,
        "trust_policy_sha256": policy_sha256,
        "trusted_host_principal": policy_principal,
        "signature_verifier_path": str(verifier_path),
        "signature_verifier_sha256": hashlib.sha256(verifier_path.read_bytes()).hexdigest(),
        "execution_nonce": secrets.token_hex(32),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _validate_request_values(request, root, request_path)
    request["request_sha256"] = _digest(request)
    _write_closed(request_path, request, root)
    return request


def _load_request(path: Path, root: Path) -> dict[str, Any]:
    request = _read_closed(path, REQUEST_PROTOCOL, REQUEST_KEYS)
    loaded_path = path.resolve(strict=False)
    if request.get("request_path") != str(loaded_path):
        raise ManifestError("request was copied or moved; request_path does not match")
    if request["request_sha256"] != _digest({k: v for k, v in request.items() if k != "request_sha256"}):
        raise ManifestError("request digest mismatch")
    _validate_request_values(request, root, loaded_path)
    return request


def _request_matches_authority(request: dict[str, Any], authority: dict[str, Any]) -> None:
    # Every archive identity field is compared, including nested move rows and
    # deterministic DOCUMENTS hashes.  Recomputing request_sha256 cannot turn
    # a semantic edit into a valid side effect.
    for key in (
        "plan_id", "plan_revision", "plan_digest_sha256", "run_id", "run_schema_version",
        "archive_path", "archive_hashes", "moves", "archive_receipt_sha256",
        "expected_main", "main_ref", "stamp", "documents_before_sha256",
        "documents_after_sha256", "candidate_c", "candidate_a", "replacement_base", "run_branch", "branch_ref",
        "prior_publication_state", "prior_publication_receipt_path", "prior_publication_receipt_sha256",
        "anchor_path", "anchor_path_sha256", "anchor_nonce",
    ):
        if request.get(key) != authority.get(key):
            raise ManifestError(f"request archive authority mismatch: {key}")


def _configured_endpoint(root: Path, request: dict[str, Any]) -> tuple[str, str, dict[str, str]]:
    checked, url = _verify_configured_remote(root, request["remote"])
    url = _safe_push_url(url)
    metadata = _push_url_metadata(url)
    metadata["push_url"] = url
    _validate_endpoint(metadata)
    if checked != request["remote"] or metadata != {
        key: request[key] for key in metadata
    }:
        raise ManifestError("configured push endpoint does not match the request")
    return checked, url, metadata


def _validate_receipt_values(receipt: dict[str, Any], root: Path) -> None:
    if receipt.get("status") != "PASS":
        raise ManifestError("receipt status must be PASS")
    _require_sha(receipt.get("request_sha256"), length=64, label="receipt.request_sha256")
    _require_sha(receipt.get("readback_head_sha"), label="receipt.readback_head_sha")
    _require_sha(receipt.get("candidate_a"), label="receipt.candidate_a")
    _require_sha(receipt.get("candidate_c"), label="receipt.candidate_c")
    _require_nonempty(receipt.get("remote"), "receipt.remote")
    _validate_endpoint(receipt)
    _canonical_external_path(receipt.get("attempt_path"), label="receipt.attempt_path", root=root)
    _canonical_external_path(receipt.get("request_path"), label="receipt.request_path", root=root)
    _canonical_external_path(receipt.get("receipt_path"), label="receipt.receipt_path", root=root)
    for key in ("request_path_sha256", "attempt_path_sha256", "receipt_path_sha256"):
        _require_sha(receipt.get(key), length=64, label=f"receipt.{key}")
    _validate_archive_authority(receipt)
    if receipt.get("readback_head_sha") != receipt.get("candidate_a"):
        raise ManifestError("receipt readback_head_sha must equal candidate_a")
    _canonical_external_path(
        receipt.get("execution_evidence_path"),
        label="receipt.execution_evidence_path",
        root=root,
    )
    for key in (
        "execution_evidence_path_sha256",
        "execution_evidence_sha256",
    ):
        _require_sha(receipt.get(key), length=64, label=f"receipt.{key}")
    _require_nonempty(receipt.get("trusted_host_issuer"), "receipt.trusted_host_issuer")
    _require_nonempty(receipt.get("trusted_host_principal"), "receipt.trusted_host_principal")
    _require_nonempty(receipt.get("trust_policy_id"), "receipt.trust_policy_id")
    _require_sha(receipt.get("trust_policy_sha256"), length=64, label="receipt.trust_policy_sha256")
    _trusted_signature_verifier_path(receipt.get("signature_verifier_path"), root=root)
    for key in ("trust_policy_sha256", "signature_verifier_sha256"):
        _require_sha(receipt.get(key), length=64, label=f"receipt.{key}")


def _pre_push_recheck(root: Path, request: dict[str, Any], authority: dict[str, Any]) -> tuple[str, str]:
    fresh = verify_archive_candidate(root, archive_path=root / request["archive_path"], candidate_a=request["candidate_a"])
    _request_matches_authority(request, fresh)
    branch = _out(root, "branch", "--show-current")
    if branch != request["run_branch"]:
        raise ManifestError("branch changed before archive push")
    if _out(root, "rev-parse", "HEAD") != request["candidate_a"]:
        raise ManifestError("HEAD changed before archive push")
    if _out(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ManifestError("checkout became dirty before archive push")
    _, url, _ = _configured_endpoint(root, request)
    if _remote_state(root, url, request["branch_ref"]) != request["remote_pre_push_head"]:
        raise ManifestError("remote pre-state changed before archive push")
    return url


def begin_handoff(root: Path, *, request_path: Path) -> dict[str, Any]:
    root = _root(root)
    request = _load_request(request_path, root)
    attempt_path = Path(request["attempt_path"])
    if attempt_path.exists():
        raise ManifestError("attempt already exists; recover or verify instead of replaying execute")
    receipt_path = Path(request["receipt_path"])
    if receipt_path.exists():
        raise ManifestError("request already consumed by a receipt")
    verified = verify_archive_candidate(root, archive_path=root / request["archive_path"], candidate_a=request["candidate_a"])
    _request_matches_authority(request, verified)
    _configured_endpoint(root, request)
    if _remote_state(root, request["push_url"], request["branch_ref"]) != request["remote_pre_push_head"]:
        raise ManifestError("remote pre-state drifted before archive push")
    endpoint_kind = request["push_endpoint_kind"]
    endpoint_summary = request["push_endpoint_summary"]
    endpoint_digest = request["push_url_sha256"]
    remote_pre_push_head = request.get("remote_pre_push_head")
    attempt = {
        "protocol": ATTEMPT_PROTOCOL,
        "request_sha256": request["request_sha256"],
        "attempt_path": request["attempt_path"],
        "attempt_path_sha256": request["attempt_path_sha256"],
        "execution_nonce": request["execution_nonce"],
        "candidate_a": request["candidate_a"],
        "replacement_base": request.get("replacement_base"),
        "prior_publication_state": request["prior_publication_state"],
        "prior_publication_receipt_path": request.get("prior_publication_receipt_path"),
        "prior_publication_receipt_sha256": request.get("prior_publication_receipt_sha256"),
        "branch_ref": request["branch_ref"],
        "remote": request["remote"],
        "push_url": request["push_url"],
        "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "push_mode": "no_force",
        "push_endpoint_kind": endpoint_kind,
        "push_endpoint_summary": endpoint_summary,
        "push_url_sha256": endpoint_digest,
        "remote_pre_push_head": remote_pre_push_head,
        "execution_evidence_path": request["execution_evidence_path"],
        "execution_evidence_path_sha256": request["execution_evidence_path_sha256"],
        "trust_policy_id": request["trust_policy_id"],
        "trust_policy_sha256": request["trust_policy_sha256"],
        "signature_verifier_path": request["signature_verifier_path"],
        "signature_verifier_sha256": request["signature_verifier_sha256"],
    }
    attempt["attempt_sha256"] = _digest(attempt)
    _write_closed(attempt_path, attempt, root)
    # Recheck endpoint, branch, candidate, and remote pre-state immediately
    # after writing the attempt.  The local tool never performs publication:
    # a human or trusted host must execute the exact no-force push, then call
    # ``recover``/``verify-receipt`` for read-back and receipt closure.
    push_url = _pre_push_recheck(root, request, verified)
    push_argv = _execution_argv(request)
    return {
        "status": PENDING_TRUSTED_HOST_STATUS,
        "request_sha256": request["request_sha256"],
        "attempt_path": request["attempt_path"],
        "attempt_path_sha256": request["attempt_path_sha256"],
        "execution_nonce": request["execution_nonce"],
        "candidate_a": request["candidate_a"],
        "branch_ref": request["branch_ref"],
        "remote": request["remote"],
        "push_url": push_url,
        "push_mode": "no_force",
        "push_endpoint_kind": endpoint_kind,
        "push_endpoint_summary": endpoint_summary,
        "push_url_sha256": endpoint_digest,
        "remote_pre_push_head": remote_pre_push_head,
        "receipt_path": request["receipt_path"],
        "receipt_path_sha256": request["receipt_path_sha256"],
        "execution_evidence_path": request["execution_evidence_path"],
        "execution_evidence_path_sha256": request["execution_evidence_path_sha256"],
        "push_argv": push_argv,
        "push_argv_sha256": _digest(push_argv),
        "message": (
            "trusted host must independently reload the immutable request, "
            "revalidate authorization and the exact URL immediately before the "
            "no-force push, then write detached signed execution evidence; "
            "local executor did not push"
        ),
    }


def execute(root: Path, *, request_path: Path) -> dict[str, Any]:
    """Compatibility alias for :func:`begin_handoff`; never invokes Git push."""

    return begin_handoff(root, request_path=request_path)


def _load_attempt(request: dict[str, Any], root: Path) -> dict[str, Any]:
    attempt = _read_closed(Path(request["attempt_path"]), ATTEMPT_PROTOCOL, ATTEMPT_KEYS)
    if attempt["attempt_sha256"] != _digest({k: v for k, v in attempt.items() if k != "attempt_sha256"}):
        raise ManifestError("attempt digest mismatch")
    _canonical_external_path(attempt.get("attempt_path"), label="attempt_path", root=root)
    _canonical_external_path(
        attempt.get("execution_evidence_path"),
        label="attempt.execution_evidence_path",
        root=root,
    )
    if attempt.get("attempt_path") != request.get("attempt_path") or attempt.get("attempt_path_sha256") != request.get("attempt_path_sha256"):
        raise ManifestError("attempt path identity does not match request")
    if attempt.get("started_at") is None:
        raise ManifestError("attempt started_at is missing")
    _validate_timestamp(attempt.get("started_at"), "attempt.started_at")
    _require_sha(attempt.get("request_sha256"), length=64, label="attempt.request_sha256")
    _require_sha(attempt.get("candidate_a"), label="attempt.candidate_a")
    if attempt.get("push_mode") != "no_force":
        raise ManifestError("attempt push_mode must be no_force")
    _validate_endpoint(attempt)
    pre = attempt.get("remote_pre_push_head")
    if pre is not None:
        _require_sha(pre, label="attempt.remote_pre_push_head")
    for key in (
        "request_sha256",
        "attempt_path",
        "attempt_path_sha256",
        "execution_nonce",
        "candidate_a",
        "replacement_base",
        "prior_publication_state",
        "prior_publication_receipt_path",
        "prior_publication_receipt_sha256",
        "branch_ref",
        "remote",
        "push_url",
        "execution_evidence_path",
        "execution_evidence_path_sha256",
        "trust_policy_id",
        "trust_policy_sha256",
        "signature_verifier_path",
        "signature_verifier_sha256",
    ):
        if attempt.get(key) != request.get(key):
            raise ManifestError("attempt identity does not match request")
    for key in (
        "push_endpoint_kind",
        "push_endpoint_summary",
        "push_url_sha256",
        "remote_pre_push_head",
    ):
        if attempt.get(key) != request.get(key):
            raise ManifestError("attempt endpoint identity does not match request")
    return attempt


def verify_receipt(
    root: Path,
    *,
    request_path: Path,
) -> dict[str, Any]:
    root = _root(root)
    request = _load_request(request_path, root)
    attempt = _load_attempt(request, root)
    evidence = _read_execution_evidence(
        root,
        request,
        attempt,
    )
    receipt = _read_closed(Path(request["receipt_path"]), RECEIPT_PROTOCOL, RECEIPT_KEYS)
    _validate_receipt_values(receipt, root)
    if receipt["receipt_sha256"] != _digest({k: v for k, v in receipt.items() if k != "receipt_sha256"}):
        raise ManifestError("receipt digest mismatch")
    if any(
        receipt.get(k) != request.get(k)
        for k in (
            "request_sha256",
            "request_path",
            "request_path_sha256",
            "attempt_path",
            "attempt_path_sha256",
            "receipt_path",
            "receipt_path_sha256",
            "execution_nonce",
            "candidate_a",
            "replacement_base",
            "branch_ref",
            "remote",
            "push_url",
            "remote_pre_push_head",
            "execution_evidence_path",
            "execution_evidence_path_sha256",
            "trust_policy_id",
            "trust_policy_sha256",
            "signature_verifier_path",
            "signature_verifier_sha256",
        )
    ):
        raise ManifestError("receipt identity does not match request")
    if any(receipt.get(k) != request.get(k) for k in (
        "plan_id", "plan_revision", "plan_digest_sha256", "run_id", "run_schema_version",
        "archive_path", "archive_hashes", "moves", "archive_receipt_sha256", "candidate_c",
        "run_branch", "replacement_base", "prior_publication_state", "prior_publication_receipt_path", "prior_publication_receipt_sha256", "expected_main", "main_ref", "stamp", "documents_before_sha256",
        "documents_after_sha256",
        "anchor_path", "anchor_path_sha256", "anchor_nonce",
    )):
        raise ManifestError("receipt archive authority does not match request")
    _, _, metadata = _configured_endpoint(root, request)
    if metadata != {key: receipt[key] for key in metadata}:
        raise ManifestError("configured push endpoint does not match receipt")
    if receipt.get("execution_evidence_sha256") != evidence.get("evidence_sha256"):
        raise ManifestError("receipt trusted-host evidence digest does not match evidence")
    if receipt.get("trusted_host_issuer") != evidence.get("trusted_host_issuer") or receipt.get("trusted_host_principal") != evidence.get("trusted_host_principal"):
        raise ManifestError("receipt trusted-host identity does not match evidence")
    authority = verify_archive_candidate(root, archive_path=root / request["archive_path"], candidate_a=request["candidate_a"])
    _request_matches_authority(request, authority)
    if _remote_state(root, request["push_url"], request["branch_ref"]) != request["candidate_a"]:
        raise ManifestError("fresh readback does not equal A")
    return receipt


def recover_uncertain(
    root: Path,
    *,
    request_path: Path,
) -> dict[str, Any]:
    root = _root(root)
    request = _load_request(request_path, root)
    attempt = _load_attempt(request, root)
    receipt_path = Path(request["receipt_path"])
    if receipt_path.exists():
        return verify_receipt(
            root,
            request_path=request_path,
        )
    evidence = _read_execution_evidence(
        root,
        request,
        attempt,
    )
    authority = verify_archive_candidate(root, archive_path=root / request["archive_path"], candidate_a=request["candidate_a"])
    _request_matches_authority(request, authority)
    if _remote_state(root, request["push_url"], request["branch_ref"]) != request["candidate_a"]:
        raise ManifestError("recovery refuses to push; remote does not already equal A")
    _, _, metadata = _configured_endpoint(root, request)
    receipt = {
        "protocol": RECEIPT_PROTOCOL,
        "status": "PASS",
        "request_path": request["request_path"],
        "request_path_sha256": request["request_path_sha256"],
        "request_sha256": request["request_sha256"],
        "attempt_path": request["attempt_path"],
        "attempt_path_sha256": request["attempt_path_sha256"],
        "receipt_path": request["receipt_path"],
        "receipt_path_sha256": request["receipt_path_sha256"],
        "execution_nonce": request["execution_nonce"],
        "candidate_a": request["candidate_a"],
        "branch_ref": request["branch_ref"],
        "remote": request["remote"],
        "push_url": request["push_url"],
        **metadata,
        "remote_pre_push_head": request["remote_pre_push_head"],
        "readback_head_sha": request["candidate_a"],
        **{key: request[key] for key in (
            "plan_id", "plan_revision", "plan_digest_sha256", "run_id", "run_schema_version",
            "archive_path", "archive_hashes", "moves", "archive_receipt_sha256", "candidate_c",
            "run_branch", "replacement_base", "prior_publication_state", "prior_publication_receipt_path", "prior_publication_receipt_sha256", "expected_main", "main_ref", "stamp", "documents_before_sha256",
            "documents_after_sha256",
            "anchor_path", "anchor_path_sha256", "anchor_nonce",
        )},
        "execution_evidence_path": request["execution_evidence_path"],
        "execution_evidence_path_sha256": request["execution_evidence_path_sha256"],
        "execution_evidence_sha256": evidence["evidence_sha256"],
        "trusted_host_issuer": evidence["trusted_host_issuer"],
        "trusted_host_principal": evidence["trusted_host_principal"],
        "trust_policy_id": request["trust_policy_id"],
        "trust_policy_sha256": request["trust_policy_sha256"],
        "signature_verifier_path": request["signature_verifier_path"],
        "signature_verifier_sha256": request["signature_verifier_sha256"],
    }
    receipt["receipt_sha256"] = _digest(receipt)
    _write_closed(receipt_path, receipt, root)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--repo-root", required=True, type=Path)
    prepare_parser.add_argument("--archive", required=True, type=Path)
    prepare_parser.add_argument("--remote", required=True)
    prepare_parser.add_argument("--request-out", required=True, type=Path)
    prepare_parser.add_argument("--attempt-path", required=True, type=Path)
    prepare_parser.add_argument("--receipt-path", required=True, type=Path)
    prepare_parser.add_argument("--archive-anchor", required=True, type=Path)
    prepare_parser.add_argument("--execution-evidence", type=Path)
    for name in ("begin-handoff", "execute", "verify-receipt", "recover"):
        current = sub.add_parser(name)
        current.add_argument("--repo-root", required=True, type=Path)
        current.add_argument("--request", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            value = prepare(
                args.repo_root,
                archive_path=args.archive,
                remote=args.remote,
                request_path=args.request_out,
                attempt_path=args.attempt_path,
                receipt_path=args.receipt_path,
                archive_anchor=args.archive_anchor,
                execution_evidence_path=args.execution_evidence,
            )
        elif args.command in {"begin-handoff", "execute"}:
            value = begin_handoff(args.repo_root, request_path=args.request)
        elif args.command == "verify-receipt":
            value = verify_receipt(
                args.repo_root,
                request_path=args.request,
            )
        else:
            value = recover_uncertain(
                args.repo_root,
                request_path=args.request,
            )
    except (OSError, ManifestError, ValueError, KeyError, GitMetadataError) as exc:
        print(json.dumps({"status": "ERROR", "errors": [str(exc)]}, sort_keys=True))
        return 2
    payload = dict(value)
    payload.setdefault("status", "PASS")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
