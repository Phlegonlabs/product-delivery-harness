#!/usr/bin/env python3
"""Deterministic helpers for the shared HiFi reviewer shell bytes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from html import escape

TEMPLATES = Path(__file__).resolve().parents[1] / "assets" / "templates"
SHARED_CSS_PATH = TEMPLATES / "REVIEWER_SHARED.css"
HIFI_TEMPLATE_PATH = TEMPLATES / "HIFI_REVIEWER.template.html"


def shared_css() -> str:
    return SHARED_CSS_PATH.read_text(encoding="utf-8").rstrip() + "\n"


def shared_style_block() -> str:
    return (
        "<!-- hifi-reviewer:css:start -->\n"
        '<style data-hifi-reviewer-css>\n'
        + shared_css()
        + "</style>\n"
        + "<!-- hifi-reviewer:css:end -->"
    )


def css_segment(html: str) -> str | None:
    prefix = "<!-- hifi-reviewer:css:start -->"
    suffix = "<!-- hifi-reviewer:css:end -->"
    start = html.find(prefix)
    end = html.find(suffix, start + len(prefix)) if start >= 0 else -1
    if start < 0 or end < 0:
        return None
    return html[start : end + len(suffix)]


def shared_css_drift(html: str) -> list[str]:
    segment = css_segment(html)
    if segment is None:
        return ["HiFi page is missing the shared reviewer CSS segment"]
    expected = shared_style_block()
    if segment != expected:
        return [
            "HiFi shared reviewer CSS must exactly match "
            "assets/templates/REVIEWER_SHARED.css"
        ]
    return []


def inject_shared_css(html: str) -> str:
    if css_segment(html) is not None:
        return html
    if "</head>" not in html.casefold():
        raise ValueError("HiFi product page has no </head> insertion point")
    index = html.casefold().rfind("</head>")
    return html[:index] + shared_style_block() + "\n" + html[index:]


def runtime_source() -> str:
    html = HIFI_TEMPLATE_PATH.read_text(encoding="utf-8")
    prefix = "<!-- hifi-reviewer:runtime:start -->\n"
    suffix = "\n<!-- hifi-reviewer:runtime:end -->"
    start = html.find(prefix)
    end = html.find(suffix, start + len(prefix)) if start >= 0 else -1
    if start < 0 or end < 0:
        raise RuntimeError("HiFi reviewer template runtime markers are missing")
    return html[start + len(prefix) : end]


def inject_runtime(html: str) -> str:
    if 'id="hifi-reviewer-runtime"' in html:
        return html
    block = (
        "<!-- hifi-reviewer:runtime:start -->\n"
        + runtime_source()
        + "\n<!-- hifi-reviewer:runtime:end -->\n"
        + "<script>connectHifiReviewer()</script>"
    )
    index = html.casefold().rfind("</body>")
    if index < 0:
        raise ValueError("HiFi product page has no </body> insertion point")
    return html[:index] + block + "\n" + html[index:]


def platform_label(row: dict[str, Any]) -> str | None:
    """Return a supplied App/Web/Admin label; never invent one."""

    supplied = row.get("platformGroup")
    if supplied is None:
        return None
    value = str(supplied).strip().casefold()
    return {"app": "App", "web": "Web", "admin": "Admin"}.get(value)


def ordered_pages(manifest: dict[str, Any]) -> list[str]:
    pages: list[str] = []
    for row in manifest.get("surfaces", []):
        page = row.get("page")
        if isinstance(page, str) and page not in pages:
            pages.append(page)
    return pages


def build_shell(manifest: dict[str, Any], page: str, *, version: int = 3) -> str:
    """Build the authoritative sidebar shell from declared manifest rows."""

    surfaces = manifest.get("surfaces", [])
    pages = ordered_pages(manifest)
    if version not in {2, 3}:
        raise ValueError("reviewer shell version must be 2 or 3")
    if page not in pages:
        raise ValueError(f"page {page!r} is not declared by the manifest")
    page_rows = [row for row in surfaces if row.get("page") == page]
    targets = []
    for row in page_rows:
        for target in row.get("responsive", {}).get("targets", []):
            value = str(target)
            if value not in targets:
                targets.append(value)

    groups: list[str] = []
    for row in surfaces:
        label = platform_label(row) if version == 3 else None
        if label and label not in groups:
            groups.append(label)

    html = (
        '<aside data-hifi-reviewer-shell data-hifi-reviewer-version="'
        + str(version)
        + '" data-hifi-platform="'
        + escape(platform_label(page_rows[0]) or "shared")
        + '" aria-label="HiFi review controls">\n'
        '<a data-hifi-review-view="overview" href="index.html#overview">Overview</a>\n'
        '<nav data-hifi-page-nav aria-label="Product screens">\n'
    )
    last_group = None
    seen_pages: set[str] = set()
    for row in surfaces:
        page_name = row.get("page", "")
        if page_name in seen_pages:
            continue
        seen_pages.add(page_name)
        label = platform_label(row) if version == 3 else None
        if label and label != last_group:
            html += f'<span data-hifi-platform-group="{escape(label)}">{escape(label)}</span>\n'
            last_group = label
        current = ' aria-current="page"' if page_name == page else ""
        html += f'<a href="{escape(page_name)}"{current}>{escape(page_name.replace(".html", ""))}</a>\n'
    html += (
        '</nav>\n'
        '<a data-hifi-review-view="design-tokens" href="index.html#design-tokens">Design Tokens</a>\n'
        '<fieldset data-hifi-responsive-controls><legend>Responsive target</legend>\n'
    )
    for index, target in enumerate(targets):
        selected = "true" if index == 0 else "false"
        label = f"{target}px" if str(target).isdigit() else str(target)
        html += (
            f'<button type="button" data-hifi-target-control="{escape(target)}" '
            f'aria-pressed="{selected}">{escape(label)}</button>\n'
        )
    html += "</fieldset>\n"
    if version == 3:
        html += '<fieldset data-hifi-state-controls><legend>Product state</legend>\n'
        for row in page_rows:
            for index, state in enumerate(row.get("states", [])):
                if str(state).strip().casefold() in {"n/a", "na"}:
                    continue
                html += (
                    f'<button type="button" data-hifi-state-control="{escape(str(state))}" '
                    f'data-hifi-state-surface="{escape(str(row["id"]))}" '
                    f'aria-pressed="{str(index == 0).lower()}">{escape(str(state))}</button>\n'
                )
        html += "</fieldset>\n"
    html += "</aside>"
    return html


def inject_shell(manifest: dict[str, Any], html: str, page: str, *, version: int = 3) -> str:
    """Install the exact shell fragment without touching product surfaces."""

    import re

    pattern = re.compile(
        r"<!-- reviewer:start -->[\s\S]*?<!-- reviewer:end -->", re.MULTILINE
    )
    fragment = (
        "<!-- reviewer:start -->\n"
        + build_shell(manifest, page, version=version)
        + "\n<!-- reviewer:end -->"
    )
    if pattern.search(html):
        return pattern.sub(fragment, html, count=1)
    index = html.casefold().rfind("<body")
    if index < 0:
        raise ValueError("HiFi product page has no <body> insertion point")
    open_end = html.find(">", index)
    if open_end < 0:
        raise ValueError("HiFi product page has a malformed <body> tag")
    return html[: open_end + 1] + "\n" + fragment + "\n" + html[open_end + 1 :]


def manifest_child_hashes(pages: dict[str, bytes]) -> list[dict[str, str]]:
    """Hash final child bytes; the entry is not a child of itself."""

    import hashlib

    return [
        {
            "path": path,
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for path, content in sorted(pages.items(), key=lambda row: row[0].casefold())
        if path.casefold() != "index.html"
    ]


def update_manifest_child_hashes(html: str, pages: dict[str, bytes]) -> str:
    """Replace only the ui-hifi manifest pages list with final child hashes."""

    import re

    pattern = re.compile(
        r'(<script id="ui-hifi-manifest" type="application/json">)([\s\S]*?)(</script>)',
        re.IGNORECASE,
    )
    match = pattern.search(html)
    if not match:
        raise ValueError("HiFi entry has no ui-hifi manifest")
    try:
        manifest = json.loads(match.group(2))
    except json.JSONDecodeError as exc:
        raise ValueError("HiFi manifest is invalid JSON") from exc
    manifest["pages"] = manifest_child_hashes(pages)
    encoded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    return html[: match.start()] + match.group(1) + encoded + match.group(3) + html[match.end():]
