#!/usr/bin/env python3
"""Check source files against a UI architecture registry.

Implements the source-scanning subset of the guardrails in
references/ui-architecture-guide.md: raw values may only appear in the token
sources, pages may not carry inline layout styles or their own control and
surface styling, class names must exist in the registry, and motion values
must come from registered variants instead of call-site numbers. Sections must
wrap an approved container.

Rules that need a running browser (viewport overflow, focus visibility) or a
build graph (hydration cost) are not checked here; they stay in
visual-acceptance.md as rendered-evidence gates. This tool only reports; it
never edits a file.
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
    "unregistered-class",
    "call-site-motion",
    "section-without-container",
)
ANALYZABLE_SUFFIXES = {".html", ".css", ".tsx", ".jsx", ".ts", ".js", ".astro", ".vue"}

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
CLASS_ATTRIBUTE = re.compile(r"""class(?:Name)?\s*=\s*(?P<quote>["'])(?P<body>[^"']*)(?P=quote)""")
CSS_VAR_REFERENCE = re.compile(r"var\(--")
SECTION_TAG = re.compile(r"<section\b[^>]*>", re.I)


class UiContractError(ValueError):
    """Raised for an unreadable file or a malformed registry."""


class Registry:
    """The allowlist a page may build from."""

    def __init__(self, data: dict, source: Path) -> None:
        if not isinstance(data, dict):
            raise UiContractError(f"{source}: registry must be a JSON object")
        self.source = source
        self.token_sources = self._string_list(data, "tokenSources")
        self.primitive_sources = self._string_list(data, "primitiveSources")
        self.motion_variants = set(self._string_list(data, "motionVariants"))
        primitives = data.get("primitives", {})
        if not isinstance(primitives, dict):
            raise UiContractError(f"{source}: 'primitives' must be an object")
        self.primitives = primitives
        recipes = data.get("recipes", {})
        if not isinstance(recipes, dict):
            raise UiContractError(f"{source}: 'recipes' must be an object")
        self.recipes = recipes
        self._validate_evidence_contract(data)
        self.scaffold_classes = set(self._string_list(data, "reviewScaffoldClasses"))
        self.container_classes = self._container_classes()
        self.known_classes = self._known_classes() | self.scaffold_classes

    @staticmethod
    def _string_list(data: dict, key: str) -> list[str]:
        value = data.get(key, [])
        if isinstance(value, dict):
            value = list(value)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise UiContractError(f"'{key}' must be a list of strings")
        return value

    def _validate_evidence_contract(self, data: dict) -> None:
        has_viewports = "viewports" in data
        has_size_classes = "sizeClasses" in data
        viewports = data.get("viewports")
        size_classes = data.get("sizeClasses")
        valid_viewports = (
            isinstance(viewports, list)
            and bool(viewports)
            and all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value > 0
                for value in viewports
            )
            and len(set(viewports)) == len(viewports)
        )
        valid_sizes = (
            isinstance(size_classes, list)
            and bool(size_classes)
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
                f"{self.source}: define exactly one non-empty unique responsive set: "
                "viewports or sizeClasses"
            )
        for route, recipe in self.recipes.items():
            if (
                not isinstance(route, str)
                or not route.strip()
                or not isinstance(recipe, dict)
            ):
                raise UiContractError(f"{self.source}: every recipe must map a route to an object")
            for key in ("requiredStates",):
                value = recipe.get(key)
                if value is not None and (
                    not isinstance(value, list)
                    or any(
                        not isinstance(item, str) or not item.strip()
                        for item in value
                    )
                ):
                    raise UiContractError(
                        f"{self.source}: recipe {route!r} {key} must be a string list"
                    )
            ui_id = recipe.get("uiId")
            if ui_id is not None and (
                not isinstance(ui_id, str) or not ui_id.strip()
            ):
                raise UiContractError(
                    f"{self.source}: recipe {route!r} uiId must be a non-empty string"
                )

    @staticmethod
    def _slug(name: str) -> str:
        without_brackets = name.strip().strip("<>")
        kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", without_brackets)
        return kebab.lower().replace(" ", "-")

    def _base_class(self, name: str, spec: dict) -> str:
        declared = spec.get("class")
        if declared is not None:
            if not isinstance(declared, str) or not declared.strip():
                raise UiContractError(
                    f"{self.source}: primitive {name!r} has a non-string 'class'"
                )
            return declared.strip()
        return self._slug(name)

    def _variant_axes(self, spec: dict) -> list[tuple[str, list[str]]]:
        axes: list[tuple[str, list[str]]] = []
        for key, value in spec.items():
            if key in ("layer", "class", "rawStylesAllowed", "minTargetPx", "requiresAccessibleName"):
                continue
            if isinstance(value, list):
                axes.append((key, [str(item) for item in value]))
        return axes

    def _container_classes(self) -> set[str]:
        classes: set[str] = set()
        for name, spec in self.primitives.items():
            if not isinstance(spec, dict) or spec.get("layer") != "layout":
                continue
            if "sizes" not in spec:
                continue
            classes.add(self._base_class(name, spec))
        return classes

    def _known_classes(self) -> set[str]:
        classes: set[str] = set()
        for name, spec in self.primitives.items():
            if not isinstance(spec, dict):
                raise UiContractError(
                    f"{self.source}: primitive {name!r} must map to an object"
                )
            base = self._base_class(name, spec)
            classes.add(base)
            for axis, values in self._variant_axes(spec):
                for value in values:
                    slug = self._slug(value)
                    if axis == "gaps":
                        # The gap scale is shared across layout primitives, so it
                        # is one utility class rather than a per-primitive modifier.
                        classes.add(f"gap-{slug}")
                        continue
                    classes.add(f"{base}--{slug}")
                    classes.add(f"{base}-{slug}")
        return classes


def load_registry(path: Path) -> Registry:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UiContractError(f"cannot read registry {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UiContractError(f"{path}: registry is not valid JSON ({exc})") from exc
    return Registry(data, path)


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

    A dependency-free mockup inlines its own tokens, so the token block is the
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
    be written as a literal. The viewport set is fixed by the registry, and the
    viewport gate checks it, so these literals are not drift.
    """
    return [(match.start(), match.end()) for match in MEDIA_PRELUDE.finditer(text)]


def _strip_comments(text: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), text, flags=re.S)
    return re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), without_block, flags=re.S)


def check_file(
    path: Path,
    registry: Registry,
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

    for match in INLINE_STYLE.finditer(text):
        if INLINE_LAYOUT_PROPERTY.search(match.group("body")):
            findings.append(
                Finding(
                    path,
                    _line_of(text, match.start()),
                    "inline-layout-style",
                    match.group(0),
                )
            )

    for match in CLASS_ATTRIBUTE.finditer(text):
        for name in match.group("body").split():
            if name not in registry.known_classes:
                findings.append(
                    Finding(path, _line_of(text, match.start()), "unregistered-class", name)
                )

    for match in SECTION_TAG.finditer(text):
        names = set()
        attribute = CLASS_ATTRIBUTE.search(match.group(0))
        if attribute:
            names = set(attribute.group("body").split())
        if not names & registry.container_classes:
            after = text[match.end() : match.end() + 400]
            nested = CLASS_ATTRIBUTE.search(after)
            nested_names = set(nested.group("body").split()) if nested else set()
            if not nested_names & registry.container_classes:
                findings.append(
                    Finding(
                        path,
                        _line_of(text, match.start()),
                        "section-without-container",
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
    registry: Registry,
    files: list[Path],
    token_sources: list[str],
    primitive_sources: list[str] | None = None,
) -> tuple[list[str], bool]:
    files = [file for file in files if file.suffix.lower() in ANALYZABLE_SUFFIXES]
    if not files:
        raise UiContractError("no analyzable UI source files were provided")
    declared = {Path(item).as_posix() for item in registry.token_sources}
    declared.update(Path(item).as_posix() for item in token_sources)
    primitives = {Path(item).as_posix() for item in registry.primitive_sources}
    primitives.update(Path(item).as_posix() for item in (primitive_sources or []))
    lines: list[str] = []
    findings: list[Finding] = []
    for file in files:
        posix = file.as_posix()
        is_token_source = any(posix.endswith(source) for source in declared if source)
        defines_primitives = any(posix.endswith(source) for source in primitives if source)
        file_findings = check_file(file, registry, is_token_source, defines_primitives)
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
        f"against {registry.source}"
    )
    return lines, not findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        required=True,
        metavar="UI_REGISTRY.JSON",
        help="Path to ui-registry.json, the allowlist every checked file must obey.",
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
        help="Extra token-source path, added to the registry's tokenSources. Raw "
        "color, dimension, and motion values are allowed only in these files.",
    )
    parser.add_argument(
        "--primitive-source",
        action="append",
        default=[],
        dest="primitive_sources",
        metavar="PATH",
        help="Path that defines primitives, added to the registry's "
        "primitiveSources. Defining a control or surface selector is that file's "
        "job, so page-local-control-style is not reported for it. A "
        "dependency-free mockup is both a token source and a primitive source.",
    )
    parser.add_argument(
        "--rule",
        action="append",
        default=[],
        dest="rules",
        choices=RULES,
        help="Report only these rules. Repeatable. Default: every rule.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.files and not args.walk:
        print("give at least one FILE or --path DIR")
        return 2
    try:
        registry = load_registry(Path(args.registry))
        files = collect_files(args.files, args.walk)
        lines, all_pass = check_paths(
            registry, files, args.token_sources, args.primitive_sources
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
