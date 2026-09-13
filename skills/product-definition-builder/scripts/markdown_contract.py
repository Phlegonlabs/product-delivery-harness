#!/usr/bin/env python3
"""Read only active Markdown content for contract validation."""

from __future__ import annotations

import re


ActiveLine = tuple[int, str]

_FENCE_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
_FENCE_CLOSE_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})[ \t]*$")
_HTML_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "body", "caption", "center",
    "colgroup", "dd", "details", "dialog", "dir", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "form", "frameset", "head",
    "header", "html", "iframe", "legend", "li", "main", "menu", "nav",
    "noframes", "ol", "optgroup", "option", "p", "pre", "script", "search",
    "section", "style", "summary", "table", "tbody", "td", "template", "tfoot",
    "th", "thead", "textarea", "title", "tr", "ul",
}
_TYPE1_RE = re.compile(r"^[ ]{0,3}<(script|pre|style|textarea)(?:\s|>|$)", re.I)
_TYPE6_RE = re.compile(
    r"^[ ]{0,3}</?(?:" + "|".join(sorted(_HTML_BLOCK_TAGS)) + r")(?:\s|/?>|$)",
    re.I,
)
_TYPE7_RE = re.compile(
    r"^[ ]{0,3}</?[A-Za-z][A-Za-z0-9-]*(?:\s+[^<>]*)?/?>[ \t]*$"
)


def _html_block_start(line: str, markers: set[str]) -> tuple[str, str | None] | None:
    """Classify CommonMark raw HTML block starts (types 1-7)."""

    if line.strip() in markers:
        return None
    leading = len(line) - len(line.lstrip(" "))
    if leading > 3:
        return None
    stripped = line[leading:]
    type1 = _TYPE1_RE.match(line)
    if type1:
        return "terminator", f"</{type1.group(1).casefold()}>"
    if stripped.startswith("<!--"):
        return "terminator", "-->"
    if stripped.startswith("<?"):
        return "terminator", "?>"
    if re.match(r"<![A-Z]", stripped):
        return "terminator", ">"
    if stripped.startswith("<![CDATA["):
        return "terminator", "]]" + ">"
    if _TYPE6_RE.match(line) or _TYPE7_RE.match(line):
        return "blank", None
    return None


def active_markdown_lines(
    text: str, *, machine_markers: tuple[str, ...] = ()
) -> tuple[ActiveLine, ...]:
    """Return line-numbered Markdown lines outside fences and comments.

    A machine marker must occupy a line by itself. Markers inside code,
    prose, or an outer HTML comment are inactive content, not contracts.
    """

    markers = set(machine_markers)
    active: list[ActiveLine] = []
    fence: tuple[str, int] | None = None
    in_comment = False
    html_block_terminator: str | None = None
    html_block_until_blank = False

    for number, line in enumerate(text.splitlines(), start=1):
        if fence is not None:
            closing = _FENCE_CLOSE_RE.match(line)
            if (
                closing
                and closing.group(1)[0] == fence[0]
                and len(closing.group(1)) >= fence[1]
            ):
                fence = None
            continue
        if html_block_terminator is not None:
            if html_block_terminator.casefold() in line.casefold():
                html_block_terminator = None
            continue
        if html_block_until_blank:
            if not line.strip():
                html_block_until_blank = False
            continue
        # Contract anchors and tables are top-level Markdown. Four-space and
        # tab-indented lines render as code and therefore carry no authority.
        if line.startswith("\t") or re.match(r"^ {4,}\S", line):
            continue
        stripped = line.strip()
        if stripped in markers:
            active.append((number, line))
            continue
        opening = _FENCE_RE.match(line)
        if opening:
            fence = (opening.group(1)[0], len(opening.group(1)))
            continue
        html_block = _html_block_start(line, markers)
        if html_block is not None:
            kind, terminator = html_block
            if kind == "terminator" and terminator is not None:
                if terminator.casefold() not in line.casefold()[
                    line.casefold().find("<") + 1 :
                ]:
                    html_block_terminator = terminator
            else:
                html_block_until_blank = True
            continue
        remainder = line
        active_parts: list[str] = []

        while remainder:
            if in_comment:
                end = remainder.find("-->")
                if end == -1:
                    break
                in_comment = False
                remainder = remainder[end + 3 :]
                continue

            start = remainder.find("<!--")
            if start == -1:
                active_parts.append(remainder)
                break

            active_parts.append(remainder[:start])
            end = remainder.find("-->", start + 4)
            if end == -1:
                in_comment = True
                break
            remainder = remainder[end + 3 :]

        value = "".join(active_parts)
        if value.strip():
            active.append((number, value))

    return tuple(active)


def active_text(text: str) -> str:
    """Return active Markdown content with line numbering removed."""

    return "\n".join(line for _, line in active_markdown_lines(text))


def exact_marker_lines(text: str, marker: str) -> tuple[int, ...]:
    """Return line numbers of exact standalone occurrences of one marker."""

    return tuple(
        number
        for number, line in active_markdown_lines(text, machine_markers=(marker,))
        if line.strip() == marker
    )


def active_machine_block(
    text: str, start_marker: str, end_marker: str
) -> tuple[str | None, str | None]:
    """Extract active content between one matched exact marker pair."""

    starts = exact_marker_lines(text, start_marker)
    ends = exact_marker_lines(text, end_marker)
    if len(starts) != 1 or len(ends) != 1:
        return None, None
    start_line, end_line = starts[0], ends[0]
    if end_line <= start_line:
        return None, "invalid marker order"
    body = "\n".join(
        line
        for number, line in active_markdown_lines(text)
        if start_line < number < end_line
    ).strip()
    if not body:
        return None, "empty machine block"
    return body, None
