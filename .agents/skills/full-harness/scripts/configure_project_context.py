#!/usr/bin/env python3
"""Safely add host-specific project context files without overwriting local rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "assets" / "templates"
DEFAULT_AGENTS_TEMPLATE = TEMPLATES_DIR / "PROJECT_AGENTS.template.md"
DEFAULT_CLAUDE_TEMPLATE = TEMPLATES_DIR / "PROJECT_CLAUDE.template.md"
UNRESOLVED_PLACEHOLDER_MARKERS = ("<fill>", "<bundled", "<or your own", "<hash of")


def _present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _write_new(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)


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
) -> dict[str, object]:
    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise ValueError(f"target root is not a directory: {resolved_root}")
    resolved_agents_template = agents_template.resolve(strict=True)
    resolved_claude_template = claude_template.resolve(strict=True)
    for template in (resolved_agents_template, resolved_claude_template):
        if not template.is_file():
            raise ValueError(f"context template is not a file: {template}")

    agents = resolved_root / "AGENTS.md"
    claude = resolved_root / "CLAUDE.md"
    created: list[str] = []

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
    return result


def unresolved_placeholders(root: Path) -> list[str]:
    """Unresolved template markers in a seeded AGENTS.md, with line numbers."""

    agents = root / "AGENTS.md"
    if not _present(agents):
        return []
    findings: list[str] = []
    for number, line in enumerate(
        agents.read_text(encoding="utf-8").splitlines(), start=1
    ):
        for marker in UNRESOLVED_PLACEHOLDER_MARKERS:
            if marker in line:
                findings.append(f"line {number}: unresolved placeholder {marker!r}")
    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Target repository root")
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
        help="Report context state without writing; exit 1 when either root file is missing",
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
    args = build_parser().parse_args()
    try:
        root = args.root.resolve(strict=True)
        result = (
            inspect_context(root)
            if args.check
            else configure_context(root, args.agents_template, args.claude_template)
        )
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    unresolved: list[str] = []
    if args.require_resolved:
        unresolved = unresolved_placeholders(root)
        result["unresolved_placeholders"] = unresolved
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.check and (result["missing"] or unresolved):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
