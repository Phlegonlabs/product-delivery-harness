#!/usr/bin/env python3
"""Read-only architecture-bound structural and readiness checks for ACTIVATION.md."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path

SIBLING_SCRIPTS_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_DEFINITION_SCRIPTS = (
    SIBLING_SCRIPTS_ROOT / "product-definition-builder" / "scripts"
)
DELIVERY_SCRIPTS = SIBLING_SCRIPTS_ROOT / "delivery-harness" / "scripts"
for sibling_scripts in (PRODUCT_DEFINITION_SCRIPTS, DELIVERY_SCRIPTS):
    if str(sibling_scripts) not in sys.path:
        sys.path.insert(0, str(sibling_scripts))

from check_deployment import (  # noqa: E402
    parse_release_target_status,
    release_target_status_duplicates,
)
from markdown_contract import active_markdown_lines, active_text, is_human_owner  # noqa: E402
from release_targets import (  # noqa: E402
    allows_no_independent_artifact,
    parse_release_targets,
)


TASK_START = "<!-- activation-task-contract:start -->"
TASK_END = "<!-- activation-task-contract:end -->"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
ACT_ID_RE = re.compile(r"^ACT-[0-9]{3}$")
MS_ID_RE = re.compile(r"^MS-[0-9]{3}$")
EVIDENCE_ID_RE = re.compile(r"^EVID-[0-9]{3}$")
CAPABILITY_ID_RE = re.compile(r"^CAP-[0-9]{3}$")
BLOCKER_ID_RE = re.compile(r"^BLOCK-[0-9]{3}$")
ARTIFACT_ID_RE = re.compile(r"^(?:n/a|[A-Za-z0-9][A-Za-z0-9._:+-]*)$")
NO_INDEPENDENT_ARTIFACT_VALUES = {
    "no independent artifact",
    "no-independent-artifact",
}
TASK_HEADING_RE = re.compile(r"^###\s+(ACT-[0-9]{3})\s+[—-]\s+(.+?)\s*$")
FIELD_RE = re.compile(r"^- ([A-Za-z][A-Za-z /-]*):\s*(.*)$")
PLACEHOLDER_RE = re.compile(r"<[^>\n]+>|\bTBD\b", re.IGNORECASE)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
BEARER_RE = re.compile(r"Authorization\s*:\s*Bearer\s+\S+", re.IGNORECASE)
CREDENTIAL_URL_RE = re.compile(r"https?://[^\s/:]+:[^\s/@]+@", re.IGNORECASE)
KNOWN_SECRET_RE = re.compile(
    r"\b(?:sk_(?:live|test|proj)_[A-Za-z0-9]+|sk-(?:live|test|proj)-[A-Za-z0-9_-]+|rk_(?:live|test)_[A-Za-z0-9]+|ghp_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|xox[baprs]-[A-Za-z0-9-]+|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,})\b"
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
        "observation id",
        "route",
        "status",
        "supports",
        "target scope",
        "environment",
        "checked",
        "evidence",
    ),
    "## Outcome Coverage": (
        "signal",
        "definition / obligation",
        "baseline",
        "target / guardrail",
        "measurement window",
        "expected signal",
        "release targets",
        "source id",
        "status",
    ),
    "## Measurement Sources": (
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
    ),
    "## Verification Evidence": (
        "evidence id",
        "item id",
        "kind",
        "route / action / release binding",
        "checked",
        "result",
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
        "stage",
        "provider / channel",
        "source sha",
        "artifact / build identity",
        "availability state",
        "status",
        "checked",
        "n/a reason",
        "blockers",
    ),
    "## Open Blockers": (
        "blocker id",
        "release targets",
        "kind",
        "owner",
        "next step",
        "status",
        "notes",
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
    "Risk tags",
    "Risk",
    "Confirmation",
    "Execution route",
    "Execution capability",
    "Read-back route",
    "Read-back capability",
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
SUPPORTS = {"read", "write", "readback"}
SOURCE_STATUSES = {"planned", "available", "verified", "blocked", "superseded", "n/a"}
SOURCE_ROLES = {
    "search_console",
    "ga4",
    "production_page",
    "google_trends",
    "keyword_planner",
    "public_serp",
    "first_party",
}
TASK_STATUSES = {"pending", "ready", "configured", "verified", "uncertain", "blocked", "stale", "n/a"}
RECORD_STATUSES = {"seeded", "preparation", "active", "handoff_ready", "blocked", "n/a"}
READINESS_STATUSES = {"preparation", "pending", "ready", "blocked", "n/a"}
TARGET_AVAILABILITY_STATES = {"deployed", "installable", "downloadable", "unavailable", "pending", "n/a"}
EVIDENCE_KINDS = {"write", "readback", "behavior", "capability", "manual"}
EVIDENCE_RESULTS = {"PASS", "FAIL", "BLOCKED", "UNCERTAIN"}
AUTHORIZATIONS = {"not_required", "pending", "approved", "consumed", "denied", "expired", "handoff_complete", "prohibited"}
OPERATIONS = {"read", "create", "update", "upload", "publish", "transmit", "delete", "rotate", "revoke", "execute"}
RISK_CONFIRMATION = {
    "read_only": "read_only",
    "standard": "exact_preapproval",
    "high": "action_time_confirmation",
    "handoff": "user_handoff",
    "prohibited": "prohibited",
}
RISK_TAGS = {
    "dns",
    "permissions",
    "persistent_access",
    "billing",
    "production_traffic",
    "public_submission",
    "data_sharing",
    "advertising_tracking",
    "upload",
    "destructive",
}
HANDOFF_STATUSES = {"pending", "completed", "n/a"}
BLOCKER_STATUSES = {"open", "resolved", "n/a"}
ABSENT = {"", "none", "n/a", "pending", "unselected"}
FORBIDDEN_HEADERS = {"value", "secret value", "token", "password", "credential"}


def _placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.search(value))


def _human(value: str) -> bool:
    return is_human_owner(value)


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


def _duplicate_sections(text: str, headings: tuple[str, ...]) -> list[str]:
    active_lines = active_text(text).splitlines()
    findings: list[str] = []
    for heading in headings:
        count = sum(line.strip() == heading for line in active_lines)
        if count > 1:
            findings.append(f"duplicate required section {heading}")
    return findings


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


def _n_a_with_reason(value: str) -> bool:
    return bool(
        re.fullmatch(r"n/a\s*(?::|-|—|–)\s*\S.*", value.strip(), re.IGNORECASE)
    )


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


def action_digest(
    task_id: str,
    task: dict[str, str],
    capability_scopes: dict[str, str] | None = None,
) -> str:
    scopes = capability_scopes or {}
    payload = {
        "schema": "activation-action/2",
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
        "risk_tags": sorted(_normal(item) for item in _parse_list(task["Risk tags"])),
        "risk": _normal(task["Risk"]),
        "confirmation": _normal(task["Confirmation"]),
        "execution_route": _normal(task["Execution route"]),
        "execution_capability": _normal(task["Execution capability"]),
        "execution_capability_scope": _normal(
            scopes.get(task["Execution capability"], "")
        ),
        "readback_route": _normal(task["Read-back route"]),
        "readback_capability": _normal(task["Read-back capability"]),
        "readback_capability_scope": _normal(
            scopes.get(task["Read-back capability"], "")
        ),
        "verification": _normal(task["Verification"]),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _tasks(text: str) -> tuple[dict[str, dict[str, str]], dict[str, str], list[str]]:
    findings: list[str] = []
    active = "\n".join(
        line
        for _, line in active_markdown_lines(
            text, machine_markers=(TASK_START, TASK_END)
        )
    )
    if active.count(TASK_START) != 1 or active.count(TASK_END) != 1:
        return {}, {}, ["Activation Tasks: expected one matched task-contract boundary pair"]
    body = active.split(TASK_START, 1)[1].split(TASK_END, 1)[0]
    before, after_start = active.split(TASK_START, 1)
    _inside, after = after_start.split(TASK_END, 1)
    for line in (before + "\n" + after).splitlines():
        heading = TASK_HEADING_RE.match(line.strip())
        if heading:
            findings.append(
                f"Activation Tasks: {heading.group(1)} heading is outside the task-contract boundaries"
            )
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


KNOWN_PROFILES = {
    "core",
    "web",
    "web-auth",
    "forms-leads",
    "transactional-email",
    "payments",
    "cms-content",
    "localization",
    "uploads-media",
    "pwa",
    "search",
    "background-jobs",
    "feature-flags",
    "paid-acquisition",
    "app-extension-linking",
    "regulated-or-ha",
    "ios",
    "android",
    "api / backend",
    "api-webhooks",
    "api-background-jobs",
    "api-data-export",
    "api-partner-access",
    "macos",
    "windows",
    "browser extension",
}


def _surface_profiles(architecture_targets: dict[str, object]) -> set[str]:
    profiles = {"core"}
    for target in architecture_targets.values():
        surface_class = str(getattr(target, "surface_class", "")).casefold()
        if surface_class == "ios":
            profiles.add("ios")
        elif surface_class == "android":
            profiles.add("android")
        elif surface_class == "macos":
            profiles.add("macos")
        elif surface_class == "windows":
            profiles.add("windows")
        elif surface_class == "browser_extension":
            profiles.add("browser extension")
        elif surface_class in {"hosted_api", "worker", "job", "webhook", "realtime"}:
            profiles.add("api / backend")
        elif surface_class == "hosted_web":
            profiles.add("web")
    return profiles


def _validate_profiles(
    rows: list[list[str]],
    architecture_targets: dict[str, object] | None = None,
    require_filled: bool = False,
) -> list[str]:
    findings: list[str] = []
    if not rows:
        return ["Applied Profiles: at least the core profile is required"]
    seen: set[str] = set()
    for profile, applies, reason, owner in rows:
        if not require_filled and any(_placeholder(value) for value in (profile, applies, reason, owner)):
            continue
        if _placeholder(profile) or _placeholder(applies):
            continue
        key = profile.lower()
        if key in seen:
            findings.append(f"Applied Profiles: duplicate profile {profile}")
        seen.add(key)
        if key not in KNOWN_PROFILES:
            findings.append(f"Applied Profiles: unknown profile {profile}")
        if applies.lower() not in {"yes", "no"}:
            findings.append(f"Applied Profiles: {profile} applies must be yes or no")
        if reason.strip().casefold() in ABSENT or not _human(owner):
            findings.append(f"Applied Profiles: {profile} needs a reason and owner")
    if rows and not any(row[0].lower() == "core" and row[1].lower() == "yes" for row in rows):
        findings.append("Applied Profiles: core must apply")
    if architecture_targets:
        actual = {row[0].casefold() for row in rows if len(row) >= 2 and row[1].casefold() == "yes"}
        required = _surface_profiles(architecture_targets)
        for profile in sorted(required - actual):
            findings.append(
                f"Applied Profiles: architecture release targets require profile {profile!r}"
            )
        for profile in sorted(actual - required):
            if profile not in KNOWN_PROFILES:
                findings.append(f"Applied Profiles: profile {profile!r} is not in the closed catalog")
    return findings


def _validate_capabilities(rows: list[list[str]]) -> tuple[dict[str, dict[str, object]], list[str]]:
    findings: list[str] = []
    capabilities: dict[str, dict[str, object]] = {}
    if not rows:
        findings.append("Capability Observations: keep at least one route row")
    for observation_id, route, status, supports, target_scope, environment, checked, evidence in rows:
        if _placeholder(observation_id):
            continue
        if not CAPABILITY_ID_RE.fullmatch(observation_id):
            findings.append(f"Capability Observations: invalid observation ID {observation_id!r}")
            continue
        if route not in ROUTES - {"unselected"}:
            findings.append(f"Capability Observations: {observation_id} has unsupported route {route}")
        if observation_id in capabilities:
            findings.append(f"Capability Observations: duplicate observation {observation_id}")
            continue
        support_set = set(_parse_list(supports.lower()))
        if supports.lower() == "n/a":
            support_set = set()
        if status not in CAPABILITY_STATUSES:
            findings.append(f"Capability Observations: {observation_id} has invalid status {status!r}")
        if support_set - SUPPORTS:
            findings.append(f"Capability Observations: {observation_id} has unsupported capabilities")
        if status in {"available", "human_only"} and (
            not support_set
            or target_scope.lower() in ABSENT
            or environment.lower() in ABSENT
            or _placeholder(target_scope)
            or _placeholder(environment)
            or checked.lower() in ABSENT
            or evidence.lower() in ABSENT
        ):
            findings.append(
                f"Capability Observations: {status} observation {observation_id} needs supports, exact target scope, environment, checked time, and evidence"
            )
        if status == "human_only" and route != "manual":
            findings.append(
                f"Capability Observations: human_only observation {observation_id} must use manual route"
            )
        if route == "manual" and status == "available":
            findings.append(
                f"Capability Observations: manual observation {observation_id} must use human_only, unavailable, or unobserved status"
            )
        if status == "unavailable" and (
            target_scope.lower() in ABSENT
            or environment.lower() in ABSENT
            or checked.lower() in ABSENT
            or evidence.lower() in ABSENT
        ):
            findings.append(
                f"Capability Observations: unavailable observation {observation_id} needs exact scope, environment, checked time, and evidence"
            )
        checked_at = _timestamp(checked)
        if status in {"available", "human_only", "unavailable"} and checked_at is None:
            findings.append(
                f"Capability Observations: {observation_id} needs an RFC3339 checked time"
            )
        elif checked_at is not None and not _not_future(checked_at):
            findings.append(
                f"Capability Observations: {observation_id} checked time cannot be in the future"
            )
        capabilities[observation_id] = {
            "status": status,
            "supports": support_set,
            "route": route,
            "target_scope": target_scope,
            "environment": environment,
            "checked_at": checked_at,
        }
    return capabilities, findings


def _validate_evidence(rows: list[list[str]]) -> tuple[dict[str, dict[str, object]], list[str]]:
    findings: list[str] = []
    evidence: dict[str, dict[str, object]] = {}
    for evidence_id, item_id, kind, binding, checked, result, reference in rows:
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
        parts = [part.strip() for part in binding.split(";")]
        route = ""
        action = ""
        release_binding = ""
        if len(parts) != 3:
            findings.append(
                f"Verification Evidence: {evidence_id} binding must be route;action-digest-or-n/a;target@sha#artifact"
            )
        else:
            route, action, release_binding = parts
        if route not in ROUTES - {"unselected"}:
            findings.append(f"Verification Evidence: {evidence_id} has invalid route {route!r}")
        if action != "n/a" and not SHA256_RE.fullmatch(action):
            findings.append(
                f"Verification Evidence: {evidence_id} needs a lowercase action digest or n/a"
            )
        parsed, binding_findings = _release_bindings(
            release_binding, f"Verification Evidence: {evidence_id}", True
        )
        findings.extend(binding_findings)
        if len(parsed) != 1:
            findings.append(
                f"Verification Evidence: {evidence_id} needs exactly one release binding"
            )
        if checked.lower() in ABSENT or reference.lower() in ABSENT:
            findings.append(f"Verification Evidence: {evidence_id} needs checked time and reference")
        checked_at = _timestamp(checked)
        if checked_at is None:
            findings.append(f"Verification Evidence: {evidence_id} needs an RFC3339 checked time")
        elif not _not_future(checked_at):
            findings.append(f"Verification Evidence: {evidence_id} checked time cannot be in the future")
        evidence[evidence_id] = {
            "item_id": item_id,
            "kind": kind,
            "result": result,
            "route": route,
            "action_digest": action,
            "release_binding": release_binding,
            "checked": checked,
            "checked_at": checked_at,
        }
    return evidence, findings


def _validate_sources(
    rows: list[list[str]],
    capabilities: dict[str, dict[str, object]],
    evidence: dict[str, dict[str, object]],
    require_filled: bool,
) -> tuple[dict[str, dict[str, object]], list[str]]:
    findings: list[str] = []
    sources: dict[str, dict[str, object]] = {}
    for (
        source_id,
        target,
        environment,
        retrieval,
        source_role,
        route_capability,
        release_bindings,
        owner,
        status,
        evidence_ids,
    ) in rows:
        if not MS_ID_RE.fullmatch(source_id):
            findings.append(f"Measurement Sources: invalid source ID {source_id!r}")
            continue
        if source_id in sources:
            findings.append(f"Measurement Sources: duplicate source ID {source_id}")
            continue
        if target.lower() in ABSENT or environment.lower() in ABSENT or retrieval.lower() in ABSENT:
            findings.append(
                f"Measurement Sources: {source_id} needs exact target, environment, and bounded retrieval"
            )
        if source_role not in SOURCE_ROLES and not _placeholder(source_role):
            findings.append(
                f"Measurement Sources: {source_id} has invalid source role {source_role!r}"
            )
        route_parts = [part.strip() for part in route_capability.split(";")]
        route = route_parts[0] if route_parts else ""
        capability_id = route_parts[1] if len(route_parts) == 2 else ""
        if len(route_parts) != 2:
            findings.append(f"Measurement Sources: {source_id} needs route;CAP-ID")
        if route not in ROUTES:
            findings.append(f"Measurement Sources: {source_id} has invalid route {route!r}")
        if capability_id not in {"pending", "n/a"} and not CAPABILITY_ID_RE.fullmatch(capability_id):
            findings.append(
                f"Measurement Sources: {source_id} has invalid capability {capability_id!r}"
            )
        capability = capabilities.get(capability_id)
        if CAPABILITY_ID_RE.fullmatch(capability_id) and capability is None:
            findings.append(f"Measurement Sources: {source_id} has unknown capability {capability_id}")
        elif capability:
            if capability["route"] != route:
                findings.append(
                    f"Measurement Sources: {source_id} capability uses another route"
                )
            if capability["target_scope"] != target:
                findings.append(
                    f"Measurement Sources: {source_id} capability does not match the exact target"
                )
            if capability["environment"] != environment:
                findings.append(
                    f"Measurement Sources: {source_id} capability does not match the environment"
                )
        if status not in SOURCE_STATUSES:
            findings.append(f"Measurement Sources: {source_id} has invalid status {status!r}")
        bindings, binding_findings = _release_bindings(
            release_bindings, f"Measurement Sources: {source_id}", require_filled or status in {"available", "verified"}
        )
        findings.extend(binding_findings)
        if status in {"available", "verified"} and not bindings:
            findings.append(
                f"Measurement Sources: {source_id} needs at least one exact release binding"
            )
        if owner.strip().casefold() not in ABSENT and (
            require_filled or not _placeholder(owner)
        ) and not _human(owner):
            findings.append(f"Measurement Sources: {source_id} owner must name a human")
        elif status in {"available", "verified"} and not _human(owner):
            findings.append(f"Measurement Sources: {source_id} needs a human owner")
        ids = _parse_list(evidence_ids)
        for evidence_id in ids:
            if evidence_id not in evidence:
                findings.append(f"Measurement Sources: {source_id} references unknown evidence {evidence_id}")
            elif evidence[evidence_id]["item_id"] != source_id:
                findings.append(f"Measurement Sources: {source_id} evidence {evidence_id} belongs to another item")
                continue
            item = evidence[evidence_id]
            if item["route"] != route:
                findings.append(
                    f"Measurement Sources: {source_id} evidence {evidence_id} uses another route"
                )
            if item["action_digest"] != "n/a":
                findings.append(
                    f"Measurement Sources: {source_id} evidence {evidence_id} must use action digest n/a"
                )
            if item["release_binding"] not in {
                binding["text"] for binding in bindings.values()
            }:
                findings.append(
                    f"Measurement Sources: {source_id} evidence {evidence_id} uses another release binding"
                )
            capability_checked = capability["checked_at"] if capability else None
            if (
                isinstance(capability_checked, datetime)
                and isinstance(item["checked_at"], datetime)
                and item["checked_at"] < capability_checked
            ):
                findings.append(
                    f"Measurement Sources: {source_id} evidence {evidence_id} predates its capability probe"
                )
        if status in {"available", "verified"}:
            accepted_statuses = {"available"} if status == "verified" else {"available", "human_only"}
            if not capability or capability["status"] not in accepted_statuses:
                findings.append(
                    f"Measurement Sources: {source_id} capability is not available"
                )
            else:
                if not ({"read", "readback"} & capability["supports"]):
                    findings.append(
                        f"Measurement Sources: {source_id} capability does not support retrieval"
                    )
        if status == "verified":
            for binding in bindings.values():
                matching_kinds = {
                    item["kind"]
                    for evidence_id in ids
                    if evidence_id in evidence
                    for item in (evidence[evidence_id],)
                    if item["item_id"] == source_id
                    and item["kind"] in {"readback", "behavior"}
                    and item["route"] == route
                    and item["action_digest"] == "n/a"
                    and item["release_binding"] == binding["text"]
                }
                if not matching_kinds or any(
                    not _has_matching_evidence(
                        ids,
                        evidence,
                        source_id,
                        {kind},
                        route,
                        "n/a",
                        binding["text"],
                    )
                    for kind in matching_kinds
                ):
                    findings.append(
                        f"Measurement Sources: verified source {source_id} needs PASS evidence for {binding['text']}"
                    )
        sources[source_id] = {
            "target": target,
            "environment": environment,
            "retrieval": retrieval,
            "source_role": source_role,
            "route": route,
            "capability_id": capability_id,
            "bindings": bindings,
            "targets": set(bindings),
            "owner": owner,
            "status": status,
            "evidence_ids": ids,
        }
    return sources, findings


def _release_bindings(
    value: str, label: str, require_filled: bool
) -> tuple[dict[str, dict[str, str]], list[str]]:
    findings: list[str] = []
    bindings: dict[str, dict[str, str]] = {}
    for item in _parse_list(value):
        if item.count("@") != 1 or item.count("#") != 1:
            findings.append(
                f"{label}: release binding {item!r} must be target@sha#artifact"
            )
            continue
        target, identity = item.rsplit("@", 1)
        sha, artifact = identity.split("#", 1)
        if not target or target in bindings:
            findings.append(f"{label}: duplicate or empty release target in {item!r}")
            continue
        pending = sha == "pending" or artifact == "pending"
        if pending and (sha, artifact) != ("pending", "pending"):
            findings.append(f"{label}: release binding {item!r} has a partial pending identity")
        if sha != "pending" and not SHA_RE.fullmatch(sha):
            findings.append(f"{label}: release binding {item!r} needs a full lowercase Git SHA")
        if artifact != "pending" and not ARTIFACT_ID_RE.fullmatch(artifact):
            findings.append(f"{label}: release binding {item!r} has an invalid artifact identity")
        if require_filled and (pending or _placeholder(target) or _placeholder(artifact)):
            findings.append(f"{label}: unresolved release binding {item!r}")
        bindings[target] = {"sha": sha, "artifact": artifact, "text": item}
    return bindings, findings


def _has_matching_evidence(
    evidence_ids: list[str],
    evidence: dict[str, dict[str, object]],
    item_id: str,
    kinds: set[str],
    route: str,
    action_digest_value: str,
    release_binding: str,
    result: str = "PASS",
) -> bool:
    matches = [
        evidence[evidence_id]
        for evidence_id in evidence_ids
        if evidence_id in evidence
        and evidence[evidence_id]["item_id"] == item_id
        and evidence[evidence_id]["kind"] in kinds
        and evidence[evidence_id]["route"] == route
        and evidence[evidence_id]["action_digest"] == action_digest_value
        and evidence[evidence_id]["release_binding"] == release_binding
        and isinstance(evidence[evidence_id]["checked_at"], datetime)
    ]
    if not matches:
        return False
    latest = max(item["checked_at"] for item in matches)
    return all(item["result"] == result for item in matches if item["checked_at"] == latest)


def _matching_evidence_times(
    evidence_ids: list[str],
    evidence: dict[str, dict[str, object]],
    item_id: str,
    kinds: set[str],
    route: str,
    action_digest_value: str,
    release_binding: str,
    result: str = "PASS",
) -> list[datetime]:
    return [
        item["checked_at"]
        for evidence_id in evidence_ids
        if evidence_id in evidence
        for item in (evidence[evidence_id],)
        if item["item_id"] == item_id
        and item["kind"] in kinds
        and item["result"] == result
        and item["route"] == route
        and item["action_digest"] == action_digest_value
        and item["release_binding"] == release_binding
        and isinstance(item["checked_at"], datetime)
    ]


def _task_findings(
    task_id: str,
    task: dict[str, str],
    tasks: dict[str, dict[str, str]],
    capabilities: dict[str, dict[str, object]],
    evidence: dict[str, dict[str, object]],
    manual: dict[str, str],
    require_filled: bool,
) -> tuple[dict[str, dict[str, str]], list[str]]:
    findings: list[str] = []
    if set(TASK_FIELDS) - set(task):
        return {}, findings
    values = [task[field] for field in TASK_FIELDS]
    findings.extend(_value_findings(task_id, values, require_filled))
    operation = task["Operation"]
    risk = task["Risk"]
    confirmation = task["Confirmation"]
    route = task["Execution route"]
    execution_capability = task["Execution capability"]
    readback_route = task["Read-back route"]
    readback_capability = task["Read-back capability"]
    authorization = task["Authorization"]
    status = task["Status"]
    updated_at = _timestamp(task["Updated"])
    if updated_at is not None and not _not_future(updated_at):
        findings.append(f"{task_id}: Updated cannot be in the future")
    verification_is_na = _n_a_with_reason(task["Verification"])
    risk_tags = set(_parse_list(task["Risk tags"].lower()))
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
    high_operations = {"upload", "publish", "transmit", "delete", "rotate", "revoke"}
    execution_observation = capabilities.get(execution_capability)
    readback_observation = capabilities.get(readback_capability)
    human_execution = route == "manual" or (
        execution_observation is not None and execution_observation["status"] == "human_only"
    )
    if human_execution and risk != "handoff":
        findings.append(f"{task_id}: manual or human-only execution requires handoff risk")
    nonproduction_environment = task["Environment"].strip().lower() in {
        "preview",
        "development",
        "dev",
        "test",
        "testing",
        "sandbox",
        "staging",
        "stage",
        "local",
    }
    sensitive_environment = (
        operation != "read"
        and not _placeholder(task["Environment"])
        and not nonproduction_environment
    )
    sensitive_text = " ".join(
        (task["Target"], task["Desired state"], task["Operation"])
    ).lower()
    inferred_tags = {
        tag
        for tag, pattern in (
            ("dns", r"\b(?:dns|nameserver|cname|txt record|mx record)\b"),
            ("permissions", r"\b(?:permission|role|rbac|access policy|oauth scope)\b"),
            ("billing", r"\b(?:billing|invoice|tax|payment mode|payout)\b"),
            ("production_traffic", r"\b(?:production traffic|load balancer|origin route)\b"),
            ("advertising_tracking", r"\b(?:pixel|advertising|ad tracking|retargeting)\b"),
        )
        if re.search(pattern, sensitive_text)
    }
    if risk_tags - RISK_TAGS:
        findings.append(
            f"{task_id}: unsupported risk tag(s) {', '.join(sorted(risk_tags - RISK_TAGS))}"
        )
    if operation != "read":
        for tag in sorted(inferred_tags - risk_tags):
            findings.append(f"{task_id}: target requires explicit {tag} risk tag")
    if (
        operation in high_operations
        or sensitive_environment
        or (operation != "read" and (risk_tags or inferred_tags))
    ) and not human_execution and risk != "high":
        if operation in high_operations:
            reason = operation
        elif sensitive_environment:
            reason = "non-preview"
        else:
            reason = "sensitive"
        findings.append(f"{task_id}: {reason} operation requires high risk")
    if route not in ROUTES or readback_route not in ROUTES:
        findings.append(f"{task_id}: invalid execution or read-back route")
    for label, capability_id, expected_route, observation in (
        ("execution", execution_capability, route, execution_observation),
        ("read-back", readback_capability, readback_route, readback_observation),
    ):
        if capability_id not in {"pending", "n/a"} and not CAPABILITY_ID_RE.fullmatch(
            capability_id
        ):
            findings.append(f"{task_id}: invalid {label} capability {capability_id!r}")
        elif CAPABILITY_ID_RE.fullmatch(capability_id) and observation is None:
            findings.append(f"{task_id}: unknown {label} capability {capability_id}")
        elif observation:
            if observation["route"] != expected_route:
                findings.append(f"{task_id}: {label} capability uses another route")
            if observation["target_scope"] != task["Target"]:
                findings.append(
                    f"{task_id}: {label} capability does not match the exact target"
                )
            if observation["environment"] != task["Environment"]:
                findings.append(
                    f"{task_id}: {label} capability does not match the environment"
                )
    if authorization not in AUTHORIZATIONS:
        findings.append(f"{task_id}: invalid authorization {authorization!r}")
    if status not in TASK_STATUSES:
        findings.append(f"{task_id}: invalid status {status!r}")
    if (
        task["Updated"].lower() not in ABSENT
        and not _placeholder(task["Updated"])
        and updated_at is None
    ):
        findings.append(f"{task_id}: Updated must be an RFC3339 timestamp")
    if status in {"ready", "configured", "verified", "uncertain", "blocked", "stale"} and updated_at is None:
        findings.append(f"{task_id}: {status} task needs an RFC3339 Updated timestamp")
    if task["Required"].lower() not in {"yes", "no"}:
        findings.append(f"{task_id}: Required must be yes or no")
    if task["Required"].lower() == "yes" and status == "n/a":
        findings.append(f"{task_id}: a required task cannot be n/a")
    if task["Verification"].strip().lower().startswith("n/a") and not verification_is_na:
        findings.append(f"{task_id}: Verification n/a needs a reason")
    if require_filled and status != "n/a":
        for name, value in (
            ("Source refs", task["Source refs"]),
            ("Target", task["Target"]),
            ("Environment", task["Environment"]),
            ("Precondition", task["Precondition"]),
            ("Desired state", task["Desired state"]),
            ("Execution route", route),
            ("Execution capability", execution_capability),
            ("Read-back route", readback_route),
            ("Read-back capability", readback_capability),
            ("Action digest", task["Action digest"]),
            ("Verification", task["Verification"]),
            ("Updated", task["Updated"]),
        ):
            if value.lower() in {"pending", "unselected", "n/a", ""}:
                findings.append(f"{task_id}: filled task needs {name}")
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
    if not bindings and (
        status in {"ready", "configured", "verified", "uncertain"}
        or (require_filled and task["Required"].lower() == "yes" and status != "n/a")
    ):
        findings.append(f"{task_id}: actionable task needs at least one exact release binding")
    dependencies = _parse_list(task["Depends on"])
    for dependency in dependencies:
        if dependency not in tasks:
            findings.append(f"{task_id}: unknown dependency {dependency}")
    names = _parse_list(task["Secret names"])
    for name in names:
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", name) is None:
            findings.append(f"{task_id}: secret name {name!r} is not a value-free configuration name")

    capability_scopes = {
        capability_id: str(observation["target_scope"])
        for capability_id, observation in capabilities.items()
    }
    computed = action_digest(task_id, task, capability_scopes)
    recorded = task["Action digest"]
    authorized = task["Authorized digest"]
    if recorded != "pending" and (not SHA256_RE.fullmatch(recorded) or recorded != computed):
        findings.append(f"{task_id}: Action digest does not match the current action")
    if status in {"ready", "configured", "verified", "uncertain"} and recorded != computed:
        findings.append(f"{task_id}: executable or attempted action needs its current Action digest")
    if authorization in {"approved", "consumed", "handoff_complete"} and authorized != computed:
        findings.append(f"{task_id}: Authorized digest must equal the current Action digest")

    evidence_ids = _parse_list(task["Evidence IDs"])
    binding_texts = {binding["text"] for binding in bindings.values()}
    for evidence_id in evidence_ids:
        if evidence_id not in evidence:
            findings.append(f"{task_id}: unknown evidence {evidence_id}")
        elif evidence[evidence_id]["item_id"] != task_id:
            findings.append(f"{task_id}: evidence {evidence_id} belongs to another item")
        else:
            item = evidence[evidence_id]
            if item["action_digest"] != computed:
                findings.append(f"{task_id}: evidence {evidence_id} has a stale action digest")
            if item["release_binding"] not in binding_texts:
                findings.append(f"{task_id}: evidence {evidence_id} uses another release binding")
            expected_route = route if item["kind"] in {"write", "manual"} else readback_route
            if item["kind"] in {"write", "manual", "readback", "behavior"} and item["route"] != expected_route:
                findings.append(f"{task_id}: evidence {evidence_id} uses another route")
            observation = (
                execution_observation
                if item["kind"] in {"write", "manual"}
                else readback_observation
            )
            capability_checked = observation["checked_at"] if observation else None
            if (
                item["kind"] in {"write", "manual", "readback", "behavior"}
                and isinstance(capability_checked, datetime)
                and isinstance(item["checked_at"], datetime)
                and item["checked_at"] < capability_checked
            ):
                findings.append(f"{task_id}: evidence {evidence_id} predates its capability probe")
    if status in {"ready", "configured", "verified", "uncertain"}:
        capability = capabilities.get(execution_capability)
        needed = "read" if operation == "read" else "write"
        if not capability or capability["status"] not in {"available", "human_only"}:
            findings.append(f"{task_id}: selected execution capability is not available")
        elif needed not in capability["supports"] and capability["status"] != "human_only":
            findings.append(f"{task_id}: selected execution capability does not support {needed}")
        for dependency in dependencies:
            if dependency in tasks and tasks[dependency].get("Status") != "verified":
                findings.append(f"{task_id}: dependency {dependency} is not verified")
    if operation != "read" and status in {"configured", "verified"}:
        for binding in bindings.values():
            if not _has_matching_evidence(
                evidence_ids,
                evidence,
                task_id,
                {"write", "manual"},
                route,
                computed,
                binding["text"],
            ):
                findings.append(
                    f"{task_id}: {status} task needs PASS write or manual evidence for {binding['text']}"
                )
    if operation != "read" and status == "uncertain":
        for binding in bindings.values():
            if not _has_matching_evidence(
                evidence_ids,
                evidence,
                task_id,
                {"write", "manual"},
                route,
                computed,
                binding["text"],
                "UNCERTAIN",
            ):
                findings.append(
                    f"{task_id}: uncertain task needs UNCERTAIN write or manual evidence for {binding['text']}"
                )
    if status == "verified":
        capability = capabilities.get(readback_capability)
        if not capability or capability["status"] != "available":
            findings.append(f"{task_id}: verified task read-back capability is not available")
        elif "readback" not in capability["supports"]:
            findings.append(f"{task_id}: verified task capability does not support readback")
        for binding in bindings.values():
            write_times = (
                _matching_evidence_times(
                    evidence_ids,
                    evidence,
                    task_id,
                    {"write", "manual"},
                    route,
                    computed,
                    binding["text"],
                )
                if operation != "read"
                else []
            )
            if not _has_matching_evidence(
                evidence_ids,
                evidence,
                task_id,
                {"readback"},
                readback_route,
                computed,
                binding["text"],
            ):
                findings.append(
                    f"{task_id}: verified task needs distinct PASS readback evidence for {binding['text']}"
                )
            readback_times = _matching_evidence_times(
                evidence_ids,
                evidence,
                task_id,
                {"readback"},
                readback_route,
                computed,
                binding["text"],
            )
            if write_times and readback_times and max(readback_times) <= max(write_times):
                findings.append(
                    f"{task_id}: readback evidence for {binding['text']} must follow write evidence"
                )
            if not verification_is_na and not _has_matching_evidence(
                evidence_ids,
                evidence,
                task_id,
                {"behavior"},
                readback_route,
                computed,
                binding["text"],
            ):
                findings.append(
                    f"{task_id}: verified task needs PASS behavior evidence for {binding['text']}"
                )
            behavior_times = _matching_evidence_times(
                evidence_ids,
                evidence,
                task_id,
                {"behavior"},
                readback_route,
                computed,
                binding["text"],
            )
            if write_times and behavior_times and max(behavior_times) <= max(write_times):
                findings.append(
                    f"{task_id}: behavior evidence for {binding['text']} must follow write evidence"
                )
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
    legacy_metrics = ["metric", "definition", "target"]
    approved_metrics = [
        "metric",
        "definition",
        "baseline",
        "target / guardrail",
        "measurement window",
        "source / method",
        "owner",
    ]
    if metrics_header != legacy_metrics and metrics_header != approved_metrics:
        findings.append("PRD: Metrics table is missing or has unexpected columns")
    else:
        metric_names: list[str] = []
        for row in metrics:
            if len(row) >= len(metrics_header) and row[0]:
                metric_names.append(row[0])
                if metrics_header == approved_metrics:
                    if any(row[index].lower() in ABSENT for index in (2, 3, 4)):
                        findings.append(
                            f"PRD: metric {row[0]} needs a concrete baseline, target / guardrail, and measurement window"
                        )
                    if not _human(row[6]):
                        findings.append(f"PRD: metric {row[0]} owner must name a human")
        duplicates = sorted(
            name for name, count in Counter(metric_names).items() if count > 1
        )
        if duplicates:
            findings.append("PRD: duplicate metric(s) " + ", ".join(duplicates))
        signals.update(metric_names)
    tests_header, tests = _table(prd_text, "## Test Obligations")
    expected_tests = ["test id", "obligation", "test type", "required", "upstream trace ids", "expected signal"]
    if tests_header[:6] != expected_tests:
        findings.append("PRD: Test Obligations table is missing or has unexpected columns")
    else:
        for row in tests:
            if len(row) >= 6 and row[3].lower() == "yes":
                signals.add(row[0])
                if row[5].lower() in ABSENT:
                    findings.append(
                        f"PRD: required test {row[0]} needs a concrete expected signal"
                    )
    return signals, findings


def _prd_signal_details(prd_text: str) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Return the structured PRD contract that Outcome Coverage must repeat exactly."""

    details: dict[str, dict[str, str]] = {}
    findings: list[str] = []
    metrics_header, metrics = _table(prd_text, "## Metrics")
    if metrics_header == ["metric", "definition", "target"]:
        for row in metrics:
            if len(row) != 3:
                continue
            name, definition, target = row
            details[name] = {
                "definition": definition,
                "baseline": "none recorded",
                "target": target,
                "window": "n/a — PRD legacy metric table omits a separate measurement window",
                "expected": "n/a — metric row",
            }
    elif metrics_header == [
        "metric",
        "definition",
        "baseline",
        "target / guardrail",
        "measurement window",
        "source / method",
        "owner",
    ]:
        for row in metrics:
            if len(row) != 7:
                continue
            name, definition, baseline, target, window, _source, _owner = row
            details[name] = {
                "definition": definition,
                "baseline": baseline,
                "target": target,
                "window": window,
                "expected": "n/a — metric row",
            }
    else:
        findings.append("PRD: Metrics table is missing or has unexpected columns")
    test_header, tests = _table(prd_text, "## Test Obligations")
    expected_tests = [
        "test id",
        "obligation",
        "test type",
        "required",
        "upstream trace ids",
        "expected signal",
    ]
    if test_header[:6] != expected_tests:
        findings.append("PRD: Test Obligations table is missing or has unexpected columns")
    else:
        for row in tests:
            if len(row) < 6 or row[3].casefold() != "yes":
                continue
            test_id, obligation, test_type, _required, _trace, expected_signal = row[:6]
            details[test_id] = {
                "definition": obligation,
                "baseline": "none recorded",
                "target": "n/a — required test has no numeric target",
                "window": f"{test_type} test",
                "expected": expected_signal,
            }
    return details, findings


def _expected_availability(target: object) -> str:
    surface_class = str(getattr(target, "surface_class", "")).casefold()
    if surface_class in {"ios", "android", "browser_extension"}:
        return "installable"
    if surface_class in {"macos", "windows"}:
        return "downloadable"
    return "deployed"


def _artifact_allows_na(target: object | None) -> bool:
    return bool(target is not None and allows_no_independent_artifact(target))


def _validate_blockers(
    rows: list[list[str]], require_filled: bool
) -> tuple[dict[str, dict[str, object]], list[str]]:
    findings: list[str] = []
    blockers: dict[str, dict[str, object]] = {}
    for blocker_id, targets, kind, owner, next_step, status, notes in rows:
        if not BLOCKER_ID_RE.fullmatch(blocker_id):
            findings.append(f"Open Blockers: invalid blocker ID {blocker_id!r}")
            continue
        if blocker_id in blockers:
            findings.append(f"Open Blockers: duplicate blocker {blocker_id}")
            continue
        target_set = set(_parse_list(targets))
        if status not in BLOCKER_STATUSES:
            findings.append(f"Open Blockers: {blocker_id} has invalid status {status!r}")
        if owner.strip().casefold() not in ABSENT and not _placeholder(owner) and not _human(owner):
            findings.append(f"Open Blockers: {blocker_id} owner must name a human")
        if status == "open" and (
            not target_set
            or kind.lower() in ABSENT
            or not _human(owner)
            or next_step.lower() in ABSENT
        ):
            findings.append(
                f"Open Blockers: {blocker_id} needs targets, kind, owner, and next step"
            )
        if require_filled:
            findings.extend(
                _value_findings(
                    f"Open Blockers: {blocker_id}",
                    [targets, kind, owner, next_step, status, notes],
                    True,
                )
            )
        blockers[blocker_id] = {
            "targets": target_set,
            "kind": kind,
            "owner": owner,
            "status": status,
        }
    return blockers, findings


def check_activation_text(
    text: str,
    *,
    prd_text: str | None = None,
    architecture_text: str | None = None,
    deployment_text: str | None = None,
    require_filled: bool = False,
    require_verified_sources: bool = False,
    require_ready: tuple[str, ...] = (),
) -> list[str]:
    require_filled = require_filled or require_verified_sources
    findings: list[str] = []
    if require_verified_sources and prd_text is None:
        findings.append("PRD: verified-source handoff requires the current PRD")
    if require_verified_sources and architecture_text is None:
        findings.append("architecture: verified-source handoff requires architecture.md")
    if require_verified_sources and deployment_text is None:
        findings.append("deployment: verified-source handoff requires DEPLOYMENT.md")
    architecture_targets = {}
    deployment_targets: dict[str, dict[str, str]] = {}
    if architecture_text is not None:
        contract, architecture_findings = parse_release_targets(architecture_text)
        findings.extend(architecture_findings)
        architecture_targets = contract.by_id()
    if deployment_text is not None:
        deployment_targets = parse_release_target_status(deployment_text)
        for target_id in sorted(release_target_status_duplicates(deployment_text)):
            findings.append(
                f"deployment: duplicate Release Target Status row {target_id}"
            )
        if architecture_text is not None and not deployment_targets:
            findings.append(
                "deployment: Release Target Status table is missing or has unexpected columns"
            )
    for heading in REQUIRED_SECTIONS:
        if _section(text, heading) is None:
            findings.append(f"missing required section {heading}")
    findings.extend(_duplicate_sections(text, REQUIRED_SECTIONS))
    if active_text(text).count("# Product Activation") != 1:
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
        for name in ("Updated", "Measurement window starts"):
            value = record.get(name, "")
            parsed_timestamp = _timestamp(value)
            if value.lower() not in ABSENT and not _placeholder(value) and parsed_timestamp is None:
                findings.append(f"Record: {name} must be an RFC3339 timestamp")
            elif parsed_timestamp is not None and not _not_future(parsed_timestamp):
                findings.append(f"Record: {name} cannot be in the future")
        if require_filled:
            for name in (
                "Product",
                "Activation owner",
                "Release reference",
                "Updated",
                "Measurement window starts",
            ):
                if record.get(name, "").lower() in ABSENT:
                    findings.append(f"Record: filled record needs {name}")
            if not _human(record.get("Activation owner", "")):
                findings.append("Record: Activation owner must name a human")

    tables, table_findings = _validate_tables(text, require_filled)
    findings.extend(table_findings)
    findings.extend(
        _validate_profiles(
            tables.get("## Applied Profiles", []), architecture_targets, require_filled
        )
    )
    capabilities, capability_findings = _validate_capabilities(
        tables.get("## Capability Observations", [])
    )
    findings.extend(capability_findings)
    evidence, evidence_findings = _validate_evidence(tables.get("## Verification Evidence", []))
    findings.extend(evidence_findings)
    sources, source_findings = _validate_sources(
        tables.get("## Measurement Sources", []), capabilities, evidence, require_filled
    )
    findings.extend(source_findings)
    for source_id, source in sources.items():
        for target, binding in source["bindings"].items():
            architecture_target = architecture_targets.get(target)
            if binding["artifact"].casefold() == "n/a" and not _artifact_allows_na(
                architecture_target
            ):
                findings.append(
                    f"Measurement Sources: {source_id} artifact n/a is allowed only for an architecture target with Artifact kind no independent artifact"
                )
            if binding["artifact"].casefold() != "n/a" and _artifact_allows_na(
                architecture_target
            ):
                findings.append(
                    f"Measurement Sources: {source_id} architecture target {target} requires artifact n/a"
                )
    blockers, blocker_findings = _validate_blockers(
        tables.get("## Open Blockers", []), require_filled
    )
    findings.extend(blocker_findings)

    manual: dict[str, str] = {}
    for item_id, owner, step, expected, status in tables.get("## Manual Handoff", []):
        if status not in HANDOFF_STATUSES and not _placeholder(status):
            findings.append(f"Manual Handoff: {item_id} has invalid status {status!r}")
        if owner.strip().casefold() not in ABSENT and not _placeholder(owner) and not _human(owner):
            findings.append(f"Manual Handoff: {item_id} owner must name a human")
        if item_id in manual:
            findings.append(f"Manual Handoff: duplicate item {item_id}")
        manual[item_id] = status
        if require_filled and (
            any(_placeholder(value) for value in (owner, step, expected))
            or (status == "completed" and not _human(owner))
        ):
            findings.append(f"Manual Handoff: {item_id} has unresolved fields")

    tasks, titles, task_parse_findings = _tasks(text)
    findings.extend(task_parse_findings)
    task_bindings: dict[str, dict[str, dict[str, str]]] = {}
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
        for target, binding in bindings.items():
            architecture_target = architecture_targets.get(target)
            if binding["artifact"].casefold() == "n/a" and not _artifact_allows_na(
                architecture_target
            ):
                findings.append(
                    f"{task_id}: artifact n/a is allowed only for an architecture target with Artifact kind no independent artifact"
                )
            if binding["artifact"].casefold() != "n/a" and _artifact_allows_na(
                architecture_target
            ):
                findings.append(
                    f"{task_id}: architecture target {target} requires artifact n/a"
                )
    findings.extend(_cycle_findings(tasks))

    for evidence_id, item in evidence.items():
        if (
            item["item_id"] not in tasks
            and item["item_id"] not in sources
            and item["item_id"] not in capabilities
        ):
            findings.append(f"Verification Evidence: {evidence_id} references unknown item {item['item_id']}")
        elif item["item_id"] in tasks and evidence_id not in _parse_list(
            tasks[item["item_id"]].get("Evidence IDs", "none")
        ):
            findings.append(
                f"Verification Evidence: {evidence_id} is not listed by task {item['item_id']}"
            )
        elif item["item_id"] in sources and evidence_id not in sources[item["item_id"]][
            "evidence_ids"
        ]:
            findings.append(
                f"Verification Evidence: {evidence_id} is not listed by source {item['item_id']}"
            )

    coverage_rows = tables.get("## Outcome Coverage", [])
    coverage: dict[str, dict[str, object]] = {}
    for (
        signal,
        definition,
        baseline,
        target_guardrail,
        measurement_window,
        expected_signal,
        targets,
        source_id,
        status,
    ) in coverage_rows:
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
        if require_filled and status != "n/a":
            for name, value in (
                ("Definition / obligation", definition),
                ("Baseline", baseline),
                ("Target / guardrail", target_guardrail),
                ("Measurement window", measurement_window),
                ("Expected signal", expected_signal),
                ("Release targets", targets),
                ("Source ID", source_id),
            ):
                if value.lower() in ABSENT:
                    findings.append(f"Outcome Coverage: {signal} needs {name}")
        if source_id in sources and not set(_parse_list(targets)).issubset(sources[source_id]["targets"]):
            findings.append(f"Outcome Coverage: source {source_id} does not cover every target for {signal}")
        coverage[signal] = {
            "definition": definition,
            "baseline": baseline,
            "target": target_guardrail,
            "window": measurement_window,
            "expected": expected_signal,
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
        details, detail_findings = _prd_signal_details(prd_text)
        findings.extend(detail_findings)
        for signal, item in coverage.items():
            expected_detail = details.get(signal)
            if expected_detail is None:
                continue
            for field, label in (
                ("definition", "definition / obligation"),
                ("baseline", "baseline"),
                ("target", "target / guardrail"),
                ("window", "measurement window"),
                ("expected", "expected signal"),
            ):
                if item[field] != expected_detail[field]:
                    findings.append(
                        f"Outcome Coverage: {signal} {label} must exactly match PRD"
                    )

    active_targets: set[str] = set()
    for bindings in task_bindings.values():
        active_targets.update(
            target for target in bindings if target.lower() not in ABSENT and not _placeholder(target)
        )
    for source in sources.values():
        active_targets.update(
            target
            for target in source["targets"]
            if target.lower() not in ABSENT and not _placeholder(target)
        )
    for item in coverage.values():
        active_targets.update(
            target
            for target in item["targets"]
            if target.lower() not in ABSENT and not _placeholder(target)
        )
    readiness_rows = tables.get("## Target Readiness", [])
    if architecture_targets:
        for target in sorted(active_targets - set(architecture_targets)):
            findings.append(
                f"Activation target {target} is not defined by architecture.md"
            )
        readiness_target_ids = {
            row[0]
            for row in readiness_rows
            if len(row) == len(TABLE_HEADERS["## Target Readiness"])
            and row[0].lower() not in ABSENT
            and not _placeholder(row[0])
        }
        for target in sorted(set(architecture_targets) - readiness_target_ids):
            findings.append(
                f"Target Readiness: architecture target {target} needs a readiness or concrete n/a row"
            )
        if require_verified_sources:
            target_rows = {
                row[0]: row
                for row in readiness_rows
                if len(row) == len(TABLE_HEADERS["## Target Readiness"])
            }
            for target in sorted(set(architecture_targets) & set(target_rows)):
                if target_rows[target][6] not in {"ready", "n/a"}:
                    findings.append(
                        f"Target Readiness: verified handoff target {target} must be ready or n/a"
                    )

    open_blockers = {
        blocker_id: item for blocker_id, item in blockers.items() if item["status"] == "open"
    }
    for blocker_id, item in open_blockers.items():
        named_targets = item["targets"] - {"all"}
        for target in sorted(named_targets - active_targets):
            findings.append(
                f"Open Blockers: {blocker_id} names unknown active target {target}"
            )

    readiness: dict[str, dict[str, object]] = {}
    active_targets.update(
        row[0]
        for row in readiness_rows
        if len(row) == len(TABLE_HEADERS["## Target Readiness"])
        and row[6].lower() != "n/a"
        and row[0].lower() not in ABSENT
        and not _placeholder(row[0])
    )
    for (
        target,
        stage,
        provider,
        source_sha,
        artifact,
        availability,
        status,
        checked,
        na_reason,
        blocker_refs,
    ) in readiness_rows:
        if _placeholder(target):
            continue
        if target in readiness:
            findings.append(f"Target Readiness: duplicate release target {target}")
        if status not in READINESS_STATUSES:
            findings.append(f"Target Readiness: {target} has invalid status {status!r}")
        architecture_target = architecture_targets.get(target)
        if architecture_text is not None and architecture_target is None:
            findings.append(
                f"Target Readiness: {target} is not an architecture release target"
            )
        if availability not in TARGET_AVAILABILITY_STATES:
            findings.append(
                f"Target Readiness: {target} has invalid availability state {availability!r}"
            )
        if status == "n/a" and not _n_a_with_reason(na_reason):
            findings.append(
                f"Target Readiness: n/a target {target} needs a concrete reason"
            )
        if status == "n/a" and architecture_target is not None and target in active_targets:
            findings.append(
                f"Target Readiness: active target {target} cannot be n/a"
            )
        if status != "n/a" and na_reason.lower() not in {"", "none", "n/a"}:
            findings.append(
                f"Target Readiness: active target {target} must not use an n/a reason"
            )
        if architecture_target is not None:
            if stage != architecture_target.stage:
                findings.append(
                    f"Target Readiness: {target} stage must be {architecture_target.stage!r}"
                )
            expected_provider_channel = (
                f"{architecture_target.provider};{architecture_target.channel}"
            )
            if provider.casefold() != expected_provider_channel.casefold():
                findings.append(
                    f"Target Readiness: {target} provider/channel must be "
                    f"{expected_provider_channel!r}"
                )
            expected_availability = _expected_availability(architecture_target)
            if status == "ready" and availability != expected_availability:
                findings.append(
                    f"Target Readiness: ready target {target} availability must be "
                    f"{expected_availability!r}"
                )
            if artifact.casefold() == "n/a" and not _artifact_allows_na(architecture_target):
                findings.append(
                    f"Target Readiness: {target} may use artifact n/a only when architecture Artifact kind is no independent artifact"
                )
            if (
                artifact.casefold() not in {"", "pending", "n/a"}
                and _artifact_allows_na(architecture_target)
            ):
                findings.append(
                    f"Target Readiness: {target} must use artifact n/a because architecture Artifact kind is no independent artifact"
                )
        deployment = deployment_targets.get(target)
        if deployment_text is not None and deployment is None:
            findings.append(
                f"Target Readiness: deployment is missing release target {target}"
            )
        elif deployment is not None:
            if architecture_target is not None:
                if deployment["stage"] != architecture_target.stage:
                    findings.append(
                        f"Target Readiness: {target} deployment stage differs from architecture"
                    )
                expected_provider_channel = (
                    f"{architecture_target.provider};{architecture_target.channel}"
                )
                if deployment["provider / channel"].casefold() != expected_provider_channel.casefold():
                    findings.append(
                        f"Target Readiness: {target} deployment provider/channel differs from architecture"
                    )
            if source_sha not in {"pending"} and (
                source_sha != deployment["expected sha"]
                or source_sha != deployment["deployed sha"]
            ):
                findings.append(
                    f"Target Readiness: {target} source SHA differs from the deployment row"
                )
            if artifact not in {"pending"} and artifact != deployment[
                "artifact / build identity"
            ]:
                findings.append(
                    f"Target Readiness: {target} artifact differs from the deployment row"
                )
            if status == "ready" and deployment["status"] != "PASS":
                findings.append(
                    f"Target Readiness: ready target {target} requires deployment PASS"
                )
        readiness[target] = {
            "source_sha": source_sha,
            "artifact": artifact,
            "binding": f"{target}@{source_sha}#{artifact}",
            "status": status,
            "checked": checked,
            "blockers": blocker_refs,
            "availability": availability,
        }
        if require_filled and status != "n/a" and (
            not SHA_RE.fullmatch(source_sha)
            or not ARTIFACT_ID_RE.fullmatch(artifact)
            or artifact == "pending"
        ):
            findings.append(
                f"Target Readiness: filled target {target} needs exact source and artifact identities"
            )
        listed_blockers = set(_parse_list(blocker_refs))
        checked_at = _timestamp(checked)
        if checked.lower() not in ABSENT and not _placeholder(checked) and checked_at is None:
            findings.append(
                f"Target Readiness: {target} Checked must be an RFC3339 timestamp"
            )
        elif checked_at is not None and not _not_future(checked_at):
            findings.append(
                f"Target Readiness: {target} Checked cannot be in the future"
            )
        for blocker_id in listed_blockers:
            if blocker_id not in blockers:
                findings.append(
                    f"Target Readiness: {target} references unknown blocker {blocker_id}"
                )
        applicable_open = {
            blocker_id
            for blocker_id, item in open_blockers.items()
            if "all" in item["targets"] or target in item["targets"]
        }
        if status == "ready":
            if not SHA_RE.fullmatch(source_sha):
                findings.append(f"Target Readiness: ready target {target} needs a full lowercase Git SHA")
            if not ARTIFACT_ID_RE.fullmatch(artifact) or artifact == "pending":
                findings.append(
                    f"Target Readiness: ready target {target} needs an exact artifact or build identity"
                )
            elif artifact.casefold() == "n/a" and not _artifact_allows_na(architecture_target):
                findings.append(
                    f"Target Readiness: ready target {target} may use n/a artifact only when architecture Artifact kind is no independent artifact"
                )
            elif artifact.casefold() != "n/a" and _artifact_allows_na(architecture_target):
                findings.append(
                    f"Target Readiness: {target} must use exact artifact n/a because architecture Artifact kind is no independent artifact"
                )
            if checked_at is None or listed_blockers:
                findings.append(f"Target Readiness: ready target {target} needs checked time and no blockers")
            if applicable_open:
                findings.append(
                    f"Target Readiness: ready target {target} has open blocker(s) {', '.join(sorted(applicable_open))}"
                )
            bound = [
                task_id
                for task_id, bindings in task_bindings.items()
                if target in bindings and tasks[task_id].get("Required", "").lower() == "yes"
            ]
            if not bound:
                findings.append(f"Target Readiness: ready target {target} has no required ACT tasks")
            for task_id in bound:
                binding = task_bindings[task_id][target]
                if binding["sha"] != source_sha or binding["artifact"] != artifact:
                    findings.append(f"Target Readiness: {target} identity differs from {task_id} release binding")
                if tasks[task_id].get("Status") != "verified":
                    findings.append(f"Target Readiness: {target} has unverified task {task_id}")
            for source_id, source in sources.items():
                if target not in source["bindings"] or source["status"] in {"n/a", "superseded"}:
                    continue
                binding = source["bindings"][target]
                if binding["sha"] != source_sha or binding["artifact"] != artifact:
                    findings.append(
                        f"Target Readiness: {target} identity differs from {source_id} release binding"
                    )
            for signal, item in coverage.items():
                if target in item["targets"] and item["status"] not in {"verified", "n/a"}:
                    findings.append(f"Target Readiness: {target} has unverified outcome signal {signal}")
            relevant_evidence_times = [
                item["checked_at"]
                for evidence_id, item in evidence.items()
                if isinstance(item["checked_at"], datetime)
                and item["release_binding"] == f"{target}@{source_sha}#{artifact}"
                and (
                    item["item_id"] in bound
                    or (
                        item["item_id"] in sources
                        and target in sources[item["item_id"]]["bindings"]
                    )
                )
            ]
            if checked_at is not None and relevant_evidence_times and checked_at < max(
                relevant_evidence_times
            ):
                findings.append(
                    f"Target Readiness: {target} readiness check predates its verification evidence"
                )

    for target in sorted(active_targets - set(readiness)):
        if require_filled or record.get("Status") == "handoff_ready":
            findings.append(f"Target Readiness: missing active target {target}")
    for target in sorted(set(readiness) - active_targets):
        if readiness[target]["status"] == "n/a":
            continue
        findings.append(f"Target Readiness: {target} is not in the active activation scope")

    if require_verified_sources:
        if record.get("Status") != "handoff_ready":
            findings.append("Record: verified-source handoff requires status handoff_ready")
        if not readiness:
            findings.append("Target Readiness: verified-source handoff needs at least one release target")
        if not active_targets:
            findings.append("Target Readiness: verified-source handoff needs an active release target")
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
        row["status"] not in {"ready", "n/a"} for row in readiness.values()
    ):
        findings.append("Record: handoff_ready requires every active target to be ready")
    if record.get("Status") == "handoff_ready" and not active_targets:
        findings.append("Record: handoff_ready requires at least one active release target")
    if record.get("Status") == "handoff_ready" and open_blockers:
        findings.append("Record: handoff_ready cannot have open blockers")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation", type=Path, default=Path("docs/ACTIVATION.md"))
    parser.add_argument("--prd", type=Path)
    parser.add_argument("--architecture", type=Path)
    parser.add_argument("--deployment", type=Path)
    parser.add_argument("--require-filled", action="store_true")
    parser.add_argument("--require-verified-sources", action="store_true")
    parser.add_argument("--require-ready", action="append", default=[])
    parser.add_argument("--show-action-digests", action="store_true")
    args = parser.parse_args(argv)
    if args.require_verified_sources and args.prd is None:
        print("--require-verified-sources requires --prd", file=sys.stderr)
        return 2
    if args.require_verified_sources and args.architecture is None:
        print("--require-verified-sources requires --architecture", file=sys.stderr)
        return 2
    if args.require_verified_sources and args.deployment is None:
        print("--require-verified-sources requires --deployment", file=sys.stderr)
        return 2
    if not args.activation.is_file():
        print(f"activation record not found: {args.activation}", file=sys.stderr)
        return 2
    if args.prd is not None and not args.prd.is_file():
        print(f"PRD not found: {args.prd}", file=sys.stderr)
        return 2
    if args.architecture is not None and not args.architecture.is_file():
        print(f"architecture record not found: {args.architecture}", file=sys.stderr)
        return 2
    if args.deployment is not None and not args.deployment.is_file():
        print(f"deployment record not found: {args.deployment}", file=sys.stderr)
        return 2
    text = args.activation.read_text(encoding="utf-8")
    prd_text = args.prd.read_text(encoding="utf-8") if args.prd is not None else None
    architecture_text = (
        args.architecture.read_text(encoding="utf-8")
        if args.architecture is not None
        else None
    )
    deployment_text = (
        args.deployment.read_text(encoding="utf-8")
        if args.deployment is not None
        else None
    )
    tasks, _titles, parse_findings = _tasks(text)
    if args.show_action_digests:
        tables, _table_findings = _validate_tables(text, False)
        capabilities, _capability_findings = _validate_capabilities(
            tables.get("## Capability Observations", [])
        )
        capability_scopes = {
            capability_id: str(observation["target_scope"])
            for capability_id, observation in capabilities.items()
        }
        for task_id in sorted(tasks):
            if set(TASK_FIELDS) <= set(tasks[task_id]):
                print(
                    f"{task_id} {action_digest(task_id, tasks[task_id], capability_scopes)}"
                )
        if parse_findings:
            return 1
    findings = check_activation_text(
        text,
        prd_text=prd_text,
        architecture_text=architecture_text,
        deployment_text=deployment_text,
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
