#!/usr/bin/env python3
"""Read-only structural and readiness checks for docs/ACTIVATION.md."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path


TASK_START = "<!-- activation-task-contract:start -->"
TASK_END = "<!-- activation-task-contract:end -->"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ACT_ID_RE = re.compile(r"^ACT-[0-9]{3}$")
MS_ID_RE = re.compile(r"^MS-[0-9]{3}$")
EVIDENCE_ID_RE = re.compile(r"^EVID-[0-9]{3}$")
TASK_HEADING_RE = re.compile(r"^###\s+(ACT-[0-9]{3})\s+[—-]\s+(.+?)\s*$")
FIELD_RE = re.compile(r"^- ([A-Za-z][A-Za-z /-]*):\s*(.*)$")
PLACEHOLDER_RE = re.compile(r"<[^>\n]+>|\bTBD\b", re.IGNORECASE)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
BEARER_RE = re.compile(r"Authorization\s*:\s*Bearer\s+\S+", re.IGNORECASE)
CREDENTIAL_URL_RE = re.compile(r"https?://[^\s/:]+:[^\s/@]+@", re.IGNORECASE)
KNOWN_SECRET_RE = re.compile(
    r"\b(?:sk_live_[A-Za-z0-9]+|ghp_[A-Za-z0-9]+|xox[baprs]-[A-Za-z0-9-]+|AKIA[0-9A-Z]{16})\b"
)

REQUIRED_SECTIONS = (
    "## Record",
    "## Applied Profiles",
    "## Capability Observations",
    "## Outcome Coverage",
    "## Measurement Sources",
    "## Activation Tasks",
    "## Verification Evidence",
    "## Manual Handoff",
    "## Target Readiness",
    "## Open Blockers",
)
RECORD_FIELDS = (
    "Schema",
    "Product",
    "Activation owner",
    "Release reference",
    "Status",
    "Updated",
    "Measurement window starts",
)
TABLE_HEADERS = {
    "## Applied Profiles": ("profile", "applies", "reason", "owner"),
    "## Capability Observations": (
        "route",
        "status",
        "supports",
        "surface",
        "target context",
        "checked",
        "evidence",
    ),
    "## Outcome Coverage": (
        "signal",
        "definition / target",
        "window",
        "release targets",
        "source id",
        "status",
    ),
    "## Measurement Sources": (
        "ms id",
        "system / retrieval",
        "route",
        "release targets",
        "owner",
        "status",
        "evidence ids",
    ),
    "## Verification Evidence": (
        "evidence id",
        "item id",
        "kind",
        "checked",
        "result",
        "route",
        "reference",
    ),
    "## Manual Handoff": (
        "item id",
        "owner",
        "exact step",
        "expected evidence",
        "status",
    ),
    "## Target Readiness": (
        "release target",
        "release identity",
        "status",
        "checked",
        "blockers",
    ),
}
TASK_FIELDS = (
    "Source refs",
    "Release bindings",
    "Depends on",
    "Operation",
    "Target",
    "Environment",
    "Precondition",
    "Desired state",
    "Secret names",
    "Risk",
    "Confirmation",
    "Execution route",
    "Read-back route",
    "Authorization",
    "Authorization source",
    "Action digest",
    "Authorized digest",
    "Required",
    "Status",
    "Verification",
    "Evidence IDs",
    "Blocker / N/A reason",
    "Updated",
)

ROUTES = {"connector", "api", "cli", "browser", "computer_use", "manual", "unselected"}
CAPABILITY_STATUSES = {"available", "unavailable", "unobserved", "human_only"}
TARGET_CONTEXTS = {"confirmed", "needs_user_login", "ambiguous", "n/a"}
SUPPORTS = {"read", "write", "readback"}
SOURCE_STATUSES = {"planned", "available", "verified", "blocked", "superseded", "n/a"}
TASK_STATUSES = {"pending", "ready", "configured", "verified", "uncertain", "blocked", "stale", "n/a"}
RECORD_STATUSES = {"seeded", "preparation", "active", "handoff_ready", "blocked", "n/a"}
READINESS_STATUSES = {"preparation", "pending", "ready", "blocked"}
EVIDENCE_KINDS = {"write", "readback", "behavior", "capability", "manual"}
EVIDENCE_RESULTS = {"PASS", "FAIL", "BLOCKED"}
AUTHORIZATIONS = {"not_required", "pending", "approved", "consumed", "denied", "expired", "handoff_complete", "prohibited"}
OPERATIONS = {"read", "create", "update", "upload", "publish", "transmit", "delete", "rotate", "revoke", "execute"}
RISK_CONFIRMATION = {
    "read_only": "read_only",
    "standard": "exact_preapproval",
    "high": "action_time_confirmation",
    "handoff": "user_handoff",
    "prohibited": "prohibited",
}
HANDOFF_STATUSES = {"pending", "completed", "n/a"}
ABSENT = {"", "none", "n/a", "pending", "unselected"}
FORBIDDEN_HEADERS = {"value", "secret value", "token", "password", "credential"}


def _placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.search(value))


def _section(text: str, heading: str) -> list[str] | None:
    lines = text.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return None
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return lines[start + 1 : end]


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(row: list[str]) -> bool:
    return bool(row) and all(cell and set(cell) <= {"-", ":", " "} for cell in row)


def _table(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    section = _section(text, heading)
    if section is None:
        return [], []
    rows = [_cells(line) for line in section if line.strip().startswith("|")]
    if not rows:
        return [], []
    header = [cell.lower() for cell in rows[0]]
    data = [row for row in rows[1:] if not _is_separator(row)]
    return header, data


def _record(text: str) -> tuple[dict[str, str], list[str]]:
    findings: list[str] = []
    section = _section(text, "## Record")
    if section is None:
        return {}, ["Record: missing section"]
    fields: dict[str, str] = {}
    for line in section:
        match = FIELD_RE.match(line.strip())
        if not match:
            continue
        name, value = match.groups()
        if name in fields:
            findings.append(f"Record: duplicate field {name}")
        fields[name] = value.strip()
    for name in RECORD_FIELDS:
        if name not in fields:
            findings.append(f"Record: missing field {name}")
    return fields, findings


def _parse_list(value: str) -> list[str]:
    if value.strip().lower() in {"", "none", "n/a"}:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _normal(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip())


def action_digest(task_id: str, task: dict[str, str]) -> str:
    payload = {
        "schema": "activation-action/1",
        "task_id": _normal(task_id),
        "source_refs": sorted(_normal(item) for item in _parse_list(task["Source refs"])),
        "release_bindings": sorted(_normal(item) for item in _parse_list(task["Release bindings"])),
        "depends_on": sorted(_normal(item) for item in _parse_list(task["Depends on"])),
        "operation": _normal(task["Operation"]),
        "target": _normal(task["Target"]),
        "environment": _normal(task["Environment"]),
        "precondition": _normal(task["Precondition"]),
        "desired_state": _normal(task["Desired state"]),
        "secret_names": sorted(_normal(item) for item in _parse_list(task["Secret names"])),
        "risk": _normal(task["Risk"]),
        "confirmation": _normal(task["Confirmation"]),
        "execution_route": _normal(task["Execution route"]),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _tasks(text: str) -> tuple[dict[str, dict[str, str]], dict[str, str], list[str]]:
    findings: list[str] = []
    if text.count(TASK_START) != 1 or text.count(TASK_END) != 1:
        return {}, {}, ["Activation Tasks: expected one matched task-contract boundary pair"]
    body = text.split(TASK_START, 1)[1].split(TASK_END, 1)[0]
    tasks: dict[str, dict[str, str]] = {}
    titles: dict[str, str] = {}
    current: str | None = None
    for raw_line in body.splitlines():
        line = raw_line.strip()
        heading = TASK_HEADING_RE.match(line)
        if heading:
            task_id, title = heading.groups()
            if task_id in tasks:
                findings.append(f"Activation Tasks: duplicate task ID {task_id}")
            else:
                tasks[task_id] = {}
                titles[task_id] = title.strip()
            current = task_id
            continue
        field = FIELD_RE.match(line)
        if field and current is not None:
            name, value = field.groups()
            if name in tasks[current]:
                findings.append(f"{current}: duplicate field {name}")
            tasks[current][name] = value.strip()
    if not tasks:
        findings.append("Activation Tasks: no ACT task blocks found")
    for task_id, fields in tasks.items():
        unknown = sorted(set(fields) - set(TASK_FIELDS))
        for name in unknown:
            findings.append(f"{task_id}: unsupported field {name}")
        for name in TASK_FIELDS:
            if name not in fields:
                findings.append(f"{task_id}: missing field {name}")
    return tasks, titles, findings


def _value_findings(label: str, values: list[str], require_filled: bool) -> list[str]:
    if not require_filled:
        return []
    return [f"{label}: unresolved placeholder {value!r}" for value in values if _placeholder(value)]


def _validate_tables(text: str, require_filled: bool) -> tuple[dict[str, list[list[str]]], list[str]]:
    findings: list[str] = []
    parsed: dict[str, list[list[str]]] = {}
    for heading, expected in TABLE_HEADERS.items():
        header, rows = _table(text, heading)
        label = heading.removeprefix("## ")
        if not header:
            findings.append(f"{label}: missing section or Markdown table")
            parsed[heading] = []
            continue
        if any(cell in FORBIDDEN_HEADERS for cell in header):
            findings.append(f"{label}: must not contain a credential-value column")
        if tuple(header) != expected:
            findings.append(f"{label}: expected columns {' | '.join(expected)}")
            parsed[heading] = []
            continue
        valid_rows: list[list[str]] = []
        for row in rows:
            if len(row) != len(expected):
                findings.append(f"{label}: each row must have {len(expected)} columns")
                continue
            valid_rows.append(row)
            findings.extend(_value_findings(label, row, require_filled))
        parsed[heading] = valid_rows
    return parsed, findings


def _validate_profiles(rows: list[list[str]]) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()
    for profile, applies, reason, owner in rows:
        if _placeholder(profile) or _placeholder(applies):
            continue
        key = profile.lower()
        if key in seen:
            findings.append(f"Applied Profiles: duplicate profile {profile}")
        seen.add(key)
        if applies.lower() not in {"yes", "no"}:
            findings.append(f"Applied Profiles: {profile} applies must be yes or no")
        if not reason or not owner:
            findings.append(f"Applied Profiles: {profile} needs a reason and owner")
    if rows and not any(row[0].lower() == "core" and row[1].lower() == "yes" for row in rows):
        findings.append("Applied Profiles: core must apply")
    return findings


def _validate_capabilities(rows: list[list[str]]) -> tuple[dict[str, dict[str, object]], list[str]]:
    findings: list[str] = []
    capabilities: dict[str, dict[str, object]] = {}
    for route, status, supports, surface, target_context, checked, evidence in rows:
        if _placeholder(route):
            continue
        if route not in ROUTES - {"unselected"}:
            findings.append(f"Capability Observations: unsupported route {route}")
            continue
        if route in capabilities:
            findings.append(f"Capability Observations: duplicate route {route}")
            continue
        support_set = set(_parse_list(supports.lower()))
        if supports.lower() == "n/a":
            support_set = set()
        if status not in CAPABILITY_STATUSES:
            findings.append(f"Capability Observations: {route} has invalid status {status!r}")
        if support_set - SUPPORTS:
            findings.append(f"Capability Observations: {route} has unsupported capabilities")
        if target_context not in TARGET_CONTEXTS:
            findings.append(f"Capability Observations: {route} has invalid target context {target_context!r}")
        if status == "available" and (not support_set or checked.lower() in ABSENT or evidence.lower() in ABSENT):
            findings.append(f"Capability Observations: available route {route} needs supports, checked time, and evidence")
        capabilities[route] = {
            "status": status,
            "supports": support_set,
            "surface": surface,
            "target_context": target_context,
        }
    return capabilities, findings


def _validate_evidence(rows: list[list[str]]) -> tuple[dict[str, dict[str, str]], list[str]]:
    findings: list[str] = []
    evidence: dict[str, dict[str, str]] = {}
    for evidence_id, item_id, kind, checked, result, route, reference in rows:
        if not EVIDENCE_ID_RE.fullmatch(evidence_id):
            findings.append(f"Verification Evidence: invalid evidence ID {evidence_id!r}")
            continue
        if evidence_id in evidence:
            findings.append(f"Verification Evidence: duplicate evidence ID {evidence_id}")
            continue
        if kind not in EVIDENCE_KINDS:
            findings.append(f"Verification Evidence: {evidence_id} has invalid kind {kind!r}")
        if result not in EVIDENCE_RESULTS:
            findings.append(f"Verification Evidence: {evidence_id} has invalid result {result!r}")
        if route not in ROUTES - {"unselected"}:
            findings.append(f"Verification Evidence: {evidence_id} has invalid route {route!r}")
        if checked.lower() in ABSENT or reference.lower() in ABSENT:
            findings.append(f"Verification Evidence: {evidence_id} needs checked time and reference")
        evidence[evidence_id] = {"item_id": item_id, "kind": kind, "result": result, "route": route}
    return evidence, findings


def _validate_sources(
    rows: list[list[str]], evidence: dict[str, dict[str, str]]
) -> tuple[dict[str, dict[str, object]], list[str]]:
    findings: list[str] = []
    sources: dict[str, dict[str, object]] = {}
    for source_id, system, route, targets, owner, status, evidence_ids in rows:
        if not MS_ID_RE.fullmatch(source_id):
            findings.append(f"Measurement Sources: invalid source ID {source_id!r}")
            continue
        if source_id in sources:
            findings.append(f"Measurement Sources: duplicate source ID {source_id}")
            continue
        if route not in ROUTES:
            findings.append(f"Measurement Sources: {source_id} has invalid route {route!r}")
        if status not in SOURCE_STATUSES:
            findings.append(f"Measurement Sources: {source_id} has invalid status {status!r}")
        ids = _parse_list(evidence_ids)
        for evidence_id in ids:
            if evidence_id not in evidence:
                findings.append(f"Measurement Sources: {source_id} references unknown evidence {evidence_id}")
            elif evidence[evidence_id]["item_id"] != source_id:
                findings.append(f"Measurement Sources: {source_id} evidence {evidence_id} belongs to another item")
        if status == "verified" and not any(
            evidence[item]["result"] == "PASS" and evidence[item]["kind"] in {"readback", "behavior"}
            for item in ids
            if item in evidence
        ):
            findings.append(f"Measurement Sources: verified source {source_id} needs PASS read-back or behavior evidence")
        sources[source_id] = {
            "system": system,
            "route": route,
            "targets": set(_parse_list(targets)),
            "owner": owner,
            "status": status,
            "evidence_ids": ids,
        }
    return sources, findings


def _release_bindings(value: str, label: str, require_filled: bool) -> tuple[dict[str, str], list[str]]:
    findings: list[str] = []
    bindings: dict[str, str] = {}
    for item in _parse_list(value):
        if "@" not in item:
            findings.append(f"{label}: release binding {item!r} must be target@sha")
            continue
        target, identity = item.rsplit("@", 1)
        if not target or target in bindings:
            findings.append(f"{label}: duplicate or empty release target in {item!r}")
            continue
        if identity != "pending" and not SHA_RE.fullmatch(identity):
            findings.append(f"{label}: release binding {item!r} needs a full lowercase Git SHA")
        if require_filled and (identity == "pending" or _placeholder(target)):
            findings.append(f"{label}: unresolved release binding {item!r}")
        bindings[target] = identity
    return bindings, findings


def _has_pass(evidence_ids: list[str], evidence: dict[str, dict[str, str]], item_id: str, kinds: set[str]) -> bool:
    return any(
        evidence[evidence_id]["item_id"] == item_id
        and evidence[evidence_id]["kind"] in kinds
        and evidence[evidence_id]["result"] == "PASS"
        for evidence_id in evidence_ids
        if evidence_id in evidence
    )


def _task_findings(
    task_id: str,
    task: dict[str, str],
    tasks: dict[str, dict[str, str]],
    capabilities: dict[str, dict[str, object]],
    evidence: dict[str, dict[str, str]],
    manual: dict[str, str],
    require_filled: bool,
) -> tuple[dict[str, str], list[str]]:
    findings: list[str] = []
    if set(TASK_FIELDS) - set(task):
        return {}, findings
    values = [task[field] for field in TASK_FIELDS]
    findings.extend(_value_findings(task_id, values, require_filled))
    operation = task["Operation"]
    risk = task["Risk"]
    confirmation = task["Confirmation"]
    route = task["Execution route"]
    readback_route = task["Read-back route"]
    authorization = task["Authorization"]
    status = task["Status"]
    if operation not in OPERATIONS:
        findings.append(f"{task_id}: invalid operation {operation!r}")
    if risk not in RISK_CONFIRMATION:
        findings.append(f"{task_id}: invalid risk {risk!r}")
    elif confirmation != RISK_CONFIRMATION[risk]:
        findings.append(f"{task_id}: risk {risk} requires confirmation {RISK_CONFIRMATION[risk]}")
    if operation == "read" and risk != "read_only":
        findings.append(f"{task_id}: read operation must use read_only risk")
    if operation != "read" and risk == "read_only":
        findings.append(f"{task_id}: mutating operation cannot use read_only risk")
    if route not in ROUTES or readback_route not in ROUTES:
        findings.append(f"{task_id}: invalid execution or read-back route")
    if authorization not in AUTHORIZATIONS:
        findings.append(f"{task_id}: invalid authorization {authorization!r}")
    if status not in TASK_STATUSES:
        findings.append(f"{task_id}: invalid status {status!r}")
    if task["Required"].lower() not in {"yes", "no"}:
        findings.append(f"{task_id}: Required must be yes or no")
    if task["Required"].lower() == "yes" and status == "n/a":
        findings.append(f"{task_id}: a required task cannot be n/a")
    if risk == "read_only" and authorization != "not_required":
        findings.append(f"{task_id}: read-only action authorization must be not_required")
    if risk == "prohibited" and (authorization != "prohibited" or status not in {"blocked", "n/a"}):
        findings.append(f"{task_id}: prohibited action must stay prohibited and blocked or n/a")
    if risk in {"standard", "high"} and status == "ready" and authorization != "approved":
        findings.append(f"{task_id}: ready write requires approved authorization")
    if risk in {"standard", "high"} and status in {"configured", "verified", "uncertain"} and authorization != "consumed":
        findings.append(f"{task_id}: attempted write requires consumed authorization")
    if risk == "handoff" and status in {"configured", "verified"} and authorization != "handoff_complete":
        findings.append(f"{task_id}: completed user handoff requires handoff_complete authorization")
    if authorization in {"approved", "consumed", "handoff_complete"} and task["Authorization source"].lower() in ABSENT:
        findings.append(f"{task_id}: authorized action needs a user-authored authorization source")

    bindings, binding_findings = _release_bindings(task["Release bindings"], task_id, require_filled)
    findings.extend(binding_findings)
    dependencies = _parse_list(task["Depends on"])
    for dependency in dependencies:
        if dependency not in tasks:
            findings.append(f"{task_id}: unknown dependency {dependency}")
    names = _parse_list(task["Secret names"])
    for name in names:
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", name) is None:
            findings.append(f"{task_id}: secret name {name!r} is not a value-free configuration name")

    computed = action_digest(task_id, task)
    recorded = task["Action digest"]
    authorized = task["Authorized digest"]
    if recorded != "pending" and (not SHA256_RE.fullmatch(recorded) or recorded != computed):
        findings.append(f"{task_id}: Action digest does not match the current action")
    if status in {"ready", "configured", "verified", "uncertain"} and recorded != computed:
        findings.append(f"{task_id}: executable or attempted action needs its current Action digest")
    if authorization in {"approved", "consumed", "handoff_complete"} and authorized != computed:
        findings.append(f"{task_id}: Authorized digest must equal the current Action digest")

    evidence_ids = _parse_list(task["Evidence IDs"])
    for evidence_id in evidence_ids:
        if evidence_id not in evidence:
            findings.append(f"{task_id}: unknown evidence {evidence_id}")
        elif evidence[evidence_id]["item_id"] != task_id:
            findings.append(f"{task_id}: evidence {evidence_id} belongs to another item")
    if status in {"ready", "configured", "verified", "uncertain"}:
        capability = capabilities.get(route)
        needed = "read" if operation == "read" else "write"
        if not capability or capability["status"] not in {"available", "human_only"}:
            findings.append(f"{task_id}: selected execution route is not available")
        elif needed not in capability["supports"] and capability["status"] != "human_only":
            findings.append(f"{task_id}: selected execution route does not support {needed}")
        if capability and capability["target_context"] != "confirmed":
            findings.append(f"{task_id}: selected execution route target context is not confirmed")
        for dependency in dependencies:
            if dependency in tasks and tasks[dependency].get("Status") != "verified":
                findings.append(f"{task_id}: dependency {dependency} is not verified")
    if status == "configured" and not _has_pass(evidence_ids, evidence, task_id, {"write", "manual"}):
        findings.append(f"{task_id}: configured task needs PASS write or manual evidence")
    if status == "verified":
        capability = capabilities.get(readback_route)
        if not capability or capability["status"] not in {"available", "human_only"}:
            findings.append(f"{task_id}: verified task read-back route is not available")
        elif "readback" not in capability["supports"] and capability["status"] != "human_only":
            findings.append(f"{task_id}: verified task route does not support readback")
        if not _has_pass(evidence_ids, evidence, task_id, {"readback"}):
            findings.append(f"{task_id}: verified task needs distinct PASS readback evidence")
        if not task["Verification"].lower().startswith("n/a") and not _has_pass(
            evidence_ids, evidence, task_id, {"behavior"}
        ):
            findings.append(f"{task_id}: verified task needs PASS behavior evidence")
    if confirmation == "user_handoff" and task_id not in manual:
        findings.append(f"{task_id}: user_handoff task needs a Manual Handoff row")
    if status in {"configured", "verified"} and confirmation == "user_handoff" and manual.get(task_id) != "completed":
        findings.append(f"{task_id}: user handoff is not completed")
    if status in {"uncertain", "blocked", "stale", "n/a"} and task["Blocker / N/A reason"].lower() in {"", "none"}:
        findings.append(f"{task_id}: {status} task needs a blocker or n/a reason")
    return bindings, findings


def _cycle_findings(tasks: dict[str, dict[str, str]]) -> list[str]:
    findings: list[str] = []
    state: dict[str, int] = {}

    def visit(task_id: str, path: list[str]) -> None:
        if state.get(task_id) == 2:
            return
        if state.get(task_id) == 1:
            cycle = path[path.index(task_id) :] + [task_id]
            findings.append("Activation Tasks: dependency cycle " + " -> ".join(cycle))
            return
        state[task_id] = 1
        for dependency in _parse_list(tasks[task_id].get("Depends on", "none")):
            if dependency in tasks:
                visit(dependency, path + [dependency])
        state[task_id] = 2

    for task_id in tasks:
        visit(task_id, [task_id])
    return findings


def _prd_signals(prd_text: str) -> tuple[set[str], list[str]]:
    findings: list[str] = []
    signals: set[str] = set()
    metrics_header, metrics = _table(prd_text, "## Metrics")
    if metrics_header[:3] != ["metric", "definition", "target"]:
        findings.append("PRD: Metrics table is missing or has unexpected columns")
    else:
        for row in metrics:
            if len(row) >= 3 and row[0]:
                signals.add(row[0])
    tests_header, tests = _table(prd_text, "## Test Obligations")
    expected_tests = ["test id", "obligation", "test type", "required", "upstream trace ids", "expected signal"]
    if tests_header[:6] != expected_tests:
        findings.append("PRD: Test Obligations table is missing or has unexpected columns")
    else:
        for row in tests:
            if len(row) >= 6 and row[3].lower() == "yes":
                signals.add(row[0])
    return signals, findings


def check_activation_text(
    text: str,
    *,
    prd_text: str | None = None,
    require_filled: bool = False,
    require_verified_sources: bool = False,
    require_ready: tuple[str, ...] = (),
) -> list[str]:
    findings: list[str] = []
    for heading in REQUIRED_SECTIONS:
        if _section(text, heading) is None:
            findings.append(f"missing required section {heading}")
    if text.count("# Product Activation") != 1:
        findings.append("expected one # Product Activation title")
    for pattern, label in (
        (PRIVATE_KEY_RE, "private key"),
        (BEARER_RE, "bearer credential"),
        (CREDENTIAL_URL_RE, "credential-bearing URL"),
        (KNOWN_SECRET_RE, "known secret value pattern"),
    ):
        if pattern.search(text):
            findings.append(f"secret safety: document contains a {label}")

    record, record_findings = _record(text)
    findings.extend(record_findings)
    if record:
        if record.get("Schema") != "product-activation/1":
            findings.append("Record: Schema must be product-activation/1")
        if record.get("Status") not in RECORD_STATUSES:
            findings.append(f"Record: invalid status {record.get('Status')!r}")
        findings.extend(_value_findings("Record", list(record.values()), require_filled))

    tables, table_findings = _validate_tables(text, require_filled)
    findings.extend(table_findings)
    findings.extend(_validate_profiles(tables.get("## Applied Profiles", [])))
    capabilities, capability_findings = _validate_capabilities(
        tables.get("## Capability Observations", [])
    )
    findings.extend(capability_findings)
    evidence, evidence_findings = _validate_evidence(tables.get("## Verification Evidence", []))
    findings.extend(evidence_findings)
    sources, source_findings = _validate_sources(tables.get("## Measurement Sources", []), evidence)
    findings.extend(source_findings)

    manual: dict[str, str] = {}
    for item_id, owner, step, expected, status in tables.get("## Manual Handoff", []):
        if status not in HANDOFF_STATUSES and not _placeholder(status):
            findings.append(f"Manual Handoff: {item_id} has invalid status {status!r}")
        if item_id in manual:
            findings.append(f"Manual Handoff: duplicate item {item_id}")
        manual[item_id] = status
        if require_filled and any(_placeholder(value) for value in (owner, step, expected)):
            findings.append(f"Manual Handoff: {item_id} has unresolved fields")

    tasks, titles, task_parse_findings = _tasks(text)
    findings.extend(task_parse_findings)
    task_bindings: dict[str, dict[str, str]] = {}
    for task_id, task in tasks.items():
        if require_filled and _placeholder(titles.get(task_id, "")):
            findings.append(f"{task_id}: unresolved task title")
        bindings, task_findings = _task_findings(
            task_id,
            task,
            tasks,
            capabilities,
            evidence,
            manual,
            require_filled or require_verified_sources,
        )
        task_bindings[task_id] = bindings
        findings.extend(task_findings)
    findings.extend(_cycle_findings(tasks))

    for evidence_id, item in evidence.items():
        if item["item_id"] not in tasks and item["item_id"] not in sources:
            findings.append(f"Verification Evidence: {evidence_id} references unknown item {item['item_id']}")

    coverage_rows = tables.get("## Outcome Coverage", [])
    coverage: dict[str, dict[str, object]] = {}
    for signal, definition, window, targets, source_id, status in coverage_rows:
        if _placeholder(signal):
            continue
        if signal in coverage:
            findings.append(f"Outcome Coverage: duplicate signal {signal}")
        if status not in SOURCE_STATUSES:
            findings.append(f"Outcome Coverage: {signal} has invalid status {status!r}")
        if source_id not in {"pending", "n/a"} and source_id not in sources:
            findings.append(f"Outcome Coverage: {signal} references unknown source {source_id}")
        if status == "verified" and (
            source_id not in sources or sources[source_id]["status"] != "verified"
        ):
            findings.append(f"Outcome Coverage: verified signal {signal} needs a verified source")
        coverage[signal] = {
            "definition": definition,
            "window": window,
            "targets": set(_parse_list(targets)),
            "source_id": source_id,
            "status": status,
        }
    if prd_text is not None:
        expected, prd_findings = _prd_signals(prd_text)
        findings.extend(prd_findings)
        actual = set(coverage)
        for signal in sorted(expected - actual):
            findings.append(f"Outcome Coverage: missing PRD signal {signal}")
        for signal in sorted(actual - expected):
            findings.append(f"Outcome Coverage: unknown PRD signal {signal}")

    readiness: dict[str, dict[str, str]] = {}
    for target, identity, status, checked, blockers in tables.get("## Target Readiness", []):
        if _placeholder(target):
            continue
        if target in readiness:
            findings.append(f"Target Readiness: duplicate release target {target}")
        if status not in READINESS_STATUSES:
            findings.append(f"Target Readiness: {target} has invalid status {status!r}")
        readiness[target] = {
            "identity": identity,
            "status": status,
            "checked": checked,
            "blockers": blockers,
        }
        if status == "ready":
            if not SHA_RE.fullmatch(identity):
                findings.append(f"Target Readiness: ready target {target} needs a full lowercase Git SHA")
            if checked.lower() in ABSENT or blockers.lower() not in {"", "none", "n/a"}:
                findings.append(f"Target Readiness: ready target {target} needs checked time and no blockers")
            bound = [
                task_id
                for task_id, bindings in task_bindings.items()
                if target in bindings and tasks[task_id].get("Required", "").lower() == "yes"
            ]
            if not bound:
                findings.append(f"Target Readiness: ready target {target} has no required ACT tasks")
            for task_id in bound:
                if task_bindings[task_id][target] != identity:
                    findings.append(f"Target Readiness: {target} identity differs from {task_id} release binding")
                if tasks[task_id].get("Status") != "verified":
                    findings.append(f"Target Readiness: {target} has unverified task {task_id}")
            for signal, item in coverage.items():
                if target in item["targets"] and item["status"] not in {"verified", "n/a"}:
                    findings.append(f"Target Readiness: {target} has unverified outcome signal {signal}")

    if require_verified_sources:
        require_filled = True
        if record.get("Status") != "handoff_ready":
            findings.append("Record: verified-source handoff requires status handoff_ready")
        for signal, item in coverage.items():
            if item["status"] not in {"verified", "n/a"}:
                findings.append(f"Outcome Coverage: signal {signal} is not verified")
        for source_id, item in sources.items():
            if item["status"] not in {"verified", "n/a", "superseded"}:
                findings.append(f"Measurement Sources: source {source_id} is not verified")
    for target in require_ready:
        row = readiness.get(target)
        if row is None:
            findings.append(f"Target Readiness: missing required target {target}")
        elif row["status"] != "ready":
            findings.append(f"Target Readiness: required target {target} is not ready")
    if record.get("Status") == "handoff_ready" and readiness and any(
        row["status"] != "ready" for row in readiness.values()
    ):
        findings.append("Record: handoff_ready requires every listed target to be ready")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation", type=Path, default=Path("docs/ACTIVATION.md"))
    parser.add_argument("--prd", type=Path)
    parser.add_argument("--require-filled", action="store_true")
    parser.add_argument("--require-verified-sources", action="store_true")
    parser.add_argument("--require-ready", action="append", default=[])
    parser.add_argument("--show-action-digests", action="store_true")
    args = parser.parse_args(argv)
    if not args.activation.is_file():
        print(f"activation record not found: {args.activation}", file=sys.stderr)
        return 2
    if args.prd is not None and not args.prd.is_file():
        print(f"PRD not found: {args.prd}", file=sys.stderr)
        return 2
    text = args.activation.read_text(encoding="utf-8")
    prd_text = args.prd.read_text(encoding="utf-8") if args.prd is not None else None
    tasks, _titles, parse_findings = _tasks(text)
    if args.show_action_digests:
        for task_id in sorted(tasks):
            if set(TASK_FIELDS) <= set(tasks[task_id]):
                print(f"{task_id} {action_digest(task_id, tasks[task_id])}")
        if parse_findings:
            return 1
    findings = check_activation_text(
        text,
        prd_text=prd_text,
        require_filled=args.require_filled,
        require_verified_sources=args.require_verified_sources,
        require_ready=tuple(args.require_ready),
    )
    for finding in findings:
        print(f"{args.activation}: {finding}")
    if findings:
        return 1
    print(f"{args.activation} satisfies the requested Product Activation checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
