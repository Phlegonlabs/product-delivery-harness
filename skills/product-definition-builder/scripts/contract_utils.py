"""Small cross-skill helpers for product identity, release applicability, and approvals.

The three lifecycle checkers deliberately share these rules instead of carrying
slightly different interpretations of the same Product Definition package.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable

from markdown_contract import active_text


def normalize_identity(value: str) -> str:
    """Return the comparison form used for a product identity."""

    value = unicodedata.normalize("NFC", value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value.casefold()


def product_identity(text: str, *, kind: str) -> str:
    """Extract a normalized title identity from a canonical package file."""

    if kind == "prd":
        pattern = r"^#\s+PRD\s*:\s*(.+?)\s*$"
    elif kind == "architecture":
        pattern = r"^#\s+Architecture\s*:\s*(.+?)\s*$"
    elif kind == "stack":
        pattern = r"^#\s+Stack Decisions\s*:\s*(.+?)\s*$"
    else:
        raise ValueError(f"unknown product identity kind: {kind}")
    match = re.search(pattern, active_text(text), re.IGNORECASE | re.MULTILINE)
    return normalize_identity(match.group(1)) if match else ""


def activation_product_identity(text: str) -> str:
    match = re.search(r"^-\s*Product:\s*(.*?)\s*$", active_text(text), re.I | re.M)
    return normalize_identity(match.group(1)) if match else ""


def release_area_requirements(targets: Iterable[object]) -> set[str]:
    """Map every shipped release class to its executable technology areas."""

    areas: set[str] = set()
    for target in targets:
        surface_class = str(getattr(target, "surface_class", "")).casefold()
        if surface_class in {"hosted_web", "browser_extension"}:
            areas.add("frontend")
        elif surface_class in {"ios", "android", "macos", "windows"}:
            areas.add("mobile or desktop")
        elif surface_class in {"hosted_api", "worker", "job", "webhook", "realtime"}:
            areas.add("backend or data")
        elif surface_class == "agent":
            areas.update({"backend or data", "ai or automation"})
        elif surface_class in {"cli", "other_nonpublic"}:
            areas.add("toolchain")
    return areas


def _without_machine_block(text: str, start: str, end: str) -> str:
    cleaned = re.sub(
        rf"(?ms)^\s*{re.escape(start)}\s*\n.*?^\s*{re.escape(end)}\s*\n?",
        "",
        text,
        count=1,
    )
    return active_text(cleaned)


def canonical_stack_bytes(stack_text: str) -> str:
    return _without_machine_block(
        stack_text,
        "<!-- stack-decision-checkpoint:start -->",
        "<!-- stack-decision-checkpoint:end -->",
    ).strip() + "\n"


def canonical_product_bytes(prd_text: str, architecture_text: str, stack_text: str) -> bytes:
    """Canonical approval payload, excluding self-referential approval blocks."""

    prd = _without_machine_block(
        prd_text,
        "<!-- product-definition-approval:start -->",
        "<!-- product-definition-approval:end -->",
    ).strip()
    architecture = active_text(architecture_text).strip()
    stack = canonical_stack_bytes(stack_text).strip()
    payload = {"architecture": architecture, "prd": prd, "stack": stack}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_text(value: str | bytes) -> str:
    payload = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_digest(value: str) -> str | None:
    match = re.fullmatch(r"sha256:([0-9a-f]{64})", value.strip(), re.I)
    return match.group(1).lower() if match else None


def safe_read_text(path: Path) -> tuple[str | None, str | None]:
    """Read UTF-8 text for CLI boundaries without leaking tracebacks."""

    try:
        return path.read_text(encoding="utf-8"), None
    except (OSError, UnicodeError) as exc:
        return None, f"cannot read UTF-8 file {path}: {exc}"


def finalize_approval_digests(
    prd_text: str,
    architecture_text: str,
    stack_text: str,
    *,
    revision: str = "PD-R1",
) -> tuple[str, str, str]:
    """Bind Product/Stack approval fields to the exact candidate bytes.

    Callers must provide the applicable-area and option-map fields before this
    helper runs.  The marker blocks are excluded from both canonical payloads,
    so the resulting fields do not form a self-referential hash.
    """

    zero = "0" * 64
    prd = re.sub(r"^- Package revision:.*$", f"- Package revision: {revision}@sha256:{zero}", prd_text, count=1, flags=re.MULTILINE)
    prd = re.sub(r"^- Package digest:.*$", f"- Package digest: sha256:{zero}", prd, count=1, flags=re.MULTILINE)
    stack = re.sub(r"^- Checkpoint digest:.*$", f"- Checkpoint digest: sha256:{zero}", stack_text, count=1, flags=re.MULTILINE)
    stack_digest = sha256_text(canonical_stack_bytes(stack))
    stack = re.sub(r"^- Checkpoint digest:.*$", f"- Checkpoint digest: sha256:{stack_digest}", stack, count=1, flags=re.MULTILINE)
    package_digest = sha256_text(canonical_product_bytes(prd, architecture_text, stack))
    prd = re.sub(r"^- Package revision:.*$", f"- Package revision: {revision}@sha256:{package_digest}", prd, count=1, flags=re.MULTILINE)
    prd = re.sub(r"^- Package digest:.*$", f"- Package digest: sha256:{package_digest}", prd, count=1, flags=re.MULTILINE)
    return prd, architecture_text, stack
