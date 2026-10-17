#!/usr/bin/env python3
"""Compute real WCAG 2.2 contrast ratios for color pairs used in design-system.md.

Implements the standard relative-luminance and contrast-ratio formulas
(https://www.w3.org/TR/WCAG22/#contrast-minimum) so a design-system.md's Color
Palette table can record an actual computed ratio instead of a guess. Every
pair is checked against the AA threshold for its stated size category:
normal text requires 4.5:1, large text or a UI component boundary requires
3:1. A foreground with alpha (#RGBA or #RRGGBBAA) is composited over the
opaque background first. This tool only computes and reports; it never edits
a file.
"""

from __future__ import annotations

import argparse
import re
import sys

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})$")
AA_NORMAL_THRESHOLD = 4.5
AA_LARGE_THRESHOLD = 3.0
SIZE_THRESHOLDS = {
    "normal": AA_NORMAL_THRESHOLD,
    "large": AA_LARGE_THRESHOLD,
    "ui": AA_LARGE_THRESHOLD,
}


class ColorContrastError(ValueError):
    """Raised for a malformed color value or pair specification."""


def parse_hex_rgba(value: str) -> tuple[int, int, int, float]:
    """Return 8-bit channels plus alpha in 0..1 (1.0 when no alpha is given)."""
    match = HEX_RE.match(value.strip())
    if not match:
        raise ColorContrastError(
            f"{value!r} is not a hex color; use #RGB, #RGBA, #RRGGBB, or #RRGGBBAA"
        )
    hex_digits = match.group(1)
    if len(hex_digits) in (3, 4):
        hex_digits = "".join(ch * 2 for ch in hex_digits)
    r = int(hex_digits[0:2], 16)
    g = int(hex_digits[2:4], 16)
    b = int(hex_digits[4:6], 16)
    alpha = int(hex_digits[6:8], 16) / 255 if len(hex_digits) == 8 else 1.0
    return r, g, b, alpha


def parse_hex_color(value: str) -> tuple[int, int, int]:
    r, g, b, _alpha = parse_hex_rgba(value)
    return r, g, b


def _linearize_channel(channel_8bit: float) -> float:
    c = channel_8bit / 255.0
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = rgb
    r_lin = _linearize_channel(r)
    g_lin = _linearize_channel(g)
    b_lin = _linearize_channel(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(foreground: str, background: str) -> float:
    *front, alpha = parse_hex_rgba(foreground)
    *back, back_alpha = parse_hex_rgba(background)
    if back_alpha < 1.0:
        raise ColorContrastError(
            f"background {background!r} must be opaque; composite it over its own backdrop first"
        )
    # Composite the foreground over the background the way browsers do.
    blended = tuple(alpha * f + (1 - alpha) * b for f, b in zip(front, back))
    l1 = relative_luminance(blended)
    l2 = relative_luminance(tuple(back))
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def parse_pair_spec(spec: str) -> tuple[str, str, str]:
    parts = [part.strip() for part in spec.split(",")]
    if len(parts) not in (2, 3):
        raise ColorContrastError(
            f"{spec!r} must be 'foreground,background' or 'foreground,background,size'"
        )
    foreground, background = parts[0], parts[1]
    size = parts[2].lower() if len(parts) == 3 else "normal"
    if size not in SIZE_THRESHOLDS:
        raise ColorContrastError(
            f"size {size!r} must be one of: {', '.join(sorted(SIZE_THRESHOLDS))}"
        )
    return foreground, background, size


def check_pairs(specs: list[str]) -> tuple[list[str], bool]:
    lines: list[str] = []
    all_pass = True
    for spec in specs:
        foreground, background, size = parse_pair_spec(spec)
        ratio = contrast_ratio(foreground, background)
        threshold = SIZE_THRESHOLDS[size]
        passed = ratio >= threshold
        all_pass = all_pass and passed
        status = "PASS" if passed else "FAIL"
        lines.append(
            f"{status} {foreground} on {background} ({size}): "
            f"{ratio:.2f}:1, needs {threshold:.1f}:1"
        )
    return lines, all_pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair",
        action="append",
        required=True,
        dest="pairs",
        metavar="FOREGROUND,BACKGROUND[,SIZE]",
        help="One color pair to check, e.g. '#111111,#FFFFFF,normal'. "
        "Colors are #RGB, #RGBA, #RRGGBB, or #RRGGBBAA; a translucent "
        "foreground is composited over the opaque background. "
        "SIZE is 'normal' (default, 4.5:1), 'large', or 'ui' (both 3:1). "
        "Repeat --pair for multiple pairs in one run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        lines, all_pass = check_pairs(args.pairs)
    except ColorContrastError as exc:
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
