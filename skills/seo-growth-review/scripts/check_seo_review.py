#!/usr/bin/env python3
"""Strict validation for a saved lifecycle public-release SEO review."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS_DIR = Path(__file__).resolve().parent
SIBLING_SCRIPTS_ROOT = SCRIPTS_DIR.parents[1]
PRODUCT_DEFINITION_SCRIPTS = (
    SIBLING_SCRIPTS_ROOT / "product-definition-builder" / "scripts"
)
ACTIVATION_SCRIPTS = SIBLING_SCRIPTS_ROOT / "product-activation" / "scripts"
DELIVERY_SCRIPTS = SIBLING_SCRIPTS_ROOT / "delivery-harness" / "scripts"
for sibling_scripts in (
    PRODUCT_DEFINITION_SCRIPTS,
    ACTIVATION_SCRIPTS,
    DELIVERY_SCRIPTS,
):
    if str(sibling_scripts) not in sys.path:
        sys.path.insert(0, str(sibling_scripts))

from check_activation import _table, check_activation_text  # noqa: E402
from check_deployment import parse_release_target_status  # noqa: E402
from markdown_contract import active_text, is_human_owner  # noqa: E402
from release_targets import (
    allows_no_independent_artifact,
    is_public_web_target,
    parse_release_targets,
)  # noqa: E402
from contract_utils import activation_product_identity, product_identity, safe_read_text  # noqa: E402


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LIFECYCLE_PATH_RE = re.compile(
    r"^docs/seo/reviews/(?P<date>\d{4}-\d{2}-\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$"
)
MS_ID_RE = re.compile(r"^MS-[0-9]{3}$")
MODES = {"baseline", "growth_review", "traffic_drop"}
SOURCE_ROLES = {
    "search_console",
    "ga4",
    "production_page",
    "google_trends",
    "keyword_planner",
    "public_serp",
    "first_party",
}
EVIDENCE_STRENGTHS = {"observed", "estimated", "hypothesis"}
PRIORITIES = {"blocker", "high", "medium", "low"}
OPPORTUNITY_TYPES = {
    "existing_page",
    "ctr",
    "content_gap",
    "decay",
    "intent_mismatch",
    "cannibalization",
    "internal_link",
    "trust_value",
}
ROUTES = {
    "product_activation",
    "product_definition",
    "delivery",
    "connector",
    "observe_later",
    "owner",
}
REQUIRED_SECTIONS = (
    "## Record",
    "## Verified Sources",
    "## Measurement Integrity",
    "## Technical Findings",
    "## Growth Opportunities",
    "## What To Do First",
    "## Limits And Next Window",
)
RECORD_FIELDS = (
    "Schema",
    "Mode",
    "Review type",
    "Review owner",
    "Production release target",
    "Release SHA",
    "Artifact / build identity",
    "Deployment identity",
    "Deployment checked",
    "Production domain",
    "Data cutoff",
    "Activation record",
    "Activation sha256",
    "Review date",
)
RECORD_FIELDS_V2 = RECORD_FIELDS + (
    "Product",
    "Target market",
    "Language",
    "Business outcome",
    "Timezone",
    "Comparison window",
    "Segmentation",
    "Global data coverage through",
)
SOURCE_HEADERS = (
    "ms id",
    "scope",
    "release binding",
    "source role",
    "data cutoff",
    "evidence",
)
SOURCE_HEADERS_V2 = (
    "ms id",
    "scope",
    "release binding",
    "source role",
    "verified at",
    "coverage through",
    "evidence",
)
INTEGRITY_HEADERS = ("check", "result", "evidence")
FINDING_HEADERS = ("priority", "finding", "scope", "evidence", "impact", "route")
OPPORTUNITY_HEADERS = (
    "priority",
    "query or topic",
    "intent / type",
    "evidence",
    "current page",
    "action / route",
    "follow-up metric",
)
ABSENT = {"", "none", "n/a", "pending"}


def _timestamp(value: str) -> datetime | None:
    if not RFC3339_RE.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _format_instant(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _hostname(value: str) -> str | None:
    candidate = value.strip().lower()
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.hostname or "").rstrip(".")
    return host if DOMAIN_RE.fullmatch(host) else None


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


def _rows(
    text: str, heading: str, expected: tuple[str, ...]
) -> tuple[list[list[str]], bool]:
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


def _human(owner: str) -> bool:
    return is_human_owner(owner)


def _valid_date(value: str) -> bool:
    if not DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _substantive(value: str, *, allow_none: bool = False) -> bool:
    normalized = value.strip().casefold()
    if not normalized or "<" in normalized or re.search(r"\b(?:tbd|todo|placeholder)\b", normalized):
        return False
    if normalized in ABSENT:
        return allow_none and normalized == "none"
    return True


def _matching_activation_sources(
    activation_text: str, target: str, sha: str, artifact: str
) -> dict[str, dict[str, object]]:
    header, rows = _table(activation_text, "## Measurement Sources")
    evidence_header, evidence_rows = _table(activation_text, "## Verification Evidence")
    if not rows or not evidence_rows:
        return {}
    evidence_by_id: dict[str, dict[str, object]] = {}
    for row in evidence_rows:
        if len(row) != 7:
            continue
        evidence_id, item_id, kind, route_binding, checked, result, _reference = row
        parts = [part.strip() for part in route_binding.split(";")]
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
    expected = f"{target}@{sha}#{artifact}"
    result: dict[str, dict[str, object]] = {}
    for row in rows:
        if len(row) != 10 or row[8] != "verified":
            continue
        source_id, source_target, _environment, _retrieval, source_role, _route, bindings, owner, _status, evidence_ids = row
        if expected not in {item.strip() for item in bindings.split(",")}:
            continue
        parsed_ids = [item.strip() for item in evidence_ids.split(",") if item.strip()]
        pass_items = [
            evidence_by_id[item_id]
            for item_id in parsed_ids
            if item_id in evidence_by_id
            and evidence_by_id[item_id]["item_id"] == source_id
            and evidence_by_id[item_id]["binding"] == expected
            and evidence_by_id[item_id]["result"] == "PASS"
            and evidence_by_id[item_id]["kind"] in {"readback", "behavior"}
        ]
        latest_pass = max(
            (item["checked_at"] for item in pass_items if isinstance(item["checked_at"], datetime)),
            default=None,
        )
        if latest_pass is None:
            continue
        role = source_role
        if role not in SOURCE_ROLES:
            continue
        result[source_id] = {
            "scope": source_target,
            "role": role,
            "owner": owner,
            "evidence_ids": tuple(parsed_ids),
            "latest_pass": latest_pass,
            "binding": expected,
        }
    return result


def check_seo_review_text(
    text: str,
    *,
    prd_text: str,
    architecture_text: str,
    deployment_text: str,
    activation_text: str,
    stack_text: str | None = None,
    repo_root: Path | None = None,
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
                repo_root=repo_root,
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
    if active.count("# SEO Growth Review") != 1:
        findings.append("expected one # SEO Growth Review title")

    record = _fields(_section(text, "## Record") or [])
    for field in _duplicate_fields(_section(text, "## Record") or []):
        findings.append(f"Record: duplicate field {field}")
    schema = record.get("Schema", "")
    record_fields = RECORD_FIELDS_V2 if schema == "seo-review/2" else RECORD_FIELDS
    for field in record_fields:
        if field not in record:
            findings.append(f"Record: missing field {field}")
    if schema not in {"seo-review/1", "seo-review/2"}:
        findings.append("Record: Schema must be seo-review/1 or seo-review/2")
    if record.get("Mode") not in MODES:
        findings.append("Record: Mode has an invalid value")
    if record.get("Review type") != "lifecycle_public_release":
        findings.append("Record: saved lifecycle reviews must use Review type lifecycle_public_release")
    if not _human(record.get("Review owner", "")):
        findings.append("Record: Review owner must name a human")
    sha = record.get("Release SHA", "")
    artifact = record.get("Artifact / build identity", "")
    if not SHA_RE.fullmatch(sha):
        findings.append("Record: Release SHA must be a full lowercase Git SHA")
    if not DOMAIN_RE.fullmatch(record.get("Production domain", "").lower().strip("/")):
        findings.append("Record: Production domain must be a lowercase registrable host without a path")
    data_cutoff = _timestamp(record.get("Data cutoff", ""))
    if data_cutoff is None:
        findings.append("Record: Data cutoff must be an RFC3339 timestamp")
    elif data_cutoff > datetime.now(timezone.utc):
        findings.append("Record: Data cutoff cannot be in the future")
    deployment_checked = _timestamp(record.get("Deployment checked", ""))
    if deployment_checked is None:
        findings.append("Record: Deployment checked must be an RFC3339 timestamp")
    elif deployment_checked > datetime.now(timezone.utc):
        findings.append("Record: Deployment checked cannot be in the future")
    if not _valid_date(record.get("Review date", "")):
        findings.append("Record: Review date must be a real calendar date")
    data_cutoff_date = record.get("Data cutoff", "")[:10]
    if _valid_date(record.get("Review date", "")) and _valid_date(data_cutoff_date):
        if record["Review date"] < data_cutoff_date:
            findings.append("Record: Review date cannot precede the data cutoff")
        if record["Review date"] > datetime.now(timezone.utc).date().isoformat():
            findings.append("Record: Review date cannot be in the future")
    if record.get("Activation record") != "docs/ACTIVATION.md":
        findings.append("Record: Activation record must be docs/ACTIVATION.md")
    activation_digest = hashlib.sha256(activation_text.encode("utf-8")).hexdigest()
    if record.get("Activation sha256") != activation_digest:
        findings.append("Record: Activation sha256 does not match the current document bytes")
    if schema == "seo-review/2":
        for field in RECORD_FIELDS_V2[len(RECORD_FIELDS):]:
            if not _substantive(record.get(field, "")):
                findings.append(f"Record: {field} must be substantive in seo-review/2")
        if record.get("Mode") == "traffic_drop" and " vs " not in record.get("Comparison window", ""):
            findings.append("Record: traffic_drop requires equal comparison windows using '<period> vs <period>'")
        if record.get("Mode") == "traffic_drop":
            segmentation = record.get("Segmentation", "").casefold()
            required_segments = ("query", "page", "country", "device")
            if any(segment not in segmentation for segment in required_segments):
                findings.append(
                    "Record: traffic_drop Segmentation must include query, page, country, and device"
                )
        if record.get("Mode") == "growth_review" and " vs " not in record.get("Comparison window", ""):
            findings.append("Record: growth_review requires a comparison window using '<period> vs <period>'")
        global_coverage = _timestamp(record.get("Global data coverage through", ""))
        if global_coverage is None:
            findings.append("Record: Global data coverage through must be RFC3339")
        elif global_coverage > datetime.now(timezone.utc):
            findings.append("Record: Global data coverage through cannot be in the future")
        elif data_cutoff is not None and global_coverage > data_cutoff:
            findings.append("Record: Global data coverage through cannot exceed Data cutoff")
    for field, value in record.items():
        if field == "Artifact / build identity":
            continue
        if not _substantive(value, allow_none=False):
            findings.append(f"Record: {field} must be substantive")

    contract, architecture_findings = parse_release_targets(architecture_text)
    findings.extend(architecture_findings)
    target_id = record.get("Production release target", "")
    target = contract.by_id().get(target_id)
    if target is None or target.stage != "production":
        findings.append("Record: SEO review target must be an architecture production target")
    elif not is_public_web_target(target):
        findings.append("Record: SEO lifecycle reviews are limited to public web production targets")
    if artifact.lower() in ABSENT and not (
        target is not None and allows_no_independent_artifact(target)
    ):
        findings.append("Record: Artifact / build identity is required")
    deployment = parse_release_target_status(deployment_text).get(target_id)
    if deployment is None:
        findings.append("Deployment: Release Target Status is missing the reviewed target")
    else:
        if deployment["expected sha"] != sha or deployment["deployed sha"] != sha:
            findings.append("Deployment: reviewed target Expected and Deployed SHAs must equal the release SHA")
        if deployment["artifact / build identity"] != artifact:
            findings.append("Deployment: reviewed target artifact differs from the SEO review")
        if deployment["status"] != "PASS":
            findings.append("Deployment: reviewed target is not a current PASS")
        if record.get("Deployment checked") != deployment["checked"]:
            findings.append("Deployment: reviewed target checked time differs from the SEO review")
        expected_identity = f"{target.release_name};{target.channel};{artifact}" if target else ""
        if record.get("Deployment identity") != expected_identity:
            findings.append(f"Record: Deployment identity must be {expected_identity!r}")
        endpoint_host = _hostname(deployment.get("endpoint / domain", ""))
        production_domain = record.get("Production domain", "").lower().strip("/")
        if endpoint_host is None:
            findings.append("Deployment: reviewed web target needs a valid endpoint/domain hostname")
        elif endpoint_host != production_domain:
            findings.append(
                "Deployment: reviewed endpoint/domain hostname must equal the SEO Production domain"
            )

    activation_findings = check_activation_text(
        activation_text,
        prd_text=prd_text,
        architecture_text=architecture_text,
        deployment_text=deployment_text,
        stack_text=stack_text,
        repo_root=repo_root,
        require_verified_sources=True,
        require_ready=(target_id,),
    )
    findings.extend(f"Activation: {item}" for item in activation_findings)
    matching_sources = _matching_activation_sources(
        activation_text, target_id, sha, artifact
    )
    if not matching_sources:
        findings.append("Activation Sources: lifecycle review requires at least one matching verified source")
    prd_identity = product_identity(prd_text, kind="prd")
    activation_identity = activation_product_identity(activation_text)
    if prd_identity and activation_identity and prd_identity != activation_identity:
        findings.append("Package: Activation Product identity does not match the approved PRD")
    record_identity = record.get("Product", "")
    if prd_identity and record_identity and record_identity.casefold().strip() != prd_identity:
        findings.append("Record: Product identity must exactly match the approved PRD")

    source_expected_headers = SOURCE_HEADERS_V2 if schema == "seo-review/2" else SOURCE_HEADERS
    source_rows, source_header_ok = _rows(text, "## Verified Sources", source_expected_headers)
    if not source_header_ok:
        findings.append("Verified Sources: expected columns " + " | ".join(source_expected_headers))
    listed: set[str] = set()
    for source_row in source_rows:
        if len(source_row) != len(source_expected_headers):
            findings.append("Verified Sources: each row must have the exact column count")
            continue
        if schema == "seo-review/2":
            source_id, scope, binding, role, verified_at, coverage_through, evidence = source_row
            cutoff = coverage_through
        else:
            source_id, scope, binding, role, cutoff, evidence = source_row
            verified_at = cutoff
        if not MS_ID_RE.fullmatch(source_id):
            findings.append(f"Verified Sources: invalid source ID {source_id!r}")
            continue
        if source_id in listed:
            findings.append(f"Verified Sources: duplicate source {source_id}")
        listed.add(source_id)
        if source_id not in matching_sources:
            findings.append(f"Verified Sources: {source_id} does not match the verified Activation release")
        activation_source = matching_sources.get(source_id)
        if scope.lower() in ABSENT:
            findings.append(f"Verified Sources: {source_id} needs an exact non-secret scope")
        elif activation_source is not None and scope != activation_source["scope"]:
            findings.append(f"Verified Sources: {source_id} scope differs from Activation")
        if binding != f"{target_id}@{sha}#{artifact}":
            findings.append(f"Verified Sources: {source_id} has a mismatched release binding")
        if source_id not in matching_sources and binding != f"{target_id}@{sha}#{artifact}":
            findings.append(f"Verified Sources: {source_id} mismatched release binding cannot support this review")
        if role not in SOURCE_ROLES:
            findings.append(f"Verified Sources: {source_id} has invalid source role {role!r}")
        elif activation_source is not None and role != activation_source["role"]:
            findings.append(f"Verified Sources: {source_id} source role differs from Activation retrieval")
        cutoff_instant = _timestamp(cutoff)
        if cutoff_instant is None:
            findings.append(f"Verified Sources: {source_id} cutoff must be RFC3339")
        elif schema == "seo-review/1" and cutoff != record.get("Data cutoff"):
            findings.append(f"Verified Sources: {source_id} cutoff differs from the Record cutoff")
        if schema == "seo-review/2":
            verified_instant = _timestamp(verified_at)
            if verified_instant is None:
                findings.append(f"Verified Sources: {source_id} verified at must be RFC3339")
            elif activation_source is not None and verified_instant != activation_source["latest_pass"]:
                findings.append(f"Verified Sources: {source_id} verified at must equal the latest PASS Activation evidence timestamp")
            if cutoff_instant is not None and cutoff_instant > data_cutoff:
                findings.append(f"Verified Sources: {source_id} coverage through cannot exceed the global data cutoff")
        elif activation_source is not None and cutoff_instant != activation_source["latest_pass"]:
            findings.append(f"Verified Sources: {source_id} cutoff must equal the latest PASS Activation evidence timestamp")
        if evidence.lower() in ABSENT:
            findings.append(f"Verified Sources: {source_id} needs evidence")
        elif activation_source is not None:
            missing_ids = [item for item in activation_source["evidence_ids"] if item not in evidence]
            if missing_ids:
                findings.append(f"Verified Sources: {source_id} evidence must name " + ", ".join(missing_ids))
        if not all(_substantive(cell) for cell in source_row):
            findings.append(f"Verified Sources: {source_id} has an empty or placeholder cell")
    if listed != set(matching_sources):
        findings.append("Verified Sources: every matching verified MS source must be listed exactly once")

    integrity_rows, integrity_ok = _rows(text, "## Measurement Integrity", INTEGRITY_HEADERS)
    if not integrity_ok:
        findings.append("Measurement Integrity: expected columns " + " | ".join(INTEGRITY_HEADERS))
    integrity_checks = [row[0].casefold() for row in integrity_rows if row]
    duplicate_integrity = sorted(
        check for check, count in Counter(integrity_checks).items() if count > 1
    )
    for check in duplicate_integrity:
        findings.append(f"Measurement Integrity: duplicate check {check}")
    for required_check in ("production scope", "release identity", "date coverage"):
        if required_check not in integrity_checks:
            findings.append(f"Measurement Integrity: missing {required_check} check")
    for integrity_row in integrity_rows:
        if len(integrity_row) != len(INTEGRITY_HEADERS):
            findings.append("Measurement Integrity: each row must have the exact column count")
            continue
        check, result, evidence = integrity_row
        if result not in {"PASS", "FAIL", "BLOCKED"}:
            findings.append(f"Measurement Integrity: {check} has invalid result {result!r}")
        elif check.casefold() in {"production scope", "release identity", "date coverage"} and result != "PASS":
            findings.append(f"Measurement Integrity: required check {check} must be PASS")
        if evidence.lower() in ABSENT:
            findings.append(f"Measurement Integrity: {check} needs evidence")
        if not all(_substantive(cell) for cell in integrity_row):
            findings.append(f"Measurement Integrity: {check} has an empty or placeholder cell")

    finding_rows, finding_ok = _rows(text, "## Technical Findings", FINDING_HEADERS)
    if not finding_ok:
        findings.append("Technical Findings: expected columns " + " | ".join(FINDING_HEADERS))
    elif not finding_rows:
        findings.append("Technical Findings: at least one substantive finding is required")
    finding_ids = [row[1] for row in finding_rows if len(row) == len(FINDING_HEADERS)]
    for finding_row in finding_rows:
        if len(finding_row) != len(FINDING_HEADERS):
            findings.append("Technical Findings: each row must have the exact column count")
            continue
        row = finding_row
        priority, _finding, _scope, evidence, _impact, route = row
        if priority not in PRIORITIES:
            findings.append(f"Technical Findings: invalid priority {priority!r}")
        if evidence not in EVIDENCE_STRENGTHS:
            findings.append(f"Technical Findings: invalid evidence strength {evidence!r}")
        if route not in ROUTES:
            findings.append(f"Technical Findings: invalid route {route!r}")
        if not all(_substantive(cell) for cell in finding_row):
            findings.append("Technical Findings: every row cell must be substantive")
    duplicates = sorted(item for item, count in Counter(finding_ids).items() if count > 1)
    if duplicates:
        findings.append("Technical Findings: duplicate finding(s) " + ", ".join(duplicates))

    opportunity_rows, opportunity_ok = _rows(
        text, "## Growth Opportunities", OPPORTUNITY_HEADERS
    )
    if not opportunity_ok:
        findings.append("Growth Opportunities: expected columns " + " | ".join(OPPORTUNITY_HEADERS))
    elif not opportunity_rows:
        findings.append("Growth Opportunities: at least one substantive opportunity is required")
    for opportunity_row in opportunity_rows:
        if len(opportunity_row) != len(OPPORTUNITY_HEADERS):
            findings.append("Growth Opportunities: each row must have the exact column count")
            continue
        row = opportunity_row
        priority, _topic, opportunity_type, evidence, _page, action, metric = row
        if priority not in {"high", "medium", "low"}:
            findings.append(f"Growth Opportunities: invalid priority {priority!r}")
        if opportunity_type not in OPPORTUNITY_TYPES:
            findings.append(f"Growth Opportunities: invalid type {opportunity_type!r}")
        if evidence not in EVIDENCE_STRENGTHS:
            findings.append(f"Growth Opportunities: invalid evidence strength {evidence!r}")
        route = action.rsplit("/", 1)[-1].strip()
        if route not in ROUTES:
            findings.append(f"Growth Opportunities: invalid route in {action!r}")
        if metric.lower() in ABSENT:
            findings.append("Growth Opportunities: follow-up metric is required")
        if not all(_substantive(cell) for cell in opportunity_row):
            findings.append("Growth Opportunities: every row cell must be substantive")
    for heading in ("## What To Do First", "## Limits And Next Window"):
        section_lines = _section(text, heading) or []
        if not any(_substantive(line) for line in section_lines):
            findings.append(f"{heading.removeprefix('## ')}: substantive narrative is required")
    return findings


def _is_dated_immutable(path: Path, repo_root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return False
    return LIFECYCLE_PATH_RE.fullmatch(relative) is not None


def _lifecycle_path_date(path: Path, repo_root: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None
    match = LIFECYCLE_PATH_RE.fullmatch(relative)
    return match.group("date") if match else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--prd", type=Path, required=True)
    parser.add_argument("--architecture", type=Path, required=True)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--activation", type=Path, required=True)
    parser.add_argument("--stack-decisions", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--require-lifecycle", action="store_true")
    args = parser.parse_args(argv)
    findings: list[str] = []
    if args.require_lifecycle and not _is_dated_immutable(args.review, args.repo_root):
        findings.append(
            "path: lifecycle public-release reviews must use docs/seo/reviews/YYYY-MM-DD-<slug>.md"
        )
    paths = (args.review, args.prd, args.architecture, args.deployment, args.activation)
    if args.stack_decisions is not None:
        paths += (args.stack_decisions,)
    if any(not path.is_file() for path in paths):
        print("one or more input files do not exist", file=sys.stderr)
        return 2
    loaded: dict[str, str] = {}
    for name, path in {
        "review": args.review,
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
    review_record = _fields(_section(loaded["review"], "## Record") or [])
    if args.require_lifecycle and review_record.get("Schema") != "seo-review/2":
        print("--require-lifecycle requires Schema: seo-review/2", file=sys.stderr)
        return 1
    if args.require_lifecycle and args.stack_decisions is None:
        print("--require-lifecycle requires --stack-decisions", file=sys.stderr)
        return 2
    if review_record.get("Schema") == "seo-review/2" and args.stack_decisions is None:
        print("seo-review/2 requires --stack-decisions", file=sys.stderr)
        return 2
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
        from check_deployment import check_deployment_text
        deployment_findings = check_deployment_text(
            loaded["deployment"], architecture_text=loaded["architecture"]
        )
        if deployment_findings:
            for item in deployment_findings:
                print(f"Deployment: {item}", file=sys.stderr)
            return 1
    findings.extend(
        check_seo_review_text(
            loaded["review"],
            prd_text=loaded["prd"],
            architecture_text=loaded["architecture"],
            deployment_text=loaded["deployment"],
            activation_text=loaded["activation"],
            stack_text=loaded.get("stack"),
            repo_root=args.repo_root,
        )
    )
    if args.require_lifecycle:
        path_date = _lifecycle_path_date(args.review, args.repo_root)
        review_fields = review_record
        if path_date is not None and review_fields.get("Review date") != path_date:
            findings.append(
                "path: lifecycle filename date must equal Record Review date"
            )
    for finding in findings:
        print(f"{args.review}: {finding}")
    if findings:
        return 1
    print(f"{args.review} is bound to the exact verified public production release")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
