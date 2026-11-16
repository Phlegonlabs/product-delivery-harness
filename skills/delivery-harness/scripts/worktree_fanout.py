#!/usr/bin/env python3
"""Read-only fan-out checks: part scope disjointness and worker merge readiness.

``scopes`` compares planned write scopes pairwise before a fan-out launches.
Both subcommands are reports: they never merge, commit, check out, fetch,
push, or write a file in the repository.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from typing import Any

from harness_core import (
    canonical_json,
    scope_overlap,
    validate_scope_claim,
)


class GitCommandError(RuntimeError):
    """Raised when a read-only Git inspection fails outside its normal codes."""


class UnresolvedRefError(RuntimeError):
    """Raised when a caller-supplied ref does not name a commit."""


def parse_part_value(value: str) -> tuple[str, list[str]]:
    """Split one ``--part <id>=<claim>[,<claim>...]`` value."""

    part_id, separator, claims_text = value.partition("=")
    if not separator or not part_id.strip() or not claims_text:
        raise ValueError(f"--part must be <id>=<claim>[,<claim>...], got {value!r}")
    return part_id, claims_text.split(",")


def build_scopes_report(parts: list[tuple[str, list[str]]]) -> dict[str, Any]:
    """Compare every pair of parts and report conflicts, invalid claims, disjointness."""

    invalid: list[dict[str, str]] = []
    for part_id, claims in parts:
        for claim in claims:
            error = validate_scope_claim(claim)
            if error:
                invalid.append({"part": part_id, "claim": claim, "error": error})
    invalid.sort(key=lambda item: (item["part"], item["claim"]))

    conflicts: set[tuple[str, str, str, str, str]] = set()
    ordered = sorted(parts, key=lambda item: item[0])
    for (left_id, left_claims), (right_id, right_claims) in itertools.combinations(ordered, 2):
        for left_claim in left_claims:
            for right_claim in right_claims:
                if scope_overlap(left_claim, right_claim):
                    reason = "scope_overlap"
                elif scope_overlap(left_claim, right_claim, casefold=True):
                    reason = "case_scope_collision"
                else:
                    continue
                conflicts.add((left_id, right_id, reason, left_claim, right_claim))
    conflict_items = [
        {"left": left, "right": right, "reason": reason, "claims": [left_claim, right_claim]}
        for left, right, reason, left_claim, right_claim in sorted(conflicts)
    ]
    return {
        "conflicts": conflict_items,
        "disjoint": not conflict_items and not invalid,
        "invalid": invalid,
        "parts": sorted(part_id for part_id, _ in parts),
    }


def _run_scopes(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    parts: list[tuple[str, list[str]]] = []
    for raw in args.part:
        try:
            parts.append(parse_part_value(raw))
        except ValueError as exc:
            parser.error(str(exc))
    if len(parts) < 2:
        parser.error("at least two --part values are required")
    part_ids = [part_id for part_id, _ in parts]
    if len(set(part_ids)) != len(part_ids):
        parser.error("part IDs must be unique")
    report = build_scopes_report(parts)
    sys.stdout.write(canonical_json(report))
    return 0 if report["disjoint"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    scopes_parser = subparsers.add_parser(
        "scopes", help="compare part write scopes pairwise for overlap"
    )
    scopes_parser.add_argument(
        "--part",
        action="append",
        required=True,
        metavar="<id>=<claim>[,<claim>...]",
        help="one fan-out part with one or more scope claims",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    """Run one subcommand and return the process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "scopes":
        return _run_scopes(parser, args)
    raise AssertionError(f"unhandled subcommand {args.command!r}")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(run())
