"""Validate frozen execution context and per-assertion observations."""


CONTEXT_KEYS = {"target", "device", "os", "persona", "initial_data", "actions",
                "assertions", "expected_side_effects", "dependency_mode"}
PERSONA_KEYS = {"role", "tenant", "account_state"}


def concrete_text(item):
    return (isinstance(item, str) and bool(item.strip())
            and not (item.strip().startswith("<") and item.strip().endswith(">"))
            and item.strip().lower() not in {"tbd", "todo", "pending", "placeholder",
                                             "n/a", "none", "unknown", "not applicable"})


def execution(value, path, errors):
    def text(item, label):
        if not concrete_text(item):
            errors.append(f"{label} needs concrete non-secret text")

    if not isinstance(value, dict) or set(value) != CONTEXT_KEYS:
        errors.append(f"{path} has invalid execution fields")
        return value
    for key in CONTEXT_KEYS - {"persona", "actions", "assertions"}:
        text(value[key], f"{path}.{key}")
    persona = value["persona"]
    if not isinstance(persona, dict) or set(persona) != PERSONA_KEYS:
        errors.append(f"{path}.persona requires role, tenant and account_state")
    else:
        for key in PERSONA_KEYS:
            text(persona[key], f"{path}.persona.{key}")
    actions = value["actions"]
    if not isinstance(actions, list) or not actions:
        errors.append(f"{path}.actions must be a nonempty list")
    else:
        for action in actions:
            text(action, f"{path}.actions")
    assertions = value["assertions"]
    if not isinstance(assertions, dict) or not assertions:
        errors.append(f"{path}.assertions must map stable assertion IDs to expected signals")
    else:
        for key, signal in assertions.items():
            text(key, f"{path}.assertions ID")
            text(signal, f"{path}.assertions signal")
    return value


def observations(row, expected, path, errors):
    assertions = expected.get("execution", {}).get("assertions", {})
    observed = row.get("assertion_results")
    if not isinstance(observed, dict) or set(observed) != set(assertions):
        errors.append(f"{path}.assertion_results must cover every frozen assertion exactly")
    elif any(not isinstance(status, str) or status not in {
            "pass", "fail", "blocked", "skipped", "unvalidated"} for status in observed.values()):
        errors.append(f"{path}.assertion_results contains an invalid status")
    elif row.get("status") == "pass" and any(status != "pass" for status in observed.values()):
        errors.append(f"{path}.assertion_results contains a non-passing assertion")
    cleanup = "cleaned" if expected.get("fixtures") else "not_required"
    allowed = {cleanup} if row.get("status") == "pass" else {cleanup, "pending", "failed"}
    if not isinstance(row.get("fixture_cleanup"), str) or row["fixture_cleanup"] not in allowed:
        errors.append(f"{path}.fixture_cleanup must be {cleanup}; retain cleanup evidence")
