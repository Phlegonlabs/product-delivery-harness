#!/usr/bin/env python3
"""Parse Product Definition UI operations and join them to design manifests."""

from __future__ import annotations

import json
import re

from markdown_contract import active_markdown_lines
from prd_ui_contract import (
    parse_prd_ui_contract,
    UI_END_MARKER,
    UI_HEADING_RE,
    UI_START_MARKER,
)


OPERATION_ANCHOR_RE = re.compile(
    r"^\s*-\s*`operations`\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def required_operations(prd_text):
    """Return active PRD operations and parser findings.

    Each operation names one product control, its source state, destination,
    and presentation.  The parser does not infer omitted actions from prose.
    ``none — <reason>`` is valid only when a surface has no product controls.
    """

    prd = prd_text
    surfaces, errors = parse_prd_ui_contract(
        prd,
        require_responsive=True,
        require_copy=True,
        web_floor=3,
    )
    active = "\n".join(line for _, line in active_markdown_lines(prd))
    body = active.split(UI_START_MARKER, 1)[-1].split(UI_END_MARKER, 1)[0]
    headings = list(UI_HEADING_RE.finditer(body))
    for surface in sorted(set(surfaces) - {h.group(1) for h in headings}):
        errors.append(surface + " has no PRD operations result")
    result = []
    for index, heading in enumerate(headings):
        surface = heading.group(1)
        block = body[
            heading.end() : headings[index + 1].start()
            if index + 1 < len(headings)
            else len(body)
        ]
        values = [match.group(1) for match in OPERATION_ANCHOR_RE.finditer(block)]
        if len(values) != 1:
            errors.append(
                surface + " requires one PRD operations anchor, including "
                "Home/back/cancel where required"
            )
            continue
        value = values[0].strip()
        if value.startswith("none — ") and len(value[7:].strip()) >= 12:
            continue
        try:
            operations = json.loads(value)
            if not isinstance(operations, list) or not operations:
                raise ValueError(
                    "operations must be a nonempty JSON list or none — <reason>"
                )
            for operation in operations:
                if not isinstance(operation, dict) or set(operation) != {
                    "id",
                    "trigger",
                    "control",
                    "sourceState",
                    "destination",
                    "presentation",
                }:
                    raise ValueError(
                        "operations require id, trigger, control, sourceState, "
                        "destination and presentation"
                    )
                if any(
                    not isinstance(operation[key], str) or not operation[key].strip()
                    for key in (
                        "id",
                        "trigger",
                        "control",
                        "sourceState",
                        "presentation",
                    )
                ):
                    raise ValueError("operation text fields must be nonempty")
                destination = operation["destination"]
                if not isinstance(destination, dict) or set(destination) != {
                    "surface",
                    "state",
                }:
                    raise ValueError("operation destination needs surface and state")
                if operation["sourceState"] not in surfaces.get(surface, {}).get(
                    "states", []
                ):
                    raise ValueError("operation source state must be declared")
                target = surfaces.get(destination.get("surface"), {})
                if destination.get("state") not in target.get("states", []):
                    raise ValueError(
                        "operation destination must be a declared surface/state"
                    )
                if operation["presentation"] not in {
                    "page",
                    "overlay",
                    "feedback",
                    "state",
                    "tab",
                }:
                    raise ValueError("operation presentation is unknown")
                result.append(dict(operation, surface=surface))
        except (ValueError, TypeError) as exc:
            errors.append(surface + ": " + str(exc))

    keys = [(row["surface"], row["control"], row["sourceState"]) for row in result]
    if len(keys) != len(set(keys)) or len({row["id"] for row in result}) != len(result):
        errors.append(
            "PRD operations contain duplicate ids or control/source-state cases"
        )
    return result, errors


def operation_graph_findings(surfaces, operations):
    """Return ui-design/3 reachability and state-exit findings.

    The first UI surface is the entry surface; HiFi renders it on index.html.
    Every operation joins its source surface to its destination surface.  A
    state that an operation opens, other than as transient feedback, needs an
    operation that leaves it.  A surface with ``none — <reason>`` is terminal.
    """

    if not surfaces:
        return []
    entry = next(iter(surfaces))
    targets = {}
    for row in operations:
        targets.setdefault(row["surface"], set()).add(row["destination"]["surface"])
    reachable, pending = {entry}, [entry]
    while pending:
        for surface in targets.get(pending.pop(), ()):
            if surface not in reachable:
                reachable.add(surface)
                pending.append(surface)
    findings = [
        f"prd: UI surface {surface} is not reachable from entry surface "
        f"{entry} through operations"
        for surface in surfaces
        if surface not in reachable
    ]
    opened, exits = set(), set()
    for row in operations:
        source = (row["surface"], row["sourceState"])
        destination = (row["destination"]["surface"], row["destination"]["state"])
        if destination != source:
            exits.add(source)
            if row["presentation"] != "feedback":
                opened.add(destination)
    for surface, state in sorted(opened - exits):
        if surface in targets:
            findings.append(
                f"prd: UI surface {surface} state {state} has no exit operation"
            )
    return findings


def coverage_findings(prd, wireframe, manifest=None):
    """Join operations to a legacy wireframe and optional HiFi manifest."""

    operations, errors = required_operations(prd)
    flows = wireframe.get("flows", [])
    for operation in operations:
        label = operation["id"]
        matches = [
            flow
            for flow in flows
            if flow.get("from") == operation["surface"]
            and flow.get("trigger") == operation["trigger"]
            and flow.get("sourceState") == operation["sourceState"]
            and flow.get("control") == operation["control"]
        ]
        if len(matches) != 1:
            errors.append(
                label + ": required operation is missing or ambiguous in Wireframe"
            )
        else:
            flow = matches[0]
            if flow.get("destination") != operation["destination"]:
                errors.append(label + ": Wireframe destination state differs from PRD")
            if flow.get("presentation") != operation["presentation"]:
                errors.append(
                    label + ": Wireframe presentation differs from PRD"
                )
            if operation["presentation"] in {"page", "overlay"} and (
                flow.get("to") != operation["destination"]["surface"]
            ):
                errors.append(label + ": Wireframe destination differs from PRD")
        if manifest is None:
            continue
        actions = [
            action
            for action in manifest.get("interactions", [])
            if action.get("source")
            == {
                "surface": operation["surface"],
                "state": operation["sourceState"],
            }
            and action.get("control") == operation["control"]
        ]
        if len(actions) != 1 or actions[0].get("destination") != operation[
            "destination"
        ]:
            errors.append(
                label + ": required HiFi control/destination differs from PRD"
            )
    if manifest is not None:
        declared = {
            (row["surface"], row["sourceState"], row["control"])
            for row in operations
        }
        for action in manifest.get("interactions", []):
            source = action.get("source", {})
            if (
                source.get("surface"),
                source.get("state"),
                action.get("control"),
            ) not in declared:
                errors.append(
                    "HiFi product interaction lacks a PRD operation: "
                    + str(action.get("id"))
                )
    return errors
