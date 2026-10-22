#!/usr/bin/env python3
"""Discover source-repo Harness test files and split them into CI shards."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUITES = {
    "harness": "skills/delivery-harness/scripts/tests",
    "product": "skills/product-definition-builder/scripts/tests",
    "ui": "skills/ui-design-builder/scripts/tests",
    "design-system": "skills/design-system-compiler/scripts/tests",
    "activation": "skills/product-activation/scripts/tests",
    "seo": "skills/seo-growth-review/scripts/tests",
}

# Only Git, filesystem, installer and verifier-runtime code differs by
# platform. Keep the list explicit so Windows and macOS coverage cannot
# broaden or shrink by accident.
NATIVE_FILES = (
    "test_platform_delivery_contract.py",
    "test_skill_contract.py",
    "test_host_verifier_runtime.py",
    "test_verifier_runtime.py",
    "test_harness_git.py",
    "test_parity_capture.py",
    "test_node_transitions.py",
    "test_configure_project_context.py",
    "test_write_path_transitions.py",
    "test_conditional_review_journey.py",
    "test_archive_run.py",
    "test_push_archived_candidate.py",
    "test_harness_strict_authority.py",
    "test_install_script.py",
)


class CommandError(Exception):
    """A caller-visible input is invalid."""


def discover_files(root: Path, suite: str) -> list[str]:
    if suite not in SUITES:
        raise CommandError(f"unknown suite: {suite}")
    directory = root / SUITES[suite]
    if not directory.is_dir():
        raise CommandError(f"test directory is missing: {directory}")
    return sorted(
        path.relative_to(root).as_posix()
        for path in directory.rglob("test_*.py")
        if path.is_file()
    )


def candidate_files(suite: str, platform: str, discovered: list[str]) -> list[str]:
    if suite != "harness" or platform == "linux":
        return discovered
    selected = [name for name in discovered if Path(name).name in NATIVE_FILES]
    missing = set(NATIVE_FILES) - {Path(name).name for name in selected}
    if missing:
        raise CommandError(f"native files no longer discovered: {', '.join(sorted(missing))}")
    return selected


def split_files(files: list[str], shard_count: int) -> list[list[str]]:
    if shard_count <= 0:
        raise CommandError("shard count must be positive")
    return [files[index::shard_count] for index in range(shard_count)]


def plan_shard(root: Path, args: argparse.Namespace) -> None:
    discovered = discover_files(root, args.suite)
    if not discovered:
        raise CommandError("discovery found no tests")
    shards = split_files(candidate_files(args.suite, args.platform, discovered), args.shard_count)
    if not 0 <= args.shard_index < args.shard_count:
        raise CommandError("shard index is outside the requested shard count")
    names = [Path(name).name for name in shards[args.shard_index]]
    if args.format == "json":
        print(json.dumps({"files": names}, indent=2))
    else:
        for name in names:
            print(name)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", default=".", help="source repository root")
    subcommands = result.add_subparsers(dest="command", required=True)
    plan = subcommands.add_parser("plan", help="print one deterministic shard")
    plan.add_argument("--suite", choices=tuple(SUITES), default="harness")
    plan.add_argument("--platform", choices=("linux", "macos", "windows"), required=True)
    plan.add_argument("--shard-count", type=int, required=True)
    plan.add_argument("--shard-index", type=int, required=True)
    plan.add_argument("--format", choices=("names", "json"), default="names")
    plan.set_defaults(handler=plan_shard)
    return result


def main() -> int:
    arguments = parser().parse_args()
    root = Path(arguments.repo_root).resolve()
    if not (root / "skills").is_dir():
        print(f"error: repository root does not contain skills/: {root}", file=sys.stderr)
        return 2
    try:
        arguments.handler(root, arguments)
    except CommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
