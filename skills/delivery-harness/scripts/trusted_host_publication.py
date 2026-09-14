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

from harness_git import git_environment, git_executable
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
    url = _pre_push_recheck(root, request, authority)
    policy = _discover_machine_trust_policy(root=Path.cwd())
    try:
        if policy.policy_id != request["trust_policy_id"] or policy.allowed_signers_sha256 != request["trust_policy_sha256"] or policy.principal != request["trusted_host_principal"]:
            raise RuntimeError("machine trust policy changed since request creation")
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
        issuer = args.trusted_host_issuer.strip()
        if not issuer or len(issuer) > 200 or any(character in issuer for character in "\r\n"):
            raise RuntimeError("trusted-host issuer must be one non-empty line")
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
        signature_path = args.evidence_out.parent / f"publication-{secrets.token_hex(8)}.sig"
        payload["authentication_proof"]["signature_path"] = str(signature_path)
        signing_key = Path(args.signing_key).resolve(strict=True)
        try:
            signing_key.relative_to(root)
        except ValueError:
            pass
        else:
            raise RuntimeError("machine signing key must stay outside the repository")
        verifier = Path(request["signature_verifier_path"]).resolve(strict=True)
        signature_path, signature_sha = _sign_payload(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
            signing_key,
            verifier,
            request["signature_verifier_sha256"],
            output_dir=args.evidence_out.parent,
            signature_path=signature_path,
        )
        payload["authentication_proof"]["signature_sha256"] = signature_sha
        payload["evidence_sha256"] = _digest(payload)
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        with args.evidence_out.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2, ensure_ascii=False)
            handle.write("\n")
    finally:
        policy.cleanup()
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
