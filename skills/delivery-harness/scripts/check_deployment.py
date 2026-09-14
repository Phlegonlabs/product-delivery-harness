#!/usr/bin/env python3
"""Read-only structural check of a project's DEPLOYMENT.md record.

Validates that the deployment record is resolved (no template placeholders),
that its name-only human configuration handoff is structurally complete, and
that its Environment Status table is coherent: both development and production
rows exist with a URL, duplicate section/row identities are rejected, and any
verified row carries full lowercase SHAs and a status. Also validates the
Release Unit Names table: production uses the canonical surface name and
development uses that exact name plus ``-dev``. Also validates the Resource
Isolation table: no binding class may list the same resource ID in both the
production and development columns. When architecture.md is supplied, validates
an exact architecture-backed Release Target Status table through the shared
release-target parser while retaining the legacy environment inspection.
Executing the platform's deployed-commit check command stays with the parent
or operator — this tool never runs recorded commands, reads secret values, or
touches the platform.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from collections import Counter

PRODUCT_DEFINITION_SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "product-definition-builder"
    / "scripts"
)
if str(PRODUCT_DEFINITION_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PRODUCT_DEFINITION_SCRIPTS))

from markdown_contract import (  # noqa: E402
    active_text,
    is_human_owner,
    is_substantive_identity,
)
from release_targets import (  # noqa: E402
    allows_no_independent_artifact,
    parse_release_targets,
)

PLACEHOLDER_MARKERS = (
    "<fill>",
    "<cloudflare |",
    "<pattern>",
    "<url>",
    "<databases",
    "<platform",
    "<secret or variable name>",
    "<service>",
    "<setting or account task>",
    "<stable surface id>",
    "<surface suffix>",
    "<production release name>",
    "<development release name>",
    "<stage-specific provider or channel>",
)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
BUILD_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+/-]*$")
HOST_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
LOWER_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENVIRONMENT_ROWS = ("development", "production")
BINDING_CLASSES = ("d1 database", "kv namespace", "r2 bucket", "durable objects")
ABSENT_VALUES = {"", "-", "n/a"}
IDENTITY_ABSENT_VALUES = {"", "-"}
HANDOFF_STATUSES = {"pending", "configured", "verified", "n/a"}
ENVIRONMENT_STATUSES = {"PASS", "FAIL", "BLOCKED", "UNVALIDATED"}
SECRET_HEADERS = (
    "name",
    "kind",
    "consumer",
    "preview placement",
    "production placement",
    "source / owner",
    "status",
)
EXTERNAL_SETUP_HEADERS = (
    "service",
    "setting",
    "preview / non-production",
    "production",
    "owner",
    "status",
)
RELEASE_UNIT_HEADERS = (
    "surface",
    "surface suffix",
    "production release name",
    "development release name",
    "production provider / channel",
    "development provider / channel",
)
RELEASE_TARGET_STATUS_HEADERS = (
    "release target",
    "surface",
    "stage",
    "provider / channel",
    "endpoint / domain",
    "expected sha",
    "deployed sha",
    "artifact / build identity",
    "availability evidence",
    "checked",
    "status",
)
KNOWN_LEVEL_TWO_SECTIONS = (
    "## Record",
    "## Release Unit Names",
    "## Resource Isolation",
    "## Required Secrets and Variables",
    "## External Console Setup",
    "## Release Target Status",
    "## Environment Status",
)
NATIVE_RELEASE_RE = re.compile(
    r"\b(?:ios|android|macos|windows|ipa|aab|dmg|pkg|msix|signed installer)\b",
    re.IGNORECASE,
)
NO_INDEPENDENT_ARTIFACT_VALUES = {
    "no independent artifact",
    "no-independent-artifact",
}
ATX_LEVEL_TWO_RE = re.compile(r"^ {0,3}##[ \t]+(?P<title>.*?)\s*$")
FENCE_RE = re.compile(r"^ {0,3}(?P<marker>`{3,}|~{3,})")


def _without_html_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    """Remove HTML comments while retaining text outside comment spans."""

    pieces: list[str] = []
    cursor = 0
    while cursor < len(line):
        if in_comment:
            end = line.find("-->", cursor)
            if end < 0:
                return "".join(pieces), True
            cursor = end + 3
            in_comment = False
            continue
        start = line.find("<!--", cursor)
        if start < 0:
            pieces.append(line[cursor:])
            break
        pieces.append(line[cursor:start])
        cursor = start + 4
        in_comment = True
    return "".join(pieces), in_comment


def _canonical_level_two_heading(line: str) -> str | None:
    match = ATX_LEVEL_TWO_RE.match(line)
    if match is None:
        return None
    title = match.group("title").strip()
    # CommonMark permits an optional closing run of hashes, so these render as
    # the same heading: `## Environment Status` and `## Environment Status ##`.
    title = re.sub(r"[ \t]+#+[ \t]*$", "", title).strip()
    if not title:
        return None
    return f"## {title}"


def _section_blocks(text: str) -> dict[str, list[list[str]]]:
    """Return the bodies of level-two sections keyed by their exact heading.

    A deployment record is Markdown, so tables with the same-looking cells in
    another section must not satisfy a required handoff or status section.  A
    level-three heading belongs to its surrounding level-two section.
    """

    sections: dict[str, list[list[str]]] = {}
    current_heading: str | None = None
    current_lines: list[str] = []
    fence_char: str | None = None
    fence_length = 0
    in_html_comment = False
    for line in text.splitlines():
        clean_line, in_html_comment = _without_html_comments(line, in_html_comment)
        if in_html_comment and not clean_line.strip():
            continue
        # Fenced and indented code is neither a section boundary nor live table
        # content. Excluding it here prevents example tables from satisfying or
        # duplicating the record's real tables.
        if fence_char is not None:
            if re.match(
                rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*$",
                clean_line,
            ):
                fence_char = None
                fence_length = 0
            continue
        # Four-space (or tab) indentation is an indented code block in
        # Markdown, so a heading-looking line there must not split a section.
        if line.startswith("\t") or len(line) - len(line.lstrip(" ")) >= 4:
            continue
        fence_match = FENCE_RE.match(clean_line)
        if fence_match:
            marker = fence_match.group("marker")
            fence_char = marker[0]
            fence_length = len(marker)
            continue
        heading = _canonical_level_two_heading(clean_line)
        if heading is not None:
            if current_heading is not None:
                sections.setdefault(current_heading, []).append(current_lines)
            current_heading = heading
            current_lines = []
        elif current_heading is not None:
            current_lines.append(clean_line)
    if current_heading is not None:
        sections.setdefault(current_heading, []).append(current_lines)
    return sections


def _table_rows(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    table_rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in lines
        if line.strip().startswith("|")
    ]
    if not table_rows:
        return [], []
    header = [cell.lower() for cell in table_rows[0]]
    data_rows = [
        row
        for row in table_rows[1:]
        if not all(set(cell) <= {"-", ":", " "} for cell in row)
    ]
    return header, data_rows


def _timestamp(value: str) -> datetime | None:
    if not RFC3339_RE.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _human(value: str) -> bool:
    return is_human_owner(value)


def _endpoint_findings(
    surface_class: str,
    stage: str,
    public_discoverability: str,
    endpoint: str,
    status: str,
    artifact: str,
    provider_channel: str,
) -> list[str]:
    """Validate endpoint/domain identity using the typed architecture class."""

    if status == "pending" and endpoint.strip().casefold() in {"", "pending"}:
        return []
    value = endpoint.strip()
    lowered = value.casefold()
    if not value or lowered in {"pending", "n/a"}:
        return ["endpoint/domain is missing"]
    if re.search(r"https?://[^\s/:]+:[^\s/@]+@", value, re.I):
        return ["endpoint/domain must not contain credentials"]
    native_classes = {"ios", "android", "macos", "windows", "browser_extension"}
    if surface_class in native_classes:
        if lowered.startswith("https://"):
            parsed = urlparse(value)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or not parsed.path
                or parsed.path == "/"
                or not HOST_RE.fullmatch(parsed.hostname.rstrip(".").casefold())
            ):
                return ["native/store endpoint must be a credential-free canonical https listing/download URL"]
            return []
        if artifact.casefold() == "n/a":
            expected = f"n/a — channel-only:{provider_channel}; no network endpoint"
            if value != expected:
                return ["native/store channel-only disposition must exactly match Provider;channel and artifact n/a"]
            return []
        expected = f"n/a — artifact-only:{artifact}; no network endpoint"
        if value != expected:
            return ["native/store artifact-only disposition must exactly match the artifact/build identity"]
        return []
    if surface_class in {"hosted_web", "hosted_api"}:
        candidate = value if "://" in value else f"https://{value}"
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return ["hosted endpoint must be an http(s) URL or hostname"]
        hostname = parsed.hostname.casefold()
        try:
            loopback = ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            loopback = hostname == "localhost"
        if parsed.scheme == "http":
            if not (
                stage == "development"
                and public_discoverability == "no"
                and loopback
            ):
                return [
                    "hosted endpoint must use HTTPS; HTTP is allowed only for "
                    "non-public localhost/loopback development"
                ]
        if parsed.username or parsed.password:
            return ["hosted endpoint must not contain userinfo"]
        if parsed.query or parsed.fragment:
            return ["hosted endpoint must not contain a query or fragment"]
        if not loopback and not HOST_RE.fullmatch(parsed.hostname.rstrip(".").casefold()):
            return ["hosted endpoint hostname is invalid"]
        return []
    if surface_class in {"worker", "job", "webhook", "realtime", "cli", "agent"}:
        if not is_substantive_identity(value):
            return ["typed endpoint/resource identity is not substantive"]
        return []
    if not is_substantive_identity(value):
        return ["endpoint/resource identity is not substantive"]
    return []


def parse_status_table(text: str) -> dict[str, dict[str, str]]:
    """Return {environment: {url, expected, deployed, checked, status}} rows."""

    rows: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0].lower() in {"environment", "---"}:
            continue
        if set(cells[0]) <= {"-", " "}:
            continue
        rows[cells[0].lower()] = {
            "url": cells[1],
            "expected": cells[2],
            "deployed": cells[3],
            "checked": cells[4],
            "status": cells[5],
        }
    return rows


def parse_section_table(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    """Return one level-two section's Markdown table header and data rows."""

    sections = _section_blocks(text).get(heading, [])
    if not sections:
        return [], []
    return _table_rows(sections[0])


def parse_release_target_status(text: str) -> dict[str, dict[str, str]]:
    """Return architecture-backed release-status rows keyed by target ID."""

    header, rows = parse_section_table(text, "## Release Target Status")
    if tuple(header) != RELEASE_TARGET_STATUS_HEADERS:
        return {}
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        if len(row) != len(RELEASE_TARGET_STATUS_HEADERS):
            continue
        result[row[0]] = {
            name: value
            for name, value in zip(RELEASE_TARGET_STATUS_HEADERS, row, strict=True)
        }
    return result


def release_target_status_duplicates(text: str) -> set[str]:
    """Return duplicated Release Target Status target IDs."""

    _header, rows = parse_section_table(text, "## Release Target Status")
    identities = [row[0] for row in rows if row]
    return {
        identity for identity, count in Counter(identities).items() if count > 1
    }


def check_handoff_table(
    text: str,
    heading: str,
    expected_headers: tuple[str, ...],
) -> tuple[list[str], list[list[str]]]:
    """Validate one required name-only human handoff table."""

    findings: list[str] = []
    header, rows = parse_section_table(text, heading)
    label = heading.removeprefix("## ")
    if not header:
        return [f"{label}: missing section or Markdown table"], []
    if any(cell in {"value", "secret value"} for cell in header):
        findings.append(f"{label}: must not include a secret-value column")
    if tuple(header) != expected_headers:
        findings.append(f"{label}: expected columns {' | '.join(expected_headers)}")
        return findings, []
    if not rows:
        findings.append(
            f"{label}: keep at least one filled row or an explicit none / n/a row"
        )
    valid_rows: list[list[str]] = []
    identities: set[str] = set()
    for row in rows:
        if len(row) != len(expected_headers):
            findings.append(
                f"{label}: each row must have {len(expected_headers)} columns"
            )
            continue
        identity = row[0].strip()
        normalized_identity = identity.casefold()
        if normalized_identity not in IDENTITY_ABSENT_VALUES:
            if normalized_identity in identities:
                findings.append(
                    f"{label}: duplicate identity row {identity!r}"
                )
            identities.add(normalized_identity)
        valid_rows.append(row)
    return findings, valid_rows


def _validate_release_target_status(
    text: str, architecture_text: str
) -> list[str]:
    contract, parser_findings = parse_release_targets(architecture_text)
    findings = list(parser_findings)
    header, rows = parse_section_table(text, "## Release Target Status")
    label = "Release Target Status"
    if not header:
        return findings + [f"{label}: architecture-backed records require this section and table"]
    if tuple(header) != RELEASE_TARGET_STATUS_HEADERS:
        findings.append(
            f"{label}: expected columns {' | '.join(RELEASE_TARGET_STATUS_HEADERS)}"
        )
        return findings

    architecture_targets = contract.by_id()
    seen: set[str] = set()
    for row in rows:
        if len(row) != len(RELEASE_TARGET_STATUS_HEADERS):
            findings.append(f"{label}: each row must have {len(RELEASE_TARGET_STATUS_HEADERS)} columns")
            continue
        (
            target_id,
            surface,
            stage,
            provider,
            endpoint,
            expected,
            deployed,
            artifact,
            availability,
            checked,
            status,
        ) = row
        if target_id in seen:
            findings.append(f"{label}: duplicate release target {target_id!r}")
            continue
        seen.add(target_id)
        target = architecture_targets.get(target_id)
        if target is None:
            findings.append(
                f"{label}: {target_id!r} is not an architecture release target"
            )
            continue
        if surface != target.surface:
            findings.append(
                f"{label}: {target_id} surface must be {target.surface!r}, not {surface!r}"
            )
        if stage != target.stage:
            findings.append(
                f"{label}: {target_id} stage must be {target.stage!r}, not {stage!r}"
            )
        expected_provider_channel = f"{target.provider};{target.channel}"
        if provider.casefold() != expected_provider_channel.casefold():
            findings.append(
                f"{label}: {target_id} provider/channel must be "
                f"{expected_provider_channel!r}, not {provider!r}"
            )
        if status != "pending" and (endpoint.casefold() in ABSENT_VALUES or endpoint.casefold() == "pending"):
            findings.append(
                f"{label}: {target_id} needs a target-specific endpoint or domain"
            )
        elif status != "pending" and ("<" in endpoint or ">" in endpoint):
            findings.append(
                f"{label}: {target_id} endpoint or domain contains a placeholder"
            )
        if (
            status == "PASS"
            and target.surface_class
            in {"hosted_web", "hosted_api", "worker", "job", "webhook", "realtime"}
            and endpoint.casefold().startswith("n/a")
        ):
            findings.append(
                f"{label}: hosted target {target_id} needs a concrete endpoint or domain"
            )
        for endpoint_finding in _endpoint_findings(
            target.surface_class,
            target.stage,
            target.public_discoverability,
            endpoint,
            status,
            artifact,
            provider,
        ):
            findings.append(f"{label}: {target_id} {endpoint_finding}")
        if status not in {*ENVIRONMENT_STATUSES, "pending"}:
            findings.append(f"{label}: {target_id} has invalid status {status!r}")
        no_independent_artifact = allows_no_independent_artifact(target)
        if artifact.casefold() == "n/a" and not no_independent_artifact:
            findings.append(
                f"{label}: target {target_id} may use artifact n/a only when architecture Artifact kind is no independent artifact"
            )
        if (
            artifact.casefold() not in {"", "pending", "n/a"}
            and no_independent_artifact
        ):
            findings.append(
                f"{label}: target {target_id} must use artifact n/a because architecture Artifact kind is no independent artifact"
            )
        if status and status != "pending" and not checked:
            findings.append(f"{label}: {target_id} status requires a checked time")
        checked_at = None
        if checked and checked != "pending":
            checked_at = _timestamp(checked)
            if checked_at is None:
                findings.append(f"{label}: {target_id} checked time must be RFC3339 with a real timezone")
            elif checked_at > datetime.now(timezone.utc):
                findings.append(f"{label}: {target_id} checked time cannot be in the future")
        if status == "PASS":
            if not FULL_SHA_RE.fullmatch(expected):
                findings.append(
                    f"{label}: PASS target {target_id} needs a full lowercase Expected SHA"
                )
            if not FULL_SHA_RE.fullmatch(deployed):
                findings.append(
                    f"{label}: PASS target {target_id} needs a full lowercase Deployed SHA"
                )
            if expected != deployed:
                findings.append(
                    f"{label}: PASS target {target_id} requires Expected and Deployed SHAs to be identical"
                )
            artifact_is_valid = (
                no_independent_artifact and artifact.casefold() == "n/a"
            ) or (
                not no_independent_artifact
                and bool(artifact)
                and artifact.casefold() not in ABSENT_VALUES
                and bool(BUILD_IDENTITY_RE.fullmatch(artifact))
            )
            if not artifact_is_valid:
                findings.append(
                    f"{label}: PASS target {target_id} needs an exact artifact or build identity"
                    + (" `n/a` because architecture Artifact kind is no independent artifact" if no_independent_artifact else "")
                )
            if availability.casefold() in ABSENT_VALUES:
                findings.append(
                    f"{label}: PASS target {target_id} needs availability evidence"
                )
            native = target.surface_class in {
                "ios",
                "android",
                "macos",
                "windows",
                "browser_extension",
            }
            availability_terms = (
                ("install", "download", "artifact", "build")
                if native
                else ("url", "route", "api", "smoke", "acceptance")
            )
            if availability.casefold() not in ABSENT_VALUES and not any(
                term in availability.casefold() for term in availability_terms
            ):
                findings.append(
                    f"{label}: PASS target {target_id} availability evidence must name "
                    + ("install/download or artifact/build proof" if native else "hosted route/API or smoke proof")
                )

    missing = sorted(set(architecture_targets) - seen)
    if missing:
        findings.append(
            f"{label}: architecture release targets are missing: {', '.join(missing)}"
        )
    return findings


def check_deployment_text(text: str, *, architecture_text: str | None = None) -> list[str]:
    findings: list[str] = []
    sections = _section_blocks(text)
    for heading in KNOWN_LEVEL_TWO_SECTIONS:
        count = len(sections.get(heading, []))
        if count > 1:
            findings.append(
                f"{heading.removeprefix('## ')}: duplicate required level-2 section"
            )
    if architecture_text is not None:
        findings.extend(_validate_release_target_status(text, architecture_text))
    for number, line in enumerate(active_text(text).splitlines(), start=1):
        for marker in PLACEHOLDER_MARKERS:
            if marker in line:
                findings.append(
                    f"line {number}: unresolved placeholder {marker!r} — fill the record from the live project"
                )

    release_findings, release_rows = check_handoff_table(
        text, "## Release Unit Names", RELEASE_UNIT_HEADERS
    )
    findings.extend(release_findings)
    if architecture_text is not None:
        architecture_contract, architecture_findings = parse_release_targets(architecture_text)
        findings.extend(architecture_findings)
        architecture_by_surface: dict[str, object] = {}
        for target in architecture_contract.targets:
            if target.stage == "production":
                architecture_by_surface[target.surface] = target
        recorded_surfaces: set[str] = set()
        for row in release_rows:
            if len(row) != len(RELEASE_UNIT_HEADERS):
                continue
            surface, suffix, production_name, development_name, _production_provider, _development_provider = row
            if surface in recorded_surfaces:
                continue
            recorded_surfaces.add(surface)
            production = architecture_by_surface.get(surface)
            development = next(
                (
                    target
                    for target in architecture_contract.targets
                    if target.surface == surface and target.stage == "development"
                ),
                None,
            )
            if production is None or development is None:
                findings.append(
                    f"Release Unit Names: {surface!r} is not an exact architecture surface"
                )
                continue
            if suffix != production.surface_suffix:
                findings.append(
                    f"Release Unit Names: {surface} suffix must equal architecture {production.surface_suffix!r}"
                )
            if production_name != production.release_name:
                findings.append(
                    f"Release Unit Names: {surface} production release name must equal architecture {production.release_name!r}"
                )
            if development_name != development.release_name:
                findings.append(
                    f"Release Unit Names: {surface} development release name must equal architecture {development.release_name!r}"
                )
            expected_production_provider = f"{production.provider};{production.channel}"
            expected_development_provider = f"{development.provider};{development.channel}"
            if _production_provider.casefold() != expected_production_provider.casefold():
                findings.append(
                    f"Release Unit Names: {surface} production provider/channel must equal architecture {expected_production_provider!r}"
                )
            if _development_provider.casefold() != expected_development_provider.casefold():
                findings.append(
                    f"Release Unit Names: {surface} development provider/channel must equal architecture {expected_development_provider!r}"
                )
        missing_surfaces = sorted(set(architecture_by_surface) - recorded_surfaces)
        if missing_surfaces:
            findings.append(
                "Release Unit Names: architecture surfaces are missing: "
                + ", ".join(missing_surfaces)
            )
    release_name_surfaces: dict[str, str] = {}
    for row in release_rows:
        surface, suffix, production_name, development_name, production_provider, development_provider = row
        if surface.casefold() in {"none", "n/a"}:
            findings.append("Release Unit Names: a deployable record needs at least one release unit")
            continue
        for label, value in (
            ("surface", surface),
            ("surface suffix", suffix),
            ("production release name", production_name),
            ("development release name", development_name),
            ("production provider / channel", production_provider),
            ("development provider / channel", development_provider),
        ):
            if value.casefold() in ABSENT_VALUES:
                findings.append(f"Release Unit Names: {surface} has no {label}")
        for label, value in (
            ("surface suffix", suffix),
            ("production release name", production_name),
            ("development release name", development_name),
        ):
            if value.casefold() not in ABSENT_VALUES and not LOWER_KEBAB_RE.fullmatch(value):
                findings.append(f"Release Unit Names: {surface} {label} must be lowercase kebab case")
        if production_name.endswith("-prod"):
            findings.append(f"Release Unit Names: {surface} production release name must not end in -prod")
        if suffix and production_name and not production_name.endswith(f"-{suffix}"):
            findings.append(
                f"Release Unit Names: {surface} production release name must end in -{suffix}"
            )
        if production_name and development_name != f"{production_name}-dev":
            findings.append(
                f"Release Unit Names: {surface} development release name must equal {production_name}-dev"
            )
        for release_name in (production_name, development_name):
            normalized_name = release_name.casefold()
            if normalized_name in ABSENT_VALUES:
                continue
            prior_surface = release_name_surfaces.get(normalized_name)
            if prior_surface is not None and prior_surface.casefold() != surface.casefold():
                findings.append(
                    f"Release Unit Names: release name {release_name!r} is reused by surfaces {prior_surface!r} and {surface!r}"
                )
            else:
                release_name_surfaces[normalized_name] = surface

    secret_findings, secret_rows = check_handoff_table(
        text, "## Required Secrets and Variables", SECRET_HEADERS
    )
    findings.extend(secret_findings)
    for row in secret_rows:
        name, kind, consumer, preview, production, source, status = row
        if name.lower() in {"none", "n/a"}:
            continue
        if kind.lower() not in {"secret", "variable"}:
            findings.append(
                f"Required Secrets and Variables: {name} kind must be secret or variable"
            )
        for label, value in (
            ("consumer", consumer),
            ("preview placement", preview),
            ("production placement", production),
            ("source / owner", source),
        ):
            if value.lower() in ABSENT_VALUES:
                findings.append(
                    f"Required Secrets and Variables: {name} has no {label}"
                )
        if not _human(source):
            findings.append(
                f"Required Secrets and Variables: {name} source / owner must name a human"
            )
        if status.lower() not in HANDOFF_STATUSES:
            findings.append(
                f"Required Secrets and Variables: {name} has invalid status {status!r}"
            )

    external_findings, external_rows = check_handoff_table(
        text, "## External Console Setup", EXTERNAL_SETUP_HEADERS
    )
    findings.extend(external_findings)
    for row in external_rows:
        service, setting, preview, production, owner, status = row
        if service.lower() in {"none", "n/a"}:
            continue
        for label, value in (
            ("setting", setting),
            ("preview / non-production target", preview),
            ("production target", production),
            ("owner", owner),
        ):
            if value.lower() in ABSENT_VALUES:
                findings.append(f"External Console Setup: {service} has no {label}")
        if not _human(owner):
            findings.append(
                f"External Console Setup: {service} owner must name a human"
            )
        if status.lower() not in HANDOFF_STATUSES:
            findings.append(
                f"External Console Setup: {service} has invalid status {status!r}"
            )

    status_sections = sections.get("## Environment Status", [])
    status_text = "\n".join(status_sections[0]) if status_sections else ""
    rows: dict[str, dict[str, str]] = {}
    duplicate_environments: set[str] = set()
    for line in status_text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6 or cells[0].lower() in {"environment", "---"}:
            continue
        environment = cells[0].lower()
        if set(environment) <= {"-", " "}:
            continue
        if environment in rows:
            if environment in ENVIRONMENT_ROWS:
                duplicate_environments.add(environment)
            continue
        rows[environment] = {
            "url": cells[1],
            "expected": cells[2],
            "deployed": cells[3],
            "checked": cells[4],
            "status": cells[5],
        }
    for environment in sorted(duplicate_environments):
        findings.append(f"Environment Status: duplicate {environment} row")
    for environment in ENVIRONMENT_ROWS:
        row = rows.get(environment)
        if row is None:
            findings.append(f"Environment Status: missing the {environment} row")
            continue
        if not row["url"] and not row["checked"]:
            # Not verified yet; the Record section still names the URL.
            continue
        if not row["url"]:
            findings.append(f"Environment Status: {environment} is checked but has no URL")
        status = row["status"].strip()
        if row["checked"]:
            for column in ("expected", "deployed"):
                if not FULL_SHA_RE.match(row[column]):
                    findings.append(
                        f"Environment Status: {environment} {column} must be a full lowercase SHA once checked"
                    )
            if not status:
                findings.append(
                    f"Environment Status: {environment} is checked but has no status"
                )
        if status:
            if status not in ENVIRONMENT_STATUSES:
                findings.append(
                    f"Environment Status: {environment} has invalid status {status!r}; "
                    "expected one of PASS, FAIL, BLOCKED, or UNVALIDATED"
                )
            elif not row["checked"]:
                findings.append(
                    f"Environment Status: {environment} status {status!r} requires a Checked value"
                )
            elif status == "PASS" and row["expected"] != row["deployed"]:
                findings.append(
                    f"Environment Status: {environment} PASS requires Expected head "
                    "and Deployed SHA to be identical"
                )
    resource_sections = sections.get("## Resource Isolation", [])
    resource_text = "\n".join(resource_sections[0]) if resource_sections else ""
    _, resource_rows = _table_rows(resource_text.splitlines())
    resource_identities: set[str] = set()
    for row in resource_rows:
        if len(row) < 3:
            continue
        identity = row[0].strip()
        normalized_identity = identity.casefold()
        if normalized_identity in IDENTITY_ABSENT_VALUES:
            continue
        if normalized_identity in resource_identities:
            findings.append(f"Resource Isolation: duplicate identity row {identity!r}")
        resource_identities.add(normalized_identity)
        if normalized_identity not in BINDING_CLASSES:
            continue
        production, development = row[1].lower(), row[2].lower()
        if production in ABSENT_VALUES or development in ABSENT_VALUES:
            continue
        if production == development:
            findings.append(
                f"Resource Isolation: {row[0]} must not share one resource between production and development"
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment", type=Path, default=Path("docs/DEPLOYMENT.md"))
    parser.add_argument("--architecture", type=Path)
    args = parser.parse_args(argv)
    path: Path = args.deployment
    if not path.is_file():
        print(f"deployment record not found: {path}", file=sys.stderr)
        return 2
    architecture_text = None
    if args.architecture is not None:
        if not args.architecture.is_file():
            print(f"architecture record not found: {args.architecture}", file=sys.stderr)
            return 2
        architecture_text = args.architecture.read_text(encoding="utf-8")
    findings = check_deployment_text(
        path.read_text(encoding="utf-8"), architecture_text=architecture_text
    )
    for finding in findings:
        print(f"{path}: {finding}")
    if findings:
        return 1
    print(f"{path} is resolved and its handoff and environment rows are coherent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
