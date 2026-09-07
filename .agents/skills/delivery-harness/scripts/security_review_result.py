#!/usr/bin/env python3
"""Validate the structured result of one code-security review."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DECISIONS = {
    "pass",
    "fix_required",
    "blocked",
    "contract_gap",
    "retryable_failure",
}
TOOL_STATUSES = {"passed", "findings", "skipped", "unavailable"}
COVERAGE_STATUSES = {"complete", "partial"}
SEVERITIES = {"critical", "high", "medium", "low"}
CONFIDENCES = {"high", "medium", "low"}
RESULT_KEYS = {
    "review_type",
    "decision",
    "reviewed_sha",
    "base_sha",
    "scope",
    "exclusions",
    "trust_boundaries",
    "tools",
    "coverage",
    "findings",
    "evidence",
}
TOOL_KEYS = {"name", "status", "evidence"}
COVERAGE_KEYS = {"status", "reviewed", "gaps"}
FINDING_KEYS = {
    "severity",
    "confidence",
    "cwe",
    "location",
    "summary",
    "source_to_sink",
    "preconditions",
    "impact",
    "counterevidence",
    "remediation",
    "remediation_test",
}


class SecurityReviewResultError(ValueError):
    """Raised when a result file is unreadable or contains duplicate keys."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SecurityReviewResultError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_security_review_result(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    try:
        value = json.loads(
            target.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SecurityReviewResultError(
            f"cannot read security review result {target}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise SecurityReviewResultError("security review result must be an object")
    return value


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_string_list(
    errors: list[str],
    path: str,
    value: Any,
    *,
    nonempty: bool = False,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{path}: must be a list")
        return []
    valid = [
        item
        for item in value
        if _is_nonempty_string(item)
    ]
    if len(valid) != len(value):
        errors.append(f"{path}: values must be non-empty strings")
    if len(valid) != len(set(valid)):
        errors.append(f"{path}: values must be unique")
    if nonempty and not valid:
        errors.append(f"{path}: must not be empty")
    return valid


def validate_security_review_result(
    value: Any,
    *,
    expected_decision: str | None = None,
    expected_reviewed_sha: str | None = None,
    expected_base_sha: str | None = None,
    expected_scope: Iterable[str] | None = None,
    required_tools: Iterable[str] = (),
    allowed_decisions: Iterable[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["security_review_result: must be an object"]
    missing = sorted(RESULT_KEYS - set(value))
    extra = sorted(set(value) - RESULT_KEYS)
    if missing:
        errors.append(
            "security_review_result: missing keys: " + ", ".join(missing)
        )
    if extra:
        errors.append(
            "security_review_result: unexpected keys: " + ", ".join(extra)
        )
    if missing:
        return errors

    if value["review_type"] != "security":
        errors.append("security_review_result.review_type: must equal security")
    decision = value["decision"]
    allowed = set(allowed_decisions) if allowed_decisions is not None else DECISIONS
    if not isinstance(decision, str) or decision not in DECISIONS or decision not in allowed:
        errors.append("security_review_result.decision: is not allowed")
    if expected_decision is not None and decision != expected_decision:
        errors.append(
            "security_review_result.decision: must match the recorded review outcome"
        )

    reviewed_sha = value["reviewed_sha"]
    if not isinstance(reviewed_sha, str) or SHA_RE.fullmatch(reviewed_sha) is None:
        errors.append("security_review_result.reviewed_sha: must be a full lowercase SHA")
    elif expected_reviewed_sha is not None and reviewed_sha != expected_reviewed_sha:
        errors.append(
            "security_review_result.reviewed_sha: must match the reserved reviewed SHA"
        )
    base_sha = value["base_sha"]
    if base_sha is not None and (
        not isinstance(base_sha, str) or SHA_RE.fullmatch(base_sha) is None
    ):
        errors.append("security_review_result.base_sha: must be null or a full lowercase SHA")
    elif expected_base_sha is not None and base_sha != expected_base_sha:
        errors.append(
            "security_review_result.base_sha: must match the dispatched base SHA"
        )

    scope = _validate_string_list(
        errors, "security_review_result.scope", value["scope"], nonempty=True
    )
    if expected_scope is not None and scope != list(expected_scope):
        errors.append(
            "security_review_result.scope: must exactly match the PLAN review scope"
        )
    _validate_string_list(
        errors, "security_review_result.exclusions", value["exclusions"]
    )
    trust_boundaries = _validate_string_list(
        errors,
        "security_review_result.trust_boundaries",
        value["trust_boundaries"],
    )
    evidence = _validate_string_list(
        errors,
        "security_review_result.evidence",
        value["evidence"],
        nonempty=True,
    )

    tools = value["tools"]
    tool_statuses: dict[str, str] = {}
    if not isinstance(tools, list):
        errors.append("security_review_result.tools: must be a list")
    else:
        for index, tool in enumerate(tools):
            path = f"security_review_result.tools[{index}]"
            if not isinstance(tool, dict) or set(tool) != TOOL_KEYS:
                errors.append(f"{path}: must contain exactly name, status, and evidence")
                continue
            if not _is_nonempty_string(tool["name"]):
                errors.append(f"{path}.name: must be a non-empty string")
                continue
            if tool["name"] in tool_statuses:
                errors.append(f"{path}.name: must be unique")
            tool_status = tool["status"]
            if not isinstance(tool_status, str) or tool_status not in TOOL_STATUSES:
                errors.append(f"{path}.status: has an unsupported value")
            if not _is_nonempty_string(tool["evidence"]):
                errors.append(f"{path}.evidence: must be a non-empty string")
            tool_statuses[tool["name"]] = (
                tool_status if isinstance(tool_status, str) else "invalid"
            )

    coverage = value["coverage"]
    reviewed_surfaces: list[str] = []
    coverage_gaps: list[str] = []
    if not isinstance(coverage, dict) or set(coverage) != COVERAGE_KEYS:
        errors.append(
            "security_review_result.coverage: must contain exactly status, reviewed, and gaps"
        )
    else:
        if (
            not isinstance(coverage["status"], str)
            or coverage["status"] not in COVERAGE_STATUSES
        ):
            errors.append("security_review_result.coverage.status: has an unsupported value")
        reviewed_surfaces = _validate_string_list(
            errors,
            "security_review_result.coverage.reviewed",
            coverage["reviewed"],
        )
        coverage_gaps = _validate_string_list(
            errors,
            "security_review_result.coverage.gaps",
            coverage["gaps"],
        )
        if coverage["status"] == "complete" and coverage_gaps:
            errors.append(
                "security_review_result.coverage.gaps: complete coverage cannot retain gaps"
            )
        if coverage["status"] == "partial" and not coverage_gaps:
            errors.append(
                "security_review_result.coverage.gaps: partial coverage requires a gap"
            )

    findings = value["findings"]
    severities: list[str] = []
    if not isinstance(findings, list):
        errors.append("security_review_result.findings: must be a list")
        findings = []
    for index, finding in enumerate(findings):
        path = f"security_review_result.findings[{index}]"
        if not isinstance(finding, dict) or set(finding) != FINDING_KEYS:
            errors.append(f"{path}: has an invalid field set")
            continue
        severity = finding["severity"]
        if not isinstance(severity, str) or severity not in SEVERITIES:
            errors.append(f"{path}.severity: has an unsupported value")
        else:
            severities.append(severity)
        if (
            not isinstance(finding["confidence"], str)
            or finding["confidence"] not in CONFIDENCES
        ):
            errors.append(f"{path}.confidence: has an unsupported value")
        if finding["cwe"] is not None and not _is_nonempty_string(finding["cwe"]):
            errors.append(f"{path}.cwe: must be null or a non-empty string")
        for key in FINDING_KEYS - {"severity", "confidence", "cwe"}:
            if not _is_nonempty_string(finding[key]):
                errors.append(f"{path}.{key}: must be a non-empty string")

    required_tool_names = set(required_tools)
    missing_tools = sorted(required_tool_names - set(tool_statuses))
    if missing_tools:
        errors.append(
            "security_review_result.tools: missing required tools: "
            + ", ".join(missing_tools)
        )
    unusable_tools = sorted(
        name
        for name in required_tool_names
        if tool_statuses.get(name) in {"skipped", "unavailable"}
    )
    if unusable_tools:
        errors.append(
            "security_review_result.tools: required tools did not run: "
            + ", ".join(unusable_tools)
        )

    if decision == "pass":
        if not isinstance(coverage, dict) or coverage.get("status") != "complete":
            errors.append("security_review_result.coverage.status: PASS requires complete")
        if not reviewed_surfaces:
            errors.append("security_review_result.coverage.reviewed: PASS requires coverage")
        if not trust_boundaries:
            errors.append(
                "security_review_result.trust_boundaries: PASS requires at least one boundary"
            )
        if not tool_statuses:
            errors.append("security_review_result.tools: PASS requires review evidence")
        if isinstance(reviewed_sha, str) and not any(
            reviewed_sha in item for item in evidence
        ):
            errors.append(
                "security_review_result.evidence: PASS must name the reviewed SHA"
            )
        if any(item in {"critical", "high"} for item in severities):
            errors.append(
                "security_review_result.findings: PASS cannot retain critical or high findings"
            )
    elif decision == "fix_required" and not findings:
        errors.append(
            "security_review_result.findings: fix_required needs a validated finding"
        )

    return sorted(set(errors))


def security_result_finding_summaries(value: dict[str, Any]) -> list[str]:
    if value.get("decision") == "pass":
        return []
    findings = value.get("findings")
    if isinstance(findings, list) and findings:
        return [
            f"{item['severity']} {item['location']}: {item['summary']}"
            for item in findings
            if isinstance(item, dict)
            and _is_nonempty_string(item.get("severity"))
            and _is_nonempty_string(item.get("location"))
            and _is_nonempty_string(item.get("summary"))
        ]
    coverage = value.get("coverage")
    gaps = coverage.get("gaps") if isinstance(coverage, dict) else None
    if isinstance(gaps, list) and gaps:
        return [item for item in gaps if _is_nonempty_string(item)]
    evidence = value.get("evidence")
    return [item for item in evidence if _is_nonempty_string(item)][:1]
