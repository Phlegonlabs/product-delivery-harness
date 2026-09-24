"""Check source identity and trace coverage of Chinese product review copies."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import re
from pathlib import Path


SOURCE = re.compile(r"<!-- review-source: ([^\r\n]+?) sha256:([0-9a-f]{64}) -->")
TRACE = re.compile(r"\b(?:PRD|ARCH|UI|UX|TEST|DS|RA|MR)-[A-Za-z0-9][A-Za-z0-9_-]*\b")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING = re.compile(r"^ {0,3}(#{1,6})(?:\s+|$)")
URL = re.compile(r"https?://[^\s)>]+", re.IGNORECASE)
LONG_HEX = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{40,64}(?![0-9A-Fa-f])")
NUMERIC_LITERAL = re.compile(
    r"(?<![A-Za-z0-9_./:])(?:[$€£¥]\s*)?\d+(?:[.,]\d+)*(?:\s*"
    r"(?:%|milliseconds?|msec|ms|seconds?|sec|s|minutes?|min|hours?|hrs?|h|"
    r"days?|weeks?|months?|years?|px|rem|em|KB|MB|GB|TB))?"
    r"(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


def _table_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if "|" not in stripped:
        return None
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells = re.split(r"(?<!\\)\|", stripped)
    return [cell.strip() for cell in cells]


def _markdown_coverage(text: str) -> tuple[Counter, Counter]:
    """Count Markdown heading levels and table shapes outside fenced code."""
    headings: Counter = Counter()
    tables: Counter = Counter()
    lines = text.splitlines()
    fence: tuple[str, int] | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        marker = FENCE.match(line)
        if fence is not None:
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= fence[1]:
                fence = None
            index += 1
            continue
        if marker:
            fence = (marker.group(1)[0], len(marker.group(1)))
            index += 1
            continue

        heading = HEADING.match(line)
        if heading:
            headings[len(heading.group(1))] += 1
        cells = _table_cells(line)
        separator = _table_cells(lines[index + 1]) if cells and index + 1 < len(lines) else None
        if cells and separator and len(cells) == len(separator) and all(
            re.fullmatch(r":?-{3,}:?", cell) for cell in separator
        ):
            rows = 0
            cursor = index + 2
            while cursor < len(lines):
                row = _table_cells(lines[cursor])
                if row is None or len(row) != len(cells):
                    break
                rows += 1
                cursor += 1
            tables[(len(cells), rows)] += 1
            index = cursor
            continue
        index += 1
    return headings, tables


def _numeric_literals(text: str) -> Counter:
    text = TRACE.sub(" ", text)
    text = URL.sub(" ", text)
    text = LONG_HEX.sub(" ", text)
    return Counter(" ".join(match.group(0).split()) for match in NUMERIC_LITERAL.finditer(text))


def _coverage_errors(source_text: str, review_text: str, review_name: str) -> list[str]:
    source_headings, source_tables = _markdown_coverage(source_text)
    review_headings, review_tables = _markdown_coverage(review_text)
    errors = []

    missing_headings = {level: count - review_headings[level]
                        for level, count in source_headings.items()
                        if count > review_headings[level]}
    if missing_headings:
        details = ", ".join(f"H{level}: {count}" for level, count in sorted(missing_headings.items()))
        errors.append(f"{review_name}: missing heading-level coverage: {details}")

    missing_tables = source_tables - review_tables
    if missing_tables:
        details = ", ".join(f"{count} table(s) with {columns} columns and {rows} data rows"
                             for (columns, rows), count in sorted(missing_tables.items()))
        errors.append(f"{review_name}: missing table-shape coverage: {details}")

    missing_numbers = _numeric_literals(source_text) - _numeric_literals(review_text)
    if missing_numbers:
        details = ", ".join(f"{literal!r} x{count}" for literal, count in sorted(missing_numbers.items()))
        errors.append(f"{review_name}: missing numeric-literal coverage: {details}")
    return errors


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
    else:
        errors.extend(_coverage_errors(source_text, body, review.name))
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
        print("PASS: review source hashes, trace IDs and structural/literal coverage match; semantic review is still required")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
