#!/usr/bin/env python3
"""Discover source-repo test files and balance Harness CI shards by timing."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from host_process import HostProcessError, run_process_tree


SUITES = {
    "harness": "skills/delivery-harness/scripts/tests",
    "product": "skills/product-definition-builder/scripts/tests",
    "ui": "skills/ui-design-builder/scripts/tests",
    "design-system": "skills/design-system-compiler/scripts/tests",
    "activation": "skills/product-activation/scripts/tests",
    "seo": "skills/seo-growth-review/scripts/tests",
}

# These are the Windows-only runtime and installer checks from the previous
# monolithic CI step. Keep the list explicit so sharding cannot broaden or
# accidentally remove this platform's focused coverage.
WINDOWS_NATIVE_FILES = (
    "test_platform_delivery_contract.py",
    "test_skill_contract.py",
    "test_host_verifier_runtime.py",
    "test_verifier_runtime.py",
    "test_harness_git.py",
    "test_parity_capture.py",
    "test_node_transitions.py",
    "test_configure_project_context.py",
    "test_write_path_transitions.py",
    "test_archive_run.py",
    "test_trusted_host_publication.py",
    "test_harness_strict_authority.py",
    "test_install_script.py",
)

AGGREGATE_SUCCESS = "success"


class CommandError(Exception):
    """A caller-visible input or profile result is invalid."""


def repo_path(args: argparse.Namespace) -> Path:
    return Path(args.repo_root).resolve()


def suite_dir(root: Path, suite: str) -> Path:
    if suite not in SUITES:
        raise CommandError(f"unknown suite: {suite}")
    return root / SUITES[suite]


def discover_files(root: Path, suite: str) -> list[str]:
    directory = suite_dir(root, suite)
    if not directory.is_dir():
        raise CommandError(f"test directory is missing: {directory}")
    return sorted(
        path.relative_to(root).as_posix()
        for path in directory.rglob("test_*.py")
        if path.is_file()
    )


def load_timings(root: Path, args: argparse.Namespace, expected: Iterable[str]) -> dict[str, float]:
    path = Path(args.timings).resolve()
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise CommandError(f"cannot read timing manifest {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise CommandError("timing manifest must be version 1")
    timings = payload.get("timings")
    if not isinstance(timings, dict):
        raise CommandError("timing manifest requires a timings object")

    expected_set = set(expected)
    actual_set = set(timings)
    missing = sorted(expected_set - actual_set)
    if missing and not getattr(args, "allow_unmeasured", False):
        extra = sorted(actual_set - expected_set)
        details = []
        if missing:
            details.append(f"unmeasured: {', '.join(missing)}")
        if extra:
            details.append(f"extra: {', '.join(extra)}")
        raise CommandError(
            "timing manifest does not cover discovery; rerun profile or pass "
            "--allow-unmeasured for conservative scheduling (" + "; ".join(details) + ")"
        )

    result: dict[str, float] = {}
    for name, value in timings.items():
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value <= 0
        ):
            raise CommandError(f"timing must be a positive finite number: {name}")
        result[name] = float(value)
    fallback_estimate = max(result.values(), default=1.0)
    for name in missing:
        result[name] = fallback_estimate
    return result


def candidate_files(root: Path, suite: str, platform: str, discovered: list[str]) -> list[str]:
    if suite != "harness" or platform != "windows":
        return discovered
    selected = set(WINDOWS_NATIVE_FILES)
    selected_paths = {
        relative_name
        for relative_name in discovered
        if Path(relative_name).name in selected
    }
    missing = selected - {Path(name).name for name in selected_paths}
    if missing:
        raise CommandError(f"Windows-native files no longer discovered: {', '.join(sorted(missing))}")
    return sorted(selected_paths)


def balance_files(files: list[str], timings: dict[str, float], shard_count: int) -> list[list[str]]:
    if shard_count <= 0:
        raise CommandError("shard count must be positive")
    shards: list[list[str]] = [[] for _ in range(shard_count)]
    loads = [0.0 for _ in range(shard_count)]
    weighted = sorted(files, key=lambda name: (-timings[name], name))
    for name in weighted:
        shard = min(range(shard_count), key=lambda index: (loads[index], index))
        shards[shard].append(name)
        loads[shard] += timings[name]
    return [[name for name in sorted(shard)] for shard in shards]


def import_test_module(path: Path, index: int):
    module_name = f"pdh_ci_profile_{index}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise CommandError(f"cannot import test file: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _profile_file(root: Path, relative_name: str, output: Path) -> None:
    """Run one file in the parent's deadline-owned process tree."""
    path = root / relative_name
    sys.path.insert(0, str(path.parent))
    started = time.perf_counter()
    module = import_test_module(path, 0)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=0).run(suite)
    output.write_text(json.dumps({
        "duration_seconds": round(time.perf_counter() - started, 6),
        "tests": result.testsRun,
        "errors": len(result.errors) + int(result.testsRun == 0),
        "failures": len(result.failures),
        "skipped": len(result.skipped),
        "status": "failed" if result.errors or result.failures or not result.testsRun else "passed",
    }), encoding="utf-8")


def profile_suite(root: Path, args: argparse.Namespace) -> dict[str, object]:
    if not math.isfinite(args.timeout_seconds) or args.timeout_seconds < 0:
        raise CommandError("profile timeout must be a finite nonnegative number")
    started = time.perf_counter()
    timings: dict[str, float] = {}
    counts = {"tests": 0, "errors": 0, "failures": 0, "skipped": 0}
    failures: list[str] = []
    file_results: dict[str, dict[str, object]] = {}
    timed_out = False

    for relative_name in discover_files(root, args.suite):
        remaining = args.timeout_seconds - (time.perf_counter() - started)
        if remaining <= 0:
            timed_out = True
            break
        file_started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="pdh-ci-profile-") as temporary:
            output = Path(temporary) / "result.json"
            environment = dict(os.environ)
            environment["PYTHONPATH"] = os.pathsep.join(filter(None, (
                str(Path(__file__).resolve().parent), environment.get("PYTHONPATH"),
            )))
            command = [sys.executable, "-c",
                       "from ci_test_shards import _profile_file; from pathlib import Path; "
                       "import sys; _profile_file(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]))",
                       str(root), relative_name, str(output)]
            try:
                process = run_process_tree(command, cwd=root, environment=environment,
                                           timeout_seconds=remaining,
                                           stdout_stream=sys.stdout, stderr_stream=sys.stderr)
            except HostProcessError as exc:
                raise CommandError(f"profile process ownership failed: {exc}") from exc
            file_result = {
                "duration_seconds": round(time.perf_counter() - file_started, 6),
                "tests": 0, "errors": 1, "failures": 0, "skipped": 0, "status": "failed",
            }
            if process.timeout:
                file_result.update(errors=0, status="timed_out")
                file_results[relative_name] = file_result
                timed_out = True
                break
            if process.exit_code == 0 and output.is_file():
                file_result = json.loads(output.read_text(encoding="utf-8"))
        file_results[relative_name] = file_result
        timings[relative_name] = max(float(file_result["duration_seconds"]), 0.000001)
        for key in counts:
            counts[key] += file_result[key]
        if file_result["status"] != "passed":
            failures.append(relative_name)
            if args.fail_fast:
                break

    payload: dict[str, object] = {
        "profiled_at": datetime.now(timezone.utc).isoformat(),
        "suite": args.suite,
        "timeout_seconds": args.timeout_seconds,
        "timings": dict(sorted(timings.items())),
        "counts": counts,
        "file_results": dict(sorted(file_results.items())),
        "incomplete": bool(failures or timed_out or counts["tests"] == 0),
    }
    if failures:
        payload["failures"] = failures
    if timed_out:
        payload["timeout"] = True
    return payload


def write_manifest(root: Path, args: argparse.Namespace) -> None:
    result = profile_suite(root, args)
    manifest = {
        "version": 1,
        "source": args.source,
        "timings": result["timings"],
    }
    output = Path(args.manifest_out).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.results_out:
        results_path = Path(args.results_out).resolve()
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["incomplete"]:
        reason = "timed out" if result.get("timeout") else "did not pass every discovered test"
        raise CommandError(f"profile {reason}; timing and per-file results were saved")


def plan_shard(root: Path, args: argparse.Namespace) -> None:
    discovered = discover_files(root, args.suite)
    if not discovered:
        raise CommandError("discovery found no tests")
    selected = candidate_files(root, args.suite, args.platform, discovered)
    timings = load_timings(root, args, selected)
    shards = balance_files(selected, timings, args.shard_count)
    if not 0 <= args.shard_index < args.shard_count:
        raise CommandError("shard index is outside the requested shard count")
    shard = shards[args.shard_index]
    runnable_files = [Path(name).name for name in shard]
    if args.format == "json":
        print(
            json.dumps(
                {
                    "files": runnable_files,
                    "timings": {Path(name).name: timings[name] for name in shard},
                },
                indent=2,
            )
        )
    else:
        for name in runnable_files:
            print(name)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CommandError(f"duplicate timing key: {key}")
        result[key] = value
    return result


def check_aggregate(results: list[str]) -> bool:
    return bool(results) and all(result == AGGREGATE_SUCCESS for result in results)


def run_gate(_root: Path, args: argparse.Namespace) -> None:
    if check_aggregate(args.result):
        print("all required matrix jobs succeeded")
        return
    for result in args.result:
        if result != AGGREGATE_SUCCESS:
            print(f"required matrix result: {result}")
    raise CommandError("a required matrix job did not succeed; skipped and timed out fail")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", default=".", help="source repository root")
    subcommands = result.add_subparsers(dest="command", required=True)

    profile = subcommands.add_parser("profile", help="profile every test file in a suite")
    profile.add_argument("--suite", choices=tuple(SUITES), default="harness")
    profile.add_argument("--timeout-seconds", type=float, default=1200.0)
    profile.add_argument("--fail-fast", action="store_true")
    profile.add_argument("--source", default="measured local profile")
    profile.add_argument("--manifest-out", required=True)
    profile.add_argument("--results-out")
    profile.set_defaults(handler=write_manifest)

    plan = subcommands.add_parser("plan", help="print one deterministic measured shard")
    plan.add_argument("--suite", choices=tuple(SUITES), default="harness")
    plan.add_argument("--platform", choices=("linux", "macos", "windows"), required=True)
    plan.add_argument("--shard-count", type=int, required=True)
    plan.add_argument("--shard-index", type=int, required=True)
    plan.add_argument("--timings", required=True)
    plan.add_argument("--allow-unmeasured", action="store_true")
    plan.add_argument("--format", choices=("names", "json"), default="names")
    plan.set_defaults(handler=plan_shard)

    gate = subcommands.add_parser("gate", help="fail unless every matrix result is success")
    gate.add_argument("--result", action="append", required=True)
    gate.set_defaults(handler=run_gate)
    return result


def main() -> int:
    arguments = parser().parse_args()
    root = repo_path(arguments)
    if not (root / "skills").is_dir():
        raise CommandError(f"repository root does not contain skills/: {root}")
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
