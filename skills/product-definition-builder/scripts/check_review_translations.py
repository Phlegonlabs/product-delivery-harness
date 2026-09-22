"""Check source identity and trace coverage of Chinese product review copies."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


SOURCE = re.compile(r"<!-- review-source: ([^\r\n]+?) sha256:([0-9a-f]{64}) -->")
TRACE = re.compile(r"\b(?:PRD|ARCH|UI|UX|TEST|DS|RA|MR)-[A-Za-z0-9][A-Za-z0-9_-]*\b")


def validate_pair(source: Path, review: Path) -> list[str]:
    """Read only; a passing hash/ID check does not prove translation accuracy."""
    if source.resolve() == review.resolve():
        return ["review copy must be separate from its English source"]
    try:
        source_bytes = source.read_bytes()
        source_text = source_bytes.decode("utf-8-sig")
        review_text = review.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        return [f"cannot read source/review pair: {exc}"]
    markers = list(SOURCE.finditer(review_text))
    if len(markers) != 1 or review_text.count("<!-- review-source:") != 1:
        return [f"{review.name}: requires exactly one review-source marker"]
    marker = markers[0]
    errors = []
    if marker[1] != source.name:
        errors.append(f"{review.name}: source filename does not match {source.name}")
    if marker[2] != hashlib.sha256(source_bytes).hexdigest():
        errors.append(f"{review.name}: stale review; English source SHA-256 changed")
    body = review_text[:marker.start()] + review_text[marker.end():]
    source_ids = set(TRACE.findall(source_text))
    review_ids = set(TRACE.findall(body))
    for label, ids in (("missing", source_ids - review_ids), ("extra", review_ids - source_ids)):
        if ids:
            errors.append(f"{review.name}: {label} trace IDs: {', '.join(sorted(ids))}")
    if not body.strip():
        errors.append(f"{review.name}: review body is empty")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prd", required=True, type=Path)
    parser.add_argument("--architecture", type=Path)
    parser.add_argument("--prd-review", type=Path)
    parser.add_argument("--architecture-review", type=Path)
    options = parser.parse_args()
    if options.architecture_review and not options.architecture:
        parser.error("--architecture-review requires --architecture")
    errors = []
    for source, review in ((options.prd, options.prd_review),
                           (options.architecture, options.architecture_review)):
        if source is None:
            continue
        review = review or source.with_name(f"{source.stem}.zh-TW.md")
        errors.extend(validate_pair(source, review))
    for error in errors:
        print(f"FAIL: {error}")
    if not errors:
        print("PASS: review source hashes and trace IDs match; semantic review is still required")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
