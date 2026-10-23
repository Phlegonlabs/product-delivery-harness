#!/usr/bin/env python3
"""Validate canonical skills against the Agent Skills open specification.

Checks every skill directory under --skills-root for: a SKILL.md with YAML
frontmatter; frontmatter keys limited to the spec's set; a name that matches
the directory name; a non-empty description of at most 1024 characters; and a
body of at most 500 lines. Read-only; exits 1 with findings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

SPEC_FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
MAX_DESCRIPTION_CHARS = 1024
MAX_BODY_LINES = 500


def split_frontmatter(text: str) -> tuple[str, int] | None:
    """Return the frontmatter text and the body line count, or None if unclosed."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index]), len(lines) - index - 1
    return None


def check_skill(skill_dir: Path) -> list[str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"]
    prefix = f"{skill_dir.name}/SKILL.md"
    parts = split_frontmatter(skill_md.read_text(encoding="utf-8"))
    if parts is None:
        return [f"{prefix}: missing or unterminated YAML frontmatter"]
    try:
        fields = yaml.safe_load(parts[0])
    except yaml.YAMLError as exc:
        return [f"{prefix}: invalid YAML frontmatter: {exc}"]
    if not isinstance(fields, dict):
        return [f"{prefix}: frontmatter is not a mapping"]
    findings: list[str] = []
    unknown = sorted(str(key) for key in set(fields) - SPEC_FRONTMATTER_KEYS)
    if unknown:
        findings.append(f"{prefix}: frontmatter keys outside the spec: " + ", ".join(unknown))
    name = fields.get("name")
    if not name:
        findings.append(f"{prefix}: frontmatter has no name")
    elif name != skill_dir.name:
        findings.append(f"{prefix}: name {name!r} does not match directory name")
    description = fields.get("description")
    if not description:
        findings.append(f"{prefix}: frontmatter has no description")
    elif len(str(description)) > MAX_DESCRIPTION_CHARS:
        findings.append(f"{prefix}: description exceeds {MAX_DESCRIPTION_CHARS} characters")
    if parts[1] > MAX_BODY_LINES:
        findings.append(
            f"{prefix}: body is {parts[1]} lines, over the {MAX_BODY_LINES}-line guidance"
        )
    return findings


def check_skills_root(root: Path) -> list[str]:
    findings: list[str] = []
    for skill_dir in sorted(item for item in root.iterdir() if item.is_dir()):
        if (skill_dir / "SKILL.md").exists() or any(skill_dir.iterdir()):
            findings.extend(check_skill(skill_dir))
    return findings


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=default_root,
        help=f"directory holding the skills (default: {default_root})",
    )
    args = parser.parse_args(argv)
    root: Path = args.skills_root
    if not root.is_dir():
        print(f"skills root not found: {root}", file=sys.stderr)
        return 2
    findings = check_skills_root(root)
    for finding in findings:
        print(finding)
    if findings:
        return 1
    print(f"all skills under {root} satisfy the Agent Skills specification checks")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
