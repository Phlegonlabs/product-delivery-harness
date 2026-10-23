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

Responsive font expressions are deliberately narrow. The expression form must
start with calc, min, or clamp and use px, rem, em, or cqi. calc supports only
positive multiplication and division. The checker rejects addition and
subtraction instead of evaluating arbitrary CSS math. Unitless or em leading
gives the exact ratio. Absolute leading with a responsive font size fails
closed because its ratio depends on the container width.
"""

from __future__ import annotations

import argparse
import math
import re
import sys

DEFAULT_ROOT_FONT_SIZE = 16.0
# House readability floors, not WCAG AA minimums.
TEXT_MIN_RATIO = 1.5
HEADING_MIN_RATIO = 1.1
KIND_THRESHOLDS = {
    "text": TEXT_MIN_RATIO,
    "heading": HEADING_MIN_RATIO,
}
_MAX_SPEC_LENGTH = 2048
_MAX_EXPRESSION_DEPTH = 16
_MAX_EXPRESSION_TOKENS = 256
_SUPPORTED_FONT_FUNCTIONS = {"calc", "min", "clamp"}
_SUPPORTED_FONT_UNITS = {"px", "rem", "em", "cqi"}
_CSS_NUMBER_RE = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_CSS_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
_CSS_FUNCTION_RE = re.compile(r"\s*(?:calc|min|clamp)\(", re.IGNORECASE)


class TypeScaleError(ValueError):
    """Raised for a malformed step specification or size value."""


def _validate_root_size(root_size: float) -> None:
    if not math.isfinite(root_size) or root_size <= 0:
        raise TypeScaleError("root font size must be a finite number greater than 0")


def _parse_size(
    value: str, label: str, root_size: float = DEFAULT_ROOT_FONT_SIZE
) -> float:
    """Return a size in px. rem and em are read against the root font size."""
    _validate_root_size(root_size)
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
    if not math.isfinite(size):
        raise TypeScaleError(
            f"{label} {value!r} must be a finite number greater than 0"
        )
    if size <= 0:
        raise TypeScaleError(f"{label} {value!r} must be greater than 0")
    scaled_size = size * scale
    if not math.isfinite(scaled_size) or scaled_size <= 0:
        raise TypeScaleError(
            f"scaled {label} {value!r} must be a finite number greater than 0"
        )
    return scaled_size


def _tokenize_css_math(value: str) -> list[tuple[str, float, str]]:
    """Tokenize the bounded math syntax used by the source font sizes."""
    if len(value) > _MAX_SPEC_LENGTH:
        raise TypeScaleError(f"font-size {value!r} exceeds 2048 characters")
    tokens: list[tuple[str, float, str]] = []
    position = 0

    def add_token(token: tuple[str, float, str]) -> None:
        tokens.append(token)
        if len(tokens) > _MAX_EXPRESSION_TOKENS:
            raise TypeScaleError(f"font-size {value!r} exceeds 256 tokens")

    while position < len(value):
        character = value[position]
        if character.isspace():
            position += 1
            continue
        if character in "+-":
            if not (
                position > 0
                and position + 1 < len(value)
                and value[position - 1].isspace()
                and value[position + 1].isspace()
            ):
                raise TypeScaleError(
                    f"font-size {value!r} requires whitespace on both sides of "
                    f"{character!r}"
                )
            add_token(("punct", 0.0, character))
            position += 1
            continue
        if character in "*/(),":
            add_token(("punct", 0.0, character))
            position += 1
            continue

        number_match = _CSS_NUMBER_RE.match(value, position)
        if number_match:
            raw_number = number_match.group(0)
            position = number_match.end()
            unit_match = _CSS_WORD_RE.match(value, position)
            if not unit_match and position < len(value) and value[position] == "%":
                unit = "%"
                position += 1
            elif unit_match:
                unit = unit_match.group(0)
                position = unit_match.end()
            else:
                unit = ""
            if unit and unit.lower() not in _SUPPORTED_FONT_UNITS:
                raise TypeScaleError(
                    f"font-size {value!r} uses unsupported unit {unit!r}"
                )
            try:
                number = float(raw_number)
            except ValueError as exc:
                raise TypeScaleError(
                    f"font-size {value!r} contains an invalid number {raw_number!r}"
                ) from exc
            if not math.isfinite(number) or number <= 0:
                raise TypeScaleError(
                    f"font-size {value!r} contains {raw_number!r}, which must "
                    "be finite and greater than 0"
                )
            add_token(("length" if unit else "number", number, unit.lower()))
            continue

        word_match = _CSS_WORD_RE.match(value, position)
        if word_match:
            word = word_match.group(0)
            position = word_match.end()
            if position >= len(value) or value[position] != "(":
                raise TypeScaleError(
                    f"font-size {value!r} contains unsupported token {word!r}"
                )
            add_token(("function", 0.0, word.lower()))
            add_token(("punct", 0.0, "("))
            position += 1
            continue

        raise TypeScaleError(f"font-size {value!r} contains an unsupported character")
    return tokens


class _CssMathParser:
    """Check bounded positive CSS math syntax and dimensions."""

    def __init__(
        self,
        tokens: list[tuple[str, float, str]],
        source: str,
        root_size: float,
    ):
        self.tokens = tokens
        self.source = source
        self.root_size = root_size
        self.index = 0
        self.depth = 0

    def _error(self, reason: str) -> TypeScaleError:
        return TypeScaleError(f"font-size {self.source!r} is invalid: {reason}")

    def _peek(self) -> tuple[str, float, str] | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def _consume(self) -> tuple[str, float, str]:
        token = self._peek()
        if token is None:
            raise self._error("unexpected end")
        self.index += 1
        return token

    def _enter_group(self) -> None:
        self.depth += 1
        if self.depth > _MAX_EXPRESSION_DEPTH:
            raise self._error("nesting is deeper than 16 levels")

    @staticmethod
    def _check_value(kind: str, number: float, unit: str) -> tuple[str, float, str]:
        if not math.isfinite(number) or number <= 0:
            raise TypeScaleError(
                "computed math values must be finite and greater than 0"
            )
        return (kind, number, unit)

    @staticmethod
    def _multiply(
        left: tuple[str, float, str], right: tuple[str, float, str]
    ) -> tuple[str, float, str]:
        if left[0] == "length" and right[0] == "length":
            raise TypeScaleError("length times length is unsupported")
        kind = "length" if "length" in (left[0], right[0]) else "number"
        unit = left[2] if left[0] == "length" else right[2]
        return _CssMathParser._check_value(kind, left[1] * right[1], unit)

    @staticmethod
    def _divide(
        left: tuple[str, float, str], right: tuple[str, float, str]
    ) -> tuple[str, float, str]:
        if left[0] == "number" and right[0] == "length":
            raise TypeScaleError("number divided by length is unsupported")
        if right[0] == "length":
            if left[0] != "length" or left[2] == "cqi" or right[2] == "cqi":
                raise TypeScaleError("unsupported length division")
            return _CssMathParser._check_value("number", left[1] / right[1], "")
        return _CssMathParser._check_value(left[0], left[1] / right[1], left[2])

    def _expression(self) -> tuple[str, float, str]:
        value = self._term()
        if self._peek() in (("punct", 0.0, "+"), ("punct", 0.0, "-")):
            raise TypeScaleError(
                f"font-size {self.source!r} is unsupported: addition and "
                "subtraction are outside the bounded expression grammar"
            )
        return value

    def _term(self) -> tuple[str, float, str]:
        value = self._unary()
        while True:
            token = self._peek()
            if token not in (("punct", 0.0, "*"), ("punct", 0.0, "/")):
                return value
            operator = self._consume()[2]
            other = self._unary()
            if operator == "*":
                value = self._multiply(value, other)
            else:
                value = self._divide(value, other)
        return value

    def _unary(self) -> tuple[str, float, str]:
        return self._primary()

    def _primary(self) -> tuple[str, float, str]:
        token = self._consume()
        kind, number, item = token
        if kind == "number":
            return ("number", number, "")
        if kind == "length":
            scale = self.root_size if item in ("rem", "em") else 1.0
            return self._check_value("length", number * scale, item)
        if token == ("punct", 0.0, "("):
            self._enter_group()
            value = self._expression()
            if self._consume() != ("punct", 0.0, ")"):
                raise self._error("unclosed parenthesis")
            self.depth -= 1
            return value
        if kind == "function":
            name = item
            if self._consume() != ("punct", 0.0, "("):
                raise self._error(f"function {name!r} is missing arguments")
            self._enter_group()
            arguments = [self._expression()]
            while self._peek() == ("punct", 0.0, ","):
                self._consume()
                arguments.append(self._expression())
            if self._consume() != ("punct", 0.0, ")"):
                raise self._error(f"unclosed function {name!r}")
            self.depth -= 1
            if name == "calc":
                if len(arguments) != 1:
                    raise self._error("calc takes one argument")
                return arguments[0]
            if any(argument[0] != arguments[0][0] for argument in arguments[1:]):
                raise self._error(f"{name} arguments mix numbers and lengths")
            if name == "min" and len(arguments) < 1:
                raise self._error("min takes at least one argument")
            if name == "clamp":
                if len(arguments) != 3:
                    raise self._error("clamp takes exactly three arguments")
            elif name != "min":
                raise self._error(f"unsupported function {name!r}")
            return arguments[0]
        raise self._error(f"unexpected {item!r}")

    def parse(self) -> tuple[str, float, str]:
        value = self._expression()
        if self._peek() is not None:
            token = self._consume()
            raise self._error(f"unexpected {token[2]!r}")
        return value


def _validate_css_font_expression(value: str, root_size: float) -> None:
    _validate_root_size(root_size)
    tokens = _tokenize_css_math(value)
    if not tokens or tokens[0][0] != "function":
        raise TypeScaleError(
            f"font-size {value!r} must start with calc, min, or clamp"
        )
    if tokens[0][2] not in _SUPPORTED_FONT_FUNCTIONS:
        raise TypeScaleError(
            f"font-size {value!r} uses unsupported function {tokens[0][2]!r}"
        )
    result = _CssMathParser(tokens, value, root_size).parse()
    if result[0] != "length":
        raise TypeScaleError(f"font-size {value!r} must resolve to a length")


def line_height_ratio(
    font_size: str, line_height: str, root_size: float = DEFAULT_ROOT_FONT_SIZE
) -> float:
    _validate_root_size(root_size)
    expression_font_size = bool(_CSS_FUNCTION_RE.match(font_size))
    if expression_font_size:
        _validate_css_font_expression(font_size, root_size)
    else:
        size = _parse_size(font_size, "font-size", root_size)
    raw = line_height.strip().lower()
    if raw.endswith("rem") or raw.endswith("px"):
        if expression_font_size:
            raise TypeScaleError(
                f"line-height {line_height!r} with responsive font-size "
                f"{font_size!r} is unsupported; use a unitless or em line-height"
            )
        assert size is not None
        height = _parse_size(line_height, "line-height", root_size)
        ratio = height / size
        if not math.isfinite(ratio) or ratio <= 0:
            raise TypeScaleError(
                f"line-height ratio for {font_size!r} and {line_height!r} "
                "must be finite and greater than 0"
            )
        return ratio
    if raw.endswith("em"):
        # An em line-height is relative to the element's own font size.
        return _parse_size(line_height, "line-height", 1.0)
    try:
        ratio = float(raw)
    except ValueError as exc:
        raise TypeScaleError(f"line-height {line_height!r} is not a number") from exc
    if not math.isfinite(ratio):
        raise TypeScaleError(
            f"line-height {line_height!r} must be a finite number greater than 0"
        )
    if ratio <= 0:
        raise TypeScaleError(f"line-height {line_height!r} must be greater than 0")
    return ratio


def parse_step_spec(spec: str) -> tuple[str, str, str, str]:
    if len(spec) > _MAX_SPEC_LENGTH:
        raise TypeScaleError(f"{spec!r} exceeds 2048 characters")
    parts = []
    field_start = 0
    depth = 0
    for index, character in enumerate(spec):
        if character == "(":
            depth += 1
            if depth > _MAX_EXPRESSION_DEPTH:
                raise TypeScaleError(f"{spec!r} nests more than 16 levels")
        elif character == ")":
            depth -= 1
            if depth < 0:
                raise TypeScaleError(f"{spec!r} has an unmatched closing parenthesis")
        elif character == "," and depth == 0:
            parts.append(spec[field_start:index].strip())
            field_start = index + 1
    if depth != 0:
        raise TypeScaleError(f"{spec!r} has an unclosed parenthesis")
    parts.append(spec[field_start:].strip())
    if len(parts) not in (3, 4):
        raise TypeScaleError(
            f"{spec!r} must be 'role,font-size,line-height' or "
            "'role,font-size,line-height,kind'"
        )
    role, font_size, line_height = parts[0], parts[1], parts[2]
    if not role:
        raise TypeScaleError(f"{spec!r} is missing a role name")
    if not font_size or not line_height or (len(parts) == 4 and not parts[3]):
        raise TypeScaleError(f"{spec!r} has an empty field")
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
        "a unitless multiplier (1.5), px (24px), rem, or em. A responsive "
        "FONT-SIZE may use bounded calc, min, or clamp with px, rem, em, and "
        "cqi; calc supports only positive multiplication and division. With "
        "responsive font-size, LINE-HEIGHT must be unitless or em. KIND is "
        "'text' (default, house readability floor 1.5) or 'heading' (house "
        "readability floor 1.1). Repeat --step for multiple roles in one run.",
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
