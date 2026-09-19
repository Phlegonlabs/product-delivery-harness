"""Validate observed motion in a HiFi projection, never native implementation."""
from __future__ import annotations

import math
from typing import Any


def motion_findings(value: Any, expected: dict[str, Any]) -> list[str]:
    """Check identity, actual preference mode and time-series observations."""
    errors: list[str] = []
    if not isinstance(value, dict) or set(value) != {
        "intent", "scope", "mode", "reducedMotion", "observations", "asset"
    }:
        return ["motion output requires typed identity, mode, observations and asset fields"]
    for key in ("intent", "scope", "mode"):
        if value[key] != expected[key]:
            errors.append(f"motion output {key} does not match the required intent")
    reduced = expected["mode"] == "reduced"
    if value["reducedMotion"] is not reduced:
        errors.append("motion output must record the actual reduced-motion preference")
    rows = value["observations"]
    if not isinstance(rows, list) or not rows:
        return errors + ["motion output requires observations at every responsive target"]
    targets = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "target", "state", "trigger", "endState", "samples", "fallbackObserved"
        }:
            errors.append("motion observation has invalid fields")
            continue
        targets.append(row["target"])
        if row["state"] not in expected["states"]:
            errors.append("motion observation state is outside the approved surface")
        for field in ("trigger", "endState"):
            if not isinstance(row[field], str) or row[field].strip().casefold() in {
                "", "none", "n/a", "tbd", "placeholder", "pass"
            }:
                errors.append(f"motion observation {field} must describe the observed behavior")
        if not isinstance(row["fallbackObserved"], bool) or (reduced and row["fallbackObserved"] is not True):
            errors.append("reduced motion must demonstrate the approved fallback")
        samples = row["samples"]
        if not isinstance(samples, list) or len(samples) < (2 if reduced else 3):
            errors.append("motion requires ordered before/during/after samples (two for reduced motion)")
            continue
        times = []
        values = []
        for sample in samples:
            if not isinstance(sample, dict) or set(sample) != {"atMs", "values"}:
                errors.append("motion sample has invalid fields")
                continue
            timestamp = sample["atMs"]
            props = sample["values"]
            if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) or (isinstance(timestamp, float) and not math.isfinite(timestamp)) or timestamp < 0:
                errors.append("motion sample time must be finite and nonnegative")
            else:
                times.append(timestamp)
            if not isinstance(props, dict) or not props or any(
                not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
                for k, v in props.items()
            ):
                errors.append("motion samples need nonempty observed property/value pairs")
            else:
                values.append(props)
        if any(a >= b for a, b in zip(times, times[1:])):
            errors.append("motion sample times must increase strictly")
        if values and any(set(v) != set(values[0]) for v in values):
            errors.append("motion samples must observe the same properties")
        if not reduced and values and all(v == values[0] for v in values):
            errors.append("normal motion samples show only a static placeholder")
    if sorted(map(str, targets)) != sorted(expected["targets"]) or any(not isinstance(t, str) for t in targets):
        errors.append("motion observations must exactly cover the responsive targets once")
    asset = value["asset"]
    if expected["assetRequired"] or asset is not None:
        if not isinstance(asset, dict) or set(asset) != {"path", "sha256", "authorization", "review"}:
            errors.append("generated or existing media requires a completed asset identity and review")
        elif any(not isinstance(asset[k], str) or not asset[k].strip() for k in asset) or asset["review"] != "approved" or asset["authorization"].strip().casefold() in {"deferred", "pending", "none", "n/a"}:
            errors.append("media asset authorization and completed review are required")
    return errors
