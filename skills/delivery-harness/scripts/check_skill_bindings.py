#!/usr/bin/env python3
"""Verify that a project's Skill Bindings pin the skills they bind.

Reads the one active Skill Bindings table in a project's AGENTS.md. Every slot
must bind one exact skill name and carry a pinned SHA-256 of the complete skill
tree. The checker recomputes the hash and fails on prose or a
compound binding, a mismatch, an unpinned binding, or a skill it cannot locate.
Changing a bound skill's content therefore requires an explicit pin update,
which is the review moment: a skill update is a code change to the instruction
path.

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
SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REQUIRED_SLOTS = {
    "ui_design",
    "style_integration",
    "design_compilation",
    "frontend_implementation",
    "ui_quality_verification",
    "code_security_verification",
}
TEXT_SUFFIXES = {
    ".css", ".html", ".js", ".json", ".md", ".ps1", ".py", ".sh",
    ".toml", ".ts", ".txt", ".yaml", ".yml",
}
HTML_BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "body", "caption", "center",
    "colgroup", "dd", "details", "dialog", "dir", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "form", "frameset", "head",
    "header", "html", "iframe", "legend", "li", "main", "menu", "nav",
    "noframes", "ol", "optgroup", "option", "p", "pre", "script", "search",
    "section", "style", "summary", "table", "tbody", "td", "template", "tfoot",
    "th", "thead", "textarea", "title", "tr", "ul",
}
FENCE_OPEN_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
FENCE_CLOSE_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})[ \t]*$")
TYPE1_RE = re.compile(r"^[ ]{0,3}<(script|pre|style|textarea)(?:\s|>|$)", re.I)
TYPE6_RE = re.compile(
    r"^[ ]{0,3}</?(?:" + "|".join(sorted(HTML_BLOCK_TAGS)) + r")(?:\s|/?>|$)",
    re.I,
)
TYPE7_RE = re.compile(
    r"^[ ]{0,3}</?[A-Za-z][A-Za-z0-9-]*(?:\s+[^<>]*)?/?>[ \t]*$"
)


def _html_block_start(line: str) -> tuple[str, str | None] | None:
    leading = len(line) - len(line.lstrip(" "))
    if leading > 3:
        return None
    stripped = line[leading:]
    type1 = TYPE1_RE.match(line)
    if type1:
        return "terminator", f"</{type1.group(1).casefold()}>"
    if stripped.startswith("<!--"):
        return "terminator", "-->"
    if stripped.startswith("<?"):
        return "terminator", "?>"
    if re.match(r"<![A-Z]", stripped):
        return "terminator", ">"
    if stripped.startswith("<![CDATA["):
        return "terminator", "]]" + ">"
    if TYPE6_RE.match(line) or TYPE7_RE.match(line):
        return "blank", None
    return None


def active_markdown_lines(text: str) -> list[tuple[int, str]]:
    active: list[tuple[int, str]] = []
    fence: tuple[str, int] | None = None
    in_comment = False
    html_block_terminator: str | None = None
    html_block_until_blank = False
    for number, line in enumerate(text.splitlines(), start=1):
        if fence is not None:
            closing_match = FENCE_CLOSE_RE.match(line)
            if (
                closing_match
                and closing_match.group(1)[0] == fence[0]
                and len(closing_match.group(1)) >= fence[1]
            ):
                fence = None
            continue
        if html_block_terminator is not None:
            if html_block_terminator.casefold() in line.casefold():
                html_block_terminator = None
            continue
        if html_block_until_blank:
            if not line.strip():
                html_block_until_blank = False
            continue
        if line.startswith("\t") or re.match(r"^ {4,}\S", line):
            continue
        fence_match = FENCE_OPEN_RE.match(line)
        if fence_match:
            fence = (fence_match.group(1)[0], len(fence_match.group(1)))
            continue
        html_block = _html_block_start(line)
        if html_block is not None:
            kind, terminator = html_block
            if kind == "terminator" and terminator is not None:
                if terminator.casefold() not in line.casefold()[
                    line.casefold().find("<") + 1 :
                ]:
                    html_block_terminator = terminator
            else:
                html_block_until_blank = True
            continue
        output = ""
        remainder = line
        while remainder:
            if in_comment:
                end = remainder.find("-->")
                if end < 0:
                    remainder = ""
                    break
                in_comment = False
                remainder = remainder[end + 3 :]
                continue
            start = remainder.find("<!--")
            if start < 0:
                output += remainder
                break
            output += remainder[:start]
            end = remainder.find("-->", start + 4)
            if end < 0:
                in_comment = True
                break
            remainder = remainder[end + 3 :]
        if output.strip():
            active.append((number, output))
    return active


def parse_binding_rows(text: str) -> list[tuple[str, str, str, int]]:
    """Return (slot, bound-skill, pin, line-number) for each binding row."""

    rows, _ = parse_binding_contract(text)
    return rows


def parse_binding_contract(
    text: str,
) -> tuple[list[tuple[str, str, str, int]], list[str]]:
    active = list(active_markdown_lines(text))
    heading_indexes = [
        index
        for index, (_, line) in enumerate(active)
        if line.strip() == "## Skill Bindings"
    ]
    if len(heading_indexes) != 1:
        return [], ["AGENTS.md must contain exactly one active ## Skill Bindings section"]
    start = heading_indexes[0] + 1
    end = len(active)
    for index in range(start, len(active)):
        if active[index][1].startswith("## "):
            end = index
            break
    table_lines = [item for item in active[start:end] if item[1].strip().startswith("|")]
    findings: list[str] = []
    if len(table_lines) < 2:
        return [], ["Skill Bindings must contain the exact four-column table"]

    def cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    expected_header = ["Slot", "Stage", "Bound skill", "Pinned SHA-256"]
    if cells(table_lines[0][1]) != expected_header:
        findings.append("Skill Bindings table header must be exactly: " + " | ".join(expected_header))
    separator = cells(table_lines[1][1])
    if len(separator) != 4 or any(
        re.fullmatch(r":?-{3,}:?", value) is None for value in separator
    ):
        findings.append("Skill Bindings table must have one four-column separator row")

    rows: list[tuple[str, str, str, int]] = []
    seen_slots: set[str] = set()
    for number, line in table_lines[2:]:
        row = cells(line)
        if len(row) != 4:
            findings.append(f"line {number}: malformed Skill Bindings row must have four cells")
            continue
        slot, _stage, bound, pin = row
        if slot in seen_slots:
            findings.append(f"line {number}: duplicate Skill Bindings slot {slot!r}")
        seen_slots.add(slot)
        rows.append((slot, bound, pin.strip("`"), number))
    missing = sorted(REQUIRED_SLOTS - seen_slots)
    extra = sorted(seen_slots - REQUIRED_SLOTS)
    if missing or extra:
        findings.append(
            "Skill Bindings must use exactly the required slots; missing: "
            + (", ".join(missing) or "none")
            + "; extra: "
            + (", ".join(extra) or "none")
        )
    return rows, findings


def bound_skill_name(cell: str) -> str | None:
    value = cell.strip().strip("`")
    if not SKILL_NAME_RE.fullmatch(value):
        return None
    return value


def locate_skill(name: str, skill_dirs: list[Path]) -> Path | None:
    for directory in skill_dirs:
        candidate = directory / name / "SKILL.md"
        if candidate.is_file():
            return candidate
    return None


def hash_skill(path: Path) -> str:
    root = path.parent if path.name == "SKILL.md" else path
    digest = hashlib.sha256()
    symlinks = [candidate for candidate in root.rglob("*") if candidate.is_symlink()]
    if symlinks:
        raise ValueError(
            "skill tree contains symlinks: "
            + ", ".join(candidate.relative_to(root).as_posix() for candidate in symlinks)
        )
    files = sorted(
        candidate
        for candidate in root.rglob("*")
        if candidate.is_file()
        and "__pycache__" not in candidate.parts
        and ".pytest_cache" not in candidate.parts
        and candidate.suffix.casefold() not in {".pyc", ".pyo"}
    )
    if not files:
        raise ValueError(f"skill tree is empty: {root}")
    for candidate in files:
        relative = candidate.relative_to(root).as_posix().encode("utf-8")
        content = candidate.read_bytes()
        if candidate.suffix.casefold() in TEXT_SUFFIXES:
            content = content.replace(b"\r\n", b"\n")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def check_bindings(
    agents_md: Path, skill_dirs: list[Path]
) -> tuple[list[str], dict[str, str]]:
    findings: list[str] = []
    hashes: dict[str, str] = {}
    text = agents_md.read_text(encoding="utf-8")
    rows, parse_findings = parse_binding_contract(text)
    findings.extend(parse_findings)
    for slot, cell, pin, number in rows:
        name = bound_skill_name(cell)
        if name is None:
            findings.append(
                f"line {number}: slot {slot!r} must bind exactly one skill name, "
                f"got {cell!r}"
            )
            continue
        located = locate_skill(name, skill_dirs)
        if located is None:
            findings.append(
                f"line {number}: bound skill {name!r} for slot {slot!r} "
                f"not found under any skill directory"
            )
            continue
        try:
            current = hash_skill(located)
        except (OSError, ValueError) as exc:
            findings.append(f"line {number}: cannot hash bound skill {name!r}: {exc}")
            continue
        hashes[name] = current
        if not PIN_RE.match(pin):
            findings.append(
                f"line {number}: {name!r} is bound without a pinned full-tree hash "
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
        agents_md.parent / "skills",
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
        help="print the current full-tree hash for each bound skill to pin",
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
