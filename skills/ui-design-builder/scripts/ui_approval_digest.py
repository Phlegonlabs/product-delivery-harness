"""Canonical digest for approved UI contract bytes."""

from __future__ import annotations

import hashlib
import re

from markdown_contract import active_text


DERIVED_LINKAGE_RE = re.compile(
    r"^\s*(?:Compiled design system pair|Replacement visual contract when(?:_| )not_required):",
    re.IGNORECASE,
)


def canonical_ui_approval_bytes(text: str) -> bytes:
    lines = [line for line in active_text(text).splitlines() if not DERIVED_LINKAGE_RE.match(line)]
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def canonical_ui_approval_sha256(text: str) -> str:
    return hashlib.sha256(canonical_ui_approval_bytes(text)).hexdigest()
