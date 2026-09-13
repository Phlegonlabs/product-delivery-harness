#!/usr/bin/env python3
"""Read only active Markdown content for contract validation."""

from __future__ import annotations

import re


ActiveLine = tuple[int, str]

_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_FENCE_CLOSE_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})[ \t]*$")
_RAW_HTML_TAGS = {
    "address", "article", "aside", "blockquote", "body", "caption", "center",
    "colgroup", "dd", "details", "dialog", "dir", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "form", "frameset", "head",
    "header", "html", "iframe", "legend", "li", "main", "menu", "nav",
    "noframes", "ol", "optgroup", "option", "p", "pre", "script", "search",
    "section", "style", "summary", "table", "tbody", "td", "template", "tfoot",
    "th", "thead", "textarea", "title", "tr", "ul",
}
_VOID_HTML_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
_RAW_HTML_OPEN_RE = re.compile(
    r"^[ ]{0,3}<([A-Za-z][A-Za-z0-9-]*)(?:\s|>|$)", re.IGNORECASE
)


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
    in_outer_comment = False
    html_block_tag: str | None = None
    html_block_terminator: str | None = None

    for number, line in enumerate(text.splitlines(), start=1):
        if fence is None and html_block_terminator is not None:
            if html_block_terminator in line:
                html_block_terminator = None
            continue
        if fence is None and html_block_tag is not None:
            if re.search(rf"</{re.escape(html_block_tag)}\s*>", line, re.IGNORECASE):
                html_block_tag = None
            continue
        if fence is None:
            stripped_html = line.lstrip(" ") if len(line) - len(line.lstrip(" ")) <= 3 else ""
            raw_pair = None
            if stripped_html.startswith("<?"):
                raw_pair = ("<?", "?>")
            elif stripped_html.startswith("<![CDATA["):
                raw_pair = ("<![CDATA[", "]]>")
            elif re.match(r"<![A-Z]", stripped_html):
                raw_pair = ("<!", ">")
            if raw_pair is not None:
                if raw_pair[1] not in stripped_html[len(raw_pair[0]) :]:
                    html_block_terminator = raw_pair[1]
                continue
            html_open = _RAW_HTML_OPEN_RE.match(line)
            if html_open:
                tag = html_open.group(1).casefold()
                if (
                    tag not in _VOID_HTML_TAGS
                    and not line.rstrip().endswith("/>")
                    and re.search(rf"</{re.escape(tag)}\s*>", line, re.IGNORECASE) is None
                ):
                    html_block_tag = tag
                continue
        # Contract anchors and tables are top-level Markdown. Four-space and
        # tab-indented lines render as code and therefore carry no authority.
        if line.startswith("\t") or re.match(r"^ {4,}\S", line):
            continue
        remainder = line
        active_parts: list[str] = []

        while remainder:
            if fence is not None:
                closing = _FENCE_CLOSE_RE.match(remainder)
                if (
                    closing
                    and closing.group(1)[0] == fence[0]
                    and len(closing.group(1)) >= fence[1]
                ):
                    fence = None
                    remainder = remainder[closing.end() :]
                    continue
                break

            if in_comment:
                end = remainder.find("-->")
                if end == -1:
                    break
                in_comment = False
                remainder = remainder[end + 3 :]
                continue

            if in_outer_comment:
                if remainder.strip() == "-->":
                    in_outer_comment = False
                    break
                break

            stripped = remainder.strip()
            if stripped in markers:
                active_parts.append(remainder)
                break

            opening = _FENCE_RE.match(remainder)
            if opening:
                fence = (opening.group(1)[0], len(opening.group(1)))
                remainder = remainder[opening.end() :]
                continue

            start = remainder.find("<!--")
            if start == -1:
                active_parts.append(remainder)
                break

            active_parts.append(remainder[:start])
            if remainder[start:].strip() == "<!--":
                in_outer_comment = True
                break
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
