#!/usr/bin/env python3
"""The ``ui-direction-review/1`` profile and its shared-reviewer study bytes.

A direction study is one author-owned product page reviewed before selection.
The profile names the compared studies by actual filename and gives every review
case its own surface, platform, target family and target-to-pixel width map.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from html import escape
from html.parser import HTMLParser
from typing import Any

import reviewer_shell
import ui_design_v3

SCHEMA = "ui-direction-review/1"
TEMPLATE_PATH = reviewer_shell.TEMPLATES / "DIRECTION_REVIEWER.template.html"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*\.html$")
PLATFORM_RE = re.compile(r"^[a-z][a-z0-9-]*$")
VIEWPORT_RE = re.compile(r"^[1-9][0-9]*$")
SIZE_CLASS_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
TARGET_FAMILIES = ("viewports", "sizeClasses")
# A platform listed here has exactly one target family; other platforms declare theirs.
PLATFORM_FAMILY = {"web": "viewports", "ios": "sizeClasses", "android": "sizeClasses"}
STUDY_COUNTS = (1, 3)
PROFILE_RE = re.compile(
    r'<script id="ui-direction-review" type="application/json">([\s\S]*?)</script>'
)
SHELL_RE = re.compile(r"<!-- reviewer:start -->[\s\S]*?<!-- reviewer:end -->")
REVIEWER_MARKERS = (
    "<!-- reviewer:start -->", "data-hifi-reviewer-shell", "hifi-reviewer:css:start",
    "direction-reviewer:css:start", 'id="hifi-reviewer-runtime"',
    'id="direction-reviewer-runtime"', 'id="ui-direction-review"',
)


def _segment(name: str) -> str:
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    prefix = f"<!-- direction-reviewer:{name}:start -->"
    suffix = f"<!-- direction-reviewer:{name}:end -->"
    start = html.find(prefix)
    end = html.find(suffix, start + len(prefix)) if start >= 0 else -1
    if start < 0 or end < 0:
        raise RuntimeError(f"direction reviewer template {name} markers are missing")
    return html[start : end + len(suffix)]


def style_block() -> str:
    return _segment("css")


def runtime_block(package: str) -> str:
    return (
        reviewer_shell.runtime_block() + "\n" + _segment("runtime") + "\n"
        + f'<script>connectDirectionReviewer({json.dumps({"packageId": package})})</script>'
    )


def package_id(profile: dict[str, Any]) -> str:
    source = json.dumps(profile, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return f"{SCHEMA}:{hashlib.sha256(source).hexdigest()[:16]}"


def study_files(profile: dict[str, Any]) -> frozenset[str]:
    """The only sibling files a study of this profile may link to."""

    return frozenset(row["file"] for row in profile["directions"])


def _width_label(value: Any) -> str:
    return f"{value:g}"


def _case_findings(index: int, case: Any) -> list[str]:
    label = f"cases[{index}]"
    if not isinstance(case, dict) or set(case) != {"id", "surface", "platform", "targetFamily", "widths"}:
        return [f"{label} must contain exactly id, surface, platform, targetFamily and widths"]
    problems: list[str] = []
    for key in ("id", "surface"):
        if not isinstance(case[key], str) or not ID_RE.fullmatch(case[key]):
            problems.append(f"{label}.{key} must be a plain identifier")
    platform, family, widths = case["platform"], case["targetFamily"], case["widths"]
    if not isinstance(platform, str) or not PLATFORM_RE.fullmatch(platform):
        problems.append(f"{label}.platform must be a lower-case platform name")
    if family not in TARGET_FAMILIES:
        problems.append(f"{label}.targetFamily must be one of " + ", ".join(TARGET_FAMILIES))
    elif isinstance(platform, str) and PLATFORM_FAMILY.get(platform, family) != family:
        problems.append(f"{label} platform {platform} requires targetFamily {PLATFORM_FAMILY[platform]}")
    if not isinstance(widths, dict) or not widths:
        return problems + [f"{label}.widths must map every approved target to its pixel width"]
    if len({target.casefold() for target in widths}) != len(widths):
        problems.append(f"{label}.widths must not repeat a target")
    for target, width in widths.items():
        finite = (isinstance(width, (int, float)) and not isinstance(width, bool)
                  and math.isfinite(width) and width > 0)
        if family == "viewports":
            if (not VIEWPORT_RE.fullmatch(target) or not finite or not isinstance(width, int)
                    or width != int(target)):
                problems.append(f"{label}.widths viewport {target!r} must equal its own integer pixel width")
        elif not SIZE_CLASS_RE.fullmatch(target) or not finite:
            problems.append(f"{label}.widths size class {target!r} must be a named target with a finite positive pixel width")
    return problems


def profile_findings(profile: Any) -> list[str]:
    """Closed validation of a ui-direction-review/1 profile."""

    if not isinstance(profile, dict) or profile.get("schema") != SCHEMA:
        return [f"direction review profile must be schema {SCHEMA}"]
    if set(profile) != {"schema", "round", "directions", "cases"}:
        return ["direction review profile must contain exactly schema, round, directions and cases"]
    problems: list[str] = []
    if not isinstance(profile["round"], str) or not ID_RE.fullmatch(profile["round"]):
        problems.append("round must name the docs/design/directions/<round> folder")
    directions, cases = profile["directions"], profile["cases"]
    if not isinstance(directions, list) or len(directions) not in STUDY_COUNTS:
        problems.append("directions must list three studies, or one by explicit owner choice")
        directions = directions if isinstance(directions, list) else []
    for index, row in enumerate(directions):
        label = f"directions[{index}]"
        if not isinstance(row, dict) or set(row) != {"id", "file", "sourceSha256"}:
            problems.append(f"{label} must contain exactly id, file and sourceSha256")
            continue
        if not isinstance(row["id"], str) or not ID_RE.fullmatch(row["id"]):
            problems.append(f"{label}.id must be a plain identifier")
        if not isinstance(row["file"], str) or not FILE_RE.fullmatch(row["file"]):
            problems.append(f"{label}.file must be the study's actual <name>.html filename")
        if not isinstance(row["sourceSha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["sourceSha256"]):
            problems.append(f"{label}.sourceSha256 must be the author source SHA-256")
    rows = [row for row in directions if isinstance(row, dict)]
    for key, meaning in (("id", "direction"), ("file", "study file"), ("sourceSha256", "study source")):
        values = [str(row.get(key)).casefold() for row in rows]
        if len(set(values)) != len(values):
            problems.append(f"directions must name each {meaning} once")
    if not isinstance(cases, list) or not cases:
        problems.append("cases must list at least one review case")
        cases = []
    for index, case in enumerate(cases):
        problems.extend(_case_findings(index, case))
    case_ids = [str(case.get("id")).casefold() for case in cases if isinstance(case, dict)]
    if len(set(case_ids)) != len(case_ids):
        problems.append("cases must name each review case once")
    return problems


def build_shell(profile: dict[str, Any], file: str) -> str:
    """Build the direction sidebar: studies by filename, then per-case targets."""

    directions, cases = profile["directions"], profile["cases"]
    if file not in [row["file"] for row in directions]:
        raise ValueError(f"study {file!r} is not declared by the profile")
    studies = "1 study" if len(directions) == 1 else f"{len(directions)} studies"
    reviewed = "1 case" if len(cases) == 1 else f"{len(cases)} cases"
    html = (
        '<aside data-hifi-reviewer-shell data-hifi-reviewer-version="3" data-hifi-review-mode="direction" '
        f'data-hifi-platform="{escape(cases[0]["platform"])}" aria-label="Direction review controls">\n'
        "<h2 data-direction-heading>Direction review</h2>\n"
        f'<p data-direction-meta>{escape(profile["round"])}, {studies}, {reviewed}</p>\n'
        '<nav data-hifi-page-nav aria-label="Direction studies">\n'
    )
    for row in directions:
        current = ' aria-current="page"' if row["file"] == file else ""
        html += (
            f'<a href="{escape(row["file"])}" data-direction-file="{escape(row["file"])}" '
            f'data-direction-id="{escape(row["id"])}"{current}>{escape(row["id"])}'
            f'<small>{escape(row["file"])}</small></a>\n'
        )
    html += "</nav>\n<fieldset data-hifi-state-controls data-direction-case-controls><legend>Review case</legend>\n"
    for index, case in enumerate(cases):
        html += (
            f'<button type="button" data-hifi-state-control="{escape(case["id"])}" '
            f'data-hifi-state-surface="{escape(case["surface"])}" data-direction-platform="{escape(case["platform"])}" '
            f'data-direction-family="{escape(case["targetFamily"])}" aria-pressed="{str(index == 0).lower()}">'
            f'{escape(case["id"])}<small>{escape(case["surface"])} on {escape(case["platform"])}</small></button>\n'
        )
    html += "</fieldset>\n<fieldset data-hifi-responsive-controls><legend>Target width</legend>\n"
    for index, case in enumerate(cases):
        for position, (target, width) in enumerate(case["widths"].items()):
            pixels = _width_label(width) + "px"
            label = pixels if case["targetFamily"] == "viewports" else f"{escape(target)}<small>{pixels}</small>"
            html += (
                f'<button type="button" data-hifi-target-control="{escape(target)}" '
                f'data-direction-case="{escape(case["id"])}" data-direction-width="{_width_label(width)}" '
                f'aria-pressed="{str(index == 0 and position == 0).lower()}"'
                f'{"" if index == 0 else " hidden"}>{label}</button>\n'
            )
    html += '</fieldset>\n<p data-direction-status role="status"></p>\n</aside>'
    return html


def _shell_fragment(profile: dict[str, Any], file: str) -> str:
    return "<!-- reviewer:start -->\n" + build_shell(profile, file) + "\n<!-- reviewer:end -->"


def _profile_block(profile: dict[str, Any]) -> str:
    encoded = json.dumps(profile, ensure_ascii=False, separators=(",", ":"))
    return f'<script id="ui-direction-review" type="application/json">{encoded}</script>'


class _ProductParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canvases = 0
        self.case_views: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if "data-hifi-canvas" in values:
            self.canvases += 1
        if "data-direction-case-view" in values:
            self.case_views.append(values["data-direction-case-view"] or "")


def product_findings(html: str, file: str, profile: dict[str, Any]) -> list[str]:
    """The author owns the product DOM; the reviewer needs one canvas and one view per case."""

    parser = _ProductParser()
    parser.feed(html)
    parser.close()
    problems: list[str] = []
    if parser.canvases != 1:
        problems.append(f"{file} must provide exactly one author-owned [data-hifi-canvas] product wrapper")
    expected = [case["id"] for case in profile["cases"]]
    if sorted(parser.case_views) != sorted(expected):
        problems.append(
            f"{file} must provide exactly one [data-direction-case-view] per review case: " + ", ".join(expected)
        )
    return problems


def source_findings(html: str, file: str, profile: dict[str, Any]) -> list[str]:
    """Checks an author source must pass before any study is written."""

    problems = [f"{file} already contains reviewer chrome ({marker}); supply the author source"
                for marker in REVIEWER_MARKERS if marker in html]
    lowered = html.casefold()
    if "</head>" not in lowered or "<body" not in lowered or "</body>" not in lowered:
        problems.append(f"{file} must be a complete HTML document with head and body")
    problems.extend(ui_design_v3.study_html_findings(html, file, local_pages=study_files(profile)))
    problems.extend(product_findings(html, file, profile))
    return problems


def render_study(profile: dict[str, Any], html: str, file: str) -> str:
    """Install the shared reviewer around one author source without editing its product DOM."""

    head = html.casefold().rfind("</head>")
    html = (html[:head] + reviewer_shell.shared_style_block() + "\n" + style_block() + "\n"
            + _profile_block(profile) + "\n" + html[head:])
    body = html.casefold().rfind("<body")
    opened = html.find(">", body)
    html = html[: opened + 1] + "\n" + _shell_fragment(profile, file) + "\n" + html[opened + 1 :]
    closed = html.casefold().rfind("</body>")
    return html[:closed] + runtime_block(package_id(profile)) + "\n" + html[closed:]


def has_profile(html: str) -> bool:
    return PROFILE_RE.search(html) is not None


def assembled_study_findings(html: str, path: str) -> list[str]:
    """Strict profile for a newly assembled study; it never applies to older studies."""

    file = path.replace("\\", "/").rsplit("/", 1)[-1]
    blocks = PROFILE_RE.findall(html)
    if len(blocks) != 1:
        return [f"Direction study {path} must embed exactly one {SCHEMA} profile"]
    try:
        profile = json.loads(blocks[0])
    except json.JSONDecodeError:
        return [f"Direction study {path} embeds an unreadable {SCHEMA} profile"]
    problems = [f"Direction study {path}: {item}" for item in profile_findings(profile)]
    if problems:
        return problems
    if file not in [row["file"] for row in profile["directions"]]:
        return [f"Direction study {path} is not one of its profile's actual study filenames"]
    if blocks[0] != json.dumps(profile, ensure_ascii=False, separators=(",", ":")):
        problems.append(f"Direction study {path} profile must use the assembler's canonical encoding")
    problems.extend(f"Direction study {path}: {item}" for item in reviewer_shell.shared_css_drift(html))
    if html.count(style_block()) != 1:
        problems.append(f"Direction study {path} must carry the exact direction reviewer styles once")
    shells = SHELL_RE.findall(html)
    if shells != [_shell_fragment(profile, file)]:
        problems.append(f"Direction study {path} reviewer shell must exactly match its profile")
    if html.count(runtime_block(package_id(profile))) != 1:
        problems.append(f"Direction study {path} must carry the exact shared runtime and direction shim once")
    problems.extend(ui_design_v3.study_html_findings(html, path, local_pages=study_files(profile)))
    problems.extend(f"Direction study {item}" for item in product_findings(html, path, profile))
    return problems
