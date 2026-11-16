"""Join explicit PRD operations to product controls in Wireframe and HiFi."""
from __future__ import annotations

from prd_operations import required_operations  # re-export for legacy callers


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


def hifi_coverage_findings(prd, manifest):
    """Join explicit PRD operations directly to the ui-hifi/2 manifest.

    This is the cheap wireframe-free preflight.  It does not infer an omitted
    operation from prose or use reviewer chrome as a product control.  The
    manifest's ``kind`` is intentionally narrower than the PRD's presentation:
    A page transition navigates. Other operations use feedback for equal
    endpoints and state for different endpoints.
    """

    operations, errors = required_operations(prd)
    actions = manifest.get("interactions", []) if isinstance(manifest, dict) else []
    if not isinstance(actions, list):
        errors.append("HiFi manifest interactions must be an array")
        actions = []
    def matches(operation, action):
        if not isinstance(action, dict):
            return False
        source = action.get("source")
        return (
            isinstance(source, dict)
            and source.get("surface") == operation["surface"]
            and source.get("state") == operation["sourceState"]
            and action.get("control") == operation["control"]
        )

    for operation in operations:
        exact = [action for action in actions if matches(operation, action)]
        label = operation["id"]
        if len(exact) != 1:
            errors.append(label + ": required operation is missing or ambiguous in HiFi")
            continue
        action = exact[0]
        if action.get("id") != operation["id"]:
            errors.append(label + ": HiFi operation ID differs from PRD")
        if action.get("destination") != operation["destination"]:
            errors.append(label + ": HiFi destination state differs from PRD")
        source = {"surface": operation["surface"], "state": operation["sourceState"]}
        expected_kind = ("navigate" if operation["presentation"] == "page" else
                         "feedback" if source == operation["destination"] else "state")
        if action.get("kind") != expected_kind:
            errors.append(
                label + ": HiFi interaction kind does not represent PRD presentation "
                + operation["presentation"]
            )
    declared = {
        (row["surface"], row["sourceState"], row["control"])
        for row in operations
    }
    for action in actions:
        if not isinstance(action, dict):
            errors.append("HiFi manifest interaction must be an object")
            continue
        source = action.get("source")
        key = (
            source.get("surface") if isinstance(source, dict) else None,
            source.get("state") if isinstance(source, dict) else None,
            action.get("control"),
        )
        if key not in declared:
            errors.append("HiFi product interaction lacks a PRD operation: " + str(action.get("id")))
    return errors
