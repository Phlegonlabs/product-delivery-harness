#!/usr/bin/env python3
"""Safely add host-specific project context files without overwriting local rules.

A missing `.gitattributes` is seeded from PROJECT_GITATTRIBUTES.template.
`--check` also reports, read-only, whether Git stores docs/product, docs/design,
docs/verification and docs/goal byte for byte, with the `.gitattributes` lines
to add; `--require-resolved` makes a finding fail. It also lists the template
lines an existing `.gitattributes` lacks.

`--check --merge-agents` prints a unified diff for each AGENTS.md section that
differs from the template beyond trailing blank lines, line endings, the
Skill Bindings skill and pin cells and the Harness Version bullet values.
`--check --documents` compares docs/DOCUMENTS.md with the manifest template.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

from check_skill_bindings import PIN_RE, STAGE_SLOTS, bound_skill_name, parse_binding_contract


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "assets" / "templates"
DEFAULT_AGENTS_TEMPLATE = TEMPLATES_DIR / "PROJECT_AGENTS.template.md"
DEFAULT_CLAUDE_TEMPLATE = TEMPLATES_DIR / "PROJECT_CLAUDE.template.md"
DOCUMENTS_TEMPLATE = TEMPLATES_DIR / "DOCUMENTS.template.md"
DOCUMENTS_PATH = "docs/DOCUMENTS.md"
GITATTRIBUTES_TEMPLATE = TEMPLATES_DIR / "PROJECT_GITATTRIBUTES.template"
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
BULLET_LABEL_RE = re.compile(r"^(\s*[-*] [^:]+):.*$")
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


def _comparable_section(heading: str, section: str) -> str:
    """Section text as compared: LF endings and no trailing blank lines.

    Skill Bindings rows drop their skill and pin cells, which
    check_skill_bindings.py owns. Harness Version bullets keep only their
    labels: each consumer records its own installed version there.
    """

    text = section.replace("\r\n", "\n").rstrip() + "\n"
    if heading == "Harness Version":
        return "\n".join(BULLET_LABEL_RE.sub(r"\1: <value>", line) for line in text.split("\n"))
    if heading != "Skill Bindings":
        return text
    lines = []
    table_line = 0
    for line in text.split("\n"):
        if line.strip().startswith("|"):
            table_line += 1
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if table_line > 2 and len(cells) == 4:
                line = f"| {cells[0]} | {cells[1]} | <skill> | <pin> |"
        lines.append(line)
    return "\n".join(lines)


def _section_diff(heading: str, existing: str, template: str) -> list[str]:
    return list(difflib.unified_diff(
        existing.splitlines(), template.splitlines(),
        f"AGENTS.md ## {heading}", f"template ## {heading}", n=1, lineterm="",
    ))


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
        compared = {
            heading: (
                _comparable_section(heading, existing_sections[heading]),
                _comparable_section(heading, template_section),
            )
            for heading, template_section in template_sections.items()
            if heading in existing_sections
        }
        divergent = [heading for heading, (mine, theirs) in compared.items() if mine != theirs]
        merge["agents_sha256"] = _sha256(existing_bytes)
        merge["template_sha256"] = _sha256(template_bytes)
        merge["proposed_additions"] = missing
        merge["parser_errors"] = parser_errors
        divergences = [
            {"heading": heading, "diff": _section_diff(heading, *compared[heading])}
            for heading in divergent
        ]
        if missing and any(
            line.strip() == MERGE_HEADING for line in existing_text.splitlines()
        ):
            # The missing sections would join the existing shared block.
            divergences.append(
                {"heading": MERGE_HEADING, "diff": [f"+## {heading}" for heading in missing]}
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

    gitattributes_created = False
    if not dry_run and not merge_blocked:
        if not _present(agents):
            _write_new(agents, resolved_agents_template.read_bytes())
            created.append("AGENTS.md")
        if not _present(claude):
            _write_new(claude, resolved_claude_template.read_bytes())
            created.append("CLAUDE.md")
        gitattributes = resolved_root / ".gitattributes"
        if not _present(gitattributes):
            _write_new(gitattributes, GITATTRIBUTES_TEMPLATE.read_bytes())
            gitattributes_created = True

    result = inspect_context(resolved_root)
    result["created"] = created
    result["preserved"] = [
        name for name in ("AGENTS.md", "CLAUDE.md") if name not in created
    ]
    result["gitattributes_created"] = gitattributes_created
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


BACKTICKED = re.compile(r"`([^`]+)`")
SEPARATOR_CELL = re.compile(r":?-{3,}:?")


def _manifest_rows(text: str) -> list[tuple[int, set[str], set[str]]]:
    """(line, document paths, all paths) for each table body row of a manifest."""

    lines = text.splitlines()
    rows = []
    for index, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if (
            not line.lstrip().startswith("|")
            or len(cells) < 2
            or all(SEPARATOR_CELL.fullmatch(cell) for cell in cells)
            or all(SEPARATOR_CELL.fullmatch(cell.strip()) for cell in following.strip().strip("|").split("|"))
        ):
            continue
        locations = BACKTICKED.findall(cells[1])
        base = locations[0].rstrip("/") if locations else ""
        documents = {
            token if "/" in token or not base else f"{base}/{token}"
            for token in BACKTICKED.findall(cells[0])
        }
        paths = documents | set(locations)
        rows.append((index + 1, documents, {path.removeprefix("./").rstrip("/") for path in paths}))
    return rows


def documents_findings(root: Path) -> dict[str, object]:
    """Read-only comparison of docs/DOCUMENTS.md with the manifest template."""

    template = DOCUMENTS_TEMPLATE.read_text(encoding="utf-8")
    manifest = root / DOCUMENTS_PATH
    report: dict[str, object] = {
        "path": DOCUMENTS_PATH, "present": manifest.is_file(), "missing_rows": [],
        "single_record_rows": [], "intro_paragraph_missing": False,
    }
    if not report["present"]:
        return report
    try:
        text = manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read {DOCUMENTS_PATH} as UTF-8: {exc}") from exc
    wanted = sorted({path for _, documents, _ in _manifest_rows(template) for path in documents})
    # A template row naming a directory stands for generated records.
    directories = [path.rstrip("/") for path in wanted if path.endswith("/")]
    rows = _manifest_rows(text)
    present = set().union(*(paths for _, _, paths in rows))
    report["missing_rows"] = [path for path in wanted if path.rstrip("/") not in present]
    report["single_record_rows"] = [
        {"line": line, "path": path, "directory": directory + "/"}
        for line, _, paths in rows
        for path in sorted(paths)
        for directory in directories
        if path.startswith(directory + "/")
    ]
    intro = next(
        part for part in template.split("\n\n") if part.strip() and not part.lstrip().startswith(("#", "|"))
    )
    report["intro_paragraph_missing"] = " ".join(intro.split()) not in " ".join(text.split())
    return report


# Product, design, verification and run files are hashed long before the
# acceptance gate, so Git must store them byte for byte.
BYTE_EXACT_ROOTS = ("docs/product", "docs/design", "docs/verification", "docs/goal")
BYTE_ATTRIBUTES = ("text", "filter", "ident", "working-tree-encoding")
ATTRIBUTE_PROBE = "pdh-attribute-probe"
FINDINGS_PER_ROOT = 20


def gitattributes_findings(root: Path) -> dict[str, object]:
    """Template lines an existing `.gitattributes` lacks; read-only."""

    path = root / ".gitattributes"
    report: dict[str, object] = {"present": _present(path), "missing_template_lines": []}
    if not report["present"]:
        return report
    try:
        existing = {" ".join(line.split()) for line in path.read_text(encoding="utf-8").splitlines()}
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read .gitattributes as UTF-8: {exc}") from exc
    report["missing_template_lines"] = [
        " ".join(line.split())
        for line in GITATTRIBUTES_TEMPLATE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        and " ".join(line.split()) not in existing
    ]
    return report


def _git(root: Path, *arguments: str, stdin: bytes | None = None) -> bytes | None:
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(root), *arguments],
            input=stdin, capture_output=True, timeout=120, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout if completed.returncode == 0 else None


def _attribute_problems(found: dict[str, str]) -> list[str]:
    problems = [] if found.get("text") == "unset" else ["text"]
    problems += [
        name for name in ("filter", "ident")
        if found.get(name) not in {"unset", "unspecified"}
    ]
    if found.get("working-tree-encoding") != "unspecified":
        problems.append("working-tree-encoding")
    return problems


def byte_attribute_findings(root: Path) -> dict[str, object]:
    """Read-only `git check-attr` of the hashed docs roots; writes nothing."""

    warnings: list[str] = []
    report: dict[str, object] = {
        "checked": False, "findings": [], "gitattributes_lines": [], "warnings": warnings,
    }
    toplevel = _git(root, "rev-parse", "--show-toplevel")
    if toplevel is None or Path(toplevel.decode("utf-8").strip()).resolve() != root.resolve():
        warnings.append("not the root of a Git checkout; attributes were not checked")
        return report
    listed = _git(root, "ls-files", "-z", "--", *BYTE_EXACT_ROOTS)
    # One probe per root stands for files that do not exist yet.
    probes = {f"{name}/{ATTRIBUTE_PROBE}": name for name in BYTE_EXACT_ROOTS}
    paths = [item for item in (listed or b"").decode("utf-8", "surrogateescape").split("\0") if item]
    query = "".join(f"{path}\0" for path in [*paths, *probes]).encode("utf-8", "surrogateescape")
    output = None if listed is None else _git(
        root, "check-attr", "-z", "--stdin", *BYTE_ATTRIBUTES, stdin=query
    )
    if output is None:
        warnings.append("git ls-files or git check-attr failed; attributes were not checked")
        return report
    report["checked"] = True
    fields = output.decode("utf-8", "surrogateescape").split("\0")
    values: dict[str, dict[str, str]] = {}
    for index in range(0, len(fields) - 2, 3):
        path, attribute, value = fields[index : index + 3]
        values.setdefault(path, {})[attribute] = value
    failed: dict[str, list[str]] = {name: [] for name in BYTE_EXACT_ROOTS}
    unsafe: dict[str, set[str]] = {name: set() for name in BYTE_EXACT_ROOTS}
    for path, found in values.items():
        problems = _attribute_problems(found)
        name = probes.get(path) or next(
            (item for item in BYTE_EXACT_ROOTS if path.startswith(item + "/")), None
        )
        if not problems or name is None:
            continue
        unsafe[name].update(problems)
        label = f"new files under {name}/" if path in probes else path
        if len(failed[name]) < FINDINGS_PER_ROOT:
            failed[name].append(label + ": " + ", ".join(f"{item} {found.get(item)}" for item in problems))
        elif len(failed[name]) == FINDINGS_PER_ROOT:
            failed[name].append(f"more paths under {name}/ fail the same check")
    flags = (("text", "-text"), ("filter", "-filter"), ("ident", "-ident"),
             ("working-tree-encoding", "!working-tree-encoding"))
    for name in BYTE_EXACT_ROOTS:
        if failed[name]:
            report["findings"].extend(failed[name])
            # -text always: a later broad rule must not turn conversion back on.
            needed = [flag for item, flag in flags if item == "text" or item in unsafe[name]]
            report["gitattributes_lines"].append(f"{name}/** {' '.join(needed)}")
    common = _git(root, "rev-parse", "--git-common-dir")
    if common is not None:
        info = root / common.decode("utf-8").strip() / "info" / "attributes"
        try:
            text = info.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        if any(line.strip() and not line.lstrip().startswith("#") for line in text.splitlines()):
            warnings.append(
                f"{info.as_posix()} holds attribute rules that clones and CI do not get; "
                "keep byte-exact rules in .gitattributes"
            )
    return report


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
        "--documents",
        action="store_true",
        help=(
            "with --check: also compare docs/DOCUMENTS.md with the manifest template; "
            "exit 1 on a missing template row, a row for one record inside a "
            "generated-records directory, or a missing intro paragraph"
        ),
    )
    parser.add_argument(
        "--require-resolved",
        action="store_true",
        help=(
            "with --check: also fail while a seeded AGENTS.md still carries "
            "unresolved template placeholders (bindings, deployment record) "
            "or a hashed docs path lacks byte-exact Git attributes"
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.merge_plan is not None and not args.merge_agents:
        parser.error("--merge-plan requires --merge-agents")
    if args.documents and not args.check:
        parser.error("--documents requires --check")
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
    unsafe_attributes = False
    if args.check:
        result["byte_attributes"] = byte_attribute_findings(root)
        unsafe_attributes = args.require_resolved and bool(result["byte_attributes"]["findings"])
        try:
            result["gitattributes"] = gitattributes_findings(root)
        except ValueError as error:
            print(json.dumps({"error": str(error)}, ensure_ascii=False))
            return 2
    documents_drift = False
    if args.documents:
        try:
            documents = documents_findings(root)
        except ValueError as error:
            print(json.dumps({"error": str(error)}, ensure_ascii=False))
            return 2
        result["documents"] = documents
        documents_drift = not documents["present"] or bool(
            documents["missing_rows"] or documents["single_record_rows"]
            or documents["intro_paragraph_missing"]
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.check and (result["missing"] or unresolved or unsafe_attributes or documents_drift):
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
