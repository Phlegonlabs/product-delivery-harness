#!/usr/bin/env python3
"""Check one commit message against the Atomic Commit Convention.

Reads the message from a UTF-8 file (--message-file) or from git (--rev,
via ``git log -1 --format=%B``) and decides mechanically what a machine
can: the ``<type>(<scope>): <summary>`` subject shape, the type and scope
vocabulary, subject length and punctuation, the blank second line, the
``BREAKING CHANGE:`` paragraph behind a ``!`` subject and, with
--managed, the Task/Trace/Verified or integration trailer set. Subjects
starting with ``Merge `` pass without further checks. Exit 0 prints
``OK: <subject>``; exit 1 prints one ``ERROR: <what>. <fix>.`` line per
problem; exit 2 reports bad arguments, an unreadable message file or a
git failure. This script only checks text; it grants no commit
authorization.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ALLOWED_TYPES = ("feat", "fix", "refactor", "test", "docs", "chore", "perf", "build", "ci")
ALLOWED_TYPES_TEXT = ", ".join(ALLOWED_TYPES)
SCOPE_PATTERN = "[a-z0-9][a-z0-9-]*"
SCOPE_AREAS = "auth, billing, api, db, dashboard, ui, harness or prd"
SHAPE_EXAMPLE = '"feat(harness): add commit message check"'
SUBJECT_PREFIX = re.compile(r"^(?P<type>[^(]*?)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?$")
TRAILER_LINE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9-]*): ?(?P<value>.*)$")
INTEGRATION_PREFIX = "chore(integration):"
MAX_SUBJECT_LENGTH = 72


def check_subject(subject: str) -> tuple[list[str], bool]:
    """Return every subject problem and whether it marks a breaking change."""

    problems: list[str] = []
    breaking = False
    head, colon, rest = subject.partition(":")
    summary = rest[1:] if rest.startswith(" ") else rest
    if not colon:
        problems.append(
            'ERROR: the subject is not in the "<type>(<scope>): <summary>" shape with an '
            'optional "!" directly before the colon. Rewrite the first line as, for example, '
            f"{SHAPE_EXAMPLE}."
        )
        summary = subject
    else:
        match = SUBJECT_PREFIX.match(head)
        if match is None:
            problems.append(
                f'ERROR: the subject prefix "{head}" does not match "<type>(<scope>)" with an '
                'optional "!" directly before the colon. Rewrite the first line as, for '
                f"example, {SHAPE_EXAMPLE}."
            )
        else:
            breaking = match.group("breaking") is not None
            type_name = match.group("type")
            scope = match.group("scope")
            if type_name not in ALLOWED_TYPES:
                problems.append(
                    f'ERROR: type "{type_name}" is not allowed. '
                    f"Use one of: {ALLOWED_TYPES_TEXT}."
                )
            if scope is None:
                problems.append(
                    "ERROR: the subject has no scope. Add a product or engineering area in "
                    f"parentheses, as in {SHAPE_EXAMPLE}."
                )
            elif re.fullmatch(SCOPE_PATTERN, scope) is None:
                if "." in scope or "/" in scope:
                    problems.append(
                        f'ERROR: scope "{scope}" contains "." or "/". A scope is a product or '
                        f"engineering area, not a filename; use an area such as {SCOPE_AREAS}."
                    )
                else:
                    problems.append(
                        f'ERROR: scope "{scope}" does not match {SCOPE_PATTERN}. Use a '
                        f"lowercase product or engineering area such as {SCOPE_AREAS}."
                    )
    if len(subject) > MAX_SUBJECT_LENGTH:
        problems.append(
            f"ERROR: the subject is {len(subject)} characters long; the maximum is "
            f"{MAX_SUBJECT_LENGTH}. Shorten the first line so the whole subject is "
            f"{MAX_SUBJECT_LENGTH} characters or fewer."
        )
    if subject.endswith("."):
        problems.append(
            "ERROR: the subject ends with a period. Remove the final period from the summary."
        )
    if not summary.strip():
        problems.append(
            "ERROR: the summary is empty. Write an imperative summary after the colon, as in "
            f"{SHAPE_EXAMPLE}."
        )
    return problems, breaking


def check_body(lines: list[str], breaking: bool) -> list[str]:
    problems: list[str] = []
    if len(lines) > 1 and lines[1].strip():
        problems.append(
            "ERROR: the second line of the message is not blank. Separate the subject from "
            "the body with one blank line."
        )
    if breaking and not any(line.startswith("BREAKING CHANGE:") for line in lines[1:]):
        problems.append(
            'ERROR: the subject marks a breaking change with "!" but no body paragraph starts '
            'with "BREAKING CHANGE:". Add a body paragraph starting with "BREAKING CHANGE: " '
            "that describes what breaks and how to migrate."
        )
    return problems


def collect_trailers(lines: list[str]) -> dict[str, list[str]]:
    trailers: dict[str, list[str]] = {}
    for line in lines[1:]:
        match = TRAILER_LINE.match(line)
        if match is not None:
            trailers.setdefault(match.group("key").lower(), []).append(match.group("value"))
    return trailers


def _trailer_problems(trailers: dict[str, list[str]], name: str, example: str) -> list[str]:
    values = trailers.get(name.lower(), [])
    if not values:
        return [f'ERROR: the {name} trailer is missing. Add "{example}" on its own line.']
    if any(not value.strip() for value in values):
        return [
            f"ERROR: the {name} trailer is empty. Give it a value on its own line, as in "
            f'"{example}".'
        ]
    return []


def check_managed_trailers(subject: str, trailers: dict[str, list[str]]) -> list[str]:
    problems: list[str] = []
    if subject.startswith(INTEGRATION_PREFIX):
        required = (
            ("Mission", "Mission: M2"),
            ("Plan-Revision", "Plan-Revision: 3"),
            ("Integrated-Head", "Integrated-Head: 8f14e45fceea167a5a36dedd4bea2543657059"),
            ("Verified", "Verified: pnpm test --filter auth (exit 0)"),
        )
    else:
        required = (
            ("Task", "Task: M2/T03"),
            ("Trace", "Trace: PRD-012, ARCH-004"),
            ("Verified", "Verified: pnpm test --filter auth (exit 0)"),
        )
    for name, example in required:
        problems.extend(_trailer_problems(trailers, name, example))
    task_values = trailers.get("task", [])
    if len(task_values) > 1:
        problems.append(
            "ERROR: the message carries more than one Task trailer. Split the work into "
            "separate tasks so each commit holds exactly one task ID."
        )
    elif any("," in value for value in task_values):
        problems.append(
            f'ERROR: the Task trailer "{task_values[0]}" holds more than one task ID. Split '
            'the task so each commit holds exactly one task ID, as in "Task: M2/T03".'
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--message-file",
        type=Path,
        help="read the commit message as UTF-8 from this file",
    )
    parser.add_argument(
        "--rev",
        help="read the message of this revision with git log -1 --format=%%B",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="repository root for --rev (default: current directory)",
    )
    parser.add_argument(
        "--managed",
        action="store_true",
        help="also require the managed-run trailer set",
    )
    args = parser.parse_args(argv)
    if (args.message_file is None) == (args.rev is None):
        parser.error("provide exactly one of --message-file or --rev")

    if args.message_file is not None:
        try:
            message = args.message_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"error: cannot read {args.message_file}: {exc}", file=sys.stderr)
            return 2
    else:
        try:
            completed = subprocess.run(
                [
                    "git", "-C", str(args.repo_root), "log", "-1", "--format=%B",
                    "--end-of-options", args.rev,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"error: git log failed for {args.rev}: {exc}", file=sys.stderr)
            return 2
        if completed.returncode != 0:
            detail = (completed.stderr or "").strip() or f"exit status {completed.returncode}"
            print(f"error: git log failed for {args.rev}: {detail}", file=sys.stderr)
            return 2
        message = completed.stdout

    lines = message.replace("\r\n", "\n").split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    subject = lines[0] if lines else ""

    if subject.startswith("Merge "):
        print(f"OK (merge commit): {subject}")
        return 0

    problems, breaking = check_subject(subject)
    problems.extend(check_body(lines, breaking))
    if args.managed:
        problems.extend(check_managed_trailers(subject, collect_trailers(lines)))
    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {subject}")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
