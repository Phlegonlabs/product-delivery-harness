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
production and development columns.
Executing the platform's deployed-commit check command stays with the parent
or operator — this tool never runs recorded commands, reads secret values, or
touches the platform.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

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
LOWER_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENVIRONMENT_ROWS = ("development", "production")
BINDING_CLASSES = ("d1 database", "kv namespace", "r2 bucket", "durable objects")
ABSENT_VALUES = {"", "-", "n/a"}
IDENTITY_ABSENT_VALUES = {"", "-"}
HANDOFF_STATUSES = {"pending", "configured", "verified", "n/a"}
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
    "provider / channel",
)
KNOWN_LEVEL_TWO_SECTIONS = (
    "## Record",
    "## Release Unit Names",
    "## Resource Isolation",
    "## Required Secrets and Variables",
    "## External Console Setup",
    "## Environment Status",
)
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


def check_deployment_text(text: str) -> list[str]:
    findings: list[str] = []
    sections = _section_blocks(text)
    for heading in KNOWN_LEVEL_TWO_SECTIONS:
        count = len(sections.get(heading, []))
        if count > 1:
            findings.append(
                f"{heading.removeprefix('## ')}: duplicate required level-2 section"
            )
    for number, line in enumerate(text.splitlines(), start=1):
        for marker in PLACEHOLDER_MARKERS:
            if marker in line:
                findings.append(
                    f"line {number}: unresolved placeholder {marker!r} — fill the record from the live project"
                )

    release_findings, release_rows = check_handoff_table(
        text, "## Release Unit Names", RELEASE_UNIT_HEADERS
    )
    findings.extend(release_findings)
    for row in release_rows:
        surface, suffix, production_name, development_name, provider = row
        if surface.casefold() in {"none", "n/a"}:
            findings.append("Release Unit Names: a deployable record needs at least one release unit")
            continue
        for label, value in (
            ("surface", surface),
            ("surface suffix", suffix),
            ("production release name", production_name),
            ("development release name", development_name),
            ("provider / channel", provider),
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
        if row["checked"]:
            for column in ("expected", "deployed"):
                if not FULL_SHA_RE.match(row[column]):
                    findings.append(
                        f"Environment Status: {environment} {column} must be a full lowercase SHA once checked"
                    )
            if not row["status"]:
                findings.append(
                    f"Environment Status: {environment} is checked but has no status"
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
    args = parser.parse_args(argv)
    path: Path = args.deployment
    if not path.is_file():
        print(f"deployment record not found: {path}", file=sys.stderr)
        return 2
    findings = check_deployment_text(path.read_text(encoding="utf-8"))
    for finding in findings:
        print(f"{path}: {finding}")
    if findings:
        return 1
    print(f"{path} is resolved and its handoff and environment rows are coherent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
