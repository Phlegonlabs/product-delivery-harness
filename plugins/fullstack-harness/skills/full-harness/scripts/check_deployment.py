#!/usr/bin/env python3
"""Read-only structural check of a project's DEPLOYMENT.md record.

Validates that the deployment record is resolved (no template placeholders)
and that its Environment Status table is coherent: both preview and
production rows exist with a URL, and any verified row carries full lowercase
SHAs and a status. Executing the platform's deployed-commit check command
stays with the parent or operator — this tool never runs recorded commands
and never touches the platform.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PLACEHOLDER_MARKERS = ("<fill>", "<cloudflare |", "<pattern>", "<url>", "<databases")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ENVIRONMENT_ROWS = ("preview", "production")


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


def check_deployment_text(text: str) -> list[str]:
    findings: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for marker in PLACEHOLDER_MARKERS:
            if marker in line:
                findings.append(
                    f"line {number}: unresolved placeholder {marker!r} — fill the record from the live project"
                )
    rows = parse_status_table(text)
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
    print(f"{path} is resolved and its environment rows are coherent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
