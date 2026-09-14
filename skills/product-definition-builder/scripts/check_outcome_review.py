#!/usr/bin/env python3
"""Strict read-only validation for a completed outcome-review.md record."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SIBLING_SCRIPTS_ROOT = SCRIPTS_DIR.parents[1]
ACTIVATION_SCRIPTS = SIBLING_SCRIPTS_ROOT / "product-activation" / "scripts"
DELIVERY_SCRIPTS = SIBLING_SCRIPTS_ROOT / "delivery-harness" / "scripts"
for sibling_scripts in (ACTIVATION_SCRIPTS, DELIVERY_SCRIPTS):
    if str(sibling_scripts) not in sys.path:
        sys.path.insert(0, str(sibling_scripts))

from check_activation import _table, check_activation_text  # noqa: E402
from check_deployment import parse_release_target_status  # noqa: E402
from markdown_contract import active_text, is_human_owner  # noqa: E402
from release_targets import allows_no_independent_artifact, parse_release_targets  # noqa: E402
from contract_utils import product_identity, safe_read_text  # noqa: E402


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MS_ID_RE = re.compile(r"^MS-[0-9]{3}$")
VERDICTS = {"no_change", "enhancement", "incident"}
REQUIRED_SECTIONS = (
    "## Record",
    "## Activation Sources",
    "## Measurements",
    "## Feedback",
    "## Incident Response",
    "## Verdict",
    "## Open Follow-ups",
)
RECORD_FIELDS = (
    "Schema",
    "Product",
    "Outcome owner",
    "Production release target",
    "Release SHA",
    "Artifact / build identity",
    "Deployment identity",
    "Deployment checked",
    "Deployment status",
    "Activation record",
    "Activation sha256",
    "Reviewed on",
    "Verdict",
)
MEASUREMENT_HEADERS = (
    "signal",
    "baseline",
    "target",
    "window start",
    "window end",
    "actual",
    "source id",
)
SOURCE_HEADERS = (
    "ms id",
    "release binding",
    "owner",
    "verified at",
    "evidence",
)
TARGET_REVIEW_HEADERS = (
    "release target",
    "release sha",
    "artifact / build identity",
    "deployment identity",
    "deployment checked",
    "deployment status",
    "activation sources",
    "verdict",
)
TARGET_MEASUREMENT_HEADERS = (
    "signal",
    "release target",
    "baseline",
    "target",
    "window start",
    "window end",
    "actual",
    "source id",
)
FEEDBACK_HEADERS = ("fact", "source id", "observed")
TARGET_FEEDBACK_HEADERS = ("fact", "release target", "source id", "observed")
INCIDENT_HEADERS = (
    "incident",
    "containment",
    "human owner",
    "prd risk routing",
    "prd open question routing",
    "evidence",
)
TARGET_INCIDENT_HEADERS = (
    "incident",
    "release target",
    "containment",
    "human owner",
    "prd risk routing",
    "prd open question routing",
    "evidence",
)
FOLLOWUP_HEADERS = ("follow-up", "route")
VERDICT_HISTORY_HEADERS = (
    "prior outcome sha256",
    "verdict",
    "verdict section sha256",
    "verdict reason",
)
VERDICT_HISTORY_NONE = ("none", "none", "none", "none")
FOLLOWUP_ROUTES = {"enhancement request", "open question", "risk", "none"}
ABSENT = {"", "none", "n/a", "pending"}
NO_INDEPENDENT_ARTIFACT_VALUES = {
    "no independent artifact",
    "no-independent-artifact",
}
CONTAINMENT_TYPES = {
    "rollout halted",
    "rollback",
    "forward fix",
    "feature disabled",
    "traffic reduced",
    "access revoked",
    "monitoring only",
}
SOURCE_ROLES = {
    "search_console",
    "ga4",
    "production_page",
    "google_trends",
    "keyword_planner",
    "public_serp",
    "first_party",
}


def _human(owner: str) -> bool:
    return is_human_owner(owner)


def _section(text: str, heading: str) -> list[str] | None:
    lines = active_text(text).splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return None
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return lines[start + 1 : end]


def _fields(lines: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^-\s*([^:\n]+):\s*(.*)$", line.strip())
        if match:
            result[match.group(1).strip()] = match.group(2).strip()
    return result


def _duplicate_fields(lines: list[str]) -> list[str]:
    names = [
        match.group(1).strip().casefold()
        for line in lines
        if (match := re.match(r"^-\s*([^:\n]+):\s*", line.strip()))
    ]
    return sorted(name for name, count in Counter(names).items() if count > 1)


IMMUTABLE_HISTORY_SECTIONS = (
    "## Activation Sources",
    "## Measurements",
    "## Target Reviews",
    "## Target Measurements",
    "## Feedback",
    "## Incident Response",
    "## Open Follow-ups",
)


def _raw_table_rows(text: str, heading: str) -> list[str]:
    """Return active table data rows exactly as authored, excluding header/separator."""

    section = _section(text, heading)
    if section is None:
        return []
    table_lines = [line.strip() for line in section if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return []
    return [
        line
        for line in table_lines[1:]
        if not all(set(cell.strip()) <= {"-", ":", " "} for cell in line.strip("|").split("|"))
    ]


def _row_values(raw_row: str) -> tuple[str, ...]:
    """Return normalized cells for one raw Markdown table row."""

    return tuple(cell.strip() for cell in raw_row.strip().strip("|").split("|"))


def _schema(text: str) -> str:
    return _fields(_section(text, "## Record") or []).get("Schema", "")


def _authoritative_verdict(text: str) -> tuple[str, str, str] | None:
    """Return (verdict, reason, canonical Verdict-section SHA-256)."""

    section = _section(text, "## Verdict")
    if section is None:
        return None
    body = "\n".join(line.rstrip() for line in section).strip()
    match = re.fullmatch(r"Verdict:\s*(\S+)\s*—\s*(.+)", body)
    if match is None:
        return None
    verdict, reason = match.group(1), match.group(2).strip()
    canonical = f"## Verdict\n{body}"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return verdict, reason, digest


def _history_data_rows(text: str) -> list[str]:
    """Return meaningful Verdict History rows, excluding its typed empty marker."""

    rows = _raw_table_rows(text, "## Verdict History")
    if len(rows) == 1 and _row_values(rows[0]) == VERDICT_HISTORY_NONE:
        return []
    return rows


def _verdict_history_findings(text: str, record: dict[str, str]) -> list[str]:
    """Validate the schema-2 typed prior-verdict history table."""

    findings: list[str] = []
    section = _section(text, "## Verdict History")
    if section is None:
        return ["Verdict History: schema outcome-review/2 requires this section"]
    rows, header_ok = _rows(text, "## Verdict History", VERDICT_HISTORY_HEADERS)
    if not header_ok:
        findings.append(
            "Verdict History: expected columns " + " | ".join(VERDICT_HISTORY_HEADERS)
        )
    if not rows:
        findings.append(
            "Verdict History: requires one row; use the exact none placeholder when no prior outcome exists"
        )
    seen_prior: set[str] = set()
    placeholder_rows = 0
    meaningful_rows: list[list[str]] = []
    for index, row in enumerate(rows, start=1):
        if len(row) != len(VERDICT_HISTORY_HEADERS):
            findings.append(
                f"Verdict History: row {index} must have the exact column count"
            )
            continue
        if tuple(cell.casefold() for cell in row) == VERDICT_HISTORY_NONE:
            placeholder_rows += 1
            if len(rows) != 1:
                findings.append(
                    "Verdict History: the none placeholder cannot be mixed with history rows"
                )
            continue
        meaningful_rows.append(row)
        if any(
            cell.casefold() in ABSENT
            or cell.strip().startswith(("<", "["))
            or cell.strip().endswith((">", "]"))
            for cell in row
        ):
            findings.append(f"Verdict History: row {index} contains a placeholder cell")
        prior_sha, verdict, section_sha, reason = row
        if not SHA256_RE.fullmatch(prior_sha):
            findings.append(
                f"Verdict History: row {index} prior outcome sha256 must be 64 lowercase hex characters"
            )
        elif prior_sha in seen_prior:
            findings.append(
                f"Verdict History: duplicate prior outcome identity {prior_sha}"
            )
        seen_prior.add(prior_sha)
        if verdict not in VERDICTS:
            findings.append(f"Verdict History: row {index} has invalid verdict {verdict!r}")
        if not SHA256_RE.fullmatch(section_sha):
            findings.append(
                f"Verdict History: row {index} verdict section sha256 must be 64 lowercase hex characters"
            )
        if not reason.strip() or "|" in reason:
            findings.append(f"Verdict History: row {index} needs one authoritative verdict reason")
    if placeholder_rows and meaningful_rows:
        findings.append("Verdict History: empty placeholder cannot accompany meaningful rows")
    if placeholder_rows > 1:
        findings.append("Verdict History: duplicate none placeholder rows")
    if meaningful_rows:
        prior_digest = record.get("Prior outcome sha256", "")
        if prior_digest != meaningful_rows[-1][0]:
            findings.append(
                "Verdict History: the last row must match Record Prior outcome sha256"
            )
    elif record.get("Prior outcome sha256", "").strip():
        findings.append(
            "Verdict History: Record Prior outcome sha256 requires a meaningful history row"
        )
    # The history must be established before the current authoritative verdict.
    active_lines = active_text(text).splitlines()
    try:
        history_index = next(i for i, line in enumerate(active_lines) if line.strip() == "## Verdict History")
        verdict_index = next(i for i, line in enumerate(active_lines) if line.strip() == "## Verdict")
        if history_index > verdict_index:
            findings.append("Verdict History: section must appear before the current Verdict section")
    except StopIteration:
        pass
    return findings


def prior_append_findings(prior_text: str, current_text: str) -> list[str]:
    """Enforce append-only preservation of a prior outcome's historical rows."""

    findings: list[str] = []
    schema2_history = (
        _schema(prior_text) == "outcome-review/2"
        or _schema(current_text) == "outcome-review/2"
    )
    if schema2_history and _schema(current_text) != "outcome-review/2":
        findings.append(
            "Prior outcome: --prior-outcome appends require current Schema outcome-review/2"
        )

    # Every retained outcome family is immutable in both schema versions.  Keep
    # this pass outside the typed Verdict History branch so schema-2 cannot
    # bypass target/source/measurement/follow-up preservation.
    for heading in IMMUTABLE_HISTORY_SECTIONS:
        prior_rows = _raw_table_rows(prior_text, heading)
        if not prior_rows:
            continue
        current_rows = _raw_table_rows(current_text, heading)
        if len(current_rows) < len(prior_rows):
            findings.append(f"Prior outcome: {heading} deleted historical row(s)")
            continue
        if current_rows[: len(prior_rows)] != prior_rows:
            findings.append(
                f"Prior outcome: {heading} historical rows must remain byte-identical and ordered"
            )

    if schema2_history and _schema(current_text) == "outcome-review/2":
        if _schema(prior_text) == "outcome-review/2":
            prior_record = _fields(_section(prior_text, "## Record") or [])
            findings.extend(
                f"Prior outcome: {item}"
                for item in _verdict_history_findings(prior_text, prior_record)
            )
        prior_rows = _history_data_rows(prior_text)
        current_rows = _history_data_rows(current_text)
        if len(current_rows) < len(prior_rows):
            findings.append("Prior outcome: Verdict History deleted historical row(s)")
        elif current_rows[: len(prior_rows)] != prior_rows:
            findings.append(
                "Prior outcome: Verdict History historical rows must remain byte-identical and ordered"
            )
        prior_details = _authoritative_verdict(prior_text)
        if prior_details is None:
            findings.append(
                "Prior outcome: prior record must contain one authoritative Verdict section"
            )
        else:
            prior_digest = hashlib.sha256(prior_text.encode("utf-8")).hexdigest()
            verdict, reason, section_digest = prior_details
            expected = f"| {prior_digest} | {verdict} | {section_digest} | {reason} |"
            if len(current_rows) != len(prior_rows) + 1:
                findings.append(
                    "Prior outcome: Verdict History must append exactly one derived row for the immediate prior record"
                )
            elif current_rows[-1] != expected:
                findings.append(
                    "Prior outcome: Verdict History last row must match the prior outcome digest and authoritative Verdict section"
                )
    elif not schema2_history:
        prior_verdict = _authoritative_verdict(prior_text)
        current_verdict_lines = {
            line.strip()
            for line in (_section(current_text, "## Verdict") or [])
            if line.strip().startswith("Verdict:")
        }
        if prior_verdict is not None and f"Verdict: {prior_verdict[0]} — {prior_verdict[1]}" not in current_verdict_lines:
            findings.append("Prior outcome: prior verdict history must remain present")
    return findings


def _rows(text: str, heading: str, expected: tuple[str, ...]) -> tuple[list[list[str]], bool]:
    section = _section(text, heading)
    if section is None:
        return [], False
    table = [line for line in section if line.strip().startswith("|")]
    if not table:
        return [], False
    cells = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in table]
    header = [cell.lower() for cell in cells[0]]
    data = [row for row in cells[1:] if not all(set(cell) <= {"-", ":", " "} for cell in row)]
    return data, tuple(header) == expected


def _valid_date(value: str) -> bool:
    if not DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _timestamp(value: str) -> datetime | None:
    if not RFC3339_RE.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _not_future(value: datetime | None) -> bool:
    return value is not None and value <= datetime.now(timezone.utc)


def _duration_days(value: str) -> int | None:
    match = re.fullmatch(r"\s*(\d+)\s*(day|days|week|weeks)\s*", value, re.I)
    if match is None or int(match.group(1)) <= 0:
        return None
    return int(match.group(1)) * (7 if match.group(2).casefold().startswith("week") else 1)


def _activation_sources(
    activation_text: str,
    target: str,
    sha: str,
    artifact: str,
    *,
    allow_other_bindings: bool = False,
) -> tuple[dict[str, dict[str, object]], list[str]]:
    header, rows = _table(activation_text, "## Measurement Sources")
    findings: list[str] = []
    expected_header = [
        "ms id",
        "target",
        "environment",
        "retrieval",
        "source role",
        "route / capability",
        "release bindings",
        "owner",
        "status",
        "evidence ids",
    ]
    if header != expected_header:
        return {}, ["Activation: Measurement Sources table is missing or invalid"]
    evidence_header, evidence_rows = _table(activation_text, "## Verification Evidence")
    expected_evidence_header = [
        "evidence id",
        "item id",
        "kind",
        "route / action / release binding",
        "checked",
        "result",
        "reference",
    ]
    if evidence_header != expected_evidence_header:
        return {}, ["Activation: Verification Evidence table is missing or invalid"]
    evidence_by_id: dict[str, dict[str, object]] = {}
    for row in evidence_rows:
        if len(row) != len(expected_evidence_header):
            continue
        evidence_id, item_id, kind, binding_text, checked, result, _reference = row
        parts = [part.strip() for part in binding_text.split(";")]
        if len(parts) != 3:
            continue
        evidence_by_id[evidence_id] = {
            "item_id": item_id,
            "kind": kind,
            "binding": parts[2],
            "checked": checked,
            "checked_at": _timestamp(checked),
            "result": result,
        }
    result: dict[str, dict[str, object]] = {}
    expected_binding = f"{target}@{sha}#{artifact}"
    for row in rows:
        if len(row) != 10:
            continue
        source_id, source_target, _environment, _retrieval, source_role, _route_capability, bindings, owner, status, evidence_ids = row
        if status != "verified" or expected_binding not in {
            item.strip() for item in bindings.split(",")
        }:
            continue
        if source_role not in SOURCE_ROLES:
            findings.append(f"Activation: {source_id} has invalid source role {source_role!r}")
        parsed_evidence_ids = [item.strip() for item in evidence_ids.split(",") if item.strip()]
        pass_evidence: list[dict[str, object]] = []
        for evidence_id in parsed_evidence_ids:
            item = evidence_by_id.get(evidence_id)
            if item is None:
                findings.append(f"Activation: {source_id} references missing evidence {evidence_id}")
                continue
            if item["item_id"] != source_id:
                findings.append(f"Activation: {source_id} evidence {evidence_id} belongs to another item")
            if item["binding"] != expected_binding and not allow_other_bindings:
                findings.append(f"Activation: {source_id} evidence {evidence_id} has a mismatched release binding")
            if item["binding"] != expected_binding and allow_other_bindings:
                continue
            if item["result"] == "PASS" and item["kind"] in {"readback", "behavior"}:
                pass_evidence.append(item)
        latest_pass = max(
            (item["checked_at"] for item in pass_evidence if isinstance(item["checked_at"], datetime)),
            default=None,
        )
        if latest_pass is None:
            findings.append(f"Activation: {source_id} needs a latest PASS readback or behavior evidence")
        result[source_id] = {
            "owner": owner,
            "source_role": source_role,
            "evidence_ids": tuple(parsed_evidence_ids),
            "latest_pass": latest_pass,
            "binding": expected_binding,
        }
    return result, findings


def _multi_target_findings(
    text: str,
    *,
    target_ids: list[str],
    contract: object,
    prd_text: str,
    architecture_text: str,
    deployment_text: str,
    activation_text: str,
    deployment_rows: dict[str, dict[str, str]],
    reviewed_on: str,
    aggregate_verdict: str,
) -> list[str]:
    """Validate ordered per-target reviews and target-bound measurements.

    The original schema remains single-target compatible.  A multi-target
    review opts in by adding ``Production release targets`` plus these two
    tables; every target keeps its own release/deployment/source identity and
    every signal is repeated with an explicit target binding.
    """

    findings: list[str] = []
    target_map = contract.by_id()  # type: ignore[attr-defined]
    target_rows, target_header_ok = _rows(text, "## Target Reviews", TARGET_REVIEW_HEADERS)
    if not target_header_ok:
        findings.append(
            "Target Reviews: expected columns " + " | ".join(TARGET_REVIEW_HEADERS)
        )
        target_rows = []
    seen_targets: list[str] = []
    target_verdicts: list[str] = []
    target_verdict_map: dict[str, str] = {}
    target_sources: dict[str, set[str]] = {}
    target_bindings: dict[str, str] = {}
    for row in target_rows:
        if len(row) != len(TARGET_REVIEW_HEADERS):
            findings.append("Target Reviews: each row must have the exact column count")
            continue
        target_id, sha, artifact, deployment_identity, checked, status, source_ids, verdict = row
        if target_id in seen_targets:
            findings.append(f"Target Reviews: duplicate release target {target_id}")
            continue
        seen_targets.append(target_id)
        target = target_map.get(target_id)
        if target is None:
            findings.append(f"Target Reviews: {target_id} is not an architecture target")
            continue
        if target.stage != "production":
            findings.append(f"Target Reviews: {target_id} must be a production target")
        if not SHA_RE.fullmatch(sha):
            findings.append(f"Target Reviews: {target_id} needs a full lowercase release SHA")
        if artifact.lower() in ABSENT and not _artifact_allows_na(target):
            findings.append(f"Target Reviews: {target_id} needs an artifact/build identity")
        if status != "PASS":
            findings.append(f"Target Reviews: {target_id} deployment must be PASS")
        if verdict not in VERDICTS:
            findings.append(f"Target Reviews: {target_id} has invalid verdict {verdict!r}")
        else:
            target_verdicts.append(verdict)
            target_verdict_map[target_id] = verdict
        deployment = deployment_rows.get(target_id)
        if deployment is None:
            findings.append(f"Target Reviews: deployment is missing {target_id}")
        else:
            expected_identity = f"{target.release_name};{target.channel};{artifact}"
            if deployment["expected sha"] != sha or deployment["deployed sha"] != sha:
                findings.append(f"Target Reviews: {target_id} deployment SHA does not match")
            if deployment["artifact / build identity"] != artifact:
                findings.append(f"Target Reviews: {target_id} artifact does not match deployment")
            if deployment["status"] != "PASS":
                findings.append(f"Target Reviews: {target_id} deployment status is not PASS")
            if checked != deployment["checked"]:
                findings.append(f"Target Reviews: {target_id} checked time differs from deployment")
            if deployment_identity != expected_identity:
                findings.append(
                    f"Target Reviews: {target_id} deployment identity must be {expected_identity!r}"
                )
        matching, source_findings = _activation_sources(
            activation_text,
            target_id,
            sha,
            artifact,
            allow_other_bindings=True,
        )
        findings.extend(f"Target Reviews {target_id}: {item}" for item in source_findings)
        listed = {item.strip() for item in source_ids.split(",") if item.strip()}
        if listed != set(matching):
            findings.append(
                f"Target Reviews: {target_id} activation sources must exactly match verified sources"
            )
        target_sources[target_id] = set(matching)
        target_bindings[target_id] = f"{target_id}@{sha}#{artifact}"
        target_findings = check_activation_text(
            activation_text,
            prd_text=prd_text,
            architecture_text=architecture_text,
            deployment_text=deployment_text,
            require_verified_sources=True,
            require_ready=(target_id,),
        )
        findings.extend(f"Activation {target_id}: {item}" for item in target_findings)

    if seen_targets != target_ids:
        findings.append(
            "Target Reviews: ordered targets must exactly match `Production release targets`"
        )
    severity = {"no_change": 0, "enhancement": 1, "incident": 2}
    if target_verdicts:
        expected_aggregate = max(target_verdicts, key=lambda item: severity[item])
        if aggregate_verdict != expected_aggregate:
            findings.append(
                f"Target Reviews: aggregate verdict must be deterministic {expected_aggregate!r}"
            )

    incident_rows, incident_header_ok = _rows(text, "## Incident Response", TARGET_INCIDENT_HEADERS)
    incident_by_target: dict[str, int] = {}
    if not incident_header_ok:
        findings.append("Incident Response: expected columns " + " | ".join(TARGET_INCIDENT_HEADERS))
        incident_rows = []
    for row in incident_rows:
        if len(row) != len(TARGET_INCIDENT_HEADERS):
            findings.append("Incident Response: each row must have the exact column count")
            continue
        incident, incident_target, containment, owner, risk_routing, question_routing, evidence = row
        if incident_target not in target_sources:
            findings.append(f"Incident Response: {incident_target} is not a reviewed target")
            continue
        if incident.casefold() in ABSENT:
            continue
        incident_by_target[incident_target] = incident_by_target.get(incident_target, 0) + 1
        if incident_by_target[incident_target] > 1:
            findings.append(f"Incident Response: duplicate incident row for {incident_target}")
        if evidence not in target_sources[incident_target]:
            findings.append(
                f"Incident Response: {incident_target} incident must use a verified source bound to that target"
            )
        if not incident.strip() or not evidence.strip():
            findings.append(f"Incident Response: {incident_target} incident and evidence are required")
        containment_kind = containment.split(":", 1)[0].strip().casefold()
        if containment_kind not in CONTAINMENT_TYPES:
            findings.append(
                f"Incident Response: {incident_target} requires typed containment"
            )
        if not _human(owner):
            findings.append(f"Incident Response: {incident_target} incident requires a human owner")
        if not re.fullmatch(r"PRD Risks:\s*\S.*", risk_routing):
            findings.append(f"Incident Response: {incident_target} requires PRD Risks routing")
        if not re.fullmatch(r"PRD Open Questions:\s*\S.*", question_routing):
            findings.append(f"Incident Response: {incident_target} requires PRD Open Questions routing")
    for target_id, target_verdict in target_verdict_map.items():
        if target_verdict == "incident" and incident_by_target.get(target_id, 0) == 0:
            findings.append(f"Incident Response: incident target {target_id} needs a target-bound incident row")
        if target_verdict != "incident" and incident_by_target.get(target_id, 0):
            findings.append(f"Incident Response: non-incident target {target_id} cannot carry an incident row")

    feedback_rows, feedback_header_ok = _rows(text, "## Feedback", TARGET_FEEDBACK_HEADERS)
    if not feedback_header_ok:
        findings.append("Feedback: expected columns " + " | ".join(TARGET_FEEDBACK_HEADERS))
        feedback_rows = []
    if not feedback_rows:
        findings.append("Feedback: at least one substantive target-bound fact is required")
    seen_feedback_rows: set[tuple[str, str, str, str]] = set()
    for row in feedback_rows:
        if len(row) != len(TARGET_FEEDBACK_HEADERS):
            findings.append("Feedback: each multi-target row must have the exact column count")
            continue
        fact, feedback_target, source_id, observed = row
        feedback_identity = (fact, feedback_target, source_id, observed)
        if feedback_identity in seen_feedback_rows:
            findings.append(f"Feedback: duplicate fact row for {feedback_target}")
        seen_feedback_rows.add(feedback_identity)
        if feedback_target not in target_ids:
            findings.append(f"Feedback: fact names an unreviewed target {feedback_target}")
        if fact.casefold() in ABSENT or observed.casefold() in ABSENT:
            findings.append(f"Feedback: {feedback_target} facts and observations cannot be empty")
        if source_id not in target_sources.get(feedback_target, set()):
            findings.append(
                f"Feedback: {feedback_target} fact must use a verified source bound to that target"
            )

    expected_signals, prd_findings = _parse_prd_signal_contract(prd_text)
    findings.extend(prd_findings)
    coverage_header, coverage_rows = _table(activation_text, "## Outcome Coverage")
    activation_target_sets: dict[str, set[str]] = {}
    if coverage_header == [
        "signal",
        "definition / obligation",
        "baseline",
        "target / guardrail",
        "measurement window",
        "expected signal",
        "release targets",
        "source id",
        "status",
    ]:
        for row in coverage_rows:
            if len(row) != 9:
                continue
            signal = row[0]
            scoped_targets = {item.strip() for item in row[6].split(",") if item.strip()}
            activation_target_sets[signal] = scoped_targets
            unknown_targets = scoped_targets - set(target_ids)
            if unknown_targets:
                findings.append(
                    f"Target Measurements: Activation Outcome Coverage for {signal} names unknown/unreviewed target(s) {', '.join(sorted(unknown_targets))}"
                )
    else:
        findings.append("Target Measurements: Activation Outcome Coverage table is missing or invalid")
    measurement_rows, measurement_header_ok = _rows(
        text, "## Target Measurements", TARGET_MEASUREMENT_HEADERS
    )
    if not measurement_header_ok:
        findings.append(
            "Target Measurements: expected columns "
            + " | ".join(TARGET_MEASUREMENT_HEADERS)
        )
        measurement_rows = []
    seen_signal_targets: set[tuple[str, str]] = set()
    for row in measurement_rows:
        if len(row) != len(TARGET_MEASUREMENT_HEADERS):
            findings.append("Target Measurements: each row must have the exact column count")
            continue
        signal, target_id, baseline, target_value, start, end, actual, source_id = row
        key = (signal, target_id)
        if key in seen_signal_targets:
            findings.append(f"Target Measurements: duplicate signal/target {signal}/{target_id}")
        seen_signal_targets.add(key)
        if target_id not in target_ids:
            findings.append(f"Target Measurements: {target_id} is not in the reviewed target set")
        expectation = expected_signals.get(signal)
        if expectation is None:
            findings.append(f"Target Measurements: unknown signal {signal}")
            continue
        for field, actual_value, expected_value in (
            ("baseline", baseline, expectation.get("baseline", "")),
            ("target", target_value, expectation.get("target", "")),
        ):
            if expected_value and actual_value != expected_value:
                findings.append(
                    f"Target Measurements: {signal}/{target_id} {field} must exactly match PRD"
                )
        if not _valid_date(start) or not _valid_date(end) or start > end:
            findings.append(f"Target Measurements: {signal}/{target_id} needs an ordered date window")
        else:
            expected_window = expectation.get("window", "")
            duration_days = _duration_days(expected_window)
            if duration_days is None and expected_window.strip() and not expected_window.casefold().startswith("n/a") and not expected_window.casefold().endswith("test"):
                findings.append(
                    f"Target Measurements: {signal}/{target_id} PRD measurement window must use a positive day/week duration"
                )
            elif duration_days is not None and (
                date.fromisoformat(end) - date.fromisoformat(start)
            ).days != duration_days:
                findings.append(
                    f"Target Measurements: {signal}/{target_id} window must match PRD measurement window {expected_window!r}"
                )
            if date.fromisoformat(end) > datetime.now(timezone.utc).date():
                findings.append(f"Target Measurements: {signal}/{target_id} window cannot end in the future")
            deployment = deployment_rows.get(target_id)
            deployment_date = deployment["checked"][:10] if deployment else ""
            if deployment_date and _valid_date(deployment_date):
                if start <= deployment_date or end <= deployment_date:
                    findings.append(
                        f"Target Measurements: {signal}/{target_id} window must start and end after target deployment"
                    )
        if _valid_date(reviewed_on) and _valid_date(end) and reviewed_on < end:
            findings.append(f"Target Measurements: {signal}/{target_id} window ends after Reviewed on")
        if actual.lower() in ABSENT:
            findings.append(f"Target Measurements: {signal}/{target_id} needs an actual value")
        if source_id not in target_sources.get(target_id, set()):
            findings.append(
                f"Target Measurements: {signal}/{target_id} source {source_id} is not a matching verified source"
            )
    for signal in sorted(set(expected_signals) - set(activation_target_sets)):
        findings.append(f"Target Measurements: Activation Outcome Coverage is missing signal {signal}")
    for target_id in target_ids:
        if not any(target_id in scoped for scoped in activation_target_sets.values()):
            findings.append(f"Target Measurements: reviewed target {target_id} has no applicable Activation Outcome Coverage signal")
    expected_pairs = {
        (signal, target_id)
        for signal, scoped_targets in activation_target_sets.items()
        for target_id in scoped_targets
        if target_id in target_ids
    }
    missing = sorted(expected_pairs - seen_signal_targets)
    for signal, target_id in missing:
        findings.append(f"Target Measurements: missing {signal} for {target_id}")
    extra = sorted(seen_signal_targets - expected_pairs)
    for signal, target_id in extra:
        findings.append(
            f"Target Measurements: {signal}/{target_id} is outside its Activation Outcome Coverage target set"
        )
    return findings


def _artifact_allows_na(target: object | None) -> bool:
    return bool(target is not None and allows_no_independent_artifact(target))


def _parse_prd_signal_contract(
    prd_text: str,
) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Return exact metric/required-test expectations for outcome joins."""

    findings: list[str] = []
    expected: dict[str, dict[str, str]] = {}
    header, rows = _table(prd_text, "## Metrics")
    if header == ["metric", "definition", "target"]:
        for row in rows:
            if len(row) != 3:
                findings.append("PRD: Metrics rows must have exactly 3 columns")
                continue
            name, _definition, target = row
            if name in expected:
                findings.append(f"PRD: duplicate metric {name}")
            if not name or not target or target.casefold() in ABSENT:
                findings.append(f"PRD: metric {name or '<empty>'} needs a target")
            expected[name] = {
                "kind": "metric",
                "baseline": "none recorded",
                "target": target,
                "window": "",
            }
    elif header == [
        "metric",
        "definition",
        "baseline",
        "target / guardrail",
        "measurement window",
        "source / method",
        "owner",
    ]:
        for row in rows:
            if len(row) != 7:
                findings.append("PRD: Metrics rows must have exactly 7 columns")
                continue
            name, _definition, baseline, target, window, _source, owner = row
            if name in expected:
                findings.append(f"PRD: duplicate metric {name}")
            if not name or any(value.casefold() in ABSENT for value in (baseline, target, window)):
                findings.append(f"PRD: metric {name or '<empty>'} needs baseline, target, and measurement window")
            if not _human(owner):
                findings.append(f"PRD: metric {name or '<empty>'} owner must name a human")
            expected[name] = {
                "kind": "metric",
                "baseline": baseline,
                "target": target,
                "window": window,
            }
    else:
        findings.append("PRD: Metrics table is missing or has unexpected columns")
    test_header, test_rows = _table(prd_text, "## Test Obligations")
    expected_test_header = [
        "test id",
        "obligation",
        "test type",
        "required",
        "upstream trace ids",
        "expected signal",
    ]
    if test_header[:6] != expected_test_header:
        findings.append("PRD: Test Obligations table is missing or has unexpected columns")
    else:
        seen_tests: set[str] = set()
        for row in test_rows:
            if len(row) < 6 or row[3].casefold() != "yes":
                continue
            test_id, _obligation, _test_type, _required, _trace, expected_signal = row[:6]
            if test_id in seen_tests:
                findings.append(f"PRD: duplicate required test {test_id}")
            seen_tests.add(test_id)
            if not MS_ID_RE.match(test_id) and not re.fullmatch(r"TEST-[0-9]{3}", test_id):
                findings.append(f"PRD: invalid required test ID {test_id!r}")
            if expected_signal.casefold() in ABSENT:
                findings.append(f"PRD: required test {test_id} needs an expected signal")
            expected[test_id] = {
                "kind": "test",
                "baseline": "none recorded",
                "target": expected_signal,
                "window": "",
            }
    return expected, findings


def _format_instant(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _prd_product_name(prd_text: str) -> str | None:
    active = active_text(prd_text)
    match = re.search(r"^#\s+PRD:\s*(.+?)\s*$", active, re.MULTILINE)
    if match:
        return match.group(1).strip()
    match = re.search(r"^#\s+Product:\s*(.+?)\s*$", active, re.MULTILINE)
    return match.group(1).strip() if match else None


def check_outcome_review_text(
    text: str,
    *,
    prd_text: str,
    architecture_text: str,
    deployment_text: str,
    activation_text: str,
    stack_text: str | None = None,
) -> list[str]:
    findings: list[str] = []
    if stack_text is not None:
        from check_product_package import validate_texts
        findings.extend(
            f"Product package: {item}"
            for item in validate_texts(
                prd_text,
                architecture_text,
                stack_text,
                require_filled=True,
                require_approved=True,
            )
        )
        from check_deployment import check_deployment_text
        findings.extend(
            f"Deployment: {item}"
            for item in check_deployment_text(
                deployment_text, architecture_text=architecture_text
            )
        )
    active = active_text(text)
    for heading in REQUIRED_SECTIONS:
        count = sum(line.strip() == heading for line in active.splitlines())
        if count == 0:
            findings.append(f"missing required section {heading}")
        elif count > 1:
            findings.append(f"duplicate required section {heading}")
    if active.count("# Outcome Review") != 1:
        findings.append("expected one # Outcome Review title")

    record_lines = _section(text, "## Record") or []
    record = _fields(record_lines)
    for field in _duplicate_fields(record_lines):
        findings.append(f"Record: duplicate field {field}")
    multi_target_mode = bool(record.get("Production release targets", "").strip())
    for field in RECORD_FIELDS:
        if field not in record:
            findings.append(f"Record: missing field {field}")
    schema = record.get("Schema")
    if schema not in {"outcome-review/1", "outcome-review/2"}:
        findings.append("Record: Schema must be outcome-review/1 or outcome-review/2")
    elif schema == "outcome-review/2":
        history_heading_count = sum(
            line.strip() == "## Verdict History" for line in active.splitlines()
        )
        if history_heading_count > 1:
            findings.append("duplicate required section ## Verdict History")
        findings.extend(_verdict_history_findings(text, record))
    verdict = record.get("Verdict", "")
    if verdict not in VERDICTS:
        findings.append(f"Record: invalid verdict {verdict!r}")
    if not _human(record.get("Outcome owner", "")):
        findings.append("Record: Outcome owner must name a human")
    product_name = _prd_product_name(prd_text)
    if product_name is None:
        findings.append("PRD: product identity heading is missing")
    elif record.get("Product") != product_name:
        findings.append(
            f"Record: Product must exactly match the PRD product identity {product_name!r}"
        )
    architecture_identity = product_identity(architecture_text, kind="architecture")
    if architecture_identity and product_identity(prd_text, kind="prd") != architecture_identity:
        findings.append("Package: PRD and architecture product identities must match")
    if stack_text is not None:
        stack_identity = product_identity(stack_text, kind="stack")
        if stack_identity and stack_identity != product_identity(prd_text, kind="prd"):
            findings.append("Package: PRD and stack-decisions product identities must match")

    contract, architecture_findings = parse_release_targets(architecture_text)
    findings.extend(architecture_findings)
    target_id = record.get("Production release target", "")
    target = contract.by_id().get(target_id)
    if target is None:
        findings.append("Record: Production release target is not defined by architecture.md")
    elif target.stage != "production":
        findings.append("Record: Production release target must be an architecture production target")
    sha = record.get("Release SHA", "")
    artifact = record.get("Artifact / build identity", "")
    if not SHA_RE.fullmatch(sha):
        findings.append("Record: Release SHA must be a full lowercase Git SHA")
    if artifact.lower() in ABSENT and not _artifact_allows_na(target):
        findings.append("Record: Artifact / build identity is required unless architecture Artifact kind is no independent artifact")
    elif artifact.lower() == "n/a" and not _artifact_allows_na(target):
        findings.append("Record: Artifact / build identity may be n/a only for architecture Artifact kind no independent artifact")
    if record.get("Deployment status") != "PASS":
        findings.append("Record: Deployment status must be PASS")
    deployment_checked = _timestamp(record.get("Deployment checked", ""))
    if deployment_checked is None:
        findings.append("Record: Deployment checked must be an RFC3339 timestamp")
    elif not _not_future(deployment_checked):
        findings.append("Record: Deployment checked cannot be in the future")
    reviewed_on = record.get("Reviewed on", "")
    if not _valid_date(reviewed_on):
        findings.append("Record: Reviewed on must be a real calendar date")
    elif reviewed_on > datetime.now(timezone.utc).date().isoformat():
        findings.append("Record: Reviewed on cannot be in the future")
    if deployment_checked is not None and _valid_date(reviewed_on):
        if reviewed_on < deployment_checked.astimezone(timezone.utc).date().isoformat():
            findings.append("Record: Reviewed on cannot precede Deployment checked")
    if record.get("Activation record") != "docs/ACTIVATION.md":
        findings.append("Record: Activation record must be docs/ACTIVATION.md")
    activation_digest = hashlib.sha256(activation_text.encode("utf-8")).hexdigest()
    if record.get("Activation sha256") != activation_digest:
        findings.append("Record: Activation sha256 does not match the current document bytes")

    deployment_rows = parse_release_target_status(deployment_text)
    deployment = deployment_rows.get(target_id)
    if deployment is None:
        findings.append("Deployment: Release Target Status is missing the reviewed target")
    else:
        if deployment["expected sha"] != sha or deployment["deployed sha"] != sha:
            findings.append("Deployment: reviewed target Expected and Deployed SHAs must equal the release SHA")
        if deployment["artifact / build identity"] != artifact:
            findings.append("Deployment: reviewed target artifact differs from the Outcome record")
        if deployment["status"] != "PASS":
            findings.append("Deployment: reviewed target is not a current PASS")
        if record.get("Deployment checked") != deployment["checked"]:
            findings.append("Deployment: reviewed target checked time differs from the Outcome record")
        expected_identity = f"{target.release_name};{target.channel};{artifact}" if target else ""
        if record.get("Deployment identity") != expected_identity:
            findings.append(
                f"Record: Deployment identity must be {expected_identity!r}"
            )

    activation_findings = check_activation_text(
        activation_text,
        prd_text=prd_text,
        architecture_text=architecture_text,
        deployment_text=deployment_text,
        require_verified_sources=True,
        require_ready=(target_id,),
    )
    findings.extend(f"Activation: {item}" for item in activation_findings)
    matching_sources, source_findings = _activation_sources(
        activation_text,
        target_id,
        sha,
        artifact,
        allow_other_bindings=bool(record.get("Production release targets", "").strip()),
    )
    findings.extend(source_findings)

    source_rows, source_header_ok = _rows(text, "## Activation Sources", SOURCE_HEADERS)
    if not source_header_ok:
        findings.append("Activation Sources: expected columns " + " | ".join(SOURCE_HEADERS))
    listed_sources: set[str] = set()
    for source_row in source_rows:
        if len(source_row) != len(SOURCE_HEADERS):
            findings.append("Activation Sources: each row must have the exact column count")
            continue
        source_id, binding, owner, verified_at, evidence = source_row
        if not MS_ID_RE.fullmatch(source_id):
            findings.append(f"Activation Sources: invalid source ID {source_id!r}")
            continue
        if source_id in listed_sources:
            findings.append(f"Activation Sources: duplicate source {source_id}")
        listed_sources.add(source_id)
        if source_id not in matching_sources:
            findings.append(
                f"Activation Sources: {source_id} is not a matching verified Activation source"
            )
        if binding != f"{target_id}@{sha}#{artifact}":
            findings.append(f"Activation Sources: {source_id} has a mismatched release binding")
        activation_source = matching_sources.get(source_id)
        if activation_source is not None:
            if owner != activation_source["owner"]:
                findings.append(f"Activation Sources: {source_id} owner differs from Activation")
        if not _human(owner):
            findings.append(f"Activation Sources: {source_id} owner must name a human")
        verified_instant = _timestamp(verified_at)
        if verified_instant is None:
            findings.append(f"Activation Sources: {source_id} verified time must be RFC3339")
        elif not _not_future(verified_instant):
            findings.append(f"Activation Sources: {source_id} verified time cannot be in the future")
        elif activation_source is not None:
            latest_pass = activation_source["latest_pass"]
            if isinstance(latest_pass, datetime) and verified_instant != latest_pass:
                findings.append(
                    f"Activation Sources: {source_id} verified time must equal the latest PASS evidence timestamp"
                )
        if evidence.lower() in ABSENT:
            findings.append(f"Activation Sources: {source_id} needs evidence")
        elif activation_source is not None:
            missing_evidence_ids = [
                evidence_id
                for evidence_id in activation_source["evidence_ids"]
                if evidence_id not in evidence
            ]
            if missing_evidence_ids:
                findings.append(
                    f"Activation Sources: {source_id} evidence must name "
                    + ", ".join(missing_evidence_ids)
                )
    if listed_sources != set(matching_sources):
        findings.append(
            "Activation Sources: every matching verified MS source must be listed exactly once"
        )

    expected_signals, prd_findings = _parse_prd_signal_contract(prd_text)
    findings.extend(prd_findings)
    measurement_rows, measurement_header_ok = (
        ([], True)
        if multi_target_mode
        else _rows(text, "## Measurements", MEASUREMENT_HEADERS)
    )
    if multi_target_mode:
        # The target-bound table below is the sole measurement authority for
        # multi-target reviews.  Legacy Measurements may remain only as a
        # compatibility view for the first target and is not revalidated.
        expected_signals = {}
    if not measurement_header_ok:
        findings.append("Measurements: expected columns " + " | ".join(MEASUREMENT_HEADERS))
    actual_signals: list[str] = []
    measurement_end_dates: list[str] = []
    for measurement_row in measurement_rows:
        if len(measurement_row) != len(MEASUREMENT_HEADERS):
            findings.append("Measurements: each row must have the exact column count")
            continue
        signal, baseline, target_value, start, end, actual, source_id = measurement_row
        actual_signals.append(signal)
        expectation = expected_signals.get(signal)
        if expectation is None:
            expectation = {}
        if expectation.get("baseline") and baseline != expectation["baseline"]:
            findings.append(
                f"Measurements: {signal} baseline must exactly match PRD {expectation['baseline']!r}"
            )
        if expectation.get("target") and target_value != expectation["target"]:
            findings.append(
                f"Measurements: {signal} target must exactly match PRD {expectation['target']!r}"
            )
        if baseline.lower() in ABSENT and baseline.lower() != "none recorded":
            findings.append(f"Measurements: {signal} needs a baseline or none recorded")
        if target_value.lower() in ABSENT:
            findings.append(f"Measurements: {signal} needs the recorded target")
        if not _valid_date(start) or not _valid_date(end) or start > end:
            findings.append(f"Measurements: {signal} needs a valid ordered window")
        else:
            measurement_end_dates.append(end)
            expected_window = expectation.get("window", "")
            duration_days = _duration_days(expected_window)
            if duration_days is None and expected_window.strip() and not expected_window.casefold().startswith("n/a") and not expected_window.casefold().endswith("test"):
                findings.append(
                    f"Measurements: {signal} PRD measurement window must use a positive day/week duration"
                )
            elif duration_days is not None and (date.fromisoformat(end) - date.fromisoformat(start)).days != duration_days:
                findings.append(
                    f"Measurements: {signal} window must match PRD measurement window {expected_window!r}"
                )
            if date.fromisoformat(end) > datetime.now(timezone.utc).date():
                findings.append(f"Measurements: {signal} window cannot end in the future")
        deployment_date = record.get("Deployment checked", "")[:10]
        if deployment_date and _valid_date(deployment_date):
            if start < deployment_date or end <= deployment_date:
                findings.append(
                    f"Measurements: {signal} window must elapse after deployment"
                )
        reviewed_on = record.get("Reviewed on", "")
        if _valid_date(reviewed_on) and reviewed_on < end:
            findings.append(f"Measurements: {signal} window ends after Reviewed on")
        if actual.lower() in ABSENT:
            findings.append(f"Measurements: {signal} needs an actual value")
        if source_id not in matching_sources:
            findings.append(f"Measurements: {signal} uses a non-matching source {source_id}")
    duplicates = sorted(
        signal for signal, count in Counter(actual_signals).items() if count > 1
    )
    if duplicates:
        findings.append("Measurements: duplicate signal(s) " + ", ".join(duplicates))
    for signal in sorted(set(expected_signals) - set(actual_signals)):
        findings.append(f"Measurements: missing PRD signal {signal}")
    for signal in sorted(set(actual_signals) - set(expected_signals)):
        findings.append(f"Measurements: unknown PRD signal {signal}")
    if measurement_end_dates and _valid_date(reviewed_on):
        latest_window_end = max(measurement_end_dates)
        if reviewed_on < latest_window_end:
            findings.append("Measurements: every measurement window must close on or before Reviewed on")

    feedback_headers = TARGET_FEEDBACK_HEADERS if multi_target_mode else FEEDBACK_HEADERS
    feedback_rows, feedback_header_ok = _rows(text, "## Feedback", feedback_headers)
    if multi_target_mode:
        feedback_rows, feedback_header_ok = [], True
    if not feedback_header_ok:
        findings.append("Feedback: expected columns " + " | ".join(feedback_headers))
    if not feedback_rows and not multi_target_mode:
        findings.append("Feedback: at least one substantive post-deployment fact is required")
    for feedback_row in feedback_rows:
        if len(feedback_row) != len(feedback_headers):
            findings.append("Feedback: each row must have the exact column count")
            continue
        if multi_target_mode:
            fact, feedback_target, source_id, observed = feedback_row
            feedback_target_set = {
                item.strip()
                for item in record.get("Production release targets", "")
                .removeprefix("target-set:")
                .split(",")
                if item.strip()
            }
            if feedback_target not in feedback_target_set:
                findings.append(f"Feedback: fact names an unreviewed target {feedback_target}")
        else:
            fact, source_id, observed = feedback_row
        if fact.lower() in ABSENT or observed.lower() in ABSENT:
            findings.append("Feedback: facts and observations cannot be empty")
        if source_id not in matching_sources:
            findings.append(f"Feedback: fact uses a non-matching source {source_id}")

    incident_headers = TARGET_INCIDENT_HEADERS if multi_target_mode else INCIDENT_HEADERS
    incident_rows, incident_header_ok = _rows(
        text, "## Incident Response", incident_headers
    )
    if multi_target_mode:
        incident_rows, incident_header_ok = [], True
    if not incident_header_ok:
        findings.append("Incident Response: expected columns " + " | ".join(incident_headers))
    if verdict == "incident" and not multi_target_mode:
        if not incident_rows:
            findings.append("Incident Response: incident verdict requires at least one incident row")
        for incident_row in incident_rows:
            if len(incident_row) != len(incident_headers):
                findings.append("Incident Response: each row must have the exact column count")
                continue
            if multi_target_mode:
                incident, incident_target, containment, owner, risk_routing, question_routing, evidence = incident_row
                if incident_target not in {
                    item.strip()
                    for item in record.get("Production release targets", "")
                    .removeprefix("target-set:")
                    .split(",")
                    if item.strip()
                }:
                    findings.append(f"Incident Response: incident names an unreviewed target {incident_target}")
            else:
                incident, containment, owner, risk_routing, question_routing, evidence = incident_row
            if incident.lower() in ABSENT or evidence.lower() in ABSENT:
                findings.append("Incident Response: incident and evidence are required")
            elif evidence not in matching_sources:
                findings.append("Incident Response: evidence must name a matching MS source")
            containment_kind = containment.split(":", 1)[0].strip().casefold()
            if containment_kind not in CONTAINMENT_TYPES:
                findings.append(
                    "Incident Response: incident requires containment with a typed kind "
                    "(rollout halted, rollback, forward fix, feature disabled, "
                    "traffic reduced, access revoked, or monitoring only)"
                )
            if not _human(owner):
                findings.append("Incident Response: incident requires a human owner")
            if not re.fullmatch(r"PRD Risks:\s*\S.*", risk_routing):
                findings.append("Incident Response: incident requires explicit PRD Risks routing")
            if not re.fullmatch(r"PRD Open Questions:\s*\S.*", question_routing):
                findings.append("Incident Response: incident requires explicit PRD Open Questions routing")
    elif not multi_target_mode and any(
        any(cell.casefold() not in ABSENT for cell in row) for row in incident_rows
    ):
        findings.append("Incident Response: only an incident verdict may contain incident rows")
    elif multi_target_mode:
        for row in incident_rows:
            if row and row[0].casefold() not in ABSENT:
                findings.append("Incident Response: only an incident target verdict may contain incident rows")

    verdict_lines = _section(text, "## Verdict") or []
    verdict_match = re.match(r"^Verdict:\s*(\S+)\s*—\s*(.+)$", "\n".join(verdict_lines).strip())
    if verdict_match is None:
        findings.append("Verdict: must use `Verdict: <enum> — <reason>`")
    elif verdict_match.group(1) != verdict:
        findings.append("Verdict: section and Record verdict differ")
    elif not verdict_match.group(2).strip():
        findings.append("Verdict: reason is required")

    followups, followup_header_ok = _rows(text, "## Open Follow-ups", FOLLOWUP_HEADERS)
    if not followup_header_ok:
        findings.append("Open Follow-ups: expected columns " + " | ".join(FOLLOWUP_HEADERS))
    for followup_row in followups:
        if len(followup_row) != len(FOLLOWUP_HEADERS):
            findings.append("Open Follow-ups: each row must have the exact column count")
            continue
        followup, route = followup_row
        if followup.lower() == "none" and route == "none":
            continue
        if followup.lower() in ABSENT or route not in FOLLOWUP_ROUTES:
            findings.append(f"Open Follow-ups: invalid route {route!r}")
    substantive_followups = [
        row for row in followups
        if len(row) == len(FOLLOWUP_HEADERS) and row[0].casefold() not in {"none", "n/a", "pending", ""}
    ]
    if verdict == "enhancement" and not any(row[1] == "enhancement request" for row in substantive_followups):
        findings.append("Open Follow-ups: enhancement verdict requires an enhancement request")
    elif verdict == "incident" and not multi_target_mode and not any(
        row[1] in {"risk", "open question"} for row in substantive_followups
    ):
        findings.append("Open Follow-ups: incident verdict requires risk or open question routing")
    elif verdict == "no_change" and substantive_followups:
        findings.append("Open Follow-ups: no_change verdict cannot carry substantive follow-ups")
    target_set_value = record.get("Production release targets", "")
    target_review_probe, target_review_header_probe = _rows(text, "## Target Reviews", TARGET_REVIEW_HEADERS)
    target_measure_probe, target_measure_header_probe = _rows(text, "## Target Measurements", TARGET_MEASUREMENT_HEADERS)
    if not target_set_value.strip():
        if target_review_header_probe and target_review_probe:
            findings.append("Outcome mode: single-target reviews cannot carry active Target Reviews")
        if target_measure_header_probe and target_measure_probe:
            findings.append("Outcome mode: single-target reviews cannot carry active Target Measurements")
    if target_set_value:
        if not target_set_value.startswith("target-set:"):
            findings.append("Record: Production release targets must use the exact `target-set:` prefix")
        if target_set_value.startswith("target-set:"):
            target_set_value = target_set_value.removeprefix("target-set:").strip()
        target_ids = [item.strip() for item in target_set_value.split(",") if item.strip()]
        if len(target_ids) < 2 or len(set(target_ids)) != len(target_ids):
            findings.append("Record: Production release targets must name an ordered unique multi-target set")
        else:
            if target_ids and target_id != target_ids[0]:
                findings.append("Record: Production release target must equal the first target-set entry")
            # Multi-target records keep a compatibility projection for the
            # first ordered target.  It must be complete and byte-for-byte
            # equal in the identity-bearing columns to that target's rows.
            legacy_rows, legacy_header_ok = _rows(text, "## Measurements", MEASUREMENT_HEADERS)
            first_target_rows = [
                row for row in target_measure_probe
                if len(row) == len(TARGET_MEASUREMENT_HEADERS) and row[1] == target_ids[0]
            ]
            if not legacy_header_ok or not legacy_rows:
                findings.append("Outcome mode: multi-target review requires a first-target Measurements projection")
            else:
                first_by_signal = {row[0]: row for row in first_target_rows}
                for row in legacy_rows:
                    if len(row) != len(MEASUREMENT_HEADERS):
                        findings.append("Measurements: projection rows must have the exact column count")
                        continue
                    target_row = first_by_signal.get(row[0])
                    if target_row is None:
                        # A signal scoped only to another target is not part of
                        # the first-target compatibility projection.
                        continue
                    if (
                        row[0], row[1], row[2], row[5], row[6]
                    ) != (
                        target_row[0], target_row[2], target_row[3], target_row[6], target_row[7]
                    ):
                        findings.append(f"Measurements: {row[0]} must project the first target exactly")
                projected_signals = {row[0] for row in legacy_rows}
                missing_projection = sorted(set(first_by_signal) - projected_signals)
                for signal in missing_projection:
                    findings.append(f"Measurements: {signal} is missing from the first-target projection")
            findings.extend(
                _multi_target_findings(
                    text,
                    target_ids=target_ids,
                    contract=contract,
                    prd_text=prd_text,
                    architecture_text=architecture_text,
                    deployment_text=deployment_text,
                    activation_text=activation_text,
                    deployment_rows=deployment_rows,
                    reviewed_on=reviewed_on,
                    aggregate_verdict=verdict,
                )
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcome", type=Path, required=True)
    parser.add_argument("--prd", type=Path, required=True)
    parser.add_argument("--architecture", type=Path, required=True)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--activation", type=Path, required=True)
    parser.add_argument("--stack-decisions", type=Path)
    parser.add_argument("--require-lifecycle", action="store_true")
    parser.add_argument("--prior-outcome", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    if args.require_lifecycle and args.prior_outcome is None:
        try:
            relative = args.outcome.resolve().relative_to(args.repo_root.resolve()).as_posix()
        except ValueError:
            relative = ""
        if not re.fullmatch(r"docs/product/outcomes/\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md", relative):
            print("path: lifecycle outcomes must use docs/product/outcomes/YYYY-MM-DD-<slug>.md", file=sys.stderr)
            return 1
    if args.prior_outcome is not None:
        if not args.prior_outcome.is_file():
            print(f"prior outcome record not found: {args.prior_outcome}", file=sys.stderr)
            return 2
        prior_text, prior_error = safe_read_text(args.prior_outcome)
        if prior_error:
            print(prior_error, file=sys.stderr)
            return 2
        current_text, current_error = safe_read_text(args.outcome)
        if current_error:
            print(current_error, file=sys.stderr)
            return 2
        prior_digest = hashlib.sha256((prior_text or "").encode("utf-8")).hexdigest()
        current_record = _fields(_section(current_text or "", "## Record") or [])
        if current_record.get("Schema") != "outcome-review/2":
            print(
                "Record: --prior-outcome requires current Schema: outcome-review/2",
                file=sys.stderr,
            )
            return 1
        if current_record.get("Prior outcome sha256") != prior_digest:
            print("Record: --prior-outcome requires an exact Prior outcome sha256 line", file=sys.stderr)
            return 1
        prior_history_findings = prior_append_findings(prior_text or "", current_text or "")
        if prior_history_findings:
            for finding in prior_history_findings:
                print(finding, file=sys.stderr)
            return 1
    if args.stack_decisions is None and args.require_lifecycle:
        print("--require-lifecycle requires --stack-decisions", file=sys.stderr)
        return 2
    paths = (args.outcome, args.prd, args.architecture, args.deployment, args.activation)
    if args.stack_decisions is not None:
        paths += (args.stack_decisions,)
    if any(not path.is_file() for path in paths):
        print("one or more input files do not exist", file=sys.stderr)
        return 2
    loaded: dict[str, str] = {}
    for name, path in {
        "outcome": args.outcome,
        "prd": args.prd,
        "architecture": args.architecture,
        "deployment": args.deployment,
        "activation": args.activation,
        "stack": args.stack_decisions,
    }.items():
        if path is None:
            continue
        value, error = safe_read_text(path)
        if error:
            print(error, file=sys.stderr)
            return 2
        loaded[name] = value or ""
    if args.require_lifecycle:
        lifecycle_record = _fields(_section(loaded["outcome"], "## Record") or [])
        if lifecycle_record.get("Schema") != "outcome-review/2":
            print("--require-lifecycle requires Schema: outcome-review/2", file=sys.stderr)
            return 1
    if args.stack_decisions is not None:
        from check_product_package import validate_texts
        package_findings = validate_texts(
            loaded["prd"], loaded["architecture"], loaded["stack"],
            require_filled=True, require_approved=True,
            repo_root=args.repo_root,
        )
        if package_findings:
            for item in package_findings:
                print(f"Product package: {item}", file=sys.stderr)
            return 1
    if args.stack_decisions is not None or args.require_lifecycle:
        from check_deployment import check_deployment_text
        deployment_findings = check_deployment_text(
            loaded["deployment"], architecture_text=loaded["architecture"]
        )
        if deployment_findings:
            for item in deployment_findings:
                print(f"Deployment: {item}", file=sys.stderr)
            return 1
    findings = check_outcome_review_text(
        loaded["outcome"],
        prd_text=loaded["prd"],
        architecture_text=loaded["architecture"],
        deployment_text=loaded["deployment"],
        activation_text=loaded["activation"],
        # The CLI validates the package/deployment immediately before this
        # call; avoid repeating the same findings in the final report.
        stack_text=None,
    )
    for finding in findings:
        print(f"{args.outcome}: {finding}")
    if findings:
        return 1
    print(f"{args.outcome} is bound to the exact verified production release")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
