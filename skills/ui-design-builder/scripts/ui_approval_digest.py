"""Canonical digest for approved UI contract bytes."""

from __future__ import annotations

import hashlib
import re
import argparse
from pathlib import Path
import sys

PRODUCT_SCRIPTS = Path(__file__).resolve().parents[2] / "product-definition-builder" / "scripts"
if str(PRODUCT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PRODUCT_SCRIPTS))

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ui_design", type=Path)
    args = parser.parse_args()
    try:
        print(canonical_ui_approval_sha256(args.ui_design.read_text(encoding="utf-8")))
    except (OSError, UnicodeError) as exc:
        parser.exit(2, f"Cannot read UI contract: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
