#!/usr/bin/env python3
"""Read-only fan-out checks: part scope disjointness and worker merge readiness.

``scopes`` compares planned write scopes pairwise before a fan-out launches.
``merge-check`` decides whether one writer's branch can merge back now and
names exact reason codes when it cannot. Both subcommands are reports: they
never merge, commit, check out, fetch, push, or write a file in the
repository. The trial merge writes its objects to a temporary directory, and
status reads take no index lock.
"""

from __future__ import annotations

import argparse
import itertools
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from harness_core import (
    canonical_json,
    parent_owned_path,
    path_in_scopes,
    scope_contains,
    scope_overlap,
    validate_scope_claim,
)
from harness_git import GitMetadataError, git_argv, git_environment, run_git


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


def _resolve_commit(root: Path, ref: str) -> str:
    result = run_git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if result.returncode == 0:
        return result.stdout.strip()
    if result.returncode == 1:
        raise UnresolvedRefError(ref)
    raise GitCommandError(f"cannot resolve {ref!r} in {root}: {result.stderr.strip()}")


def _is_ancestor(root: Path, left: str, right: str) -> bool:
    result = run_git(root, "merge-base", "--is-ancestor", left, right)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise GitCommandError(f"cannot compare {left} and {right}: {result.stderr.strip()}")


def _commit_count(root: Path, base: str, head: str) -> int:
    result = run_git(root, "rev-list", "--count", f"{base}..{head}")
    if result.returncode != 0:
        raise GitCommandError(f"cannot count commits in {base}..{head}: {result.stderr.strip()}")
    return int(result.stdout.strip())


def _changed_paths(root: Path, base: str, head: str) -> list[str]:
    result = run_git(root, "diff", "--name-only", "-z", "--no-renames", f"{base}..{head}")
    if result.returncode != 0:
        raise GitCommandError(f"cannot list changed paths: {result.stderr.strip()}")
    paths = result.stdout.split("\0")
    if paths and paths[-1] == "":
        paths.pop()
    return sorted(set(paths))


def _touched_paths(root: Path, base: str, head: str) -> list[str]:
    """Every path any commit in base..head touched.

    The endpoint diff misses a file a worker changed in one commit and put back
    in a later one, yet the merge still brings in both commits.
    """

    result = run_git(
        root, "log", "--format=", "--name-only", "-z", "--no-renames",
        "--diff-merges=first-parent", f"{base}..{head}",
    )
    if result.returncode != 0:
        raise GitCommandError(f"cannot list touched paths: {result.stderr.strip()}")
    return sorted({item.strip() for item in result.stdout.split("\0") if item.strip()})


def _whitespace_problems(root: Path, base: str, head: str) -> list[str]:
    result = run_git(root, "diff", "--check", f"{base}..{head}")
    if result.returncode == 0 and not result.stdout.strip():
        return []
    if result.returncode in (1, 2):
        return sorted(set(result.stdout.splitlines()))
    raise GitCommandError(f"cannot check diff whitespace: {result.stderr.strip()}")


def _porcelain_status(root: Path, *, tracked_only: bool = False) -> list[str]:
    arguments = ["status", "--porcelain"]
    if tracked_only:
        arguments.append("--untracked-files=no")
    # Without this, status may rewrite the index to refresh its stat cache.
    result = run_git(root, *arguments, environment={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    if result.returncode != 0:
        raise GitCommandError(f"cannot read status in {root}: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def _head_commit(root: Path) -> str:
    result = run_git(root, "rev-parse", "HEAD")
    if result.returncode != 0:
        raise GitCommandError(f"cannot read HEAD in {root}: {result.stderr.strip()}")
    return result.stdout.strip()


def _objects_directory(root: Path) -> str:
    result = run_git(root, "rev-parse", "--path-format=absolute", "--git-path", "objects")
    if result.returncode != 0:
        raise GitCommandError(f"cannot locate the object directory: {result.stderr.strip()}")
    return result.stdout.strip()


def _merge_tree(root: Path, into: str, head: str) -> subprocess.CompletedProcess[str]:
    """Trial-merge without touching the repository.

    ``merge-tree --write-tree`` writes the merged trees and blobs. Point Git at
    a throwaway object directory, with the real one as a read-only alternate,
    so nothing lands in the repository's object database.
    """

    with tempfile.TemporaryDirectory(prefix="fanout-merge-") as scratch:
        environment = git_environment()
        environment["GIT_OBJECT_DIRECTORY"] = scratch
        environment["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = _objects_directory(root)
        return subprocess.run(
            git_argv("merge-tree", "--write-tree", into, head),
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            timeout=120,
            env=environment,
        )


def _untracked_collisions(root: Path, paths: list[str]) -> list[str]:
    """Changed paths that exist in the checkout as untracked or ignored files.

    A merge would refuse to overwrite an untracked file and, by default,
    silently replaces an ignored one. A file sitting where an incoming path
    needs a directory blocks the merge the same way, so each parent that is
    not a directory on disk is checked too.
    """

    candidates = set(paths)
    for path in paths:
        parts = path.split("/")
        for depth in range(1, len(parts)):
            parent = "/".join(parts[:depth])
            location = root / parent
            if os.path.lexists(location) and not (location.is_dir() and not location.is_symlink()):
                candidates.add(parent)
    ordered = sorted(candidates)
    found: set[str] = set()
    for start in range(0, len(ordered), 200):
        chunk = [f":(literal){path}" for path in ordered[start : start + 200]]
        result = run_git(root, "ls-files", "--others", "-z", "--", *chunk)
        if result.returncode != 0:
            raise GitCommandError(f"cannot list untracked files: {result.stderr.strip()}")
        found.update(item for item in result.stdout.split("\0") if item)
    return sorted(found)


_MERGE_TREE_UNAVAILABLE_MESSAGE = (
    "git merge-tree --write-tree is unavailable; this check needs Git 2.38 or newer"
)


def _conflicted_paths(stdout: str) -> list[str]:
    paths = []
    for line in stdout.splitlines():
        if not line.strip():
            break
        if "\t" in line:
            paths.append(line.split("\t", 1)[1])
    return sorted(set(paths))


def _merge_tree_verdict(root: Path, into: str, head: str) -> tuple[str, list[str]]:
    """Classify one trial merge as clean, conflict, refused, or unavailable."""

    result = _merge_tree(root, into, head)
    if result.returncode == 0:
        return "clean", []
    stderr_lines = [line for line in result.stderr.splitlines() if line.strip()]
    lowered = result.stderr.casefold()
    if result.returncode != 1 and ("unknown" in lowered or "usage" in lowered):
        return "unavailable", [_MERGE_TREE_UNAVAILABLE_MESSAGE]
    paths = _conflicted_paths(result.stdout)
    if paths:
        return "conflict", paths
    message = stderr_lines[0] if stderr_lines else "the trial merge was refused"
    return "refused", [message]


def build_merge_report(
    *,
    repo_root: Path,
    base: str,
    head: str,
    into: str,
    scopes: list[str],
    denies: list[str],
    worktree: Path | None,
) -> dict[str, Any]:
    """Run every merge-readiness check and collect all failing reason codes."""

    reasons: set[str] = set()
    details: dict[str, list[str]] = {}

    def note(reason: str, entries: list[str] | None = None) -> None:
        reasons.add(reason)
        if entries:
            details.setdefault(reason, []).extend(entries)

    claim_problems = {
        claim: validate_scope_claim(claim) for claim in dict.fromkeys([*scopes, *denies])
    }
    invalid_claims = [
        f"{claim}: {problem}" for claim, problem in claim_problems.items() if problem
    ]
    if invalid_claims:
        note("invalid_scope", invalid_claims)
    valid_scopes = [claim for claim in scopes if claim_problems.get(claim) is None]
    valid_denies = [claim for claim in denies if claim_problems.get(claim) is None]

    if not _is_ancestor(repo_root, base, head):
        note("base_not_ancestor")
    commits = _commit_count(repo_root, base, head)
    if commits == 0:
        note("no_commits")
    if not _is_ancestor(repo_root, base, into):
        note("into_missing_base")

    if worktree is not None:
        dirty = _porcelain_status(worktree)
        if dirty:
            note("worktree_dirty", dirty)
        worktree_head = _head_commit(worktree)
        if worktree_head != head:
            note(
                "worktree_head_mismatch",
                [f"worktree HEAD is {worktree_head}, --head resolves to {head}"],
            )

    tracked_changes = _porcelain_status(repo_root, tracked_only=True)
    if tracked_changes:
        note("integration_checkout_dirty", tracked_changes)

    incoming = _changed_paths(repo_root, base, head)
    paths = sorted(set(incoming) | set(_touched_paths(repo_root, base, head)))
    collisions = _untracked_collisions(repo_root, incoming)
    if collisions:
        note("untracked_collision", collisions)
    outside = []
    denied = []
    parent_owned = []
    for path in paths:
        if not path_in_scopes(path, valid_scopes):
            outside.append(path)
        if any(scope_contains(claim, path) for claim in valid_denies):
            denied.append(path)
        if parent_owned_path(path):
            parent_owned.append(path)
    if outside:
        note("out_of_scope", outside)
    if denied:
        note("denied_path", denied)
    if parent_owned:
        note("parent_owned_file", parent_owned)

    problems = _whitespace_problems(repo_root, base, head)
    if problems:
        note("whitespace_error", problems)

    verdict, verdict_details = _merge_tree_verdict(repo_root, into, head)
    if verdict in {"conflict", "refused"}:
        note("merge_conflict", verdict_details)
    elif verdict == "unavailable":
        note("merge_tree_unavailable", verdict_details)

    mergeable = not reasons
    return {
        "mergeable": mergeable,
        "reasons": sorted(reasons),
        "details": {reason: sorted(entries) for reason, entries in details.items()},
        "base": base,
        "head": head,
        "into": into,
        "commits": commits,
        "changed_paths": paths,
        "merge_command": (
            f"git merge --no-ff --no-edit --no-overwrite-ignore {head}" if mergeable else None
        ),
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


def _run_merge_check(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    if not repo_root.is_dir():
        parser.error(f"--repo-root is not a directory: {args.repo_root}")
    worktree = Path(args.worktree) if args.worktree else None
    if worktree is not None and not worktree.is_dir():
        parser.error(f"--worktree is not a directory: {args.worktree}")
    try:
        base = _resolve_commit(repo_root, args.base)
        head = _resolve_commit(repo_root, args.head)
        # The printed command merges into this checkout, so check against its HEAD.
        into = _head_commit(repo_root)
        report = build_merge_report(
            repo_root=repo_root,
            base=base,
            head=head,
            into=into,
            scopes=args.scope,
            denies=args.deny,
            worktree=worktree,
        )
    except UnresolvedRefError as exc:
        parser.error(f"ref does not resolve to a commit: {exc}")
    except (GitMetadataError, GitCommandError, OSError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(canonical_json(report))
    return 0 if report["mergeable"] else 1


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
    merge_parser = subparsers.add_parser(
        "merge-check", help="check whether a worker branch can merge back now"
    )
    merge_parser.add_argument("--repo-root", required=True, help="integration checkout root")
    merge_parser.add_argument(
        "--base", required=True, help="commit the worker's worktree was cut from"
    )
    merge_parser.add_argument("--head", required=True, help="worker branch or SHA")
    merge_parser.add_argument(
        "--scope",
        action="append",
        required=True,
        metavar="<claim>",
        help="worker write scope claim",
    )
    merge_parser.add_argument(
        "--deny", action="append", default=[], metavar="<claim>", help="claim the worker must not touch"
    )
    merge_parser.add_argument(
        "--worktree", default=None, help="worker worktree path for dirty and HEAD checks"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one subcommand and return the process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "scopes":
        return _run_scopes(parser, args)
    if args.command == "merge-check":
        return _run_merge_check(parser, args)
    raise AssertionError(f"unhandled subcommand {args.command!r}")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
