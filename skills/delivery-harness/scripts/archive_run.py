#!/usr/bin/env python3
"""Archive a completed run's coordination set under docs/goal/archived/.

The script refuses anything but a completed run whose PLAN/RUN pair
passes full manifest validation with every final gate PASS, lists every
exact move first (dry run by default), and moves — never deletes — the
coordination set into one timestamped archive directory. It performs no
Git operations; committing the archival stays with the parent under its
ordinary create_local_commits authorization.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import load_plan, load_run  # noqa: E402
from harness_manifest import validate_current_plan_run  # noqa: E402
from harness_ui_evidence import (  # noqa: E402
    validate_integration_head_against_git,
    validate_ui_evidence_files,
)

GOAL_DIR = Path("docs/goal")
REQUIRED_FILES = ("PLAN.md", "RUN.md")
OPTIONAL_FILES = ("DECISIONS.md", "REFINEMENT_BACKLOG.md")
OPTIONAL_DIRS = ("evidence",)
OPTIONAL_OUTSIDE = ("docs/tasks.md",)
DOCUMENTS_PATH = Path("docs/DOCUMENTS.md")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAIN_REF_RE = re.compile(
    r"^(?:refs/heads/main|refs/remotes/[A-Za-z0-9._-]+/main)$"
)
DOCUMENTS_ROW = (
    "| `docs/goal/archived/` | `docs/goal/archived/` | run closeout | "
    "harness parent | archived completed run coordination sets "
    "(move, never delete) | "
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "run"


def _completed_run_ok(run: dict[str, object]) -> list[str]:
    problems: list[str] = []
    if run.get("status") != "complete":
        problems.append(
            f"run status is {run.get('status')!r}; only a complete run may be archived"
        )
    final_gates = run.get("final_gate_results")
    if final_gates is not None:
        if not isinstance(final_gates, list):
            problems.append("run.final_gate_results must be a list")
        else:
            for gate in final_gates:
                if isinstance(gate, dict) and gate.get("status") != "PASS":
                    problems.append(
                        f"final gate {gate.get('id')!r} is {gate.get('status')!r}; "
                        "every final gate must PASS before archival"
                    )
    return problems


def plan_moves(root: Path) -> tuple[list[Path], list[str]]:
    """Return repo-relative sources to move, and missing required paths."""

    moves: list[Path] = []
    missing_required: list[str] = []
    sources: list[tuple[Path, bool]] = [
        (GOAL_DIR / name, True) for name in REQUIRED_FILES
    ]
    sources.extend((GOAL_DIR / name, False) for name in OPTIONAL_FILES)
    sources.append((GOAL_DIR / "evidence", False))
    sources.append((Path("docs/tasks.md"), False))
    for source, required in sources:
        if (root / source).exists():
            moves.append(source)
        elif required:
            missing_required.append(source.as_posix())
    return moves, missing_required


def _resolved_inside(root: Path, path: Path) -> Path | None:
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root)
        return resolved
    except (OSError, ValueError):
        return None


def _preflight_archive_paths(
    root: Path, moves: list[Path], target: Path
) -> list[str]:
    """Check every source and destination before creating anything."""

    problems: list[str] = []
    root = root.resolve()
    resolved_target = _resolved_inside(root, target)
    if resolved_target is None:
        return [f"archive target resolves outside the repository root: {target}"]
    if target.exists():
        problems.append(f"archive target already exists: {target}")
    if target.parent.exists() and not target.parent.is_dir():
        problems.append(
            f"archive destination parent is not a directory: {target.parent}"
        )

    destinations: set[Path] = set()
    for source in moves:
        source_path = root / source
        resolved_source = _resolved_inside(root, source_path)
        if resolved_source is None:
            problems.append(f"source resolves outside the repository root: {source}")
            continue
        if not source_path.exists():
            # plan_moves reports required files; optional paths may be absent.
            continue
        destination = resolved_target / source.name
        if destination in destinations:
            problems.append(f"duplicate archive destination: {destination}")
        destinations.add(destination)
        if destination.exists():
            problems.append(f"archive destination already exists: {destination}")

    documents = root / DOCUMENTS_PATH
    if documents.parent.exists() and not documents.parent.is_dir():
        problems.append(
            f"documents destination parent is not a directory: {documents.parent}"
        )
    if documents.exists() and not documents.is_file():
        problems.append(f"documents destination is not a file: {DOCUMENTS_PATH}")
    resolved_documents = _resolved_inside(root, documents)
    if documents.exists() and resolved_documents is None:
        problems.append(
            f"documents destination resolves outside the repository root: {DOCUMENTS_PATH}"
        )
    return problems


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _live_head_problems(
    run: dict[str, object],
    root: Path,
    expected_main: str | None,
    main_ref: str | None,
    allowed_dirty_roots: list[Path],
) -> list[str]:
    """Bind pre-promotion archival to the exact run branch and observed main."""

    problems: list[str] = []
    if expected_main is None:
        return ["--expected-main is required with --apply"]
    if not FULL_SHA_RE.fullmatch(expected_main):
        return [f"--expected-main {expected_main!r} must be a full lowercase SHA"]
    if main_ref is None:
        return ["--main-ref is required with --apply"]
    if not MAIN_REF_RE.fullmatch(main_ref) or ".." in main_ref:
        return [
            "--main-ref must be refs/heads/main or refs/remotes/<remote>/main"
        ]

    observed_main = _git(root, "rev-parse", "--verify", f"{main_ref}^{{commit}}")
    if observed_main is None:
        return [f"could not resolve the observed main ref {main_ref}"]
    if observed_main.returncode != 0:
        reason = observed_main.stderr.strip() or (
            f"git rev-parse exited {observed_main.returncode}"
        )
        return [f"could not resolve the observed main ref {main_ref}: {reason}"]
    observed_main_sha = observed_main.stdout.strip()
    if observed_main_sha != expected_main:
        return [
            f"observed main ref {main_ref} is {observed_main_sha}, not the "
            f"authorized/read-back SHA {expected_main}"
        ]

    integration = run.get("integration")
    recorded_branch = (
        integration.get("branch") if isinstance(integration, dict) else None
    )
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch is None:
        return ["could not read the current Git branch"]
    if branch.returncode != 0:
        return ["archive apply requires a named run branch; detached HEAD is refused"]
    live_branch = branch.stdout.strip()
    if live_branch in {"main", "master", "development"}:
        problems.append(
            f"archive apply is forbidden on protected branch {live_branch!r}"
        )
    if live_branch != recorded_branch:
        problems.append(
            f"current branch {live_branch!r} does not match run integration branch "
            f"{recorded_branch!r}"
        )

    head = _git(root, "rev-parse", "HEAD")
    if head is None:
        return ["could not read the live Git HEAD"]
    if head.returncode != 0:
        reason = head.stderr.strip() or f"git rev-parse exited {head.returncode}"
        return [f"could not read the live Git HEAD: {reason}"]
    live_head = head.stdout.strip()
    recorded_head = (
        integration.get("integration_head_sha")
        if isinstance(integration, dict)
        else None
    )
    if live_head != recorded_head:
        problems.append(
            f"live HEAD {live_head} does not match run integration head {recorded_head}"
        )

    ancestry = _git(root, "merge-base", "--is-ancestor", expected_main, live_head)
    if ancestry is None:
        problems.append("could not verify live HEAD ancestry")
    elif ancestry.returncode != 0:
        problems.append(
            f"live HEAD {live_head} does not descend from expected main/base {expected_main}"
        )

    status = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if status is None:
        problems.append("could not read the live checkout status")
    elif status.returncode != 0:
        reason = status.stderr.strip() or f"git status exited {status.returncode}"
        problems.append(f"could not read the live checkout status: {reason}")
    else:
        allowed = [path.as_posix().rstrip("/") for path in allowed_dirty_roots]
        entries = status.stdout.split("\0")
        index = 0
        while index < len(entries):
            entry = entries[index]
            index += 1
            if not entry:
                continue
            code = entry[:2]
            dirty_path = entry[3:].replace("\\", "/")
            if "R" in code or "C" in code:
                # In porcelain -z mode a rename/copy has a second path field.
                if index < len(entries) and entries[index]:
                    dirty_path = f"{dirty_path} -> {entries[index]}"
                    index += 1
                problems.append(
                    f"archive apply refuses renamed/copied dirty path: {dirty_path}"
                )
                continue
            if not any(
                dirty_path == root_path or dirty_path.startswith(root_path + "/")
                for root_path in allowed
            ):
                problems.append(
                    f"archive apply found unrelated dirty path: {dirty_path}"
                )
    return problems


def _move_entry(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"archive destination already exists: {destination}")
    shutil.move(str(source), str(destination))


def _rollback_archive(
    root: Path,
    moved: list[tuple[Path, Path]],
    documents_snapshot: bytes | None,
    target: Path,
) -> list[str]:
    """Restore the pre-archive layout; retain archive copies only if a restore fails."""

    problems: list[str] = []
    documents_path = root / DOCUMENTS_PATH
    if documents_snapshot is not None:
        try:
            documents_path.write_bytes(documents_snapshot)
        except OSError as exc:
            problems.append(
                f"could not restore {DOCUMENTS_PATH.as_posix()}: {exc}; "
                "the original bytes were not replaced"
            )
    elif documents_path.exists():
        try:
            if documents_path.is_file():
                documents_path.unlink()
            else:
                problems.append(
                    f"cannot remove newly created {DOCUMENTS_PATH.as_posix()}: "
                    "the path is no longer a file"
                )
        except OSError as exc:
            problems.append(
                f"could not remove newly created {DOCUMENTS_PATH.as_posix()}: {exc}"
            )
    for source, destination in reversed(moved):
        try:
            if not destination.exists():
                problems.append(f"rolled-back entry is absent: {destination}")
            elif source.exists():
                problems.append(
                    f"cannot restore {source.as_posix()} because the source path reappeared"
                )
            else:
                shutil.move(str(destination), str(source))
        except OSError as exc:
            problems.append(
                f"could not restore {source.as_posix()}; recoverable copy retained at "
                f"{destination}: {exc}"
            )
    if not problems and target.exists():
        try:
            target.rmdir()
        except OSError as exc:
            problems.append(f"could not remove the empty failed archive target: {exc}")
    if not problems and target.parent.exists():
        try:
            target.parent.rmdir()
        except OSError:
            # A non-empty parent may retain unrelated archives; only the empty
            # directory chain created for this failed attempt is safe to undo.
            pass
    return problems


def archive(
    root: Path,
    *,
    slug: str,
    apply: bool,
    stamp: str | None = None,
    expected_main: str | None = None,
    main_ref: str | None = None,
) -> int:
    root = root.resolve()
    run_path = root / GOAL_DIR / "RUN.md"
    if not run_path.is_file():
        print(f"error: {run_path} does not exist", file=sys.stderr)
        return 1
    try:
        run = load_run(run_path)
    except Exception as exc:  # noqa: BLE001 - report any parse failure verbatim
        print(f"error: cannot read RUN manifest: {exc}", file=sys.stderr)
        return 1

    problems = _completed_run_ok(run)
    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1

    moves, missing_required = plan_moves(root)
    if missing_required:
        for name in missing_required:
            print(f"error: required coordination file missing: {name}", file=sys.stderr)
        return 1
    if not moves:
        print("error: nothing to archive", file=sys.stderr)
        return 1

    try:
        plan = load_plan(root / GOAL_DIR / "PLAN.md")
    except Exception as exc:  # noqa: BLE001 - report any parse failure verbatim
        print(f"error: cannot read PLAN manifest: {exc}", file=sys.stderr)
        return 1
    validation_errors = validate_current_plan_run(plan, run, repo_root=root)
    validation_errors.extend(validate_ui_evidence_files(run, root))
    validation_errors.extend(validate_integration_head_against_git(run, root))
    if validation_errors:
        print(
            "error: run validation failed; fix RUN/PLAN before archival:",
            file=sys.stderr,
        )
        for error in validation_errors[:5]:
            print(f"error: {error}", file=sys.stderr)
        return 1

    if stamp is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    elif not re.fullmatch(r"\d{8}-\d{6}", stamp):
        print(
            f"error: --stamp {stamp!r} must look like YYYYMMDD-HHMMSS",
            file=sys.stderr,
        )
        return 2
    target = root / GOAL_DIR / "archived" / f"{stamp}-{_slugify(slug)}"
    if target.exists():
        print(
            f"error: archive target already exists: {target}", file=sys.stderr
        )
        return 1
    preflight_problems = _preflight_archive_paths(root, moves, target)
    if preflight_problems:
        for problem in preflight_problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    live_head_problems = (
        _live_head_problems(run, root, expected_main, main_ref, moves)
        if apply
        else []
    )
    if live_head_problems:
        for problem in live_head_problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1

    print(f"archive target: {target.relative_to(root).as_posix()}")
    for source in moves:
        print(f"move: {source.as_posix()}")
    print(f"documents row: {DOCUMENTS_ROW}")
    if not apply:
        print("dry run only; pass --apply to move these exact paths")
        return 0

    documents_path = root / DOCUMENTS_PATH
    documents_snapshot = (
        documents_path.read_bytes() if documents_path.is_file() else None
    )
    moved: list[tuple[Path, Path]] = []
    try:
        target.mkdir(parents=True)
        for source in moves:
            source_path = root / source
            destination_path = target / source.name
            _move_entry(source_path, destination_path)
            moved.append((source_path, destination_path))
        _update_documents(root)
    except Exception as exc:  # noqa: BLE001 - every apply failure must roll back
        print(f"error: archival failed: {exc}", file=sys.stderr)
        rollback_problems = _rollback_archive(
            root, moved, documents_snapshot, target
        )
        if rollback_problems:
            for problem in rollback_problems:
                print(f"error: {problem}", file=sys.stderr)
        else:
            print(
                "rolled back every moved entry after the failure",
                file=sys.stderr,
            )
        return 1

    print(f"archived {len(moves)} entries; never deleted anything")
    return 0


def _update_documents(root: Path) -> None:
    documents = root / DOCUMENTS_PATH
    if not documents.is_file():
        print(f"note: {DOCUMENTS_PATH.as_posix()} absent; row not recorded")
        return
    text = documents.read_text(encoding="utf-8")
    if "docs/goal/archived/" in text:
        return
    lines = text.splitlines(keepends=True)
    insert_at = len(lines)
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].lstrip().startswith("|"):
            insert_at = index + 1
            break
    newline = "\r\n" if "\r\n" in text else "\n"
    lines.insert(insert_at, DOCUMENTS_ROW + newline)
    documents.write_text("".join(lines), encoding="utf-8", newline="")
    print(f"documents row recorded in {DOCUMENTS_PATH.as_posix()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="target repository root (default: current directory)",
    )
    parser.add_argument(
        "--slug",
        help="initiative slug for the archive directory name "
        "(default: the run id)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the listed moves; default is a dry run",
    )
    parser.add_argument(
        "--stamp",
        help="pin the archive directory timestamp as YYYYMMDD-HHMMSS "
        "(default: now; deterministic re-runs and tests)",
    )
    parser.add_argument(
        "--expected-main",
        help="full current main SHA read back immediately before pre-promotion archival; "
        "required with --apply",
    )
    parser.add_argument(
        "--main-ref",
        help="fully qualified local or remote-tracking main ref whose current value "
        "must equal --expected-main; required with --apply",
    )
    args = parser.parse_args(argv)
    run_path = args.repo_root / GOAL_DIR / "RUN.md"
    slug = args.slug
    if slug is None:
        try:
            slug = str(load_run(run_path).get("run_id") or "run")
        except Exception:  # noqa: BLE001 - slug falls back below
            slug = "run"
    return archive(
        args.repo_root,
        slug=slug,
        apply=args.apply,
        stamp=args.stamp,
        expected_main=args.expected_main,
        main_ref=args.main_ref,
    )


if __name__ == "__main__":
    raise SystemExit(main())
