#!/usr/bin/env python3
"""Verify that a project's Skill Bindings pin the skills they bind.

Reads the Skill Bindings table in a project's AGENTS.md. Every bound skill
that is not the bundled default must carry a pinned SHA-256 of its SKILL.md;
the checker recomputes the hash from the installed skill and fails on a
mismatch, an unpinned binding, or a skill it cannot locate. Changing a bound
skill's content therefore requires an explicit pin update, which is the
review moment: a skill update is a code change to the instruction path.

Read-only. --show-hashes prints the current hashes to pin; it never edits
AGENTS.md.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

PIN_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_binding_rows(text: str) -> list[tuple[str, str, str, int]]:
    """Return (slot, bound-skill, pin, line-number) for each binding row."""

    rows: list[tuple[str, str, str, int]] = []
    in_section = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            in_section = line.strip() == "## Skill Bindings"
            continue
        if not in_section or not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"Slot", "---"} or set(cells[0]) <= {"-", " "}:
            continue
        pin = cells[3].strip().strip("`") if len(cells) >= 4 else ""
        rows.append((cells[0], cells[2], pin, number))
    return rows


def is_bound_skill(cell: str) -> bool:
    value = cell.strip().strip("`")
    if not value or value.startswith("<"):
        return False
    return "bundled" not in value.lower()


def locate_skill(name: str, skill_dirs: list[Path]) -> Path | None:
    for directory in skill_dirs:
        candidate = directory / name / "SKILL.md"
        if candidate.is_file():
            return candidate
    return None


def hash_skill(path: Path) -> str:
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def check_bindings(
    agents_md: Path, skill_dirs: list[Path]
) -> tuple[list[str], dict[str, str]]:
    findings: list[str] = []
    hashes: dict[str, str] = {}
    text = agents_md.read_text(encoding="utf-8")
    for slot, cell, pin, number in parse_binding_rows(text):
        if not is_bound_skill(cell):
            continue
        name = cell.strip().strip("`")
        located = locate_skill(name, skill_dirs)
        if located is None:
            findings.append(
                f"line {number}: bound skill {name!r} for slot {slot!r} "
                f"not found under any skill directory"
            )
            continue
        current = hash_skill(located)
        hashes[name] = current
        if not PIN_RE.match(pin):
            findings.append(
                f"line {number}: {name!r} is bound without a pinned SKILL.md hash "
                f"(current: {current})"
            )
        elif pin != current:
            findings.append(
                f"line {number}: pinned hash for {name!r} does not match the "
                f"installed skill (pinned {pin[:12]}..., installed {current[:12]}...); "
                "review the skill change, then update the pin deliberately"
            )
    return findings, hashes


def default_skill_dirs(agents_md: Path) -> list[Path]:
    return [
        agents_md.parent / ".agents" / "skills",
        Path.home() / ".agents" / "skills",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agents-md", type=Path, default=Path("AGENTS.md"))
    parser.add_argument(
        "--skill-dir",
        type=Path,
        action="append",
        default=[],
        help="additional directory holding installed skills (repeatable)",
    )
    parser.add_argument(
        "--show-hashes",
        action="store_true",
        help="print the current SKILL.md hash for each bound skill to pin",
    )
    args = parser.parse_args(argv)

    agents_md: Path = args.agents_md
    if not agents_md.is_file():
        print(f"AGENTS.md not found: {agents_md}", file=sys.stderr)
        return 2
    skill_dirs = list(args.skill_dir) or default_skill_dirs(agents_md)
    findings, hashes = check_bindings(agents_md, skill_dirs)
    if args.show_hashes:
        for name, digest in sorted(hashes.items()):
            print(f"{name}: {digest}")
    for finding in findings:
        print(f"{agents_md}: {finding}")
    if findings:
        return 1
    if not args.show_hashes:
        print(f"all bound skills in {agents_md} are pinned and unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
