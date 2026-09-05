#!/usr/bin/env python3
"""Validate a self-contained PRD wireframe HTML projection."""

from __future__ import annotations

import argparse
import json
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
PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
VALID_APPROVAL_STATUSES = {"draft", "approved", "revision_requested", "blocked"}
VALID_PRIORITIES = {"primary", "secondary", "quiet"}


class ResourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.external_resources: list[str] = []
        self.link_tags = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag.lower() == "link":
            self.link_tags += 1
        for name in ("src", "href"):
            value = values.get(name)
            if not value:
                continue
            lowered = value.strip().lower()
            if lowered.startswith(("http://", "https://", "//")):
                self.external_resources.append(f"{tag}[{name}={value!r}]")


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


def _validate_data(data: Any, *, require_filled: bool) -> list[str]:
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["wireframe-data: must be a JSON object"]

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

        compact_order = screen.get("compactOrder")
        if not _string_list(compact_order):
            _add(problems, f"{path}.compactOrder", "must be a non-empty string list")
        elif len(compact_order) != len(set(compact_order)) or set(compact_order) != set(region_ids):
            _add(
                problems,
                f"{path}.compactOrder",
                "must contain every region ID exactly once",
            )

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

    match = DATA_BLOCK_RE.search(html)
    if not match:
        return [f"{html_path}: missing wireframe-data application/json block"]
    try:
        data = json.loads(match.group("data"))
    except json.JSONDecodeError as exc:
        return [f"{html_path}: wireframe-data is invalid JSON: {exc}"]

    problems.extend(_validate_data(data, require_filled=require_filled))

    if prd_path is not None:
        try:
            prd_text = prd_path.read_text(encoding="utf-8")
        except OSError as exc:
            return [f"{prd_path}: cannot read PRD: {exc}"]
        problems.extend(validate_prd_wireframe_data(prd_text, data))

    for required in (
        'id="page-list"',
        'id="state-controls"',
        'data-viewport="expanded"',
        'data-viewport="compact"',
        "All pages",
        "textContent",
    ):
        if required not in html:
            _add(problems, str(html_path), f"missing reviewer-shell marker {required!r}")

    parser = ResourceParser()
    parser.feed(html)
    if parser.link_tags:
        _add(problems, str(html_path), "must not contain <link> resources")
    if parser.external_resources:
        _add(
            problems,
            str(html_path),
            "must not load external resources: " + ", ".join(parser.external_resources),
        )
    if re.search(r"@import\s", html, re.IGNORECASE):
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
