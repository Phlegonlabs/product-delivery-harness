#!/usr/bin/env python3
"""Advisory scan of direction-study and HiFi pages for default design patterns.

Reads:
- Style blocks and style attributes of the page. External sheets and styles applied by script are not read.
- Rules inside @media, @supports, @layer and @container. Other at-rules are skipped.
- Colors: hex, rgb()/rgba() and hsl()/hsla() with the hue as a plain number or deg. Named colors and other
  color functions (oklch, lab, color-mix, hue in rad or turn) are not read.
- var(--x) is replaced once, from the same rule or from :root, html or body; a value that still contains var() after that is not read.
- A rule belongs to its subject, the last compound of each comma-separated selector (.card in "body .card").
  No selector is matched against elements.
- The reviewer shell is excluded: marked style blocks, marked elements and comment-marked regions. An unclosed
  shell element or an unmatched start marker hides the rest of the page.
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

SCHEMA = "slop-scan/1"
CLUSTER_AT = 3
READS = __doc__.partition("\n\n")[2].strip()
PATTERNS = {
    "default-sans": "first family of font-family or font is Inter, Roboto, Arial, Helvetica, Open Sans, Poppins, system-ui, -apple-system, Segoe UI or sans-serif, on a rule whose subject is html, body, :root, *, p or h1-h6, or on an inline style of html, body, p or h1-h6 (the font shorthand needs a size such as 16px, 1rem or 100%; size keywords are not read)",
    "purple-gradient": "a linear or radial gradient (repeating and prefixed forms too), in any property, with a color in the same layer at hue 225-300 and saturation >= 35%",
    "gradient-text": "background-clip or -webkit-background-clip with text as a layer",
    "glass-blur": "backdrop-filter or -webkit-backdrop-filter with blur(",
    "colored-glow": "box-shadow with blur >= 20px (rem and em count as 16px) and a color at saturation >= 40% and lightness 15-85% in the same shadow",
    "beige-canvas": "plain background (first color; no gradient or image) on a rule whose subject is html, body or :root, or on an inline style of html or body, at hue 25-60, lightness >= 90% and a faint tint (chroma 3-12%)",
    "uniform-rounded-cards": "border-radius with every corner a length of 12-28px (rem and em count as 16px) together with a box-shadow other than none in the same rule, on three or more distinct selectors with the same corners",
    "equal-feature-tiles": "grid-template-columns: repeat(3, 1fr) or repeat(4, 1fr), also minmax(0, 1fr)",
    "emoji-ui": "emoji (a pinned list of default-emoji-presentation characters, or any character followed by U+FE0F) in heading, button, link or list-item text",
}
SHELL_MARKS = {"reviewer", "hifi-reviewer:css", "direction-reviewer:css", "hifi-reviewer:runtime",
               "direction-reviewer:runtime"}
SHELL_CSS = {"data-hifi-reviewer-css", "data-direction-reviewer-css"}
SHELL_ATTRS = {"data-hifi-reviewer-shell", "data-reviewer-shell"}
MAX_DEPTH = 64
VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,[^()]*)?\)", re.I)
COLOR_RE = re.compile(r"#[0-9a-f]{3,8}\b|(?:rgb|hsl)a?\([^()]*\)", re.I)
GRADIENT_RE = re.compile(r"(?:linear|radial)-gradient\(", re.I)
TILES_RE = re.compile(r"repeat\(\s*[34]\s*,\s*(?:minmax\(\s*0(?:px)?\s*,\s*1fr\s*\)|1fr)\s*\)")
SIZE_RE = re.compile(r"(?:^|\s)[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:px|rem|em|pt|%)(?:\s*/\s*\S+)?\s+")
ESCAPE_RE = re.compile(r"[0-9a-fA-F]{1,6}\s?|.", re.S)
TAG_RE = re.compile(r"\*|[a-z][\w-]*")
ROOT_RE = re.compile(r":root(?![\w-])")
PSEUDO_RE = re.compile(r"::|:(?:before|after|first-line|first-letter)(?![\w-])")
DEFAULT_FAMILIES = {"inter", "roboto", "arial", "helvetica", "open sans", "poppins", "system-ui", "-apple-system",
                    "segoe ui", "sans-serif"}
TEXT_NAMES = {"html", "body", "p", "*", ":root", "h1", "h2", "h3", "h4", "h5", "h6"}
CANVAS_NAMES = {"html", "body", ":root"}
TEXT_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "button", "a", "li"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
UNIT_PX = {"": 1, "px": 1, "rem": 16, "em": 16}
EXPAND = {1: (0, 0, 0, 0), 2: (0, 1, 0, 1), 3: (0, 1, 2, 1), 4: (0, 1, 2, 3)}
# Default emoji presentation, as hex code points.
EMOJI_SET = ("231A-231B 23E9-23EC 23F0 23F3 25FD-25FE 2614-2615 2648-2653 267F 2693 26A1 26AA-26AB 26BD-26BE "
             "26C4-26C5 26CE 26D4 26EA 26F2-26F3 26F5 26FA 26FD 2705 270A-270B 2728 274C 274E 2753-2755 2757 "
             "2795-2797 27B0 27BF 2B1B-2B1C 2B50 2B55 "
             "1F004 1F0CF 1F18E 1F191-1F19A 1F1E6-1F1FF 1F201 1F21A 1F22F 1F232-1F236 1F238-1F23A 1F250-1F251 "
             "1F300-1F320 1F32D-1F335 1F337-1F37C 1F37E-1F393 1F3A0-1F3CA 1F3CF-1F3D3 1F3E0-1F3F0 1F3F4 1F3F8-1F43E "
             "1F440 1F442-1F4FC 1F4FF-1F53D 1F54B-1F54E 1F550-1F567 1F57A 1F595-1F596 1F5A4 1F5FB-1F64F 1F680-1F6C5 "
             "1F6CC 1F6D0-1F6D2 1F6D5-1F6D7 1F6EB-1F6EC 1F6F4-1F6FC 1F7E0-1F7EB 1F90C-1F93A 1F93C-1F945 1F947-1F9FF "
             "1FA70-1FA74 1FA78-1FA7C 1FA80-1FA86 1FA90-1FAAC 1FAB0-1FABA 1FAC0-1FAC5 1FAD0-1FAD9 1FAE0-1FAE7 "
             "1FAF0-1FAF6")
EMOJI_RE = re.compile("[%s]|.️" % "".join(
    chr(int(lo, 16)) + "-" + chr(int(hi or lo, 16)) for lo, _, hi in (part.partition("-") for part in EMOJI_SET.split())),
    re.S)
TOKEN_RE = re.compile(r"[{};\"'\\/]")
STRING_END = {'"': re.compile(r'["\\]'), "'": re.compile(r"['\\]")}
GROUP_RE = re.compile(r"@(?:media|supports|layer|container)\b", re.I)


def split_top(text: str, sep: str) -> list[str]:
    """Split on sep outside parentheses and quotes; a backslash skips the next character."""
    parts, depth, quote, start, skip = [], 0, "", 0, False
    for index, char in enumerate(text):
        if skip:
            skip = False
        elif char == "\\":
            skip = True
        elif quote:
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


def last_compound(selector: str) -> str:
    """Plain top-level characters of the last compound: brackets, parentheses and strings are dropped and each
    escape becomes one underscore."""
    buf, depth, quote, index = [], 0, "", 0
    while index < len(selector):
        char = selector[index]
        index += 1
        if char == "\\":
            index = ESCAPE_RE.match(selector, index).end() if index < len(selector) else index
            buf += [] if depth or quote else ["_"]
        elif quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char in "[(":
            depth += 1
        elif char in "])":
            depth = max(depth - 1, 0)
        elif not depth and (char.isspace() or char in ">+~"):
            buf.clear()
        elif not depth:
            buf.append(char)
    return "".join(buf)


def subjects(selector: str) -> set[str]:
    """Names the last compounds of a selector list stand for: the lowercase tag, "*" and ":root". A compound
    with a pseudo-element or a namespace stands for nothing; classes, ids, attributes and pseudo-classes
    do not change it."""
    names = set()
    for part in split_top(selector, ","):
        text = last_compound(part).lower()
        if "|" not in text and not PSEUDO_RE.search(text):
            names |= {match[0] for match in (TAG_RE.match(text), ROOT_RE.search(text)) if match}
    return names


class Page(HTMLParser):
    """Collects style text, inline styles as (tag, style) and emoji text, leaving out the reviewer shell."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.styles: list[list[str]] = []
        self.inline: list[tuple[str, str]] = []
        self.emoji: list[str] = []
        self._stack: list[str] = []
        self._open: Counter = Counter()
        self._hide: int | None = None  # stack depth of the open shell element
        self._marks: set[str] = set()  # comment-marked regions that have started
        self._css: list[str] | None = None  # text of the current style element; None when not collected

    def hidden(self) -> bool:
        return self._hide is not None or bool(self._marks)

    def handle_comment(self, data):
        name, _, kind = data.strip().lower().rpartition(":")
        if name in SHELL_MARKS and kind in ("start", "end"):
            (self._marks.add if kind == "start" else self._marks.discard)(name)

    def handle_starttag(self, tag, attrs):
        names = {key for key, _ in attrs}
        shell = bool(names & SHELL_ATTRS)
        hidden = self.hidden() or shell
        if tag == "style":
            self._css = None if hidden or names & SHELL_CSS else []
            if self._css is not None:
                self.styles.append(self._css)
        if dict(attrs).get("style") and not hidden:
            self.inline.append((tag, dict(attrs)["style"]))
        if tag not in VOID:
            self._stack.append(tag)
            self._open[tag] += 1
            if shell and self._hide is None:
                self._hide = len(self._stack)

    def handle_endtag(self, tag):
        while self._open[tag]:
            name = self._stack.pop()
            self._open[name] -= 1
            if name == tag:
                break
        if self._hide is not None and len(self._stack) < self._hide:
            self._hide = None

    def handle_data(self, data):
        if self.hidden():
            return
        if self._stack and self._stack[-1] == "style":
            if self._css is not None:
                self._css.append(data)
        elif not self._open["script"] and any(self._open[tag] for tag in TEXT_TAGS) and EMOJI_RE.search(data):
            self.emoji.append(" ".join(data.split())[:40])


def number(text: str) -> float | None:
    body = text[1:] if text[:1] in ("+", "-") else text
    ok = len(body) <= 32 and body.replace(".", "", 1).isdigit() and body.isascii()  # long digit runs are not read
    return float(text) if ok else None


def length(token: str) -> tuple[float, str] | None:
    """(number, unit) for 16px, 1rem or a bare number (unit ''), else None."""
    unit = next((item for item in ("px", "rem", "em") if token.endswith(item)), "")
    value = number(token[:len(token) - len(unit)])
    return None if value is None else (value, unit)


def substitute(value: str, own: dict[str, str], root: dict[str, str]) -> str | None:
    """Replace each var(--x) once, from the rule's own properties, else the root ones. None when var( is still
    in the result: unknown name, chain, cycle, or a declared value over 1000 characters."""
    def replace(found):
        text = own.get(found[1], root.get(found[1], found[0]))
        return text if len(text) <= 1000 else found[0]

    value = VAR_RE.sub(replace, value)
    return None if "var(" in value.lower() else value


def hsl(token: str) -> tuple[float, float, float] | None:
    """Hue in degrees, saturation and lightness in percent, or None when the token is not a plain color."""
    if token.startswith("#"):
        digits = token[1:]
        digits = "".join(c * 2 for c in digits[:3]) if len(digits) in (3, 4) else digits[:6] if len(digits) in (6, 8) else ""
        if not digits:
            return None
        red, green, blue = (int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))
    else:
        name, _, args = token.partition("(")
        parts = [part for part in re.split(r"[\s,]+", args.rstrip(")").partition("/")[0]) if part][:3]
        if len(parts) < 3:
            return None
        hue = parts[0][:-3] if parts[0].lower().endswith("deg") else parts[0]
        values = [number(hue if name.lower().startswith("hsl") and not index else part.rstrip("%"))
                  for index, part in enumerate(parts)]
        if None in values:
            return None
        if name.lower().startswith("hsl"):
            if not all(0 <= v <= 100 for v in values[1:]):
                return None  # saturation or lightness out of range: not read
            red, green, blue = colorsys.hls_to_rgb(values[0] % 360 / 360, values[2] / 100, values[1] / 100)
        else:
            red, green, blue = (min(max(v / (100 if part.endswith("%") else 255), 0), 1)
                                for v, part in zip(values, parts))
    hue, light, sat = colorsys.rgb_to_hls(red, green, blue)
    return hue * 360, sat * 100, light * 100


def colors(value: str) -> list[tuple[float, float, float]]:
    found = []
    for token in COLOR_RE.findall(value):
        try:
            found.append(hsl(token))
        except (ValueError, ZeroDivisionError, OverflowError):
            pass  # not a color
    return [color for color in found if color]


def blur_px(shadow: str) -> float:
    lengths = [found for found in map(length, COLOR_RE.sub(" ", shadow).split()) if found]
    return lengths[2][0] * UNIT_PX[lengths[2][1]] if len(lengths) >= 3 else 0


def radius(value: str) -> list[tuple[float, str]] | None:
    """The eight corners (4 horizontal, then 4 vertical) of a border-radius value, or None unless every
    component is a length with px, rem or em."""
    halves = [[length(token) for token in half.split()] for half in value.split("/")]
    if len(halves) > 2 or any(not 1 <= len(half) <= 4 or any(item is None or not item[1] for item in half)
                              for half in halves):
        return None
    corners = [[half[i] for i in EXPAND[len(half)]] for half in halves]
    return corners[0] + corners[-1]


def first_family(name: str, value: str) -> str:
    """First family of a font-family list, or of the list after the size of a font shorthand."""
    if name == "font":
        found = SIZE_RE.search(value)
        value = value[found.end():] if found else ""
    return re.sub(r"[\"']", "", (split_top(value, ",") or [""])[0]).strip().lower()


def purple_gradient(value: str) -> bool:
    return any(GRADIENT_RE.search(layer) and any(225 <= hue <= 300 and sat >= 35 for hue, sat, _ in colors(layer))
               for layer in split_top(value, ","))


def scan_html(html: str, allow: set[str]) -> dict:
    page = Page()
    page.feed(html)
    # (selector, declarations, names its subjects stand for, inline style)
    rules = [(selector, block, subjects(selector), False) for css in page.styles
             for selector, block in css_rules("".join(css))]
    rules += [("<%s style>" % tag, declarations(style), {tag}, True) for tag, style in page.inline]
    root: dict[str, str] = {}
    for _, block, names, inline in rules:
        if not inline and names & CANVAS_NAMES:
            root.update((name, value) for name, value in block if name.startswith("--"))
    hits: dict[str, dict] = {}

    def hit(pattern: str, evidence: str) -> None:
        row = hits.setdefault(pattern, {"id": pattern, "count": 0, "evidence": [], "allowed": pattern in allow})
        row["count"] += 1
        evidence = " ".join(evidence.split())[:90]
        if evidence not in row["evidence"] and len(row["evidence"]) < 3:
            row["evidence"].append(evidence)

    radius_groups: dict[tuple, dict[str, str]] = {}
    for selector, block, names, inline in rules:
        own = {name: value for name, value in block if name.startswith("--")}
        values = {name: substitute(value, own, root) for name, value in block if not name.startswith("--")}
        for name, value in values.items():
            if value is None:
                continue
            label = "%s { %s: %s }" % (selector, name, value)
            low = value.lower()
            if name in ("font-family", "font") and names & TEXT_NAMES and first_family(name, low) in DEFAULT_FAMILIES:
                hit("default-sans", label)
            if "-gradient(" in low and purple_gradient(value):
                hit("purple-gradient", label)
            if name in ("background-clip", "-webkit-background-clip") and "text" in map(str.strip, low.split(",")):
                hit("gradient-text", label)
            if name in ("backdrop-filter", "-webkit-backdrop-filter") and "blur(" in low:
                hit("glass-blur", label)
            if name == "box-shadow" and any(
                    blur_px(shadow) >= 20 and any(sat >= 40 and 15 <= light <= 85 for _, sat, light in colors(shadow))
                    for shadow in split_top(low, ",")):
                hit("colored-glow", label)
            if name in ("background", "background-color") and names & CANVAS_NAMES and (
                    "gradient" not in low and "url(" not in low):
                found = colors(value)[:1]
                if found and 25 <= found[0][0] <= 60 and found[0][2] >= 90 and (
                        3 <= found[0][1] * (100 - abs(2 * found[0][2] - 100)) / 100 <= 12):
                    hit("beige-canvas", label)
            if name == "grid-template-columns" and TILES_RE.search(low):
                hit("equal-feature-tiles", label)
            corners = radius(low) if name == "border-radius" and not inline else None
            if corners and all(12 <= size * UNIT_PX[unit] <= 28 for size, unit in corners) and (
                    (values.get("box-shadow") or "none").lower() != "none"):
                key = tuple(size * UNIT_PX[unit] for size, unit in corners)
                radius_groups.setdefault(key, {}).update((part, value) for part in split_top(selector, ","))
    for group in radius_groups.values():
        if len(group) >= 3:
            for part, value in sorted(group.items()):
                hit("uniform-rounded-cards", "%s { border-radius: %s; box-shadow }" % (part, value))
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
    except Exception as exc:
        parser.exit(2, "slop scan blocked: internal error: " + type(exc).__name__ + "\n")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
