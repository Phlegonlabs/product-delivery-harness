#!/usr/bin/env python3
"""Validate canonical skills against the Agent Skills open specification.

Checks every skill directory under --skills-root for: a SKILL.md with YAML
frontmatter; frontmatter keys limited to the spec's set; a name that matches
the directory name; a non-empty description of at most 1024 characters; and a
body of at most 500 lines. Read-only; exits 1 with findings.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

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
TOP_LEVEL_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
BLOCK_SCALAR_RE = re.compile(r"^[|>](?:[1-9])?[+-]?$")


class FrontmatterError(ValueError):
    """A syntax error in the supported top-level frontmatter subset."""


def _strip_wrapping_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
        return value[1:-1]
    return value


def _scan_quoted_piece(
    piece: str,
    quote: str,
    content: list[str],
    *,
    opening: bool,
) -> bool:
    """Consume one folded piece of a quoted scalar.

    The first piece includes the opening quote; later pieces are already
    indented continuations. A closing quote must end the scalar (apart from a
    trailing comment), otherwise the value is malformed rather than a plain
    string with stray quote characters.
    """

    start = 1 if opening else 0
    index = start
    while index < len(piece):
        char = piece[index]
        if quote == '"' and char == "\\":
            # Preserve escaped characters and skip the escaped quote so it
            # cannot terminate the scalar early.
            if index + 1 < len(piece):
                content.append(piece[index : index + 2])
                index += 2
                continue
        if quote == "'" and char == "'" and index + 1 < len(piece) and piece[index + 1] == "'":
            content.append("''")
            index += 2
            continue
        if char == quote:
            trailing = piece[index + 1 :].strip()
            if trailing and not trailing.startswith("#"):
                raise FrontmatterError("invalid quoted scalar trailing text")
            return True
        content.append(char)
        index += 1
    return False


def _parse_frontmatter(text: str) -> tuple[dict[str, str], int]:
    """Parse scalar keys, values, and folded continuations.

    Blank lines and comments are valid inside the delimiters. Values are
    partitioned at their first colon so URLs and other colon-containing values
    remain intact.
    """

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("missing opening '---' delimiter")
    fields: dict[str, str] = {}
    index = 1
    while index < len(lines):
        line_number = index + 1
        line = lines[index]
        if line.strip() == "---":
            return fields, index + 1
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            # Blank and comment lines are inert inside frontmatter.
            index += 1
            continue
        if line.startswith((" ", "\t")):
            raise FrontmatterError(f"line {line_number}: orphan continuation")
        if ":" not in line:
            raise FrontmatterError(
                f"line {line_number}: malformed top-level line "
                "(expected 'key: value')"
            )
        key, _, value = line.partition(":")
        key = key.strip()
        if not key:
            raise FrontmatterError(f"line {line_number}: empty frontmatter key")
        if not TOP_LEVEL_KEY_RE.fullmatch(key):
            raise FrontmatterError(
                f"line {line_number}: malformed top-level key {key!r}"
            )
        if key in fields:
            raise FrontmatterError(
                f"line {line_number}: duplicate top-level key {key!r}"
            )

        raw_value = value.strip()
        mode = "plain"
        quote: str | None = None
        quote_content: list[str] = []
        quote_closed = False
        continuation_parts: list[str] = []
        if raw_value.startswith(("\"", "'")):
            mode = "quoted"
            quote = raw_value[0]
            quote_closed = _scan_quoted_piece(
                raw_value, quote, quote_content, opening=True
            )
        elif BLOCK_SCALAR_RE.fullmatch(raw_value):
            mode = "block"
        elif not raw_value:
            mode = "empty"
        else:
            continuation_parts.append(raw_value)
        index += 1

        # Consume folded/structured continuations owned by this top-level key.
        while index < len(lines):
            next_line = lines[index]
            next_stripped = next_line.strip()
            if next_line.strip() == "---":
                break
            if not next_stripped or next_stripped.startswith("#"):
                # Keep scanning so a blank/comment line does not orphan a
                # legitimate folded continuation. Block scalars retain blank
                # lines as content; comments outside a block stay inert.
                if mode == "block" and not next_stripped:
                    continuation_parts.append("")
                index += 1
                continue
            if not next_line.startswith((" ", "\t")):
                if mode == "quoted" and not quote_closed:
                    raise FrontmatterError(
                        f"line {index + 1}: unterminated quoted scalar for {key!r}"
                    )
                break
            if mode == "quoted":
                if quote_closed:
                    raise FrontmatterError(
                        f"line {index + 1}: indented continuation after closed quoted scalar"
                    )
                assert quote is not None
                if quote_content:
                    quote_content.append(" ")
                quote_closed = _scan_quoted_piece(
                    next_stripped, quote, quote_content, opening=False
                )
            elif mode == "block":
                continuation_parts.append(next_line.lstrip())
            else:
                # Empty values accept the simple multiline list shape (`- x`)
                # as well as ordinary folded scalar continuations.
                continuation_parts.append(next_stripped)
                if mode == "empty":
                    mode = "list" if next_stripped.startswith("-") else "plain"
            index += 1

        if mode == "quoted":
            if not quote_closed:
                raise FrontmatterError(f"unterminated quoted scalar for {key!r}")
            fields[key] = "".join(quote_content)
        elif mode == "block":
            separator = "\n" if raw_value.startswith("|") else " "
            fields[key] = separator.join(continuation_parts).rstrip("\n")
        elif continuation_parts:
            fields[key] = " ".join(continuation_parts)
        else:
            fields[key] = _strip_wrapping_quotes(raw_value)
    raise FrontmatterError("unterminated frontmatter (missing closing '---')")


def parse_frontmatter(text: str) -> tuple[dict[str, str], int] | None:
    """Parse the supported subset; return ``None`` when its syntax is invalid."""

    try:
        return _parse_frontmatter(text)
    except FrontmatterError:
        return None


def check_skill(skill_dir: Path) -> list[str]:
    findings: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
    try:
        fields, body_start = _parse_frontmatter(text)
    except FrontmatterError as exc:
        prefix = f"{skill_dir.name}/SKILL.md"
        if str(exc) == "missing opening '---' delimiter":
            return [f"{prefix}: missing YAML frontmatter"]
        return [f"{prefix}: invalid YAML frontmatter: {exc}"]
    unknown = sorted(set(fields) - SPEC_FRONTMATTER_KEYS)
    if unknown:
        findings.append(
            f"{skill_dir.name}/SKILL.md: frontmatter keys outside the spec: "
            + ", ".join(unknown)
        )
    name = fields.get("name")
    if not name:
        findings.append(f"{skill_dir.name}/SKILL.md: frontmatter has no name")
    elif name != skill_dir.name:
        findings.append(
            f"{skill_dir.name}/SKILL.md: name {name!r} does not match directory name"
        )
    description = fields.get("description")
    if not description:
        findings.append(f"{skill_dir.name}/SKILL.md: frontmatter has no description")
    elif len(description) > MAX_DESCRIPTION_CHARS:
        findings.append(
            f"{skill_dir.name}/SKILL.md: description exceeds {MAX_DESCRIPTION_CHARS} characters"
        )
    body_lines = len(text.splitlines()) - body_start
    if body_lines > MAX_BODY_LINES:
        findings.append(
            f"{skill_dir.name}/SKILL.md: body is {body_lines} lines, over the "
            f"{MAX_BODY_LINES}-line guidance"
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
    raise SystemExit(main())
