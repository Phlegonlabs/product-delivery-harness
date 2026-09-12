#!/usr/bin/env python3
"""Report the normative word weight of each skill and its delta vs a baseline.

Counts words in every skill's SKILL.md plus its references/*.md, compares
the totals against the most recent reachable v* tag (or --baseline <ref>),
and prints one line per changed file plus per-skill and grand totals. This
is a read-only visibility tool for the documentation complexity ratchet:
it makes growth visible at verification time and never gates a release.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import ManifestError  # noqa: E402

SKILLS_ROOT = Path("skills")


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if result.returncode != 0:
        raise ManifestError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout


def _word_count(text: str) -> int:
    return len(text.split())


def tracked_files(repo_root: Path, ref: str | None) -> list[Path]:
    """SKILL.md plus references/*.md under skills/ at ref (None = worktree)."""

    if ref is None:
        listing = _git(repo_root, "ls-files", "--", "skills")
    else:
        listing = _git(repo_root, "ls-tree", "-r", "--name-only", ref, "--", "skills")
    files = []
    for line in listing.splitlines():
        path = line.strip()
        if not path:
            continue
        pure = Path(path)
        if pure.parent.parent == SKILLS_ROOT and pure.name == "SKILL.md":
            files.append(pure)
        elif (
            pure.parent.parent.parent == SKILLS_ROOT
            and pure.parent.name == "references"
            and pure.suffix == ".md"
        ):
            files.append(pure)
    return sorted(files)


def read_file(repo_root: Path, path: Path, ref: str | None) -> str:
    if ref is None:
        return (repo_root / path).read_text(encoding="utf-8")
    return _git(repo_root, "show", f"{ref}:{path.as_posix()}")


def weights(repo_root: Path, ref: str | None) -> dict[str, int]:
    return {
        path.as_posix(): _word_count(read_file(repo_root, path, ref))
        for path in tracked_files(repo_root, ref)
    }


def latest_tag(repo_root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "describe", "--tags", "--abbrev=0",
         "--match", "v[0-9]*"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    tag = result.stdout.strip()
    return tag if result.returncode == 0 and re.fullmatch(r"v[\d.]+", tag) else None


def report(repo_root: Path, baseline: str | None) -> int:
    now = weights(repo_root, None)
    ref = baseline
    if ref is None:
        ref = latest_tag(repo_root)
        if ref is None:
            print("no v* tag found; reporting absolute counts only")
    base = weights(repo_root, ref) if ref else {}

    skills = sorted({path.split("/", 2)[1] for path in now} |
                    {path.split("/", 2)[1] for path in base})
    grand_now = grand_base = 0
    for skill in skills:
        prefix = f"skills/{skill}/"
        skill_now = sum(v for k, v in now.items() if k.startswith(prefix))
        skill_base = sum(v for k, v in base.items() if k.startswith(prefix))
        grand_now += skill_now
        grand_base += skill_base
        for key in sorted(set(now) | set(base)):
            if not key.startswith(prefix):
                continue
            file_now = now.get(key, 0)
            file_base = base.get(key, 0)
            if file_now == file_base:
                continue
            status = "added" if key not in base else (
                "removed" if key not in now else "changed"
            )
            print(
                f"{status:>7} {key}: {file_base} -> {file_now} "
                f"({file_now - file_base:+d})"
            )
        print(f"TOTAL {skill}: {skill_base} -> {skill_now} "
              f"({skill_now - skill_base:+d})")
    print(f"GRAND TOTAL: {grand_base} -> {grand_now} ({grand_now - grand_base:+d}) "
          f"baseline: {ref or 'none'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="repository root (default: current directory)",
    )
    parser.add_argument(
        "--baseline",
        help="git ref to compare against (default: most recent v* tag)",
    )
    args = parser.parse_args(argv)
    try:
        return report(args.repo_root, args.baseline)
    except (ManifestError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
