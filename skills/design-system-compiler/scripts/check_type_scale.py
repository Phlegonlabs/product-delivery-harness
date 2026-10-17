#!/usr/bin/env python3
"""Check line-height ratios for a design system's type scale.

The thresholds are this skill's house readability floors, not WCAG AA
requirements. Body text ("text" kind) needs a line height of at least 1.5
times its font size; headings ("heading" kind) need at least 1.1 so that
ascenders and descenders do not clip. WCAG 2.2 SC 1.4.12 Text Spacing only
requires that content survives a user override to 1.5, and the 1.5 authored
spacing in SC 1.4.8 is AAA, so a lower authored value can still conform. Sizes may be px, unitless (px), rem, or em; rem and
em font sizes use the declared root font size (default 16px). This tool only
computes and reports; it never edits a file.
"""

from __future__ import annotations

import argparse
import sys

DEFAULT_ROOT_FONT_SIZE = 16.0
# House readability floors, not WCAG AA minimums.
TEXT_MIN_RATIO = 1.5
HEADING_MIN_RATIO = 1.1
KIND_THRESHOLDS = {
    "text": TEXT_MIN_RATIO,
    "heading": HEADING_MIN_RATIO,
}


class TypeScaleError(ValueError):
    """Raised for a malformed step specification or size value."""


def _parse_size(
    value: str, label: str, root_size: float = DEFAULT_ROOT_FONT_SIZE
) -> float:
    """Return a size in px. rem and em are read against the root font size."""
    raw = value.strip().lower()
    scale = 1.0
    for unit, unit_scale in (("px", 1.0), ("rem", root_size), ("em", root_size)):
        if raw.endswith(unit):
            raw = raw[: -len(unit)].strip()
            scale = unit_scale
            break
    try:
        size = float(raw)
    except ValueError as exc:
        raise TypeScaleError(f"{label} {value!r} is not a number") from exc
    if size <= 0:
        raise TypeScaleError(f"{label} {value!r} must be greater than 0")
    return size * scale


def line_height_ratio(
    font_size: str, line_height: str, root_size: float = DEFAULT_ROOT_FONT_SIZE
) -> float:
    size = _parse_size(font_size, "font-size", root_size)
    raw = line_height.strip().lower()
    if raw.endswith("rem") or raw.endswith("px"):
        height = _parse_size(line_height, "line-height", root_size)
        return height / size
    if raw.endswith("em"):
        # An em line-height is relative to the element's own font size.
        return _parse_size(line_height, "line-height", 1.0)
    try:
        ratio = float(raw)
    except ValueError as exc:
        raise TypeScaleError(f"line-height {line_height!r} is not a number") from exc
    if ratio <= 0:
        raise TypeScaleError(f"line-height {line_height!r} must be greater than 0")
    return ratio


def parse_step_spec(spec: str) -> tuple[str, str, str, str]:
    parts = [part.strip() for part in spec.split(",")]
    if len(parts) not in (3, 4):
        raise TypeScaleError(
            f"{spec!r} must be 'role,font-size,line-height' or "
            "'role,font-size,line-height,kind'"
        )
    role, font_size, line_height = parts[0], parts[1], parts[2]
    if not role:
        raise TypeScaleError(f"{spec!r} is missing a role name")
    kind = parts[3].lower() if len(parts) == 4 else "text"
    if kind not in KIND_THRESHOLDS:
        raise TypeScaleError(
            f"kind {kind!r} must be one of: {', '.join(sorted(KIND_THRESHOLDS))}"
        )
    return role, font_size, line_height, kind


def check_steps(
    specs: list[str], root_size: float = DEFAULT_ROOT_FONT_SIZE
) -> tuple[list[str], bool]:
    lines: list[str] = []
    all_pass = True
    for spec in specs:
        role, font_size, line_height, kind = parse_step_spec(spec)
        ratio = line_height_ratio(font_size, line_height, root_size)
        threshold = KIND_THRESHOLDS[kind]
        passed = ratio >= threshold
        all_pass = all_pass and passed
        status = "PASS" if passed else "FAIL"
        lines.append(
            f"{status} {role} ({kind}): line-height ratio {ratio:.2f}, "
            f"needs >= {threshold:.2f}"
        )
    return lines, all_pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--step",
        action="append",
        required=True,
        dest="steps",
        metavar="ROLE,FONT-SIZE,LINE-HEIGHT[,KIND]",
        help="One type-scale step to check, e.g. 'Body,16px,1.5,text'. "
        "FONT-SIZE may be px, unitless (px), rem, or em. LINE-HEIGHT may be "
        "a unitless multiplier (1.5), px (24px), rem, or em. "
        "KIND is 'text' (default, house readability floor 1.5) or 'heading' "
        "(house readability floor 1.1). Repeat --step for multiple roles in one run.",
    )
    parser.add_argument(
        "--root-font-size",
        default="16px",
        help="Root font size used for rem and em values (default 16px).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        root_size = _parse_size(args.root_font_size, "root font-size", DEFAULT_ROOT_FONT_SIZE)
        lines, all_pass = check_steps(args.steps, root_size)
    except TypeScaleError as exc:
        print(str(exc))
        return 2
    for line in lines:
        print(line)
    return 0 if all_pass else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
