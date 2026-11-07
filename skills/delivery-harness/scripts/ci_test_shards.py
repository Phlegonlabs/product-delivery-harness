#!/usr/bin/env python3
"""Discover source-repo Harness test files, split them into CI shards, or run them in parallel.

`matrix --base <sha> --log-dir <new dir>` runs the whole Required Verification
matrix from the repository root, with the browser suites required and the diff
checked from the base to HEAD. It writes one log per step and summary.txt,
whose last line is `result: pass`, `fail` or `interrupted`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path

SUITES = {
    "harness": "skills/delivery-harness/scripts/tests",
    "product": "skills/product-definition-builder/scripts/tests",
    "ui": "skills/ui-design-builder/scripts/tests",
    "design-system": "skills/design-system-compiler/scripts/tests",
}

# Only Git, filesystem, installer and verifier-runtime code differs by
# platform. Keep the list explicit so Windows and macOS coverage cannot
# broaden or shrink by accident.
NATIVE_FILES = (
    "test_platform_delivery_contract.py",
    "test_skill_contract.py",
    "test_host_verifier_runtime.py",
    "test_current_host_admission.py",
    "test_document_write.py",
    "test_worktree_path_identity.py",
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


# Modules that drive install.sh against the checkout and read its Git state
# collide with concurrent modules; the local runner executes them after the
# parallel batch, one at a time.
SERIAL_FILES = ("test_install_script.py",)


PYFLAKES_DIRS = tuple(
    f"skills/{name}/scripts"
    for name in ("delivery-harness", "product-definition-builder", "ui-design-builder", "design-system-compiler")
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


def run_one(root: Path, suite: str, name: str, log_dir: Path) -> tuple[str, int, float, Path]:
    """Run one test module in its own process from the repository root."""
    log_path = log_dir / f"{name}.log"
    started = time.perf_counter()
    with log_path.open("wb") as log:
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", SUITES[suite], "-p", name],
            cwd=root, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )
    return name, completed.returncode, time.perf_counter() - started, log_path


def run_suite(root: Path, suite: str, workers: int, log_dir: Path, files: list[str] | None = None) -> int:
    """Run a suite's test modules in parallel processes; return 1 on any failure."""
    if workers <= 0:
        raise CommandError("worker count must be positive")
    names = files or [Path(name).name for name in discover_files(root, suite)]
    if not names:
        raise CommandError("discovery found no tests")
    log_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    parallel = [name for name in names if name not in SERIAL_FILES]
    serial = [name for name in names if name in SERIAL_FILES]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda name: run_one(root, suite, name, log_dir), parallel))
    results.extend(run_one(root, suite, name, log_dir) for name in serial)
    failed = [result for result in results if result[1] != 0]
    for name, code, seconds, log_path in sorted(results, key=lambda item: -item[2]):
        print(f"{'FAIL' if code else 'ok  '} {seconds:7.1f}s {name} -> {log_path}")
    print(f"{suite}: {len(results) - len(failed)} passed, {len(failed)} failed, "
          f"{time.perf_counter() - started:.1f}s wall with {workers} workers")
    return 1 if failed else 0


def run_shards(root: Path, args: argparse.Namespace) -> None:
    log_dir = Path(args.log_dir) if args.log_dir else Path(tempfile.mkdtemp(prefix="pdh-tests-"))
    code = run_suite(root, args.suite, args.workers, log_dir)
    if code:
        raise CommandError(f"{args.suite} suite failed; logs under {log_dir}")


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True)
    if completed.returncode:
        raise CommandError(f"git {' '.join(arguments)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def matrix_steps(root: Path, base: str) -> list[tuple[str, list[str] | None, dict[str, str]]]:
    """Return (name, command, extra env) per step; the harness suite has no command."""
    python = sys.executable
    browser = {"PDH_REQUIRE_BROWSER_TESTS": "1", "PLAYWRIGHT_MODULE": str(root / "node_modules" / "playwright")}

    def suite(name: str, *pattern: str) -> list[str]:
        return [python, "-m", "unittest", "discover", "-s", SUITES[name], *pattern, "-v"]

    return [
        ("check_skill_spec", [python, "skills/delivery-harness/scripts/check_skill_spec.py"], {}),
        ("pyflakes", [python, "-m", "pyflakes", *PYFLAKES_DIRS], {}),
        ("docs_weight", [python, "skills/delivery-harness/scripts/docs_weight.py"], {}),
        ("harness", None, {}),
        ("golden_path", suite("harness", "-p", "test_golden_path.py"), {"HARNESS_GOLDEN_PATH": "1"}),
        ("product", suite("product"), {}),
        ("ui", suite("ui"), browser),
        ("design-system", suite("design-system"), browser),
        ("diff_check", ["git", "diff", "--check", base, "HEAD"], {}),
    ]


def _append(path: Path, line: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")


def run_matrix(root: Path, args: argparse.Namespace) -> int:
    """Run every Required Verification step in order; return 1 if any step fails."""
    if args.workers <= 0:
        raise CommandError("worker count must be positive")
    base = _git(root, "rev-parse", "--verify", "--quiet", f"{args.base}^{{commit}}")
    head = _git(root, "rev-parse", "HEAD")
    dirty = "yes" if _git(root, "status", "--porcelain") else "no"
    log_dir = Path(args.log_dir)
    if log_dir.exists() and (not log_dir.is_dir() or any(log_dir.iterdir())):
        raise CommandError(f"log directory must be new or empty: {log_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)
    summary = log_dir / "summary.txt"
    for line in (f"head: {head}", f"base: {base}", f"dirty: {dirty}"):
        _append(summary, line)
    result, failed = "interrupted", 0
    try:
        for name, command, extra in matrix_steps(root, base):
            log_path = log_dir / f"{name}.log"
            started = time.perf_counter()
            if command is None:
                with log_path.open("w", encoding="utf-8") as log, redirect_stdout(log):
                    code = run_suite(root, "harness", args.workers, log_dir / "harness")
            else:
                with log_path.open("wb") as log:
                    code = subprocess.run(
                        command, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                        env=dict(os.environ, PYTHONIOENCODING="utf-8", **extra),
                    ).returncode
            line = f"{name} exit={code} seconds={time.perf_counter() - started:.1f}"
            _append(summary, line)
            print(f"{line} -> {log_path}", flush=True)
            failed += code != 0
        result = "fail" if failed else "pass"
    finally:
        _append(summary, f"result: {result}")
    print(f"matrix: {result}; summary {summary}")
    return 1 if failed else 0


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
    run = subcommands.add_parser("run", help="run one suite's modules in parallel processes")
    run.add_argument("--suite", choices=tuple(SUITES), default="harness")
    run.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    run.add_argument("--log-dir", default=None, help="per-module log directory (default: a new temp dir)")
    run.set_defaults(handler=run_shards)
    matrix = subcommands.add_parser("matrix", help="run the whole Required Verification matrix")
    matrix.add_argument("--base", required=True, help="commit the candidate diff is checked against")
    matrix.add_argument("--log-dir", required=True, help="new or empty directory for logs and summary.txt")
    matrix.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    matrix.set_defaults(handler=run_matrix)
    return result


def main() -> int:
    arguments = parser().parse_args()
    root = Path(arguments.repo_root).resolve()
    if not (root / "skills").is_dir():
        print(f"error: repository root does not contain skills/: {root}", file=sys.stderr)
        return 2
    try:
        return arguments.handler(root, arguments) or 0
    except CommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
