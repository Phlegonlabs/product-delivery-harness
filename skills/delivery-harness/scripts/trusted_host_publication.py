#!/usr/bin/env python3
"""Execute one archive publication on an explicitly trusted host.

This helper is deliberately separate from the local Harness.  It is the only
supported place where the request-bound publication argv may be executed.  The
caller must set ``HARNESS_TRUSTED_HOST=1`` on an administrator-managed host;
without that marker the command exits before it reads credentials or starts Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_git import git_environment, git_executable, _windows_parent_user_writable
from push_archived_candidate import (
    EXECUTION_EVIDENCE_NAMESPACE,
    EXECUTION_EVIDENCE_PROTOCOL,
    _discover_machine_trust_policy,
    _discover_os_managed_verifier,
    _execution_argv,
    _load_attempt,
    _load_request,
    _pre_push_recheck,
    _request_matches_authority,
    _root,
    verify_archive_candidate,
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read immutable publication record {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"publication record {path} must be a JSON object")
    return value


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reserve_output(path: Path) -> tuple[int, tuple[int, int, int]]:
    """Create one exclusive output reservation and retain its inode identity."""

    try:
        if os.name == "nt":
            import ctypes
            import msvcrt
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateFileW.restype = wintypes.HANDLE
            handle = kernel32.CreateFileW(
                str(path),
                0xC0000000,  # GENERIC_READ | GENERIC_WRITE
                0,  # deny concurrent write/delete/replacement
                None,
                1,  # CREATE_NEW
                0x00000080 | 0x00200000,  # NORMAL | OPEN_REPARSE_POINT
                None,
            )
            if handle in (None, wintypes.HANDLE(-1).value):
                raise OSError(ctypes.get_last_error(), "CreateFileW CREATE_NEW failed")
            fd = msvcrt.open_osfhandle(int(handle), os.O_RDWR | getattr(os, "O_BINARY", 0))
        else:
            flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
            fd = os.open(path, flags, 0o600)
        info = os.fstat(fd)
    except OSError as exc:
        raise RuntimeError(f"cannot reserve exclusive output {path}: {exc}") from exc
    return fd, (int(info.st_dev), int(info.st_ino), int(info.st_size))


def _assert_reserved_output(path: Path, fd: int, identity: tuple[int, int, int]) -> None:
    try:
        current = path.stat()
        held = os.fstat(fd)
    except OSError as exc:
        raise RuntimeError(f"reserved output changed or disappeared: {path}") from exc
    if (int(current.st_dev), int(current.st_ino), int(current.st_size)) != (
        identity[0], identity[1], int(held.st_size)
    ):
        raise RuntimeError(f"reserved output was replaced before publication: {path}")


def _write_reserved_output(fd: int, payload: bytes) -> None:
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        view = view[written:]
    os.fsync(fd)


def _validate_one_line_issuer(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or any(
        character in value for character in "\r\n"
    ) or len(value) > 200:
        raise RuntimeError("trusted-host issuer must be one substantive line")
    if not any(character.isalnum() for character in value):
        raise RuntimeError("trusted-host issuer must contain an alphanumeric identity")
    return value


def _validate_signing_key(path: Path, root: Path) -> Path:
    key = path.resolve(strict=True)
    if not key.is_file() or path.is_symlink():
        raise RuntimeError("machine signing key must be a regular non-reparse file")
    try:
        key.relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise RuntimeError("machine signing key must stay outside the repository")
    if os.name != "nt":
        for component in (key, *key.parents):
            info = component.stat()
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise RuntimeError("machine signing key path must be root-owned and not writable by group/other")
        if key.stat().st_mode & 0o077:
            raise RuntimeError("machine signing key must be mode 0600 or stricter")
    elif _windows_parent_user_writable(key.parent):
        raise RuntimeError("machine signing key parent ACL is user-writable")
    return key


def _challenge_sign_and_verify(
    payload: bytes,
    *,
    key: Path,
    verifier: Path,
    verifier_sha256: str,
    signers: Path,
    principal: str,
    output_dir: Path,
) -> None:
    """Prove the key, verifier, policy, principal, and namespace before push."""

    challenge_dir = Path(tempfile.mkdtemp(prefix="trusted-host-challenge-", dir=output_dir))
    signature = challenge_dir / "challenge.sig"
    try:
        _sign_payload(
            payload,
            key,
            verifier,
            verifier_sha256,
            output_dir=challenge_dir,
            signature_path=signature,
        )
        env = git_environment()
        verified = subprocess.run(
            [
                str(verifier),
                "-Y",
                "verify",
                "-f",
                str(signers),
                "-I",
                principal,
                "-n",
                EXECUTION_EVIDENCE_NAMESPACE,
                "-s",
                str(signature),
            ],
            input=payload,
            capture_output=True,
            timeout=30,
            check=False,
            env=env,
        )
        if verified.returncode != 0:
            detail = verified.stderr.decode(errors="replace") if isinstance(verified.stderr, bytes) else str(verified.stderr)
            raise RuntimeError(detail.strip() or "machine challenge signature verification failed")
    finally:
        try:
            signature.unlink()
        except OSError:
            pass
        try:
            challenge_dir.rmdir()
        except OSError:
            pass


def _remote_head(url: str, branch_ref: str, *, cwd: Path) -> str | None:
    isolated = Path(tempfile.mkdtemp(prefix="harness-trusted-host-"))
    try:
        env = git_environment()
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        env["GIT_CONFIG_GLOBAL"] = os.devnull if os.name != "nt" else "NUL"
        result = subprocess.run(
            [git_executable(env), "--no-replace-objects", "ls-remote", "--", url, branch_ref],
            cwd=isolated,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=60,
            check=False,
        )
    finally:
        try:
            isolated.rmdir()
        except OSError:
            pass
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "trusted-host remote read failed")
    if not result.stdout.strip():
        return None
    fields = result.stdout.strip().split()
    if len(fields) != 2 or fields[1] != branch_ref or len(fields[0]) != 40:
        raise RuntimeError("trusted-host remote readback is malformed")
    return fields[0]


def _sign_payload(
    payload: bytes,
    key: Path,
    verifier: Path,
    expected_verifier_sha256: str,
    *,
    output_dir: Path,
    signature_path: Path | None = None,
) -> tuple[Path, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload_path = output_dir / f".publication-payload-{secrets.token_hex(8)}.json"
    payload_path.write_bytes(payload)
    signature_path = signature_path or output_dir / f"publication-{secrets.token_hex(8)}.sig"
    try:
        if _sha256_file(verifier) != expected_verifier_sha256:
            raise RuntimeError("OS-managed signature verifier changed before signing")
        result = subprocess.run(
            [
                str(verifier),
                "-Y",
                "sign",
                "-f",
                str(key),
                "-n",
                EXECUTION_EVIDENCE_NAMESPACE,
                str(payload_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "machine signature failed")
        if not signature_path.is_file():
            # OpenSSH versions without signature_file write <payload>.sig.
            generated = payload_path.with_name(payload_path.name + ".sig")
            if generated.is_file():
                generated.replace(signature_path)
        if not signature_path.is_file():
            raise RuntimeError("machine signature command produced no detached signature")
        if _sha256_file(verifier) != expected_verifier_sha256:
            raise RuntimeError("OS-managed signature verifier changed during signing")
        return signature_path, _sha256_file(signature_path)
    finally:
        try:
            payload_path.unlink()
        except OSError:
            pass


def execute(args: argparse.Namespace) -> int:
    if os.environ.get("HARNESS_TRUSTED_HOST") != "1":
        raise RuntimeError("trusted-host publication requires HARNESS_TRUSTED_HOST=1")
    root = _root(Path.cwd())
    request_path = args.request.resolve(strict=False)
    request = _load_request(request_path, root)
    if args.attempt.resolve(strict=False) != Path(request["attempt_path"]).resolve(strict=False):
        raise RuntimeError("--attempt does not match the immutable request")
    if args.evidence_out.resolve(strict=False) != Path(
        request["execution_evidence_path"]
    ).resolve(strict=False):
        raise RuntimeError("--evidence-out does not match the immutable request")
    attempt = _load_attempt(request, root)
    authority = verify_archive_candidate(
        root,
        archive_path=root / request["archive_path"],
        candidate_a=request["candidate_a"],
    )
    _request_matches_authority(request, authority)
    issuer = _validate_one_line_issuer(args.trusted_host_issuer)
    evidence_path = args.evidence_out.resolve(strict=False)
    if evidence_path.exists():
        raise RuntimeError("evidence output already exists; refusing to overwrite")
    signature_path = evidence_path.with_suffix(".sig")
    if signature_path.exists():
        raise RuntimeError("signature output already exists; refusing to overwrite")
    try:
        evidence_path.relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise RuntimeError("evidence output must stay outside the repository")
    signing_key = _validate_signing_key(Path(args.signing_key), root)
    verifier = Path(_discover_os_managed_verifier(root=root)).resolve(strict=True)
    if str(verifier) != str(Path(request["signature_verifier_path"]).resolve(strict=True)):
        raise RuntimeError("OS-managed signature verifier path does not match request")
    if _sha256_file(verifier) != request["signature_verifier_sha256"]:
        raise RuntimeError("OS-managed signature verifier hash does not match request")
    policy = _discover_machine_trust_policy(root=Path.cwd())
    evidence_fd: int | None = None
    signature_fd: int | None = None
    evidence_reserved = False
    signature_reserved = False
    evidence_written = False
    signature_written = False
    private_signature_path = evidence_path.parent / f".publication-private-{secrets.token_hex(8)}.sig"
    try:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_fd, evidence_identity = _reserve_output(evidence_path)
        evidence_reserved = True
        try:
            signature_fd, signature_identity = _reserve_output(signature_path)
            signature_reserved = True
        except Exception:
            try:
                _assert_reserved_output(evidence_path, evidence_fd, evidence_identity)
                evidence_path.unlink()
            except (OSError, RuntimeError):
                pass
            finally:
                os.close(evidence_fd)
                evidence_fd = None
            raise
        if policy.policy_id != request["trust_policy_id"] or policy.allowed_signers_sha256 != request["trust_policy_sha256"] or policy.principal != request["trusted_host_principal"]:
            raise RuntimeError("machine trust policy changed since request creation")
        challenge_payload = json.dumps(
            {
                "protocol": "trusted-host-publication-challenge-v1",
                "request_sha256": request["request_sha256"],
                "attempt_sha256": attempt.get("attempt_sha256") or _digest(attempt),
                "execution_nonce": request["execution_nonce"],
                "principal": policy.principal,
                "namespace": EXECUTION_EVIDENCE_NAMESPACE,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        _challenge_sign_and_verify(
            challenge_payload,
            key=signing_key,
            verifier=verifier,
            verifier_sha256=request["signature_verifier_sha256"],
            signers=policy.allowed_signers_path,
            principal=policy.principal,
            output_dir=evidence_path.parent,
        )
        assert evidence_fd is not None and signature_fd is not None
        _assert_reserved_output(evidence_path, evidence_fd, evidence_identity)
        _assert_reserved_output(signature_path, signature_fd, signature_identity)
        # Re-read the immutable request/attempt and remote state only after the
        # challenge has proven the key/policy/verifier; this is the final
        # pre-side-effect boundary.
        request = _load_request(request_path, root)
        attempt = _load_attempt(request, root)
        authority = verify_archive_candidate(
            root,
            archive_path=root / request["archive_path"],
            candidate_a=request["candidate_a"],
        )
        _request_matches_authority(request, authority)
        url = _pre_push_recheck(root, request, authority)
        push_argv = _execution_argv(request)
        executable_argv = [git_executable(), *push_argv[1:]]
        env = git_environment()
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        env["GIT_CONFIG_GLOBAL"] = os.devnull if os.name != "nt" else "NUL"
        pushed = subprocess.run(executable_argv, cwd=Path.cwd(), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, check=False)
        if pushed.returncode != 0:
            raise RuntimeError(pushed.stderr.strip() or "trusted-host push failed")
        readback = _remote_head(url, request["branch_ref"], cwd=Path.cwd())
        if readback != request["candidate_a"]:
            raise RuntimeError("trusted-host remote readback does not equal candidate A")
        payload = {
            "protocol": EXECUTION_EVIDENCE_PROTOCOL,
            "request_sha256": request["request_sha256"],
            "attempt_sha256": attempt.get("attempt_sha256") or _digest(attempt),
            "execution_nonce": request["execution_nonce"],
            "candidate_a": request["candidate_a"],
            "branch_ref": request["branch_ref"],
            "push_url": url,
            "push_url_sha256": request["push_url_sha256"],
            "remote_pre_push_head": request.get("remote_pre_push_head"),
            "readback_head_sha": readback,
            "push_argv": push_argv,
            "push_argv_sha256": _digest(push_argv),
            "request_reloaded": True,
            "authorization_revalidated": True,
            "endpoint_revalidated": True,
            "config_sanitized": True,
            "dangerous_local_config_rejected": True,
            "trusted_host_issuer": issuer,
            "trusted_host_principal": policy.principal,
            "trust_policy_id": policy.policy_id,
            "authentication_proof": {
                "kind": "ssh-signature",
                "namespace": EXECUTION_EVIDENCE_NAMESPACE,
                "policy_id": policy.policy_id,
                "principal": policy.principal,
                "signature_path": "",
                "signature_sha256": "<detached-signature>",
            },
            "executed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        payload["authentication_proof"]["signature_path"] = str(signature_path)
        _, signature_sha = _sign_payload(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
            signing_key,
            verifier,
            request["signature_verifier_sha256"],
            output_dir=evidence_path.parent,
            signature_path=private_signature_path,
        )
        signature_bytes = private_signature_path.read_bytes()
        _assert_reserved_output(evidence_path, evidence_fd, evidence_identity)
        _assert_reserved_output(signature_path, signature_fd, signature_identity)
        _write_reserved_output(signature_fd, signature_bytes)
        signature_written = True
        try:
            private_signature_path.unlink()
        except OSError:
            pass
        payload["authentication_proof"]["signature_path"] = str(signature_path)
        payload["authentication_proof"]["signature_sha256"] = hashlib.sha256(signature_bytes).hexdigest()
        payload["evidence_sha256"] = _digest(payload)
        evidence_bytes = (json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        _write_reserved_output(evidence_fd, evidence_bytes)
        evidence_written = True
    finally:
        policy.cleanup()
        if signature_reserved and not signature_written and signature_path.exists():
            try:
                _assert_reserved_output(signature_path, signature_fd, signature_identity)
                signature_path.unlink()
            except OSError:
                pass
            except RuntimeError:
                pass
        if evidence_reserved and not evidence_written and evidence_path.exists():
            try:
                _assert_reserved_output(evidence_path, evidence_fd, evidence_identity)
                evidence_path.unlink()
            except OSError:
                pass
            except RuntimeError:
                pass
        try:
            private_signature_path.unlink()
        except OSError:
            pass
        if signature_fd is not None:
            os.close(signature_fd)
        if evidence_fd is not None:
            os.close(evidence_fd)
    print(args.evidence_out)
    return 0


def verify_policy(args: argparse.Namespace) -> int:
    """Read back the machine policy and OS-managed verifier without publishing."""

    root = _root(args.repo_root)
    policy = _discover_machine_trust_policy(root=root)
    try:
        verifier = Path(_discover_os_managed_verifier(root=root)).resolve(strict=True)
        result = {
            "policy_id": policy.policy_id,
            "principal": policy.principal,
            "allowed_signers_sha256": policy.allowed_signers_sha256,
            "signature_verifier_path": str(verifier),
            "signature_verifier_sha256": _sha256_file(verifier),
        }
    finally:
        policy.cleanup()
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    verify_parser = sub.add_parser("verify-policy")
    verify_parser.add_argument("--repo-root", type=Path, required=True)
    execute_parser = sub.add_parser("execute")
    execute_parser.add_argument("--request", type=Path, required=True)
    execute_parser.add_argument("--attempt", type=Path, required=True)
    execute_parser.add_argument("--evidence-out", type=Path, required=True)
    execute_parser.add_argument("--signing-key", type=Path, required=True)
    execute_parser.add_argument("--trusted-host-issuer", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-policy":
            return verify_policy(args)
        return execute(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
