#!/usr/bin/env python3
"""Strict read-only validation for a completed single-target outcome-review.md record."""

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
DELIVERY_SCRIPTS = SIBLING_SCRIPTS_ROOT / "delivery-harness" / "scripts"
if str(DELIVERY_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DELIVERY_SCRIPTS))

from check_deployment import parse_release_target_status  # noqa: E402
from markdown_contract import active_text, is_human_owner  # noqa: E402
from release_targets import allows_no_independent_artifact, parse_release_targets  # noqa: E402
from contract_utils import product_identity, safe_read_text  # noqa: E402


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
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
    "Measurement record",
    "Deployment sha256",
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
FEEDBACK_HEADERS = ("fact", "source id", "observed")
INCIDENT_HEADERS = (
    "incident",
    "containment",
    "human owner",
    "prd risk routing",
    "prd open question routing",
    "evidence",
)
FOLLOWUP_HEADERS = ("follow-up", "route")
FOLLOWUP_ROUTES = {"enhancement request", "open question", "risk", "none"}
ABSENT = {"", "none", "n/a", "pending"}
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
    "app_store_connect",
    "play_console",
    "revenuecat",
    "auth_provider",
    "crash",
    "registry",
    "bot_platform",
    "platform_insights",
    "service_health",
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


def _table(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    section = _section(text, heading)
    if section is None:
        return [], []
    table = [line for line in section if line.strip().startswith("|")]
    if not table:
        return [], []
    cells = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in table]
    header = [cell.lower() for cell in cells[0]]
    data = [row for row in cells[1:] if not all(set(cell) <= {"-", ":", " "} for cell in row)]
    return header, data


def _rows(text: str, heading: str, expected: tuple[str, ...]) -> tuple[list[list[str]], bool]:
    header, data = _table(text, heading)
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


MEASUREMENT_SOURCE_HEADERS = [
    "ms id",
    "signals",
    "target",
    "environment",
    "retrieval",
    "source role",
    "release bindings",
    "owner",
    "status",
    "verified at",
    "evidence",
]


def _measurement_sources(
    deployment_text: str,
    target: str,
    sha: str,
    artifact: str,
) -> tuple[dict[str, dict[str, object]], list[str]]:
    header, rows = _table(deployment_text, "## Measurement Sources")
    findings: list[str] = []
    if header != MEASUREMENT_SOURCE_HEADERS:
        return {}, ["Deployment: Measurement Sources table is missing or invalid"]
    result: dict[str, dict[str, object]] = {}
    expected_binding = f"{target}@{sha}#{artifact}"
    for row in rows:
        if len(row) != len(MEASUREMENT_SOURCE_HEADERS):
            continue
        source_id, _signals, _ms_target, _environment, _retrieval, source_role, bindings, owner, status, verified_at, evidence = row
        if status != "verified" or expected_binding not in {
            item.strip() for item in bindings.split(",")
        }:
            continue
        if source_role not in SOURCE_ROLES:
            findings.append(f"Deployment: {source_id} has invalid source role {source_role!r}")
        verified_instant = _timestamp(verified_at)
        if verified_instant is None:
            findings.append(f"Deployment: {source_id} Verified at must be an RFC3339 timestamp")
        if evidence.casefold() in ABSENT:
            findings.append(f"Deployment: {source_id} needs evidence")
        result[source_id] = {
            "owner": owner,
            "source_role": source_role,
            "verified_at": verified_instant,
            "evidence": evidence,
            "binding": expected_binding,
        }
    return result, findings


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
) -> list[str]:
    """Join one outcome record to its PRD and deployment bytes.

    The product and deployment checkers run on their own inputs;
    this check binds the record to the exact release they describe.
    """

    findings: list[str] = []
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
    for field in RECORD_FIELDS:
        if field not in record:
            findings.append(f"Record: missing field {field}")
    if "Production release targets" in record:
        findings.append(
            "Record: one record covers one production release target; write one record per target"
        )
    if record.get("Schema") not in {"outcome-review/1", "outcome-review/2"}:
        findings.append("Record: Schema must be outcome-review/1 or outcome-review/2")
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
    if record.get("Measurement record") != "docs/DEPLOYMENT.md":
        findings.append("Record: Measurement record must be docs/DEPLOYMENT.md")
    deployment_digest = hashlib.sha256(deployment_text.encode("utf-8")).hexdigest()
    if record.get("Deployment sha256") != deployment_digest:
        findings.append("Record: Deployment sha256 does not match the current document bytes")

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

    matching_sources, source_findings = _measurement_sources(
        deployment_text, target_id, sha, artifact
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
                f"Activation Sources: {source_id} is not a matching verified measurement source"
            )
        if binding != f"{target_id}@{sha}#{artifact}":
            findings.append(f"Activation Sources: {source_id} has a mismatched release binding")
        activation_source = matching_sources.get(source_id)
        if activation_source is not None:
            if owner != activation_source["owner"]:
                findings.append(
                    f"Activation Sources: {source_id} owner differs from the deployment row"
                )
        if not _human(owner):
            findings.append(f"Activation Sources: {source_id} owner must name a human")
        verified_instant = _timestamp(verified_at)
        if verified_instant is None:
            findings.append(f"Activation Sources: {source_id} verified time must be RFC3339")
        elif not _not_future(verified_instant):
            findings.append(f"Activation Sources: {source_id} verified time cannot be in the future")
        elif activation_source is not None:
            source_verified = activation_source["verified_at"]
            if isinstance(source_verified, datetime) and verified_instant != source_verified:
                findings.append(
                    f"Activation Sources: {source_id} verified time must equal the deployment row Verified at"
                )
        if evidence.lower() in ABSENT:
            findings.append(f"Activation Sources: {source_id} needs evidence")
        elif activation_source is not None and evidence != activation_source["evidence"]:
            findings.append(
                f"Activation Sources: {source_id} evidence must equal the deployment row Evidence"
            )
    if listed_sources != set(matching_sources):
        findings.append(
            "Activation Sources: every matching verified MS source must be listed exactly once"
        )

    expected_signals, prd_findings = _parse_prd_signal_contract(prd_text)
    findings.extend(prd_findings)
    measurement_rows, measurement_header_ok = _rows(text, "## Measurements", MEASUREMENT_HEADERS)
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
        if reviewed_on < max(measurement_end_dates):
            findings.append("Measurements: every measurement window must close on or before Reviewed on")

    feedback_rows, feedback_header_ok = _rows(text, "## Feedback", FEEDBACK_HEADERS)
    if not feedback_header_ok:
        findings.append("Feedback: expected columns " + " | ".join(FEEDBACK_HEADERS))
    if not feedback_rows:
        findings.append("Feedback: at least one substantive post-deployment fact is required")
    for feedback_row in feedback_rows:
        if len(feedback_row) != len(FEEDBACK_HEADERS):
            findings.append("Feedback: each row must have the exact column count")
            continue
        fact, source_id, observed = feedback_row
        if fact.lower() in ABSENT or observed.lower() in ABSENT:
            findings.append("Feedback: facts and observations cannot be empty")
        if source_id not in matching_sources:
            findings.append(f"Feedback: fact uses a non-matching source {source_id}")

    incident_rows, incident_header_ok = _rows(text, "## Incident Response", INCIDENT_HEADERS)
    if not incident_header_ok:
        findings.append("Incident Response: expected columns " + " | ".join(INCIDENT_HEADERS))
    if verdict == "incident":
        if not incident_rows:
            findings.append("Incident Response: incident verdict requires at least one incident row")
        for incident_row in incident_rows:
            if len(incident_row) != len(INCIDENT_HEADERS):
                findings.append("Incident Response: each row must have the exact column count")
                continue
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
    elif any(any(cell.casefold() not in ABSENT for cell in row) for row in incident_rows):
        findings.append("Incident Response: only an incident verdict may contain incident rows")

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
    elif verdict == "incident" and not any(
        row[1] in {"risk", "open question"} for row in substantive_followups
    ):
        findings.append("Open Follow-ups: incident verdict requires risk or open question routing")
    elif verdict == "no_change" and substantive_followups:
        findings.append("Open Follow-ups: no_change verdict cannot carry substantive follow-ups")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcome", type=Path, required=True)
    parser.add_argument("--prd", type=Path, required=True)
    parser.add_argument("--architecture", type=Path, required=True)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--require-lifecycle", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    if args.require_lifecycle:
        try:
            relative = args.outcome.resolve().relative_to(args.repo_root.resolve()).as_posix()
        except ValueError:
            relative = ""
        if not re.fullmatch(r"docs/product/outcomes/\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md", relative):
            print("path: lifecycle outcomes must use docs/product/outcomes/YYYY-MM-DD-<slug>.md", file=sys.stderr)
            return 1
    paths = {
        "outcome": args.outcome,
        "prd": args.prd,
        "architecture": args.architecture,
        "deployment": args.deployment,
    }
    if any(not path.is_file() for path in paths.values()):
        print("one or more input files do not exist", file=sys.stderr)
        return 2
    loaded: dict[str, str] = {}
    for name, path in paths.items():
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
    findings = check_outcome_review_text(
        loaded["outcome"],
        prd_text=loaded["prd"],
        architecture_text=loaded["architecture"],
        deployment_text=loaded["deployment"],
    )
    for finding in findings:
        print(f"{args.outcome}: {finding}")
    if findings:
        return 1
    print(f"{args.outcome} is bound to the exact verified production release")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
