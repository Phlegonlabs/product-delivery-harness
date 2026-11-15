#!/usr/bin/env python3
"""Advisory scan of direction-study and HiFi pages for default design patterns."""

from __future__ import annotations

import argparse
import colorsys
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import sys

SCHEMA = "slop-scan/1"
CLUSTER_AT = 3
PATTERNS = {
    "default-sans": "first font-family is Inter, Roboto, Arial, Helvetica, Open Sans, Poppins, system-ui, -apple-system, Segoe UI or bare sans-serif, set on html, body, :root, *, p or h1-h6 (the font shorthand counts)",
    "purple-gradient": "linear or radial gradient with a color at hue 225-300 and saturation >= 35% (var(--x) is resolved from the page)",
    "gradient-text": "background-clip: text, with or without -webkit-",
    "glass-blur": "backdrop-filter with blur(",
    "colored-glow": "box-shadow with blur >= 20px and a color at saturation >= 40% and lightness 15-85%",
    "beige-canvas": "html, body or :root plain background at hue 25-60, lightness >= 90% and a faint tint (chroma 3-12%)",
    "uniform-rounded-cards": "one border-radius of 12-28px together with a box-shadow in the same rule, on three or more distinct selectors",
    "equal-feature-tiles": "grid-template-columns: repeat(3, 1fr) or repeat(4, 1fr), also minmax(0, 1fr)",
    "emoji-ui": "emoji character in heading, button, link or list-item text",
    "pill-badge-row": "three or more elements with border-radius of 999px or more, 100vmax or 50rem, not buttons, inputs or btn/button classes",
}
SHELL_RE = re.compile(
    r"<!-- (reviewer|hifi-reviewer:css|direction-reviewer:css|hifi-reviewer:runtime|direction-reviewer:runtime):start -->"
    r"[\s\S]*?<!-- \1:end -->")
SHELL_ASIDE_RE = re.compile(r"<aside[^>]*data-hifi-reviewer-shell[^>]*>[\s\S]*?</aside>")
SHELL_STYLE_RE = re.compile(r"<style[^>]*data-(?:hifi|direction)-reviewer-css[^>]*>[\s\S]*?</style>")
VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*))?\)")
COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|(?:rgb|hsl)a?\([^)]*\)|\b(?:%s)\b" % "|".join(
    ("blue", "purple", "violet", "indigo", "magenta", "fuchsia", "rebeccapurple", "blueviolet", "mediumpurple")))
NAMED = {"blue": "#0000ff", "purple": "#800080", "violet": "#ee82ee", "indigo": "#4b0082", "magenta": "#ff00ff",
         "fuchsia": "#ff00ff", "rebeccapurple": "#663399", "blueviolet": "#8a2be2", "mediumpurple": "#9370db"}
NUMBER_RE = re.compile(r"-?\d*\.?\d+")
FAMILY_AFTER_SIZE_RE = re.compile(r"\d(?:px|rem|em|pt|%)(?:/[\d.]+\w*)?\s+(.+)")
DEFAULT_FAMILIES = {"inter", "roboto", "arial", "helvetica", "open sans", "poppins", "system-ui", "-apple-system",
                    "segoe ui", "sans-serif"}
TEXT_SELECTOR_RE = re.compile(r"(?:^|[\s,>+~(])(?:html|body|:root|\*|p|h[1-6])(?![\w-])")
CANVAS_SELECTOR_RE = re.compile(r"(?:^|[\s,>+~(])(?:html|body|:root)(?![\w-])")
TILES_RE = re.compile(r"repeat\(\s*[34]\s*,\s*(?:minmax\(\s*0(?:px)?\s*,\s*1fr\s*\)|1fr)\s*\)")
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2728\u26A1\u2705\u274C\u2B50\u2764\u2B06\u2B07\uFE0F]")
TEXT_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "button", "a", "li"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
COMPOUND_RE = re.compile(r"([a-z][\w-]*)?((?:[.#][\w-]+)*)")


def split_top(text: str, sep: str) -> list[str]:
    """Split on sep outside parentheses and quotes."""
    parts, depth, quote, start = [], 0, "", 0
    for index, char in enumerate(text):
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        elif char == sep and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return [part.strip() for part in parts if part.strip()]


def declarations(block: str) -> list[tuple[str, str]]:
    rows = []
    for item in split_top(block, ";"):
        name, _, value = item.partition(":")
        if value:
            rows.append((name.strip().lower(), re.sub(r"\s*!important\s*$", "", value.strip(), flags=re.I)))
    return rows


def css_rules(css: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Leaf rules as (selector, declarations); @media-like blocks are entered, other at-rules skipped."""
    css = re.sub(r"/\*[\s\S]*?\*/", "", css)
    rules, position = [], 0
    while True:
        open_at = css.find("{", position)
        if open_at < 0:
            return rules
        depth, close_at = 1, open_at + 1
        while close_at < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[close_at], 0)
            close_at += 1
        prelude, body = css[position:open_at].strip(), css[open_at + 1:close_at - 1]
        if prelude.startswith("@"):
            if re.match(r"@(media|supports|layer|container)\b", prelude):
                rules.extend(css_rules(body))
        elif prelude:
            rules.append((" ".join(prelude.split()), declarations(body)))
        position = close_at


class Page(HTMLParser):
    """Collects style text, inline styles, elements and the text of heading, button, link and list-item elements."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.styles: list[str] = []
        self.elements: list[tuple[str, dict[str, str]]] = []
        self.emoji: list[str] = []
        self._stack: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = {key: value or "" for key, value in attrs}
        self.elements.append((tag, attrs))
        if tag not in VOID:
            self._stack.append(tag)
        if tag == "style":
            self.styles.append("")

    def handle_endtag(self, tag):
        if tag in self._stack:
            while self._stack.pop() != tag:
                pass

    def handle_data(self, data):
        if self._stack and self._stack[-1] == "style":
            self.styles[-1] += data
        elif TEXT_TAGS.intersection(self._stack) and "script" not in self._stack:
            for match in EMOJI_RE.finditer(data):
                self.emoji.append(" ".join(data.split())[:40] or match.group())
                break


def resolve(value: str, custom: dict[str, str]) -> str:
    for _ in range(2):
        value = VAR_RE.sub(lambda m: custom.get(m.group(1), m.group(2) or ""), value)
    return value


def hsl(token: str) -> tuple[float, float, float] | None:
    """Hue in degrees, saturation and lightness in percent, or None when the token is not a plain color."""
    token = NAMED.get(token.lower(), token)
    if token.startswith("#"):
        digits = token[1:]
        digits = "".join(c * 2 for c in digits[:3]) if len(digits) in (3, 4) else digits[:6]
        if len(digits) != 6:
            return None
        red, green, blue = (int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))
    else:
        numbers = NUMBER_RE.findall(token.partition("(")[2].partition("/")[0])[:3]
        if len(numbers) < 3:
            return None
        values = [float(n) for n in numbers]
        if token.lower().startswith("hsl"):
            red, green, blue = colorsys.hls_to_rgb(values[0] % 360 / 360, values[2] / 100, values[1] / 100)
        else:
            scale = 100 if "%" in token else 255
            red, green, blue = (min(max(v / scale, 0), 1) for v in values)
    hue, light, sat = colorsys.rgb_to_hls(red, green, blue)
    return hue * 360, sat * 100, light * 100


def colors(value: str) -> list[tuple[float, float, float]]:
    return [found for found in map(hsl, COLOR_RE.findall(value)) if found]


def to_px(number: str, unit: str) -> float:
    return float(number) * (16 if unit in ("rem", "em") else 1)


def pill(value: str) -> bool:
    match = re.match(r"\s*(\d*\.?\d+)(px|rem|em|vmax)", value)
    if not match:
        return False
    number, unit = float(match.group(1)), match.group(2)
    return number >= {"px": 999, "rem": 50, "em": 50, "vmax": 100}[unit]


def matches(selector: str, tag: str, attrs: dict[str, str]) -> bool:
    last = re.split(r"[\s>+~]+", selector.strip())[-1]
    found = COMPOUND_RE.fullmatch(last)
    if not found or not last:
        return False
    wanted_tag, rest = found.groups()
    classes, ids = set(re.findall(r"\.([\w-]+)", rest)), re.findall(r"#([\w-]+)", rest)
    return ((not wanted_tag or wanted_tag == tag) and classes <= set(attrs.get("class", "").split())
            and all(item == attrs.get("id") for item in ids))


def exempt(tag: str, attrs: dict[str, str]) -> bool:
    classes = attrs.get("class", "").lower()
    return (tag in {"button", "input", "select", "textarea"} or attrs.get("role") == "button"
            or "btn" in classes or "button" in classes)


def first_family(name: str, value: str) -> str:
    if name == "font":
        found = FAMILY_AFTER_SIZE_RE.search(value)
        value = found.group(1) if found else ""
    return re.sub(r"[\"']", "", (split_top(value, ",") or [""])[0]).strip().lower()


def blur_px(shadow: str) -> float:
    lengths = re.findall(r"(-?\d*\.?\d+)(px|rem|em)?\b", COLOR_RE.sub("", shadow))
    return to_px(*lengths[2]) if len(lengths) >= 3 else 0


def scan_html(html: str, allow: set[str]) -> dict:
    html = SHELL_STYLE_RE.sub("", SHELL_RE.sub("", html))
    html = SHELL_ASIDE_RE.sub("", html)
    page = Page()
    page.feed(html)
    # (selector, declarations, element index for an inline style or None)
    rules = [(selector, block, None) for css in page.styles for selector, block in css_rules(css)]
    rules += [("<%s style>" % tag, declarations(attrs["style"]), index)
              for index, (tag, attrs) in enumerate(page.elements) if attrs.get("style")]
    custom = {name: value for _, block, _ in rules for name, value in block if name.startswith("--")}
    hits: dict[str, dict] = {}

    def hit(pattern: str, evidence: str) -> None:
        row = hits.setdefault(pattern, {"id": pattern, "count": 0, "evidence": [], "allowed": pattern in allow})
        row["count"] += 1
        evidence = " ".join(evidence.split())[:90]
        if evidence not in row["evidence"] and len(row["evidence"]) < 3:
            row["evidence"].append(evidence)

    radius_groups: dict[str, set[str]] = {}
    pills: dict[int, str] = {}
    for selector, block, inline in rules:
        values = {name: resolve(value, custom) for name, value in block if not name.startswith("--")}
        for name, value in values.items():
            label = "%s { %s: %s }" % (selector, name, value)
            if name in ("font-family", "font") and (
                    inline is not None and page.elements[inline][0] in TEXT_TAGS | {"html", "body", "p"}
                    or inline is None and TEXT_SELECTOR_RE.search(selector)):
                if first_family(name, value) in DEFAULT_FAMILIES:
                    hit("default-sans", label)
            if re.search(r"(linear|radial)-gradient\(", value) and any(
                    225 <= hue <= 300 and sat >= 35 for hue, sat, _ in colors(value)):
                hit("purple-gradient", label)
            if name.endswith("background-clip") and "text" in value:
                hit("gradient-text", label)
            if name.endswith("backdrop-filter") and "blur(" in value:
                hit("glass-blur", label)
            if name == "box-shadow" and any(
                    blur_px(shadow) >= 20 and any(sat >= 40 and 15 <= light <= 85 for _, sat, light in colors(shadow))
                    for shadow in split_top(value, ",")):
                hit("colored-glow", label)
            if name in ("background", "background-color") and "gradient" not in value and "url(" not in value and (
                    inline is not None and page.elements[inline][0] in {"html", "body"}
                    or inline is None and CANVAS_SELECTOR_RE.search(selector)):
                found = colors(value)[:1]
                if found and 25 <= found[0][0] <= 60 and found[0][2] >= 90 and (
                        3 <= found[0][1] * (100 - abs(2 * found[0][2] - 100)) / 100 <= 12):
                    hit("beige-canvas", label)
            if name == "grid-template-columns" and TILES_RE.search(value):
                hit("equal-feature-tiles", label)
            if name == "border-radius" and pill(value):
                for index, (tag, attrs) in enumerate(page.elements):
                    if (index == inline if inline is not None else any(
                            matches(part, tag, attrs) for part in split_top(selector, ","))) and not exempt(tag, attrs):
                        pills[index] = label
        sizes = re.findall(r"(\d*\.?\d+)(px|rem|em)\b", values.get("border-radius", ""))
        if (inline is None and sizes and all(12 <= to_px(*size) <= 28 for size in sizes)
                and values.get("box-shadow", "none") != "none"):
            radius_groups.setdefault(values["border-radius"], set()).update(split_top(selector, ","))
    for radius, selectors in sorted(radius_groups.items()):
        if len(selectors) >= 3:
            for selector in sorted(selectors):
                hit("uniform-rounded-cards", "%s { border-radius: %s; box-shadow }" % (selector, radius))
    if len(pills) >= 3:
        for index in sorted(pills):
            hit("pill-badge-row", pills[index])
    for text in page.emoji:
        hit("emoji-ui", text)
    ordered = [hits[key] for key in sorted(hits)]
    distinct = sum(1 for row in ordered if not row["allowed"])
    return {"hits": ordered, "distinctPatterns": distinct, "cluster": distinct >= CLUSTER_AT}


def safe_page(root: Path, relative: str) -> Path:
    if not relative or "\\" in relative or ":" in relative or PurePosixPath(relative).is_absolute() or any(
            part in {".", ".."} for part in relative.split("/")):
        raise ValueError("path must be repository-relative and stay inside the root: " + relative)
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink() or (path.exists() and getattr(path.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("path must not traverse links or reparse points: " + relative)
    return path


def build_report(root: Path, pages: list[str], allow: list[str]) -> dict:
    unknown = sorted(set(allow) - set(PATTERNS))
    if unknown:
        raise ValueError("unknown pattern id: " + ", ".join(unknown))
    rows = []
    for relative in pages:
        path = safe_page(root, relative)
        if not path.is_file():
            raise ValueError("page is missing: " + relative)
        data = path.read_bytes()
        rows.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest(),
                     **scan_html(data.decode("utf-8", errors="replace"), set(allow))})
    return {"schema": SCHEMA, "allowed": sorted(set(allow)), "pages": rows,
            "clusters": sum(1 for row in rows if row["cluster"])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--page", action="append", default=[], help="HTML file inside the root; repeatable")
    parser.add_argument("--allow", nargs="+", action="extend", default=[], metavar="PATTERN",
                        help="pattern id the selected direction calls for; still listed, not counted")
    parser.add_argument("--out", help="write the JSON report here (inside the root)")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing --out file")
    parser.add_argument("--list", action="store_true", help="list pattern ids and exit")
    options = parser.parse_args(argv)
    if options.list:
        for pattern, description in PATTERNS.items():
            print(pattern + ": " + description)
        return 0
    if options.repo_root is None or not options.page:
        parser.exit(2, "slop scan blocked: --repo-root and at least one --page are required\n")
    try:
        root = options.repo_root.resolve()
        report = json.dumps(build_report(root, options.page, options.allow), indent=2, ensure_ascii=False) + "\n"
        if options.out:
            target = safe_page(root, options.out)
            if target.exists() and not options.overwrite:
                raise ValueError("report already exists; pass --overwrite to replace it: " + options.out)
            target.write_text(report, encoding="utf-8")
        else:
            print(report, end="")
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(2, "slop scan blocked: " + str(exc) + "\n")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
