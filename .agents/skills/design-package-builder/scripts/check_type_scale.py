#!/usr/bin/env python3
"""Check WCAG 2.2 line-height ratios for a design system's type scale.

Implements the line-height portion of Success Criterion 1.4.12 Text Spacing
(https://www.w3.org/TR/WCAG22/#text-spacing): a block of text needs a line
height (line spacing) of at least 1.5 times its font size. That SC targets
blocks of text, not isolated headings, so this tool applies the 1.5 minimum
only to the "text" kind; the "heading" kind instead uses a lower general
readability floor (1.1) to catch a line-height tight enough to clip
ascenders and descenders. This tool only computes and reports; it never
edits a file.
"""

from __future__ import annotations

import argparse

TEXT_MIN_RATIO = 1.5
HEADING_MIN_RATIO = 1.1
KIND_THRESHOLDS = {
    "text": TEXT_MIN_RATIO,
    "heading": HEADING_MIN_RATIO,
}


class TypeScaleError(ValueError):
    """Raised for a malformed step specification or size value."""


def _parse_size(value: str, label: str) -> float:
    raw = value.strip()
    if raw.lower().endswith("px"):
        raw = raw[:-2].strip()
    try:
        size = float(raw)
    except ValueError as exc:
        raise TypeScaleError(f"{label} {value!r} is not a number") from exc
    if size <= 0:
        raise TypeScaleError(f"{label} {value!r} must be greater than 0")
    return size


def line_height_ratio(font_size: str, line_height: str) -> float:
    size = _parse_size(font_size, "font-size")
    raw = line_height.strip()
    if raw.lower().endswith("px"):
        height = _parse_size(line_height, "line-height")
        return height / size
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


def check_steps(specs: list[str]) -> tuple[list[str], bool]:
    lines: list[str] = []
    all_pass = True
    for spec in specs:
        role, font_size, line_height, kind = parse_step_spec(spec)
        ratio = line_height_ratio(font_size, line_height)
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
        "LINE-HEIGHT may be a unitless multiplier (1.5) or a px value (24px). "
        "KIND is 'text' (default, WCAG 1.4.12 minimum 1.5) or 'heading' "
        "(readability floor 1.1). Repeat --step for multiple roles in one run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        lines, all_pass = check_steps(args.steps)
    except TypeScaleError as exc:
        print(str(exc))
        return 2
    for line in lines:
        print(line)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
