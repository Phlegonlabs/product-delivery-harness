#!/usr/bin/env python3
"""Validate a self-contained PRD wireframe HTML projection."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from prd_ui_contract import validate_prd_wireframe_data


DATA_BLOCK_RE = re.compile(
    r'<script\s+id=["\']wireframe-data["\']\s+type=["\']application/json["\']\s*>'
    r"(?P<data>[\s\S]*?)</script>",
    re.IGNORECASE,
)
REMOTE_CSS_URL_RE = re.compile(
    r"""url\s*\(\s*(?:
        "(?P<double>(?:https?:)?//[^"]+)"
        |'(?P<single>(?:https?:)?//[^']+)'
        |(?P<bare>(?:https?:)?//[^\s)]+)
    )\s*\)""",
    re.IGNORECASE | re.VERBOSE,
)
CSS_IMAGE_SET_RE = re.compile(r"(?:-webkit-)?image-set\s*\(", re.IGNORECASE)
REMOTE_CSS_STRING_RE = re.compile(
    r"""(?:
        "(?P<double>(?:https?:)?//[^"]+)"
        |'(?P<single>(?:https?:)?//[^']+)'
        |(?P<bare>(?<![A-Za-z0-9_'\"])(?:https?:)?//[^\s,)'\"]+)
    )""",
    re.IGNORECASE | re.VERBOSE,
)
PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
VALID_APPROVAL_STATUSES = {"draft", "approved", "revision_requested", "blocked"}
VALID_PRIORITIES = {"primary", "secondary", "quiet"}
WIREFRAME_SCHEMA = "wireframes/2"


def _strip_css_comments(css: str) -> str:
    """Remove CSS comments without treating comment markers inside strings as syntax."""

    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    while index < len(css):
        char = css[index]
        if quote is not None:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            output.append(char)
            index += 1
            continue
        if css.startswith("/*", index):
            end = css.find("*/", index + 2)
            index = len(css) if end < 0 else end + 2
            output.append(" ")
            continue
        output.append(char)
        index += 1
    return "".join(output)


class ResourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.data_block_count = 0
        self.data_blocks: list[str] = []
        self.duplicate_attributes: list[str] = []
        self.external_resources: list[str] = []
        self.external_css_resources: list[str] = []
        self.css_imports = False
        self._data_block: list[str] | None = None
        self._style_depth = 0
        self._css_chunks: list[str] = []
        self.link_tags = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        seen_attributes: set[str] = set()
        for name, _ in attrs:
            lowered_name = name.lower()
            if lowered_name in seen_attributes:
                self.duplicate_attributes.append(f"{tag_name}[{lowered_name}]")
            seen_attributes.add(lowered_name)
        values = dict(attrs)
        if tag_name == "link":
            self.link_tags += 1
        if tag_name == "script":
            script_id = values.get("id")
            script_type = values.get("type")
            if (
                isinstance(script_id, str)
                and script_id.strip().lower() == "wireframe-data"
                and isinstance(script_type, str)
                and script_type.strip().lower() == "application/json"
            ):
                self.data_block_count += 1
                self._data_block = []
        elif tag_name == "style":
            self._style_depth += 1

        inline_style = values.get("style")
        if inline_style:
            self._css_chunks.append(inline_style)

        for name in ("src", "href", "xlink:href", "poster"):
            value = values.get(name)
            if not value:
                continue
            lowered = value.strip().lower()
            if lowered.startswith(("http://", "https://", "//")):
                self.external_resources.append(f"{tag}[{name}={value!r}]")

        if tag_name == "object":
            value = values.get("data")
            if value and value.strip().lower().startswith(("http://", "https://", "//")):
                self.external_resources.append(f"{tag}[data={value!r}]")

        srcset = values.get("srcset")
        if srcset:
            for match in re.finditer(r"(?:https?:)?//[^\s,]+", srcset, re.IGNORECASE):
                self.external_resources.append(f"{tag}[srcset={match.group(0)!r}]")

    def handle_data(self, data: str) -> None:
        if self._data_block is not None:
            self._data_block.append(data)
        if self._style_depth:
            self._css_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name == "script" and self._data_block is not None:
            self.data_blocks.append("".join(self._data_block))
            self._data_block = None
        elif tag_name == "style" and self._style_depth:
            self._style_depth -= 1

    def close(self) -> None:
        super().close()
        css = _strip_css_comments("\n".join(self._css_chunks))
        self.css_imports = re.search(r"@import\b", css, re.IGNORECASE) is not None
        for match in REMOTE_CSS_URL_RE.finditer(css):
            resource = next(
                value for value in match.groups() if value is not None
            )
            self.external_css_resources.append(f"CSS url({resource!r})")
        for match in CSS_IMAGE_SET_RE.finditer(css):
            start = match.end()
            depth = 1
            quote: str | None = None
            escaped = False
            index = start
            while index < len(css) and depth:
                character = css[index]
                if quote is not None:
                    if escaped:
                        escaped = False
                    elif character == "\\":
                        escaped = True
                    elif character == quote:
                        quote = None
                elif character in {"'", '"'}:
                    quote = character
                elif character == "(":
                    depth += 1
                elif character == ")":
                    depth -= 1
                index += 1
            contents = css[start : index - 1 if depth == 0 else index]
            for resource_match in REMOTE_CSS_STRING_RE.finditer(contents):
                resource = next(
                    value
                    for value in resource_match.groups()
                    if value is not None
                )
                self.external_css_resources.append(
                    f"CSS image-set({resource!r})"
                )


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty(item) for item in value)


def _display_element(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if not isinstance(value, dict) or not _nonempty(value.get("label")):
        return False
    contract = value.get("contract")
    if contract is None:
        return True
    return (
        isinstance(contract, dict)
        and bool(contract)
        and all(_nonempty(key) and _nonempty(item) for key, item in contract.items())
    )


def _add(problems: list[str], path: str, message: str) -> None:
    problems.append(f"{path}: {message}")


def _responsive_key(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _validate_responsive_data(
    data: dict[str, Any], problems: list[str]
) -> list[str]:
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
    valid_size_classes = (
        isinstance(size_classes, list)
        and len(size_classes) >= 2
        and all(_nonempty(value) for value in size_classes)
        and len(set(size_classes)) == len(size_classes)
    )
    if (
        has_viewports == has_size_classes
        or (has_viewports and not valid_viewports)
        or (has_size_classes and not valid_size_classes)
    ):
        _add(
            problems,
            "wireframe-data",
            "must declare exactly one responsive set with at least two unique "
            "targets: ascending positive numeric viewports or string sizeClasses",
        )
        return []

    targets = viewports if has_viewports else size_classes
    target_keys = [_responsive_key(value) for value in targets]
    canvas_widths = data.get("canvasWidths")
    if not isinstance(canvas_widths, dict):
        _add(
            problems,
            "wireframe-data.canvasWidths",
            "must map every responsive target to a positive review-canvas width",
        )
    else:
        actual_keys = set(canvas_widths)
        expected_keys = set(target_keys)
        if actual_keys != expected_keys:
            _add(
                problems,
                "wireframe-data.canvasWidths",
                "must contain exactly the responsive target keys: "
                + ", ".join(target_keys),
            )
        for target, width in canvas_widths.items():
            if (
                not isinstance(width, (int, float))
                or isinstance(width, bool)
                or not math.isfinite(width)
                or width <= 0
            ):
                _add(
                    problems,
                    f"wireframe-data.canvasWidths.{target}",
                    "must be a positive numeric width",
                )
            elif (
                has_viewports
                and target in expected_keys
                and float(width) != float(target)
            ):
                _add(
                    problems,
                    f"wireframe-data.canvasWidths.{target}",
                    "must equal its web viewport target",
                )
    return target_keys


def _validate_data(data: Any, *, require_filled: bool) -> list[str]:
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["wireframe-data: must be a JSON object"]

    if data.get("schema") != WIREFRAME_SCHEMA:
        _add(
            problems,
            "wireframe-data.schema",
            f"must be {WIREFRAME_SCHEMA!r}",
        )

    for key in ("product", "approvalStatus", "source"):
        if not _nonempty(data.get(key)):
            _add(problems, f"wireframe-data.{key}", "must be a non-empty string")

    status = data.get("approvalStatus")
    if _nonempty(status) and status not in VALID_APPROVAL_STATUSES:
        _add(
            problems,
            "wireframe-data.approvalStatus",
            f"must be one of {sorted(VALID_APPROVAL_STATUSES)}",
        )
    if data.get("source") != "PRD.md#UI-Surface-Contract":
        _add(
            problems,
            "wireframe-data.source",
            "must be 'PRD.md#UI-Surface-Contract'",
        )

    responsive_targets = _validate_responsive_data(data, problems)

    screens = data.get("screens")
    if not isinstance(screens, list) or not screens:
        _add(problems, "wireframe-data.screens", "must be a non-empty list")
        return problems

    seen_screens: set[str] = set()
    for screen_index, screen in enumerate(screens):
        path = f"wireframe-data.screens[{screen_index}]"
        if not isinstance(screen, dict):
            _add(problems, path, "must be an object")
            continue
        screen_id = screen.get("id")
        if not _nonempty(screen_id) or not screen_id.startswith("UI-"):
            _add(problems, f"{path}.id", "must be a non-empty UI-* ID")
        elif screen_id in seen_screens:
            _add(problems, f"{path}.id", f"duplicates {screen_id}")
        else:
            seen_screens.add(screen_id)

        for key in ("name", "route", "goal"):
            if not _nonempty(screen.get(key)):
                _add(problems, f"{path}.{key}", "must be a non-empty string")
        if "traces" in screen and not _string_list(screen["traces"]):
            _add(problems, f"{path}.traces", "must be a string list when present")

        regions = screen.get("regions")
        if not isinstance(regions, list) or not regions:
            _add(problems, f"{path}.regions", "must be a non-empty list")
            continue

        region_ids: list[str] = []
        for region_index, region in enumerate(regions):
            region_path = f"{path}.regions[{region_index}]"
            if not isinstance(region, dict):
                _add(problems, region_path, "must be an object")
                continue
            region_id = region.get("id")
            if not _nonempty(region_id):
                _add(problems, f"{region_path}.id", "must be a non-empty string")
            elif region_id in region_ids:
                _add(problems, f"{region_path}.id", f"duplicates {region_id}")
            else:
                region_ids.append(region_id)
            for key in ("section", "purpose"):
                if not _nonempty(region.get(key)):
                    _add(problems, f"{region_path}.{key}", "must be a non-empty string")
            if region.get("priority") not in VALID_PRIORITIES:
                _add(
                    problems,
                    f"{region_path}.priority",
                    f"must be one of {sorted(VALID_PRIORITIES)}",
                )
            span = region.get("span")
            if not isinstance(span, int) or isinstance(span, bool) or not 1 <= span <= 12:
                _add(problems, f"{region_path}.span", "must be an integer from 1 to 12")
            elements = region.get("elements")
            if (
                not isinstance(elements, list)
                or not elements
                or not all(_display_element(item) for item in elements)
            ):
                _add(
                    problems,
                    f"{region_path}.elements",
                    "must be a non-empty list of strings or {label, contract} objects",
                )
            actions = region.get("actions")
            if not isinstance(actions, list) or not all(_nonempty(item) for item in actions):
                _add(problems, f"{region_path}.actions", "must be a string list")
            if "traces" in region and not _string_list(region["traces"]):
                _add(problems, f"{region_path}.traces", "must be a string list when present")

        never_drop = screen.get("neverDrop")
        if not _string_list(never_drop) or not never_drop:
            _add(problems, f"{path}.neverDrop", "must be a non-empty string list")
            never_drop_ids: set[str] = set()
        else:
            never_drop_ids = set(never_drop)
            if len(never_drop) != len(never_drop_ids):
                _add(problems, f"{path}.neverDrop", "must not contain duplicates")
            unknown_never_drop = sorted(never_drop_ids - set(region_ids))
            if unknown_never_drop:
                _add(
                    problems,
                    f"{path}.neverDrop",
                    "references unknown region IDs: " + ", ".join(unknown_never_drop),
                )
            primary_regions = {
                region.get("id")
                for region in regions
                if isinstance(region, dict)
                and region.get("priority") == "primary"
                and _nonempty(region.get("id"))
            }
            missing_primary = sorted(primary_regions - never_drop_ids)
            if missing_primary:
                _add(
                    problems,
                    f"{path}.neverDrop",
                    "must include every primary region: " + ", ".join(missing_primary),
                )

        responsive_layouts = screen.get("responsiveLayouts")
        if not isinstance(responsive_layouts, dict):
            _add(
                problems,
                f"{path}.responsiveLayouts",
                "must be an object keyed by every responsive target",
            )
            responsive_layouts = {}
        elif set(responsive_layouts) != set(responsive_targets):
            _add(
                problems,
                f"{path}.responsiveLayouts",
                "must contain exactly the responsive targets: "
                + ", ".join(responsive_targets),
            )
        for target in responsive_targets:
            layout = responsive_layouts.get(target)
            layout_path = f"{path}.responsiveLayouts.{target}"
            if not isinstance(layout, dict):
                _add(problems, layout_path, "must be an object")
                continue
            order = layout.get("order")
            if not _string_list(order):
                _add(problems, f"{layout_path}.order", "must be a non-empty string list")
            elif len(order) != len(set(order)) or set(order) != set(region_ids):
                _add(
                    problems,
                    f"{layout_path}.order",
                    "must contain every region ID exactly once",
                )
            hidden = layout.get("hidden")
            if not isinstance(hidden, list) or not all(_nonempty(item) for item in hidden):
                _add(problems, f"{layout_path}.hidden", "must be a string list")
                hidden_ids: set[str] = set()
            else:
                hidden_ids = set(hidden)
                if len(hidden) != len(hidden_ids):
                    _add(problems, f"{layout_path}.hidden", "must not contain duplicates")
                unknown_hidden = sorted(hidden_ids - set(region_ids))
                if unknown_hidden:
                    _add(
                        problems,
                        f"{layout_path}.hidden",
                        "references unknown region IDs: " + ", ".join(unknown_hidden),
                    )
                hidden_never_drop = sorted(hidden_ids & never_drop_ids)
                if hidden_never_drop:
                    _add(
                        problems,
                        f"{layout_path}.hidden",
                        "must not hide never-drop regions: "
                        + ", ".join(hidden_never_drop),
                    )
            columns = layout.get("columns")
            if (
                not isinstance(columns, int)
                or isinstance(columns, bool)
                or not 1 <= columns <= 12
            ):
                _add(problems, f"{layout_path}.columns", "must be an integer from 1 to 12")
                columns = 12
            spans = layout.get("spans")
            if not isinstance(spans, dict) or set(spans) != set(region_ids):
                _add(
                    problems,
                    f"{layout_path}.spans",
                    "must map every region ID exactly once",
                )
            else:
                for region_id, span in spans.items():
                    if (
                        not isinstance(span, int)
                        or isinstance(span, bool)
                        or not 1 <= span <= columns
                    ):
                        _add(
                            problems,
                            f"{layout_path}.spans.{region_id}",
                            f"must be an integer from 1 to {columns}",
                        )
            for key in ("reflow", "interaction"):
                if not _nonempty(layout.get(key)):
                    _add(problems, f"{layout_path}.{key}", "must be a non-empty string")

        states = screen.get("states")
        if not isinstance(states, list) or not states:
            _add(problems, f"{path}.states", "must be a non-empty list")
            continue
        seen_states: set[str] = set()
        for state_index, screen_state in enumerate(states):
            state_path = f"{path}.states[{state_index}]"
            if not isinstance(screen_state, dict):
                _add(problems, state_path, "must be an object")
                continue
            state_id = screen_state.get("id")
            if not _nonempty(state_id):
                _add(problems, f"{state_path}.id", "must be a non-empty string")
            elif state_id in seen_states:
                _add(problems, f"{state_path}.id", f"duplicates {state_id}")
            else:
                seen_states.add(state_id)
            if not _nonempty(screen_state.get("label")):
                _add(problems, f"{state_path}.label", "must be a non-empty string")
            treatments = screen_state.get("treatments")
            if not isinstance(treatments, dict):
                _add(problems, f"{state_path}.treatments", "must be an object")
            else:
                unknown = sorted(set(treatments) - set(region_ids))
                if unknown:
                    _add(
                        problems,
                        f"{state_path}.treatments",
                        "references unknown region IDs: " + ", ".join(unknown),
                    )
                for region_id, treatment in treatments.items():
                    if not _nonempty(treatment):
                        _add(
                            problems,
                            f"{state_path}.treatments.{region_id}",
                            "must be a non-empty string",
                        )

    flows = data.get("flows")
    if flows is not None:
        if not isinstance(flows, list):
            _add(problems, "wireframe-data.flows", "must be a list when present")
        else:
            for flow_index, flow in enumerate(flows):
                flow_path = f"wireframe-data.flows[{flow_index}]"
                if not isinstance(flow, dict):
                    _add(problems, flow_path, "must be an object")
                    continue
                for key in ("from", "trigger", "to"):
                    if not _nonempty(flow.get(key)):
                        _add(problems, f"{flow_path}.{key}", "must be a non-empty string")
                origin = flow.get("from")
                if _nonempty(origin) and origin not in seen_screens:
                    _add(
                        problems,
                        f"{flow_path}.from",
                        f"references unknown screen ID {origin}",
                    )

    if require_filled:
        def walk(value: Any, path: str) -> None:
            if isinstance(value, str) and PLACEHOLDER_RE.search(value):
                _add(problems, path, "contains an unfilled <placeholder>")
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")
            elif isinstance(value, dict):
                for key, item in value.items():
                    walk(item, f"{path}.{key}")

        walk(data, "wireframe-data")

    return problems


def validate(
    html_path: Path,
    *,
    require_filled: bool = False,
    require_approved: bool = False,
    prd_path: Path | None = None,
) -> list[str]:
    problems: list[str] = []
    try:
        html = html_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{html_path}: cannot read HTML: {exc}"]

    parser = ResourceParser()
    parser.feed(html)
    parser.close()
    if parser.duplicate_attributes:
        return [
            f"{html_path}: must not contain duplicate HTML attributes: "
            + ", ".join(parser.duplicate_attributes)
        ]
    if parser.data_block_count == 0:
        return [f"{html_path}: missing wireframe-data application/json block"]
    if parser.data_block_count != 1 or len(parser.data_blocks) != 1:
        return [
            f"{html_path}: must contain exactly one wireframe-data "
            f"application/json block (found {parser.data_block_count})"
        ]
    try:
        data = json.loads(parser.data_blocks[0])
    except json.JSONDecodeError as exc:
        return [f"{html_path}: wireframe-data is invalid JSON: {exc}"]

    problems.extend(_validate_data(data, require_filled=require_filled))
    if not isinstance(data, dict):
        return problems

    if prd_path is not None:
        try:
            prd_text = prd_path.read_text(encoding="utf-8")
        except OSError as exc:
            return [f"{prd_path}: cannot read PRD: {exc}"]
        problems.extend(validate_prd_wireframe_data(prd_text, data))

    for required in (
        'id="page-list"',
        'id="state-controls"',
        'id="responsive-controls"',
        "data-responsive-target",
        "runLayoutQa",
        "data-layout-qa",
        "All pages",
        "textContent",
    ):
        if required not in html:
            _add(problems, str(html_path), f"missing reviewer-shell marker {required!r}")

    if parser.link_tags:
        _add(problems, str(html_path), "must not contain <link> resources")
    external_resources = parser.external_resources + parser.external_css_resources
    if external_resources:
        _add(
            problems,
            str(html_path),
            "must not load external resources: " + ", ".join(external_resources),
        )
    if parser.css_imports:
        _add(problems, str(html_path), "must not contain CSS @import")

    if require_approved and data.get("approvalStatus") != "approved":
        _add(problems, "wireframe-data.approvalStatus", "must be 'approved'")

    return problems


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--prd", type=Path, help="cross-check the PRD UI-* surface contract")
    parser.add_argument("--require-filled", action="store_true")
    parser.add_argument("--require-approved", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    problems = validate(
        args.html,
        require_filled=args.require_filled,
        require_approved=args.require_approved,
        prd_path=args.prd,
    )
    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        return 1
    print(f"PASS {args.html} is a valid self-contained wireframe projection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
