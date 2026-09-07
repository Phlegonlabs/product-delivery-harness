#!/usr/bin/env python3
"""Check source files against a product's design system.

Reads `design-system.json`, the machine-readable half of the design system
`product-definition-builder` publishes, and enforces the source-scannable part of its two
binding rules: nothing outside the declared token sources may invent a raw
color, dimension, or motion value, and no page may style its own controls or
surfaces or inline its own layout.

Rules that need a running browser (viewport overflow, focus visibility) or a
build graph (hydration cost) are not checked here; they stay as
rendered-evidence gates in references/verification-gates.md. This tool only
reports; it never edits a file.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

RULES = (
    "raw-color",
    "raw-dimension",
    "inline-layout-style",
    "page-local-control-style",
    "call-site-motion",
)
ANALYZABLE_SUFFIXES = {".html", ".css", ".tsx", ".jsx", ".ts", ".js", ".astro", ".vue"}
PRIMITIVE_LAYERS = {"layout", "surface", "typography", "control"}

HEX_COLOR = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b")
# color-mix is excluded on purpose: it derives a color from its arguments, and a
# raw argument is already caught by HEX_COLOR or by the functions listed here.
FUNCTION_COLOR = re.compile(r"\b(?:rgb|rgba|hsl|hsla|oklch|lab|lch)\s*\(")
MEDIA_PRELUDE = re.compile(r"@(?:media|container)[^{]*\{")
ARBITRARY_UTILITY = re.compile(r"[-:]\[[^\]]*(?:px|rem|em|%|s|ms)\]")
DIMENSION_DECLARATION = re.compile(
    r"\b(?:gap|row-gap|column-gap|margin|margin-\w+|padding|padding-\w+|width"
    r"|min-width|max-width|height|min-height|max-height|font-size|line-height"
    r"|border-radius|top|right|bottom|left|inset)\s*:\s*[^;{}]*?"
    r"(?<![\w-])\d*\.?\d+(?:px|rem|em)\b"
)
INLINE_STYLE = re.compile(r"""style\s*=\s*(?P<quote>["'])(?P<body>.*?)(?P=quote)""", re.S)
# JSX/Vue write the same thing as an object literal, and .tsx/.jsx/.vue are
# in this checker's own extension list, so the quoted-attribute form alone
# misses inline layout in every React-family codebase.
JSX_INLINE_STYLE = re.compile(r"style\s*=\s*\{\{(?P<body>.*?)\}\}", re.S)
CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
INLINE_LAYOUT_PROPERTY = re.compile(
    r"\b(?:display|position|gap|row-gap|column-gap|margin|margin-\w+|padding"
    r"|padding-\w+|grid|grid-\w+|flex|flex-\w+|width|height)\s*:"
)
CONTROL_SELECTOR = re.compile(
    r"^[^@{}]*(?:\bbutton\b|\[type=[\"']?(?:button|submit)|\.(?:btn|button|card"
    r"|panel|surface|box)\b)[^{}]*\{",
    re.M,
)
MOTION_VALUE = re.compile(
    r"\b(?:transition|transition-duration|transition-delay|animation"
    r"|animation-duration|animation-delay|duration|delay|stiffness|damping)\b"
    r"\s*[:=]\s*[^;,)}\n]*?(?<![\w-])\d*\.?\d+\s*(?:m?s\b|[,;}\n)]|$)"
)
CSS_VAR_REFERENCE = re.compile(r"var\(--")


class UiContractError(ValueError):
    """Raised for an unreadable file or a malformed design system."""


class DesignSystem:
    """The allowlist a page may build from."""

    def __init__(self, data: dict, source: Path) -> None:
        if not isinstance(data, dict):
            raise UiContractError(f"{source}: design system must be a JSON object")
        self.source = source
        self.token_sources = self._string_list(data, "tokenSources")
        self.primitive_sources = self._string_list(data, "primitiveSources")
        self.motion_variants = set(self._string_list(data, "motionVariants"))
        primitives = data.get("primitives", {})
        if not isinstance(primitives, dict):
            raise UiContractError(f"{source}: 'primitives' must be an object")
        self.primitives = primitives
        self._validate_primitives()
        self._validate_responsive_set(data)

    @staticmethod
    def _string_list(data: dict, key: str) -> list[str]:
        value = data.get(key, [])
        if isinstance(value, dict):
            value = list(value)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise UiContractError(f"'{key}' must be a list of strings")
        return value

    def _validate_primitives(self) -> None:
        for name, spec in self.primitives.items():
            if not isinstance(spec, dict):
                raise UiContractError(
                    f"{self.source}: primitive {name!r} must map to an object"
                )
            layer = spec.get("layer")
            if layer not in PRIMITIVE_LAYERS:
                raise UiContractError(
                    f"{self.source}: primitive {name!r} needs a layer of "
                    f"{', '.join(sorted(PRIMITIVE_LAYERS))}"
                )
            declared = spec.get("class")
            if declared is not None and (
                not isinstance(declared, str) or not declared.strip()
            ):
                raise UiContractError(
                    f"{self.source}: primitive {name!r} has a non-string 'class'"
                )

    def _validate_responsive_set(self, data: dict) -> None:
        has_viewports = "viewports" in data
        has_size_classes = "sizeClasses" in data
        viewports = data.get("viewports")
        size_classes = data.get("sizeClasses")
        valid_viewports = (
            isinstance(viewports, list)
            and len(viewports) >= 2
            and all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value > 0
                for value in viewports
            )
            and len(set(viewports)) == len(viewports)
            and all(left < right for left, right in zip(viewports, viewports[1:]))
        )
        valid_sizes = (
            isinstance(size_classes, list)
            and len(size_classes) >= 2
            and all(
                isinstance(value, str) and bool(value.strip())
                for value in size_classes
            )
            and len(set(size_classes)) == len(size_classes)
        )
        if (
            has_viewports == has_size_classes
            or (has_viewports and not valid_viewports)
            or (has_size_classes and not valid_sizes)
        ):
            raise UiContractError(
                f"{self.source}: define exactly one non-empty unique responsive set "
                "with at least two targets: viewports or sizeClasses"
            )


def load_design_system(path: Path) -> DesignSystem:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UiContractError(f"cannot read design system {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UiContractError(f"{path}: design system is not valid JSON ({exc})") from exc
    return DesignSystem(data, path)


class Finding:
    def __init__(self, path: Path, line: int, rule: str, text: str) -> None:
        self.path = path
        self.line = line
        self.rule = rule
        self.text = text.strip()

    def __str__(self) -> str:
        return f"FAIL {self.path}:{self.line} [{self.rule}] {self.text}"


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


TOKEN_BLOCK_START = re.compile(
    r"(?::root\b[^{]*|@media[^{]*prefers-reduced-motion[^{]*)\{", re.I
)


def token_regions(text: str) -> list[tuple[int, int]]:
    """Spans where raw values are allowed even in a page file.

    A self-contained file may inline its own tokens, so the token block is the
    one place a raw value may appear. The global reduced-motion override counts
    too: it is the single place the reduced-motion policy is set.
    """
    regions: list[tuple[int, int]] = []
    for match in TOKEN_BLOCK_START.finditer(text):
        depth = 0
        for index in range(match.end() - 1, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    regions.append((match.start(), index + 1))
                    break
        else:
            regions.append((match.start(), len(text)))
    return regions


def _in_regions(index: int, regions: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in regions)


def media_prelude_regions(text: str) -> list[tuple[int, int]]:
    """Breakpoint values in an @media prelude.

    CSS cannot read a custom property in a media query, so a breakpoint has to
    be written as a literal. The responsive set is fixed by the design system,
    and the viewport gate checks it, so these literals are not drift.
    """
    return [(match.start(), match.end()) for match in MEDIA_PRELUDE.finditer(text)]


def _strip_comments(text: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), text, flags=re.S)
    return re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), without_block, flags=re.S)


def check_file(
    path: Path,
    design_system: DesignSystem,
    is_token_source: bool,
    defines_primitives: bool = False,
) -> list[Finding]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UiContractError(f"cannot read {path}: {exc}") from exc
    text = _strip_comments(raw)
    findings: list[Finding] = []
    allowed = token_regions(text) + media_prelude_regions(text)

    if not is_token_source:
        for match in HEX_COLOR.finditer(text):
            if _in_regions(match.start(), allowed):
                continue
            findings.append(Finding(path, _line_of(text, match.start()), "raw-color", match.group(0)))
        for match in FUNCTION_COLOR.finditer(text):
            if _in_regions(match.start(), allowed):
                continue
            findings.append(Finding(path, _line_of(text, match.start()), "raw-color", match.group(0)))
        for match in DIMENSION_DECLARATION.finditer(text):
            if CSS_VAR_REFERENCE.search(match.group(0)) or _in_regions(match.start(), allowed):
                continue
            findings.append(
                Finding(path, _line_of(text, match.start()), "raw-dimension", match.group(0))
            )
        for match in ARBITRARY_UTILITY.finditer(text):
            findings.append(
                Finding(path, _line_of(text, match.start()), "raw-dimension", match.group(0))
            )
        if not defines_primitives:
            for match in CONTROL_SELECTOR.finditer(text):
                findings.append(
                    Finding(
                        path,
                        _line_of(text, match.start()),
                        "page-local-control-style",
                        match.group(0),
                    )
                )
        for match in MOTION_VALUE.finditer(text):
            if _in_regions(match.start(), allowed):
                continue
            findings.append(
                Finding(path, _line_of(text, match.start()), "call-site-motion", match.group(0))
            )

    for pattern in (INLINE_STYLE, JSX_INLINE_STYLE):
        for match in pattern.finditer(text):
            # camelCase -> kebab-case so `flexDirection` reads as `flex-direction`.
            body = CAMEL_BOUNDARY.sub("-", match.group("body")).lower()
            if INLINE_LAYOUT_PROPERTY.search(body):
                findings.append(
                    Finding(
                        path,
                        _line_of(text, match.start()),
                        "inline-layout-style",
                        match.group(0),
                    )
                )

    return findings


def collect_files(paths: list[str], walk: list[str]) -> list[Path]:
    files = [Path(item) for item in paths]
    for root in walk:
        base = Path(root)
        if not base.is_dir():
            raise UiContractError(f"{base} is not a directory")
        for suffix in ("*.html", "*.css", "*.tsx", "*.jsx", "*.ts", "*.js", "*.astro", "*.vue"):
            files.extend(sorted(base.rglob(suffix)))
    resolved: list[Path] = []
    for file in files:
        if not file.is_file():
            raise UiContractError(f"{file} is not a file")
        if file not in resolved:
            resolved.append(file)
    return resolved


def check_paths(
    design_system: DesignSystem,
    files: list[Path],
    token_sources: list[str],
    primitive_sources: list[str] | None = None,
) -> tuple[list[str], bool]:
    files = [file for file in files if file.suffix.lower() in ANALYZABLE_SUFFIXES]
    if not files:
        raise UiContractError("no analyzable UI source files were provided")
    declared = {Path(item).as_posix() for item in design_system.token_sources}
    declared.update(Path(item).as_posix() for item in token_sources)
    primitives = {Path(item).as_posix() for item in design_system.primitive_sources}
    primitives.update(Path(item).as_posix() for item in (primitive_sources or []))
    lines: list[str] = []
    findings: list[Finding] = []
    for file in files:
        posix = file.as_posix()
        is_token_source = any(posix.endswith(source) for source in declared if source)
        defines_primitives = any(posix.endswith(source) for source in primitives if source)
        file_findings = check_file(file, design_system, is_token_source, defines_primitives)
        findings.extend(file_findings)
        if is_token_source:
            role = "token source"
        elif defines_primitives:
            role = "primitive source"
        else:
            role = "page"
        if not file_findings:
            lines.append(f"PASS {file} ({role})")
    lines.extend(str(finding) for finding in findings)
    lines.append(
        f"{len(findings)} violation(s) across {len(files)} file(s) "
        f"against {design_system.source}"
    )
    return lines, not findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        required=True,
        metavar="DESIGN_SYSTEM.JSON",
        help="Path to the product's design-system.json, the allowlist every "
        "checked file must obey.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="Files to check. Combine with --path to add a directory walk.",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        dest="walk",
        metavar="DIR",
        help="Directory to walk for markup and component files. Repeatable.",
    )
    parser.add_argument(
        "--token-source",
        action="append",
        default=[],
        dest="token_sources",
        metavar="PATH",
        help="Extra token-source path, added to the design system's tokenSources. "
        "Raw color, dimension, and motion values are allowed only in these files.",
    )
    parser.add_argument(
        "--primitive-source",
        action="append",
        default=[],
        dest="primitive_sources",
        metavar="PATH",
        help="Path that defines primitives, added to the design system's "
        "primitiveSources. Defining a control or surface selector is that file's "
        "job, so page-local-control-style is not reported for it.",
    )
    parser.add_argument(
        "--rule",
        action="append",
        default=[],
        dest="rules",
        choices=RULES,
        help="Report only these rules. Repeatable. Default: every rule. A "
        "filtered run reports only the selected rules, so its exit code does not "
        "mean the file is contract-clean.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.files and not args.walk:
        print("give at least one FILE or --path DIR")
        return 2
    try:
        design_system = load_design_system(Path(args.registry))
        files = collect_files(args.files, args.walk)
        lines, all_pass = check_paths(
            design_system, files, args.token_sources, args.primitive_sources
        )
    except UiContractError as exc:
        print(str(exc))
        return 2
    if args.rules:
        selected = set(args.rules)
        lines = [
            line
            for line in lines
            if not line.startswith("FAIL") or any(f"[{rule}]" in line for rule in selected)
        ]
        all_pass = not any(line.startswith("FAIL") for line in lines)
    for line in lines:
        print(line)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
