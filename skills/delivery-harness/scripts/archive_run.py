#!/usr/bin/env python3
"""Archive a completed run's coordination set under docs/goal/archived/.

The script refuses anything but a completed run whose final gates all
PASS, lists every exact move first (dry run by default), and moves —
never deletes — the coordination set into one timestamped archive
directory. It performs no Git operations; committing the archival stays
with the parent under its ordinary create_local_commits authorization.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import load_run  # noqa: E402

GOAL_DIR = Path("docs/goal")
REQUIRED_FILES = ("PLAN.md", "RUN.md")
OPTIONAL_FILES = ("DECISIONS.md", "REFINEMENT_BACKLOG.md")
OPTIONAL_DIRS = ("evidence",)
OPTIONAL_OUTSIDE = ("docs/tasks.md",)
DOCUMENTS_PATH = Path("docs/DOCUMENTS.md")
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


def archive(
    root: Path,
    *,
    slug: str,
    apply: bool,
) -> int:
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

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = root / GOAL_DIR / "archived" / f"{stamp}-{_slugify(slug)}"
    if target.exists():
        print(
            f"error: archive target already exists: {target}", file=sys.stderr
        )
        return 1

    print(f"archive target: {target.relative_to(root).as_posix()}")
    for source in moves:
        print(f"move: {source.as_posix()}")
    print(f"documents row: {DOCUMENTS_ROW}")
    if not apply:
        print("dry run only; pass --apply to move these exact paths")
        return 0

    target.mkdir(parents=True)
    for source in moves:
        shutil.move(str(root / source), str(target / source.name))
    _update_documents(root)
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
    args = parser.parse_args(argv)
    run_path = args.repo_root / GOAL_DIR / "RUN.md"
    slug = args.slug
    if slug is None:
        try:
            slug = str(load_run(run_path).get("run_id") or "run")
        except Exception:  # noqa: BLE001 - slug falls back below
            slug = "run"
    return archive(args.repo_root, slug=slug, apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
