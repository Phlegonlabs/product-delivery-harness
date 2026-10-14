#!/usr/bin/env python3
"""Read and join one retained Deployment source observation."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any


OBSERVATION_SCHEMA = "deployment-source-observation/1"
OBSERVATION_FIELDS = {
    "schema",
    "target",
    "repository",
    "source_ref",
    "resolved_ref",
    "source_sha",
    "artifact",
    "observed_at",
    "readback",
}
READBACK_FIELDS = {"kind", "request", "status", "output"}
OUTPUT_FIELDS = {"repository", "ref", "sha", "artifact"}
MAX_OBSERVATION_BYTES = 1024 * 1024
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA64_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
REPOSITORY_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)+$"
)
PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]|<[^>]+>|\b(?:tbd|todo|placeholder)\b", re.I)
WINDOWS_DEVICE_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
KNOWN_CREDENTIAL_PATHS = {
    ".env", ".env.local", ".dev.vars", "credentials.json", "credential-store",
    "id_rsa", "id_ed25519", "token.json",
}


class _DuplicateKeyError(ValueError):
    pass


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(value)


def _timestamp(value: str) -> datetime | None:
    if not RFC3339_RE.fullmatch(value):
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _substantive(value: str) -> bool:
    return bool(value.strip()) and PLACEHOLDER_RE.search(value) is None


def _reject_reference(path_text: str) -> str | None:
    if not path_text or path_text.strip() != path_text:
        return "path is empty or has surrounding spacing"
    if "\\" in path_text or ":" in path_text:
        return "path uses a backslash, drive, URL, or alternate stream separator"
    if path_text.startswith("/") or path_text.startswith("//"):
        return "path is absolute or UNC-like"
    raw = path_text.encode("utf-8", errors="surrogatepass")
    if any(code < 32 or code == 127 for code in raw):
        return "path contains a control character"
    pure = PurePosixPath(path_text)
    if pure.is_absolute():
        return "path is absolute"
    for part in pure.parts:
        if part in {"", ".", ".."}:
            return "path contains an empty, current, or parent component"
        if part != part.strip() or part.endswith("."):
            return "path contains a dot-space or trailing-dot component"
        lowered = part.casefold()
        if lowered in WINDOWS_DEVICE_NAMES or lowered in KNOWN_CREDENTIAL_PATHS:
            return "path names a device or known credential path"
    return None


def _is_reparse(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError:
        return False
    if path.is_symlink():
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _safe_regular_bytes(
    repo_root: Path,
    relative_path: str,
    label: str,
) -> tuple[bytes, str, list[str]]:
    path_error = _reject_reference(relative_path)
    if path_error:
        return b"", "", [f"{label}: retained evidence {path_error}"]

    try:
        root = repo_root.resolve()
        if not root.is_dir():
            return b"", "", [f"{label}: repository root is not a directory"]
        candidate = root.joinpath(*pure_parts(relative_path))
        if os.name == "nt":
            relative = candidate.relative_to(root)
            current = root
            for part in relative.parts:
                current = current / part
                if _is_reparse(current):
                    return b"", "", [f"{label}: retained evidence path contains a link or reparse point"]
        else:
            current = root
            for part in pure_parts(relative_path):
                current = current / part
                if current.is_symlink():
                    return b"", "", [f"{label}: retained evidence path contains a symlink"]

        resolved = candidate.resolve()
        resolved.relative_to(root)
        before = os.lstat(resolved)
        if not stat.S_ISREG(before.st_mode):
            return b"", "", [f"{label}: retained evidence is not a regular file"]
        if before.st_size > MAX_OBSERVATION_BYTES:
            return b"", "", [f"{label}: retained evidence exceeds 1 MiB"]

        with resolved.open("rb") as stream:
            content = stream.read(MAX_OBSERVATION_BYTES + 1)
        after = os.lstat(resolved)
        identity_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns")
        if any(getattr(before, field) != getattr(after, field) for field in identity_fields):
            return b"", "", [f"{label}: retained evidence changed while it was read"]
    except (OSError, ValueError):
        return b"", "", [f"{label}: retained evidence cannot be read safely"]

    if len(content) > MAX_OBSERVATION_BYTES:
        return b"", "", [f"{label}: retained evidence exceeds 1 MiB"]
    digest = hashlib.sha256(content).hexdigest()
    return content, digest, []


def pure_parts(relative_path: str) -> tuple[str, ...]:
    return PurePosixPath(relative_path).parts


def _load_json(
    content: bytes,
    label: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        text = content.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, TypeError):
        return None, [f"{label}: retained evidence is not strict UTF-8 JSON"]
    if not isinstance(value, dict):
        return None, [f"{label}: retained observation must be a JSON object"]
    return value, []


def load_retained_observation(
    *,
    repo_root: Path,
    reference: str,
    expected_hash: str,
    expected_repository: str,
    target: str,
    source_ref: str,
    resolved_ref: str,
    source_sha: str,
    artifact: str,
    checked_at: datetime | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Load one bounded retained observation and return it with findings."""

    label = f"target {target}"
    match = re.fullmatch(
        r"file:(?P<path>[^@]+)@sha256:(?P<hash>[0-9a-f]{64})",
        reference,
    )
    if match is None:
        return None, [
            f"{label}: authority evidence must use "
            "file:<relative-path>@sha256:<64 lowercase hex>"
        ]
    if match.group("hash") != expected_hash:
        return None, [f"{label}: authority evidence digest is malformed"]

    content, actual_hash, findings = _safe_regular_bytes(
        repo_root,
        match.group("path"),
        label,
    )
    if findings:
        return None, findings
    if actual_hash != expected_hash:
        return None, [f"{label}: retained evidence hash does not match authority evidence"]

    observation, json_findings = _load_json(content, label)
    findings.extend(json_findings)
    if observation is None:
        return None, findings
    if set(observation) != OBSERVATION_FIELDS:
        findings.append(f"{label}: retained observation fields are not exactly closed")
        return None, findings

    readback = observation["readback"]
    if not isinstance(readback, dict) or set(readback) != READBACK_FIELDS:
        findings.append(f"{label}: retained readback fields are not exactly closed")
        return None, findings

    output_text = readback["output"]
    output: dict[str, Any] | None = None
    if not isinstance(output_text, str):
        findings.append(f"{label}: retained output must be UTF-8 JSON text")
    else:
        try:
            output_value = json.loads(
                output_text,
                object_pairs_hook=_object_pairs,
                parse_constant=_reject_constant,
            )
        except (ValueError, TypeError):
            output_value = None
        if not isinstance(output_value, dict) or set(output_value) != OUTPUT_FIELDS:
            findings.append(f"{label}: retained output fields are not exactly closed")
        else:
            output = output_value

    for field in (
        "schema", "target", "repository", "source_ref", "resolved_ref",
        "source_sha", "artifact", "observed_at",
    ):
        if not isinstance(observation[field], str):
            findings.append(f"{label}: retained observation {field} must be a string")
    if observation["schema"] != OBSERVATION_SCHEMA:
        findings.append(f"{label}: retained observation schema must be {OBSERVATION_SCHEMA}")
    if observation["target"] != target:
        findings.append(f"{label}: retained observation target differs from deployment")
    if not REPOSITORY_RE.fullmatch(observation["repository"]):
        findings.append(f"{label}: retained repository identity is malformed")
    elif observation["repository"] != expected_repository:
        findings.append(f"{label}: retained repository differs from expected context")
    if observation["source_ref"] != source_ref:
        findings.append(f"{label}: retained source ref differs from deployment")
    if observation["resolved_ref"] != resolved_ref:
        findings.append(f"{label}: retained resolved ref differs from expected context")
    if not SHA40_RE.fullmatch(observation["source_sha"]):
        findings.append(f"{label}: retained source SHA must be full lowercase hex")
    elif observation["source_sha"] != source_sha:
        findings.append(f"{label}: retained source SHA differs from deployment")
    if observation["artifact"] != artifact:
        findings.append(f"{label}: retained artifact differs from deployment")

    observed_at = _timestamp(observation["observed_at"])
    if observed_at is None:
        findings.append(f"{label}: retained observation time must be RFC3339 with a timezone")
    elif observed_at > datetime.now(timezone.utc):
        findings.append(f"{label}: retained observation time cannot be in the future")
    elif checked_at is not None and observed_at > checked_at:
        findings.append(f"{label}: retained observation is newer than deployment checked time")

    kind = readback["kind"]
    request = readback["request"]
    status = readback["status"]
    if kind not in {"command", "provider"}:
        findings.append(f"{label}: retained readback kind must be command or provider")
    if not isinstance(request, str) or not _substantive(request):
        findings.append(f"{label}: retained readback request must be substantive")
    if isinstance(status, bool) or not isinstance(status, int):
        findings.append(f"{label}: retained readback status must be an integer")
    elif kind == "command" and status != 0:
        findings.append(f"{label}: retained command readback status must be zero")
    elif kind == "provider" and not 200 <= status <= 299:
        findings.append(f"{label}: retained provider readback status must be HTTP 2xx")

    if output is not None:
        if output["repository"] != observation["repository"]:
            findings.append(f"{label}: retained output repository differs from observation")
        if output["ref"] != observation["resolved_ref"]:
            findings.append(f"{label}: retained output ref differs from observation")
        if output["sha"] != observation["source_sha"]:
            findings.append(f"{label}: retained output SHA differs from observation")
        if output["artifact"] != observation["artifact"]:
            findings.append(f"{label}: retained output artifact differs from observation")

    if findings:
        return None, findings
    return observation, []


if __name__ == "__main__":
    raise SystemExit(2)
