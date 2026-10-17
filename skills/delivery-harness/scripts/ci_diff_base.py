#!/usr/bin/env python3
"""Resolve a meaningful source-CI whitespace diff base without silent self-diffs."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
ZERO_SHA = re.compile(r"^0{40}$")


class DiffBaseError(Exception):
    """The requested event has no safe candidate-to-base diff."""


def run_git(*arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiffBaseError(f"git {' '.join(arguments)} failed: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise DiffBaseError(f"git {' '.join(arguments)} failed: {detail or result.returncode}")
    return result.stdout.decode("utf-8").strip()


def resolve_commit(value: str, label: str) -> str:
    if not FULL_SHA.fullmatch(value):
        raise DiffBaseError(f"{label} must be a full lowercase commit SHA")
    resolved = run_git("rev-parse", "--verify", f"{value}^{{commit}}")
    if resolved != value:
        raise DiffBaseError(f"{label} resolved to {resolved}, not its exact bytes")
    return resolved


def require_ancestor(base: str, candidate: str) -> None:
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, candidate],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiffBaseError(f"ancestor check failed: {exc}") from exc
    if result.returncode == 1:
        raise DiffBaseError(f"base {base} is not an ancestor of candidate {candidate}")
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise DiffBaseError(f"ancestor check failed: {detail or result.returncode}")


def empty_tree() -> str:
    result = run_git("mktree")
    if not FULL_SHA.fullmatch(result):
        raise DiffBaseError(f"Git returned an unexpected empty-tree value: {result}")
    return result


def resolve(event: str, candidate: str, base: str | None) -> str:
    if run_git("rev-parse", "--show-object-format") != "sha1":
        raise DiffBaseError("this CI helper requires a SHA-1 repository")
    resolve_commit(candidate, "candidate")

    if event == "workflow_dispatch":
        if not base:
            raise DiffBaseError("manual release requires base_sha")
        resolved_base = resolve_commit(base, "base")
        if resolved_base == candidate:
            raise DiffBaseError("manual base_sha must differ from candidate_sha")
        require_ancestor(resolved_base, candidate)
        return resolved_base

    if event in {"pull_request", "merge_group"}:
        if not base:
            raise DiffBaseError(f"{event} did not provide a base SHA")
        resolved_base = resolve_commit(base, "base")
        if resolved_base == candidate:
            raise DiffBaseError(f"{event} base equals the candidate")
        merge_base = run_git("merge-base", resolved_base, candidate)
        if not FULL_SHA.fullmatch(merge_base):
            raise DiffBaseError(f"{event} merge base is not a full commit SHA")
        return merge_base

    if event == "push":
        if not base or ZERO_SHA.fullmatch(base):
            return empty_tree()
        resolved_base = resolve_commit(base, "push base")
        if resolved_base == candidate:
            raise DiffBaseError("push base equals the candidate")
        require_ancestor(resolved_base, candidate)
        return resolved_base

    raise DiffBaseError(f"unsupported event: {event}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    resolve_parser = commands.add_parser("resolve", help="print the safe diff base")
    resolve_parser.add_argument("--event", required=True)
    resolve_parser.add_argument("--candidate", required=True)
    resolve_parser.add_argument("--base")
    arguments = parser.parse_args()
    try:
        print(resolve(arguments.event, arguments.candidate, arguments.base))
    except DiffBaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
