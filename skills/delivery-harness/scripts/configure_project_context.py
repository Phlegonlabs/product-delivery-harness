#!/usr/bin/env python3
"""Safely add host-specific project context files without overwriting local rules."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

from check_skill_bindings import PIN_RE, STAGE_SLOTS, bound_skill_name, parse_binding_contract


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "assets" / "templates"
DEFAULT_AGENTS_TEMPLATE = TEMPLATES_DIR / "PROJECT_AGENTS.template.md"
DEFAULT_CLAUDE_TEMPLATE = TEMPLATES_DIR / "PROJECT_CLAUDE.template.md"
MERGE_HEADING = "# Project Delivery Harness Shared Guidance"
MERGE_INTRO = (
    "Added by `configure_project_context.py --merge-agents`. Local rules above "
    "stay authoritative. Resolve any reported same-heading divergence by "
    "meaning; do not overwrite the local rules or bindings."
)
MERGE_PLAN_SCHEMA = "pdh-context-merge/1"
MERGE_PLAN_KEYS = {
    "schema",
    "reviewed",
    "agents_sha256",
    "template_sha256",
    "add_sections",
    "acknowledged_divergences",
}
FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t\r]*$")
HEADING_RE = re.compile(r"^ {0,3}## (.+?)[ \t]*#*[ \t]*$")
UNRESOLVED_PLACEHOLDER_MARKERS = (
    "<fill>",
    "<bundled",
    "<or your own",
    "<hash of",
    "<resolve",
    "<full-tree",
    "<databases",
)


def _present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _assert_no_reparse_components(path: Path) -> None:
    current = Path(path)
    while True:
        try:
            if current.is_symlink() or bool(
                getattr(current.stat(), "st_file_attributes", 0) & 0x0400
            ):
                raise ValueError(f"context path contains a symlink or reparse point: {current}")
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise ValueError(f"cannot inspect context path {current}: {exc}") from exc
        parent = current.parent
        if parent == current:
            return
        current = parent


def _write_new(path: Path, content: bytes) -> None:
    _assert_no_reparse_components(path.parent)
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _level_two_sections(
    text: str,
) -> tuple[dict[str, str], list[str]]:
    """Return fenced-aware level-two sections and duplicate headings."""

    sections: dict[str, str] = {}
    duplicates: list[str] = []
    current: list[str] | None = None
    heading = ""
    fence: tuple[str, int] | None = None
    for line in text.splitlines(keepends=True):
        if fence is not None:
            closing = FENCE_CLOSE_RE.match(line)
            if closing and closing.group(1)[0] == fence[0] and len(closing.group(1)) >= fence[1]:
                fence = None
            if current is not None:
                current.append(line)
            continue
        opening = FENCE_OPEN_RE.match(line)
        if opening:
            fence = (opening.group(1)[0], len(opening.group(1)))
            if current is not None:
                current.append(line)
            continue
        heading_match = HEADING_RE.match(line)
        if heading_match:
            if current is not None:
                sections[heading] = "".join(current)
            heading = heading_match.group(1).strip()
            if heading in sections:
                duplicates.append(heading)
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        sections[heading] = "".join(current)
    return sections, duplicates


def _file_has_exact_bytes(path: Path, expected: bytes) -> bool:
    """Observe the path immediately before an append."""

    _assert_no_reparse_components(path)
    return path.read_bytes() == expected


def _append_merge(path: Path, original: bytes, block: bytes) -> None:
    """Append a reviewed block without replacing or truncating current bytes."""

    if not _file_has_exact_bytes(path, original):
        raise ValueError(f"context file changed since the reviewed plan: {path}")
    open_flags = os.O_RDWR | os.O_APPEND | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        open_flags |= os.O_NOFOLLOW
    descriptor = os.open(path, open_flags)
    try:
        opened_stat = os.fstat(descriptor)
        path_stat = os.stat(path)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"context merge target is not a regular file: {path}")
        if (opened_stat.st_dev, opened_stat.st_ino) != (path_stat.st_dev, path_stat.st_ino):
            raise ValueError(f"context target changed during merge: {path}")
        os.lseek(descriptor, 0, os.SEEK_SET)
        if opened_stat.st_size != len(original) or os.read(descriptor, len(original) + 1) != original:
            raise ValueError(f"context file changed since the reviewed plan: {path}")
        written = 0
        while written < len(block):
            count = os.write(descriptor, block[written:])
            if count <= 0:
                raise OSError("short write while appending context guidance")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    final = path.read_bytes()
    if final != original + block:
        raise ValueError(f"context append could not be verified; no bytes were replaced: {path}")


def _load_merge_plan(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read context merge plan: {exc}") from exc
    if not isinstance(value, dict) or set(value) != MERGE_PLAN_KEYS:
        expected = ", ".join(sorted(MERGE_PLAN_KEYS))
        raise ValueError(f"context merge plan must contain exactly: {expected}")
    if value["schema"] != MERGE_PLAN_SCHEMA or value["reviewed"] is not True:
        raise ValueError("context merge plan must use the reviewed pdh-context-merge/1 schema")
    for key in ("agents_sha256", "template_sha256"):
        if not isinstance(value[key], str) or PIN_RE.fullmatch(value[key]) is None:
            raise ValueError(f"context merge plan {key} must be a lowercase SHA-256")
    additions = value["add_sections"]
    acknowledgements = value["acknowledged_divergences"]
    if not isinstance(additions, list) or not additions or not all(isinstance(item, str) for item in additions):
        raise ValueError("context merge plan add_sections must be a non-empty string list")
    if not isinstance(acknowledgements, list) or not all(isinstance(item, str) for item in acknowledgements):
        raise ValueError("context merge plan acknowledged_divergences must be a string list")
    return value


def _validate_merge_plan(
    plan: dict[str, object],
    *,
    agents_sha256: str,
    template_sha256: str,
    missing: list[str],
    divergences: list[dict[str, object]],
) -> list[str]:
    if plan["agents_sha256"] != agents_sha256:
        raise ValueError("context merge plan agents_sha256 does not match AGENTS.md")
    if plan["template_sha256"] != template_sha256:
        raise ValueError("context merge plan template_sha256 does not match the template")
    selected = list(plan["add_sections"])
    unknown = sorted(set(selected) - set(missing))
    if unknown or len(selected) != len(set(selected)):
        raise ValueError("context merge plan selects unknown or duplicate headings")
    if plan["acknowledged_divergences"] != [
        item["heading"] for item in divergences
    ]:
        raise ValueError(
            "context merge plan acknowledged_divergences must exactly match the report"
        )
    return selected


def inspect_context(root: Path) -> dict[str, object]:
    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    override = root / "AGENTS.override.md"
    return {
        "root": str(root),
        "agents_present": _present(agents),
        "claude_present": _present(claude),
        "agents_override_present": _present(override),
        "missing": [
            name
            for name, path in (("AGENTS.md", agents), ("CLAUDE.md", claude))
            if not _present(path)
        ],
    }


def configure_context(
    root: Path,
    agents_template: Path = DEFAULT_AGENTS_TEMPLATE,
    claude_template: Path = DEFAULT_CLAUDE_TEMPLATE,
    merge_agents: bool = False,
    dry_run: bool = False,
    merge_plan: Path | None = None,
) -> dict[str, object]:
    try:
        resolved_root = root.resolve(strict=True)
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot resolve target root: {exc}") from exc
    if not resolved_root.is_dir():
        raise ValueError(f"target root is not a directory: {resolved_root}")
    resolved_agents_template = agents_template.resolve(strict=True)
    resolved_claude_template = claude_template.resolve(strict=True)
    _assert_no_reparse_components(resolved_root)
    for template in (resolved_agents_template, resolved_claude_template):
        if not template.is_file():
            raise ValueError(f"context template is not a file: {template}")

    agents = resolved_root / "AGENTS.md"
    claude = resolved_root / "CLAUDE.md"
    if merge_plan is not None and not _present(agents):
        raise ValueError("context merge plan requires an existing AGENTS.md")
    created: list[str] = []
    merge_blocked = False
    merge: dict[str, object] = {
        "requested": merge_agents,
        "status": "not_requested",
        "proposed_additions": [],
        "applied_additions": [],
        "parser_errors": [],
        "unresolved_divergences": [],
        "acknowledged_divergences": [],
        "semantic_review_required": False,
    }

    if merge_agents and _present(agents):
        _assert_no_reparse_components(agents)
        try:
            existing_bytes = agents.read_bytes()
            existing_text = existing_bytes.decode("utf-8")
            template_bytes = resolved_agents_template.read_bytes()
            template_text = template_bytes.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"cannot merge AGENTS.md as UTF-8: {exc}") from exc

        existing_sections, existing_duplicates = _level_two_sections(existing_text)
        template_sections, template_duplicates = _level_two_sections(template_text)
        parser_errors = [
            f"duplicate heading {heading!r}" for heading in existing_duplicates
        ] + [f"duplicate template heading {heading!r}" for heading in template_duplicates]
        missing = [
            heading for heading in template_sections if heading not in existing_sections
        ]
        if parser_errors:
            missing = []
        divergent = [
            heading
            for heading, template_section in template_sections.items()
            if heading in existing_sections
            and existing_sections[heading] != template_section
        ]
        merge["agents_sha256"] = _sha256(existing_bytes)
        merge["template_sha256"] = _sha256(template_bytes)
        merge["proposed_additions"] = missing
        merge["parser_errors"] = parser_errors
        divergences = [
            {
                "heading": heading,
                "existing_sha256": _sha256(existing_sections[heading].encode("utf-8")),
                "template_sha256": _sha256(template_sections[heading].encode("utf-8")),
            }
            for heading in divergent
        ]
        if missing and any(
            line.strip() == MERGE_HEADING for line in existing_text.splitlines()
        ):
            divergences.append(
                {
                    "heading": MERGE_HEADING,
                    "existing_sha256": _sha256(existing_bytes),
                    "template_sha256": _sha256(template_text.encode("utf-8")),
                }
            )
        merge["unresolved_divergences"] = divergences
        merge["semantic_review_required"] = bool(
            missing or divergent or parser_errors
        )

        if parser_errors and merge_plan is not None:
            raise ValueError("context merge plan is blocked by ambiguous duplicate headings")

        if merge_plan is not None and not dry_run and not parser_errors:
            plan = _load_merge_plan(merge_plan)
            selected = _validate_merge_plan(
                plan,
                agents_sha256=str(merge["agents_sha256"]),
                template_sha256=str(merge["template_sha256"]),
                missing=missing,
                divergences=divergences,
            )
            merge["acknowledged_divergences"] = list(plan["acknowledged_divergences"])

            shared_heading_exists = any(
                line.strip() == MERGE_HEADING for line in existing_text.splitlines()
            )
            if missing and not shared_heading_exists:
                tail = "" if existing_bytes.endswith(b"\n") else "\n\n"
                block = "\n".join(
                    (
                        MERGE_HEADING,
                        "",
                        MERGE_INTRO,
                        "",
                        *(template_sections[heading] for heading in selected),
                    )
                )
                if not block.endswith("\n"):
                    block += "\n"
                _append_merge(
                    agents,
                    existing_bytes,
                    tail.encode("utf-8") + block.encode("utf-8"),
                )
                merge["applied_additions"] = selected
                merge["status"] = "applied"
            elif missing and shared_heading_exists:
                separator = b""
                if not existing_bytes.endswith(b"\n"):
                    separator = b"\n\n"
                elif not existing_bytes.endswith(b"\n\n"):
                    separator = b"\n"
                continuation = "".join(
                    template_sections[heading] for heading in selected
                )
                if not continuation.endswith("\n"):
                    continuation += "\n"
                _append_merge(
                    agents,
                    existing_bytes,
                    separator + continuation.encode("utf-8"),
                )
                merge["applied_additions"] = selected
                merge["status"] = "applied"
            else:
                merge["status"] = "unchanged"
        elif parser_errors:
            merge["status"] = "blocked"
            merge_blocked = True
        elif missing or divergent:
            merge["status"] = "proposal_required"
        else:
            merge["status"] = "unchanged"

        if merge_plan is not None and dry_run:
            # Validation is deliberately repeated on the same observed bytes so
            # check mode cannot accept a plan that would not be the apply input.
            plan = _load_merge_plan(merge_plan)
            _validate_merge_plan(
                plan,
                agents_sha256=str(merge["agents_sha256"]),
                template_sha256=str(merge["template_sha256"]),
                missing=missing,
                divergences=divergences,
            )
            merge["status"] = "plan_valid"

    if not dry_run and not merge_blocked:
        if not _present(agents):
            _write_new(agents, resolved_agents_template.read_bytes())
            created.append("AGENTS.md")
        if not _present(claude):
            _write_new(claude, resolved_claude_template.read_bytes())
            created.append("CLAUDE.md")

    result = inspect_context(resolved_root)
    result["created"] = created
    result["preserved"] = [
        name for name in ("AGENTS.md", "CLAUDE.md") if name not in created
    ]
    result["agents_merge"] = merge
    return result


def unresolved_placeholders(root: Path, *, stage: str = "all") -> list[str]:
    """Unresolved template markers in a seeded AGENTS.md, with line numbers."""

    agents = root / "AGENTS.md"
    if not _present(agents):
        return []
    findings: list[str] = []
    try:
        text = agents.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"AGENTS.md is not valid UTF-8: {exc}") from exc
    for number, line in enumerate(text.splitlines(), start=1):
        for marker in UNRESOLVED_PLACEHOLDER_MARKERS:
            if marker in line:
                findings.append(f"line {number}: unresolved placeholder {marker!r}")
    rows, binding_findings = parse_binding_contract(text, stage=stage)
    findings.extend(f"skill bindings: {finding}" for finding in binding_findings)
    for slot, cell, pin, number in rows:
        if slot not in STAGE_SLOTS[stage] and cell.strip("`") == pin == "pending":
            continue
        if bound_skill_name(cell) is None or PIN_RE.fullmatch(pin) is None:
            findings.append(
                f"line {number}: unresolved Skill Bindings row for slot {slot!r}"
            )
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Target repository root")
    parser.add_argument("--stage", choices=sorted(STAGE_SLOTS), default="all")
    parser.add_argument(
        "--agents-template",
        type=Path,
        default=DEFAULT_AGENTS_TEMPLATE,
        help="AGENTS.md template for Codex and Pi project governance",
    )
    parser.add_argument(
        "--claude-template",
        type=Path,
        default=DEFAULT_CLAUDE_TEMPLATE,
        help="CLAUDE.md template for the Claude Code project overlay",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "report context state without writing; exit 1 when either root file "
            "is missing, a merge has additions, or same-heading rules diverge"
        ),
    )
    parser.add_argument(
        "--merge-agents",
        action="store_true",
        help=(
            "propose shared AGENTS.md additions; --merge-plan is required to apply"
        ),
    )
    parser.add_argument(
        "--merge-plan",
        type=Path,
        help=(
            "with --merge-agents: reviewed pdh-context-merge/1 plan containing "
            "observed hashes, selected headings and acknowledged divergences"
        ),
    )
    parser.add_argument(
        "--require-resolved",
        action="store_true",
        help=(
            "with --check: also fail while a seeded AGENTS.md still carries "
            "unresolved template placeholders (bindings, deployment record)"
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.merge_plan is not None and not args.merge_agents:
        parser.error("--merge-plan requires --merge-agents")
    try:
        root = args.root.resolve(strict=True)
        result = configure_context(
            root,
            args.agents_template,
            args.claude_template,
            merge_agents=args.merge_agents,
            dry_run=args.check,
            merge_plan=args.merge_plan,
        )
    except (OSError, UnicodeError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    unresolved: list[str] = []
    if args.require_resolved:
        unresolved = unresolved_placeholders(root, stage=args.stage)
        result["unresolved_placeholders"] = unresolved
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.check and (result["missing"] or unresolved):
        return 1
    if not args.check and args.merge_agents and not args.merge_plan:
        merge = result["agents_merge"]
        if merge["status"] not in {"not_requested", "unchanged"}:
            return 1
    if args.check and args.merge_agents and args.merge_plan is None:
        merge = result["agents_merge"]
        if (
            merge["proposed_additions"]
            or merge["unresolved_divergences"]
            or merge["parser_errors"]
        ):
            return 1
    if args.check and args.merge_plan is not None:
        merge = result["agents_merge"]
        if merge["parser_errors"] or merge["status"] != "plan_valid":
            return 1
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
