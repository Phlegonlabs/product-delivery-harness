#!/usr/bin/env python3
"""Advisory scan of direction-study and HiFi pages for default design patterns.

Reads:
- <style> blocks and style attributes of the page. External sheets and styles applied by script are not read.
- Rules inside @media, @supports, @layer and @container. Other at-rules are skipped.
- Colors: hex, rgb()/rgba() and hsl()/hsla() with the hue as a plain number or deg. Named colors and other
  color functions (oklch, lab, color-mix, hue in rad or turn) are not read.
- var(--x) resolves from the same rule and from rules whose subject is :root, html or body, through chains.
- Selectors match by tag, class, id, [attr] and [attr=value], with ancestors up to 64 levels up; matching
  stops after two million element checks.
- Misses are expected. A hit on the reviewer shell or on a neutral page is a bug.
"""

from __future__ import annotations

import argparse
from collections import Counter
import colorsys
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import NamedTuple

SCHEMA = "slop-scan/1"
CLUSTER_AT = 3
READS = __doc__.partition("\n\n")[2].strip()
PATTERNS = {
    "default-sans": "first family of font-family or font is Inter, Roboto, Arial, Helvetica, Open Sans, Poppins, system-ui, -apple-system, Segoe UI or sans-serif, on a rule whose subject is html, body, :root, *, p or h1-h6, or on an inline style of those elements (the font shorthand needs a size such as 16px, 1rem or 100%; size keywords are not read)",
    "purple-gradient": "linear or radial gradient (repeating and prefixed forms too) with a color at hue 225-300 and saturation >= 35%",
    "gradient-text": "background-clip or -webkit-background-clip with text as a layer",
    "glass-blur": "backdrop-filter or -webkit-backdrop-filter with blur(",
    "colored-glow": "box-shadow with blur >= 20px (rem and em count as 16px) and a color at saturation >= 40% and lightness 15-85%",
    "beige-canvas": "plain background (first color; no gradient or image) on html, body or :root at hue 25-60, lightness >= 90% and a faint tint (chroma 3-12%)",
    "uniform-rounded-cards": "border-radius with every corner a length of 12-28px (rem and em count as 16px) together with a box-shadow in the same rule, on three or more distinct selectors with the same corners",
    "equal-feature-tiles": "grid-template-columns: repeat(3, 1fr) or repeat(4, 1fr), also minmax(0, 1fr)",
    "emoji-ui": "emoji (default emoji presentation, or any character followed by U+FE0F) in heading, button, link or list-item text",
    "pill-badge-row": "three or more elements with every border-radius corner at 999px or more, 50rem or 50em or more, or 100vmax or more, not buttons, inputs, selects, textareas, role=button or btn/button classes; percentages such as 50% are not pills",
}
LOWER = {code: code + 32 for code in range(65, 91)}
SHELL_MARKS = ("reviewer", "hifi-reviewer:css", "direction-reviewer:css", "hifi-reviewer:runtime",
               "direction-reviewer:runtime")
SHELL_STYLE = re.compile(r"data-(?:hifi|direction)-reviewer-css")
SHELL_ASIDE = re.compile(r"data-hifi-reviewer-shell")
MAX_DEPTH = 64
MATCH_BUDGET = 2_000_000
VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*))?\)", re.I)
COLOR_RE = re.compile(r"#[0-9a-f]{3,8}\b|(?:rgb|hsl)a?\([^()]*\)", re.I)
GRADIENT_RE = re.compile(r"(?:linear|radial)-gradient\(")
TILES_RE = re.compile(r"repeat\(\s*[34]\s*,\s*(?:minmax\(\s*0(?:px)?\s*,\s*1fr\s*\)|1fr)\s*\)")
DEFAULT_FAMILIES = {"inter", "roboto", "arial", "helvetica", "open sans", "poppins", "system-ui", "-apple-system",
                    "segoe ui", "sans-serif"}
TEXT_NAMES = {"html", "body", "p", "*", ":root", "h1", "h2", "h3", "h4", "h5", "h6"}
CANVAS_NAMES = {"html", "body", ":root"}
TEXT_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "button", "a", "li"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
UNITS = ("px", "rem", "vmax", "em")
UNIT_PX = {"": 1, "px": 1, "rem": 16, "em": 16}
PILL_AT = {"px": 999, "rem": 50, "em": 50, "vmax": 100}
EXPAND = {1: (0, 0, 0, 0), 2: (0, 1, 0, 1), 3: (0, 1, 2, 1), 4: (0, 1, 2, 3)}
# Default emoji presentation, as hex code points; U+1F000-1FAFF is taken whole.
EMOJI_SET = ("231A-231B 23E9-23EC 23F0 23F3 25FD-25FE 2614-2615 2648-2653 267F 2693 26A1 26AA-26AB 26BD-26BE "
             "26C4-26C5 26CE 26D4 26EA 26F2-26F3 26F5 26FA 26FD 2705 270A-270B 2728 274C 274E 2753-2755 2757 "
             "2795-2797 27B0 27BF 2B1B-2B1C 2B50 2B55 1F000-1FAFF")
EMOJI_RE = re.compile("[%s]|.️" % "".join(
    chr(int(lo, 16)) + "-" + chr(int(hi or lo, 16)) for lo, _, hi in (part.partition("-") for part in EMOJI_SET.split())),
    re.S)


def strip_marked(html: str, start: str, end: str) -> str:
    """Remove start..end pairs, ignoring case. An unmatched start removes nothing more."""
    low = html.translate(LOWER)
    parts, position = [], 0
    while True:
        first = low.find(start, position)
        last = low.find(end, first + len(start)) if first >= 0 else -1
        if last < 0:
            return "".join(parts) + html[position:]
        parts.append(html[position:first])
        position = last + len(end)


def strip_tag(html: str, tag: str, marker: re.Pattern) -> str:
    """Remove <tag ...marker...>...</tag> elements, ignoring case, in one pass."""
    low = html.translate(LOWER)
    opening, close = re.compile("<" + tag + r"\b"), "</" + tag + ">"
    parts, position, search, tag_end, marked = [], 0, 0, -1, -2
    while True:
        found = opening.search(low, search)
        if not found:
            break
        start = found.start()
        if tag_end < start:
            tag_end = low.find(">", start)
            if tag_end < 0:
                break
        if marked < start:
            nearest = marker.search(low, start)
            if not nearest:
                break
            marked = nearest.start()
        search = start + 1
        if marked < tag_end:
            end = low.find(close, tag_end)
            if end < 0:
                break
            parts.append(html[position:start])
            position = search = end + len(close)
    return "".join(parts) + html[position:]


def strip_shell(html: str) -> str:
    for name in SHELL_MARKS:
        html = strip_marked(html, "<!-- %s:start -->" % name, "<!-- %s:end -->" % name)
    return strip_tag(strip_tag(html, "style", SHELL_STYLE), "aside", SHELL_ASIDE)


TOKEN_RE = re.compile(r"[{};\"'\\/]")
STRING_END = {'"': re.compile(r'["\\]'), "'": re.compile(r"['\\]")}
GROUP_RE = re.compile(r"@(?:media|supports|layer|container)\b", re.I)


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
            head, bang, tail = value.strip().rpartition("!")
            value = head.rstrip() if bang and tail.strip().lower() == "important" else value.strip()
            name = name.strip()
            rows.append((name if name.startswith("--") else name.lower(), value))
    return rows


def uncomment(css: str, start: int, end: int, comments: list[tuple[int, int]]) -> str:
    """css[start:end] with each comment (all inside the range) replaced by one space."""
    parts, position = [], start
    for first, last in comments:
        parts += [css[position:first], " "]
        position = last
    return "".join(parts) + css[position:end]


def css_rules(css: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Leaf rules as (selector, declarations) in one linear pass; no recursion, stops cleanly on unterminated text."""
    rules: list[tuple[str, list[tuple[str, str]]]] = []
    comments: list[tuple[int, int]] = []
    stack: list = []  # "group", "skip", or ("rule", selector, body start, comment count)
    start = mark = position = 0
    while True:
        found = TOKEN_RE.search(css, position)
        if not found:
            return rules
        position, char = found.start(), found.group()
        top = stack[-1] if stack else "group"
        if char == "\\":
            position += 2
        elif char in "\"'":
            position += 1
            while True:
                end = STRING_END[char].search(css, position)
                if not end:
                    return rules
                position = end.end() + (end.group() == "\\")
                if end.group() == char:
                    break
        elif char == "/":
            if css.startswith("/*", position):
                end = css.find("*/", position + 2)
                if end < 0:
                    return rules
                comments.append((position, end + 2))
                position = end + 2
            else:
                position += 1
        elif char == ";":
            position += 1
            if top == "group":
                start, mark = position, len(comments)
        elif char == "{":
            if len(stack) >= MAX_DEPTH:
                raise ValueError("css nesting is deeper than %d levels" % MAX_DEPTH)
            prelude = " ".join(uncomment(css, start, position, comments[mark:]).split()) if top == "group" else ""
            position += 1
            if top != "group" or prelude.startswith("@") and not GROUP_RE.match(prelude):
                stack.append("skip")
            elif prelude.startswith("@"):
                stack.append("group")
                start, mark = position, len(comments)
            else:
                stack.append(("rule", prelude, position, len(comments)))
        else:
            if stack:
                closed = stack.pop()
                if isinstance(closed, tuple) and closed[1]:
                    body = uncomment(css, closed[2], position, comments[closed[3]:])
                    rules.append((closed[1], declarations(body)))
            position += 1
            if not stack or stack[-1] == "group":
                start, mark = position, len(comments)


PART_RE = re.compile(r"""(?P<tag>\*|[A-Za-z][\w-]*)|\.(?P<cls>[\w-]+)|\#(?P<id>[\w-]+)"""
                     r"""|\[\s*(?P<attr>[\w-]+)\s*(?:=\s*(?P<val>"[^"]*"|'[^']*'|[^\]\s'"]*)\s*)?\]"""
                     r"""|(?P<colons>::?)(?P<pseudo>[\w-]+)""")
LEGACY_ELEMENTS = {"before", "after", "first-line", "first-letter"}


class Compound(NamedTuple):
    tag: str
    classes: tuple
    ids: tuple
    attrs: tuple
    pseudos: tuple
    element: bool  # has a pseudo-element


def compounds(selector: str) -> list[tuple[str, str]]:
    """Split one selector at combinators outside [] () and quotes into (combinator before, compound)."""
    out, buf, depth, quote, link = [], [], 0, "", " "
    for char in selector.strip() + " ":
        if depth == 0 and not quote and (char.isspace() or char in ">+~"):
            if buf:
                out.append((link, "".join(buf)))
                buf, link = [], " "
            link = char if char in ">+~" else link
            continue
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char in "[(":
            depth += 1
        elif char in "])":
            depth = max(depth - 1, 0)
        buf.append(char)
    return out


def parse_compound(text: str) -> Compound | None:
    tag, classes, ids, attrs, pseudos, element, index = "", [], [], [], [], False, 0
    while index < len(text):
        found = PART_RE.match(text, index)
        if not found or found["tag"] and index:
            return None
        index = found.end()
        if found["tag"]:
            tag = found["tag"].lower()
        elif found["cls"]:
            classes.append(found["cls"])
        elif found["id"]:
            ids.append(found["id"])
        elif found["attr"]:
            value = found["val"]
            attrs.append((found["attr"].lower(), None if value is None else value.strip("\"'")))
        else:
            name = found["pseudo"].lower()
            element = element or found["colons"] == "::" or name in LEGACY_ELEMENTS
            pseudos.append(name)
            if text[index:index + 1] == "(":
                depth = 0
                while index < len(text):
                    depth += {"(": 1, ")": -1}.get(text[index], 0)
                    index += 1
                    if not depth:
                        break
    return Compound(tag, tuple(classes), tuple(ids), tuple(attrs), tuple(pseudos), element)


def parse_selector(part: str) -> list[tuple[str, Compound]]:
    """(combinator before, compound) list, or [] when any compound is not understood."""
    chain = [(link, parse_compound(text)) for link, text in compounds(part)]
    return [] if any(item is None for _, item in chain) else chain


def is_subject(chains: list, names: set[str]) -> bool:
    """True when some comma-separated selector has a subject (last compound) that is one of names."""
    for chain in chains:
        subject = chain[-1][1]
        if not subject.element and (subject.tag in names or ":root" in names and "root" in subject.pseudos):
            return True
    return False


def fits(compound: Compound, element: tuple) -> bool:
    tag, attrs, _ = element
    return (compound.tag in ("", "*", tag) and set(compound.classes) <= set(attrs.get("class", "").split())
            and all(item == attrs.get("id") for item in compound.ids)
            and all(name in attrs and (value is None or attrs[name] == value) for name, value in compound.attrs))


def matches(chain: list, index: int, elements: list) -> bool:
    """Subject matches the element; earlier compounds match ancestors in order (> counts as descendant);
    after + or ~ only the subject is checked."""
    if chain[-1][1].element or not fits(chain[-1][1], elements[index]):
        return False
    node, link = elements[index][2], chain[-1][0]
    for before, compound in reversed(chain[:-1]):
        if link in "+~":
            break
        steps = 0
        while node is not None and steps < MAX_DEPTH and not fits(compound, elements[node]):
            node, steps = elements[node][2], steps + 1
        if node is None or steps >= MAX_DEPTH:
            return False
        node, link = elements[node][2], before
    return True


class Page(HTMLParser):
    """Collects style text, inline styles, elements (tag, attributes, parent index) and emoji text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.styles: list[list[str]] = []
        self.elements: list[tuple[str, dict[str, str], int | None]] = []
        self.emoji: list[str] = []
        self._stack: list[tuple[str, int]] = []
        self._open: Counter = Counter()

    def handle_starttag(self, tag, attrs):
        parent = self._stack[-1][1] if self._stack else None
        self.elements.append((tag, {key: value or "" for key, value in attrs}, parent))
        if tag not in VOID:
            self._stack.append((tag, len(self.elements) - 1))
            self._open[tag] += 1
        if tag == "style":
            self.styles.append([])

    def handle_endtag(self, tag):
        while self._open[tag]:
            name, _ = self._stack.pop()
            self._open[name] -= 1
            if name == tag:
                break

    def handle_data(self, data):
        if self._stack and self._stack[-1][0] == "style":
            self.styles[-1].append(data)
        elif not self._open["script"] and any(self._open[tag] for tag in TEXT_TAGS) and EMOJI_RE.search(data):
            self.emoji.append(" ".join(data.split())[:40])


def number(text: str) -> float | None:
    body = text[1:] if text[:1] in ("+", "-") else text
    return float(text) if body.replace(".", "", 1).isdigit() and body.isascii() else None


def length(token: str) -> tuple[float, str] | None:
    """(number, unit) for 16px, 1rem, 100vmax or a bare number (unit ''), else None."""
    unit = next((item for item in UNITS if token.endswith(item)), "")
    value = number(token[:len(token) - len(unit)])
    return None if value is None else (value, unit)


def resolve(value: str, own: dict[str, str], root: dict[str, str]) -> str:
    """Replace var() from the rule's own properties, then the root ones, then its fallback; at most 8 passes."""
    for _ in range(8):
        new = VAR_RE.sub(lambda m: own.get(m.group(1), root.get(m.group(1), m.group(2) or "")), value)
        if new == value or len(new) > 100_000:
            break
        value = new
    return value


def hsl(token: str) -> tuple[float, float, float] | None:
    """Hue in degrees, saturation and lightness in percent, or None when the token is not a plain color."""
    if token.startswith("#"):
        digits = token[1:]
        if len(digits) in (3, 4):
            digits = "".join(c * 2 for c in digits[:3])
        elif len(digits) in (6, 8):
            digits = digits[:6]
        else:
            return None
        red, green, blue = (int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))
    else:
        name, _, args = token.partition("(")
        parts = [part for part in re.split(r"[\s,]+", args.rstrip(")").partition("/")[0]) if part][:3]
        if len(parts) < 3:
            return None
        if name.lower().startswith("hsl"):
            hue = parts[0][:-3] if parts[0].lower().endswith("deg") else parts[0]
            values = [number(hue)] + [number(part.rstrip("%")) for part in parts[1:]]
            if None in values:
                return None
            red, green, blue = colorsys.hls_to_rgb(values[0] % 360 / 360, values[2] / 100, values[1] / 100)
        else:
            values = [number(part.rstrip("%")) for part in parts]
            if None in values:
                return None
            red, green, blue = (min(max(v / (100 if part.endswith("%") else 255), 0), 1)
                                for v, part in zip(values, parts))
    hue, light, sat = colorsys.rgb_to_hls(red, green, blue)
    return hue * 360, sat * 100, light * 100


def colors(value: str) -> list[tuple[float, float, float]]:
    return [found for found in map(hsl, COLOR_RE.findall(value)) if found]


def blur_px(shadow: str) -> float:
    lengths = [found for found in map(length, COLOR_RE.sub(" ", shadow).split()) if found]
    return lengths[2][0] * UNIT_PX.get(lengths[2][1], 0) if len(lengths) >= 3 else 0


def radius(value: str) -> list[tuple[float, str]] | None:
    """The eight corners (4 horizontal, then 4 vertical) of a border-radius value, or None unless every
    component is a length with px, rem, em or vmax."""
    halves = value.split("/")
    corners = []
    if len(halves) > 2:
        return None
    for half in halves:
        tokens = half.split()
        parsed = [length(token) for token in tokens]
        if not 1 <= len(tokens) <= 4 or any(item is None or not item[1] for item in parsed):
            return None
        corners.append([parsed[i] for i in EXPAND[len(tokens)]])
    return corners[0] + corners[-1]


def font_family(value: str) -> str:
    """Family list after the size and optional /line-height of a font shorthand, or ''."""
    tokens = value.split() if len(value) <= 500 else []
    for index, token in enumerate(tokens):
        size, slash, height = token.partition("/")
        unit = next((item for item in ("px", "rem", "em", "pt", "%") if size.endswith(item)), None)
        if unit and number(size[:-len(unit)]) is not None:
            rest = tokens[index + 1:]
            if slash and not height:
                rest = rest[1:]
            elif not slash and rest[:1] and rest[0].startswith("/"):
                rest = rest[1:] if len(rest[0]) > 1 else rest[2:]
            return " ".join(rest)
    return ""


def first_family(name: str, value: str) -> str:
    if name == "font":
        value = font_family(value)
    return re.sub(r"[\"']", "", (split_top(value, ",") or [""])[0]).strip().lower()


def exempt(tag: str, attrs: dict[str, str]) -> bool:
    classes = attrs.get("class", "").lower()
    return (tag in {"button", "input", "select", "textarea"} or attrs.get("role") == "button"
            or "btn" in classes or "button" in classes)


def scan_html(html: str, allow: set[str]) -> dict:
    page = Page()
    page.feed(strip_shell(html))
    # (selector, declarations, element index for an inline style or None, parsed selector parts)
    rules = []
    for css in page.styles:
        for selector, block in css_rules("".join(css)):
            chains = [chain for chain in map(parse_selector, split_top(selector, ",")) if chain]
            rules.append((selector, block, None, chains))
    rules += [("<%s style>" % tag, declarations(attrs["style"]), index, [])
              for index, (tag, attrs, _) in enumerate(page.elements) if attrs.get("style")]
    root: dict[str, str] = {}
    for _, block, inline, chains in rules:
        if inline is None and is_subject(chains, CANVAS_NAMES):
            root.update((name, value) for name, value in block if name.startswith("--"))
    hits: dict[str, dict] = {}

    def hit(pattern: str, evidence: str) -> None:
        row = hits.setdefault(pattern, {"id": pattern, "count": 0, "evidence": [], "allowed": pattern in allow})
        row["count"] += 1
        evidence = " ".join(evidence.split())[:90]
        if evidence not in row["evidence"] and len(row["evidence"]) < 3:
            row["evidence"].append(evidence)

    radius_groups: dict[tuple, dict[str, str]] = {}
    budget = MATCH_BUDGET  # element checks left for selector matching
    pills: dict[int, str] = {}
    for selector, block, inline, chains in rules:
        own = {name: value for name, value in block if name.startswith("--")}
        values = {name: resolve(value, own, root) for name, value in block if not name.startswith("--")}
        own_tag = page.elements[inline][0] if inline is not None else ""
        for name, value in values.items():
            label = "%s { %s: %s }" % (selector, name, value)
            low = value.lower()
            if name in ("font-family", "font") and (
                    own_tag in TEXT_NAMES or inline is None and is_subject(chains, TEXT_NAMES)):
                if first_family(name, low) in DEFAULT_FAMILIES:
                    hit("default-sans", label)
            if GRADIENT_RE.search(low) and any(225 <= hue <= 300 and sat >= 35 for hue, sat, _ in colors(value)):
                hit("purple-gradient", label)
            if name in ("background-clip", "-webkit-background-clip") and re.search(r"\btext\b", low):
                hit("gradient-text", label)
            if name in ("backdrop-filter", "-webkit-backdrop-filter") and "blur(" in low:
                hit("glass-blur", label)
            if name == "box-shadow" and any(
                    blur_px(shadow) >= 20 and any(sat >= 40 and 15 <= light <= 85 for _, sat, light in colors(shadow))
                    for shadow in split_top(low, ",")):
                hit("colored-glow", label)
            if name in ("background", "background-color") and "gradient" not in low and "url(" not in low and (
                    own_tag in {"html", "body"} or inline is None and is_subject(chains, CANVAS_NAMES)):
                found = colors(value)[:1]
                if found and 25 <= found[0][0] <= 60 and found[0][2] >= 90 and (
                        3 <= found[0][1] * (100 - abs(2 * found[0][2] - 100)) / 100 <= 12):
                    hit("beige-canvas", label)
            if name == "grid-template-columns" and TILES_RE.search(low):
                hit("equal-feature-tiles", label)
            corners = radius(low) if name == "border-radius" else None
            if corners and all(size >= PILL_AT.get(unit, 0) for size, unit in corners):
                targets = [inline] if inline is not None else range(len(page.elements) if budget > 0 else 0)
                budget -= len(targets) * sum(map(len, chains))
                for index in targets:
                    tag, attrs, _ = page.elements[index]
                    if (inline is not None or any(matches(chain, index, page.elements) for chain in chains))                             and not exempt(tag, attrs):
                        pills[index] = label
            if corners and inline is None and all(unit in UNIT_PX and 12 <= size * UNIT_PX[unit] <= 28
                                                  for size, unit in corners) and (
                    values.get("box-shadow", "none").lower() != "none"):
                key = tuple(size * UNIT_PX[unit] for size, unit in corners)
                radius_groups.setdefault(key, {}).update((part, value) for part in split_top(selector, ","))
    for group in radius_groups.values():
        if len(group) >= 3:
            for part, value in sorted(group.items()):
                hit("uniform-rounded-cards", "%s { border-radius: %s; box-shadow }" % (part, value))
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
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--page", action="append", default=[], help="HTML file inside the root; repeatable")
    parser.add_argument("--allow", nargs="+", action="extend", default=[], metavar="PATTERN",
                        help="pattern id the selected direction calls for; still listed, not counted")
    parser.add_argument("--out", help="write the JSON report here (inside the root)")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing --out file")
    parser.add_argument("--list", action="store_true", help="list pattern ids and exit")
    options = parser.parse_args(argv)
    if options.list:
        print(READS)
        print()
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
