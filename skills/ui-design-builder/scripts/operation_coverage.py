"""Join explicit PRD operations to product controls in Wireframe and HiFi."""
from __future__ import annotations

import json
import re

from markdown_contract import active_markdown_lines
from prd_ui_contract import parse_prd_ui_contract, UI_START_MARKER, UI_END_MARKER


def required_operations(prd):
    surfaces, errors = parse_prd_ui_contract(prd, require_responsive=True, require_copy=True, web_floor=3)
    active = "\n".join(line for _, line in active_markdown_lines(prd))
    body = active.split(UI_START_MARKER, 1)[-1].split(UI_END_MARKER, 1)[0]
    headings = list(re.finditer(r"^### (UI-[A-Z0-9]+(?:-[A-Z0-9]+)*)\b.*$", body, re.M))
    result = []
    for index, heading in enumerate(headings):
        surface = heading.group(1)
        block = body[heading.end():headings[index + 1].start() if index + 1 < len(headings) else len(body)]
        values = re.findall(r"^\s*-\s*"+chr(96)+r"operations"+chr(96)+r"\s*:\s*(.+)$", block, re.M)
        if len(values) != 1:
            errors.append(surface + " requires one PRD operations anchor, including Home/back/cancel where required")
            continue
        if values[0].startswith("none — ") and len(values[0][7:].strip()) >= 12:
            continue
        try:
            operations = json.loads(values[0])
            if not isinstance(operations, list) or not operations:
                raise ValueError("operations must be a nonempty JSON list or none — <reason>")
            for operation in operations:
                if not isinstance(operation, dict) or set(operation) != {
                    "id", "trigger", "control", "sourceState", "destination", "presentation"
                }:
                    raise ValueError("operations require id, trigger, control, sourceState, destination and presentation")
                if any(not isinstance(operation[k], str) or not operation[k].strip()
                       for k in ("id", "trigger", "control", "sourceState", "presentation")):
                    raise ValueError("operation text fields must be nonempty")
                destination = operation["destination"]
                if not isinstance(destination, dict) or set(destination) != {"surface", "state"}:
                    raise ValueError("operation destination needs surface and state")
                if operation["sourceState"] not in surfaces.get(surface, {}).get("states", []):
                    raise ValueError("operation source state must be declared")
                target = surfaces.get(destination.get("surface"), {})
                if destination.get("state") not in target.get("states", []):
                    raise ValueError("operation destination must be a declared surface/state")
                if operation["presentation"] not in {"page", "overlay", "feedback", "state", "tab"}:
                    raise ValueError("operation presentation is unknown")
                result.append(dict(operation, surface=surface))
        except (ValueError, TypeError) as exc:
            errors.append(surface + ": " + str(exc))
    keys = [(row["surface"], row["control"], row["sourceState"]) for row in result]
    if len(keys) != len(set(keys)) or len({row["id"] for row in result}) != len(result):
        errors.append("PRD operations contain duplicate ids or control/source-state cases")
    return result, errors


def coverage_findings(prd, wireframe, manifest=None):
    operations, errors = required_operations(prd)
    flows = wireframe.get("flows", [])
    for operation in operations:
        label = operation["id"]
        matches = [flow for flow in flows if flow.get("from") == operation["surface"]
                   and flow.get("trigger") == operation["trigger"]
                   and flow.get("sourceState") == operation["sourceState"]
                   and flow.get("control") == operation["control"]]
        if len(matches) != 1:
            errors.append(label + ": required operation is missing or ambiguous in Wireframe")
        else:
            flow = matches[0]
            if flow.get("destination") != operation["destination"]:
                errors.append(label + ": Wireframe destination state differs from PRD")
            if flow.get("presentation") != operation["presentation"]:
                errors.append(label + ": Wireframe presentation differs from PRD")
            if operation["presentation"] in {"page", "overlay"} and (
                flow.get("to") != operation["destination"]["surface"]
            ):
                errors.append(label + ": Wireframe destination differs from PRD")
        if manifest is None:
            continue
        actions = [action for action in manifest.get("interactions", [])
                   if action.get("source") == {"surface": operation["surface"], "state": operation["sourceState"]}
                   and action.get("control") == operation["control"]]
        if len(actions) != 1 or actions[0].get("destination") != operation["destination"]:
            errors.append(label + ": required HiFi control/destination differs from PRD")
    if manifest is not None:
        declared = {(row["surface"], row["sourceState"], row["control"]) for row in operations}
        for action in manifest.get("interactions", []):
            source = action.get("source", {})
            if (source.get("surface"), source.get("state"), action.get("control")) not in declared:
                errors.append("HiFi product interaction lacks a PRD operation: " + str(action.get("id")))
    return errors
