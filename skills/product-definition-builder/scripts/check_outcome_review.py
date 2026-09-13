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


def _activation_sources(
    activation_text: str, target: str, sha: str, artifact: str
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
            if item["binding"] != expected_binding:
                findings.append(f"Activation: {source_id} evidence {evidence_id} has a mismatched release binding")
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
) -> list[str]:
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
    for field in RECORD_FIELDS:
        if field not in record:
            findings.append(f"Record: missing field {field}")
    if record.get("Schema") != "outcome-review/1":
        findings.append("Record: Schema must be outcome-review/1")
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
        activation_text, target_id, sha, artifact
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
    measurement_rows, measurement_header_ok = _rows(
        text, "## Measurements", MEASUREMENT_HEADERS
    )
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
            duration_match = re.search(r"\b(\d+)\s*days?\b", expected_window, re.IGNORECASE)
            if duration_match and (date.fromisoformat(end) - date.fromisoformat(start)).days != int(duration_match.group(1)):
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

    incident_rows, incident_header_ok = _rows(
        text, "## Incident Response", INCIDENT_HEADERS
    )
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
    elif any(
        any(cell.casefold() not in ABSENT for cell in row) for row in incident_rows
    ):
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
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcome", type=Path, required=True)
    parser.add_argument("--prd", type=Path, required=True)
    parser.add_argument("--architecture", type=Path, required=True)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--activation", type=Path, required=True)
    args = parser.parse_args(argv)
    paths = (args.outcome, args.prd, args.architecture, args.deployment, args.activation)
    if any(not path.is_file() for path in paths):
        print("one or more input files do not exist", file=sys.stderr)
        return 2
    findings = check_outcome_review_text(
        args.outcome.read_text(encoding="utf-8"),
        prd_text=args.prd.read_text(encoding="utf-8"),
        architecture_text=args.architecture.read_text(encoding="utf-8"),
        deployment_text=args.deployment.read_text(encoding="utf-8"),
        activation_text=args.activation.read_text(encoding="utf-8"),
    )
    for finding in findings:
        print(f"{args.outcome}: {finding}")
    if findings:
        return 1
    print(f"{args.outcome} is bound to the exact verified production release")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
